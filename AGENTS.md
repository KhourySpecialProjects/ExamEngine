# AGENTS.md

Orientation for AI agents working in **ExamEngine** — an automated final-exam scheduler for
Northeastern University. It models scheduling as **graph coloring** (course sections = nodes,
shared-student conflicts = edges, time slots = colors) and solves it with **DSATUR**.

## Architecture

Monorepo, three deployable pieces + IaC:

| Path | Stack | Role |
| --- | --- | --- |
| `backend/` | FastAPI, Python 3.12, SQLAlchemy 2.0, pandas, networkx | REST API + scheduling engine |
| `frontend/` | Next.js 15 (app router), React 19, TypeScript, Zustand, Shadcn/ui, Tailwind v4 | Web UI |
| `infrastructure/terraform/` | Terraform, AWS (ECS Fargate, RDS, S3, ALB) | Production infra |
| `docker-compose.yml` | Postgres 15, nginx, pgadmin | Local + prod orchestration (profiles) |

Data flow: user uploads 3 CSVs (`courses`, `enrollments`, `rooms`) → backend validates/persists →
DSATUR assigns time slots + rooms → schedule returned to UI. CSV contracts and the DB schema are in
`docs/DATA.md`.

## Where the important code lives

**Backend** (`backend/src/`):
- `domain/services/scheduler.py` — **the DSATUR engine; the core of the system.**
- `domain/services/` — also `constraint_evaluator.py`, `conflict_detector.py`, `schedule_analyzer.py`.
- `domain/value_objects/` — hard/soft conflicts, penalties, scheduling config + state.
- `domain/adapters/` — CSV parsing + column-alias schema detection (`csv_adapters.py`, `schemas_detector.py`).
- `domain/models/`, `domain/factories/`, `domain/assemblers/` — domain entities and construction.
- `api/routes/` — `schedule.py`, `datasets.py`, `auth.py`, `admin.py`; all mounted under `/api` in `main.py`.
- `schemas/db.py` — SQLAlchemy DB schema. `core/` — config, DB engine, exceptions.
- `services/`, `repo/` — app-level business logic and DB repositories.

**Frontend** (`frontend/src/`): `app/` (routes), `components/` (feature dirs + `ui/` Shadcn),
`lib/api/` (API client), `lib/store/` (Zustand), `lib/hooks/`.

## Setup

```bash
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
docker-compose --profile dev up -d      # frontend :3000, backend :8000, db :5432
```

Live API contract (ground truth for routes/schemas): **http://localhost:8000/docs** (FastAPI OpenAPI).

Local (non-Docker): `npm run install:all` then `npm run dev` (runs backend + frontend concurrently).

## Verify your changes

Run these before claiming done — they are the CI gates (`.github/workflows/{unit-test,e2e}.yml`):

| Command | Scope |
| --- | --- |
| `npm run test` | backend `pytest` + frontend `vitest` |
| `npm run lint` | backend `ruff check` + frontend `biome check` |
| `cd backend && pytest -m unit` | fast backend units only (markers: `unit`, `integration`, `slow`) |
| `cd frontend && npm run test:e2e` | Playwright e2e (needs `npx playwright install` once) |

Backend runs from `backend/` (`pythonpath=["."]`, `testpaths=["tests"]`). If imports fail:
`cd backend && pip install -e ".[dev]"`.

## Conventions & gotchas

- **Pre-commit hook is active** (`.husky/pre-commit` → lint-staged): commits auto-run `ruff format`/`ruff check --fix`
  on `backend/**/*.py` and Biome on `frontend/**/*.{ts,tsx,js,jsx,json}`. Match existing style or the hook rewrites it.
- **Frontend `lint`/`format` are mutating** — `biome check --write` / `biome format --write`. `npm run lint` edits files.
- Backend style: PEP 8, type hints everywhere, `ruff` (line-length 88, double quotes). Config in `backend/pyproject.toml`.
- Conventional commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`).
- Docker uses **profiles**: `--profile dev` vs `--profile prod`. Bare `docker-compose up` starts nothing meaningful.
- DB reset (drops + recreates): `cd backend && python src/schemas/reset_database.py`.
- `bcrypt` is pinned to `3.2.0` for passlib compatibility — do not bump casually.
- Datasets persist to S3 (`s3://.../{dataset_uuid}/{courses,enrollments,rooms}.csv`); needs AWS creds in `backend/.env`.

### Known doc drift (verify against code, not docs, when it matters)
- `docs/DEVELOPMENT.md` cites `backend/src/schema/reset_database.py` (singular); actual path is `src/schemas/` (plural).
- `docs/TESTING.md` references `npm run test:watch` / `npm run test:coverage`; those scripts are **not** in
  `frontend/package.json` (only `test`, `test:e2e`, `lint`, `format`, `clean`). Use `vitest --watch` / `--coverage` directly.

## Reference docs

`docs/DEVELOPMENT.md` (setup, scripts, architecture) · `docs/ALGORITHM.md` (DSATUR + constraints) ·
`docs/DATA.md` (CSV formats, DB schema) · `docs/TESTING.md` · `docs/INFRASTRUCTURE.md` (AWS/Terraform).
