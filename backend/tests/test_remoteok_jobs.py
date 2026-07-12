"""
Tests for RemoteOK Jobs Ingestion Module (`app.ingestion.remoteok_jobs`)
Mirrors test_arbeitnow_jobs.py structure and coverage.
All tests are offline (mocked via httpx.MockTransport).
"""

import asyncio
import pytest
import httpx

from app.db.models import Opportunity, OpportunityType
from app.ingestion.remoteok_jobs import (
    fetch_remoteok_jobs,
    normalize_job,
    opportunity_to_dict,
    ingest_remoteok_jobs,
)
from app.agents.prompts.remoteok import REMOTEOK_SYSTEM_PROMPT


def test_normalize_job():
    raw_job = {
        "position": "Senior Python Developer",
        "description": "<p>We need a senior Python developer for our distributed systems team.</p>",
        "url": "https://remoteok.com/remote-jobs/12345",
        "company": "Distributed Inc",
        "location": "Worldwide",
        "tags": ["Python", "Docker", "Kubernetes"],
        "epoch": 1782948628,
        "salary_min": 120000,
        "salary_max": 180000,
    }
    opp = normalize_job(raw_job)

    assert isinstance(opp, Opportunity)
    assert opp.type == OpportunityType.JOB
    assert opp.title == "Senior Python Developer"
    assert "senior Python developer" in opp.description
    assert opp.url == "https://remoteok.com/remote-jobs/12345"
    assert opp.source == "remoteok"
    assert opp.company == "Distributed Inc"
    assert opp.location == "Worldwide"
    assert opp.is_active is True
    assert opp.metadata_["tags"] == ["Python", "Docker", "Kubernetes"]
    assert opp.metadata_["salary_min"] == 120000
    assert opp.metadata_["salary_max"] == 180000
    assert opp.metadata_["remote"] is True
    assert opp.metadata_["created_at_timestamp"] == 1782948628
    assert opp.metadata_["created_at_iso"] is not None
    assert opp.metadata_["role_scoping"] == "remoteok"


def test_normalize_job_uses_position_field():
    raw_job = {
        "position": "Frontend Engineer",
        "description": "Build great UIs.",
        "company": "UI Co",
    }
    opp = normalize_job(raw_job)
    assert opp.title == "Frontend Engineer"
    assert opp.source == "remoteok"


def test_opportunity_to_dict():
    raw_job = {
        "position": "DevOps Engineer",
        "description": "Manage cloud infrastructure.",
        "url": "https://remoteok.com/remote-jobs/999",
        "company": "CloudBase",
        "location": "US Only",
        "tags": ["AWS", "Terraform"],
        "epoch": 1782000000,
    }
    opp = normalize_job(raw_job)
    data = opportunity_to_dict(opp)

    assert data["type"] == "job"
    assert data["title"] == "DevOps Engineer"
    assert data["description"] == "Manage cloud infrastructure."
    assert data["source"] == "remoteok"
    assert data["company"] == "CloudBase"
    assert data["location"] == "US Only"
    assert data["tags"] == ["AWS", "Terraform"]
    assert data["remote"] is True
    assert data["created_at_timestamp"] == 1782000000
    assert data["ingestion_role_scoping"] == REMOTEOK_SYSTEM_PROMPT


@pytest.mark.asyncio
async def test_fetch_remoteok_jobs_success():
    mock_data = [
        {"_metadata": "legal info"},
        {"position": "Job 1", "company": "Co A", "description": "Desc 1", "url": "https://remoteok.com/1"},
        {"position": "Job 2", "company": "Co B", "description": "Desc 2", "url": "https://remoteok.com/2"},
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "remoteok.com"
        assert request.url.path == "/api"
        assert request.headers.get("User-Agent") == "Waypoint-Career-Agent/0.1.0"
        return httpx.Response(200, json=mock_data)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        results = await fetch_remoteok_jobs(max_jobs=10, client=client)
        assert len(results) == 2
        assert results[0]["position"] == "Job 1"
        assert results[1]["position"] == "Job 2"


@pytest.mark.asyncio
async def test_fetch_remoteok_jobs_skips_metadata_element():
    mock_data = [
        {"legal": "RemoteOK Legal Notice", "sponsored": True},
        {"position": "Real Job", "company": "Co", "description": "Desc"},
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=mock_data)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        results = await fetch_remoteok_jobs(client=client)
        assert len(results) == 1
        assert results[0]["position"] == "Real Job"


@pytest.mark.asyncio
async def test_fetch_remoteok_jobs_rate_limit_backoff():
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, headers={"Retry-After": "1"})
        return httpx.Response(200, json=[{"_meta": ""}, {"position": "Recovered Job", "url": "https://rec.remoteok.com/"}])

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        start = asyncio.get_event_loop().time()
        results = await fetch_remoteok_jobs(max_jobs=5, max_retries=3, max_backoff_seconds=5, client=client)
        elapsed = asyncio.get_event_loop().time() - start
        assert len(results) == 1
        assert results[0]["position"] == "Recovered Job"
        assert attempts == 2
        assert elapsed >= 0.8


@pytest.mark.asyncio
async def test_ingest_remoteok_jobs(monkeypatch):
    mock_data = [
        {"_meta": ""},
        {"position": "Ingest Test Job", "company": "Ingest Corp", "description": "<p>Ingest test</p>", "url": "https://ingest.remoteok.com/"},
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=mock_data)

    transport = httpx.MockTransport(handler)

    remember_calls = []
    async def mock_remember(data, data_type, dataset_name=None, user_id=None, session_id=None):
        remember_calls.append((data, data_type, dataset_name, user_id))
        return "mock_remember_result"

    monkeypatch.setattr("app.ingestion.remoteok_jobs.remember", mock_remember)

    async with httpx.AsyncClient(transport=transport) as client:
        opps = await ingest_remoteok_jobs(client=client)
        assert len(opps) == 1
        assert opps[0].title == "Ingest Test Job"
        assert len(remember_calls) == 1
        data, dtype, dsname, uid = remember_calls[0]
        assert dtype == "job"
        assert dsname == "job"
        assert uid is None
        assert data["title"] == "Ingest Test Job"
        assert data["company"] == "Ingest Corp"
        assert data["ingestion_role_scoping"] == REMOTEOK_SYSTEM_PROMPT
