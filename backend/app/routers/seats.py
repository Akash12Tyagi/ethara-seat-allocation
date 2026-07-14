from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AllocationStatus, Employee, Seat, SeatAllocation, SeatStatus
from app.schemas.seat import AllocateRequest, AllocateResponse, ReleaseRequest, SeatCreate, SeatOut
from app.services import allocation as alloc_service

router = APIRouter(prefix="/seats", tags=["seats"])


def to_out(seat: Seat, db: Session | None = None) -> SeatOut:
    active = next((a for a in seat.allocations if a.allocation_status == AllocationStatus.ACTIVE), None)
    return SeatOut(
        id=seat.id,
        floor=seat.floor,
        zone=seat.zone,
        bay=seat.bay,
        seat_number=seat.seat_number,
        status=seat.status,
        code=seat.code,
        allocated_employee_id=active.employee_id if active else None,
        allocated_employee_name=active.employee.name if active else None,
        allocated_project_id=active.project_id if active else None,
        allocated_project_name=(active.project.name if active and active.project else None),
        allocation_date=active.allocation_date if active else None,
    )


@router.post("", response_model=SeatOut, status_code=status.HTTP_201_CREATED)
def create_seat(payload: SeatCreate, db: Session = Depends(get_db)):
    seat = Seat(**payload.model_dump())
    db.add(seat)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Seat number already exists on this floor/zone")
    db.refresh(seat)
    return to_out(seat)


@router.get("", response_model=dict)
def list_seats(
    db: Session = Depends(get_db),
    floor: int | None = None,
    zone: str | None = None,
    seat_status: SeatStatus | None = Query(None, alias="status"),
    project_id: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
):
    stmt = select(Seat)
    if floor is not None:
        stmt = stmt.where(Seat.floor == floor)
    if zone is not None:
        stmt = stmt.where(Seat.zone == zone)
    if seat_status is not None:
        stmt = stmt.where(Seat.status == seat_status)
    if project_id is not None:
        stmt = stmt.join(SeatAllocation, SeatAllocation.seat_id == Seat.id).where(
            SeatAllocation.project_id == project_id,
            SeatAllocation.allocation_status == AllocationStatus.ACTIVE,
        )

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    stmt = stmt.order_by(Seat.floor, Seat.zone, Seat.bay, Seat.seat_number)
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    seats = db.execute(stmt).scalars().unique().all()

    return {
        "items": [to_out(s) for s in seats],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }


@router.get("/available", response_model=list[SeatOut])
def list_available_seats(
    db: Session = Depends(get_db),
    floor: int | None = None,
    zone: str | None = None,
    limit: int = Query(100, le=1000),
):
    stmt = select(Seat).where(Seat.status == SeatStatus.AVAILABLE)
    if floor is not None:
        stmt = stmt.where(Seat.floor == floor)
    if zone is not None:
        stmt = stmt.where(Seat.zone == zone)
    stmt = stmt.order_by(Seat.floor, Seat.zone, Seat.bay, Seat.seat_number).limit(limit)
    seats = db.execute(stmt).scalars().all()
    return [to_out(s) for s in seats]


@router.get("/{seat_id}", response_model=SeatOut)
def get_seat(seat_id: int, db: Session = Depends(get_db)):
    seat = db.get(Seat, seat_id)
    if not seat:
        raise HTTPException(404, "Seat not found")
    return to_out(seat)


@router.post("/allocate", response_model=AllocateResponse)
def allocate(payload: AllocateRequest, db: Session = Depends(get_db)):
    employee = db.get(Employee, payload.employee_id)
    if not employee:
        raise HTTPException(404, "Employee not found")

    seat = db.get(Seat, payload.seat_id) if payload.seat_id else None
    if payload.seat_id and not seat:
        raise HTTPException(404, "Seat not found")

    try:
        allocated_seat, alternate_used = alloc_service.allocate_seat(
            db, employee, seat, payload.preferred_floor, payload.preferred_zone
        )
        db.commit()
    except alloc_service.EmployeeAlreadyAllocatedError as exc:
        db.rollback()
        raise HTTPException(409, str(exc))
    except alloc_service.SeatNotAvailableError as exc:
        db.rollback()
        raise HTTPException(409, str(exc))
    except alloc_service.NoSeatAvailableError as exc:
        db.rollback()
        raise HTTPException(409, str(exc))
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Seat or employee was allocated concurrently, please retry")

    db.refresh(allocated_seat)
    message = f"Seat {allocated_seat.code} allocated to {employee.name}."
    if alternate_used:
        message += " Preferred zone was full; an alternate zone was used."
    return AllocateResponse(seat=to_out(allocated_seat), message=message, alternate_zone_used=alternate_used)


@router.post("/release", response_model=SeatOut)
def release(payload: ReleaseRequest, db: Session = Depends(get_db)):
    try:
        seat = alloc_service.release_seat(db, payload.employee_id, payload.seat_id)
        db.commit()
    except alloc_service.NoActiveAllocationError as exc:
        db.rollback()
        raise HTTPException(404, str(exc))
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    db.refresh(seat)
    return to_out(seat)
