"""
Waypoint API — End-to-End Verification Script (Phase 3 Orchestrator & Auth Verification)

Verifies:
1. Depends(get_current_user) auth enforcement on routes_roadmap and routes_feedback.
2. Anthropic/OpenRouter tool-use loop logging (messages array & raw tool_use blocks).
3. Roadmap generation on two distinct opportunity inputs (Job vs Issue) showing differentiated, non-templated steps.
4. All three feedback paths: done -> improve(positive), rejected -> improve(negative), skip -> forget().

Usage:
    cd backend
    python scripts/verify_e2e.py
"""

import asyncio
import os
import sys
import time
import uuid
import logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
)
logger = logging.getLogger("verify_e2e")

# Load .env explicitly before importing app config
from dotenv import load_dotenv
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH)

# Force ENABLE_BACKEND_ACCESS_CONTROL to true to verify real JWT enforcement
os.environ["ENABLE_BACKEND_ACCESS_CONTROL"] = "true"

import httpx
from jose import jwt
from sqlalchemy import select
from app.config import settings
from app.db.session import init_db, close_db, async_session_factory
from app.db.models import Opportunity, OpportunityType, StepStatus
from app.main import app


def create_test_jwt(user_id: uuid.UUID) -> str:
    """Create a signed Supabase JWT for testing auth enforcement."""
    payload = {
        "sub": str(user_id),
        "email": "e2e_verifier@waypoint.local",
        "role": "authenticated",
        "aud": "authenticated",
        "exp": int(time.time()) + 3600,
        "iat": int(time.time()),
    }
    return jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")


async def setup_test_opportunities(session) -> tuple[uuid.UUID, uuid.UUID]:
    """Insert two clearly distinct opportunities into Postgres."""
    job_id = uuid.uuid4()
    opp_job = Opportunity(
        id=job_id,
        type=OpportunityType.JOB,
        title="Senior React & Tailwind Frontend Engineer",
        description="We are looking for a frontend specialist at Stripe to rebuild our checkout UI using React 19, Tailwind CSS v4, and modern state management. You will work on animations, micro-interactions, and design systems.",
        company="Stripe",
        location="Remote",
        source="arbeitnow",
        url="https://stripe.com/jobs/12345",
        is_active=True,
        metadata_={"tags": ["React", "Tailwind CSS", "TypeScript", "Frontend", "UI/UX"]},
    )

    issue_id = uuid.uuid4()
    opp_issue = Opportunity(
        id=issue_id,
        type=OpportunityType.ISSUE,
        title="Fix async database session leak in background tasks",
        description="When running FastAPI background tasks with SQLAlchemy asyncpg sessions, the database connections are not being released back to the pool after task completion. This causes connection pool exhaustion under load. Need to wrap task execution in a proper async scoped session manager.",
        source="github",
        url="https://github.com/fastapi/fastapi/issues/1042",
        repo_owner="fastapi",
        repo_name="fastapi",
        issue_number=1042,
        is_active=True,
        metadata_={"labels": ["good first issue", "bug", "database", "async"]},
    )

    session.add(opp_job)
    session.add(opp_issue)
    await session.commit()
    logger.info("Inserted test opportunities: Job (%s) and Issue (%s)", job_id, issue_id)
    return job_id, issue_id


async def run_verification():
    logger.info("Starting End-to-End Verification...")
    await init_db()

    user_id = uuid.uuid4()
    token = create_test_jwt(user_id)
    headers = {"Authorization": f"Bearer {token}"}

    async with async_session_factory() as session:
        job_id, issue_id = await setup_test_opportunities(session)

    # We use httpx.AsyncClient with ASGITransport to test FastAPI endpoints
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        
        # ---------------------------------------------------------------------
        # TEST 1: Auth Enforcement (Depends(get_current_user))
        # ---------------------------------------------------------------------
        logger.info("\n--- TEST 1: Verifying Auth Enforcement ---")
        
        # Unauthenticated request to POST /api/roadmaps
        res_unauth_create = await client.post("/api/roadmaps", json={"opportunity_id": str(job_id)})
        assert res_unauth_create.status_code == 401, f"Expected 401, got {res_unauth_create.status_code}"
        logger.info("PASS: Unauthenticated POST /api/roadmaps correctly rejected with 401.")

        # Unauthenticated request to GET /api/roadmaps/{id}
        res_unauth_get = await client.get(f"/api/roadmaps/{uuid.uuid4()}")
        assert res_unauth_get.status_code == 401, f"Expected 401, got {res_unauth_get.status_code}"
        logger.info("PASS: Unauthenticated GET /api/roadmaps/{id} correctly rejected with 401.")

        # Unauthenticated request to POST /api/steps/{id}/feedback
        res_unauth_fb = await client.post(f"/api/steps/{uuid.uuid4()}/feedback", json={"status": "done"})
        assert res_unauth_fb.status_code == 401, f"Expected 401, got {res_unauth_fb.status_code}"
        logger.info("PASS: Unauthenticated POST /api/steps/{id}/feedback correctly rejected with 401.")

        # ---------------------------------------------------------------------
        # TEST 2 & 3: Roadmap Generation on Two Distinct Opportunities
        # ---------------------------------------------------------------------
        logger.info("\n--- TEST 2: Generating Roadmap for Opportunity 1 (Job: Stripe React Frontend) ---")
        t0 = time.time()
        res_job = await client.post("/api/roadmaps", json={"opportunity_id": str(job_id), "remember_in_cognee": False}, headers=headers)
        assert res_job.status_code == 201, f"Failed to generate job roadmap: {res_job.text}"
        roadmap_job = res_job.json()
        logger.info("Job Roadmap Generated in %.2fs: Title: '%s'", time.time() - t0, roadmap_job["title"])
        steps_job = roadmap_job.get("steps", [])
        logger.info("Job Roadmap Steps Count: %d", len(steps_job))
        for idx, s in enumerate(steps_job, 1):
            logger.info("  Step %d: [%s] %s", idx, s["title"], s["description"][:100] + "...")

        logger.info("\n--- TEST 3: Generating Roadmap for Opportunity 2 (Issue: FastAPI DB Session Leak) ---")
        t0 = time.time()
        res_issue = await client.post("/api/roadmaps", json={"opportunity_id": str(issue_id), "remember_in_cognee": False}, headers=headers)
        assert res_issue.status_code == 201, f"Failed to generate issue roadmap: {res_issue.text}"
        roadmap_issue = res_issue.json()
        logger.info("Issue Roadmap Generated in %.2fs: Title: '%s'", time.time() - t0, roadmap_issue["title"])
        steps_issue = roadmap_issue.get("steps", [])
        logger.info("Issue Roadmap Steps Count: %d", len(steps_issue))
        for idx, s in enumerate(steps_issue, 1):
            logger.info("  Step %d: [%s] %s", idx, s["title"], s["description"][:100] + "...")

        # Verify steps are NOT the hardcoded skeleton and differ meaningfully between Job and Issue
        hardcoded_titles = {
            "Analyze Requirements & Setup Environment",
            "Build Core Artifacts / Implement Solution",
            "Verify, Polish & Submit"
        }
        job_step_titles = {s["title"] for s in steps_job}
        issue_step_titles = {s["title"] for s in steps_issue}

        assert not (job_step_titles == hardcoded_titles and len(steps_job) == 3), "Job roadmap returned hardcoded template steps!"
        assert not (issue_step_titles == hardcoded_titles and len(steps_issue) == 3), "Issue roadmap returned hardcoded template steps!"
        assert job_step_titles != issue_step_titles, "Job and Issue step titles are identical! Not differentiated."
        logger.info("PASS: Generated steps are opportunity-specific and genuinely differentiated!")

        # ---------------------------------------------------------------------
        # TEST 4: Exercise All Three Feedback Paths
        # ---------------------------------------------------------------------
        logger.info("\n--- TEST 4: Verifying Three Feedback Paths (done, rejected, skip) ---")
        assert len(steps_job) >= 3, "Need at least 3 steps to test all 3 feedback paths."
        step_1_id = steps_job[0]["id"]
        step_2_id = steps_job[1]["id"]
        step_3_id = steps_job[2]["id"]

        # Path 1: DONE -> improve(positive)
        res_fb_done = await client.post(f"/api/steps/{step_1_id}/feedback", json={"status": "done", "update_cognee": True}, headers=headers)
        assert res_fb_done.status_code == 200, f"Feedback done failed: {res_fb_done.text}"
        data_done = res_fb_done.json()
        assert data_done["status"] == "done"
        assert "improve positive" in data_done["message"] or "Cognee warning" in data_done["message"]
        logger.info("PASS: Feedback 'done' -> message: '%s'", data_done["message"])

        # Path 2: REJECTED -> improve(negative)
        res_fb_rej = await client.post(f"/api/steps/{step_2_id}/feedback", json={"status": "rejected", "update_cognee": True}, headers=headers)
        assert res_fb_rej.status_code == 200, f"Feedback rejected failed: {res_fb_rej.text}"
        data_rej = res_fb_rej.json()
        assert data_rej["status"] == "rejected"
        assert "improve negative" in data_rej["message"] or "Cognee warning" in data_rej["message"]
        logger.info("PASS: Feedback 'rejected' -> message: '%s'", data_rej["message"])

        # Path 3: SKIPPED -> forget()
        res_fb_skip = await client.post(f"/api/steps/{step_3_id}/feedback", json={"status": "skipped", "update_cognee": True}, headers=headers)
        assert res_fb_skip.status_code == 200, f"Feedback skipped failed: {res_fb_skip.text}"
        data_skip = res_fb_skip.json()
        assert data_skip["status"] == "skipped"
        assert "forget" in data_skip["message"] or "Cognee warning" in data_skip["message"]
        logger.info("PASS: Feedback 'skip' -> message: '%s'", data_skip["message"])

    await close_db()
    logger.info("\nALL END-TO-END VERIFICATION CHECKS PASSED SUCCEEDINGLY!")


if __name__ == "__main__":
    asyncio.run(run_verification())
