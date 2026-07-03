"""
Waypoint API — Devpost Hackathons Ingestion

Deliverable for Phase 3:
- fetch_devpost_hackathons(status: str = "open", ...) -> list[dict]
  Calls Devpost hackathon listing endpoint (/api/hackathons) and returns raw hackathon data.
- normalize_hackathon(raw: dict) -> Opportunity
  Normalizes each result into the shared Opportunity schema with type="hackathon".
- opportunity_to_dict(opp: Opportunity, system_prompt: Optional[str] = DEVPOST_SYSTEM_PROMPT) -> dict
  Formats the Opportunity for Cognee memory ingestion.
- ingest_devpost_hackathons(status: str = "open", ...) -> list[Opportunity]
  Calls fetch -> normalize -> cognee.remember() with dataset_name="hackathon" (shared public data),
  scoped with the devpost-role system prompt.
- Handles rate limiting and ToS considerations gracefully (user-agent, backoff, no crashes).
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from app.db.models import Opportunity, OpportunityType
from app.memory.cognee_client import remember
from app.agents.prompts.devpost import DEVPOST_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


async def fetch_devpost_hackathons(
    status: str = "open",
    max_hackathons: int = 30,
    max_retries: int = 3,
    max_backoff_seconds: int = 60,
    client: Optional[httpx.AsyncClient] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch hackathons from Devpost's JSON listing endpoint (https://devpost.com/api/hackathons).

    ToS & Scraping Considerations:
    - Devpost does not offer a formal public REST API with SLA or official API keys.
    - We utilize the internal JSON endpoint `/api/hackathons` used by Devpost's frontend AJAX listing page.
    - To remain respectful and avoid rate limits or Cloudflare blocking (e.g., HTTP 429 / 403):
      1. We send a descriptive User-Agent header (`Waypoint-Career-Agent/0.1.0`).
      2. We inspect response status and rate-limit headers (`Retry-After`, `X-RateLimit-Reset`).
      3. We apply exponential backoff on errors and gracefully stop fetching without crashing.
    """
    url = "https://devpost.com/api/hackathons"
    headers = {
        "Accept": "application/json",
        "User-Agent": "Waypoint-Career-Agent/0.1.0",
    }

    hackathons: List[Dict[str, Any]] = []
    page = 1
    per_page = min(max_hackathons, 50)

    close_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=15.0)
        close_client = True

    try:
        while len(hackathons) < max_hackathons:
            params = {
                "status[]": status,
                "page": page,
                "per_page": per_page,
            }

            attempt = 0
            success = False

            while attempt < max_retries and not success:
                try:
                    logger.info(
                        "Fetching Devpost hackathons (page %d, attempt %d)...",
                        page, attempt + 1,
                    )
                    response = await client.get(url, headers=headers, params=params)

                    retry_after = response.headers.get("Retry-After")
                    reset_time = response.headers.get("X-RateLimit-Reset")

                    if response.status_code == 200:
                        data = response.json()
                        # The Devpost API returns a dict containing a "hackathons" list,
                        # or sometimes directly a list in mock/test setups.
                        page_items = data.get("hackathons", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
                        if not isinstance(page_items, list):
                            logger.error("Unexpected Devpost API response format: 'hackathons' is not a list.")
                            break

                        hackathons.extend(page_items)
                        success = True

                        if len(page_items) == 0 or (isinstance(data, dict) and data.get("meta", {}).get("total_count", 0) <= len(hackathons)):
                            # Last page reached
                            return hackathons[:max_hackathons]

                    elif response.status_code in (403, 429):
                        wait_seconds = 60
                        if retry_after and retry_after.isdigit():
                            wait_seconds = int(retry_after)
                        elif reset_time and reset_time.isdigit():
                            wait_seconds = max(1, int(reset_time) - int(time.time()) + 1)

                        if wait_seconds <= max_backoff_seconds and attempt < max_retries - 1:
                            logger.warning(
                                "Devpost API rate limit hit (%d). Sleeping for %d seconds before retry...",
                                response.status_code, wait_seconds,
                            )
                            await asyncio.sleep(wait_seconds)
                            attempt += 1
                        else:
                            logger.error(
                                "Devpost API rate limit exceeded (%d). Wait time (%d s) exceeds threshold (%d s) or retries exhausted. Gracefully stopping fetch.",
                                response.status_code, wait_seconds, max_backoff_seconds,
                            )
                            return hackathons[:max_hackathons]
                    else:
                        logger.warning(
                            "Devpost API returned status %d. Retrying...",
                            response.status_code,
                        )
                        attempt += 1
                        await asyncio.sleep(2 ** attempt)

                except (httpx.RequestError, httpx.TimeoutException) as exc:
                    attempt += 1
                    logger.warning(
                        "Network error fetching Devpost hackathons: %s. Retrying (attempt %d/%d)...",
                        exc, attempt, max_retries,
                    )
                    if attempt >= max_retries:
                        logger.error("Exhausted retries due to network errors fetching Devpost hackathons.")
                        return hackathons[:max_hackathons]
                    await asyncio.sleep(2 ** attempt)

            if not success:
                break

            page += 1

    finally:
        if close_client:
            await client.aclose()

    return hackathons[:max_hackathons]


def normalize_hackathon(raw: Dict[str, Any]) -> Opportunity:
    """
    Normalize raw Devpost hackathon dict into the shared Opportunity SQLAlchemy model.
    Sets type="hackathon" per project schema constraints.
    """
    themes = []
    for theme in raw.get("themes", []):
        if isinstance(theme, dict) and "name" in theme:
            themes.append(theme["name"])
        elif isinstance(theme, str):
            themes.append(theme)

    title = str(raw.get("title") or "Untitled Hackathon")[:500]
    if raw.get("tagline"):
        description = str(raw["tagline"])
    elif raw.get("description"):
        description = str(raw["description"])
    else:
        parts = []
        if raw.get("organization_name"):
            parts.append(f"Organized by {raw['organization_name']}.")
        if raw.get("submission_period_dates"):
            parts.append(f"Submission period: {raw['submission_period_dates']}.")
        if raw.get("time_left_to_submission"):
            parts.append(f"Time left: {raw['time_left_to_submission']}.")
        if raw.get("prize_amount"):
            parts.append(f"Prizes: {raw['prize_amount']}.")
        description = " ".join(parts) if parts else "No description provided."
    url = str(raw.get("url") or "https://devpost.com/hackathons")[:2048]

    # Attempt to parse ISO format deadline if provided
    deadline_val = None
    raw_deadline = raw.get("submission_deadline") or raw.get("submission_period_dates")
    if isinstance(raw_deadline, str):
        try:
            if "T" in raw_deadline:
                deadline_val = datetime.fromisoformat(raw_deadline.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            deadline_val = None

    metadata = {
        "themes": themes,
        "prize_amount": raw.get("prize_amount"),
        "registrations_count": raw.get("registrations_count", 0),
        "organization_name": raw.get("organization_name"),
        "submission_period_dates": raw.get("submission_period_dates"),
        "time_left_to_submission": raw.get("time_left_to_submission"),
        "open_state": raw.get("open_state"),
        "thumbnail_url": raw.get("thumbnail_url"),
        "role_scoping": "devpost",
    }

    open_state = str(raw.get("open_state", "open")).lower()
    is_active = open_state in ("open", "upcoming", "recent")

    opportunity = Opportunity(
        id=uuid.uuid4(),
        type=OpportunityType.HACKATHON,
        title=title,
        description=description,
        url=url,
        source="devpost",
        metadata_=metadata,
        deadline=deadline_val,
        is_active=is_active,
    )
    return opportunity


def opportunity_to_dict(
    opp: Opportunity,
    system_prompt: Optional[str] = DEVPOST_SYSTEM_PROMPT,
) -> Dict[str, Any]:
    """
    Convert an Opportunity model instance into a structured dictionary for Cognee ingestion.
    Includes the devpost-role system prompt context per AGENT.md.
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
    if opp.deadline:
        data["deadline"] = opp.deadline.isoformat() if hasattr(opp.deadline, "isoformat") else str(opp.deadline)

    if opp.metadata_:
        data["themes"] = opp.metadata_.get("themes", [])
        data["prize_amount"] = opp.metadata_.get("prize_amount")
        data["registrations_count"] = opp.metadata_.get("registrations_count")
        data["organization_name"] = opp.metadata_.get("organization_name")
        data["submission_period_dates"] = opp.metadata_.get("submission_period_dates")
        data["time_left_to_submission"] = opp.metadata_.get("time_left_to_submission")

    if system_prompt:
        data["ingestion_role_scoping"] = system_prompt

    return data


async def ingest_devpost_hackathons(
    status: str = "open",
    max_hackathons: int = 30,
    remember_in_cognee: bool = True,
    client: Optional[httpx.AsyncClient] = None,
) -> List[Opportunity]:
    """
    Orchestrate full Devpost hackathon ingestion:
    1. Fetch hackathons from Devpost API/endpoint.
    2. Normalize each into an Opportunity schema object.
    3. Call cognee.remember() with dataset_name="hackathon" (shared public data),
       using the devpost-role system prompt scoping.
    """
    raw_hackathons = await fetch_devpost_hackathons(
        status=status,
        max_hackathons=max_hackathons,
        client=client,
    )

    opportunities: List[Opportunity] = []
    for raw in raw_hackathons:
        opp = normalize_hackathon(raw)
        opportunities.append(opp)

        if remember_in_cognee:
            try:
                opp_dict = opportunity_to_dict(opp, system_prompt=DEVPOST_SYSTEM_PROMPT)
                logger.info(
                    "Remembering hackathon '%s' in Cognee dataset 'hackathon'...",
                    opp.title,
                )
                await remember(
                    data=opp_dict,
                    data_type="hackathon",
                    dataset_name="hackathon",
                )
            except Exception as exc:
                # Log error and continue — don't crash ingestion run on memory storage failure
                logger.error(
                    "Failed to remember hackathon '%s' in Cognee: %s",
                    opp.title, exc, exc_info=True,
                )

    logger.info(
        "Successfully ingested %d hackathons from Devpost.",
        len(opportunities),
    )
    return opportunities
