from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.models import EmploymentStatus


class EmployeeBase(BaseModel):
    name: str
    email: EmailStr
    department: str
    role: str
    joining_date: date
    status: EmploymentStatus = EmploymentStatus.ACTIVE
    project_id: int | None = None

    @field_validator("name", "department", "role")
    @classmethod
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v


class EmployeeCreate(EmployeeBase):
    employee_code: str | None = None  # auto-generated if omitted


class EmployeeUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    department: str | None = None
    role: str | None = None
    status: EmploymentStatus | None = None
    project_id: int | None = None


class SeatSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    floor: int
    zone: str
    bay: str
    seat_number: str
    code: str


class EmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_code: str
    name: str
    email: str
    department: str
    role: str
    joining_date: date
    status: EmploymentStatus
    project_id: int | None
    project_name: str | None = None
    seat: SeatSummary | None = None
    seat_allocation_status: str  # "allocated" | "pending"
    created_at: datetime
    updated_at: datetime
