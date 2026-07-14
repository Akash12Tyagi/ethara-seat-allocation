# Ethara Seat Allocation & Project Mapping System

A full-stack app that manages seat allocation and project mapping for ~5,000 employees across 5 floors / 10 zones, with an AI assistant for natural-language seat/project queries.

Built for the *Vibe Coding Assessment: Ethara Seat Allocation & Project Mapping System*. See [REQUIREMENTS.md](REQUIREMENTS.md) for the full requirement/gap analysis and [AI_PROMPTS.md](AI_PROMPTS.md) for the AI-usage log this assessment requires.

## Live deployment

| | |
|---|---|
| Frontend | https://ethara-seat-allocation-gilt.vercel.app |
| Backend API | https://ethara-backend-ngmp.onrender.com |
| API docs (Swagger) | https://ethara-backend-ngmp.onrender.com/docs |
| GitHub repo | https://github.com/Akash12Tyagi/ethara-seat-allocation |

Backend runs on Render's free tier (Docker web service + free Postgres) — the free Postgres instance expires 30 days after creation; the free web service spins down after 15 minutes of inactivity and takes ~30-60s to wake up on the first request after idling. Seeded with the full 5,000-employee / 5,600-seat demo dataset described below. No `ANTHROPIC_API_KEY` is set on the live deployment, so the AI Assistant runs in rule-based fallback mode (fully functional, per the PDF's explicit fallback requirement).

## Stack

| Layer | Choice |
|---|---|
| Frontend | Next.js 16 (App Router) · TypeScript · Tailwind CSS 4 · TanStack Query · React Hook Form + Zod · Framer Motion |
| Backend | FastAPI · SQLAlchemy 2 · Alembic · Pydantic v2 |
| Database | PostgreSQL (production) · SQLite (zero-setup local dev, default) |
| AI Assistant | Rule-based intent parser (default) · optional Claude (`claude-opus-4-8`) phrasing layer if `ANTHROPIC_API_KEY` is set |

## Project layout

```
backend/
  app/
    models.py            SQLAlchemy models (Employee, Project, Seat, SeatAllocation)
    schemas/              Pydantic request/response models
    routers/               employees.py, projects.py, seats.py, dashboard.py, ai.py
    services/
      allocation.py       seat allocation engine (proximity-based auto-select, release)
      ai_assistant.py     intent parser + optional Claude API phrasing
  alembic/                 migrations
  seed.py                  generates the 5,000-employee demo dataset
  tests/                   29 pytest tests covering every business rule (B1-B8)
frontend/
  src/app/                 dashboard, employees, projects, seats, assistant routes
  src/components/          shared UI primitives + per-feature components
  src/lib/                 typed API client (lib/api.ts) and types (lib/types.ts)
docker-compose.yml          postgres + backend + frontend, one command to run everything
```

## Quick start (local, no Docker)

### Backend
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                 # defaults to SQLite, zero setup
alembic upgrade head
python seed.py                       # generates the 5,000-employee dataset (~2s)
uvicorn app.main:app --reload --port 8000
```
API docs (Swagger): http://localhost:8000/docs

### Frontend
```bash
cd frontend
npm install
cp .env.example .env.local           # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```
App: http://localhost:3000

### Tests
```bash
cd backend && source .venv/bin/activate && pytest -v
```

## Quick start (Docker)

```bash
docker compose up --build
```
This starts Postgres + the FastAPI backend (migrations run automatically on container start) + the Next.js frontend. Seed data is **not** auto-generated in Docker (avoids accidentally reseeding a shared DB on every restart) - run it once manually:
```bash
docker compose exec backend python seed.py
```
Frontend: http://localhost:3000 · Backend: http://localhost:8000 · Swagger: http://localhost:8000/docs

## Seed data

`python seed.py` (`--reset` to wipe and regenerate) produces, matching the PDF's minimums:

| | Target | Generated |
|---|---|---|
| Employees | 5,000 | 5,000 |
| Floors | ≥5 | 5 |
| Zones | ≥10 | 10 |
| Seats | ≥5,500 | 5,600 |
| Projects | ≥10 | 11 (all PDF-named projects) |
| Available seats | ≥500 | 600 |
| Reserved seats | ≥100 | 120 |
| Pending allocation | ≥50 | 60 |

Inactive employees and pending allocations are scattered randomly across employee IDs (not clustered at the start of the table), so the default employee list view reflects a realistic mix rather than a block of stale data.

## Core business rules (enforced at the service + DB layer, not just the UI)

1. One employee → only one **active** seat at a time (partial unique index on `seat_allocations.employee_id`).
2. One seat → only one active employee (partial unique index on `seat_allocations.seat_id`).
3. Releasing a seat sets it back to `available` and closes the allocation (`released_date` recorded).
4. `reserved` / `maintenance` seats reject allocation attempts (409).
5. New joiners are prioritized near their project teammates: the allocation engine finds the floor+zone with the most active teammates on the same project, then falls back to the same floor, then anywhere in the building.
6. Duplicate employee email → 409 (DB unique constraint).
7. Duplicate seat number on the same floor+zone → 409 (DB unique constraint).
8. Dashboard reads live from the DB - no caching layer, so it reflects every allocation/release immediately.

Full mapping of every PDF requirement to its implementation is in [REQUIREMENTS.md](REQUIREMENTS.md).

## API summary

All endpoints from the PDF's spec (section 5) are implemented, plus a few needed to make the UI usable (pagination, pending-allocation list, CSV upload). Full interactive docs at `/docs` (Swagger) once the backend is running. Highlights:

- `POST /seats/allocate` - body `{employee_id, seat_id?, preferred_floor?, preferred_zone?}`. Omit `seat_id` to let the engine auto-select.
- `POST /seats/release` - body `{employee_id}` or `{seat_id}`.
- `POST /ai/query` - body `{query, employee_email?}` → `{answer, intent, data}`.
- `GET /dashboard/summary`, `/dashboard/project-utilization`, `/dashboard/floor-utilization`, `/dashboard/recent-allocations`.

## AI Assistant

Two tiers:
1. **Rule-based intent parser** (`app/services/ai_assistant.py`) - always active, no API key needed. Resolves the actual data (seat/project/availability lookups) via SQL, so answers are always accurate.
2. **Optional Claude phrasing** - if `ANTHROPIC_API_KEY` is set, the *already-resolved* factual answer is rephrased by Claude (`claude-opus-4-8` by default, via the official `anthropic` Python SDK) into friendlier prose. The model never invents facts; it only rewords a sentence the database already produced. If the Claude call fails (bad key, network, refusal) or no key is set, it silently falls back to the deterministic answer — verified by testing with a deliberately invalid key.

Supported query types: employee seat lookup, self seat lookup (`employee_email` in the request), project assignment, available seats by floor/zone, nearby teammates, project seat utilization, allocate-a-seat-for-a-new-joiner.

## Known simplifications (see REQUIREMENTS.md "Known Gaps" for full reasoning)

- **Auth**: a lightweight `X-Role` header (admin/hr/employee) stands in for full authentication, since the PDF doesn't mandate a specific auth scheme and the assessment's focus is the allocation/data logic. Not a security boundary as-is.
- **Live deployment**: this repo is fully deployment-ready (Dockerfiles, migrations, env-based config), but publishing to Railway/Vercel/etc. requires the developer's own cloud accounts - see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for the exact steps.

## Documentation index

- [REQUIREMENTS.md](REQUIREMENTS.md) - requirement + gap analysis, checklist against every line of the PDF
- [AI_PROMPTS.md](AI_PROMPTS.md) - AI tool usage log (prompts, what was generated correctly/incorrectly, how it was validated)
- [docs/DATABASE.md](docs/DATABASE.md) - schema, ER relationships, indexes, constraints
- [docs/API.md](docs/API.md) - endpoint reference
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) - Railway/Vercel/Docker deployment steps
- [docs/DEBUGGING.md](docs/DEBUGGING.md) - notable bugs found and fixed during development, and how
- [docs/TESTING.md](docs/TESTING.md) - test coverage notes
