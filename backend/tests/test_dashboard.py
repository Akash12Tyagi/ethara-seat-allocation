def test_dashboard_summary_updates_after_allocation(client, employee, seat):
    before = client.get("/dashboard/summary").json()
    assert before["available_seats"] == 1
    assert before["pending_allocation"] == 1

    client.post("/seats/allocate", json={"employee_id": employee["id"], "seat_id": seat["id"]})

    after = client.get("/dashboard/summary").json()
    assert after["occupied_seats"] == 1
    assert after["available_seats"] == 0
    assert after["pending_allocation"] == 0  # B8: dashboard updates after every allocation


def test_dashboard_summary_updates_after_release(client, employee, seat):
    client.post("/seats/allocate", json={"employee_id": employee["id"], "seat_id": seat["id"]})
    client.post("/seats/release", json={"employee_id": employee["id"]})

    after = client.get("/dashboard/summary").json()
    assert after["available_seats"] == 1
    assert after["occupied_seats"] == 0
    assert after["pending_allocation"] == 1


def test_project_utilization(client, employee, seat, project):
    client.post("/seats/allocate", json={"employee_id": employee["id"], "seat_id": seat["id"]})
    r = client.get("/dashboard/project-utilization")
    assert r.status_code == 200
    row = next(p for p in r.json() if p["project_id"] == project["id"])
    assert row["employee_count"] == 1
    assert row["allocated_seats"] == 1
    assert row["utilization_pct"] == 100.0


def test_floor_utilization(client, employee, seat):
    client.post("/seats/allocate", json={"employee_id": employee["id"], "seat_id": seat["id"]})
    r = client.get("/dashboard/floor-utilization")
    assert r.status_code == 200
    row = next(f for f in r.json() if f["floor"] == seat["floor"])
    assert row["occupied_seats"] == 1
    assert row["occupancy_pct"] == 100.0
