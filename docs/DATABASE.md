# Database Schema

PostgreSQL preferred (production), SQLite for zero-setup local dev (`DATABASE_URL` env var switches between them — see `backend/.env.example`). Schema is identical on both; managed by Alembic (`backend/alembic/versions/`).

## ER overview

```
projects (1) ──< employees (N)          one project has many employees
employees (1) ──< seat_allocations (N)  one employee has many allocations over time (history)
seats (1)     ──< seat_allocations (N)  one seat has many allocations over time (history)
projects (1)  ──< seat_allocations (N)  denormalized project_id on the allocation for fast utilization queries
```

Only one `seat_allocations` row per employee (and per seat) may have `allocation_status = 'active'` at a time — enforced by partial unique indexes, not application logic alone.

## Tables

### `projects`
| Column | Type | Notes |
|---|---|---|
| id | PK int | |
| name | varchar(120) | unique, indexed |
| description | varchar(500) | nullable |
| manager_name | varchar(120) | nullable |
| status | enum(active, inactive) | default active |
| created_at | timestamp | server default now() |

### `employees`
| Column | Type | Notes |
|---|---|---|
| id | PK int | |
| employee_code | varchar(20) | unique, indexed (e.g. `ETH00001`) |
| name | varchar(150) | indexed |
| email | varchar(200) | **unique**, indexed — enforces business rule B6 |
| department | varchar(100) | |
| role | varchar(100) | |
| joining_date | date | |
| status | enum(active, inactive) | indexed |
| project_id | FK → projects.id | nullable, indexed |
| created_at / updated_at | timestamp | |

### `seats`
| Column | Type | Notes |
|---|---|---|
| id | PK int | |
| floor | int | indexed |
| zone | varchar(10) | indexed |
| bay | varchar(10) | |
| seat_number | varchar(20) | |
| status | enum(available, occupied, reserved, maintenance) | indexed |
| created_at | timestamp | |

**Constraints:**
- `UNIQUE(floor, zone, seat_number)` — enforces business rule B7 (no duplicate seat number on the same floor/zone).
- Composite index on `(floor, zone)` for the allocation engine's proximity queries.

### `seat_allocations`
| Column | Type | Notes |
|---|---|---|
| id | PK int | |
| employee_id | FK → employees.id | indexed |
| seat_id | FK → seats.id | indexed |
| project_id | FK → projects.id | nullable, denormalized from employee at allocation time |
| allocation_status | enum(active, released) | indexed |
| allocation_date | timestamp | server default now() |
| released_date | timestamp | nullable |

**Constraints (the core business rules, enforced at the DB layer):**
- Partial unique index `uq_active_allocation_per_employee` on `employee_id` `WHERE allocation_status = 'active'` — enforces B1 (one active seat per employee). Works identically on SQLite (`sqlite_where=`) and Postgres (`postgresql_where=`).
- Partial unique index `uq_active_allocation_per_seat` on `seat_id` `WHERE allocation_status = 'active'` — enforces B2 (one active employee per seat).

## Enum storage

All enum columns use `values_callable=lambda e: [m.value for m in e]` so the database stores the lowercase `.value` (`"active"`, `"reserved"`) rather than SQLAlchemy's default of the Python enum member `.name` (`"ACTIVE"`, `"RESERVED"`). This keeps DB rows, JSON API responses, and the partial-index predicates (`allocation_status = 'active'`) all consistent — see `backend/app/models.py::_enum()`.

## Business rules enforced here vs. in the service layer

| Rule | Where |
|---|---|
| B1/B2: one active seat per employee/seat | DB partial unique index (`seat_allocations`) — belt-and-suspenders with the service-layer check in `allocation.py`, which raises a friendly `409` before the DB would even reject it |
| B3: released seats become available | Service layer (`release_seat()`), not a DB trigger — kept explicit and testable |
| B4: reserved/maintenance seats can't be allocated | Service layer check (`allocate_seat()`) |
| B6: duplicate email rejected | DB unique constraint (`employees.email`) |
| B7: duplicate seat number per floor/zone rejected | DB unique constraint (`seats(floor, zone, seat_number)`) |

## Migrations

```bash
cd backend && source .venv/bin/activate
alembic revision --autogenerate -m "description"   # generate after model changes
alembic upgrade head                                 # apply
```

The one migration currently in the repo (`3557cd0fad57_initial_schema.py`) creates all four tables plus every index/constraint above. Verified against both SQLite and a live Postgres 16 container (`docker compose up`).
