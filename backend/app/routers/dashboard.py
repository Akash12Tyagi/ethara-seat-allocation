from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    AllocationStatus,
    Employee,
    EmploymentStatus,
    Project,
    Seat,
    SeatAllocation,
    SeatStatus,
)
from app.schemas.dashboard import DashboardSummary, FloorUtilization, ProjectUtilization, RecentAllocation

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def summary(db: Session = Depends(get_db)):
    total_employees = db.execute(select(func.count()).select_from(Employee)).scalar_one()
    active_employees = db.execute(
        select(func.count()).select_from(Employee).where(Employee.status == EmploymentStatus.ACTIVE)
    ).scalar_one()
    total_seats = db.execute(select(func.count()).select_from(Seat)).scalar_one()

    def count_by_status(s: SeatStatus) -> int:
        return db.execute(select(func.count()).select_from(Seat).where(Seat.status == s)).scalar_one()

    occupied = count_by_status(SeatStatus.OCCUPIED)
    available = count_by_status(SeatStatus.AVAILABLE)
    reserved = count_by_status(SeatStatus.RESERVED)
    maintenance = count_by_status(SeatStatus.MAINTENANCE)

    allocated_subq = select(SeatAllocation.employee_id).where(
        SeatAllocation.allocation_status == AllocationStatus.ACTIVE
    )
    pending = db.execute(
        select(func.count())
        .select_from(Employee)
        .where(Employee.status == EmploymentStatus.ACTIVE, Employee.id.not_in(allocated_subq))
    ).scalar_one()

    return DashboardSummary(
        total_employees=total_employees,
        active_employees=active_employees,
        total_seats=total_seats,
        occupied_seats=occupied,
        available_seats=available,
        reserved_seats=reserved,
        maintenance_seats=maintenance,
        pending_allocation=pending,
    )


@router.get("/project-utilization", response_model=list[ProjectUtilization])
def project_utilization(db: Session = Depends(get_db)):
    projects = db.execute(select(Project)).scalars().all()
    results = []
    for p in projects:
        employee_count = db.execute(
            select(func.count()).select_from(Employee).where(Employee.project_id == p.id)
        ).scalar_one()
        allocated_seats = db.execute(
            select(func.count())
            .select_from(SeatAllocation)
            .where(SeatAllocation.project_id == p.id, SeatAllocation.allocation_status == AllocationStatus.ACTIVE)
        ).scalar_one()
        pct = round((allocated_seats / employee_count * 100), 1) if employee_count else 0.0
        results.append(
            ProjectUtilization(
                project_id=p.id,
                project_name=p.name,
                employee_count=employee_count,
                allocated_seats=allocated_seats,
                utilization_pct=pct,
            )
        )
    return sorted(results, key=lambda r: r.employee_count, reverse=True)


@router.get("/floor-utilization", response_model=list[FloorUtilization])
def floor_utilization(db: Session = Depends(get_db)):
    floors = sorted({row[0] for row in db.execute(select(Seat.floor).distinct())})
    results = []
    for floor in floors:
        total = db.execute(select(func.count()).select_from(Seat).where(Seat.floor == floor)).scalar_one()

        def count_by_status(s: SeatStatus) -> int:
            return db.execute(
                select(func.count()).select_from(Seat).where(Seat.floor == floor, Seat.status == s)
            ).scalar_one()

        occupied = count_by_status(SeatStatus.OCCUPIED)
        available = count_by_status(SeatStatus.AVAILABLE)
        reserved = count_by_status(SeatStatus.RESERVED)
        maintenance = count_by_status(SeatStatus.MAINTENANCE)
        pct = round((occupied / total * 100), 1) if total else 0.0
        results.append(
            FloorUtilization(
                floor=floor,
                total_seats=total,
                occupied_seats=occupied,
                available_seats=available,
                reserved_seats=reserved,
                maintenance_seats=maintenance,
                occupancy_pct=pct,
            )
        )
    return results


@router.get("/recent-allocations", response_model=list[RecentAllocation])
def recent_allocations(db: Session = Depends(get_db), limit: int = 20):
    stmt = select(SeatAllocation).order_by(SeatAllocation.allocation_date.desc()).limit(limit)
    allocations = db.execute(stmt).scalars().all()
    out = []
    for a in allocations:
        out.append(
            RecentAllocation(
                employee_name=a.employee.name,
                seat_code=a.seat.code,
                project_name=a.project.name if a.project else None,
                allocation_date=a.allocation_date.isoformat(),
                action="released" if a.allocation_status == AllocationStatus.RELEASED else "allocated",
            )
        )
    return out
