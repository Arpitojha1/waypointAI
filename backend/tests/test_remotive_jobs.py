"""
Tests for Remotive Jobs Ingestion Module (`app.ingestion.remotive_jobs`)
Mirrors test_arbeitnow_jobs.py structure and coverage.
All tests are offline (mocked via httpx.MockTransport).
"""

import asyncio
import pytest
import httpx

from app.db.models import Opportunity, OpportunityType
from app.ingestion.remotive_jobs import (
    fetch_remotive_jobs,
    normalize_job,
    opportunity_to_dict,
    ingest_remotive_jobs,
    _strip_html_tags,
)
from app.agents.prompts.remotive import REMOTIVE_SYSTEM_PROMPT


def test_strip_html_tags():
    assert _strip_html_tags("<p>Hello <b>world</b></p>") == "Hello world"
    assert _strip_html_tags("No tags here") == "No tags here"
    assert _strip_html_tags("<div>Line 1</div><div>Line 2</div>") == "Line 1 Line 2"
    assert _strip_html_tags("A &amp; B") == "A & B"
    assert _strip_html_tags("") == ""


def test_normalize_job():
    raw_job = {
        "title": "Full-Stack React Developer",
        "description": "<p>We are looking for a <strong>full-stack developer</strong> to build amazing products.</p>",
        "url": "https://remotive.com/job/full-stack-react-12345",
        "company_name": "StartupCo",
        "candidate_required_location": "Worldwide",
        "tags": ["React", "Node.js", "TypeScript"],
        "publication_date": "2026-07-01T10:00:00Z",
        "category": "Software Development",
        "salary": "$100k - $150k",
    }
    opp = normalize_job(raw_job)

    assert isinstance(opp, Opportunity)
    assert opp.type == OpportunityType.JOB
    assert opp.title == "Full-Stack React Developer"
    assert "full-stack developer" in opp.description
    assert "<p>" not in opp.description
    assert "<strong>" not in opp.description
    assert opp.url == "https://remotive.com/job/full-stack-react-12345"
    assert opp.source == "remotive"
    assert opp.company == "StartupCo"
    assert opp.location == "Worldwide"
    assert opp.is_active is True
    assert opp.metadata_["tags"] == ["React", "Node.js", "TypeScript"]
    assert opp.metadata_["category"] == "Software Development"
    assert opp.metadata_["salary"] == "$100k - $150k"
    assert opp.metadata_["remote"] is True
    assert opp.metadata_["created_at_iso"] is not None
    assert opp.metadata_["role_scoping"] == "remotive"


def test_opportunity_to_dict():
    raw_job = {
        "title": "Backend Python Engineer",
        "description": "Build scalable APIs.",
        "url": "https://remotive.com/job/backend-999",
        "company_name": "API Corp",
        "candidate_required_location": "EU Only",
        "tags": ["Python", "FastAPI"],
        "publication_date": "2026-06-15T08:00:00Z",
        "category": "Backend",
    }
    opp = normalize_job(raw_job)
    data = opportunity_to_dict(opp)

    assert data["type"] == "job"
    assert data["title"] == "Backend Python Engineer"
    assert data["description"] == "Build scalable APIs."
    assert data["source"] == "remotive"
    assert data["company"] == "API Corp"
    assert data["location"] == "EU Only"
    assert data["tags"] == ["Python", "FastAPI"]
    assert data["category"] == "Backend"
    assert data["remote"] is True
    assert data["ingestion_role_scoping"] == REMOTIVE_SYSTEM_PROMPT


@pytest.mark.asyncio
async def test_fetch_remotive_jobs_success():
    mock_data = {
        "jobs": [
            {"title": "Job 1", "company_name": "Co A", "description": "Desc 1", "url": "https://remotive.com/1"},
            {"title": "Job 2", "company_name": "Co B", "description": "Desc 2", "url": "https://remotive.com/2"},
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "remotive.com"
        assert request.url.path == "/api/remote-jobs"
        assert request.headers.get("User-Agent") == "Waypoint-Career-Agent/0.1.0"
        return httpx.Response(200, json=mock_data)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        results = await fetch_remotive_jobs(max_jobs=10, client=client)
        assert len(results) == 2
        assert results[0]["title"] == "Job 1"
        assert results[1]["title"] == "Job 2"


@pytest.mark.asyncio
async def test_fetch_remotive_jobs_with_search():
    mock_data = {"jobs": [{"title": "Python Dev", "company_name": "Co"}]}

    def handler(request: httpx.Request) -> httpx.Response:
        assert "search=python" in str(request.url)
        return httpx.Response(200, json=mock_data)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        results = await fetch_remotive_jobs(search="python", client=client)
        assert len(results) == 1


@pytest.mark.asyncio
async def test_fetch_remotive_jobs_rate_limit_backoff():
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, headers={"Retry-After": "1"})
        return httpx.Response(200, json={"jobs": [{"title": "Recovered Job", "url": "https://rec.remotive.com/"}]})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        start = asyncio.get_event_loop().time()
        results = await fetch_remotive_jobs(max_jobs=5, max_retries=3, max_backoff_seconds=5, client=client)
        elapsed = asyncio.get_event_loop().time() - start
        assert len(results) == 1
        assert results[0]["title"] == "Recovered Job"
        assert attempts == 2
        assert elapsed >= 0.8


@pytest.mark.asyncio
async def test_ingest_remotive_jobs(monkeypatch):
    mock_data = {
        "jobs": [
            {"title": "Ingest Test Job", "company_name": "Ingest Corp", "description": "<p>Ingest test</p>", "url": "https://ingest.remotive.com/"}
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=mock_data)

    transport = httpx.MockTransport(handler)

    remember_calls = []
    async def mock_remember(data, data_type, dataset_name=None, user_id=None, session_id=None):
        remember_calls.append((data, data_type, dataset_name, user_id))
        return "mock_remember_result"

    monkeypatch.setattr("app.ingestion.remotive_jobs.remember", mock_remember)

    async with httpx.AsyncClient(transport=transport) as client:
        opps = await ingest_remotive_jobs(client=client)
        assert len(opps) == 1
        assert opps[0].title == "Ingest Test Job"
        assert len(remember_calls) == 1
        data, dtype, dsname, uid = remember_calls[0]
        assert dtype == "job"
        assert dsname == "job"
        assert uid is None
        assert data["title"] == "Ingest Test Job"
        assert data["company"] == "Ingest Corp"
        assert data["ingestion_role_scoping"] == REMOTIVE_SYSTEM_PROMPT
