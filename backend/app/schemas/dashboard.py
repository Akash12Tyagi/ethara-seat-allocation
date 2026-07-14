from pydantic import BaseModel


class DashboardSummary(BaseModel):
    total_employees: int
    active_employees: int
    total_seats: int
    occupied_seats: int
    available_seats: int
    reserved_seats: int
    maintenance_seats: int
    pending_allocation: int


class ProjectUtilization(BaseModel):
    project_id: int
    project_name: str
    employee_count: int
    allocated_seats: int
    utilization_pct: float


class FloorUtilization(BaseModel):
    floor: int
    total_seats: int
    occupied_seats: int
    available_seats: int
    reserved_seats: int
    maintenance_seats: int
    occupancy_pct: float


class RecentAllocation(BaseModel):
    employee_name: str
    seat_code: str
    project_name: str | None
    allocation_date: str
    action: str  # "allocated" | "released"
