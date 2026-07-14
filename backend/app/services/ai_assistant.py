"""AI assistant for seat/project queries.

Two tiers, per PDF section 3.7:
  1. If ANTHROPIC_API_KEY is set, Claude rephrases the already-resolved factual answer
     into friendlier prose (see answer_with_llm_or_fallback below).
  2. Otherwise a deterministic rule-based intent parser answers the same question set.
     This is also what actually resolves the *data* in both tiers - the LLM is only used
     to phrase the sentence, never to invent seat/employee facts, so answers stay accurate
     even if the model hallucinates prose.
"""
import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import (
    AllocationStatus,
    Employee,
    Project,
    Seat,
    SeatAllocation,
    SeatStatus,
)

FLOOR_RE = re.compile(r"floor\s*(\d+)", re.I)
ZONE_RE = re.compile(r"zone\s*([a-z0-9]+)", re.I)
PROPER_NOUN_RE = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b")

# Sentence-leading capitalized words that are never part of a person's name.
NAME_STOPWORDS = {
    "Where", "Show", "Who", "How", "Which", "What", "Allocate", "Is", "The",
    "Floor", "Zone", "Project", "Seat", "Seats", "Available", "My",
}


def _find_employee_by_name_or_email(db: Session, text: str) -> Employee | None:
    email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
    if email_match:
        emp = db.execute(select(Employee).where(Employee.email == email_match.group(0).lower())).scalar_one_or_none()
        if emp:
            return emp

    # Prefer full name-shaped phrases ("Kristen Weeks") over single words - with 5,000
    # employees a single first/last name almost never uniquely identifies someone, but a
    # first+last pair almost always does. Longest candidate phrases are tried first.
    candidates = [
        m.group(0)
        for m in PROPER_NOUN_RE.finditer(text)
        if m.group(0) not in NAME_STOPWORDS
    ]
    candidates.sort(key=len, reverse=True)
    for candidate in candidates:
        stmt = select(Employee).where(Employee.name.ilike(f"%{candidate}%")).order_by(Employee.name).limit(5)
        matches = db.execute(stmt).scalars().all()
        if matches:
            return matches[0]

    # Last resort: any word (>2 chars) that uniquely identifies one employee.
    # For 5,000 employees this is a single indexed ILIKE scan, not a full table pull.
    words = [w.strip(",.?!'\"") for w in text.split() if len(w) > 2]
    for w in words:
        stmt = select(Employee).where(Employee.name.ilike(f"%{w}%")).limit(2)
        matches = db.execute(stmt).scalars().all()
        if len(matches) == 1:
            return matches[0]
    return None


def _find_project(db: Session, text: str) -> Project | None:
    projects = db.execute(select(Project)).scalars().all()
    text_low = text.lower()
    for p in projects:
        if p.name.lower() in text_low:
            return p
    return None


def _seat_sentence(emp: Employee) -> str:
    allocation = emp.active_allocation
    if not allocation:
        return f"{emp.name} has not been allocated a seat yet."
    seat = allocation.seat
    project = allocation.project.name if allocation.project else "no project"
    return (
        f"{emp.name} is seated on Floor {seat.floor}, Zone {seat.zone}, Bay {seat.bay}, "
        f"Seat {seat.code}. Assigned to Project {project}."
    )


def answer_query(db: Session, query: str, employee_email: str | None = None) -> tuple[str, str, dict]:
    q = query.strip()
    q_low = q.lower()

    # --- intent: my own seat / who am I ---
    if employee_email and any(k in q_low for k in ["my seat", "where is my", "who am i", "my project"]):
        emp = db.execute(select(Employee).where(Employee.email == employee_email.lower())).scalar_one_or_none()
        if not emp:
            return "I couldn't find an employee with that email.", "self_lookup_not_found", {}
        return _seat_sentence(emp), "self_seat_lookup", {"employee_id": emp.id}

    # --- intent: who is sitting near me / teammates nearby (checked before the
    # generic seat-lookup below, since "sitting near X" would otherwise also match
    # the "sitting" keyword there and short-circuit to a plain seat lookup) ---
    if any(k in q_low for k in ["near me", "sitting near", "nearby", "teammates"]):
        emp = None
        if employee_email:
            emp = db.execute(select(Employee).where(Employee.email == employee_email.lower())).scalar_one_or_none()
        emp = emp or _find_employee_by_name_or_email(db, q)
        if not emp or not emp.active_allocation:
            return "I need a seated employee to find nearby teammates.", "nearby_not_found", {}
        seat = emp.active_allocation.seat
        stmt = (
            select(Employee)
            .join(SeatAllocation, SeatAllocation.employee_id == Employee.id)
            .join(Seat, Seat.id == SeatAllocation.seat_id)
            .where(
                Seat.floor == seat.floor,
                Seat.zone == seat.zone,
                SeatAllocation.allocation_status == AllocationStatus.ACTIVE,
                Employee.id != emp.id,
            )
            .limit(10)
        )
        neighbors = db.execute(stmt).scalars().all()
        if not neighbors:
            return f"No one else is currently seated in {seat.zone} on Floor {seat.floor}.", "nearby_teammates", {}
        names = ", ".join(n.name for n in neighbors)
        return f"Seated near {emp.name} (Floor {seat.floor}, Zone {seat.zone}): {names}", "nearby_teammates", {}

    # --- intent: where is employee X seated ---
    if any(k in q_low for k in ["where is", "seated", "seat of", "sitting"]):
        emp = _find_employee_by_name_or_email(db, q)
        if emp:
            return _seat_sentence(emp), "employee_seat_lookup", {"employee_id": emp.id}
        return (
            "I couldn't identify that employee. Try including their full name or email.",
            "employee_seat_lookup_not_found",
            {},
        )

    # --- intent: which project is X assigned to ---
    if "project" in q_low and any(k in q_low for k in ["assigned", "which project", "what project", "belong"]):
        emp = _find_employee_by_name_or_email(db, q)
        if emp:
            proj = emp.project.name if emp.project else "no project"
            return f"{emp.name} is assigned to Project {proj}.", "employee_project_lookup", {"employee_id": emp.id}
        return "I couldn't identify that employee.", "employee_project_lookup_not_found", {}

    # --- intent: seat utilization for a project ---
    if any(k in q_low for k in ["utilization", "how many seats", "occupied for", "seats are occupied"]):
        project = _find_project(db, q)
        if project:
            total = db.execute(
                select(func.count()).select_from(Employee).where(Employee.project_id == project.id)
            ).scalar_one()
            allocated = db.execute(
                select(func.count())
                .select_from(SeatAllocation)
                .where(SeatAllocation.project_id == project.id, SeatAllocation.allocation_status == AllocationStatus.ACTIVE)
            ).scalar_one()
            return (
                f"Project {project.name} has {allocated} occupied seat(s) out of {total} employee(s).",
                "project_utilization",
                {"project_id": project.id, "allocated": allocated, "total": total},
            )
        return "Which project did you mean? Please name it explicitly.", "project_utilization_not_found", {}

    # --- intent: available seats on floor/zone ---
    if "available" in q_low and ("seat" in q_low or "floor" in q_low or "zone" in q_low):
        floor_m = FLOOR_RE.search(q)
        zone_m = ZONE_RE.search(q)
        stmt = select(Seat).where(Seat.status == SeatStatus.AVAILABLE)
        if floor_m:
            stmt = stmt.where(Seat.floor == int(floor_m.group(1)))
        if zone_m:
            stmt = stmt.where(Seat.zone.ilike(zone_m.group(1)))
        seats = db.execute(stmt.order_by(Seat.floor, Seat.zone, Seat.seat_number).limit(20)).scalars().all()
        if not seats:
            return "No available seats matched that filter.", "available_seats", {"count": 0}
        codes = ", ".join(s.code for s in seats[:10])
        more = f" (+{len(seats) - 10} more)" if len(seats) > 10 else ""
        scope = f"Floor {floor_m.group(1)} " if floor_m else ""
        scope += f"Zone {zone_m.group(1)} " if zone_m else ""
        return (
            f"There are {len(seats)} available seat(s) {('on ' + scope) if scope else ''}: {codes}{more}",
            "available_seats",
            {"count": len(seats), "seat_ids": [s.id for s in seats]},
        )

    # --- intent: allocate a seat for a new employee ---
    if "allocate" in q_low and ("new" in q_low or "seat for" in q_low):
        emp = _find_employee_by_name_or_email(db, q)
        if not emp:
            return (
                "Tell me which employee (name or email) needs a seat allocated.",
                "allocate_needs_employee",
                {},
            )
        from app.services import allocation as alloc_service

        try:
            seat, alt = alloc_service.allocate_seat(db, emp)
            db.commit()
        except alloc_service.EmployeeAlreadyAllocatedError:
            return f"{emp.name} already has an active seat.", "allocate_already_has_seat", {}
        except alloc_service.NoSeatAvailableError:
            return "No seats are available anywhere right now.", "allocate_no_seats", {}
        msg = f"Allocated Seat {seat.code} (Floor {seat.floor}, Zone {seat.zone}) to {emp.name}."
        if alt:
            msg += " Preferred zone was full, so an alternate zone was used."
        return msg, "allocate_new_joiner", {"seat_id": seat.id, "employee_id": emp.id}

    return (
        "I can help with: 'Where is <employee> seated?', 'Which project is <employee> assigned to?', "
        "'Show available seats on Floor X', 'Who is sitting near <employee>?', "
        "'How many seats are occupied for Project X?', or 'Allocate a seat for <employee>'.",
        "unknown",
        {},
    )


def answer_with_llm_or_fallback(db: Session, query: str, employee_email: str | None = None) -> tuple[str, str, dict]:
    answer, intent, data = answer_query(db, query, employee_email)

    settings = get_settings()
    if not settings.anthropic_api_key or intent in ("unknown",):
        return answer, intent, data

    # Claude only rephrases the already-resolved factual answer - it cannot alter the data,
    # so answers stay accurate even in the (unlikely) case the model drifts in prose.
    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=settings.anthropic_api_key)
        message = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=120,
            system=(
                "You are Ethara's workplace assistant. Rephrase the given factual answer "
                "in one or two friendly, professional sentences. Do not add any facts "
                "that are not already present in the answer."
            ),
            messages=[{"role": "user", "content": f"Question: {query}\nFactual answer: {answer}"}],
        )
        if message.stop_reason != "refusal":
            polished = next((block.text for block in message.content if block.type == "text"), None)
            if polished:
                return polished.strip(), intent, data
    except Exception:  # noqa: BLE001 - network/quota/refusal errors fall back to the deterministic answer
        pass
    return answer, intent, data
