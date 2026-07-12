"""
Unit tests for GitHub Good First Issues Ingestion (Phase 2+).
Uses httpx.MockTransport to test API fetching, rate limit backoff handling,
normalization, global search, and deduplication without requiring live network.
"""

import asyncio
import time
import uuid
import pytest
import httpx

from app.db.models import Opportunity, OpportunityType
from app.ingestion.github_issues import (
    fetch_good_first_issues,
    fetch_good_first_issues_global,
    normalize_issue,
    opportunity_to_dict,
    ingest_github_issues,
    FEATURED_REPOSITORIES,
    COMMUNITY_LABELS,
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
    assert opp.source == "github_issue"
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
        source="github_issue",
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
        q = str(request.url)
        # Verify OR label query is used
        assert "label=" in q or "label%3A" in q
        return httpx.Response(200, json={"items": mock_data}, headers={"X-RateLimit-Remaining": "50"})

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
        return httpx.Response(200, json={"items": [{"number": 10, "title": "After backoff", "state": "open"}]})

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
            "repository_url": "https://api.github.com/repos/owner/repo",
        }
    ]

    call_count = 0
    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(200, json={"items": mock_data})

    transport = httpx.MockTransport(handler)
    
    # Mock remember so we don't call real Cognee LLM / vector store in unit tests
    remember_calls = []
    async def mock_remember(data, data_type, dataset_name=None, user_id=None, session_id=None):
        remember_calls.append((data, data_type, dataset_name, user_id))
        return "mock_remember_result"

    monkeypatch.setattr("app.ingestion.github_issues.remember", mock_remember)

    async with httpx.AsyncClient(transport=transport) as client:
        # With owner/repo specified: only featured-repo search, no global
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


@pytest.mark.asyncio
async def test_ingest_github_issues_featured_repos_and_global(monkeypatch):
    mock_data = [
        {
            "number": 1,
            "title": "Issue from search",
            "body": "Body test",
            "html_url": "https://github.com/test-owner/test-repo/issues/1",
            "state": "open",
            "repository_url": "https://api.github.com/repos/test-owner/test-repo",
        }
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"items": mock_data})

    transport = httpx.MockTransport(handler)

    remember_calls = []
    async def mock_remember(data, data_type, dataset_name=None, user_id=None, session_id=None):
        remember_calls.append((data, data_type, dataset_name, user_id))
        return "mock_remember_result"

    monkeypatch.setattr("app.ingestion.github_issues.remember", mock_remember)

    async with httpx.AsyncClient(transport=transport) as client:
        opps = await ingest_github_issues(client=client)
        # 1 from global search + 10 from featured repos = 11 unique issues
        # (all have different dedup keys since normalize_issue uses the passed owner/repo)
        assert len(opps) == 11
        assert len(remember_calls) == 11
        for data, dtype, dsname, uid in remember_calls:
            assert dtype == "issue"
            assert dsname == "issue"
            assert data["title"] == "Issue from search"


@pytest.mark.asyncio
async def test_fetch_good_first_issues_global_success():
    mock_data = [
        {
            "number": 100,
            "title": "Global Issue 1",
            "body": "Global body 1",
            "html_url": "https://github.com/someone/somewhere/issues/100",
            "state": "open",
            "repository_url": "https://api.github.com/repos/someone/somewhere",
        },
        {
            "number": 200,
            "title": "Global Issue 2",
            "body": "Global body 2",
            "html_url": "https://github.com/other/project/issues/200",
            "state": "open",
            "repository_url": "https://api.github.com/repos/other/project",
        },
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        q = str(request.url)
        # Verify no repo: qualifier in global search
        assert "repo%3A" not in q and "repo:" not in q
        assert "is%3Aopen" in q or "is:open" in q
        return httpx.Response(200, json={"items": mock_data, "total_count": 2})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        issues = await fetch_good_first_issues_global(max_issues=10, client=client)
        assert len(issues) == 2
        assert issues[0]["title"] == "Global Issue 1"


@pytest.mark.asyncio
async def test_fetch_good_first_issues_global_with_language():
    mock_data = [{"number": 1, "title": "Python Issue", "state": "open", "html_url": "https://github.com/a/b/issues/1"}]

    def handler(request: httpx.Request) -> httpx.Response:
        q = str(request.url)
        assert "language%3Apython" in q or "language:python" in q
        return httpx.Response(200, json={"items": mock_data})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        issues = await fetch_good_first_issues_global(language="python", max_issues=5, client=client)
        assert len(issues) == 1


@pytest.mark.asyncio
async def test_ingest_deduplicates_global_and_featured(monkeypatch):
    """Global search and featured repo return the same issue — dedup should keep only one."""
    shared_issue = {
        "number": 42,
        "title": "Duplicate Issue",
        "body": "Body",
        "html_url": "https://github.com/pytorch/pytorch/issues/42",
        "state": "open",
        "repository_url": "https://api.github.com/repos/pytorch/pytorch",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"items": [shared_issue]})

    transport = httpx.MockTransport(handler)

    remember_calls = []
    async def mock_remember(data, data_type, dataset_name=None, user_id=None, session_id=None):
        remember_calls.append((data, data_type, dataset_name, user_id))

    monkeypatch.setattr("app.ingestion.github_issues.remember", mock_remember)

    async with httpx.AsyncClient(transport=transport) as client:
        opps = await ingest_github_issues(client=client)
        # Global finds pytorch/pytorch#42, featured repos also find pytorch/pytorch#42
        # Dedup should keep only one
        pytorch_issues = [o for o in opps if o.repo_owner == "pytorch" and o.issue_number == 42]
        assert len(pytorch_issues) == 1
        # Verify Cognee remember was called exactly once for the deduplicated issue
        pytorch_remember_calls = [
            (data, dtype, dsname)
            for data, dtype, dsname, _uid in remember_calls
            if data.get("repo_owner") == "pytorch" and data.get("issue_number") == 42
        ]
        assert len(pytorch_remember_calls) == 1
        data, dtype, dsname = pytorch_remember_calls[0]
        assert dtype == "issue"
        assert dsname == "issue"
        assert data["title"] == "Duplicate Issue"
        assert data["repo_owner"] == "pytorch"
        assert data["repo_name"] == "pytorch"
        assert data["issue_number"] == 42
        assert data["is_active"] is True

