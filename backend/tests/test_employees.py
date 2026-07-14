def test_create_and_get_employee(client, employee):
    r = client.get(f"/employees/{employee['id']}")
    assert r.status_code == 200
    assert r.json()["email"] == "amit@ethara.ai"
    assert r.json()["seat_allocation_status"] == "pending"


def test_duplicate_email_rejected(client, employee, project):
    r = client.post(
        "/employees",
        json={
            "name": "Second Person",
            "email": "amit@ethara.ai",
            "department": "Engineering",
            "role": "SDE1",
            "joining_date": "2026-01-01",
            "project_id": project["id"],
        },
    )
    assert r.status_code == 409


def test_search_by_name(client, employee):
    r = client.get("/employees", params={"search": "Amit"})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["email"] == "amit@ethara.ai"


def test_update_employee(client, employee):
    r = client.put(f"/employees/{employee['id']}", json={"department": "Platform"})
    assert r.status_code == 200
    assert r.json()["department"] == "Platform"


def test_deactivate_releases_seat(client, employee, seat):
    client.post("/seats/allocate", json={"employee_id": employee["id"], "seat_id": seat["id"]})
    r = client.delete(f"/employees/{employee['id']}")
    assert r.status_code == 200

    seat_after = client.get(f"/seats/{seat['id']}").json()
    assert seat_after["status"] == "available"
    assert seat_after["allocated_employee_id"] is None

    emp_after = client.get(f"/employees/{employee['id']}").json()
    assert emp_after["status"] == "inactive"


def test_pending_allocation_endpoint(client, employee):
    r = client.get("/employees/pending-allocation")
    assert r.status_code == 200
    assert any(e["id"] == employee["id"] for e in r.json())
