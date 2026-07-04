
Waypoint: An Open Guide to Shipping a Real Cognee Memory Product Under Hackathon Pressure

*Everything I learned building an AI career-opportunity agent on Cognee's full memory lifecycle — the working decisions, the dead ends, the exact error messages, and the config nobody documents. Take all of it.*

---

## Why this guide exists

I built **Waypoint** for the Cognee Hackathon: an agent that ingests GitHub "good first issues," Devpost hackathons, and Arbeitnow job postings, then generates a personalized roadmap for each opportunity — and *adapts that roadmap live* when you accept or reject a step, using Cognee's `remember → recall → improve → forget` lifecycle instead of a single vector-search bolt-on.

That last part — a visible, judge-facing "the memory actually changed the plan" moment — is the single highest-leverage thing you can build if you're using Cognee for a hackathon. It's the difference between "we used an embeddings database" and "we built something with memory." I'm writing this the way I wish someone had written it for me: warts included, so you don't burn your runway on the same dead ends I did.

If you only read one section, read **"The memify reorder is your demo, build backward from it"** and **"The Cognee gotchas nobody puts in the README."**

---

## Part 1 — What Waypoint actually is

**The pitch:** three heterogeneous opportunity sources (issues, hackathons, jobs) get normalized into one shared schema, each opportunity gets an AI-generated step-by-step roadmap, and every time a user marks a step done or rejects it, that feedback is written into Cognee, `improve()` re-weights the graph, and the next `recall()` visibly reorders the remaining steps — good steps float up, rejected steps sink to the bottom.

**The architecture, in one paragraph:** FastAPI + PostgreSQL (via Supabase) on the backend, Vite + React 19 + TypeScript + Tailwind on the frontend, a raw Anthropic SDK tool-use loop for orchestration (no LangChain, no CrewAI — I'll defend that choice below), BYOK model routing through OpenRouter with pgcrypto-encrypted keys, and Cognee handling the memory lifecycle underneath it all.

### The architectural decisions I'd make again

These were locked early and never revisited, which is exactly what let me move fast later:

- **One orchestrator, five role-scoped system prompts** (ingestion, roadmap, outreach, resource, memory/Cognee-client) — not five separate microservices. A hackathon judge does not care about your service mesh. A single tool-use loop with well-separated *prompts* gets you 90% of the architectural clarity of "agents" with 10% of the deployment pain.
- **One shared `Opportunity` / `Roadmap` / `Step` schema across all three opportunity types.** Don't build a `GithubOpportunity` and a `HackathonOpportunity` and a `JobOpportunity`. You will regret every hour spent on that divergence when you get to roadmap generation, which should not care where the opportunity came from.
- **Raw Anthropic SDK tool-use loop, no agent framework.** For a project this size, LangChain/CrewAI add abstraction overhead you'll spend more time debugging than you save. A `while` loop that calls the API, checks for `tool_use` blocks, executes them, and appends `tool_result` blocks back into messages is maybe 80 lines of code and you understand every line of it at 2 AM.
- **BYOK via OpenRouter with pgcrypto encryption.** Letting judges/users bring their own key both solves your API cost problem and demonstrates you understand production security concerns (not storing plaintext keys).
- **`dataset_name` convention: `{user_id}_{data_type}`** for anything user-scoped, and a *bare* literal string (`"issue"`, `"hackathon"`, `"job"`) for shared public data with no `user_id` at all. Opportunities themselves are public — don't scope them per-user in Cognee; only profiles, roadmaps, and steps are user data.
- **Pre-designate a cut line.** I flagged the outreach/resource roles as "first thing to cut if the deadline gets tight" *before* I needed to cut anything. Decide what's non-essential while you're calm, not while you're panicking on day 5.

### What I scoped out, on purpose

Don't build these unless you have real time slack, which you won't:

- An interactive react-flow knowledge-graph visualization as your primary UI. It looks incredible in a "look what we could build" sense and contributes almost nothing to "does the memory feature actually work." Judges reward working demos over pretty static-content viewers.
- Five separate agent *services*. One orchestrator process, multiple prompts.
- A skills/certifications graph as a separate data model. Fold it into the profile.
- Any monetization layer. Nobody is judging your business model on day 5.

---

## Part 2 — Understanding Cognee's real API (do this before you write a line of app code)

Here's the first lesson that will save you the most time: **don't trust secondhand summaries of Cognee's API, including ones an AI subagent gives you.** My first research pass (done by a subagent) reported that `improve()` didn't exist and that `forget()` was nuclear-only (delete-everything). Both were wrong. The actual, verified-via-`inspect.signature()` API in Cognee v1.2.2 is much richer:

```python
cognee.remember(data, dataset_name, session_id, self_improvement=True)
# stores data, builds the knowledge graph

cognee.recall(query_text, datasets, top_k, feedback_influence=0.0, session_id)
# queries with feedback-weighted ranking

cognee.improve(dataset, session_ids, build_global_context_index)
# applies session feedback weights to graph nodes

cognee.forget(data_id, dataset, dataset_id, everything, memory_only)
# GRANULAR deletion by data_id or dataset — not just nuke-everything

cognee.memify(dataset, ...)
# enrichment pipeline

cognee.FeedbackEntry(qa_id, feedback_score, feedback_text)
# attaches a feedback score to a specific QA entry
```

**Do this yourself before you build anything:**

```python
import inspect, cognee
print(inspect.signature(cognee.remember))
print(inspect.signature(cognee.recall))
print(inspect.signature(cognee.improve))
print(inspect.signature(cognee.forget))
```

Five minutes of this will save you a day of building around an imagined API surface.

### The feedback loop that actually powers the "memify reorder" demo moment

This is the core mechanic. Internalize it — it's four calls, in this order:

1. `recall(query, session_id=sid)` → returns QA entries, each with an ID
2. `remember(FeedbackEntry(qa_id=..., feedback_score=+1 or -1))` → scores that QA entry
3. `improve(dataset, session_ids=[sid])` → applies the feedback weight into the graph
4. `recall(query, feedback_influence=0.5)` → ranking is now visibly influenced by the feedback

If you get nothing else from this guide: build a tiny standalone spike script that runs exactly these four steps against a toy dataset *before* you write any FastAPI routes. Verify each step logs PASS. This is your foundation; don't build the house before you've tested it.

### Two more API-shape facts that matter

- `remember()` does **not** have a `node_set` parameter — only `memify()` does. All type filtering has to happen through `dataset_name` isolation plus `recall(datasets=[...])`. Don't go looking for a filtering param that isn't there.
- `remember()` auto-runs `add()` + `cognify()` internally when you don't pass a `session_id`. You do not need to call `cognify()` yourself in the common path — one less moving part to worry about.

---

## Part 3 — The Cognee gotchas nobody puts in the README

This is the section that will save you the most hours. Every one of these cost me real debugging time.

### 1. Cognee's config env vars are bare, not prefixed
It's `LLM_PROVIDER`, `LLM_MODEL`, `LLM_ENDPOINT`, `LLM_API_KEY` — **not** `COGNEE_LLM_*`. This is the single most common "why is it silently falling back to defaults" bug.

### 2. Wiring OpenRouter into Cognee requires four things together
- `LLM_PROVIDER=custom`
- an `openrouter/` prefix on the model name (e.g. `openrouter/openai/gpt-4o-mini`)
- an explicit `LLM_ENDPOINT`
- `COGNEE_SKIP_CONNECTION_TEST=true`

Miss any one of these and you'll get an opaque connection failure that looks like a network problem but is actually a config problem.

### 3. Free-tier rate limits hit Cognee's *internal* LLM calls, not just yours
`cognee.remember()` triggers its own entity-extraction LLM call under the hood, and `cognify()` does too. These count against the same provider quota as your application's own calls. If you're burning through a free tier faster than expected, this is why.

### 4. Free MoE models are a demo-reliability trap
I tried a free-tier model (`nemotron-3-ultra-550b:free`) first. It suffered severe mid-pipeline request queuing — over 4 minutes per graph extraction step, sometimes with no response at all. Switching the *entire pipeline* to `openrouter/openai/gpt-4o-mini` (paired with `openrouter/openai/text-embedding-3-large` for embeddings) got core Cognee operations (`remember`, `recall`, `improve`) down to roughly 10 seconds each, reliably. **Lock your demo model early and don't second-guess it under deadline pressure** — the "free" option is a false economy when your entire demo depends on latency.

### 5. Windows: `aiodns` breaks async LLM calls
If you're on Windows, having `aiodns` (c-ares) installed will make Cognee's async LLM calls (via `litellm`/`aiohttp`) fail with something like:
```
litellm.APIError: OpenrouterException - Cannot connect to host openrouter.ai:443 [Could not contact DNS servers]
```
even though plain synchronous requests work fine. This is an incompatibility with Python's default `ProactorEventLoop` on Windows. **Fix:** `pip uninstall aiodns -y`. It's usually pulled in transitively by an unrelated dependency. Don't touch the asyncio event loop policy to work around this — that's a much deeper rabbit hole and is unnecessary once `aiodns` is gone.

### 6. `DatasetNotFoundError` on first run is expected, not a bug
On a completely fresh Cognee install, calling `recall()` against a dataset that hasn't had anything written to it yet raises `DatasetNotFoundError`. This is Cognee correctly telling you the dataset doesn't exist in its SQLite metadata store yet — write something with `remember()` first.

### 7. `EntityNotFoundError` ("Empty graph projected... 404") almost always means your *provider* failed silently upstream
If `remember()` succeeds enough to register dataset metadata but the underlying `cognify()` entity-extraction call hits a rate limit or budget cap, you'll get a dataset that "exists" but has an empty graph. The `recall()` that follows will throw `EntityNotFoundError` with a 404-flavored message. This is not a Cognee bug — check your provider's dashboard for rate-limit or budget errors first.

### 8. Watch for a hard organization-level budget cap, separate from rate limits
Rate-limit errors are recoverable with backoff. A `403 Budget limit exceeded (monthly limit)` from your LLM provider is not — no amount of retrying fixes it, and every downstream Cognee call will keep failing until the cap resets or is raised. **Diagnose which one you're hitting before you spend an hour writing retry logic for the wrong problem.**

### 9. Build an honest fallback path, and say so in your demo narrative
Because of the above, I designed the recall path to gracefully fall back to a Postgres query of the user's own step history when Cognee's native recall times out or 404s. This is not a cop-out — it's a legitimate resiliency pattern, and I say exactly that to judges: *Cognee handles memory writes and graph construction via `remember()`/`cognify()`; when native recall is degraded by provider-side constraints, a Postgres-backed fallback preserves the reorder behavior without ever implying live Cognee-native retrieval that isn't actually happening.* Being precise about what's really running under the hood is worth more to technical judges than pretending everything is on the "happy path."

### 10. Cognee logs warnings to stderr even on success
On Windows especially, PowerShell will treat a non-zero exit code as failure even when your script's actual output shows every step passing. Check the printed output, not just the exit code, before you declare something broken.

### 11. Local-first storage by default — you don't need extra infra to spike Cognee
Out of the box, Cognee uses LanceDB (vectors), KuzuDB (graph), and SQLite (metadata) — all local. The only external dependency for a first spike is an LLM API key. Don't provision Postgres/Neo4j just to validate that Cognee's lifecycle works; do that validation first, cheaply, before you wire up your "real" database.

---

## Part 4 — Build order that actually works under a deadline

Here's the phase sequence I used, and *why* the order matters more than it looks like it should.

### Phase 0: Spike Cognee's lifecycle in total isolation
Before touching FastAPI, write one script that exercises all nine lifecycle operations against a scratch dataset: remember a profile, recall it, submit positive and negative feedback, run improve, recall again with `feedback_influence` set, and forget. If any step fails, you now know exactly which piece of the chain is broken, with zero application code in the way to confuse the diagnosis.

Likely failure points, ranked by frequency:
- Remembering fails → LLM key/provider config issue (see gotchas #1–2 above)
- Improve on positive/negative feedback fails → check how you're extracting `qa_id` from the recall result; you may need `entry.model_dump()` or to inspect `entry.__dict__` directly, since the object shape isn't always obvious
- Recall-with-feedback doesn't show any influence → try a stronger `feedback_influence` value (0.8–1.0) before assuming it's broken; also give `improve()` a moment before recalling again
- Forget fails → try `everything=True` instead of `memory_only=True` for the test dataset

### Phase 1: Backend skeleton + Cognee wrapper
FastAPI app skeleton, SQLAlchemy async engine, your shared `Opportunity`/`Roadmap`/`Step`/`UserProfile` models, a Supabase JWT auth dependency, and a thin Cognee wrapper module exposing `remember`/`recall`/`improve`/`forget`. Get Alembic initialized and your first migration written — even if you can't connect to a live DB yet, write the migration by hand so it's ready the moment you can.

### Phase 2–4: Ingestion, one source at a time
Build GitHub good-first-issues ingestion first (simplest, well-documented API), then Devpost, then Arbeitnow. Each source gets: a fetch function with rate-limit backoff, a normalizer into the shared `Opportunity` schema, and a `dataset_name` write into Cognee as **shared public data** (no `user_id`).

A few real quirks you'll hit:
- **GitHub's `/issues` endpoint returns pull requests too.** Filter anything with a `"pull_request"` key out of the results.
- **Unauthenticated GitHub is 60 requests/hour.** Handle `403`/`429` proactively, read `Retry-After` and `X-RateLimit-Reset` headers, and back off exponentially rather than crashing. Before a real demo run, get a `GITHUB_TOKEN` into your env.
- **Undocumented endpoints need a robots.txt check.** Devpost's lightweight `/api/hackathons` gallery endpoint is undiscovered-by-official-docs — I found it via network inspection. Its `robots.txt` allows general crawling but explicitly disallows AI-specific crawlers (`GPTBot`, `ChatGPT-User`, `anthropic-ai`, `Google-Extended`). Flag this kind of thing for human review rather than deciding unilaterally that it's fine.
- **Real API shapes rarely match your first guess.** Devpost's actual response has `submission_period_dates` and `time_left_to_submission`, not the `tagline`/`submission_deadline` fields I initially assumed. Build a fallback description generator from whatever fields *are* present rather than assuming a fixed shape, and validate against the live endpoint before you trust your mocks.
- **Arbeitnow, by contrast, is clean and documented** — a public, ToS-friendly job board API. Use it as your "this one just works" source to build momentum before tackling messier ones.

### Phase 5 (pre-flight): stop and verify before you build frontend
This is the check I'd tell anyone to steal directly: **before starting any frontend work, verify your orchestrator, your API routes, your live DB connection, and your Cognee spike are all real and unmocked.** I hit exactly this wall — my pre-flight check found the orchestrator, tool definitions, and all API routers simply didn't exist yet, and my `DATABASE_URL` was still the placeholder from `.env.example`. Catching that *before* wiring UI to fake data saved me from building an entire frontend against endpoints that didn't exist. If your DB connection string looks wrong or is unreachable, stop and fix that specifically — don't route around it with SQLite or mocks "just to keep moving." A demo built on a workaround has a way of falling over at the worst possible moment.

### Phase 3 (orchestrator): the actual AI loop
Once the DB is real:
- Write your tool definitions (`create_roadmap`, `create_step`, `append_resources`, `draft_outreach`, or whatever your equivalent is) as plain functions with JSON schemas, not framework abstractions.
- Write role-scoped system prompts per opportunity type (roadmap-for-job vs. roadmap-for-hackathon vs. roadmap-for-issue) — same tools, different framing.
- Write the orchestrator as a single `while` loop: call the model, check for `tool_use` blocks, execute them, append `tool_result` blocks, repeat until the model stops requesting tools.
- Wire it to Postgres (persist the roadmap/steps) *and* Cognee (`remember()` the opportunity + steps) in the same flow.
- Test end-to-end with real HTTP calls, not unit-test mocks, before calling this phase done. Seed a profile, generate a roadmap, submit feedback on a step, refetch the roadmap, and read the actual JSON response at each stage.

### Phase 6: the feedback loop, for real
Wire `POST /api/steps/{id}/feedback` to Cognee's `improve()`/`forget()` hooks. This is where the matching logic between "steps in your DB" and "items recalled from Cognee" has to be exact, or you'll get a demo that looks broken. My matching bug, concretely: naive keyword-intersection matching caused *every* recalled step to match with `recall_weight=1.0`, which made the reorder animation meaningless because nothing ever moved. The fix was requiring **exact significant-word overlap** (stop-words filtered, ≥2 matching significant title words, or 1 if the title is a single word) and preserving the actual **signed** score from the recall result — positive matches float up, negative (rejected) matches get pushed to the bottom, unmatched steps sit at neutral weight. Loose matching is the single most likely reason your memify reorder demo will look like nothing happened.

### Phase 7 (performance): don't skip this even if it feels like polish
Roadmap generation at 15–30 minutes end-to-end is a real risk I hit, and it is *not* an LLM speed problem by itself — it's architectural:
- **No cache check** meant every click, including re-opening an *existing* roadmap, triggered a full regeneration. Fix: check the DB for an existing roadmap by opportunity ID before invoking the orchestrator at all; a cache hit should be a ~200ms DB read, not a multi-minute regeneration.
- **Sequential Cognee writes** (1 + N `remember()` calls, one per step) are slow because each one triggers its own internal LLM extraction pass. Batch them with `asyncio.gather()` — Cognee v1.2.2 doesn't support true batch `remember()`, so parallelizing your own calls is the best lever you have.
- **No timeouts anywhere** meant one slow/queued LLM call could stall the entire pipeline indefinitely. Wrap every LLM call and every Cognee SDK call in a `asyncio.wait_for()` with a hard ceiling (30s is a reasonable start).
- **First-generation vs. background reseeding is a meaningful distinction, not just an optimization.** For a brand-new roadmap, *await* the Cognee seeding synchronously — you need that memory actually written before the very next step-completion triggers a `memify()`/reorder, or you'll get a race condition where the demo reorder silently does nothing because the graph wasn't ready yet. For a regeneration of something already seeded, fire the reseed as a background task — don't make the user wait on it.
- **Idempotency matters.** Track a boolean flag (`cognee_seeded`) on your roadmap record so you don't reseed Cognee on every reopen.

The net effect of these four fixes took my worst-case flow from 15–30 minutes down to roughly 200ms for cache hits and 2–5 minutes for genuinely new generations. That difference is the difference between a demo that flows and a demo where you're narrating over dead air.

### Phase 8 (frontend polish, sequenced deliberately)
Do frontend polish in this order, and treat everything past step 4 as optional if you're tight on time:
1. Global light/dark theme system, with a FOUC-prevention inline script so there's no white flash on load, and deliberately re-tuned accent colors for contrast in light mode rather than just inverting.
2. Navigation (a proper router, a slide-in staggered menu — small, cheap, high perceived-polish).
3. Footer with a bit of brand personality (a scramble-text animation costs nothing and reads as "these people cared").
4. Profile page rebuild — this is usually a coherent, shippable stopping point on its own.
5. Landing page with a narrative section that visually represents your core mechanic (I used a scroll-scrubbed branching timeline with nodes for each core capability, culminating in a highlighted node for the memify/reorder feature — the landing page should visually foreshadow the thing you're about to demo live).
6. **Auth flow is the highest-risk addition this close to a deadline — build it last, and only if everything else is already solid.** I explicitly deprioritized a multi-step auth flow to guarantee zero breaking changes right before submission, and I'd make that call again every time.

Two frontend traps worth flagging explicitly: if you paste in a UI component library or template, restyle it to your own design tokens before integration — off-the-shelf defaults are instantly recognizable to judges as "not really yours." And if you're running multiple AI coding agent sessions across days, watch for **rogue scope creep**: an agent asked to fix a rendering bug in a 3D scene once quietly introduced an entirely new component with procedural geometry instead of touching the actual mounted component. Before writing any corrective prompt, grep/confirm which component is *actually* mounted and rendering — don't assume the file you last edited is the one currently in the DOM.

---

## Part 5 — Working with AI coding agents across a multi-day build

This part isn't Cognee-specific, but it's what actually let me keep momentum across many sessions and multiple agents (I rotated between two, as free-tier credits ran out on each):

- **Keep an append-only session log.** Every session, a new entry gets appended to a build log — never edit or delete a prior entry. This means any agent picking up mid-project can read the full history and understand *why* a decision was made, not just *what* the current state is. This one habit alone is worth adopting even outside a hackathon context.
- **Write your architectural guardrails down once, in a file every agent is instructed to read first.** Mine locked things like "single orchestrator," "one shared schema," "raw SDK tool-use loop, no frameworks," and "BYOK via pgcrypto" — so no agent session could accidentally reintroduce complexity I'd already ruled out.
- **Diagnose root cause before you hand over a fix.** If an agent (or you) can't point to the actual broken layer, don't write a "fix" prompt yet — you'll waste an iteration patching a symptom.
- **Prefer raw log output over summaries as proof something works.** "It passed" from an agent is not proof. A pasted terminal output showing five PASS lines is proof.
- **Validate one layer before moving to the next.** DB connectivity, then auth, then orchestrator, then frontend — in that order, with an explicit stop-and-report step if any layer isn't real. This is the single habit that caught my placeholder `DATABASE_URL` before I'd built an entire frontend against it.
- **Any DB schema change needs a migration in the same breath as the model change.** I missed this twice — updated a SQLAlchemy model, forgot the Alembic migration, and got a very confusing `UndefinedColumnError` at runtime days later. If you can, add a standing rule that no model change is "done" until the migration has actually been generated and applied.

---

## Part 6 — What I'd tell you to prioritize if you're reading this with two days left

1. **Get the Cognee lifecycle spike passing first, in total isolation, on your locked demo model.** Nothing else matters until this is real.
2. **Build the memify reorder mechanic before you build anything decorative.** It's your entire pitch. A gorgeous landing page with a broken reorder is a worse demo than an ugly page with a reorder that visibly works.
3. **Fix your step-matching logic carefully.** A loose match makes every step look "memified" and the demo looks like it's doing nothing, even when the underlying mechanics are correct.
4. **Add timeouts everywhere an LLM or Cognee call can block.** A hung call during a live demo is the single worst failure mode — worse than a clean error message.
5. **Know exactly what your fallback path is, and be honest about it on stage.** If your demo runs partly on a Postgres fallback because your LLM provider capped your budget mid-week, say so precisely. Technical judges respect "here's what's really happening under the hood" far more than a vague claim that everything is running on live vector recall when it isn't.
6. **Cut auth, cut outreach/resource features, cut the fancy graph visualizer before you cut the reorder animation.** Decide your cut list before you're under enough pressure to make that decision badly.

Good luck. If you're building on Cognee, the lifecycle is genuinely more capable than the docs make it look — `improve()` and granular `forget()` are real, and the feedback-weighted `recall()` is the actual product idea most teams are reaching for without realizing Cognee already has the primitive built in. Go find it with `inspect.signature()` before you build around an imagined version of it.
