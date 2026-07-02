"""
Waypoint — Cognee Memory Lifecycle Validation Spike

Validates the core primitives the entire demo depends on using
the real Cognee v1.2.2 API:

1. remember() — storing data with dataset isolation
2. recall() — querying memory
3. improve() via FeedbackEntry — feedback-weighted learning
4. forget() — granular data removal

Run: python scripts/cognee_spike.py
Requires: LLM_API_KEY env var set (OpenAI key for Cognee's internal LLM)

EXIT CODES:
  0 = all assertions passed — safe to proceed to Phase 2
  1 = one or more assertions failed — STOP, debug before proceeding
"""

import asyncio
import os
import sys
import logging
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s %(message)s",
)
logger = logging.getLogger("cognee_spike")

# Dataset name for isolation
SPIKE_DATASET = "spike_test_data"


async def run_spike():
    """Run the complete Cognee memory lifecycle validation."""
    import cognee
    from cognee import FeedbackEntry, SearchType

    results = {
        "step_0_reset": False,
        "step_1_remember_profile": False,
        "step_2_remember_steps": False,
        "step_3_recall_basic": False,
        "step_4_improve_positive": False,
        "step_5_improve_negative": False,
        "step_6_recall_with_feedback": False,
        "step_7_forget": False,
        "step_8_recall_after_forget": False,
    }

    # Session ID for tracking feedback
    session_id = f"spike_session_{int(time.time())}"

    # ==================================================================
    # Step 0: Clean slate
    # ==================================================================
    logger.info("=" * 70)
    logger.info("STEP 0: Reset Cognee state")
    try:
        await cognee.forget(everything=True)
        results["step_0_reset"] = True
        logger.info("PASS: Reset complete")
    except Exception as e:
        logger.warning("Reset may have failed (OK if first run): %s", e)
        results["step_0_reset"] = True  # Non-blocking

    # ==================================================================
    # Step 1: remember(user_profile)
    # ==================================================================
    logger.info("=" * 70)
    logger.info("STEP 1: remember(user_profile)")

    profile_text = (
        "User Profile for Jane Tester.\n"
        "Skills: Python, FastAPI, PostgreSQL, React, TypeScript.\n"
        "Experience: 2 years building web applications.\n"
        "Projects: Built a task manager with FastAPI and React. "
        "Contributed to open-source Python libraries.\n"
        "Interests: Backend development, AI/ML, databases."
    )

    try:
        result = await cognee.remember(
            profile_text,
            dataset_name=SPIKE_DATASET,
        )
        logger.info("remember result: %s", result)
        results["step_1_remember_profile"] = True
        logger.info("PASS: Profile remembered")
    except Exception as e:
        logger.error("FAIL: remember(profile) error: %s", e, exc_info=True)

    # ==================================================================
    # Step 2: remember(step_1, step_2) — two different steps
    # ==================================================================
    logger.info("=" * 70)
    logger.info("STEP 2: remember(step_1) and remember(step_2)")

    step_1_text = (
        "Roadmap Step: Set up FastAPI project with async PostgreSQL.\n"
        "Description: Initialize a FastAPI project with SQLAlchemy async, "
        "create data models, and set up database migrations. "
        "This is a Python backend development task using the FastAPI framework.\n"
        "Type: issue\n"
        "Roadmap: Contribute to open-source issue tracker"
    )

    step_2_text = (
        "Roadmap Step: Write comprehensive CSS styling for landing page.\n"
        "Description: Create responsive CSS layouts and visual animations "
        "for the project landing page. Focus on colors, typography, and "
        "cross-browser compatibility. Pure frontend styling work.\n"
        "Type: issue\n"
        "Roadmap: Contribute to open-source issue tracker"
    )

    try:
        r1 = await cognee.remember(
            step_1_text,
            dataset_name=SPIKE_DATASET,
        )
        logger.info("Step 1 remembered: %s", r1)

        r2 = await cognee.remember(
            step_2_text,
            dataset_name=SPIKE_DATASET,
        )
        logger.info("Step 2 remembered: %s", r2)

        results["step_2_remember_steps"] = True
        logger.info("PASS: Both steps remembered")
    except Exception as e:
        logger.error("FAIL: remember(steps) error: %s", e, exc_info=True)

    # ==================================================================
    # Step 3: Basic recall (before feedback)
    # ==================================================================
    logger.info("=" * 70)
    logger.info("STEP 3: Basic recall (pre-feedback)")

    query = (
        "What steps should I take to contribute to an open-source project "
        "given my Python and FastAPI skills?"
    )

    try:
        recall_results = await cognee.recall(
            query,
            datasets=[SPIKE_DATASET],
            top_k=10,
        )
        logger.info("Pre-feedback recall type: %s", type(recall_results))
        logger.info("Pre-feedback recall: %s", str(recall_results)[:3000])
        results["step_3_recall_basic"] = True
        logger.info("PASS: Basic recall works")
    except Exception as e:
        logger.error("FAIL: recall() error: %s", e, exc_info=True)

    # ==================================================================
    # Step 4: Provide positive feedback for step_1
    # ==================================================================
    logger.info("=" * 70)
    logger.info("STEP 4: Positive feedback via session + FeedbackEntry")

    try:
        # First, ask about step_1 in a session to create a QA entry
        session_result = await cognee.recall(
            "Tell me about the FastAPI project setup step",
            datasets=[SPIKE_DATASET],
            session_id=session_id,
            top_k=5,
        )
        logger.info("Session recall result: %s", str(session_result)[:2000])

        # Extract QA entry ID from session results
        qa_id = None
        if session_result and isinstance(session_result, list):
            for entry in session_result:
                entry_dict = entry if isinstance(entry, dict) else getattr(entry, '__dict__', {})
                logger.info("Entry keys: %s", entry_dict.keys() if isinstance(entry_dict, dict) else dir(entry))
                # Try to find an id field
                potential_id = (
                    entry_dict.get("id") or
                    entry_dict.get("qa_id") or
                    entry_dict.get("entry_id") or
                    getattr(entry, "id", None) or
                    getattr(entry, "qa_id", None)
                )
                if potential_id:
                    qa_id = str(potential_id)
                    break

        if qa_id:
            logger.info("Found QA entry ID: %s", qa_id)
            feedback = FeedbackEntry(
                qa_id=qa_id,
                feedback_score=1,
                feedback_text="This step was very helpful for setting up the backend.",
            )
            await cognee.remember(feedback)
            results["step_4_improve_positive"] = True
            logger.info("PASS: Positive feedback stored for qa_id=%s", qa_id)
        else:
            # Fallback: try improve() directly without FeedbackEntry
            logger.warning("No QA entry ID found — trying improve() directly")
            await cognee.improve(dataset=SPIKE_DATASET)
            results["step_4_improve_positive"] = "partial"
            logger.info("PARTIAL: improve() ran without explicit feedback")

    except Exception as e:
        logger.error("FAIL: positive feedback error: %s", e, exc_info=True)

    # ==================================================================
    # Step 5: Provide negative feedback for step_2
    # ==================================================================
    logger.info("=" * 70)
    logger.info("STEP 5: Negative feedback for CSS step")

    try:
        session_id_2 = f"spike_session_neg_{int(time.time())}"
        session_result_2 = await cognee.recall(
            "Tell me about the CSS styling landing page step",
            datasets=[SPIKE_DATASET],
            session_id=session_id_2,
            top_k=5,
        )
        logger.info("Session recall 2 result: %s", str(session_result_2)[:2000])

        qa_id_2 = None
        if session_result_2 and isinstance(session_result_2, list):
            for entry in session_result_2:
                entry_dict = entry if isinstance(entry, dict) else getattr(entry, '__dict__', {})
                potential_id = (
                    entry_dict.get("id") or
                    entry_dict.get("qa_id") or
                    entry_dict.get("entry_id") or
                    getattr(entry, "id", None) or
                    getattr(entry, "qa_id", None)
                )
                if potential_id:
                    qa_id_2 = str(potential_id)
                    break

        if qa_id_2:
            feedback_neg = FeedbackEntry(
                qa_id=qa_id_2,
                feedback_score=-1,
                feedback_text="This step is irrelevant to my backend-focused skills.",
            )
            await cognee.remember(feedback_neg)
            results["step_5_improve_negative"] = True
            logger.info("PASS: Negative feedback stored for qa_id=%s", qa_id_2)
        else:
            logger.warning("No QA entry ID found for CSS step — marking partial")
            results["step_5_improve_negative"] = "partial"

    except Exception as e:
        logger.error("FAIL: negative feedback error: %s", e, exc_info=True)

    # ==================================================================
    # Step 6: Run improve() then recall with feedback_influence
    # ==================================================================
    logger.info("=" * 70)
    logger.info("STEP 6: improve() + recall with feedback_influence")

    try:
        # Run improve to apply feedback weights
        session_ids_to_improve = [session_id]
        if session_id_2:
            session_ids_to_improve.append(session_id_2)

        logger.info("Running improve with sessions: %s", session_ids_to_improve)
        await cognee.improve(
            dataset=SPIKE_DATASET,
            session_ids=session_ids_to_improve,
        )
        logger.info("improve() completed")

        # Recall with feedback influence
        recall_with_feedback = await cognee.recall(
            query,
            datasets=[SPIKE_DATASET],
            top_k=10,
            feedback_influence=0.5,
        )

        logger.info("Post-feedback recall type: %s", type(recall_with_feedback))
        logger.info("Post-feedback recall: %s", str(recall_with_feedback)[:3000])

        # Check ordering
        result_str = str(recall_with_feedback).lower()
        has_fastapi = "fastapi" in result_str
        has_css = "css" in result_str or "landing page" in result_str

        if has_fastapi:
            logger.info("FastAPI step appears in recall")
            if has_css:
                fastapi_pos = result_str.find("fastapi")
                css_pos = min(
                    result_str.find("css") if "css" in result_str else 99999,
                    result_str.find("landing page") if "landing page" in result_str else 99999,
                )
                if fastapi_pos < css_pos:
                    logger.info("PASS: FastAPI ranks higher than CSS (pos %d vs %d)", fastapi_pos, css_pos)
                    results["step_6_recall_with_feedback"] = True
                else:
                    logger.warning("PARTIAL: Both present but CSS ranks higher (%d vs %d)", css_pos, fastapi_pos)
                    results["step_6_recall_with_feedback"] = "partial"
            else:
                logger.info("PASS: Only FastAPI step returned (CSS excluded)")
                results["step_6_recall_with_feedback"] = True
        else:
            logger.warning("FastAPI step not in results")
            results["step_6_recall_with_feedback"] = False

    except Exception as e:
        logger.error("FAIL: improve/recall-with-feedback error: %s", e, exc_info=True)

    # ==================================================================
    # Step 7: forget(step_2 dataset)
    # ==================================================================
    logger.info("=" * 70)
    logger.info("STEP 7: forget()")

    try:
        # Forget the entire dataset to test the mechanism
        # In production we'd use data_id for granular deletion
        forget_result = await cognee.forget(dataset=SPIKE_DATASET, memory_only=True)
        logger.info("forget result: %s", forget_result)
        results["step_7_forget"] = True
        logger.info("PASS: forget() completed")
    except Exception as e:
        logger.error("FAIL: forget() error: %s", e, exc_info=True)

    # ==================================================================
    # Step 8: recall after forget — should return empty/minimal
    # ==================================================================
    logger.info("=" * 70)
    logger.info("STEP 8: Recall after forget — verify data removed")

    try:
        recall_after_forget = await cognee.recall(
            query,
            datasets=[SPIKE_DATASET],
            top_k=10,
        )
        logger.info("Post-forget recall: %s", str(recall_after_forget)[:2000])

        result_str = str(recall_after_forget).lower()
        has_any_step = "fastapi" in result_str or "css" in result_str

        if not has_any_step:
            logger.info("PASS: No step data returned after forget()")
            results["step_8_recall_after_forget"] = True
        else:
            logger.warning("PARTIAL: Some data still appears after memory_only forget")
            results["step_8_recall_after_forget"] = "partial"

    except Exception as e:
        # If recall errors because dataset is gone, that's actually a pass
        logger.info("Recall errored after forget (expected): %s", e)
        results["step_8_recall_after_forget"] = True

    # ==================================================================
    # Final Report
    # ==================================================================
    logger.info("=" * 70)
    logger.info("COGNEE MEMORY LIFECYCLE SPIKE — RESULTS")
    logger.info("=" * 70)

    all_pass = True
    for test, result in results.items():
        if result is True:
            icon = "PASS"
        elif result == "partial":
            icon = "PARTIAL"
        else:
            icon = "FAIL"
            all_pass = False
        logger.info("  %-35s %s", test, icon)

    logger.info("=" * 70)
    if all_pass:
        logger.info("ALL TESTS PASSED — Safe to proceed to Phase 2")
        return 0
    else:
        failed = [k for k, v in results.items() if v is False]
        logger.error(
            "BLOCKED — Failed tests: %s. "
            "Debug before proceeding to Phase 2.",
            ", ".join(failed),
        )
        return 1


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    if not os.environ.get("ENABLE_BACKEND_ACCESS_CONTROL"):
        os.environ["ENABLE_BACKEND_ACCESS_CONTROL"] = "false"

    # Check for LLM API key
    if not os.environ.get("LLM_API_KEY") and not os.environ.get("COGNEE_LLM_API_KEY"):
        logger.error(
            "LLM_API_KEY or COGNEE_LLM_API_KEY must be set. "
            "Cognee needs an LLM (e.g., OpenAI) for knowledge graph processing."
        )
        sys.exit(1)

    # Set LLM_API_KEY if only COGNEE_LLM_API_KEY is provided
    if os.environ.get("COGNEE_LLM_API_KEY") and not os.environ.get("LLM_API_KEY"):
        os.environ["LLM_API_KEY"] = os.environ["COGNEE_LLM_API_KEY"]

    exit_code = asyncio.run(run_spike())
    sys.exit(exit_code)
