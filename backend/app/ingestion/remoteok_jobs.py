"""
Waypoint API — RemoteOK Jobs Ingestion

Fetches remote job postings from RemoteOK's public JSON API (https://remoteok.com/api).
RemoteOK returns a flat JSON array where the first element is metadata/legal info — skipped.
Jobs are normalized into the shared Opportunity schema with type="job" and source="remoteok".
"""

import asyncio
import logging
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.db.models import Opportunity, OpportunityType
from app.memory.cognee_client import remember
from app.agents.prompts.remoteok import REMOTEOK_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


async def fetch_remoteok_jobs(
    max_jobs: int = 30,
    max_retries: int = 3,
    max_backoff_seconds: int = 60,
    client: Optional[httpx.AsyncClient] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch job postings from RemoteOK's public JSON API (https://remoteok.com/api).
    RemoteOK returns a single JSON array; the first element is metadata (not a job) and is skipped.

    ToS & Scraping Considerations:
    - RemoteOK provides a public JSON API but blocks default/empty User-Agent headers.
    - We send a descriptive User-Agent header (Waypoint-Career-Agent/0.1.0).
    - We apply exponential backoff on errors and gracefully stop without crashing.
    """
    url = "https://remoteok.com/api"
    headers = {
        "Accept": "application/json",
        "User-Agent": "Waypoint-Career-Agent/0.1.0",
    }

    close_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=15.0)
        close_client = True

    try:
        attempt = 0
        while attempt < max_retries:
            try:
                logger.info("Fetching RemoteOK jobs (attempt %d)...", attempt + 1)
                response = await client.get(url, headers=headers)

                if response.status_code == 200:
                    data = response.json()
                    if not isinstance(data, list):
                        logger.error("Unexpected RemoteOK API response format: expected list, got %s.", type(data).__name__)
                        return []

                    # First element is metadata/legal info — skip it
                    jobs = data[1:] if len(data) > 1 else []
                    logger.info("Fetched %d jobs from RemoteOK.", len(jobs))
                    return jobs[:max_jobs]

                elif response.status_code in (403, 429):
                    retry_after = response.headers.get("Retry-After")
                    wait_seconds = 60
                    if retry_after and retry_after.isdigit():
                        wait_seconds = int(retry_after)

                    if wait_seconds <= max_backoff_seconds and attempt < max_retries - 1:
                        logger.warning(
                            "RemoteOK API rate limit hit (%d). Sleeping for %d seconds before retry...",
                            response.status_code, wait_seconds,
                        )
                        await asyncio.sleep(wait_seconds)
                        attempt += 1
                    else:
                        logger.error(
                            "RemoteOK API rate limit exceeded (%d). Wait time (%d s) exceeds threshold or retries exhausted.",
                            response.status_code, wait_seconds,
                        )
                        return []
                else:
                    logger.warning("RemoteOK API returned status %d. Retrying...", response.status_code)
                    attempt += 1
                    await asyncio.sleep(2 ** attempt)

            except (httpx.RequestError, httpx.TimeoutException) as exc:
                attempt += 1
                logger.warning(
                    "Network error fetching RemoteOK jobs: %s. Retrying (attempt %d/%d)...",
                    exc, attempt, max_retries,
                )
                if attempt >= max_retries:
                    logger.error("Exhausted retries due to network errors fetching RemoteOK jobs.")
                    return []
                await asyncio.sleep(2 ** attempt)

        return []

    finally:
        if close_client:
            await client.aclose()


def normalize_job(raw: Dict[str, Any]) -> Opportunity:
    """
    Normalize raw RemoteOK job dict into the shared Opportunity SQLAlchemy model.
    RemoteOK fields: position (title), description, url, company, location, tags, epoch.
    """
    title = str(raw.get("position") or raw.get("title") or "Untitled Job")[:500]
    description = str(raw.get("description") or "No description provided.")
    url = str(raw.get("url") or raw.get("apply_url") or "https://remoteok.com")[:2048]
    company = str(raw.get("company") or "")[:500] if raw.get("company") else None
    location = str(raw.get("location") or "")[:500] if raw.get("location") else None

    tags = raw.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]

    epoch = raw.get("epoch")
    created_dt_iso = None
    if isinstance(epoch, (int, float)):
        try:
            created_dt_iso = datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()
        except (ValueError, OSError, OverflowError):
            created_dt_iso = None

    metadata = {
        "tags": tags,
        "salary_min": raw.get("salary_min"),
        "salary_max": raw.get("salary_max"),
        "remote": True,  # RemoteOK is remote-only
        "created_at_timestamp": epoch,
        "created_at_iso": created_dt_iso,
        "role_scoping": "remoteok",
    }

    return Opportunity(
        id=uuid.uuid4(),
        type=OpportunityType.JOB,
        title=title,
        description=description,
        url=url,
        source="remoteok",
        company=company,
        location=location,
        metadata_=metadata,
        is_active=True,
    )


def opportunity_to_dict(
    opp: Opportunity,
    system_prompt: Optional[str] = REMOTEOK_SYSTEM_PROMPT,
) -> Dict[str, Any]:
    """
    Convert an Opportunity model instance into a structured dictionary for Cognee ingestion.
    Includes the remoteok-role system prompt context per AGENT.MD.
    """
    data = {
        "id": str(opp.id),
        "type": opp.type.value if hasattr(opp.type, "value") else str(opp.type),
        "title": opp.title,
        "description": opp.description,
        "url": opp.url,
        "source": opp.source,
        "is_active": opp.is_active,
    }
    if opp.company:
        data["company"] = opp.company
    if opp.location:
        data["location"] = opp.location

    if opp.metadata_:
        data["tags"] = opp.metadata_.get("tags", [])
        data["remote"] = opp.metadata_.get("remote", True)
        data["salary_min"] = opp.metadata_.get("salary_min")
        data["salary_max"] = opp.metadata_.get("salary_max")
        data["created_at_timestamp"] = opp.metadata_.get("created_at_timestamp")

    if system_prompt:
        data["ingestion_role_scoping"] = system_prompt

    return data


async def ingest_remoteok_jobs(
    max_jobs: int = 30,
    remember_in_cognee: bool = True,
    client: Optional[httpx.AsyncClient] = None,
) -> List[Opportunity]:
    """
    Orchestrate full RemoteOK job posting ingestion:
    1. Fetch job postings from RemoteOK API.
    2. Normalize each into an Opportunity schema object.
    3. Call cognee.remember() with dataset_name="job" (shared public data),
       using the remoteok-role system prompt scoping.
    """
    raw_jobs = await fetch_remoteok_jobs(
        max_jobs=max_jobs,
        client=client,
    )

    opportunities: List[Opportunity] = []
    for raw in raw_jobs:
        opp = normalize_job(raw)
        opportunities.append(opp)

        if remember_in_cognee:
            try:
                opp_dict = opportunity_to_dict(opp, system_prompt=REMOTEOK_SYSTEM_PROMPT)
                logger.info("Remembering job '%s' in Cognee dataset 'job'...", opp.title)
                await remember(
                    data=opp_dict,
                    data_type="job",
                    dataset_name="job",
                )
            except Exception as exc:
                logger.error(
                    "Failed to remember job '%s' in Cognee: %s",
                    opp.title, exc, exc_info=True,
                )

    logger.info("Successfully ingested %d jobs from RemoteOK.", len(opportunities))
    return opportunities
