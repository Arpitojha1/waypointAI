"""
Waypoint API — Remotive Jobs Ingestion

Fetches remote job postings from Remotive's public JSON API (https://remotive.com/api/remote-jobs).
Remotive returns {"jobs": [...]} with HTML descriptions that are stripped before storage.
Jobs are normalized into the shared Opportunity schema with type="job" and source="remotive".
"""

import asyncio
import html
import logging
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.db.models import Opportunity, OpportunityType
from app.memory.cognee_client import remember
from app.agents.prompts.remotive import REMOTIVE_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


def _strip_html_tags(text: str) -> str:
    """Remove HTML tags from a string, decoding common entities."""
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = html.unescape(clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


async def fetch_remotive_jobs(
    search: Optional[str] = None,
    max_jobs: int = 30,
    max_retries: int = 3,
    max_backoff_seconds: int = 60,
    client: Optional[httpx.AsyncClient] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch job postings from Remotive's public JSON API (https://remotive.com/api/remote-jobs).
    Response shape: {"jobs": [...]}.
    Optional ?search= parameter filters by keyword.

    ToS & Scraping Considerations:
    - Remotive provides a documented public API.
    - We send a descriptive User-Agent header (Waypoint-Career-Agent/0.1.0).
    - We apply exponential backoff on errors and gracefully stop without crashing.
    """
    url = "https://remotive.com/api/remote-jobs"
    headers = {
        "Accept": "application/json",
        "User-Agent": "Waypoint-Career-Agent/0.1.0",
    }

    params: Dict[str, Any] = {}
    if search:
        params["search"] = search

    close_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=15.0)
        close_client = True

    try:
        attempt = 0
        while attempt < max_retries:
            try:
                logger.info("Fetching Remotive jobs (attempt %d)...", attempt + 1)
                response = await client.get(url, headers=headers, params=params)

                if response.status_code == 200:
                    data = response.json()
                    jobs = data.get("jobs", []) if isinstance(data, dict) else []
                    if not isinstance(jobs, list):
                        logger.error("Unexpected Remotive API response format: 'jobs' is not a list.")
                        return []
                    logger.info("Fetched %d jobs from Remotive.", len(jobs))
                    return jobs[:max_jobs]

                elif response.status_code in (403, 429):
                    retry_after = response.headers.get("Retry-After")
                    wait_seconds = 60
                    if retry_after and retry_after.isdigit():
                        wait_seconds = int(retry_after)

                    if wait_seconds <= max_backoff_seconds and attempt < max_retries - 1:
                        logger.warning(
                            "Remotive API rate limit hit (%d). Sleeping for %d seconds before retry...",
                            response.status_code, wait_seconds,
                        )
                        await asyncio.sleep(wait_seconds)
                        attempt += 1
                    else:
                        logger.error(
                            "Remotive API rate limit exceeded (%d). Wait time (%d s) exceeds threshold or retries exhausted.",
                            response.status_code, wait_seconds,
                        )
                        return []
                else:
                    logger.warning("Remotive API returned status %d. Retrying...", response.status_code)
                    attempt += 1
                    await asyncio.sleep(2 ** attempt)

            except (httpx.RequestError, httpx.TimeoutException) as exc:
                attempt += 1
                logger.warning(
                    "Network error fetching Remotive jobs: %s. Retrying (attempt %d/%d)...",
                    exc, attempt, max_retries,
                )
                if attempt >= max_retries:
                    logger.error("Exhausted retries due to network errors fetching Remotive jobs.")
                    return []
                await asyncio.sleep(2 ** attempt)

        return []

    finally:
        if close_client:
            await client.aclose()


def normalize_job(raw: Dict[str, Any]) -> Opportunity:
    """
    Normalize raw Remotive job dict into the shared Opportunity SQLAlchemy model.
    Remotive fields: title, description (HTML), url, company_name, candidate_required_location, tags.
    HTML in description is stripped before storage.
    """
    title = str(raw.get("title") or "Untitled Job")[:500]
    raw_desc = str(raw.get("description") or "No description provided.")
    description = _strip_html_tags(raw_desc)
    url = str(raw.get("url") or raw.get("candidate_required_location") or "https://remotive.com")[:2048]
    company = str(raw.get("company_name") or "")[:500] if raw.get("company_name") else None
    location = str(raw.get("candidate_required_location") or "")[:500] if raw.get("candidate_required_location") else None

    tags = raw.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]

    pub_date = raw.get("publication_date")
    created_dt_iso = None
    if isinstance(pub_date, str):
        try:
            created_dt_iso = datetime.fromisoformat(pub_date.replace("Z", "+00:00")).isoformat()
        except (ValueError, TypeError):
            created_dt_iso = pub_date

    metadata = {
        "tags": tags,
        "category": raw.get("category"),
        "salary": raw.get("salary"),
        "remote": True,  # Remotive is remote-only
        "created_at_iso": created_dt_iso,
        "role_scoping": "remotive",
    }

    return Opportunity(
        id=uuid.uuid4(),
        type=OpportunityType.JOB,
        title=title,
        description=description,
        url=url,
        source="remotive",
        company=company,
        location=location,
        metadata_=metadata,
        is_active=True,
    )


def opportunity_to_dict(
    opp: Opportunity,
    system_prompt: Optional[str] = REMOTIVE_SYSTEM_PROMPT,
) -> Dict[str, Any]:
    """
    Convert an Opportunity model instance into a structured dictionary for Cognee ingestion.
    Includes the remotive-role system prompt context per AGENT.MD.
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
        data["category"] = opp.metadata_.get("category")
        data["salary"] = opp.metadata_.get("salary")
        data["remote"] = opp.metadata_.get("remote", True)
        data["created_at_iso"] = opp.metadata_.get("created_at_iso")

    if system_prompt:
        data["ingestion_role_scoping"] = system_prompt

    return data


async def ingest_remotive_jobs(
    search: Optional[str] = None,
    max_jobs: int = 30,
    remember_in_cognee: bool = True,
    client: Optional[httpx.AsyncClient] = None,
) -> List[Opportunity]:
    """
    Orchestrate full Remotive job posting ingestion:
    1. Fetch job postings from Remotive API.
    2. Normalize each into an Opportunity schema object.
    3. Call cognee.remember() with dataset_name="job" (shared public data),
       using the remotive-role system prompt scoping.
    """
    raw_jobs = await fetch_remotive_jobs(
        search=search,
        max_jobs=max_jobs,
        client=client,
    )

    opportunities: List[Opportunity] = []
    for raw in raw_jobs:
        opp = normalize_job(raw)
        opportunities.append(opp)

        if remember_in_cognee:
            try:
                opp_dict = opportunity_to_dict(opp, system_prompt=REMOTIVE_SYSTEM_PROMPT)
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

    logger.info("Successfully ingested %d jobs from Remotive.", len(opportunities))
    return opportunities
