"""
Standalone isolation test: does cognee.recall(..., feedback_influence=0.5)
work on nemotron via OpenRouter, or does it hit the same Instructor/
WrittenLesson JSON-schema-wrapping bug we saw on gpt-4o-mini?

Does NOT run the full spike pipeline. Assumes a dataset already has
remember() + improve() applied (reuse "spike_test_data" from cognee_spike.py
if its local LanceDB/KuzuDB state is still on disk — this avoids re-running
remember/improve just to test one call).

If no prior state exists, this script does a minimal remember + improve
first so the recall call has something to work with.

Usage:
    cd backend
    python scripts/test_nemotron_feedback_influence.py

Forces LLM_MODEL to nemotron for this run regardless of what's in .env,
so you don't have to hand-edit .env to test this. Also pins EMBEDDING_*
vars explicitly (rather than trusting .env) since embeddings aren't part
of what we're testing here and a missing/unloaded .env shouldn't be able
to corrupt this run.
"""
import asyncio
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# Load .env by explicit path (backend/.env), independent of whatever
# directory this script happens to be run from. Assumes this file lives
# at backend/scripts/<this file>.py.
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
loaded = load_dotenv(dotenv_path=_ENV_PATH)
print(f"[config] .env path   = {_ENV_PATH} (loaded={loaded})")

# Force nemotron for this run only -- doesn't touch your .env file.
os.environ["LLM_PROVIDER"] = "custom"
os.environ["LLM_MODEL"] = "openrouter/nvidia/nemotron-3-ultra-550b-a55b:free"
os.environ["LLM_ENDPOINT"] = "https://openrouter.ai/api/v1"
os.environ.setdefault("ENABLE_BACKEND_ACCESS_CONTROL", "false")

# Embeddings are NOT what we're testing here -- pin them explicitly to the
# known-working config from Phase 1 rather than trusting .env to have it,
# so a missing/unloaded .env can't silently corrupt this test the way it
# just did (Cognee fell back to deriving an embedding model from LLM_MODEL,
# producing the bogus "nvidia/nemotron-3-ultra-550b-a55b" embedding call).
os.environ["EMBEDDING_PROVIDER"] = "custom"
os.environ["EMBEDDING_MODEL"] = "openrouter/openai/text-embedding-3-large"
os.environ["EMBEDDING_ENDPOINT"] = "https://openrouter.ai/api/v1"
os.environ["EMBEDDING_DIMENSIONS"] = "3072"
os.environ.setdefault("EMBEDDING_API_KEY", os.environ.get("LLM_API_KEY", ""))

if not os.environ.get("LLM_API_KEY"):
    print("\nFAIL: LLM_API_KEY is not set. .env didn't load it and it's not "
          "in your shell environment either. Set it and re-run.")
    sys.exit(1)
print(f"[config] LLM_API_KEY  = {'*' * 6}{os.environ['LLM_API_KEY'][-4:]} (present)")

DATASET = "spike_test_data"
SESSION_ID = "feedback_isolation_test"


async def main():
    import cognee
    from cognee import FeedbackEntry

    print(f"[config] LLM_MODEL = {os.environ['LLM_MODEL']}")
    print(f"[config] dataset   = {DATASET}\n")

    # Minimal seed so recall has something to rank, in case prior spike
    # state isn't present. Cheap — a couple short remembers.
    print("[setup] seeding minimal step data (idempotent-ish)...")
    t0 = time.monotonic()
    await cognee.remember(
        {"title": "step_1", "content": "Set up a FastAPI project skeleton."},
        dataset_name=DATASET,
        session_id=SESSION_ID,
    )
    await cognee.remember(
        {"title": "step_2", "content": "Add a CSS theme to the frontend."},
        dataset_name=DATASET,
        session_id=SESSION_ID,
    )
    print(f"[setup] remember() done in {time.monotonic() - t0:.1f}s\n")

    print("[setup] running a baseline recall to generate a QA entry to attach feedback to...")
    recall_result = await cognee.recall(
        "What should I do first?",
        datasets=[DATASET],
        session_id=SESSION_ID,
    )
    qa_id = getattr(recall_result, "qa_id", None) or getattr(recall_result, "id", None)
    print(f"[setup] baseline recall qa_id = {qa_id}\n")

    if qa_id:
        print("[setup] attaching positive feedback + running improve()...")
        await cognee.remember(
            FeedbackEntry(qa_id=qa_id, feedback_score=1, feedback_text="step_1 was correct first step"),
            dataset_name=DATASET,
            session_id=SESSION_ID,
        )
        await cognee.improve(dataset=DATASET, session_ids=[SESSION_ID])
    else:
        print("[setup] WARNING: no qa_id found on recall result — feedback_influence "
              "test below may run against an un-improved graph. Proceeding anyway.")

    # --- The actual test: isolate feedback_influence recall on nemotron ---
    print("\n[test] calling recall(..., feedback_influence=0.5) on nemotron...")
    t0 = time.monotonic()
    try:
        result = await cognee.recall(
            "What should I do first?",
            datasets=[DATASET],
            session_id=SESSION_ID,
            feedback_influence=0.5,
        )
        elapsed = time.monotonic() - t0
        print(f"\nPASS: feedback_influence recall completed in {elapsed:.1f}s")
        print(f"      result: {result}")
    except Exception as e:
        elapsed = time.monotonic() - t0
        print(f"\nFAIL: feedback_influence recall raised after {elapsed:.1f}s")
        print(f"      {type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())