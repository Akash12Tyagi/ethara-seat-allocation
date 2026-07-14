def test_ai_seat_lookup(client, employee, seat):
    client.post("/seats/allocate", json={"employee_id": employee["id"], "seat_id": seat["id"]})
    r = client.post("/ai/query", json={"query": "Where is Amit Sharma seated?"})
    assert r.status_code == 200
    body = r.json()
    assert body["intent"] == "employee_seat_lookup"
    assert "Floor 2" in body["answer"]
    assert "B4-23" in body["answer"]


def test_ai_self_seat_lookup_with_email(client, employee, seat):
    client.post("/seats/allocate", json={"employee_id": employee["id"], "seat_id": seat["id"]})
    r = client.post("/ai/query", json={"query": "Where is my seat?", "employee_email": "amit@ethara.ai"})
    assert r.json()["intent"] == "self_seat_lookup"


def test_ai_unallocated_employee(client, employee):
    r = client.post("/ai/query", json={"query": "Where is Amit Sharma seated?"})
    assert "not been allocated" in r.json()["answer"]


def test_ai_project_lookup(client, employee, project):
    r = client.post("/ai/query", json={"query": "Which project is Amit Sharma assigned to?"})
    assert r.json()["intent"] == "employee_project_lookup"
    assert project["name"] in r.json()["answer"]


def test_ai_available_seats_by_floor(client, seat):
    r = client.post("/ai/query", json={"query": "Show all available seats on Floor 2."})
    assert r.json()["intent"] == "available_seats"
    assert r.json()["data"]["count"] == 1


def test_ai_project_utilization(client, employee, seat, project):
    client.post("/seats/allocate", json={"employee_id": employee["id"], "seat_id": seat["id"]})
    r = client.post("/ai/query", json={"query": f"How many seats are occupied for Project {project['name']}?"})
    assert r.json()["intent"] == "project_utilization"
    assert "1 occupied" in r.json()["answer"]


def test_ai_nearby_teammates(client, project):
    seat_a = client.post("/seats", json={"floor": 1, "zone": "A", "bay": "1", "seat_number": "1"}).json()
    seat_b = client.post("/seats", json={"floor": 1, "zone": "A", "bay": "1", "seat_number": "2"}).json()
    e1 = client.post(
        "/employees",
        json={"name": "Nina Patel", "email": "nina@ethara.ai", "department": "Eng", "role": "SDE1",
              "joining_date": "2026-01-01", "project_id": project["id"]},
    ).json()
    e2 = client.post(
        "/employees",
        json={"name": "Omar Ali", "email": "omar@ethara.ai", "department": "Eng", "role": "SDE1",
              "joining_date": "2026-01-01", "project_id": project["id"]},
    ).json()
    client.post("/seats/allocate", json={"employee_id": e1["id"], "seat_id": seat_a["id"]})
    client.post("/seats/allocate", json={"employee_id": e2["id"], "seat_id": seat_b["id"]})

    r = client.post("/ai/query", json={"query": "Who is sitting near Nina Patel?"})
    assert r.json()["intent"] == "nearby_teammates"
    assert "Omar Ali" in r.json()["answer"]


def test_ai_allocate_new_joiner(client, employee, seat):
    r = client.post("/ai/query", json={"query": "Allocate a seat for new employee Amit Sharma"})
    assert r.json()["intent"] == "allocate_new_joiner"
    emp_after = client.get(f"/employees/{employee['id']}").json()
    assert emp_after["seat_allocation_status"] == "allocated"


def test_ai_unknown_intent_returns_help(client):
    r = client.post("/ai/query", json={"query": "asdkjaslkdj random text"})
    assert r.json()["intent"] == "unknown"
