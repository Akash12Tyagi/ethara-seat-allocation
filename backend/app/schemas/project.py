from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import ProjectStatus


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    manager_name: str | None = None
    status: ProjectStatus = ProjectStatus.ACTIVE


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    manager_name: str | None
    status: ProjectStatus
    created_at: datetime
    employee_count: int = 0
