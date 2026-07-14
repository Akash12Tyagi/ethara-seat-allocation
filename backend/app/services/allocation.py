"""Seat allocation engine.

Core rules enforced here (see REQUIREMENTS.md section 3):
  B1 one active seat per employee, B2 one active employee per seat,
  B3 released seats become available again, B4 reserved/maintenance seats
  cannot be allocated, B5 new joiners are prioritized near their project team.

Algorithm for auto-selection (`suggest_and_allocate` / `best_seat_for_employee`):
  1. Find the floor+zone with the most active teammates on the employee's project
     (a GROUP BY/COUNT query - O(zones) rows, trivially fast even at 5-10k seats).
  2. Look for an AVAILABLE seat in that floor+zone first.
  3. If none, widen to the same floor (any zone).
  4. If still none, widen to any floor/zone in the building (alternate_zone_used=True).
  5. If nothing is AVAILABLE anywhere, raise NoSeatAvailableError.
Each step is a single indexed query (seats has an index on floor+zone and on status),
so allocation stays O(log n) per step rather than scanning all 5,500 seats.
"""
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    AllocationStatus,
    Employee,
    Seat,
    SeatAllocation,
    SeatStatus,
)


class AllocationError(Exception):
    """Base class for allocation failures the API layer turns into 4xx responses."""


class EmployeeAlreadyAllocatedError(AllocationError):
    pass


class SeatNotAvailableError(AllocationError):
    pass


class NoSeatAvailableError(AllocationError):
    pass


class NoActiveAllocationError(AllocationError):
    pass


def get_active_allocation_for_employee(db: Session, employee_id: int) -> SeatAllocation | None:
    stmt = select(SeatAllocation).where(
        SeatAllocation.employee_id == employee_id,
        SeatAllocation.allocation_status == AllocationStatus.ACTIVE,
    )
    return db.execute(stmt).scalar_one_or_none()


def get_active_allocation_for_seat(db: Session, seat_id: int) -> SeatAllocation | None:
    stmt = select(SeatAllocation).where(
        SeatAllocation.seat_id == seat_id,
        SeatAllocation.allocation_status == AllocationStatus.ACTIVE,
    )
    return db.execute(stmt).scalar_one_or_none()


def _preferred_zone_for_project(db: Session, project_id: int) -> tuple[int, str] | None:
    """Floor+zone with the most active teammates on this project."""
    stmt = (
        select(Seat.floor, Seat.zone, func.count(SeatAllocation.id).label("cnt"))
        .join(SeatAllocation, SeatAllocation.seat_id == Seat.id)
        .where(
            SeatAllocation.project_id == project_id,
            SeatAllocation.allocation_status == AllocationStatus.ACTIVE,
        )
        .group_by(Seat.floor, Seat.zone)
        .order_by(func.count(SeatAllocation.id).desc())
        .limit(1)
    )
    row = db.execute(stmt).first()
    return (row.floor, row.zone) if row else None


def _first_available_seat(
    db: Session, floor: int | None = None, zone: str | None = None
) -> Seat | None:
    stmt = select(Seat).where(Seat.status == SeatStatus.AVAILABLE)
    if floor is not None:
        stmt = stmt.where(Seat.floor == floor)
    if zone is not None:
        stmt = stmt.where(Seat.zone == zone)
    stmt = stmt.order_by(Seat.floor, Seat.zone, Seat.bay, Seat.seat_number).limit(1)
    return db.execute(stmt).scalar_one_or_none()


def best_seat_for_employee(
    db: Session,
    employee: Employee,
    preferred_floor: int | None = None,
    preferred_zone: str | None = None,
) -> tuple[Seat, bool]:
    """Returns (seat, alternate_zone_used)."""
    # 1. explicit preference wins
    if preferred_floor is not None or preferred_zone is not None:
        seat = _first_available_seat(db, preferred_floor, preferred_zone)
        if seat:
            return seat, False

    # 2. project-teammate proximity
    zone_pref = None
    if employee.project_id:
        zone_pref = _preferred_zone_for_project(db, employee.project_id)
    if zone_pref:
        floor, zone = zone_pref
        seat = _first_available_seat(db, floor, zone)
        if seat:
            return seat, False
        # 3. same floor, any zone
        seat = _first_available_seat(db, floor=floor)
        if seat:
            return seat, True

    # 4. anywhere in the building. Only counts as "alternate zone" if we actually had
    # a preference (explicit or teammate-derived) that we're overriding - a brand new
    # project with no seated teammates yet has no preference to override.
    seat = _first_available_seat(db)
    if seat:
        had_preference = preferred_floor is not None or preferred_zone is not None or zone_pref is not None
        return seat, had_preference

    raise NoSeatAvailableError("No available seats in any floor or zone.")


def allocate_seat(
    db: Session,
    employee: Employee,
    seat: Seat | None = None,
    preferred_floor: int | None = None,
    preferred_zone: str | None = None,
) -> tuple[Seat, bool]:
    """Allocate `seat` to `employee`, or auto-select the best seat if seat is None.
    Returns (seat, alternate_zone_used)."""
    if get_active_allocation_for_employee(db, employee.id):
        raise EmployeeAlreadyAllocatedError(
            f"Employee {employee.employee_code} already has an active seat."
        )

    alternate_zone_used = False
    if seat is None:
        seat, alternate_zone_used = best_seat_for_employee(
            db, employee, preferred_floor, preferred_zone
        )
    elif seat.status != SeatStatus.AVAILABLE:
        raise SeatNotAvailableError(f"Seat {seat.code} is {seat.status.value}, not available.")

    allocation = SeatAllocation(
        employee_id=employee.id,
        seat_id=seat.id,
        project_id=employee.project_id,
        allocation_status=AllocationStatus.ACTIVE,
        allocation_date=datetime.now(timezone.utc),
    )
    seat.status = SeatStatus.OCCUPIED
    db.add(allocation)
    db.add(seat)
    db.flush()
    return seat, alternate_zone_used


def release_seat(
    db: Session, employee_id: int | None = None, seat_id: int | None = None
) -> Seat:
    if employee_id is not None:
        allocation = get_active_allocation_for_employee(db, employee_id)
    elif seat_id is not None:
        allocation = get_active_allocation_for_seat(db, seat_id)
    else:
        raise ValueError("employee_id or seat_id required")

    if allocation is None:
        raise NoActiveAllocationError("No active allocation found to release.")

    allocation.allocation_status = AllocationStatus.RELEASED
    allocation.released_date = datetime.now(timezone.utc)
    seat = allocation.seat
    seat.status = SeatStatus.AVAILABLE
    db.add(allocation)
    db.add(seat)
    db.flush()
    return seat
