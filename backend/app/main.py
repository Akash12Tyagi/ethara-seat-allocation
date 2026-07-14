import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import Base, engine
from app.routers import ai, dashboard, employees, projects, seats

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("ethara")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # For local/dev convenience. In production, Alembic migrations are authoritative
    # (see alembic/ and docs/DEPLOYMENT.md) - this call is a no-op once tables exist.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Ethara Seat Allocation & Project Mapping API",
    description="Employee, project, and seat management for ~5,000 employees across floors/zones.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(employees.router)
app.include_router(projects.router)
app.include_router(seats.router)
app.include_router(dashboard.router)
app.include_router(ai.router)


@app.get("/")
def root():
    return {"service": "ethara-seat-allocation-api", "status": "ok", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "healthy"}
