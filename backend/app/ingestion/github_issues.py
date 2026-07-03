"""
Waypoint API — GitHub Good First Issues Ingestion

Deliverable for Phase 2:
- fetch_good_first_issues(owner: str, repo: str) -> list[dict]
  Calls the GitHub API (label:"good first issue", open, unassigned) and returns raw issue data.
- normalize_issue(raw: dict, owner: str, repo: str) -> Opportunity
  Normalizes each result into the shared Opportunity schema with type="issue".
- opportunity_to_dict(opp: Opportunity, system_prompt: Optional[str] = INGESTION_SYSTEM_PROMPT) -> dict
  Formats the Opportunity for Cognee memory ingestion.
- ingest_github_issues(owner: str, repo: str, ...) -> list[Opportunity]
  Calls fetch -> normalize -> cognee.remember() with dataset_name="issue" (shared public data),
  scoped with the ingestion-role system prompt.
- Handles rate limiting gracefully (log and back off, no crashes).
"""

import asyncio
import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional

import httpx

from app.db.models import Opportunity, OpportunityType
from app.memory.cognee_client import remember
from app.agents.prompts.ingestion import INGESTION_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


async def fetch_good_first_issues(
    owner: str,
    repo: str,
    label: str = "good first issue",
    max_issues: int = 30,
    max_retries: int = 3,
    max_backoff_seconds: int = 60,
    client: Optional[httpx.AsyncClient] = None,
) -> List[Dict[str, Any]]:
    """
    Call GitHub REST API to fetch open, unassigned issues with the given label.

    Handles unauthenticated rate limits (60 req/hr) gracefully by checking headers,
    logging warnings, and backing off exponentially or via Retry-After/X-RateLimit-Reset.
    Does not crash on rate limit exhaustion or network failure.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Waypoint-Career-Agent/0.1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # Optional token if present in environment (never touches .env)
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GITHUB_API_KEY")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    issues: List[Dict[str, Any]] = []
    page = 1
    per_page = min(max_issues, 100)

    close_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=15.0)
        close_client = True

    try:
        while len(issues) < max_issues:
            params = {
                "state": "open",
                "labels": label,
                "assignee": "none",
                "per_page": per_page,
                "page": page,
            }

            attempt = 0
            success = False

            while attempt < max_retries and not success:
                try:
                    logger.info(
                        "Fetching GitHub issues for %s/%s (page %d, attempt %d)...",
                        owner, repo, page, attempt + 1,
                    )
                    response = await client.get(url, headers=headers, params=params)

                    # Inspect rate limit headers
                    remaining = response.headers.get("X-RateLimit-Remaining")
                    reset_time = response.headers.get("X-RateLimit-Reset")
                    retry_after = response.headers.get("Retry-After")

                    if response.status_code == 200:
                        if remaining == "0":
                            logger.warning(
                                "GitHub API rate limit remaining is 0 for %s/%s. Reset at epoch %s.",
                                owner, repo, reset_time,
                            )
                        data = response.json()
                        if not isinstance(data, list):
                            logger.error("Unexpected GitHub API response format for %s/%s: not a list.", owner, repo)
                            break

                        # GitHub API returns pull requests inside /issues endpoint; filter them out and ensure state is open
                        page_issues = [item for item in data if isinstance(item, dict) and "pull_request" not in item and item.get("state") == "open"]
                        issues.extend(page_issues)
                        success = True

                        if len(data) < per_page:
                            # Last page reached
                            return issues[:max_issues]

                    elif response.status_code == 404:
                        logger.error("GitHub repository %s/%s not found (404).", owner, repo)
                        return issues

                    elif response.status_code in (403, 429):
                        wait_seconds = 60
                        if retry_after and retry_after.isdigit():
                            wait_seconds = int(retry_after)
                        elif reset_time and reset_time.isdigit():
                            wait_seconds = max(1, int(reset_time) - int(time.time()) + 1)

                        if wait_seconds <= max_backoff_seconds and attempt < max_retries - 1:
                            logger.warning(
                                "GitHub API rate limit hit (%d). Sleeping for %d seconds before retry...",
                                response.status_code, wait_seconds,
                            )
                            await asyncio.sleep(wait_seconds)
                            attempt += 1
                        else:
                            logger.error(
                                "GitHub API rate limit exceeded (%d). Wait time (%d s) exceeds threshold (%d s) or retries exhausted. Gracefully stopping fetch.",
                                response.status_code, wait_seconds, max_backoff_seconds,
                            )
                            return issues[:max_issues]
                    else:
                        logger.warning(
                            "GitHub API returned status %d for %s/%s. Retrying...",
                            response.status_code, owner, repo,
                        )
                        attempt += 1
                        await asyncio.sleep(2 ** attempt)

                except (httpx.RequestError, httpx.TimeoutException) as exc:
                    attempt += 1
                    logger.warning(
                        "Network error fetching GitHub issues for %s/%s: %s. Retrying (attempt %d/%d)...",
                        owner, repo, exc, attempt, max_retries,
                    )
                    if attempt >= max_retries:
                        logger.error("Exhausted retries due to network errors for %s/%s.", owner, repo)
                        return issues[:max_issues]
                    await asyncio.sleep(2 ** attempt)

            if not success:
                break

            page += 1

    finally:
        if close_client:
            await client.aclose()

    return issues[:max_issues]


def normalize_issue(raw: Dict[str, Any], owner: str, repo: str) -> Opportunity:
    """
    Normalize raw GitHub issue dict into the shared Opportunity SQLAlchemy model.
    Sets type="issue" per project schema constraints.
    """
    labels = []
    for lbl in raw.get("labels", []):
        if isinstance(lbl, dict) and "name" in lbl:
            labels.append(lbl["name"])
        elif isinstance(lbl, str):
            labels.append(lbl)

    title = str(raw.get("title") or "Untitled Issue")[:500]
    description = str(raw.get("body") or "No description provided.")
    issue_number = raw.get("number")
    url = str(raw.get("html_url") or f"https://github.com/{owner}/{repo}/issues/{issue_number if issue_number else ''}")[:2048]

    author = None
    if isinstance(raw.get("user"), dict):
        author = raw.get("user", {}).get("login")

    assignee = None
    if isinstance(raw.get("assignee"), dict):
        assignee = raw.get("assignee", {}).get("login")

    metadata = {
        "labels": labels,
        "created_at": raw.get("created_at"),
        "updated_at": raw.get("updated_at"),
        "comments_count": raw.get("comments", 0),
        "author": author,
        "assignee": assignee,
        "role_scoping": "ingestion",
    }

    opportunity = Opportunity(
        id=uuid.uuid4(),
        type=OpportunityType.ISSUE,
        title=title,
        description=description,
        url=url,
        source="github",
        metadata_=metadata,
        repo_owner=owner[:255],
        repo_name=repo[:255],
        issue_number=issue_number if isinstance(issue_number, int) else None,
        is_active=(raw.get("state", "open") == "open"),
    )
    return opportunity


async def verify_github_issue_open(
    owner: str,
    repo: str,
    issue_number: int,
    client: Optional[httpx.AsyncClient] = None,
) -> bool:
    """
    Check GitHub REST API to confirm if an issue is still currently open.
    Returns True if open (or if rate-limited/network failure occurs, to fail open/gracefully).
    Returns False only if GitHub explicitly confirms state is not open or issue was deleted (404/closed).
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Waypoint-Career-Agent/0.1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GITHUB_API_KEY")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    close_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=5.0)
        close_client = True

    try:
        res = await client.get(url, headers=headers)
        if res.status_code == 200:
            data = res.json()
            return data.get("state") == "open" and "pull_request" not in data
        elif res.status_code == 404:
            return False
        else:
            # Rate limited, 403, or 500 -> fail open
            return True
    except Exception as exc:
        logger.warning("Error verifying GitHub issue %s/%s#%d: %s", owner, repo, issue_number, exc)
        return True
    finally:
        if close_client:
            await client.aclose()


def opportunity_to_dict(
    opp: Opportunity,
    system_prompt: Optional[str] = INGESTION_SYSTEM_PROMPT,
) -> Dict[str, Any]:
    """
    Convert an Opportunity model instance into a structured dictionary for Cognee ingestion.
    Includes the ingestion-role system prompt context per AGENT.md.
    """
    data = {
        "id": str(opp.id),
        "type": opp.type.value if hasattr(opp.type, "value") else str(opp.type),
        "title": opp.title,
        "description": opp.description,
        "url": opp.url,
        "source": opp.source,
        "repo_owner": opp.repo_owner,
        "repo_name": opp.repo_name,
        "issue_number": opp.issue_number,
        "is_active": opp.is_active,
    }
    if opp.metadata_:
        data["labels"] = opp.metadata_.get("labels", [])
        data["created_at"] = opp.metadata_.get("created_at")
        data["updated_at"] = opp.metadata_.get("updated_at")
        data["comments_count"] = opp.metadata_.get("comments_count")
        data["author"] = opp.metadata_.get("author")

    if system_prompt:
        data["ingestion_role_scoping"] = system_prompt

    return data


async def ingest_github_issues(
    owner: str,
    repo: str,
    label: str = "good first issue",
    max_issues: int = 30,
    remember_in_cognee: bool = True,
    client: Optional[httpx.AsyncClient] = None,
) -> List[Opportunity]:
    """
    Orchestrate full ingestion:
    1. Fetch good first issues from GitHub API.
    2. Normalize each into an Opportunity schema object.
    3. Call cognee.remember() with dataset_name="issue" (shared public data),
       using the ingestion-role system prompt scoping.
    """
    raw_issues = await fetch_good_first_issues(
        owner=owner,
        repo=repo,
        label=label,
        max_issues=max_issues,
        client=client,
    )

    opportunities: List[Opportunity] = []
    for raw in raw_issues:
        opp = normalize_issue(raw, owner, repo)
        opportunities.append(opp)

        if remember_in_cognee:
            try:
                opp_dict = opportunity_to_dict(opp, system_prompt=INGESTION_SYSTEM_PROMPT)
                logger.info(
                    "Remembering issue #%s in Cognee dataset 'issue'...",
                    opp.issue_number,
                )
                await remember(
                    data=opp_dict,
                    data_type="issue",
                    dataset_name="issue",
                )
            except Exception as exc:
                # Log error and continue — don't crash ingestion run on memory storage failure
                logger.error(
                    "Failed to remember issue #%s in Cognee: %s",
                    opp.issue_number, exc, exc_info=True,
                )

    logger.info(
        "Successfully ingested %d issues for repository %s/%s.",
        len(opportunities), owner, repo,
    )
    return opportunities
