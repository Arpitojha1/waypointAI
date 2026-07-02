"""
Waypoint API — Cognee Memory Client

Thin wrapper over the Cognee SDK (v1.2+), exposing the 4 operations:
  remember() — store data with dataset/node_set tagging
  recall()   — query memory with dataset scoping + feedback influence
  improve()  — apply session feedback weights to enrich the knowledge graph
  forget()   — remove specific data or entire datasets from memory

═══════════════════════════════════════════════════════════════════════════
COGNEE SDK API REFERENCE (v1.2.2, verified via inspect)
═══════════════════════════════════════════════════════════════════════════
- cognee.remember(data, dataset_name, session_id, self_improvement=True)
- cognee.recall(query_text, datasets, top_k, feedback_influence, session_id)
- cognee.improve(dataset, session_ids, build_global_context_index)
- cognee.forget(data_id, dataset, dataset_id, everything, memory_only)
- cognee.FeedbackEntry(qa_id, feedback_score, feedback_text)
- cognee.memify(dataset, ...) — enrichment pipeline

Feedback flow:
  1. remember(data, session_id=sid) → QA entries with IDs
  2. remember(FeedbackEntry(qa_id=..., feedback_score=+1/-1))
  3. improve(dataset, session_ids=[sid]) → applies feedback weights to graph
  4. recall(query, feedback_influence=0.5) → weighted ranking
═══════════════════════════════════════════════════════════════════════════
"""

import logging
import uuid
from typing import Any, Dict, List, Optional, Union

import cognee
from cognee import SearchType, FeedbackEntry

logger = logging.getLogger(__name__)


async def configure_cognee(
    llm_api_key: str,
    llm_provider: str = "openai",
    llm_model: str = "gpt-4o-mini",
) -> None:
    """
    Initialize Cognee's LLM and storage configuration.
    Call once at app startup (in the lifespan manager).
    """
    from cognee import config as cognee_config

    cognee_config.set_llm_config({
        "llm_provider": llm_provider,
        "llm_model": llm_model,
        "llm_api_key": llm_api_key,
    })
    logger.info("Cognee configured: provider=%s model=%s", llm_provider, llm_model)


# ---------------------------------------------------------------------------
# remember — store data into Cognee's knowledge graph
# ---------------------------------------------------------------------------

async def remember(
    data: Any,
    data_type: str,
    dataset_name: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Any:
    """
    Store data in Cognee with type-based dataset isolation.

    Args:
        data: Text content, file path, or structured data to remember.
        data_type: One of "user_profile", "job", "hackathon", "issue", "step".
        dataset_name: Override dataset name (defaults to data_type).
        user_id: User ID for dataset scoping (prepended to dataset name).
        session_id: If set, stores in session cache for feedback tracking.

    Returns:
        RememberResult from Cognee.
    """
    # Build dataset name: user-scoped if user_id provided
    ds_name = dataset_name or data_type
    if user_id:
        ds_name = f"{user_id}_{ds_name}"

    # Convert structured data to text if needed
    if isinstance(data, dict):
        text = _dict_to_text(data, data_type)
    elif not isinstance(data, str):
        text = str(data)
    else:
        text = data

    logger.info(
        "cognee.remember: dataset=%s session=%s len=%d",
        ds_name, session_id, len(text),
    )

    result = await cognee.remember(
        text,
        dataset_name=ds_name,
        session_id=session_id,
        self_improvement=True,
    )

    return result


# ---------------------------------------------------------------------------
# recall — query Cognee's knowledge graph
# ---------------------------------------------------------------------------

async def recall(
    query: str,
    data_type: Optional[str] = None,
    datasets: Optional[List[str]] = None,
    user_id: Optional[str] = None,
    top_k: int = 15,
    search_type: Optional[SearchType] = None,
    feedback_influence: float = 0.3,
    session_id: Optional[str] = None,
) -> Any:
    """
    Query Cognee's memory with optional feedback-weighted ranking.

    Args:
        query: Natural language query.
        data_type: Filter to a specific type (used to build dataset name).
        datasets: Explicit dataset names to scope the search.
        user_id: User ID for scoping.
        top_k: Number of results to return.
        search_type: Force a specific retrieval mode (auto if None).
        feedback_influence: Weight of feedback scores on ranking (0.0-1.0).
        session_id: Session ID to search within.

    Returns:
        List of search results from Cognee.
    """
    # Build dataset scope
    ds_scope = datasets
    if data_type and not ds_scope:
        ds_name = data_type
        if user_id:
            ds_name = f"{user_id}_{data_type}"
        ds_scope = [ds_name]

    logger.info(
        "cognee.recall: query='%s' datasets=%s feedback_influence=%.2f",
        query[:80], ds_scope, feedback_influence,
    )

    kwargs = {
        "query_text": query,
        "top_k": top_k,
        "feedback_influence": feedback_influence,
    }
    if ds_scope:
        kwargs["datasets"] = ds_scope
    if search_type:
        kwargs["query_type"] = search_type
    if session_id:
        kwargs["session_id"] = session_id

    results = await cognee.recall(**kwargs)
    return results


# ---------------------------------------------------------------------------
# improve — apply feedback weights and enrich the knowledge graph
# ---------------------------------------------------------------------------

async def improve(
    step_data: Dict[str, Any],
    outcome: str,
    session_id: str,
    user_id: Optional[str] = None,
    dataset_name: Optional[str] = None,
) -> None:
    """
    Record feedback on a step and enrich the knowledge graph.

    Uses Cognee's native feedback mechanism:
    1. Store a FeedbackEntry with a score (+1 for positive, -1 for negative)
    2. Run improve() to apply feedback weights to the knowledge graph

    Args:
        step_data: Dict with at minimum {"title": ..., "qa_id": ...}
                   qa_id is the Cognee QA entry ID from the original remember()
        outcome: "positive" (done/helpful) or "negative" (rejected/unhelpful)
        session_id: The session ID where the original data was remembered.
        user_id: User ID for scoping.
        dataset_name: Dataset to improve (defaults to "step").
    """
    qa_id = step_data.get("qa_id")
    score = 1 if outcome == "positive" else -1

    feedback_text = (
        f"Step '{step_data.get('title', 'Unknown')}' was "
        f"{'completed and found helpful' if outcome == 'positive' else 'rejected as unhelpful'}."
    )

    # Store feedback entry
    if qa_id:
        feedback = FeedbackEntry(
            qa_id=qa_id,
            feedback_score=score,
            feedback_text=feedback_text,
        )
        await cognee.remember(feedback)
        logger.info(
            "cognee.improve: feedback stored for qa_id=%s score=%d",
            qa_id, score,
        )

    # Run improve to apply feedback weights
    ds_name = dataset_name or "step"
    if user_id:
        ds_name = f"{user_id}_{ds_name}"

    await cognee.improve(
        dataset=ds_name,
        session_ids=[session_id] if session_id else None,
    )

    logger.info(
        "cognee.improve: enrichment complete for dataset=%s session=%s",
        ds_name, session_id,
    )


# ---------------------------------------------------------------------------
# forget — remove data from Cognee's memory
# ---------------------------------------------------------------------------

async def forget(
    data_type: Optional[str] = None,
    data_id: Optional[str] = None,
    dataset_name: Optional[str] = None,
    user_id: Optional[str] = None,
    forget_all: bool = False,
    memory_only: bool = False,
) -> dict:
    """
    Remove data from Cognee's knowledge graph.

    Uses Cognee's native forget() which supports:
    - Forgetting a specific data item (data_id + dataset)
    - Forgetting an entire dataset
    - Forgetting everything the user owns

    Args:
        data_type: Type of data (used to build dataset name).
        data_id: UUID of specific item to forget.
        dataset_name: Explicit dataset name to forget.
        user_id: User ID for scoping.
        forget_all: If True, wipes everything (dev/test use only).
        memory_only: If True, keep raw data but clear graph + vectors.

    Returns:
        Dict with deletion summary from Cognee.
    """
    if forget_all:
        result = await cognee.forget(everything=True)
        logger.warning("cognee.forget: WIPED ALL DATA — result=%s", result)
        return result

    ds_name = dataset_name or data_type
    if user_id and ds_name:
        ds_name = f"{user_id}_{ds_name}"

    kwargs = {}
    if ds_name:
        kwargs["dataset"] = ds_name
    if data_id:
        kwargs["data_id"] = uuid.UUID(data_id) if isinstance(data_id, str) else data_id
    if memory_only:
        kwargs["memory_only"] = True

    result = await cognee.forget(**kwargs)
    logger.info("cognee.forget: dataset=%s data_id=%s result=%s", ds_name, data_id, result)
    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _dict_to_text(data: dict, data_type: str) -> str:
    """Convert a dict to a structured text representation for Cognee ingestion."""
    lines = [f"Type: {data_type}"]
    for key, value in data.items():
        if value is not None:
            if isinstance(value, list):
                lines.append(f"{key}: {', '.join(str(v) for v in value)}")
            else:
                lines.append(f"{key}: {value}")
    return "\n".join(lines)
