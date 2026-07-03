"""
Waypoint API — Arbeitnow Jobs Ingestion

Deliverable for Phase 4:
- fetch_arbeitnow_jobs(...) -> list[dict]
  Calls Arbeitnow job board listing endpoint (/api/job-board-api) and returns raw job data.
- normalize_job(raw: dict) -> Opportunity
  Normalizes each result into the shared Opportunity schema with type="job".
- opportunity_to_dict(opp: Opportunity, system_prompt: Optional[str] = ARBEITNOW_SYSTEM_PROMPT) -> dict
  Formats the Opportunity for Cognee memory ingestion.
- ingest_arbeitnow_jobs(...) -> list[Opportunity]
  Calls fetch -> normalize -> cognee.remember() with dataset_name="job" (shared public data),
  scoped with the arbeitnow-role system prompt.
- Handles rate limiting and ToS considerations gracefully (user-agent, backoff, no crashes).
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.db.models import Opportunity, OpportunityType
from app.memory.cognee_client import remember
from app.agents.prompts.arbeitnow import ARBEITNOW_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


async def fetch_arbeitnow_jobs(
    page: int = 1,
    max_jobs: int = 30,
    search: Optional[str] = None,
    max_retries: int = 3,
    max_backoff_seconds: int = 60,
    client: Optional[httpx.AsyncClient] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch job postings from Arbeitnow's public API endpoint (https://www.arbeitnow.com/api/job-board-api).

    ToS & Scraping Considerations:
    - Arbeitnow offers a documented, free public API for job listings.
    - To remain respectful and avoid rate limits or blocking (e.g., HTTP 429 / 403):
      1. We send a descriptive User-Agent header (`Waypoint-Career-Agent/0.1.0`).
      2. We inspect response status and rate-limit headers (`Retry-After`, `X-RateLimit-Reset`).
      3. We apply exponential backoff on errors and gracefully stop fetching without crashing.
    """
    url = "https://www.arbeitnow.com/api/job-board-api"
    headers = {
        "Accept": "application/json",
        "User-Agent": "Waypoint-Career-Agent/0.1.0",
    }

    jobs: List[Dict[str, Any]] = []
    current_page = page

    close_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=15.0)
        close_client = True

    try:
        while len(jobs) < max_jobs:
            params: Dict[str, Any] = {"page": current_page}
            if search:
                params["search"] = search

            attempt = 0
            success = False

            while attempt < max_retries and not success:
                try:
                    logger.info(
                        "Fetching Arbeitnow jobs (page %d, attempt %d)...",
                        current_page, attempt + 1,
                    )
                    response = await client.get(url, headers=headers, params=params)

                    retry_after = response.headers.get("Retry-After")
                    reset_time = response.headers.get("X-RateLimit-Reset")

                    if response.status_code == 200:
                        data = response.json()
                        # The Arbeitnow API returns a dict containing a "data" list,
                        # or sometimes directly a list in mock/test setups.
                        page_items = data.get("data", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
                        if not isinstance(page_items, list):
                            logger.error("Unexpected Arbeitnow API response format: 'data' is not a list.")
                            break

                        jobs.extend(page_items)
                        success = True

                        if len(page_items) == 0 or (isinstance(data, dict) and data.get("links", {}).get("next") is None):
                            # Last page reached
                            return jobs[:max_jobs]

                    elif response.status_code in (403, 429):
                        wait_seconds = 60
                        if retry_after and retry_after.isdigit():
                            wait_seconds = int(retry_after)
                        elif reset_time and reset_time.isdigit():
                            wait_seconds = max(1, int(reset_time) - int(time.time()) + 1)

                        if wait_seconds <= max_backoff_seconds and attempt < max_retries - 1:
                            logger.warning(
                                "Arbeitnow API rate limit hit (%d). Sleeping for %d seconds before retry...",
                                response.status_code, wait_seconds,
                            )
                            await asyncio.sleep(wait_seconds)
                            attempt += 1
                        else:
                            logger.error(
                                "Arbeitnow API rate limit exceeded (%d). Wait time (%d s) exceeds threshold (%d s) or retries exhausted. Gracefully stopping fetch.",
                                response.status_code, wait_seconds, max_backoff_seconds,
                            )
                            return jobs[:max_jobs]
                    else:
                        logger.warning(
                            "Arbeitnow API returned status %d. Retrying...",
                            response.status_code,
                        )
                        attempt += 1
                        await asyncio.sleep(2 ** attempt)

                except (httpx.RequestError, httpx.TimeoutException) as exc:
                    attempt += 1
                    logger.warning(
                        "Network error fetching Arbeitnow jobs: %s. Retrying (attempt %d/%d)...",
                        exc, attempt, max_retries,
                    )
                    if attempt >= max_retries:
                        logger.error("Exhausted retries due to network errors fetching Arbeitnow jobs.")
                        return jobs[:max_jobs]
                    await asyncio.sleep(2 ** attempt)

            if not success:
                break

            current_page += 1

    finally:
        if close_client:
            await client.aclose()

    return jobs[:max_jobs]


def normalize_job(raw: Dict[str, Any]) -> Opportunity:
    """
    Normalize raw Arbeitnow job dict into the shared Opportunity SQLAlchemy model.
    Sets type="job" per project schema constraints.
    """
    title = str(raw.get("title") or "Untitled Job")[:500]
    description = str(raw.get("description") or "No description provided.")
    url = str(raw.get("url") or "https://www.arbeitnow.com")[:2048]
    company = str(raw.get("company_name") or "")[:500] if raw.get("company_name") else None
    location = str(raw.get("location") or "")[:500] if raw.get("location") else None

    # Attempt to convert UNIX timestamp to ISO date or datetime if provided
    created_at_val = raw.get("created_at")
    created_dt_iso = None
    if isinstance(created_at_val, (int, float)):
        try:
            created_dt_iso = datetime.fromtimestamp(created_at_val, tz=timezone.utc).isoformat()
        except (ValueError, OSError, OverflowError):
            created_dt_iso = None

    metadata = {
        "slug": raw.get("slug"),
        "remote": raw.get("remote", False),
        "tags": raw.get("tags", []),
        "job_types": raw.get("job_types", []),
        "created_at_timestamp": created_at_val,
        "created_at_iso": created_dt_iso,
        "role_scoping": "arbeitnow",
    }

    opportunity = Opportunity(
        id=uuid.uuid4(),
        type=OpportunityType.JOB,
        title=title,
        description=description,
        url=url,
        source="arbeitnow",
        company=company,
        location=location,
        metadata_=metadata,
        is_active=True,
    )
    return opportunity


def opportunity_to_dict(
    opp: Opportunity,
    system_prompt: Optional[str] = ARBEITNOW_SYSTEM_PROMPT,
) -> Dict[str, Any]:
    """
    Convert an Opportunity model instance into a structured dictionary for Cognee ingestion.
    Includes the arbeitnow-role system prompt context per AGENT.md.
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
        data["slug"] = opp.metadata_.get("slug")
        data["remote"] = opp.metadata_.get("remote")
        data["tags"] = opp.metadata_.get("tags", [])
        data["job_types"] = opp.metadata_.get("job_types", [])
        data["created_at_timestamp"] = opp.metadata_.get("created_at_timestamp")

    if system_prompt:
        data["ingestion_role_scoping"] = system_prompt

    return data


async def ingest_arbeitnow_jobs(
    page: int = 1,
    max_jobs: int = 30,
    search: Optional[str] = None,
    remember_in_cognee: bool = True,
    client: Optional[httpx.AsyncClient] = None,
) -> List[Opportunity]:
    """
    Orchestrate full Arbeitnow job posting ingestion:
    1. Fetch job postings from Arbeitnow API/endpoint.
    2. Normalize each into an Opportunity schema object.
    3. Call cognee.remember() with dataset_name="job" (shared public data),
       using the arbeitnow-role system prompt scoping.
    """
    raw_jobs = await fetch_arbeitnow_jobs(
        page=page,
        max_jobs=max_jobs,
        search=search,
        client=client,
    )

    opportunities: List[Opportunity] = []
    for raw in raw_jobs:
        opp = normalize_job(raw)
        opportunities.append(opp)

        if remember_in_cognee:
            try:
                opp_dict = opportunity_to_dict(opp, system_prompt=ARBEITNOW_SYSTEM_PROMPT)
                logger.info(
                    "Remembering job '%s' in Cognee dataset 'job'...",
                    opp.title,
                )
                await remember(
                    data=opp_dict,
                    data_type="job",
                    dataset_name="job",
                )
            except Exception as exc:
                # Log error and continue — don't crash ingestion run on memory storage failure
                logger.error(
                    "Failed to remember job '%s' in Cognee: %s",
                    opp.title, exc, exc_info=True,
                )

    logger.info(
        "Successfully ingested %d jobs from Arbeitnow.",
        len(opportunities),
    )
    return opportunities
