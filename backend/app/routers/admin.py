"""Temporary remote-seeding endpoint for managed platforms whose free tier has
no shell/job primitive (see docs/DEPLOYMENT.md). Only active when ADMIN_SEED_TOKEN
is set; meant to be removed (or the env var unset) once a deployment is seeded."""
from fastapi import APIRouter, Header, HTTPException

from app.config import get_settings
from app.database import SessionLocal
from app.models import Employee

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/seed")
def run_seed(x_admin_token: str | None = Header(default=None)):
    settings = get_settings()
    if not settings.admin_seed_token or x_admin_token != settings.admin_seed_token:
        raise HTTPException(404)  # look like a missing route, not a protected one

    import seed as seed_module

    db = SessionLocal()
    try:
        if db.query(Employee).count() > 0:
            raise HTTPException(409, "Database already has employees.")

        projects = seed_module.create_projects(db)
        seats = seed_module.create_seats(db)
        employees = seed_module.create_employees(db, projects)
        seed_module.allocate_seats(db, employees, seats, projects)
        seats = db.query(seed_module.Seat).order_by(seed_module.Seat.floor, seed_module.Seat.zone, seed_module.Seat.id).all()
        seed_module.mark_reserved_and_maintenance(db, seats)

        return {
            "employees": db.query(Employee).count(),
            "seats": db.query(seed_module.Seat).count(),
        }
    finally:
        db.close()
