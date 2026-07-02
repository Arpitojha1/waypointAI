# AGENT.md — Waypoint (Career Opportunity Agent)

Read this file first, every session, before touching code. It is the contract for this build — do not re-derive architecture from scratch, and do not "improve" it mid-build unless explicitly asked to.

## What this is

An AI career opportunity agent for the Cognee Hackathon (deadline July 5). It ingests GitHub "good first issues," Devpost hackathons, and Arbeitnow job postings, then generates a per-opportunity **roadmap** using Cognee's full memory lifecycle (`remember`, `recall`, `improve`/`memify`, `forget`). UI is card list → click → roadmap checklist. No graph view. No react-flow.

## Context files — read in this order

1. `AGENT.md` (this file) — guardrails, skill routing, non-negotiables
2. `PRODUCT.md` — audience, feature scope, what's explicitly cut (written by `/impeccable init`)
3. `DESIGN.md` — visual system, tokens, components
4. `SESSION_CONTEXT.md` — append-only log; read the last 2 entries before starting work

`PRODUCT.md` and `DESIGN.md` are **frozen after Phase 1**. Don't redesign them mid-build. If something in them looks genuinely wrong once real data is flowing, flag it explicitly and ask — don't silently drift from them.

## Non-negotiable guardrails

| Rule | Why it exists |
|---|---|
| Single orchestrator, 5 role-scoped system prompts (ingestion, roadmap, outreach, resource, memory) | Not 5 separate agent services — doesn't fit the 32-hour budget |
| One `Roadmap` + `Step` schema for all 3 opportunity types | Only the system prompt and recall query differ per type — no bespoke tables |
| Cognee lifecycle is load-bearing, not decorative | `remember` on ingest, typed `recall` per role, `improve`/`memify` triggered by step check-off/reject, `forget` for stale/closed listings |
| Raw Anthropic SDK tool-use loop | No LangChain, no CrewAI, hand-written in `orchestrator.py` |
| BYOK key encrypted via pgcrypto | Never stored plaintext |
| No graph visualization, no react-flow | Card list → checklist only — this was cut for demo risk and time |
| RLS enabled on every user-scoped table | Policy keyed to `auth.uid()`, directly or via join |

If a request would violate one of these, say so before implementing it — don't quietly work around it or reinterpret it as "close enough."

## Frontend skill routing

Three design skills are installed in this repo. They are **not interchangeable** — each owns a different pass, and running the wrong one at the wrong time wastes hours you don't have.

| Skill | When to invoke | What it's for here |
|---|---|---|
| **taste-skill** (`design-taste-frontend`) | Once, at the start of Phase 5, against `DESIGN.md` | Reads the brief and confirms/tunes the VARIANCE / MOTION / DENSITY dials before any component exists. This is a one-time direction-setting pass, not something you re-run per component. |
| **impeccable** | After each component ships (`OpportunityCard`, `RoadmapView`, `StepItem`, `BYOKPanel`), and once more as a full pass before Phase 9 deploy | `/impeccable audit <file>` then `/impeccable polish <file>` per component. `/impeccable critique` on `Dashboard` + `RoadmapPage` right before the demo. It auto-reads `PRODUCT.md`/`DESIGN.md` — run `/impeccable init` once at the very start if it reports `NO_PRODUCT_MD`. |
| **emil-design-eng** (emilkowalski/skills) | Specifically for: `StepItem` check-off animation, the memify reorder animation, hover/press states on cards | This is the demo centerpiece — the judge-visible before/after roadmap reordering. It earns hand-tuned motion (spring-based reorder, deliberate easing), not a default CSS transition. Follow up with `review-animations` once the motion exists. |

Don't let taste-skill and impeccable fight over the same file in the same pass — taste-skill sets direction once, impeccable enforces and tightens it afterward. emil-design-eng only touches motion, never layout or color.

## Session hygiene

- At the end of a working session, **append** (never rewrite) a short entry to `SESSION_CONTEXT.md`: what shipped, what's next, any deviation from this file and why.
- If starting a fresh session/task, paste the "Non-negotiable guardrails" table verbatim — don't summarize or paraphrase it from memory.
- If you're unsure whether a decision was already made, check `SESSION_CONTEXT.md` before asking or before re-deciding.