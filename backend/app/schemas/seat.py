from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import SeatStatus


class SeatCreate(BaseModel):
    floor: int
    zone: str
    bay: str
    seat_number: str
    status: SeatStatus = SeatStatus.AVAILABLE


class SeatOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    floor: int
    zone: str
    bay: str
    seat_number: str
    status: SeatStatus
    code: str
    allocated_employee_id: int | None = None
    allocated_employee_name: str | None = None
    allocated_project_id: int | None = None
    allocated_project_name: str | None = None
    allocation_date: datetime | None = None


class AllocateRequest(BaseModel):
    employee_id: int
    seat_id: int | None = None  # if omitted, engine auto-selects best seat
    preferred_floor: int | None = None
    preferred_zone: str | None = None


class AllocateResponse(BaseModel):
    seat: SeatOut
    message: str
    alternate_zone_used: bool = False


class ReleaseRequest(BaseModel):
    employee_id: int | None = None
    seat_id: int | None = None
