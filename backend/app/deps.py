from enum import Enum

from fastapi import Header


class Role(str, Enum):
    ADMIN = "admin"
    HR = "hr"
    EMPLOYEE = "employee"


def get_role(x_role: str | None = Header(default="employee")) -> Role:
    """Lightweight role signal via header instead of full auth (see REQUIREMENTS.md Known Gaps).
    Not a security boundary — good enough to distinguish HR/Admin views from employee self-service."""
    try:
        return Role(x_role.lower()) if x_role else Role.EMPLOYEE
    except ValueError:
        return Role.EMPLOYEE
