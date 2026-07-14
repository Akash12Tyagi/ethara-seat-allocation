"""Seed the database with realistic demo data per REQUIREMENTS.md section 7:
  - 5,000 employees   - 5 floors   - 10 zones   - >=5,500 seats (we create 5,600)
  - >=10 projects (we create the 11 named in the PDF)
  - >=500 available seats, >=100 reserved seats, >=50 employees pending allocation

Run:  python seed.py [--reset]
"""
import argparse
import random
import sys
from datetime import date, timedelta

from faker import Faker
from sqlalchemy import delete

from app.database import Base, SessionLocal, engine
from app.models import (
    AllocationStatus,
    Employee,
    EmploymentStatus,
    Project,
    ProjectStatus,
    Seat,
    SeatAllocation,
    SeatStatus,
)

fake = Faker()
Faker.seed(42)
random.seed(42)

PROJECT_NAMES = [
    "Indigo", "Indreed", "Mydreed", "Preed", "Serfy",
    "Oreed", "bedegreed", "Opreed", "Serry", "Kaary", "Mered",
]
DEPARTMENTS = ["Engineering", "QA", "Product", "Design", "DevOps", "Data", "Support", "HR", "Finance"]
ROLES = ["Associate", "Senior Associate", "Team Lead", "Manager", "SDE1", "SDE2", "SDE3", "Analyst"]

FLOORS = [1, 2, 3, 4, 5]
ZONES_PER_FLOOR = 2
ZONE_LETTERS = list("ABCDEFGHIJ")  # 10 distinct zones total (2 per floor)
SEATS_PER_ZONE = 560  # 5 floors * 2 zones * 560 = 5,600 seats total
BAY_SIZE = 8  # seats per bay cluster

TOTAL_EMPLOYEES = 5000
INACTIVE_EMPLOYEES = 90
PENDING_ALLOCATION = 60  # active employees with no seat (>= 50 required)
RESERVED_SEATS = 120
MAINTENANCE_SEATS = 30


def reset_data(db):
    db.execute(delete(SeatAllocation))
    db.execute(delete(Employee))
    db.execute(delete(Seat))
    db.execute(delete(Project))
    db.commit()


def create_projects(db) -> list[Project]:
    projects = [Project(name=name, manager_name=fake.name(), status=ProjectStatus.ACTIVE) for name in PROJECT_NAMES]
    db.add_all(projects)
    db.commit()
    for p in projects:
        db.refresh(p)
    return projects


def create_seats(db) -> list[Seat]:
    seats = []
    zone_idx = 0
    zone_by_floor: dict[int, list[str]] = {}
    for floor in FLOORS:
        zone_by_floor[floor] = ZONE_LETTERS[zone_idx : zone_idx + ZONES_PER_FLOOR]
        zone_idx += ZONES_PER_FLOOR

    for floor in FLOORS:
        for zone in zone_by_floor[floor]:
            for n in range(1, SEATS_PER_ZONE + 1):
                bay = str((n - 1) // BAY_SIZE + 1)
                seats.append(
                    Seat(floor=floor, zone=zone, bay=bay, seat_number=str(n), status=SeatStatus.AVAILABLE)
                )

    db.bulk_save_objects(seats)
    db.commit()
    return db.query(Seat).order_by(Seat.floor, Seat.zone, Seat.id).all()


def create_employees(db, projects: list[Project]) -> list[Employee]:
    employees = []
    used_emails = set()
    project_cycle = projects * ((TOTAL_EMPLOYEES // len(projects)) + 1)
    random.shuffle(project_cycle)

    # Scatter inactive employees randomly across the ID range rather than the first N -
    # otherwise every default (id-ascending) list view opens on a wall of departed,
    # unallocated employees, which reads as broken data rather than a realistic mix.
    inactive_ids = set(random.sample(range(1, TOTAL_EMPLOYEES + 1), INACTIVE_EMPLOYEES))

    for i in range(1, TOTAL_EMPLOYEES + 1):
        first, last = fake.first_name(), fake.last_name()
        email = f"{first}.{last}{i}@ethara.ai".lower()
        while email in used_emails:
            email = f"{first}.{last}{i}.{random.randint(1,9999)}@ethara.ai".lower()
        used_emails.add(email)

        status = EmploymentStatus.INACTIVE if i in inactive_ids else EmploymentStatus.ACTIVE
        joining_date = date.today() - timedelta(days=random.randint(0, 5 * 365))

        employees.append(
            Employee(
                employee_code=f"ETH{i:05d}",
                name=f"{first} {last}",
                email=email,
                department=random.choice(DEPARTMENTS),
                role=random.choice(ROLES),
                joining_date=joining_date,
                status=status,
                project_id=project_cycle[i - 1].id,
            )
        )

    db.bulk_save_objects(employees)
    db.commit()
    return db.query(Employee).order_by(Employee.id).all()


def allocate_seats(db, employees: list[Employee], seats: list[Seat], projects: list[Project]):
    """Cluster each project's employees into a home floor/zone (mirrors the real
    allocation engine's proximity rule), then allocate seats there, spilling into
    other zones once the home zone fills up.

    Every seat lives in exactly one zone bucket (seats_by_zone) - both the home-zone
    path and the overflow path pop from those same buckets, so a seat can never be
    handed to two employees (unlike an earlier version that used a second, separately
    tracked "overflow pool" referencing the same objects - that double-booked seats
    and tripped the uq_active_allocation_per_seat constraint)."""
    seats_by_zone: dict[tuple[int, str], list[Seat]] = {}
    for s in seats:
        seats_by_zone.setdefault((s.floor, s.zone), []).append(s)
    for bucket in seats_by_zone.values():
        random.shuffle(bucket)
    zone_keys = list(seats_by_zone.keys())

    home_zone_by_project = {p.id: zone_keys[i % len(zone_keys)] for i, p in enumerate(projects)}

    active_employees = [e for e in employees if e.status == EmploymentStatus.ACTIVE]
    random.shuffle(active_employees)
    to_allocate = active_employees[: len(active_employees) - PENDING_ALLOCATION]

    allocations = []
    for emp in to_allocate:
        home_zone = home_zone_by_project.get(emp.project_id)
        seat = None
        if home_zone and seats_by_zone[home_zone]:
            seat = seats_by_zone[home_zone].pop()
        else:
            for zone_key in zone_keys:
                if seats_by_zone[zone_key]:
                    seat = seats_by_zone[zone_key].pop()
                    break
        if seat is None:
            continue  # no seats left anywhere - remaining employees stay pending

        seat.status = SeatStatus.OCCUPIED
        allocations.append(
            SeatAllocation(
                employee_id=emp.id,
                seat_id=seat.id,
                project_id=emp.project_id,
                allocation_status=AllocationStatus.ACTIVE,
                allocation_date=fake.date_time_between(start_date="-1y", end_date="now"),
            )
        )

    db.bulk_save_objects(allocations)
    db.commit()


def mark_reserved_and_maintenance(db, seats: list[Seat]):
    remaining_available = [s for s in seats if s.status == SeatStatus.AVAILABLE]
    random.shuffle(remaining_available)

    for s in remaining_available[:RESERVED_SEATS]:
        s.status = SeatStatus.RESERVED
    for s in remaining_available[RESERVED_SEATS : RESERVED_SEATS + MAINTENANCE_SEATS]:
        s.status = SeatStatus.MAINTENANCE

    # These Seat instances are already attached to the session (loaded via query in
    # create_seats), so mutating .status is enough - commit() flushes the changes.
    db.commit()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="wipe existing data first")
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if args.reset:
            print("Resetting existing data...")
            reset_data(db)
        elif db.query(Employee).count() > 0:
            print("Database already has employees. Re-run with --reset to wipe and reseed.")
            sys.exit(1)

        print("Creating projects...")
        projects = create_projects(db)

        print("Creating seats...")
        seats = create_seats(db)
        print(f"  {len(seats)} seats created")

        print("Creating employees...")
        employees = create_employees(db, projects)
        print(f"  {len(employees)} employees created")

        print("Allocating seats...")
        allocate_seats(db, employees, seats, projects)

        print("Marking reserved/maintenance seats...")
        # Re-query: seat.status was mutated in Python during allocate_seats, but the
        # session expires attributes on commit, so pull fresh rows before filtering.
        seats = db.query(Seat).order_by(Seat.floor, Seat.zone, Seat.id).all()
        mark_reserved_and_maintenance(db, seats)

        occupied = db.query(Seat).filter(Seat.status == SeatStatus.OCCUPIED).count()
        available = db.query(Seat).filter(Seat.status == SeatStatus.AVAILABLE).count()
        reserved = db.query(Seat).filter(Seat.status == SeatStatus.RESERVED).count()
        maintenance = db.query(Seat).filter(Seat.status == SeatStatus.MAINTENANCE).count()
        print(
            f"\nDone. seats: total={len(seats)} occupied={occupied} available={available} "
            f"reserved={reserved} maintenance={maintenance}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
