import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def db_session(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def project(client):
    r = client.post("/projects", json={"name": "Talos", "manager_name": "Asha Rao"})
    assert r.status_code == 201
    return r.json()


@pytest.fixture()
def seat(client):
    r = client.post("/seats", json={"floor": 2, "zone": "B", "bay": "4", "seat_number": "23"})
    assert r.status_code == 201
    return r.json()


@pytest.fixture()
def employee(client, project):
    r = client.post(
        "/employees",
        json={
            "name": "Amit Sharma",
            "email": "amit@ethara.ai",
            "department": "Engineering",
            "role": "SDE2",
            "joining_date": "2026-01-01",
            "project_id": project["id"],
        },
    )
    assert r.status_code == 201
    return r.json()
