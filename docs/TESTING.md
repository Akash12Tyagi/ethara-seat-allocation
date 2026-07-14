# Testing Notes

## Backend: automated (pytest)

29 tests across 5 files, run against an isolated per-test SQLite database (fresh schema per test via the `db_session` fixture, FastAPI `dependency_overrides` swap in the test session).

```bash
cd backend && source .venv/bin/activate && pytest -v
```

| File | Covers |
|---|---|
| `test_employees.py` | CRUD, duplicate-email rejection (B6), search, deactivate-releases-seat, pending-allocation listing |
| `test_seat_allocation.py` | B1 (one seat/employee), B2 (one employee/seat), B4 (reserved/maintenance blocked), B5 (auto-select prioritizes teammates), B7 (duplicate seat number), no-seats-available |
| `test_dashboard.py` | B8 — summary/project-utilization/floor-utilization update after every allocate/release |
| `test_ai_assistant.py` | Every supported intent: seat lookup, self-lookup, project lookup, available seats, project utilization, nearby teammates, allocate-new-joiner, unknown-query fallback |

**Known coverage gap:** the pytest fixtures only ever create 1-2 employees, so they cannot exercise scale-dependent behavior. The AI assistant's name-disambiguation bug (see `docs/DEBUGGING.md` #5) only appeared against the real 5,000-employee dataset and was found by manual testing, not by this suite. If extending the test suite, consider a fixture that seeds a few hundred employees with intentionally colliding first/last names to close this gap.

## Backend: manual (curl, against seeded data)

After `python seed.py`, every endpoint was exercised via `curl` against the real 5,000-employee / 5,600-seat dataset — not just the small pytest fixtures. This is what surfaced bugs #2, #5, and #6 in `docs/DEBUGGING.md`, none of which the automated suite catches.

## Frontend: automated

```bash
cd frontend && npm run build && npm run lint
```
`next build` performs a full TypeScript check and static-generation pass across all 5 routes (dashboard, employees, projects, seats, assistant) — this is what caught the `qs()` typing issue and the missing `Suspense` boundary (see `docs/DEBUGGING.md` #7-8). `npm run lint` (ESLint) runs clean.

## Frontend: manual (headless browser)

A Playwright script (ad hoc, not committed to the repo — run from a scratch directory) loaded each of the 5 pages against the live dev server + seeded backend, captured a full-page screenshot, and asserted zero browser console errors. This caught:
- The misleading all-inactive default Employees view (seed data issue, `docs/DEBUGGING.md` #4)
- Confirmed the AI Assistant chat interaction actually round-trips through the backend correctly (clicked a suggestion chip, verified the rendered response)

To reproduce: install `playwright`, `npx playwright install chromium`, then drive `page.goto()` + `page.screenshot()` against `http://localhost:3000/<route>` with both dev servers running.

## Docker / integration

`docker compose up` was run end-to-end against a **real Postgres 16 container** (not SQLite) to verify:
- Alembic migrations apply automatically on backend container start (confirmed via `docker compose logs backend`)
- `python seed.py` works inside the container (`docker compose exec backend python seed.py`)
- Dashboard and AI endpoints return correct data through the full containerized stack
- Frontend serves and reaches the containerized backend

## AI Claude-API fallback path

Deliberately set `ANTHROPIC_API_KEY` to an invalid value and confirmed via the server log that the request reached `api.anthropic.com` and received a real `401 Unauthorized` (proving correct request construction), while the `/ai/query` endpoint still returned `200` with the deterministic fallback answer (proving the `try/except` in `answer_with_llm_or_fallback` degrades gracefully instead of crashing or 500ing).
