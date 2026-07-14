import csv
import io
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AllocationStatus, Employee, EmploymentStatus, Project
from app.schemas.employee import EmployeeCreate, EmployeeOut, EmployeeUpdate

router = APIRouter(prefix="/employees", tags=["employees"])


def _next_employee_code(db: Session) -> str:
    count = db.execute(select(func.count()).select_from(Employee)).scalar_one()
    return f"ETH{count + 1:05d}"


def to_out(emp: Employee) -> EmployeeOut:
    allocation = emp.active_allocation
    return EmployeeOut(
        id=emp.id,
        employee_code=emp.employee_code,
        name=emp.name,
        email=emp.email,
        department=emp.department,
        role=emp.role,
        joining_date=emp.joining_date,
        status=emp.status,
        project_id=emp.project_id,
        project_name=emp.project.name if emp.project else None,
        seat=allocation.seat if allocation else None,
        seat_allocation_status="allocated" if allocation else "pending",
        created_at=emp.created_at,
        updated_at=emp.updated_at,
    )


@router.post("", response_model=EmployeeOut, status_code=status.HTTP_201_CREATED)
def create_employee(payload: EmployeeCreate, db: Session = Depends(get_db)):
    if payload.project_id is not None and not db.get(Project, payload.project_id):
        raise HTTPException(404, "Project not found")

    employee = Employee(
        employee_code=payload.employee_code or _next_employee_code(db),
        name=payload.name,
        email=payload.email,
        department=payload.department,
        role=payload.role,
        joining_date=payload.joining_date,
        status=payload.status,
        project_id=payload.project_id,
    )
    db.add(employee)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Employee with this email or code already exists")
    db.refresh(employee)
    return to_out(employee)


@router.get("", response_model=dict)
def list_employees(
    db: Session = Depends(get_db),
    search: str | None = Query(None, description="matches name, employee_code, or email"),
    project_id: int | None = None,
    department: str | None = None,
    status_filter: EmploymentStatus | None = Query(None, alias="status"),
    seat_status: str | None = Query(None, description="'allocated' or 'pending'"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
):
    stmt = select(Employee)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            or_(Employee.name.ilike(like), Employee.employee_code.ilike(like), Employee.email.ilike(like))
        )
    if project_id is not None:
        stmt = stmt.where(Employee.project_id == project_id)
    if department:
        stmt = stmt.where(Employee.department == department)
    if status_filter:
        stmt = stmt.where(Employee.status == status_filter)

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()

    stmt = stmt.order_by(Employee.id).offset((page - 1) * page_size).limit(page_size)
    employees = db.execute(stmt).scalars().all()

    results = [to_out(e) for e in employees]
    if seat_status in ("allocated", "pending"):
        results = [r for r in results if r.seat_allocation_status == seat_status]

    return {
        "items": results,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }


@router.get("/pending-allocation", response_model=list[EmployeeOut])
def pending_allocation(db: Session = Depends(get_db), limit: int = 100):
    stmt = select(Employee).where(Employee.status == EmploymentStatus.ACTIVE)
    employees = db.execute(stmt).scalars().all()
    pending = [e for e in employees if e.active_allocation is None]
    return [to_out(e) for e in pending[:limit]]


@router.get("/{employee_id}", response_model=EmployeeOut)
def get_employee(employee_id: int, db: Session = Depends(get_db)):
    employee = db.get(Employee, employee_id)
    if not employee:
        raise HTTPException(404, "Employee not found")
    return to_out(employee)


@router.put("/{employee_id}", response_model=EmployeeOut)
def update_employee(employee_id: int, payload: EmployeeUpdate, db: Session = Depends(get_db)):
    employee = db.get(Employee, employee_id)
    if not employee:
        raise HTTPException(404, "Employee not found")
    if payload.project_id is not None and not db.get(Project, payload.project_id):
        raise HTTPException(404, "Project not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(employee, field, value)

    db.add(employee)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Email already in use by another employee")
    db.refresh(employee)
    return to_out(employee)


@router.delete("/{employee_id}", status_code=status.HTTP_200_OK)
def deactivate_employee(employee_id: int, db: Session = Depends(get_db)):
    """Soft-delete: marks employment inactive and releases any active seat."""
    from app.services.allocation import NoActiveAllocationError, release_seat

    employee = db.get(Employee, employee_id)
    if not employee:
        raise HTTPException(404, "Employee not found")

    employee.status = EmploymentStatus.INACTIVE
    db.add(employee)
    try:
        release_seat(db, employee_id=employee_id)
    except NoActiveAllocationError:
        pass
    db.commit()
    return {"message": f"Employee {employee.employee_code} deactivated"}


@router.post("/csv-upload", status_code=status.HTTP_201_CREATED)
def csv_upload(file: UploadFile, db: Session = Depends(get_db)):
    """Bulk-create employees from a CSV with columns:
    name,email,department,role,joining_date(YYYY-MM-DD),project_name"""
    content = file.file.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))

    projects_by_name = {p.name: p for p in db.execute(select(Project)).scalars().all()}
    created, errors = 0, []
    for i, row in enumerate(reader, start=2):
        try:
            project = projects_by_name.get((row.get("project_name") or "").strip())
            employee = Employee(
                employee_code=_next_employee_code(db),
                name=row["name"].strip(),
                email=row["email"].strip().lower(),
                department=row.get("department", "").strip() or "Unassigned",
                role=row.get("role", "").strip() or "Employee",
                joining_date=date.fromisoformat(row["joining_date"].strip()),
                project_id=project.id if project else None,
            )
            db.add(employee)
            db.flush()
            created += 1
        except Exception as exc:  # noqa: BLE001 - collect row-level errors, keep importing
            db.rollback()
            errors.append(f"row {i}: {exc}")
    db.commit()
    return {"created": created, "errors": errors}
