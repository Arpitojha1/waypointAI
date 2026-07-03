"""
Waypoint API — Type-Scoped Recall Helpers

Per-opportunity-type recall queries that scope Cognee searches to the right
datasets and augment queries with relevant context.

These are used by the orchestrator to fetch memory context before generating
roadmaps. Each helper knows which datasets to search and how to frame the
query for its opportunity type.
"""

import logging
from typing import Any, Dict, Optional

from app.memory.cognee_client import recall

logger = logging.getLogger(__name__)


async def recall_for_job(
    query: str,
    user_id: Optional[str] = None,
    job_context: Optional[Dict[str, Any]] = None,
    top_k: int = 15,
) -> Any:
    """
    Recall memory relevant to a job opportunity.

    Searches across user profile, job listings, and feedback datasets
    to surface: user's skill gaps relative to the JD, past feedback
    on similar job-prep steps, and relevant experience.

    Args:
        query: The job title, description, or skill-gap query.
        user_id: Authenticated user's ID for scoped retrieval.
        job_context: Optional dict with job-specific context (title, company, skills).
        top_k: Max results to return.
    """
    # Augment query with job context if available
    augmented_query = query
    if job_context:
        parts = [query]
        if job_context.get("title"):
            parts.append(f"Job: {job_context['title']}")
        if job_context.get("company"):
            parts.append(f"Company: {job_context['company']}")
        if job_context.get("skills"):
            parts.append(f"Required skills: {', '.join(job_context['skills'])}")
        if job_context.get("description"):
            parts.append(f"Description: {job_context['description']}")
        augmented_query = " | ".join(parts)

    # Search across relevant datasets
    datasets = _build_dataset_list(user_id, ["user_profile", "job", "feedback"])

    logger.info("recall_for_job: query='%s' datasets=%s", augmented_query[:80], datasets)

    return await recall(
        query=augmented_query,
        datasets=datasets,
        top_k=top_k,
    )


async def recall_for_hackathon(
    query: str,
    user_id: Optional[str] = None,
    hackathon_context: Optional[Dict[str, Any]] = None,
    top_k: int = 15,
) -> Any:
    """
    Recall memory relevant to a hackathon opportunity.

    Searches across user profile, hackathon listings, and feedback datasets
    to surface: user's relevant project experience, time constraints,
    and past feedback on hackathon-type steps.

    Args:
        query: The hackathon name, theme, or build-plan query.
        user_id: Authenticated user's ID for scoped retrieval.
        hackathon_context: Optional dict with hackathon details (name, deadline, topics).
        top_k: Max results to return.
    """
    augmented_query = query
    if hackathon_context:
        parts = [query]
        if hackathon_context.get("name"):
            parts.append(f"Hackathon: {hackathon_context['name']}")
        if hackathon_context.get("topics"):
            parts.append(f"Topics: {', '.join(hackathon_context['topics'])}")
        if hackathon_context.get("deadline"):
            parts.append(f"Deadline: {hackathon_context['deadline']}")
        if hackathon_context.get("description"):
            parts.append(f"Description: {hackathon_context['description']}")
        augmented_query = " | ".join(parts)

    datasets = _build_dataset_list(user_id, ["user_profile", "hackathon", "feedback"])

    logger.info("recall_for_hackathon: query='%s' datasets=%s", augmented_query[:80], datasets)

    return await recall(
        query=augmented_query,
        datasets=datasets,
        top_k=top_k,
    )


async def recall_for_issue(
    query: str,
    user_id: Optional[str] = None,
    issue_context: Optional[Dict[str, Any]] = None,
    top_k: int = 15,
) -> Any:
    """
    Recall memory relevant to a GitHub issue (good first issue).

    Searches across user profile, issue listings, and feedback datasets
    to surface: user's relevant skills for the issue's tech stack,
    past contribution patterns, and feedback on similar issue-prep steps.

    Args:
        query: The issue title, repo context, or contribution-plan query.
        user_id: Authenticated user's ID for scoped retrieval.
        issue_context: Optional dict with issue details (title, repo, labels, language).
        top_k: Max results to return.
    """
    augmented_query = query
    if issue_context:
        parts = [query]
        if issue_context.get("title"):
            parts.append(f"Issue: {issue_context['title']}")
        if issue_context.get("repo"):
            parts.append(f"Repo: {issue_context['repo']}")
        if issue_context.get("labels"):
            parts.append(f"Labels: {', '.join(issue_context['labels'])}")
        if issue_context.get("language"):
            parts.append(f"Language: {issue_context['language']}")
        if issue_context.get("description"):
            parts.append(f"Description: {issue_context['description']}")
        augmented_query = " | ".join(parts)

    datasets = _build_dataset_list(user_id, ["user_profile", "issue", "feedback"])

    logger.info("recall_for_issue: query='%s' datasets=%s", augmented_query[:80], datasets)

    return await recall(
        query=augmented_query,
        datasets=datasets,
        top_k=top_k,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_dataset_list(user_id: Optional[str], types: list[str]) -> list[str]:
    """Build user-scoped and shared dataset names for Cognee queries."""
    shared_types = {"job", "hackathon", "issue"}
    result = []
    for t in types:
        if t in shared_types:
            result.append(t)
            if user_id:
                result.append(f"{user_id}_{t}")
        elif user_id:
            result.append(f"{user_id}_{t}")
        else:
            result.append(t)
    return list(dict.fromkeys(result))
