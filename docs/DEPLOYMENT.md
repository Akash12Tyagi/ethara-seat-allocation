# Deployment Guide

This repo is deploy-ready (Dockerfiles, Alembic migrations, env-based config), but publishing to a live URL requires the developer's own cloud accounts — this section documents the exact steps.

## Option A: Docker Compose (any VPS / local)

```bash
docker compose up --build -d
docker compose exec backend python seed.py   # one-time, generates demo data
```
This is the fastest path to a fully working stack and is what was actually verified during development (see `AI_PROMPTS.md` Prompt 9) — Postgres + backend + frontend, migrations run automatically on backend container start.

## Option B: Railway (backend + Postgres)

1. `railway login` / create a new project at railway.app.
2. Add a **PostgreSQL** plugin — Railway provisions `DATABASE_URL` automatically (note: Railway's variable uses `postgres://`; SQLAlchemy 2 with psycopg3 needs `postgresql+psycopg://` — either transform it in `app/config.py` or set an explicit `DATABASE_URL` override in Railway's variables).
3. Deploy the `backend/` directory as a service (Railway auto-detects the `Dockerfile`).
4. Set environment variables: `DATABASE_URL`, `CORS_ORIGINS` (your frontend's deployed URL), optionally `ANTHROPIC_API_KEY` + `ANTHROPIC_MODEL`.
5. Railway runs `alembic upgrade head && uvicorn ...` automatically per the Dockerfile `CMD`.
6. Run the seed once via Railway's shell/exec: `python seed.py`.

## Option C: Vercel (frontend)

1. Import the `frontend/` directory as a Vercel project (Next.js is auto-detected).
2. Set `NEXT_PUBLIC_API_URL` to your deployed backend URL (Railway, etc.) in Vercel's environment variables.
3. Deploy — Vercel builds with `npm run build` (which we've verified passes cleanly, including the Suspense boundary fix).

## Environment variables reference

**Backend** (`backend/.env.example`):
```
DATABASE_URL=postgresql+psycopg://user:password@host:5432/ethara
ANTHROPIC_API_KEY=            # optional — enables Claude-phrased AI responses
ANTHROPIC_MODEL=claude-opus-4-8
CORS_ORIGINS=https://your-frontend-domain.com
ENVIRONMENT=production
```

**Frontend** (`frontend/.env.example`):
```
NEXT_PUBLIC_API_URL=https://your-backend-domain.com
```

## Post-deploy checklist

- [ ] `GET /health` returns `{"status": "healthy"}`
- [ ] `GET /docs` (Swagger) loads
- [ ] Frontend dashboard loads and shows non-zero counts (i.e. seed ran)
- [ ] `POST /ai/query` with a known employee name returns a correct seat lookup
- [ ] CORS: frontend can call backend without browser console errors (check `CORS_ORIGINS` matches the deployed frontend origin exactly, including scheme)
