"""Covers business rules B1-B5 from REQUIREMENTS.md."""


def test_allocate_and_release(client, employee, seat):
    r = client.post("/seats/allocate", json={"employee_id": employee["id"], "seat_id": seat["id"]})
    assert r.status_code == 200
    assert r.json()["seat"]["status"] == "occupied"
    assert r.json()["seat"]["allocated_employee_id"] == employee["id"]

    emp = client.get(f"/employees/{employee['id']}").json()
    assert emp["seat_allocation_status"] == "allocated"

    r = client.post("/seats/release", json={"employee_id": employee["id"]})
    assert r.status_code == 200
    assert r.json()["status"] == "available"  # B3: released seats become available again

    emp = client.get(f"/employees/{employee['id']}").json()
    assert emp["seat_allocation_status"] == "pending"


def test_one_active_seat_per_employee(client, employee, seat):
    client.post("/seats/allocate", json={"employee_id": employee["id"], "seat_id": seat["id"]})
    second = client.post("/seats", json={"floor": 2, "zone": "B", "bay": "4", "seat_number": "24"}).json()

    r = client.post("/seats/allocate", json={"employee_id": employee["id"], "seat_id": second["id"]})
    assert r.status_code == 409  # B1


def test_one_active_employee_per_seat(client, employee, seat, project):
    client.post("/seats/allocate", json={"employee_id": employee["id"], "seat_id": seat["id"]})
    other = client.post(
        "/employees",
        json={
            "name": "Second Person",
            "email": "second@ethara.ai",
            "department": "Engineering",
            "role": "SDE1",
            "joining_date": "2026-01-01",
            "project_id": project["id"],
        },
    ).json()

    r = client.post("/seats/allocate", json={"employee_id": other["id"], "seat_id": seat["id"]})
    assert r.status_code == 409  # B2


def test_reserved_seat_cannot_be_allocated(client, employee):
    reserved = client.post(
        "/seats", json={"floor": 3, "zone": "C", "bay": "1", "seat_number": "1", "status": "reserved"}
    ).json()
    r = client.post("/seats/allocate", json={"employee_id": employee["id"], "seat_id": reserved["id"]})
    assert r.status_code == 409  # B4


def test_maintenance_seat_cannot_be_allocated(client, employee):
    seat = client.post(
        "/seats", json={"floor": 3, "zone": "C", "bay": "1", "seat_number": "2", "status": "maintenance"}
    ).json()
    r = client.post("/seats/allocate", json={"employee_id": employee["id"], "seat_id": seat["id"]})
    assert r.status_code == 409


def test_release_with_no_active_allocation_404(client, employee):
    r = client.post("/seats/release", json={"employee_id": employee["id"]})
    assert r.status_code == 404


def test_duplicate_seat_number_same_floor_zone_rejected(client):
    client.post("/seats", json={"floor": 1, "zone": "A", "bay": "1", "seat_number": "5"})
    r = client.post("/seats", json={"floor": 1, "zone": "A", "bay": "2", "seat_number": "5"})
    assert r.status_code == 409  # B7


def test_same_seat_number_different_zone_allowed(client):
    r1 = client.post("/seats", json={"floor": 1, "zone": "A", "bay": "1", "seat_number": "5"})
    r2 = client.post("/seats", json={"floor": 1, "zone": "B", "bay": "1", "seat_number": "5"})
    assert r1.status_code == 201
    assert r2.status_code == 201


def test_auto_select_prioritizes_project_teammates(client, project):
    """B5: new joiners should land near existing teammates on the same project."""
    zone_a_seat = client.post("/seats", json={"floor": 1, "zone": "A", "bay": "1", "seat_number": "1"}).json()
    client.post("/seats", json={"floor": 1, "zone": "B", "bay": "1", "seat_number": "1"})  # zone B seat, unused

    teammate = client.post(
        "/employees",
        json={
            "name": "Teammate One",
            "email": "teammate@ethara.ai",
            "department": "Engineering",
            "role": "SDE1",
            "joining_date": "2026-01-01",
            "project_id": project["id"],
        },
    ).json()
    client.post("/seats/allocate", json={"employee_id": teammate["id"], "seat_id": zone_a_seat["id"]})

    # second seat in zone A so the new joiner has somewhere to land next to their teammate
    zone_a_seat_2 = client.post("/seats", json={"floor": 1, "zone": "A", "bay": "1", "seat_number": "2"}).json()

    newcomer = client.post(
        "/employees",
        json={
            "name": "New Joiner",
            "email": "newcomer@ethara.ai",
            "department": "Engineering",
            "role": "SDE1",
            "joining_date": "2026-01-01",
            "project_id": project["id"],
        },
    ).json()

    r = client.post("/seats/allocate", json={"employee_id": newcomer["id"]})  # no seat_id -> auto-select
    assert r.status_code == 200
    assert r.json()["seat"]["id"] == zone_a_seat_2["id"]
    assert r.json()["alternate_zone_used"] is False


def test_no_seats_available_anywhere(client, employee):
    r = client.post("/seats/allocate", json={"employee_id": employee["id"]})
    assert r.status_code == 409
