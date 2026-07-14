from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Employee, Project
from app.routers.employees import to_out as employee_to_out
from app.schemas.employee import EmployeeOut
from app.schemas.project import ProjectCreate, ProjectOut

router = APIRouter(prefix="/projects", tags=["projects"])


def to_out(project: Project, db: Session) -> ProjectOut:
    count = db.execute(
        select(func.count()).select_from(Employee).where(Employee.project_id == project.id)
    ).scalar_one()
    return ProjectOut(
        id=project.id,
        name=project.name,
        description=project.description,
        manager_name=project.manager_name,
        status=project.status,
        created_at=project.created_at,
        employee_count=count,
    )


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(**payload.model_dump())
    db.add(project)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Project name already exists")
    db.refresh(project)
    return to_out(project, db)


@router.get("", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    projects = db.execute(select(Project).order_by(Project.name)).scalars().all()
    return [to_out(p, db) for p in projects]


@router.get("/{project_id}/employees", response_model=list[EmployeeOut])
def list_project_employees(project_id: int, db: Session = Depends(get_db)):
    if not db.get(Project, project_id):
        raise HTTPException(404, "Project not found")
    employees = db.execute(select(Employee).where(Employee.project_id == project_id)).scalars().all()
    return [employee_to_out(e) for e in employees]
