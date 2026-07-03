"""
Tests for Arbeitnow Jobs Ingestion Module (`app.ingestion.arbeitnow_jobs`)
Mirrors test_devpost_hackathons.py structure and coverage.
All tests are offline (mocked via httpx.MockTransport).
"""

import asyncio
from datetime import datetime, timezone
import pytest
import httpx

from app.db.models import Opportunity, OpportunityType
from app.ingestion.arbeitnow_jobs import (
    fetch_arbeitnow_jobs,
    normalize_job,
    opportunity_to_dict,
    ingest_arbeitnow_jobs,
)
from app.agents.prompts.arbeitnow import ARBEITNOW_SYSTEM_PROMPT


def test_normalize_job():
    raw_job = {
        "slug": "senior-ai-engineer-berlin-12345",
        "company_name": "Waypoint AI GmbH",
        "title": "Senior AI Engineer (m/w/d)",
        "description": "<p>We are looking for a Senior AI Engineer to build agentic coding systems.</p>",
        "remote": True,
        "url": "https://www.arbeitnow.com/jobs/companies/waypoint-ai/senior-ai-engineer",
        "tags": ["Python", "FastAPI", "AI/ML", "LLMs"],
        "job_types": ["full-time"],
        "location": "Berlin",
        "created_at": 1782948628,
    }
    opp = normalize_job(raw_job)

    assert isinstance(opp, Opportunity)
    assert opp.type == OpportunityType.JOB
    assert opp.title == "Senior AI Engineer (m/w/d)"
    assert "<p>We are looking for a Senior AI Engineer" in opp.description
    assert opp.url == "https://www.arbeitnow.com/jobs/companies/waypoint-ai/senior-ai-engineer"
    assert opp.source == "arbeitnow"
    assert opp.company == "Waypoint AI GmbH"
    assert opp.location == "Berlin"
    assert opp.is_active is True
    assert opp.metadata_["slug"] == "senior-ai-engineer-berlin-12345"
    assert opp.metadata_["remote"] is True
    assert opp.metadata_["tags"] == ["Python", "FastAPI", "AI/ML", "LLMs"]
    assert opp.metadata_["job_types"] == ["full-time"]
    assert opp.metadata_["created_at_timestamp"] == 1782948628
    assert opp.metadata_["created_at_iso"] is not None
    assert opp.metadata_["role_scoping"] == "arbeitnow"


def test_opportunity_to_dict():
    raw_job = {
        "slug": "backend-developer-munich-54321",
        "company_name": "Tech Corp",
        "title": "Backend Developer",
        "description": "Develop scalable Python backends.",
        "remote": False,
        "url": "https://www.arbeitnow.com/jobs/companies/tech-corp/backend-developer",
        "tags": ["Python", "PostgreSQL"],
        "job_types": ["contract"],
        "location": "Munich",
        "created_at": 1782000000,
    }
    opp = normalize_job(raw_job)
    data = opportunity_to_dict(opp)

    assert data["type"] == "job"
    assert data["title"] == "Backend Developer"
    assert data["description"] == "Develop scalable Python backends."
    assert data["url"] == "https://www.arbeitnow.com/jobs/companies/tech-corp/backend-developer"
    assert data["source"] == "arbeitnow"
    assert data["company"] == "Tech Corp"
    assert data["location"] == "Munich"
    assert data["slug"] == "backend-developer-munich-54321"
    assert data["remote"] is False
    assert data["tags"] == ["Python", "PostgreSQL"]
    assert data["job_types"] == ["contract"]
    assert data["created_at_timestamp"] == 1782000000
    assert data["ingestion_role_scoping"] == ARBEITNOW_SYSTEM_PROMPT


@pytest.mark.asyncio
async def test_fetch_arbeitnow_jobs_success():
    mock_response_data = {
        "data": [
            {
                "slug": "job-1",
                "company_name": "Company A",
                "title": "Job 1",
                "description": "Desc 1",
                "url": "https://arbeitnow.com/job-1",
            },
            {
                "slug": "job-2",
                "company_name": "Company B",
                "title": "Job 2",
                "description": "Desc 2",
                "url": "https://arbeitnow.com/job-2",
            },
        ],
        "links": {
            "next": None,
        },
        "meta": {
            "current_page": 1,
            "total": 2,
        },
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "www.arbeitnow.com"
        assert request.url.path == "/api/job-board-api"
        assert request.headers.get("User-Agent") == "Waypoint-Career-Agent/0.1.0"
        return httpx.Response(200, json=mock_response_data)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        results = await fetch_arbeitnow_jobs(max_jobs=10, client=client)
        assert len(results) == 2
        assert results[0]["title"] == "Job 1"
        assert results[1]["title"] == "Job 2"


@pytest.mark.asyncio
async def test_fetch_arbeitnow_jobs_rate_limit_backoff():
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, headers={"Retry-After": "1"})
        return httpx.Response(
            200,
            json={"data": [{"title": "Recovered Job", "url": "https://rec.arbeitnow.com/"}], "links": {"next": None}},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        start = asyncio.get_event_loop().time()
        results = await fetch_arbeitnow_jobs(max_jobs=5, max_retries=3, max_backoff_seconds=5, client=client)
        elapsed = asyncio.get_event_loop().time() - start

        assert len(results) == 1
        assert results[0]["title"] == "Recovered Job"
        assert attempts == 2
        assert elapsed >= 0.8  # Assert sleep was called


@pytest.mark.asyncio
async def test_ingest_arbeitnow_jobs(monkeypatch):
    mock_data = {
        "data": [
            {
                "slug": "ingest-job",
                "company_name": "Ingest Corp",
                "title": "Ingest Test Job",
                "description": "<p>Ingest test</p>",
                "url": "https://ingest.arbeitnow.com/",
            }
        ],
        "links": {"next": None},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=mock_data)

    transport = httpx.MockTransport(handler)

    remember_calls = []
    async def mock_remember(data, data_type, dataset_name=None, user_id=None, session_id=None):
        remember_calls.append((data, data_type, dataset_name, user_id))
        return "mock_remember_result"

    monkeypatch.setattr("app.ingestion.arbeitnow_jobs.remember", mock_remember)

    async with httpx.AsyncClient(transport=transport) as client:
        opps = await ingest_arbeitnow_jobs(client=client)
        assert len(opps) == 1
        assert opps[0].title == "Ingest Test Job"
        assert len(remember_calls) == 1
        data, dtype, dsname, uid = remember_calls[0]
        assert dtype == "job"
        assert dsname == "job"
        assert uid is None
        assert data["title"] == "Ingest Test Job"
        assert data["company"] == "Ingest Corp"
        assert data["ingestion_role_scoping"] == ARBEITNOW_SYSTEM_PROMPT
