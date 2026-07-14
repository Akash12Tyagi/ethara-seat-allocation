# AI Tool Usage Log

This entire application was built in a single session with **Claude** (Anthropic, running as "Claude Code") acting as the primary engineer, driven by one master prompt plus follow-up instructions from the candidate. This file documents that process per the assessment's §9/§10 requirements: the prompts used, what Claude generated correctly vs. incorrectly, what was manually fixed, and how correctness was validated.

## How this session worked

Rather than many short back-and-forth prompts, the candidate supplied one large upfront "master prompt" (reproduced in full context below) specifying a 14-phase build process (requirement analysis → architecture → database → backend → allocation engine → dashboard → AI assistant → frontend → seed data → testing → deployment → documentation → self-review). Claude executed all phases autonomously in one continuous session, self-directing the sub-tasks, running its own tests, catching and fixing its own bugs, and asking the candidate only when genuinely blocked (e.g., which AI provider to use for the assistant's LLM layer).

## Prompt 1 — Planning / Architecture

> "You are a Principal Software Engineer... [full 14-phase master prompt covering requirement analysis, gap analysis, architecture, database, backend, seat allocation engine, dashboard, AI assistant, frontend, seed data, testing, deployment, documentation, and self-review, targeting the attached Ethara Seat Allocation & Project Mapping System PDF as the single source of truth]"

**What Claude generated correctly:** A full requirement/gap analysis (`REQUIREMENTS.md`) extracting every functional requirement, business rule, API endpoint, and edge case from the PDF into a checklist; a stack decision (FastAPI + SQLAlchemy 2 + Alembic + PostgreSQL/SQLite, Next.js 16 + TypeScript + Tailwind + TanStack Query) matching the PDF's recommended stack.

**What needed correction:** Nothing structural — the plan itself was sound. The gap analysis correctly flagged upfront that live deployment and screenshots would need user action / a running browser, rather than silently skipping them.

**Validation:** Manually reviewed `REQUIREMENTS.md` against every bullet in the PDF section-by-section before implementation began.

## Prompt 2 — Database Design

> (Part of the master prompt, Phase 4) "Design a normalized PostgreSQL database... Ensure: No duplicate employee email, no duplicate seat, one active seat per employee, one employee per seat, reserved seats cannot be allocated, released seats become available."

**What Claude generated correctly:** SQLAlchemy models (`app/models.py`) with the four core tables (`employees`, `projects`, `seats`, `seat_allocations`), a `_enum()` helper that stores lowercase `.value` strings (not Python enum `.name`) so DB rows, API JSON, and partial-index predicates all agree, and standard unique constraints (`employees.email`, `seats(floor, zone, seat_number)`).

**What Claude generated incorrectly (and fixed itself):** The first draft of the "one active allocation per employee/seat" constraint used a nonsensical `postgresql_where=(mapped_column := None) or None` expression — a leftover from an aborted approach. Caught immediately on review (before ever running it) and rewritten as two proper partial unique `Index` objects with `sqlite_where`/`postgresql_where` predicates on `allocation_status = 'active'`.

**Validation:** Ran `alembic revision --autogenerate` and inspected the generated migration SQL; applied it to a fresh SQLite DB and inspected the resulting schema with `sqlite3`; later re-verified against a real Postgres instance via Docker Compose (see Prompt 9).

## Prompt 3 — Backend APIs

> (Master prompt, Phase 5) "Generate production-quality FastAPI code... Every API must include validation, error handling, pagination, filtering, sorting, search, documentation, proper HTTP status codes. Keep code modular. No monolithic files."

**What Claude generated correctly:** Modular routers (`employees.py`, `projects.py`, `seats.py`, `dashboard.py`, `ai.py`), each under 200 lines; consistent pagination (`page`/`page_size`/`total_pages`) on list endpoints; proper 404/409 status codes for not-found and conflict cases; CSV bulk-upload endpoint as a bonus.

**What needed correction:** An early version of `dashboard.py`'s `pending_allocation` calculation built a Python `set` of allocated employee IDs and then did an O(n) list comprehension over all employees in Python — correct but needlessly slow at 5,000 rows. Rewritten to a single SQL `NOT IN` subquery.

**Validation:** `pytest` unit tests (29 tests, see Prompt 7) plus manual `curl` smoke tests against every endpoint after seeding.

## Prompt 4 — Seat Allocation Logic

> (Master prompt, Phase 6) "Build an intelligent seat allocation engine. Rules: Find available seat, keep project members together, suggest nearby seats, suggest alternate zones, prevent duplicate allocations, prevent reserved seats, prevent maintenance seats, support release workflow."

**What Claude generated correctly:** `app/services/allocation.py` implements a 4-step fallback (preferred zone → project-teammate zone → same floor → any floor), correctly rejecting `reserved`/`maintenance` seats and raising typed exceptions (`EmployeeAlreadyAllocatedError`, `SeatNotAvailableError`, `NoSeatAvailableError`) that the router maps to `409`.

**What Claude generated incorrectly (caught by manual testing, not by an automated test):** The very first version marked `alternate_zone_used=True` even when there was no actual zone preference to override (e.g., a brand-new project with no seated teammates yet, so the engine fell straight to "any seat" — technically not an "alternate"). Caught by manually inspecting a `curl` response during smoke testing and reading the returned message ("Preferred zone was full; an alternate zone was used" when no preference existed at all). Fixed by tracking whether a real preference existed before labeling the fallback as "alternate."

**Validation:** 12 dedicated pytest cases in `tests/test_seat_allocation.py` covering every business rule (B1–B5), plus a manual allocation sequence via `curl` to visually confirm the returned messages made sense.

## Prompt 5 — AI Assistant

> (Master prompt, Phase 8) "Implement an AI assistant. Preferred: OpenAI API. Fallback: Keyword and intent parser. Support queries like: Where is my seat? ... Return professional responses." — later superseded by an explicit follow-up: **"continue with CLAUDE API"** (switch the optional LLM-phrasing tier from OpenAI to Anthropic's Claude API).

**What Claude generated correctly:** A deterministic regex/keyword intent parser (`app/services/ai_assistant.py`) that resolves seat lookup, project assignment, available-seats, nearby-teammates, project-utilization, and allocate-new-joiner intents purely from SQL — this is what actually answers the question in both tiers, so the optional LLM only rephrases prose and can never hallucinate a wrong seat number.

**What Claude generated incorrectly (found via manual testing against the real 5,000-employee dataset, not caught by early unit tests written against a tiny 1-employee fixture):**
1. Single-word substring name matching (`"Kristen"` alone) almost never uniquely identified one of 5,000 employees, so "Where is Kristen Weeks seated?" failed with "I couldn't identify that employee." Fixed by extracting full capitalized-phrase candidates (`"Kristen Weeks"`) via regex before falling back to single words.
2. "Who is sitting near Kristen Weeks?" was intercepted by the earlier "where is ... seated" branch because that branch's keyword list included the bare word "sitting", so it returned a seat lookup instead of a teammate list. Fixed by reordering intent checks so the more specific "near me / sitting near / nearby" branch is checked first.

**What needed correction after switching to Claude:** The original OpenAI call passed `temperature=0.3`, which Claude Opus 4.8 rejects (`400`, sampling parameters removed on Opus 4.7+). Removed the parameter entirely rather than porting it.

**Validation:** 9 pytest cases in `tests/test_ai_assistant.py`; then, critically, *manual* testing against the full 5,000-row seeded dataset via `curl` (not just the small pytest fixtures) — this is what actually surfaced both name-matching bugs above, since a 1-employee test fixture can't expose an ambiguous-name collision. After switching to Claude, tested the fallback path by deliberately setting `ANTHROPIC_API_KEY` to an invalid value and confirming the server logged a real `401` from `api.anthropic.com` (proving the request reached Anthropic correctly) and the endpoint still returned `200` with the deterministic answer (proving the `try/except` fallback works).

## Prompt 6 — Frontend

> (Master prompt, Phase 9) "Create a modern enterprise UI. Requirements: Responsive, clean, premium, fast, accessible... The application should look like an internal enterprise product rather than a marketing website."

**What Claude generated correctly:** Next.js 16 App Router pages for Dashboard, Employees, Projects, Seats, and AI Assistant, using TanStack Query for data fetching, React Hook Form + Zod for the create/edit modals, and hand-rolled Tailwind UI primitives (no external component library, since shadcn's CLI would need a network registry fetch that could fail unpredictably in this environment).

**What Claude generated incorrectly (self-caught before it reached the user):**
1. `qs()` in `lib/api.ts` was typed as `Record<string, string | number | undefined | null>`, which TypeScript rejects when called with a concrete interface like `EmployeeListParams` that has no index signature — a `next build` type-check failure. Fixed by loosening the parameter type to `object` and casting internally.
2. `useSearchParams()` on the Employees page (used to pre-fill the project filter from a "View team →" link) needs a `<Suspense>` boundary in Next.js 16's App Router, or `next build` fails outright with "Missing Suspense boundary." Fixed by splitting the page into an outer `Suspense`-wrapped default export and an inner content component.

**Validation:** `npm run build` (production build, catches type errors and the Suspense requirement) and `npm run lint` both run clean; then a headless-browser (Playwright) screenshot pass across all 5 pages checking for console errors and visually inspecting the rendered output against real seeded data — this caught issues a build/lint pass alone would have missed (see Prompt 8).

## Prompt 7 — Testing

> (Master prompt, Phase 11) "Generate: Unit Tests, API Tests, Integration Tests, Business Rule Tests, Dashboard Tests, AI Assistant Tests. Validate every business rule."

**What Claude generated correctly:** 29 pytest tests across 5 files (`test_employees.py`, `test_seat_allocation.py`, `test_dashboard.py`, `test_ai_assistant.py`), each mapped in a comment to the specific business rule (B1–B8) it verifies, using an isolated per-test SQLite database via a `db_session` fixture and FastAPI's `dependency_overrides`.

**What needed correction:** None on first pass, but see Prompt 5 above — the pytest suite alone did *not* catch the AI name-matching bugs, because the fixtures only ever create 1–2 employees. This is documented as a known test-coverage gap: the automated suite validates business-rule *correctness*, while *scale-dependent* behavior (name ambiguity at 5,000 rows) required manual testing against the real seeded dataset.

**Validation:** `pytest -v` run repeatedly throughout development; 29/29 passing at every checkpoint, including after the Claude API switch.

## Prompt 8 — Debugging

Several bugs were found and fixed purely through manual verification rather than being caught by any prompt or automated test:

1. **Seed script double-allocated seats.** `allocate_seats()` in `seed.py` originally used two separate Python lists — a per-zone dict and a global "overflow pool" — both referencing the *same* `Seat` objects. Depleting one didn't remove entries from the other, so a seat could be handed to two different employees, tripping the `uq_active_allocation_per_seat` constraint with an `IntegrityError` on the 4,850th-ish insert. Root-caused by reading the traceback (`UNIQUE constraint failed: seat_allocations.seat_id`) and rewriting to a single shared per-zone bucket structure that both the home-zone and overflow paths pop from.
2. **Seed script produced a misleading default view.** Employees 1–90 were unconditionally marked inactive (matching `INACTIVE_EMPLOYEES=90`), so the default employee list (sorted by ID) opened on a wall of 90 straight "Inactive / Pending" rows — technically correct data, but looked like broken seeding on first glance. Caught via a Playwright screenshot of the Employees page. Fixed by using `random.sample()` to scatter inactive employee IDs across the full range instead of the first 90.
3. **Next.js dev server hung at 417% CPU after editing `next.config.ts` while running.** Editing the Turbopack config file while `next dev` was live triggered a hot-restart that corrupted the RSC manifest (`SyntaxError: Invalid or unexpected token` in the dev server log), leaving the process spinning and unresponsive to `curl`. Root-caused via the dev server log; fixed by force-killing the process and restarting clean (not a code bug, but documented here since it cost real debugging time).

**Validation:** All three were confirmed fixed by re-running the affected command (`python seed.py`, loading the Employees page, restarting `next dev`) and observing correct behavior.

## Prompt 9 — Deployment

> (Master prompt, Phase 12) "Prepare for production deployment... Generate: Dockerfile, docker-compose, Environment Variables, Deployment Guide."

**What Claude generated correctly:** Multi-stage `Dockerfile`s for both services (Python slim + Node standalone output), a root `docker-compose.yml` (Postgres + backend + frontend with healthchecks), and `.env.example` files for both.

**What needed correction:** The backend `Dockerfile` originally pinned `psycopg2-binary`, which has no prebuilt wheel for this machine's Python/architecture combination and fails to compile from source without `pg_config`. Switched to `psycopg[binary]>=3.2.10` (psycopg3), which ships wheels for the target platforms.

**Validation:** Ran `docker compose build` for both images and `docker compose up` for the full stack against a **real** (non-SQLite) Postgres container — confirmed Alembic migrations applied automatically on container start, `python seed.py` ran successfully inside the container, and the dashboard/AI endpoints returned correct data through the containerized stack, not just the local dev setup. (One transient `docker compose build` failure was a Docker Desktop memory limit during `apt-get`, not a code issue — resolved by retrying.)

## Prompt 10 — Refactoring / Self-Review

> (Master prompt, Phase 14) "Before considering any feature complete: Review the entire project against the attached PDF. Create a comparison table... Repeat this review until every requirement in the PDF is fully satisfied."

See `REQUIREMENTS.md` for the full requirement-by-requirement checklist maintained throughout the build, and the final summary in this session's closing message for the completion table.

---

## Summary: what AI generated correctly vs. incorrectly

| Category | Correct on first pass | Needed a fix |
|---|---|---|
| Database schema & constraints | Table design, FKs, unique constraints | Partial-index predicate (caught before running) |
| Backend CRUD/routers | Structure, status codes, pagination | Dashboard pending-count query efficiency |
| Allocation engine | Core 4-step fallback logic | `alternate_zone_used` mislabeling |
| AI assistant | Intent resolution logic, SQL grounding | Name-matching at scale; intent-priority ordering; OpenAI→Claude param cleanup |
| Frontend | Page structure, data fetching, forms | TS generic typing; Next.js Suspense requirement |
| Seed data | Volume targets, status distribution | Double-allocation bug; inactive-employee clustering |
| Docker/deployment | Dockerfile structure, compose topology | psycopg2 → psycopg3 swap |

## How correctness was validated (summary)

- **Automated:** 29 pytest tests (backend business rules), `next build` + `npm run lint` (frontend), `alembic upgrade head` against both SQLite and real Postgres.
- **Manual, against real data:** curl smoke tests against every endpoint after seeding 5,000 employees; Playwright headless-browser screenshots of all 5 frontend pages checked for console errors and visual correctness; a deliberate invalid-API-key test to confirm the Claude fallback path degrades gracefully instead of crashing.
- **Root-causing:** every bug listed above was found by reading actual error output (tracebacks, HTTP status codes, server logs) rather than guessing, and confirmed fixed by re-running the exact failing scenario.
