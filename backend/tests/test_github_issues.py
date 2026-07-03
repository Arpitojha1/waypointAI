"""
Unit tests for GitHub Good First Issues Ingestion (Phase 2).
Uses httpx.MockTransport to test API fetching, rate limit backoff handling,
and normalization without requiring live network or touching .env.
"""

import asyncio
import time
import uuid
import pytest
import httpx

from app.db.models import Opportunity, OpportunityType
from app.ingestion.github_issues import (
    fetch_good_first_issues,
    normalize_issue,
    opportunity_to_dict,
    ingest_github_issues,
)
from app.agents.prompts.ingestion import INGESTION_SYSTEM_PROMPT


def test_normalize_issue():
    raw_issue = {
        "number": 101,
        "title": "Add async support to database client",
        "body": "We need to migrate our DB calls to asyncpg.",
        "html_url": "https://github.com/test-owner/test-repo/issues/101",
        "state": "open",
        "labels": [
            {"name": "good first issue", "color": "7057ff"},
            {"name": "backend", "color": "008672"},
        ],
        "comments": 5,
        "user": {"login": "octocat"},
        "assignee": None,
        "created_at": "2026-07-01T10:00:00Z",
        "updated_at": "2026-07-02T12:00:00Z",
    }

    opp = normalize_issue(raw_issue, "test-owner", "test-repo")
    assert isinstance(opp, Opportunity)
    assert opp.type == OpportunityType.ISSUE
    assert opp.title == "Add async support to database client"
    assert opp.description == "We need to migrate our DB calls to asyncpg."
    assert opp.url == "https://github.com/test-owner/test-repo/issues/101"
    assert opp.source == "github"
    assert opp.repo_owner == "test-owner"
    assert opp.repo_name == "test-repo"
    assert opp.issue_number == 101
    assert opp.is_active is True
    assert opp.metadata_["labels"] == ["good first issue", "backend"]
    assert opp.metadata_["comments_count"] == 5
    assert opp.metadata_["author"] == "octocat"
    assert opp.metadata_["assignee"] is None
    assert opp.metadata_["role_scoping"] == "ingestion"


def test_opportunity_to_dict():
    opp = Opportunity(
        id=uuid.uuid4(),
        type=OpportunityType.ISSUE,
        title="Test Issue",
        description="Test Body",
        url="https://github.com/owner/repo/issues/1",
        source="github",
        repo_owner="owner",
        repo_name="repo",
        issue_number=1,
        is_active=True,
        metadata_={"labels": ["good first issue"], "author": "dev"},
    )
    data = opportunity_to_dict(opp, system_prompt=INGESTION_SYSTEM_PROMPT)
    assert data["title"] == "Test Issue"
    assert data["type"] == "issue"
    assert data["labels"] == ["good first issue"]
    assert data["author"] == "dev"
    assert data["ingestion_role_scoping"] == INGESTION_SYSTEM_PROMPT


@pytest.mark.asyncio
async def test_fetch_good_first_issues_success():
    mock_data = [
        {
            "number": 1,
            "title": "Issue 1",
            "body": "Body 1",
            "html_url": "https://github.com/owner/repo/issues/1",
            "state": "open",
        },
        {
            "number": 2,
            "title": "PR 1 should be filtered out",
            "body": "Body PR",
            "html_url": "https://github.com/owner/repo/pull/2",
            "state": "open",
            "pull_request": {"url": "https://api.github.com/repos/owner/repo/pulls/2"},
        },
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        assert "labels=good+first+issue" in str(request.url) or "labels=good%20first%20issue" in str(request.url)
        return httpx.Response(200, json=mock_data, headers={"X-RateLimit-Remaining": "50"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        issues = await fetch_good_first_issues("owner", "repo", client=client)
        assert len(issues) == 1
        assert issues[0]["number"] == 1
        assert issues[0]["title"] == "Issue 1"


@pytest.mark.asyncio
async def test_fetch_good_first_issues_rate_limit_backoff():
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # Return 403 rate limit with Retry-After: 1
            return httpx.Response(403, headers={"Retry-After": "1"}, text="API rate limit exceeded")
        # Second call succeeds
        return httpx.Response(200, json=[{"number": 10, "title": "After backoff", "state": "open"}])

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        t0 = time.monotonic()
        issues = await fetch_good_first_issues("owner", "repo", max_retries=3, max_backoff_seconds=5, client=client)
        elapsed = time.monotonic() - t0
        assert len(issues) == 1
        assert issues[0]["number"] == 10
        assert call_count == 2
        assert elapsed >= 0.8  # Verify sleep occurred


@pytest.mark.asyncio
async def test_ingest_github_issues(monkeypatch):
    mock_data = [
        {
            "number": 50,
            "title": "Ingest issue test",
            "body": "Body test",
            "html_url": "https://github.com/owner/repo/issues/50",
            "state": "open",
        }
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=mock_data)

    transport = httpx.MockTransport(handler)
    
    # Mock remember so we don't call real Cognee LLM / vector store in unit tests
    remember_calls = []
    async def mock_remember(data, data_type, dataset_name=None, user_id=None, session_id=None):
        remember_calls.append((data, data_type, dataset_name, user_id))
        return "mock_remember_result"

    monkeypatch.setattr("app.ingestion.github_issues.remember", mock_remember)

    async with httpx.AsyncClient(transport=transport) as client:
        opps = await ingest_github_issues("owner", "repo", client=client)
        assert len(opps) == 1
        assert opps[0].issue_number == 50
        assert len(remember_calls) == 1
        data, dtype, dsname, uid = remember_calls[0]
        assert dtype == "issue"
        assert dsname == "issue"
        assert uid is None
        assert data["title"] == "Ingest issue test"
        assert data["ingestion_role_scoping"] == INGESTION_SYSTEM_PROMPT


@pytest.mark.asyncio
async def test_verify_github_issue_open():
    from app.ingestion import verify_github_issue_open

    def handler(request: httpx.Request) -> httpx.Response:
        if "/1" in str(request.url):
            return httpx.Response(200, json={"state": "open"})
        elif "/2" in str(request.url):
            return httpx.Response(200, json={"state": "closed"})
        elif "/3" in str(request.url):
            return httpx.Response(404)
        return httpx.Response(500)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        assert await verify_github_issue_open("owner", "repo", 1, client=client) is True
        assert await verify_github_issue_open("owner", "repo", 2, client=client) is False
        assert await verify_github_issue_open("owner", "repo", 3, client=client) is False
        assert await verify_github_issue_open("owner", "repo", 4, client=client) is True

