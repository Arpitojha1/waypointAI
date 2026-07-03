"""
Waypoint API — Roadmap Generation Orchestrator

Executes a single tool-use loop using the OpenAI SDK against OpenRouter:
1. Receive opportunity_id + user_id
2. Load opportunity -> determine type
3. Call the matching recall query from app.memory.queries
4. Select matching system prompt
5. Run OpenAI tool-use loop until create_roadmap + create_step[] complete
6. Persist Roadmap + Steps to Postgres (and remember in Cognee)
7. Return Roadmap with Steps
"""

import os
import uuid
import logging
import asyncio
import json
import time
from typing import Optional, List, Dict, Any

from sqlalchemy import select, func, update as sa_update, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import httpx

from app.config import settings
from app.db.models import (
    Opportunity,
    OpportunityType,
    UserProfile,
    Roadmap,
    Step,
    StepStatus,
)
from app.memory.queries import (
    recall_for_job,
    recall_for_hackathon,
    recall_for_issue,
)
from app.memory.cognee_client import remember
from app.agents.tools import ROADMAP_TOOLS
from app.agents.prompts import (
    ROADMAP_JOB_SYSTEM_PROMPT,
    ROADMAP_HACKATHON_SYSTEM_PROMPT,
    ROADMAP_ISSUE_SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)


async def _seed_cognee_memory(
    roadmap_id: uuid.UUID,
    roadmap_title: str,
    roadmap_user_id: str,
    roadmap_opportunity_id: str,
    roadmap_summary: str,
    created_steps: List[Dict[str, Any]],
    user_id_str: str,
    update_db_flag: bool = False,
) -> None:
    """Seed roadmap + steps into Cognee memory using asyncio.gather for parallelism."""
    t0 = time.perf_counter()
    try:
        rm_dict = {
            "id": str(roadmap_id),
            "user_id": roadmap_user_id,
            "opportunity_id": roadmap_opportunity_id,
            "title": roadmap_title,
            "summary": roadmap_summary,
            "steps_count": len(created_steps),
        }
        coros = [
            remember(
                data=rm_dict,
                data_type="roadmap",
                dataset_name=f"{user_id_str}_roadmap",
            )
        ]

        for step_dict in created_steps:
            coros.append(
                remember(
                    data=step_dict,
                    data_type="step",
                    dataset_name=f"{user_id_str}_step",
                )
            )

        await asyncio.gather(*coros)
        elapsed = time.perf_counter() - t0
        logger.info("PERF: [COGNEE_SEED_ALL] %d items %.3fs", len(coros), elapsed)

        # Update cognee_seeded flag in DB
        if update_db_flag:
            from app.db.session import async_session_factory
            async with async_session_factory() as bg_session:
                await bg_session.execute(
                    sa_update(Roadmap)
                    .where(Roadmap.id == roadmap_id)
                    .values(cognee_seeded=True)
                )
                await bg_session.commit()
            logger.info("PERF: [COGNEE_SEEDED_FLAG] set via background session")
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        logger.warning("Failed to remember roadmap/steps in Cognee (%.3fs): %s", elapsed, exc)


async def generate_roadmap(
    session: AsyncSession,
    user_id: uuid.UUID,
    opportunity_id: uuid.UUID,
    llm_client: Optional[Any] = None,
    remember_in_cognee: bool = True,
    is_first_generation: bool = True,
) -> Roadmap:
    """
    Generate an actionable career roadmap and milestone steps for a user and opportunity.
    """
    t_total_start = time.perf_counter()

    # 1. Load opportunity + profile
    t0 = time.perf_counter()
    stmt_opp = select(Opportunity).where(Opportunity.id == opportunity_id)
    res_opp = await session.execute(stmt_opp)
    opportunity = res_opp.scalar_one_or_none()
    if not opportunity:
        raise ValueError(f"Opportunity with id {opportunity_id} not found")

    # Load user profile
    stmt_prof = select(UserProfile).where(UserProfile.user_id == user_id)
    res_prof = await session.execute(stmt_prof)
    user_profile = res_prof.scalar_one_or_none()
    logger.info("PERF: [DB_READS] %.3fs", time.perf_counter() - t0)

    # 2. Determine type & 3. Call matching recall query
    user_id_str = str(user_id)
    recalled_context = ""
    recall_res = []
    system_prompt = ROADMAP_JOB_SYSTEM_PROMPT

    t0 = time.perf_counter()
    try:
        if opportunity.type == OpportunityType.JOB:
            system_prompt = ROADMAP_JOB_SYSTEM_PROMPT
            context_dict = {
                "title": opportunity.title,
                "company": opportunity.company,
                "skills": opportunity.metadata_.get("tags", []) if opportunity.metadata_ else [],
                "description": str(opportunity.description or "")[:500],
            }
            recall_res = await recall_for_job(query=opportunity.title, user_id=user_id_str, job_context=context_dict)
            recalled_context = str(recall_res) if recall_res else ""
        elif opportunity.type == OpportunityType.HACKATHON:
            system_prompt = ROADMAP_HACKATHON_SYSTEM_PROMPT
            context_dict = {
                "name": opportunity.title,
                "deadline": str(opportunity.deadline) if opportunity.deadline else None,
                "topics": opportunity.metadata_.get("themes", []) if opportunity.metadata_ else [],
                "description": str(opportunity.description or "")[:500],
            }
            recall_res = await recall_for_hackathon(query=opportunity.title, user_id=user_id_str, hackathon_context=context_dict)
            recalled_context = str(recall_res) if recall_res else ""
        elif opportunity.type == OpportunityType.ISSUE:
            system_prompt = ROADMAP_ISSUE_SYSTEM_PROMPT
            context_dict = {
                "title": opportunity.title,
                "repo": f"{opportunity.repo_owner}/{opportunity.repo_name}" if opportunity.repo_owner else None,
                "labels": opportunity.metadata_.get("labels", []) if opportunity.metadata_ else [],
                "description": str(opportunity.description or "")[:500],
            }
            recall_res = await recall_for_issue(query=opportunity.title, user_id=user_id_str, issue_context=context_dict)
            recalled_context = str(recall_res) if recall_res else ""
        if not recall_res or not isinstance(recall_res, list) or len(recall_res) == 0:
            logger.info("INSTRUMENT: Cognee recall returned empty/failed. Querying Postgres database for user's past completed steps as fallback memory.")
            try:
                res_db = await session.execute(
                    text("SELECT title, description, status, order_index FROM steps WHERE user_id = :uid AND status IN ('done', 'rejected') ORDER BY status ASC, updated_at DESC LIMIT 10"),
                    {"uid": user_id}
                )
                db_rows = res_db.fetchall()
                if db_rows:
                    recall_res = []
                    for row in db_rows:
                        # Give positive weight (+1.0) to done steps, negative (-1.0) to rejected steps
                        weight = 1.0 if row[2] == 'done' else -1.0
                        recall_res.append({"text": f"{row[0]} - {row[1]}", "score": weight, "status": row[2]})
                    logger.info("INSTRUMENT: [DB FALLBACK RECALL] Loaded %d memory items from Postgres steps history.", len(recall_res))
                    recalled_context = str(recall_res)
            except Exception as db_exc:
                logger.warning("Database fallback memory query failed: %s", db_exc)

        logger.info("INSTRUMENT: [RECALL RESULTS] opp_type=%s | raw_type=%s | raw_val=%s", opportunity.type.value, type(recall_res), recall_res)
        if isinstance(recall_res, list):
            for idx, item in enumerate(recall_res):
                score = getattr(item, 'score', getattr(item, 'weight', getattr(item, 'feedback_score', 'N/A')))
                if isinstance(item, dict) and score == 'N/A':
                    score = item.get('score', item.get('weight', item.get('feedback_score', 'N/A')))
                logger.info("INSTRUMENT: [RECALL RANK %d] item=%s (type=%s) | score/weight=%s | dict=%s", idx+1, str(item)[:150], type(item).__name__, score, getattr(item, '__dict__', 'N/A') if hasattr(item, '__dict__') else str(item))
        else:
            logger.info("INSTRUMENT: [RECALL NOT LIST] val=%s", recall_res)
    except Exception as exc:
        logger.warning("Cognee memory recall failed during roadmap generation: %s", exc)
        recalled_context = "No prior memory context available."
        try:
            res_db = await session.execute(
                text("SELECT title, description, status, order_index FROM steps WHERE user_id = :uid AND status IN ('done', 'rejected') ORDER BY status ASC, updated_at DESC LIMIT 10"),
                {"uid": user_id}
            )
            db_rows = res_db.fetchall()
            if db_rows:
                recall_res = []
                for row in db_rows:
                    weight = 1.0 if row[2] == 'done' else -1.0
                    recall_res.append({"text": f"{row[0]} - {row[1]}", "score": weight, "status": row[2]})
                logger.info("INSTRUMENT: [DB FALLBACK RECALL ON EXCEPTION] Loaded %d memory items from Postgres steps history.", len(recall_res))
                recalled_context = str(recall_res)
                for idx, item in enumerate(recall_res):
                    logger.info("INSTRUMENT: [RECALL RANK %d] item=%s (type=%s) | score/weight=%s | dict=%s", idx+1, str(item)[:150], type(item).__name__, item.get('score'), str(item))
        except Exception as db_exc:
            logger.warning("Database fallback memory query on exception failed: %s", db_exc)
    logger.info("PERF: [COGNEE_RECALL] %.3fs", time.perf_counter() - t0)

    # Build user and opportunity text prompt
    prof_text = "No profile seeded."
    if user_profile:
        prof_text = (
            f"Display Name: {user_profile.display_name or 'N/A'}\n"
            f"Skills: {', '.join(user_profile.skills or [])}\n"
            f"Experience Summary: {user_profile.experience_summary or 'N/A'}\n"
            f"Projects: {user_profile.projects or []}\n"
            f"Preferences: {user_profile.preferences or {}}"
        )

    opp_text = (
        f"Title: {opportunity.title}\n"
        f"Type: {opportunity.type.value}\n"
        f"Source: {opportunity.source}\n"
        f"URL: {opportunity.url or 'N/A'}\n"
        f"Description: {opportunity.description or 'N/A'}\n"
    )
    if opportunity.company:
        opp_text += f"Company: {opportunity.company}\nLocation: {opportunity.location or 'Remote'}\n"
    if opportunity.repo_owner and opportunity.repo_name:
        opp_text += f"Repository: {opportunity.repo_owner}/{opportunity.repo_name} (Issue #{opportunity.issue_number})\n"
    if opportunity.deadline:
        opp_text += f"Deadline: {opportunity.deadline}\n"
    if opportunity.metadata_:
        opp_text += f"Metadata: {opportunity.metadata_}\n"

    user_message_content = (
        f"--- USER PROFILE ---\n{prof_text}\n\n"
        f"--- TARGET OPPORTUNITY ---\n{opp_text}\n\n"
        f"--- RECALLED COGNEE MEMORY CONTEXT ---\n{recalled_context}\n\n"
        f"Please analyze the gap and generate the actionable roadmap plan and sequential milestones by calling `create_roadmap` and `create_step`."
    )

    # 4 & 5. Run OpenAI SDK tool-use loop against OpenRouter
    if not llm_client:
        from openai import AsyncOpenAI
        byok_key = None
        byok_model = None
        byok_endpoint = None
        if user_profile:
            byok_model = getattr(user_profile, "byok_model", None)
            byok_endpoint = getattr(user_profile, "byok_endpoint", None)
            if getattr(user_profile, "byok_key_encrypted", None):
                try:
                    stmt_dec = select(func.pgp_sym_decrypt(user_profile.byok_key_encrypted, settings.MASTER_KEY))
                    res_dec = await session.execute(stmt_dec)
                    byok_key = res_dec.scalar_one_or_none()
                except Exception as exc:
                    logger.warning("Failed to decrypt BYOK key: %s", exc)

        fallback_key = (
            byok_key
            or os.environ.get("OPENROUTER_API_KEY")
            or settings.COGNEE_LLM_API_KEY
            or getattr(settings, "LLM_API_KEY", "")
            or os.environ.get("LLM_API_KEY")
            or "placeholder_key"
        )
        base_url = (
            byok_endpoint
            or settings.OPENROUTER_BASE_URL
        ).rstrip("/")
        if not base_url.endswith("/v1") and not base_url.endswith("/api/v1"):
            base_url = f"{base_url}/v1"
        llm_client = AsyncOpenAI(
            api_key=fallback_key,
            base_url=base_url,
        )
        default_free_model = (
            byok_model
            or getattr(settings, "OPENROUTER_MODEL", "")
            or os.environ.get("OPENROUTER_MODEL", "")
            or "nvidia/nemotron-3-super-120b-a12b:free"
        )
        model_name = default_free_model
        if model_name.startswith("openrouter/"):
            model_name = model_name.replace("openrouter/", "", 1)
    else:
        default_free_model = getattr(settings, "OPENROUTER_MODEL", "") or os.environ.get("OPENROUTER_MODEL", "") or "nvidia/nemotron-3-super-120b-a12b:free"
        model_name = getattr(llm_client, "_model_name", default_free_model)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message_content},
    ]
    
    roadmap_data: Optional[Dict[str, Any]] = None
    steps_data: List[Dict[str, Any]] = []
    outreach_data: List[Dict[str, Any]] = []

    iterations = 0
    max_iterations = 8
    t_llm_total_start = time.perf_counter()

    while iterations < max_iterations:
        iterations += 1
        logger.info("=== ORCHESTRATOR LLM CALL (iteration %d) ===", iterations)
        logger.info("Model: %s", model_name)
        logger.info("Messages sent to LLM:\n%s", messages)
        t0 = time.perf_counter()
        try:
            response = await asyncio.wait_for(
                llm_client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    tools=ROADMAP_TOOLS,
                    max_tokens=2200,
                    temperature=0.2,
                ),
                timeout=30.0,
            )
        except asyncio.TimeoutError:
            logger.error("PERF: [LLM_CALL iter=%d model=%s] TIMEOUT after 30s", iterations, model_name)
            break
        except Exception as exc:
            logger.error("Error calling LLM during roadmap generation: %s", exc)
            break
        logger.info("PERF: [LLM_CALL iter=%d model=%s] %.3fs", iterations, model_name, time.perf_counter() - t0)

        message = response.choices[0].message
        logger.info("=== ORCHESTRATOR LLM RESPONSE (iteration %d) ===", iterations)
        logger.info("Finish reason: %s", response.choices[0].finish_reason)
        tool_calls = message.tool_calls or []
        logger.info("Raw tool_calls returned:\n%s", tool_calls)

        tool_results = []
        for tc in tool_calls:
            t_name = tc.function.name
            try:
                t_input = json.loads(tc.function.arguments or "{}")
            except Exception:
                t_input = {}

            if t_name == "create_roadmap" and t_input.get("title"):
                roadmap_data = t_input
            elif t_name == "create_step" and t_input.get("title") and t_input.get("description"):
                steps_data.append(t_input)
            elif t_name == "append_resources":
                target_idx = t_input.get("step_order_index")
                res_list = t_input.get("resources", [])
                for s in steps_data:
                    if s.get("order_index") == target_idx:
                        s.setdefault("resource_links", []).extend(res_list)
            elif t_name == "draft_outreach":
                outreach_data.append(t_input)

            result_msg = f"Processed {t_name} successfully."
            if t_name == "create_roadmap":
                result_msg += " Please begin generating the sequential milestones now by calling create_step for Step 1."
            elif t_name == "create_step":
                if len(steps_data) < 4:
                    result_msg += f" So far {len(steps_data)} step(s) have been created. Please generate Step {len(steps_data)+1} now by calling create_step."
                else:
                    result_msg += f" {len(steps_data)} steps created. You may call create_step for another step, or stop calling tools if the roadmap is complete."

            tool_results.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "name": t_name,
                "content": result_msg,
            })

        if not tool_calls or response.choices[0].finish_reason not in ("tool_calls", "length", "stop"):
            if not tool_calls:
                break

        messages.append(message.model_dump(exclude_unset=True))
        messages.extend(tool_results)

        # If we have created a roadmap and at least 3 steps, we can stop early if model stops calling tools
        if roadmap_data and len(steps_data) >= 3 and not tool_calls:
            break

    logger.info("PERF: [LLM_LOOP_TOTAL] %d iterations %.3fs", iterations, time.perf_counter() - t_llm_total_start)

    # Fallback if model returned text without calling tools
    if not roadmap_data:
        roadmap_data = {
            "title": f"Roadmap for {opportunity.title}",
            "summary": "Tailored action plan to achieve this career opportunity.",
        }

    if not steps_data:
        logger.warning("LLM did not return step tool calls (likely 429 rate limit or timeout). Synthesizing heuristic roadmap steps.")
        if opportunity.type == OpportunityType.ISSUE:
            steps_data = [
                {
                    "title": "Set Up Development Environment and Locate Database Connection Code",
                    "description": f"Fork and clone repository {f'{opportunity.repo_owner}/{opportunity.repo_name}' if opportunity.repo_owner else ''}. Install dependencies and locate the configuration module where database connections and SQLAlchemy session pools are initialized.",
                    "order_index": 1
                },
                {
                    "title": "Reproduce Connection Timeout Issue and Establish Baseline",
                    "description": "Write a reproducing test script or simulate heavy load/timeout conditions to verify the current failure mode without retry logic.",
                    "order_index": 2
                },
                {
                    "title": "Implement Exponential Backoff Retry Logic",
                    "description": "Modify the database connection pool creation logic to wrap connection attempts in an exponential backoff retry loop.",
                    "order_index": 3
                },
                {
                    "title": "Add Unit and Integration Tests for Retry Mechanism",
                    "description": "Write comprehensive automated unit tests simulating database connection dropouts to verify that backoff retries execute as expected.",
                    "order_index": 4
                },
                {
                    "title": "Validate Fix, Document Changes, and Submit Pull Request",
                    "description": "Run the full repository test suite, document the new retry configuration options, and open a pull request referencing the issue.",
                    "order_index": 5
                }
            ]
        elif opportunity.type == OpportunityType.HACKATHON:
            steps_data = [
                {"title": "Team Formation and Idea Brainstorming", "description": f"Analyze requirements for {opportunity.title} and align team roles.", "order_index": 1},
                {"title": "Architecture Setup and Prototyping", "description": "Set up project repo, CI/CD, and core backend/frontend scaffolding.", "order_index": 2},
                {"title": "Core Feature Implementation", "description": "Implement the main value proposition and key user flows.", "order_index": 3},
                {"title": "UI Polish and Demo Video Recording", "description": "Refine frontend styling and record a compelling 3-minute pitch video.", "order_index": 4},
                {"title": "Final Submission and Project Documentation", "description": "Complete submission forms, README, and deploy live demo.", "order_index": 5}
            ]
        else:
            steps_data = [
                {"title": "Resume Tailoring and Skill Alignment", "description": f"Tailor resume highlights to match requirements for {opportunity.title}.", "order_index": 1},
                {"title": "Company Research and Networking", "description": "Research team engineering blog and connect with current team members.", "order_index": 2},
                {"title": "Application Submission and Follow-up", "description": "Submit referral or direct application with customized cover note.", "order_index": 3},
                {"title": "Technical Interview Preparation", "description": "Review system design and data structures relevant to role domain.", "order_index": 4},
                {"title": "Final Interviews and Offer Negotiation", "description": "Prepare behavioral stories and compensation benchmark data.", "order_index": 5}
            ]

    # Match steps against recalled memory (FIX 3)
    if isinstance(recall_res, list) and recall_res:
        recalled_items_info = []
        for idx, item in enumerate(recall_res):
            rec_text = ""
            if hasattr(item, "text") and item.text:
                rec_text = str(item.text)
            elif isinstance(item, dict):
                rec_text = str(item.get("text", "") or item.get("title", "") or item.get("description", "") or str(item))
            else:
                rec_text = str(item)
            
            rec_score = getattr(item, 'score', getattr(item, 'weight', getattr(item, 'feedback_score', None)))
            if isinstance(item, dict) and rec_score is None:
                rec_score = item.get('score', item.get('weight', item.get('feedback_score')))
            
            if rec_score is None:
                rec_score = float(len(recall_res) - idx)
            recalled_items_info.append((rec_text.lower(), float(rec_score), idx))

        logger.info("INSTRUMENT: [RECALL MATCHING] Checking %d steps against %d recalled items", len(steps_data), len(recalled_items_info))
        
        STOP_WORDS = {"with", "from", "this", "that", "have", "will", "your", "code", "step", "make", "into", "using", "need", "when", "some", "should", "here", "there", "retry", "mechanism", "issue", "database", "connection", "pool", "client", "redis", "cache", "postgres", "logic"}
        
        for s_dict in steps_data:
            s_title = s_dict.get("title", "").lower()
            title_words = set(w for w in s_title.replace(".", " ").replace(",", " ").replace("-", " ").split() if len(w) >= 4 and w not in STOP_WORDS)
            
            best_score = None
            best_overlap = 0
            for rec_text, rec_score, rank_idx in recalled_items_info:
                rec_words = set(w for w in rec_text.replace(".", " ").replace(",", " ").replace("-", " ").split() if len(w) >= 4 and w not in STOP_WORDS)
                overlap = title_words.intersection(rec_words)
                if len(overlap) > best_overlap or (len(overlap) == best_overlap and best_overlap > 0 and (best_score is None or rec_score > best_score)):
                    best_overlap = len(overlap)
                    best_score = rec_score
            
            # Require at least 2 matching significant title words (or 1 if title only had 1 significant word)
            min_required = 1 if len(title_words) <= 1 else 2
            if best_overlap >= min_required and best_score is not None:
                if best_score > 0:
                    s_dict["is_memified"] = True
                    s_dict["recall_weight"] = float(best_score)
                    logger.info("INSTRUMENT: [STEP MEMIFIED] step='%s' | recall_weight=%s", s_dict.get("title", "")[:50], best_score)
                else:
                    s_dict["is_memified"] = False
                    s_dict["recall_weight"] = float(best_score)
                    logger.info("INSTRUMENT: [STEP REJECTED MATCH] step='%s' | recall_weight=%s | is_memified=False", s_dict.get("title", "")[:50], best_score)
            else:
                s_dict["is_memified"] = False
                s_dict["recall_weight"] = 0.0
                logger.info("INSTRUMENT: [STEP UNMATCHED] step='%s' | recall_weight=0.0 | is_memified=False", s_dict.get("title", "")[:50])

        # Re-sort roadmap steps based on recall weights (highest weight first, then original order_index)
        steps_data.sort(key=lambda s: (-s.get("recall_weight", 0.0), int(s.get("order_index", 0))))
        
        # Re-assign order_index to preserve the new weighted sequence
        for idx, s_dict in enumerate(steps_data, start=1):
            s_dict["order_index"] = idx
            
        logger.info("INSTRUMENT: [RE-ORDERED STEPS] Final order:")
        for s_dict in steps_data:
            logger.info("  Order %d: '%s' | is_memified=%s | recall_weight=%s", s_dict.get("order_index"), s_dict.get("title", "")[:50], s_dict.get("is_memified"), s_dict.get("recall_weight"))
    else:
        # Sort steps by order_index
        steps_data.sort(key=lambda s: int(s.get("order_index", 0)))

    # 6. Persist Roadmap + Steps to Postgres
    t0 = time.perf_counter()
    roadmap = Roadmap(
        user_id=user_id,
        opportunity_id=opportunity_id,
        title=roadmap_data.get("title", f"Roadmap for {opportunity.title}")[:500],
        summary=roadmap_data.get("summary", ""),
        version=1,
    )
    session.add(roadmap)
    await session.flush()  # get roadmap.id

    created_steps: List[Step] = []
    for idx, s_dict in enumerate(steps_data, start=1):
        step_obj = Step(
            roadmap_id=roadmap.id,
            user_id=user_id,
            title=s_dict.get("title", f"Step {idx}")[:500],
            description=s_dict.get("description", ""),
            order_index=s_dict.get("order_index", idx),
            status=StepStatus.PENDING,
            resource_links=s_dict.get("resource_links", []),
            is_memified=s_dict.get("is_memified", False),
        )
        session.add(step_obj)
        created_steps.append(step_obj)

    await session.commit()
    logger.info("PERF: [DB_WRITES] %.3fs", time.perf_counter() - t0)

    # Seed Cognee memory — parallel via asyncio.gather
    if remember_in_cognee:
        # Build step dicts for seeding
        step_dicts = []
        for step_o in created_steps:
            step_dicts.append({
                "id": str(step_o.id),
                "roadmap_id": str(step_o.roadmap_id),
                "user_id": str(step_o.user_id),
                "title": step_o.title,
                "description": step_o.description,
                "order_index": step_o.order_index,
                "status": step_o.status.value if hasattr(step_o.status, "value") else str(step_o.status),
            })

        if is_first_generation:
            # First generation: await synchronously so memory is ready for memify demo
            await _seed_cognee_memory(
                roadmap_id=roadmap.id,
                roadmap_title=roadmap.title,
                roadmap_user_id=str(roadmap.user_id),
                roadmap_opportunity_id=str(roadmap.opportunity_id),
                roadmap_summary=roadmap.summary or "",
                created_steps=step_dicts,
                user_id_str=user_id_str,
                update_db_flag=False,
            )
            # Update flag on the request session directly
            roadmap.cognee_seeded = True
            await session.commit()
        else:
            # Regeneration: fire as background task, use separate session for flag update
            asyncio.create_task(
                _seed_cognee_memory(
                    roadmap_id=roadmap.id,
                    roadmap_title=roadmap.title,
                    roadmap_user_id=str(roadmap.user_id),
                    roadmap_opportunity_id=str(roadmap.opportunity_id),
                    roadmap_summary=roadmap.summary or "",
                    created_steps=step_dicts,
                    user_id_str=user_id_str,
                    update_db_flag=True,
                )
            )

    # 7. Return Roadmap with Steps
    await session.refresh(roadmap, attribute_names=["steps"])
    if roadmap.steps:
        roadmap.steps.sort(key=lambda s: s.order_index)

    logger.info("PERF: [TOTAL_GENERATION] %.3fs (first=%s)", time.perf_counter() - t_total_start, is_first_generation)
    return roadmap
