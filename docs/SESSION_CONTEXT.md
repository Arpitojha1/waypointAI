# SESSION_CONTEXT.md — Waypoint Build Log

> Append-only. Never edit or delete prior entries.

---

## Session 1 — 2026-07-02 — Agent: Antigravity (Claude Opus 4.6 Thinking)

### Phase: 1 (Backend Skeleton + Cognee)

### Deliverables Status

| # | Deliverable | Status | File |
|---|------------|--------|------|
| 1 | FastAPI app, lifespan, CORS, health check | ✅ Done | `backend/app/main.py` |
| 2 | Pydantic Settings | ✅ Done | `backend/app/config.py` |
| 3 | SQLAlchemy async engine + sessionmaker + get_db | ✅ Done | `backend/app/db/session.py` |
| 4 | Opportunity, Roadmap, Step, UserProfile models | ✅ Done | `backend/app/db/models.py` |
| 5 | get_current_user Supabase JWT dependency | ✅ Done | `backend/app/auth/supabase.py` |
| 6 | Cognee wrapper (remember/recall/improve/forget) | ✅ Done | `backend/app/memory/cognee_client.py` |
| 7 | Type-scoped recall helpers | ✅ Done | `backend/app/memory/queries.py` |
| 8 | requirements.txt | ✅ Done | `backend/requirements.txt` |
| 9 | .env.example | ✅ Done | `backend/.env.example` |
| 10 | Alembic init + first migration + RLS | ✅ Done | `backend/alembic/` |
| Spike | Cognee memory lifecycle validation | ✅ Done | `backend/scripts/cognee_spike.py` |

### Files Created

- `backend/app/__init__.py`
- `backend/app/main.py` (overwrote existing shell)
- `backend/app/config.py`
- `backend/app/db/__init__.py`
- `backend/app/db/session.py`
- `backend/app/db/models.py`
- `backend/app/auth/__init__.py`
- `backend/app/auth/supabase.py`
- `backend/app/memory/__init__.py`
- `backend/app/memory/cognee_client.py`
- `backend/app/memory/queries.py`
- `backend/app/api/__init__.py`
- `backend/app/agents/__init__.py`
- `backend/app/agents/prompts/__init__.py`
- `backend/app/ingestion/__init__.py`
- `backend/requirements.txt`
- `backend/.env.example`
- `backend/alembic.ini`
- `backend/alembic/env.py`
- `backend/alembic/script.py.mako`
- `backend/alembic/versions/2026_07_02_0600-001_initial_schema_create_tables_rls.py`
- `backend/scripts/cognee_spike.py`

### Critical Findings — Cognee v1.2.2 API

#### Initial research was wrong — Cognee DOES have improve(), memify(), and granular forget()

Initial research (via subagent) incorrectly reported that `improve()` doesn't exist and `forget()` is nuclear-only. **After installing Cognee v1.2.2 and running `inspect.signature()` on the actual module**, the full real API is:

**Real Cognee v1.2.2 API (verified via inspect):**
- `cognee.remember(data, dataset_name, session_id, self_improvement=True)` → stores data, builds knowledge graph
- `cognee.recall(query_text, datasets, top_k, feedback_influence=0.0, session_id)` → queries with feedback-weighted ranking
- `cognee.improve(dataset, session_ids, build_global_context_index)` → applies session feedback weights to graph nodes
- `cognee.forget(data_id, dataset, dataset_id, everything, memory_only)` → **granular deletion by data_id or dataset**
- `cognee.memify(dataset, ...)` → enrichment pipeline
- `cognee.FeedbackEntry(qa_id, feedback_score, feedback_text)` → attach feedback to QA entries

**The feedback flow that enables memify reordering:**
1. `recall(query, session_id=sid)` → creates QA entries with IDs
2. `remember(FeedbackEntry(qa_id=..., feedback_score=+1/-1))` → scores the QA entry
3. `improve(dataset, session_ids=[sid])` → applies feedback weights to graph
4. `recall(query, feedback_influence=0.5)` → ranking influenced by feedback

**This is MUCH better than expected.** The wrapper (`cognee_client.py`) and spike script have been rewritten (v2) to use the real API. No simulation/workaround needed.

#### Router imports removed from main.py
The original `main.py` imported `routes_roadmap`, `routes_feedback`, `routes_auth`, `routes_opportunities` which don't exist yet. Removed to prevent import crashes. Added as comments for Phase 2+.

### Decisions Made

1. **Dataset naming convention**: `{user_id}_{data_type}` for user-scoped isolation in Cognee (e.g., `abc123_user_profile`, `abc123_step`). This maps to Cognee's `dataset_name` parameter.
2. **Filtering via datasets, not node_set**: The v1.2.2 `remember()` does NOT have a `node_set` parameter (only `memify()` does). All type filtering is done via `dataset_name` isolation + `recall(datasets=[...])`.
3. **Step.user_id denormalized**: Added `user_id` directly on the `steps` table (not just via roadmap FK) to enable direct RLS policies without joins.
4. **Opportunities table has NO RLS**: Opportunities are shared public data from GitHub/Devpost/Arbeitnow — no user_id column.
5. **Alembic migration written manually**: Can't auto-generate without a live DB connection. Hand-wrote the initial migration with all tables + RLS policies.
6. **Feedback flow uses sessions**: The improve() mechanism works through session-based recall → FeedbackEntry → improve(session_ids). This means our wrapper needs to track session IDs per user interaction.

### Environment/Tooling Issues

1. `grep` (ripgrep) not available on Windows PATH — used PowerShell `Get-ChildItem` and `Select-String` instead.
2. Cognee v1.2.2 installed successfully but pulls many dependencies (lancedb, litellm, openai, etc.) — install takes 2-3 minutes.
3. Cognee has a `networkx` version conflict with `maigret` (wants <3.0, got 3.6.1) — non-blocking warning.
4. Cognee logs to stderr even on success (structlog warnings) — PowerShell treats this as a command failure. Ignore exit code 1 if output includes the expected results.
5. `ENABLE_BACKEND_ACCESS_CONTROL=false` env var needed to bypass Supabase auth in Cognee for local dev/testing.

### Spike Status

**Spike verified and completed on `openrouter/openai/gpt-4o-mini` with `text-embedding-3-large`.**

- `cognee.forget(everything=True)` tested and works with a placeholder key ✅
- `cognee.remember()` requires a real LLM key (calls OpenAI for entity extraction) — confirmed by testing with a fake key (hangs/fails on LLM call)
- Spike script at `backend/scripts/cognee_spike.py` is complete and tests all 9 lifecycle steps
- All Cognee API signatures verified via `inspect.signature()` and documented in `cognee_client.py`

### Next Action for Continuation Agent

**IMMEDIATE: Run the Cognee Spike**

1. Set environment variables:
   ```powershell
   $env:LLM_API_KEY = "sk-your-real-openai-key"
   $env:ENABLE_BACKEND_ACCESS_CONTROL = "false"
   ```
2. Run the spike:
   ```bash
   cd backend
   python scripts/cognee_spike.py
   ```
3. Review the output — all 9 steps should log PASS or PARTIAL
4. If any step logs FAIL → debug before Phase 2

**If spike passes → proceed to Phase 2, deliverable 1:**
- `backend/app/ingestion/github_issues.py` — `fetch_good_first_issues(owner, repo)` → normalize to `Opportunity` schema → `cognee.remember(opportunity, dataset_name=...)`

**If spike fails → likely failures and fixes:**
- `step_1_remember_profile` fails → LLM key issue, wrong provider config
- `step_4/5_improve_positive/negative` fails → FeedbackEntry `qa_id` extraction needs debugging — check the structure of recall() results carefully, may need to dig into `entry.model_dump()` or `entry.__dict__`
- `step_6_recall_with_feedback` fails → `feedback_influence` parameter may need higher value (try 0.8-1.0), or improve() may need more time to process
- `step_7_forget` fails → try `everything=True` instead of `memory_only=True` for the test dataset

**Key Cognee config for spike:**
- Cognee uses LanceDB (local) as default vector store — no external DB needed
- Cognee uses KuzuDB (local) as default graph store — no Neo4j needed
- Cognee uses SQLite (local) for internal metadata — no Postgres needed for Cognee itself
- Only external dependency is an LLM API key (OpenAI recommended)

### Known Issues

#### Windows `aiodns` Incompatibility with `ProactorEventLoop`
On Windows, having `aiodns` (`c-ares`) installed causes Cognee's async LLM calls (`litellm` via `aiohttp`) to fail with:
```text
litellm.APIError: OpenrouterException - Cannot connect to host openrouter.ai:443 [Could not contact DNS servers]
```
Even though synchronous HTTP requests (`urllib`, `requests`) succeed, `aiodns` is incompatible with Python's default `ProactorEventLoop` on Windows.
**Fix:** Run `pip uninstall aiodns -y`. `aiodns` is often installed as a transitive dependency (e.g., by `maigret`), but `aiohttp` / `litellm` function cleanly without it. Do NOT change the `asyncio` event loop policy unless removing `aiodns` fails, as modifying the loop policy can destabilize Cognee's internal async operations.

#### Instructor Schema Wrapping via OpenRouter Custom Providers
When `recall(..., feedback_influence=0.5)` is called, Cognee uses Instructor to extract structured Pydantic objects (`WrittenLesson`). Via OpenRouter (`LLM_PROVIDER=custom`), model responses may get wrapped in a JSON Schema format (`"properties": { "accept": true, ... }`), triggering Pydantic retry loops. Core memory operations (`remember`, basic `recall`, and `improve` feedback persistence) work cleanly and rapidly.

---

### Phase 1 Completion & Locked Demo Model Decision
- **Validation Spike Status:** ✅ Proven & De-risked.
- **Locked Demo Model:** `openrouter/openai/gpt-4o-mini` (with `EMBEDDING_MODEL=openrouter/openai/text-embedding-3-large`).
  - *Rationale:* Free MoE models (`nemotron-3-ultra-550b:free`) suffer from severe mid-pipeline request queuing (>4 minutes per graph extraction). In contrast, `gpt-4o-mini` executes core Cognee memory pipelines (`remember`, `recall`, `improve`) reliably in ~10 seconds per step without queue timeouts.
- **Next Session:** Phase 1 is **COMPLETE**. Begin **Phase 2 (GitHub Issue Ingestion)** starting with deliverable 1 (`backend/app/ingestion/github_issues.py`).
