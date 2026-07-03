"""
Phase 6 End-to-End Validation Script
1. Generate a roadmap for a GitHub issue opportunity.
2. Mark 2 steps "done" via POST /api/steps/{id}/feedback (status: "done").
3. Reject 1 step (status: "rejected").
4. Regenerate a roadmap for a similar-type issue opportunity.
5. Inspect recall results and memify triggers.
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
logger = logging.getLogger("test_phase6")

from dotenv import load_dotenv
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH)

os.environ["ENABLE_BACKEND_ACCESS_CONTROL"] = "true"

import httpx
from jose import jwt
from app.config import settings
from app.db.session import init_db, close_db, async_session_factory
from app.db.models import Opportunity, OpportunityType, StepStatus, UserProfile
from app.main import app

def create_test_jwt(user_id: uuid.UUID) -> str:
    payload = {
        "sub": str(user_id),
        "email": "phase6_tester@waypoint.local",
        "role": "authenticated",
        "aud": "authenticated",
        "exp": int(time.time()) + 3600,
        "iat": int(time.time()),
    }
    return jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")

async def setup_test_data(session, user_id: uuid.UUID):
    # Create profile
    profile = UserProfile(
        id=uuid.uuid4(),
        user_id=user_id,
        display_name="Phase 6 Tester",
        skills=["Python", "FastAPI", "SQLAlchemy", "AsyncIO"],
        experience_summary="Backend developer working on Python APIs."
    )
    session.add(profile)

    issue1_id = uuid.uuid4()
    opp_issue1 = Opportunity(
        id=issue1_id,
        type=OpportunityType.ISSUE,
        title="Add retry mechanism to database connection pool",
        description="When connecting to PostgreSQL database under heavy load, connection timeouts occur. We need to add an exponential backoff retry logic to the database connection pool initialization in our SQLAlchemy session setup.",
        source="github",
        url="https://github.com/test/repo1/issues/101",
        repo_owner="test",
        repo_name="repo1",
        issue_number=101,
        is_active=True,
        metadata_={"labels": ["good first issue", "database", "python"]},
    )

    issue2_id = uuid.uuid4()
    opp_issue2 = Opportunity(
        id=issue2_id,
        type=OpportunityType.ISSUE,
        title="Add exponential backoff retry to Redis cache client",
        description="When connecting to Redis cache server under high latency, connection failures happen. Need to implement an exponential backoff retry mechanism in the Redis async client initialization.",
        source="github",
        url="https://github.com/test/repo2/issues/202",
        repo_owner="test",
        repo_name="repo2",
        issue_number=202,
        is_active=True,
        metadata_={"labels": ["good first issue", "cache", "python"]},
    )

    session.add(opp_issue1)
    session.add(opp_issue2)
    await session.commit()
    logger.info("Inserted test opportunities: Issue 1 (%s) and Issue 2 (%s)", issue1_id, issue2_id)
    return issue1_id, issue2_id

async def run_test():
    logger.info("Starting Phase 6 Live Test...")
    await init_db()

    user_id = uuid.uuid4()
    token = create_test_jwt(user_id)
    headers = {"Authorization": f"Bearer {token}"}

    async with async_session_factory() as session:
        issue1_id, issue2_id = await setup_test_data(session, user_id)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver", timeout=300.0) as client:
        logger.info("\n=======================================================")
        logger.info("STEP 1: Generate roadmap for GitHub issue opportunity 1")
        logger.info("=======================================================")
        t0 = time.time()
        res1 = await client.post("/api/roadmaps", json={"opportunity_id": str(issue1_id), "remember_in_cognee": True, "force_regenerate": True}, headers=headers)
        logger.info("POST /api/roadmaps (Issue 1) status: %d (time: %.2fs)", res1.status_code, time.time() - t0)
        if res1.status_code not in (200, 201):
            logger.error("Failed to generate Issue 1 roadmap: %s", res1.text)
            return
        roadmap1 = res1.json()
        logger.info("Roadmap 1 ID: %s | Title: '%s'", roadmap1["id"], roadmap1["title"])
        steps1 = roadmap1.get("steps", [])
        logger.info("Generated %d steps for Roadmap 1:", len(steps1))
        for idx, s in enumerate(steps1, 1):
            logger.info("  Step %d [%s] id=%s: status=%s | is_memified=%s | %s", idx, s["title"], s["id"], s["status"], s["is_memified"], s["description"][:100])

        if len(steps1) < 3:
            logger.error("Expected at least 3 steps, got %d. Aborting test.", len(steps1))
            return

        logger.info("\n=======================================================")
        logger.info("STEP 2: Mark 2 steps 'done' via POST /api/steps/{id}/feedback")
        logger.info("=======================================================")
        step1_id = steps1[0]["id"]
        step2_id = steps1[1]["id"]
        step3_id = steps1[2]["id"]

        logger.info("Marking step 1 done (%s)...", step1_id)
        res_fb1 = await client.post(f"/api/steps/{step1_id}/feedback", json={"status": "done", "update_cognee": True}, headers=headers)
        logger.info("Feedback response Step 1: status=%d | body=%s", res_fb1.status_code, res_fb1.text)

        logger.info("Marking step 2 done (%s)...", step2_id)
        res_fb2 = await client.post(f"/api/steps/{step2_id}/feedback", json={"status": "done", "update_cognee": True}, headers=headers)
        logger.info("Feedback response Step 2: status=%d | body=%s", res_fb2.status_code, res_fb2.text)

        logger.info("\n=======================================================")
        logger.info("STEP 3: Reject 1 step via POST /api/steps/{id}/feedback")
        logger.info("=======================================================")
        logger.info("Marking step 3 rejected (%s)...", step3_id)
        res_fb3 = await client.post(f"/api/steps/{step3_id}/feedback", json={"status": "rejected", "update_cognee": True}, headers=headers)
        logger.info("Feedback response Step 3: status=%d | body=%s", res_fb3.status_code, res_fb3.text)

        # Give Cognee background/async processing a moment if needed
        logger.info("Waiting 5 seconds before generating similar roadmap...")
        await asyncio.sleep(5)

        logger.info("\n=======================================================")
        logger.info("STEP 4: Regenerate a roadmap for similar-type issue opportunity 2")
        logger.info("=======================================================")
        t0 = time.time()
        res2 = await client.post("/api/roadmaps", json={"opportunity_id": str(issue2_id), "remember_in_cognee": True, "force_regenerate": True}, headers=headers)
        logger.info("POST /api/roadmaps (Issue 2) status: %d (time: %.2fs)", res2.status_code, time.time() - t0)
        if res2.status_code not in (200, 201):
            logger.error("Failed to generate Issue 2 roadmap: %s", res2.text)
            return
        roadmap2 = res2.json()
        logger.info("Roadmap 2 ID: %s | Title: '%s'", roadmap2["id"], roadmap2["title"])
        steps2 = roadmap2.get("steps", [])
        logger.info("Generated %d steps for Roadmap 2:", len(steps2))
        for idx, s in enumerate(steps2, 1):
            logger.info("  Step %d [%s] id=%s: status=%s | is_memified=%s | %s", idx, s["title"], s["id"], s["status"], s["is_memified"], s["description"][:100])

        logger.info("\n=======================================================")
        logger.info("STEP 5: Check GET /api/roadmaps/{id} for Roadmap 2")
        logger.info("=======================================================")
        res_get2 = await client.get(f"/api/roadmaps/{roadmap2['id']}", headers=headers)
        logger.info("GET /api/roadmaps/%s status: %d | body=%s", roadmap2["id"], res_get2.status_code, res_get2.text)

    await close_db()
    logger.info("Phase 6 Live Test Completed.")

if __name__ == "__main__":
    asyncio.run(run_test())
