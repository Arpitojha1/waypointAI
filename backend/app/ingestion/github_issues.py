"""
Waypoint API — GitHub Good First Issues Ingestion

- fetch_good_first_issues(owner, repo, ...) -> list[dict]
  Searches a specific repo with community-friendly label OR query.
- fetch_good_first_issues_global(language, max_issues, ...) -> list[dict]
  Searches GitHub globally (no repo: qualifier) for community-friendly issues.
- normalize_issue(raw, owner, repo) -> Opportunity
  Normalizes each result into the shared Opportunity schema with type="issue".
- opportunity_to_dict(opp, system_prompt) -> dict
  Formats the Opportunity for Cognee memory ingestion.
- ingest_github_issues(owner, repo, ...) -> list[Opportunity]
  Calls BOTH global search + featured-repo search, deduplicates, normalizes,
  and remembers in Cognee with dataset_name="issue".
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

FEATURED_REPOSITORIES: List[str] = [
    "pytorch/pytorch",
    "microsoft/vscode",
    "matplotlib/matplotlib",
    "vercel/next.js",
    "storybookjs/storybook",
    "gatsbyjs/gatsby",
    "appwrite/appwrite",
    "godotengine/godot",
    "angular/angular",
    "supabase/supabase",
]

# Community-friendly label variants — OR'd via GitHub comma syntax
# Each label is individually quoted; GitHub docs: label:"bug","resolved" matches bug OR resolved
COMMUNITY_LABELS_LIST = [
    "good first issue",
    "good-first-issue",
    "help wanted",
    "beginner friendly",
    "up-for-grabs",
]
COMMUNITY_LABELS = ",".join(f'"{l}"' for l in COMMUNITY_LABELS_LIST)


async def fetch_good_first_issues(
    owner: str,
    repo: str,
    label: str = COMMUNITY_LABELS,
    max_issues: int = 30,
    max_retries: int = 3,
    max_backoff_seconds: int = 60,
    client: Optional[httpx.AsyncClient] = None,
) -> List[Dict[str, Any]]:
    """
    Call GitHub REST API to fetch open issues matching community-friendly labels.
    Uses comma-separated label OR syntax: label:"good first issue,help wanted,..."
    """
    url = "https://api.github.com/search/issues"
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
                "q": f'repo:{owner}/{repo} is:open is:issue label:{label}',
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
                        if not isinstance(data, dict):
                            logger.error("Unexpected GitHub Search API response format for %s/%s: not a dict.", owner, repo)
                            break

                        items = data.get("items", [])
                        if not isinstance(items, list):
                            logger.error("Unexpected GitHub Search API items format for %s/%s: not a list.", owner, repo)
                            break

                        # Filter out any PRs just in case, and ensure state is open
                        page_issues = [
                            item for item in items
                            if isinstance(item, dict) and "pull_request" not in item and item.get("state", "open") == "open"
                        ]
                        issues.extend(page_issues)
                        success = True

                        if len(items) < per_page or len(issues) >= max_issues:
                            # Last page reached
                            return issues[:max_issues]

                    elif response.status_code in (404, 422):
                        logger.error("GitHub repository %s/%s not found or unsearchable (%d).", owner, repo, response.status_code)
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


async def fetch_good_first_issues_global(
    language: Optional[str] = None,
    max_issues: int = 30,
    max_retries: int = 3,
    max_backoff_seconds: int = 60,
    client: Optional[httpx.AsyncClient] = None,
) -> List[Dict[str, Any]]:
    """
    Search GitHub globally (no repo: qualifier) for community-friendly issues.
    Query: is:open is:issue label:"good first issue,help wanted,..." sort:updated-desc
    Optional language: qualifier narrows to a specific programming language.
    """
    url = "https://api.github.com/search/issues"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Waypoint-Career-Agent/0.1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GITHUB_API_KEY")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    q_parts = [
        "is:open",
        "is:issue",
        f'label:{COMMUNITY_LABELS}',
        "sort:updated-desc",
    ]
    if language:
        q_parts.append(f"language:{language}")

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
                "q": " ".join(q_parts),
                "per_page": per_page,
                "page": page,
            }

            attempt = 0
            success = False

            while attempt < max_retries and not success:
                try:
                    logger.info("Fetching GitHub global issues (page %d, attempt %d)...", page, attempt + 1)
                    response = await client.get(url, headers=headers, params=params)

                    remaining = response.headers.get("X-RateLimit-Remaining")
                    reset_time = response.headers.get("X-RateLimit-Reset")
                    retry_after = response.headers.get("Retry-After")

                    if response.status_code == 200:
                        if remaining == "0":
                            logger.warning("GitHub API rate limit remaining is 0. Reset at epoch %s.", reset_time)
                        data = response.json()
                        if not isinstance(data, dict):
                            logger.error("Unexpected GitHub Search API response format: not a dict.")
                            break

                        items = data.get("items", [])
                        if not isinstance(items, list):
                            logger.error("Unexpected GitHub Search API items format: not a list.")
                            break

                        page_issues = [
                            item for item in items
                            if isinstance(item, dict) and "pull_request" not in item and item.get("state", "open") == "open"
                        ]
                        issues.extend(page_issues)
                        success = True

                        total_count = data.get("total_count", 0)
                        logger.info("Global search: got %d items (total_count=%d, accumulated=%d).", len(items), total_count, len(issues))

                        if len(items) < per_page or len(issues) >= max_issues:
                            return issues[:max_issues]

                    elif response.status_code in (403, 429):
                        wait_seconds = 60
                        if retry_after and retry_after.isdigit():
                            wait_seconds = int(retry_after)
                        elif reset_time and reset_time.isdigit():
                            wait_seconds = max(1, int(reset_time) - int(time.time()) + 1)

                        if wait_seconds <= max_backoff_seconds and attempt < max_retries - 1:
                            logger.warning("GitHub API rate limit hit (%d). Sleeping %ds...", response.status_code, wait_seconds)
                            await asyncio.sleep(wait_seconds)
                            attempt += 1
                        else:
                            logger.error("GitHub API rate limit exceeded (%d). Stopping global fetch.", response.status_code)
                            return issues[:max_issues]
                    else:
                        logger.warning("GitHub API returned status %d for global search. Retrying...", response.status_code)
                        attempt += 1
                        await asyncio.sleep(2 ** attempt)

                except (httpx.RequestError, httpx.TimeoutException) as exc:
                    attempt += 1
                    logger.warning("Network error fetching global GitHub issues: %s. Retrying (%d/%d)...", exc, attempt, max_retries)
                    if attempt >= max_retries:
                        logger.error("Exhausted retries for global GitHub issues search.")
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
        source="github_issue",
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


def _extract_owner_repo_from_url(repository_url: str) -> tuple[str, str]:
    """Extract (owner, repo) from a GitHub API repository_url like .../repos/{owner}/{repo}."""
    parts = repository_url.rstrip("/").split("/")
    if len(parts) >= 2:
        return parts[-2], parts[-1]
    return "", ""


async def ingest_github_issues(
    owner: Optional[str] = None,
    repo: Optional[str] = None,
    language: Optional[str] = None,
    max_issues: int = 30,
    remember_in_cognee: bool = True,
    client: Optional[httpx.AsyncClient] = None,
) -> List[Opportunity]:
    """
    Orchestrate full ingestion from two sources:
    1. Global GitHub search (no repo qualifier) for community-friendly issues.
    2. Featured-repo search (HARDCODED list) for each repo.
    Deduplicates by (repo_owner, repo_name, issue_number) before returning.
    """
    seen_keys: set = set()
    all_opportunities: List[Opportunity] = []

    def _dedup_and_append(opp: Opportunity) -> bool:
        key = (opp.repo_owner, opp.repo_name, opp.issue_number)
        if key in seen_keys:
            return False
        seen_keys.add(key)
        all_opportunities.append(opp)
        return True

    async def _remember(opp: Opportunity):
        if not remember_in_cognee:
            return
        try:
            opp_dict = opportunity_to_dict(opp, system_prompt=INGESTION_SYSTEM_PROMPT)
            logger.info("Remembering issue %s/%s#%s in Cognee dataset 'issue'...", opp.repo_owner, opp.repo_name, opp.issue_number)
            await remember(data=opp_dict, data_type="issue", dataset_name="issue")
        except Exception as exc:
            logger.error("Failed to remember issue %s/%s#%s in Cognee: %s", opp.repo_owner, opp.repo_name, opp.issue_number, exc, exc_info=True)

    # --- Source 1: Global search ---
    if not owner or not repo:
        try:
            raw_global = await fetch_good_first_issues_global(language=language, max_issues=max_issues, client=client)
            added_global = 0
            for raw in raw_global:
                repo_url = raw.get("repository_url", "")
                g_owner, g_repo = _extract_owner_repo_from_url(repo_url)
                if not g_owner:
                    # Fallback: try to extract from html_url
                    html_url = raw.get("html_url", "")
                    url_parts = html_url.replace("https://github.com/", "").split("/")
                    if len(url_parts) >= 3:
                        g_owner, g_repo = url_parts[0], url_parts[1]
                opp = normalize_issue(raw, g_owner, g_repo)
                if _dedup_and_append(opp):
                    added_global += 1
                    await _remember(opp)
            logger.info("Global search: %d unique issues added (from %d raw).", added_global, len(raw_global))
        except Exception as exc:
            logger.error("Global GitHub search failed: %s", exc, exc_info=True)

    # --- Source 2: Featured repos ---
    repos = [f"{owner}/{repo}"] if owner and repo else FEATURED_REPOSITORIES
    added_featured = 0
    for repo_full in repos:
        try:
            parts = repo_full.split("/", 1)
            if len(parts) != 2:
                continue
            r_owner, r_repo = parts[0], parts[1]
            raw_issues = await fetch_good_first_issues(owner=r_owner, repo=r_repo, max_issues=max_issues, client=client)
            for raw in raw_issues:
                opp = normalize_issue(raw, r_owner, r_repo)
                if _dedup_and_append(opp):
                    added_featured += 1
                    await _remember(opp)
            logger.info("Featured repo %s/%s: %d issues fetched.", r_owner, r_repo, len(raw_issues))
        except Exception as exc:
            logger.error("Error ingesting featured repo %s: %s", repo_full, exc, exc_info=True)

    logger.info(
        "Ingestion complete: %d total unique issues (global=%d, featured=%d, deduped=%d).",
        len(all_opportunities), added_global if not (owner and repo) else 0, added_featured,
        (added_global if not (owner and repo) else 0) + added_featured - len(all_opportunities),
    )
    return all_opportunities
