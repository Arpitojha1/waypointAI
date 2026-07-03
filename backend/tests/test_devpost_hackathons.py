"""
Tests for Devpost Hackathons Ingestion Module (`app.ingestion.devpost_hackathons`)
Mirrors test_github_issues.py structure and coverage.
All tests are offline (mocked via httpx.MockTransport).
"""

import asyncio
from datetime import datetime, timezone
import pytest
import httpx

from app.db.models import Opportunity, OpportunityType
from app.ingestion.devpost_hackathons import (
    fetch_devpost_hackathons,
    normalize_hackathon,
    opportunity_to_dict,
    ingest_devpost_hackathons,
)
from app.agents.prompts.devpost import DEVPOST_SYSTEM_PROMPT


def test_normalize_hackathon():
    raw_hackathon = {
        "id": 12345,
        "title": "Global AI Hackathon 2026",
        "url": "https://global-ai.devpost.com/",
        "submission_period_dates": "May 19 - Aug 17, 2026",
        "time_left_to_submission": "about 2 months left",
        "open_state": "open",
        "themes": [{"id": 1, "name": "AI/ML"}, {"id": 2, "name": "Agentic Coding"}],
        "prize_amount": "$50,000 in prizes",
        "registrations_count": 450,
        "organization_name": "Waypoint AI",
        "submission_deadline": "2026-07-31T23:59:00Z",
    }
    opp = normalize_hackathon(raw_hackathon)

    assert isinstance(opp, Opportunity)
    assert opp.type == OpportunityType.HACKATHON
    assert opp.title == "Global AI Hackathon 2026"
    assert "Organized by Waypoint AI." in opp.description
    assert opp.url == "https://global-ai.devpost.com/"
    assert opp.source == "devpost"
    assert opp.is_active is True
    assert opp.deadline is not None
    assert opp.deadline.year == 2026
    assert opp.deadline.month == 7
    assert opp.deadline.day == 31
    assert opp.metadata_["themes"] == ["AI/ML", "Agentic Coding"]
    assert opp.metadata_["prize_amount"] == "$50,000 in prizes"
    assert opp.metadata_["registrations_count"] == 450
    assert opp.metadata_["organization_name"] == "Waypoint AI"
    assert opp.metadata_["role_scoping"] == "devpost"


def test_opportunity_to_dict():
    raw_hackathon = {
        "id": 54321,
        "title": "Dict test hackathon",
        "url": "https://dict-test.devpost.com/",
        "submission_period_dates": "Aug 1 - Aug 15, 2026",
        "submission_deadline": "2026-08-15T12:00:00Z",
        "open_state": "open",
        "themes": [{"id": 3, "name": "Web3"}],
        "organization_name": "Dict Org",
    }
    opp = normalize_hackathon(raw_hackathon)
    data = opportunity_to_dict(opp)

    assert data["type"] == "hackathon"
    assert data["title"] == "Dict test hackathon"
    assert "Organized by Dict Org." in data["description"]
    assert data["url"] == "https://dict-test.devpost.com/"
    assert data["source"] == "devpost"
    assert data["themes"] == ["Web3"]
    assert "2026-08-15" in data["deadline"]
    assert data["ingestion_role_scoping"] == DEVPOST_SYSTEM_PROMPT


@pytest.mark.asyncio
async def test_fetch_devpost_hackathons_success():
    mock_response_data = {
        "hackathons": [
            {
                "id": 1,
                "title": "Hackathon 1",
                "organization_name": "Org 1",
                "submission_period_dates": "Jan 1 - Feb 1, 2026",
                "url": "https://hack1.devpost.com/",
                "open_state": "open",
            },
            {
                "id": 2,
                "title": "Hackathon 2",
                "organization_name": "Org 2",
                "submission_period_dates": "Feb 1 - Mar 1, 2026",
                "url": "https://hack2.devpost.com/",
                "open_state": "upcoming",
            },
        ],
        "meta": {
            "total_count": 2,
            "per_page": 50,
        },
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "devpost.com"
        assert request.url.path == "/api/hackathons"
        assert request.headers.get("User-Agent") == "Waypoint-Career-Agent/0.1.0"
        return httpx.Response(200, json=mock_response_data)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        results = await fetch_devpost_hackathons(max_hackathons=10, client=client)
        assert len(results) == 2
        assert results[0]["title"] == "Hackathon 1"
        assert results[1]["title"] == "Hackathon 2"


@pytest.mark.asyncio
async def test_fetch_devpost_hackathons_rate_limit_backoff():
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, headers={"Retry-After": "1"})
        return httpx.Response(
            200,
            json={"hackathons": [{"title": "Recovered Hackathon", "url": "https://rec.devpost.com/"}]},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        start = asyncio.get_event_loop().time()
        results = await fetch_devpost_hackathons(max_hackathons=5, max_retries=3, max_backoff_seconds=5, client=client)
        elapsed = asyncio.get_event_loop().time() - start

        assert len(results) == 1
        assert results[0]["title"] == "Recovered Hackathon"
        assert attempts == 2
        assert elapsed >= 0.8  # Assert sleep was called


@pytest.mark.asyncio
async def test_ingest_devpost_hackathons(monkeypatch):
    mock_data = {
        "hackathons": [
            {
                "id": 100,
                "title": "Ingest test hackathon",
                "organization_name": "Ingest Org",
                "submission_period_dates": "Mar 1 - Apr 1, 2026",
                "url": "https://ingest.devpost.com/",
                "open_state": "open",
            }
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=mock_data)

    transport = httpx.MockTransport(handler)

    remember_calls = []
    async def mock_remember(data, data_type, dataset_name=None, user_id=None, session_id=None):
        remember_calls.append((data, data_type, dataset_name, user_id))
        return "mock_remember_result"

    monkeypatch.setattr("app.ingestion.devpost_hackathons.remember", mock_remember)

    async with httpx.AsyncClient(transport=transport) as client:
        opps = await ingest_devpost_hackathons(client=client)
        assert len(opps) == 1
        assert opps[0].title == "Ingest test hackathon"
        assert len(remember_calls) == 1
        data, dtype, dsname, uid = remember_calls[0]
        assert dtype == "hackathon"
        assert dsname == "hackathon"
        assert uid is None
        assert data["title"] == "Ingest test hackathon"
        assert data["ingestion_role_scoping"] == DEVPOST_SYSTEM_PROMPT
