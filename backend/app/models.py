import enum
from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _enum(py_enum: type[enum.Enum], **kw):
    """Store the lowercase .value in the DB (not the member NAME) so API values,
    DB rows, and partial-index predicates all agree."""
    return Enum(py_enum, native_enum=False, values_callable=lambda e: [m.value for m in e], **kw)


class EmploymentStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class ProjectStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class SeatStatus(str, enum.Enum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    RESERVED = "reserved"
    MAINTENANCE = "maintenance"


class AllocationStatus(str, enum.Enum):
    ACTIVE = "active"
    RELEASED = "released"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    manager_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(_enum(ProjectStatus), default=ProjectStatus.ACTIVE)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    employees: Mapped[list["Employee"]] = relationship(back_populates="project")


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(150), index=True)
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    department: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(100))
    joining_date: Mapped[date] = mapped_column(Date)
    status: Mapped[EmploymentStatus] = mapped_column(
        _enum(EmploymentStatus), default=EmploymentStatus.ACTIVE, index=True
    )
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    project: Mapped[Project | None] = relationship(back_populates="employees")
    allocations: Mapped[list["SeatAllocation"]] = relationship(back_populates="employee")

    @property
    def active_allocation(self) -> "SeatAllocation | None":
        for a in self.allocations:
            if a.allocation_status == AllocationStatus.ACTIVE:
                return a
        return None


class Seat(Base):
    __tablename__ = "seats"
    __table_args__ = (
        UniqueConstraint("floor", "zone", "seat_number", name="uq_seat_floor_zone_number"),
        Index("ix_seat_floor_zone", "floor", "zone"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    floor: Mapped[int] = mapped_column(index=True)
    zone: Mapped[str] = mapped_column(String(10), index=True)
    bay: Mapped[str] = mapped_column(String(10))
    seat_number: Mapped[str] = mapped_column(String(20))
    status: Mapped[SeatStatus] = mapped_column(_enum(SeatStatus), default=SeatStatus.AVAILABLE, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    allocations: Mapped[list["SeatAllocation"]] = relationship(back_populates="seat")

    @property
    def code(self) -> str:
        return f"{self.zone}{self.bay}-{self.seat_number}"


class SeatAllocation(Base):
    __tablename__ = "seat_allocations"
    __table_args__ = (
        # Business rules: one ACTIVE allocation per employee, and per seat.
        Index(
            "uq_active_allocation_per_employee",
            "employee_id",
            unique=True,
            sqlite_where=text("allocation_status = 'active'"),
            postgresql_where=text("allocation_status = 'active'"),
        ),
        Index(
            "uq_active_allocation_per_seat",
            "seat_id",
            unique=True,
            sqlite_where=text("allocation_status = 'active'"),
            postgresql_where=text("allocation_status = 'active'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    seat_id: Mapped[int] = mapped_column(ForeignKey("seats.id"), index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    allocation_status: Mapped[AllocationStatus] = mapped_column(
        _enum(AllocationStatus), default=AllocationStatus.ACTIVE, index=True
    )
    allocation_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    released_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    employee: Mapped[Employee] = relationship(back_populates="allocations")
    seat: Mapped[Seat] = relationship(back_populates="allocations")
    project: Mapped[Project | None] = relationship()
