# Waypoint

An AI career-opportunity agent with real, adaptive memory.

Waypoint ingests opportunities from five different sources — GitHub good-first-issues (global search + featured repos), Devpost hackathons, Arbeitnow job postings, RemoteOK remote jobs, and Remotive remote jobs — and generates a personalized, step-by-step roadmap for each one. As you work through a roadmap and mark steps done or rejected, Waypoint feeds that feedback into Cognee's memory lifecycle (remember → recall → improve → forget), and the roadmap visibly reorders itself: steps that worked for you float up, steps you rejected sink to the bottom.

Built for the Cognee Hackathon 2026.

---

## Table of contents

- [Quickstart](#quickstart)
- [End-to-end walkthrough](#end-to-end-walkthrough)
- [What it does](#what-it-does)
- [Why Cognee, and how we actually use it](#why-cognee-and-how-we-actually-use-it)
- [Architecture](#architecture)
- [Tech stack](#tech-stack)
- [Project structure](#project-structure)
- [Environment variables](#environment-variables)
- [API overview](#api-overview)
- [The memify feedback loop, end to end](#the-memify-feedback-loop-end-to-end)
- [Known limitations & honest caveats](#known-limitations--honest-caveats)
- [Testing](#testing)
- [Roadmap / what's next](#roadmap--whats-next)
- [Credits](#credits)

---

## Quickstart

Get the full stack running locally in under 10 minutes.

### Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.11+ | |
| Node 18+ | |
| A PostgreSQL database | Supabase recommended — you need RLS support |
| An OpenRouter API key | Free tier works — see [Getting an OpenRouter API key](#3-getting-an-openrouter-api-key) if you don't have one yet |

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

Create `.env` from the example:

```bash
cp .env.example .env
```

Fill in these required variables in `.env` (everything else — Cognee config, embeddings, encryption keys — already has sane defaults):

| Variable | What to put |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@host:5432/dbname` |
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_JWT_SECRET` | Supabase → Settings → API → JWT Secret |
| `SUPABASE_ANON_KEY` | Supabase → Settings → API → anon public key |
| `LLM_API_KEY` | Your OpenRouter API key (`sk-or-...`) |
| `GITHUB_TOKEN` | A GitHub personal access token — required for production GitHub ingestion; without it you're capped at 60 req/hr |

Then run:

```bash
alembic upgrade head
uvicorn app.main:app --reload
```

### 2. Frontend

```bash
cd frontend/career-agent
npm install
npm run dev
```

Open `http://localhost:5173`. The frontend talks to the backend at `http://localhost:8000` by default.

### 3. Getting an OpenRouter API key

1. Go to [openrouter.ai](https://openrouter.ai) and sign up.
2. Navigate to **Keys → Create Key**.
3. Copy the `sk-or-...` value into `LLM_API_KEY` in your `.env`.

Free-tier models (e.g. `openai/gpt-4o-mini`) work out of the box. Users can also bring their own key (BYOK) via the app itself — encrypted at rest with pgcrypto, never stored in plaintext.

### 4. Validate the Cognee lifecycle

```bash
cd backend
python scripts/cognee_spike.py
```

This runs all nine lifecycle steps (remember, recall, positive/negative feedback, improve, recall-with-feedback, forget) against a scratch dataset and should log `PASS` for each. **Don't build on top of this until it does** — see [Known limitations](#known-limitations--honest-caveats) for why this matters.

> **Windows users:** if async Cognee/LLM calls fail with a DNS-looking error even though plain HTTP requests work, run `pip uninstall aiodns -y`. It's incompatible with `ProactorEventLoop` and is usually pulled in as a transitive dependency, not something you installed on purpose.

---

## End-to-end walkthrough

Once both servers are running, open `http://localhost:5173` and follow these steps in order.

**Step 1 — Sign up or log in**
Click **Sign Up** in the nav bar. A four-step stepper walks you through:
1. Create a Supabase Auth account (email + password)
2. Set your display name and username
3. Enter your technical skills (comma-separated — quick-add pills exist for React, TypeScript, Python, etc.)
4. Write a brief experience summary & career goals

All four steps submit together in a single `POST /api/profile/seed` call on the last step. Already have an account? Click **Log In** instead.

**Step 2 — (Optional) Connect your own API key**
Click **`LLM: nemotron-3-super (free)`** in the nav bar to open the BYOK modal. Paste your OpenRouter key, and optionally set a custom model ID/endpoint. It's encrypted at rest via PostgreSQL's `pgcrypto` (`pgp_sym_encrypt`) — never stored in plaintext. Leave every field blank to keep using the server default.

**Step 3 — Browse opportunities**
The dashboard loads opportunities from all five sources (GitHub good-first-issues, Devpost hackathons, Arbeitnow, RemoteOK, Remotive). Use the filter buttons — **All Opportunities / Jobs / Hackathons / GitHub Issues** — to narrow results, or click **Refresh** to re-fetch.

**Step 4 — Generate a roadmap**
Click **Roadmap →** on any opportunity card. Waypoint checks for a cached roadmap first; if none exists, the AI orchestrator generates one tailored to your profile and saves it to Cognee memory (you'll see a toast like *"Orchestrating career roadmap with ..."* while this runs).

**Step 5 — Work the roadmap, then watch it adapt**
For each step you can:
- Click **Mark Done** to accept it → triggers Cognee `improve()` with positive feedback
- Click **Not Relevant** to reject it → triggers Cognee `forget()`
- Click the pencil icon to edit the description, then **Save & Adapt** → feeds the edit diff back into Cognee

After you act on a step, Cognee's memory graph updates and the roadmap **reorders itself**: accepted steps rise, rejected steps sink. Adapted steps show a ✨ **adapted** badge.

> **Note:** when Cognee-native `recall()` is unavailable (see [Known limitations](#known-limitations--honest-caveats)), a Postgres-backed fallback handles the reordering instead — the behavior you see is the same either way.

---

## What it does

- **Ingest** — pulls live opportunities from five sources and normalizes them into one shared schema:
  - GitHub "good first issue" listings (global search + 10 featured repos like pytorch, vscode, godot)
  - Devpost hackathons
  - Arbeitnow job postings
  - RemoteOK remote jobs
  - Remotive remote jobs
- **Generate** — an AI orchestrator (a plain `while` loop using the OpenAI SDK against OpenRouter, no agent framework) builds a structured roadmap of steps for whichever opportunity a user selects, tailored to their profile. If both LLM calls fail, it falls back to a dynamic heuristic roadmap flagged with `is_synthetic_fallback=True` in the API response.
- **Remember** — every opportunity, roadmap, and step is written into Cognee's memory graph, scoped per-user for personal data and shared for public opportunity data.
- **Adapt** — when a user marks a step done (accept) or rejected, that feedback is scored and pushed through Cognee's `improve()` call. The next `recall()` reflects the updated weighting, and the roadmap's step order updates to match — accepted steps rise, rejected steps fall to the bottom.
- **BYOK** — users bring their own LLM key via OpenRouter; keys are encrypted at rest with pgcrypto, never stored in plaintext.

---

## Why Cognee, and how we actually use it

Most "AI memory" demos are a vector database with extra steps. Waypoint uses Cognee's actual lifecycle, not just similarity search:

| Cognee call | What Waypoint uses it for |
|---|---|
| `cognee.remember(data, dataset_name, session_id)` | Writes opportunities (shared), user profiles, roadmaps, and steps (user-scoped) into the memory graph |
| `cognee.recall(query_text, datasets, top_k, feedback_influence)` | Retrieves relevant prior steps/context, weighted by past feedback |
| `cognee.improve(dataset, session_ids)` | Applies accumulated step feedback into the graph so future recalls reflect it |
| `cognee.forget(data_id, dataset, everything, memory_only)` | Granular deletion — used for both targeted cleanup and full-reset flows |
| `cognee.FeedbackEntry(qa_id, feedback_score, feedback_text)` | Scores a specific recalled item as accepted (+1) or rejected (-1) |

The feedback loop that powers the reorder animation, concretely:

```python
recall(query, session_id=sid)                       # get scoped QA entries
remember(FeedbackEntry(qa_id=..., feedback_score))   # score a step's outcome
improve(dataset, session_ids=[sid])                  # fold the feedback into the graph
recall(query, feedback_influence=0.5)                # ranking now reflects the feedback
```

All type-based filtering happens through `dataset_name` isolation and `recall(datasets=[...])` — Cognee's `remember()` has no `node_set` parameter (only `memify()` does), so datasets are the unit of separation.

**Dataset naming convention:**
- Shared public data (opportunities): bare literal name, e.g. `dataset_name="issue"`, `"hackathon"`, `"job"` — no `user_id`.
- User-scoped data (profiles, roadmaps, steps): `{user_id}_{data_type}`, e.g. `abc123_user_profile`, `abc123_step`.

---

## Architecture

```
┌─────────────────────┐        ┌──────────────────────────┐
│   React 19 Frontend  │◄──────►│   FastAPI Backend        │
│  (Vite, TS, vanilla  │  REST  │                          │
│   CSS, no Tailwind)  │        │  ┌────────────────────┐  │
└─────────────────────┘        │  │ Orchestrator        │  │
                                │  │ (OpenAI SDK tool-use│  │
                                │  │ loop via OpenRouter) │  │
                                │  └─────────┬──────────┘  │
                                │            │             │
                                │  ┌─────────▼──────────┐  │
                                │  │ Cognee memory client │ │
                                │  │ remember/recall/     │ │
                                │  │ improve/forget        │ │
                                │  └─────────┬──────────┘  │
                                │            │             │
                                └────────────┼─────────────┘
                                             │
                       ┌─────────────────────┼─────────────────────┐
                       ▼                     ▼                     ▼
              PostgreSQL (Supabase)   Cognee (LanceDB +      OpenRouter (BYOK)
              roadmaps, steps,        KuzuDB + SQLite,       LLM + embeddings
              profiles, RLS           local by default)
```

Single orchestrator, five role-scoped system prompts — ingestion, roadmap generation, outreach, resource suggestions, and the memory/Cognee-client role — rather than five separate services. Roadmap generation itself has three prompt variants (job / hackathon / issue) sharing the same tool definitions, so the model's framing changes per opportunity type without duplicating the schema or the tool-use loop.

**Why no LangChain/CrewAI:** the tool-use loop is a plain `while` loop — call the model via `llm_client.chat.completions.create()`, check for `tool_calls` in the response, execute them, append tool role results, repeat. At this project's scope, a framework adds more debugging surface than it saves.

**Ingestion pipeline:** all five sources (GitHub, Devpost, Arbeitnow, RemoteOK, Remotive) follow the same pattern: `fetch()` → `normalize()` → `opportunity_to_dict()` → `remember()`. A batch script (`scripts/ingest_all_sources.py`) runs all sources concurrently via `asyncio.gather`, with each source independently try/except'd so one failure never blocks the others.

---

## Tech stack

**Backend**
- FastAPI, async SQLAlchemy, Alembic migrations
- PostgreSQL via Supabase, with row-level security (RLS)
- Supabase Auth (JWT) for `get_current_user`
- Cognee (v1.2.2) for memory lifecycle — LanceDB (vector), KuzuDB (graph), SQLite (metadata) locally by default
- OpenAI SDK (`AsyncOpenAI`) against OpenRouter for the orchestrator tool-use loop
- OpenRouter for BYOK model routing; keys encrypted with pgcrypto

**Frontend**
- Vite + React 19 + TypeScript
- Vanilla CSS (design tokens, no Tailwind)
- `react-router-dom` for routing
- GSAP ScrollTrigger for the landing-page branch narrative
- Custom, dependency-free scramble-text and 3D tilt/flip components (no paid animation plugins)

**Infra**
- Frontend: Vercel
- Backend: Railway / Render

---

## Project structure

```
backend/
  app/
    main.py                     # FastAPI app, lifespan, CORS, health check
    config.py                   # Pydantic Settings, loads .env from root or backend/
    db/
      session.py                # async engine + sessionmaker
      models.py                 # Opportunity, Roadmap, Step, UserProfile
    auth/
      supabase.py               # get_current_user JWT dependency
    memory/
      cognee_client.py          # remember/recall/improve/forget wrapper
      queries.py                # type-scoped recall helpers
    ingestion/
      github_issues.py          # good-first-issues fetch + normalize (global + featured repos)
      devpost_hackathons.py     # hackathon fetch + normalize
      arbeitnow_jobs.py         # job fetch + normalize
      remoteok_jobs.py          # RemoteOK job fetch + normalize
      remotive_jobs.py          # Remotive job fetch + normalize
    agents/
      orchestrator.py           # OpenAI SDK tool-use loop, Postgres + Cognee persistence
      tools.py                  # create_roadmap, create_step, append_resources, draft_outreach
      prompts/
        ingestion.py
        devpost.py
        arbeitnow.py
        remoteok.py
        remotive.py
        roadmap_job.py
        roadmap_hackathon.py
        roadmap_issue.py
    api/
      routes_auth.py
      routes_opportunities.py
      routes_roadmap.py
      routes_feedback.py
  alembic/
    versions/                   # schema + RLS migrations
  scripts/
    cognee_spike.py             # standalone Cognee lifecycle validation
    ingest_all_sources.py       # batch ingestion: all 5 sources concurrently
    test_phase6_validation.py   # feedback → improve → reorder e2e check
  tests/
    test_github_issues.py
    test_devpost_hackathons.py
    test_arbeitnow_jobs.py
    test_remoteok_jobs.py
    test_remotive_jobs.py

frontend/career-agent/
  src/
    api.ts                      # fetchRoadmapByOpportunity, submitStepEdit, etc.
    App.tsx                     # routing, cache-first opportunity selection
    components/
      StepItem.tsx              # inline edit mode: Accept / Improve / Cancel
      StaggeredMenu.tsx
      Footer.tsx / ScrambledText.tsx
    pages/
      RoadmapView.tsx
      ProfilePage.tsx
      LandingPage.tsx
      AboutPage.tsx

docs/
  AGENT.md / PRODUCT.md / DESIGN.md
  SESSION_CONTEXT.md            # append-only build log
.clinerules                     # agent entry-point contract (guardrails)
```

---

## Environment variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname

# Supabase Auth
SUPABASE_URL=
SUPABASE_JWT_SECRET=
SUPABASE_ANON_KEY=
ENABLE_BACKEND_ACCESS_CONTROL=true    # set false for local dev without real auth

# Cognee — bare names, NOT COGNEE_LLM_* prefixed
LLM_PROVIDER=custom
LLM_MODEL=openrouter/openai/gpt-4o-mini
LLM_ENDPOINT=https://openrouter.ai/api/v1
LLM_API_KEY=sk-or-...
EMBEDDING_MODEL=openrouter/openai/text-embedding-3-large
COGNEE_SKIP_CONNECTION_TEST=true

# GitHub — strongly recommended for production use
# Without a token, GitHub search is limited to 60 requests/hour.
# With a token, you get 5,000 requests/hour.
GITHUB_TOKEN=
```

---

## API overview

| Method | Route | Purpose |
|---|---|---|
| `POST` | `/api/profile/seed` | Create/seed a user profile |
| `GET` | `/api/opportunities` | List normalized opportunities across all five sources |
| `POST` | `/api/roadmaps` | Generate a roadmap for an opportunity (checks cache first unless `force_regenerate=true`) |
| `GET` | `/api/roadmaps/{id}` | Fetch a roadmap with its ordered steps |
| `GET` | `/api/roadmaps/by-opportunity/{opportunity_id}` | Cache lookup — returns existing roadmap without regenerating |
| `POST` | `/api/steps/{id}/feedback` | Mark a step done/rejected; triggers Cognee `improve()` |
| `POST` | `/api/steps/{id}/edit` | Accept (save only) or Improve (save + feed diff into `cognee.improve()`) |

`POST /api/roadmaps` checks the database for an existing roadmap before invoking the orchestrator at all — regenerating on every click was the single biggest performance problem early on (15–30 minutes per click); a cache hit is now a ~200ms read.

The roadmap response includes an `is_synthetic_fallback` boolean — when `true`, it means the LLM failed (timeout or rate limit) and the roadmap was generated from a heuristic template using the opportunity's actual fields. This is the honesty mechanism: the API never silently passes off synthetic data as LLM-generated.

---

## The memify feedback loop, end to end

1. User marks a step done or rejected in the UI.
2. `routes_feedback.py` scores the step (+1 / -1) and calls `cognee.improve()` for that user's session.
3. On the next roadmap fetch, recalled items are matched against current steps using exact significant-title-word overlap (stop-words filtered; ≥2 matching words, or 1 if the title is single-word) — this exactness matters, because loose keyword matching will make every step look "memified" and the reorder will look like it did nothing.
4. Matched-positive steps get `is_memified=True` and a positive `recall_weight`; matched-negative (rejected) steps get `is_memified=False` and a negative weight, which demotes them to the bottom; unmatched steps get `recall_weight=0.0` and sit at neutral position.
5. Steps are re-sorted by weight and persisted back to Postgres with updated `order_index` values — the reorder is not just a UI animation, it's a real, durable change to step order.

Example of the actual instrumented output from a validation run:

```
Order 1: 'Set Up Development Environment...'        | is_memified=True  | recall_weight=1.0
Order 2: 'Reproduce Connection Timeout Issue...'     | is_memified=True  | recall_weight=1.0
Order 3: 'Add Unit and Integration Tests...'         | is_memified=False | recall_weight=0.0
Order 4: 'Validate Fix, Document Changes...'         | is_memified=False | recall_weight=0.0
Order 5: 'Implement Exponential Backoff Retry Logic' | is_memified=False | recall_weight=-1.0
```

---

## Known limitations & honest caveats

We'd rather you read this than find it out mid-demo:

- **Cognee-native `recall()` has not been observed succeeding end-to-end** in this project. It has been blocked, in sequence, by free-tier rate limits during `cognify()`'s internal entity extraction, and later by an organization-level LLM provider budget cap (`403 Budget limit exceeded`). When this happens, `recall()` times out or raises `EntityNotFoundError` ("empty graph projected").
- **A Postgres-backed fallback recall is the current, intentional demo path.** When Cognee's native recall is unavailable, the system queries the user's own step history directly from Postgres and uses that as the memory source for reordering. This is a deliberate resiliency design, not a bug — but it means the memify demo, as currently deployed, is not guaranteed to be running on live Cognee-native retrieval at any given moment. We do not claim live Cognee-native retrieval in the demo narrative — we describe Cognee as handling memory writes and graph construction via `remember()`/`cognify()`, with a Postgres-backed fallback for recall under provider constraints.
- **Synthetic fallback roadmaps are flagged, not hidden.** When both LLM calls fail (timeout or rate limit), the orchestrator generates a dynamic heuristic roadmap using the opportunity's actual fields (title, description, language, labels) and sets `is_synthetic_fallback=True` on the API response. The frontend does not currently distinguish these visually, but the flag is available to any consumer of the `/api/roadmaps` endpoint. This is an honesty mechanism: the system never silently passes off synthetic data as LLM-generated.
- **Auth flow (multi-step signup) was deliberately deprioritized** to protect demo stability close to the deadline. Core flows (profile, opportunities, roadmap generation, feedback) do not depend on it.
- **The `cognee_seeded` migration was applied manually once** (`ALTER TABLE roadmaps ADD COLUMN cognee_seeded BOOLEAN DEFAULT FALSE`) before a proper Alembic migration was generated — if you're setting up fresh, `alembic upgrade head` should already include this; if you're migrating an older local DB, double check.

> Before any live demo, we recommend confirming at least one real, successful Cognee-native `recall()` — not just the Postgres fallback — so you can speak to both paths honestly.

---

## Testing

```bash
# from repo root or backend/
pytest -v
```

Covers ingestion normalization and Cognee-write mocking for all five opportunity sources (GitHub, Devpost, Arbeitnow, RemoteOK, Remotive), plus a live-flavored end-to-end feedback/reorder validation script:

```bash
python backend/scripts/test_phase6_validation.py
```

TypeScript compiles cleanly with:

```bash
cd frontend/career-agent
npx tsc --noEmit
```

---

## Roadmap / what's next

- Confirm and document a successful Cognee-native `recall()` run (not just the Postgres fallback) ahead of any live demo
- Surface synthetic fallback state in the frontend UI (the `is_synthetic_fallback` flag already exists in the API response)
- Complete the auth flow (four-step signup: credentials → identity → skills → summary) as a post-deadline follow-up
- Parallelize/cache GitHub issue status verification in the opportunities listing route

---

## Credits

Built solo for the Cognee Hackathon 2026, using Cognee for the memory lifecycle, the OpenAI SDK against OpenRouter for orchestration, and OpenRouter for BYOK model routing. See `docs/SESSION_CONTEXT.md` for the full, append-only build log across every development session.
