# Development Guide

Local development setup for ExamEngine. The branch model and the issue → branch → PR →
promotion workflow are in [`AGENTS.md`](../AGENTS.md#development-workflow).

## Prerequisites

- **Node.js 20+** and npm
- **Python 3.12+**
- **Docker & Docker Compose**
- **Git**

## Installation

### Option 1: Docker (Recommended)

```bash
git clone https://github.com/KhourySpecialProjects/ExamEngine.git
cd ExamEngine

# Copy environment files
cp .env.example .env
cp backend/.env.example backend/.env

# Start all dev services
docker-compose --profile dev up -d

# View logs
docker-compose --profile dev logs -f
```

The dev profile runs Postgres, LocalStack (S3), the backend and frontend with hot reload from
the working tree, nginx, and pgadmin. The committed `docker-compose.override.yml` is merged
automatically and remaps the host ports:

| Service | Host port (with override) | Default without override |
| --- | --- | --- |
| Frontend | <http://localhost:3100> | 3000 |
| Backend API | <http://localhost:8100/api> | 8000 |
| API docs | <http://localhost:8100/docs> | 8000 |
| Postgres | 5434 | 5432 |
| LocalStack S3 | 4576 | 4566 |
| pgadmin | <http://localhost:5050> | 5050 |

Edit the override locally if those ports clash on your machine, but don't commit
machine-specific changes.

In development (`ENVIRONMENT=development`) the backend seeds an admin account from
`ADMIN_EMAIL` / `ADMIN_PASSWORD` at startup.

### Option 2: Local (no Docker)

```bash
# Install root, frontend and backend (editable, with dev extras) dependencies
npm run install:all

# Start both frontend and backend with hot reload
npm run dev
```

Or run the services separately:

```bash
# Terminal 1: Backend
cd backend && uvicorn src.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend && npm run dev
```

You still need Postgres and S3, for example
`docker-compose --profile dev up -d db localstack localstack-init` (`localstack-init` creates the
S3 bucket; uploads fail without it). Without Docker networking:

- In `backend/.env`, point `DATABASE_URL` and `AWS_ENDPOINT_URL` at `localhost` and the host
  ports, not the `db` / `localstack` service names.
- Create `frontend/.env.local` with `NEXT_PUBLIC_API_URL=http://localhost:8000/api`. Without it,
  the browser falls back to `http://localhost:8000` (no `/api` prefix) and every request 404s.

## Environment Variables

The example files are the source of truth; copy them and fill in values.

| File | Used by | Notes |
| --- | --- | --- |
| `.env.example` → `.env` | `docker-compose.yml` | Postgres credentials, ports, AWS settings, `SECRET_KEY`, `FRONTEND_URL`, `NEXT_PUBLIC_API_URL` (includes `/api`) |
| `backend/.env.example` → `backend/.env` | backend | `DATABASE_URL`, `AWS_ENDPOINT_URL` (LocalStack; remove for real AWS), AWS credentials (`test`/`test` for LocalStack), `SECRET_KEY`, `ENVIRONMENT`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` |
| `.env.coolify-dev.example`, `.env.coolify-staging.example` | Coolify | Set in the Coolify resource, not in files: `APP_URL`, passwords, MinIO credentials, admin account |

`frontend/.env.example` is empty: in Docker, the compose file sets `NEXT_PUBLIC_API_URL`.

## Environments

| Environment | Compose file | Branch | Storage |
| --- | --- | --- | --- |
| Local | `docker-compose.yml` (+ override), `--profile dev` | any | Postgres + LocalStack (S3 is not persisted across restarts) |
| Coolify dev | `docker-compose.coolify-dev.yml` | `develop` | Postgres + MinIO in-stack on named volumes; seeds the admin automatically; `/docs` enabled |
| Coolify staging | `docker-compose.coolify-staging.yml` | `staging` | Postgres + MinIO in-stack on named volumes (data survives redeploys and is in informal use); seed the admin once with `python script/add_admin.py`; `/docs` disabled |
| Production (AWS) | `docker-compose.yml --profile prod`, `infrastructure/terraform/` | — | RDS + S3; not in active use |

Each Coolify stack routes `/api/*` to the backend and everything else to the frontend from one
public domain (`APP_URL`).

## Available Scripts

From the root directory:

| Command | Description |
| --- | --- |
| `npm run install:all` | Install root + frontend packages and the backend (`pip install -e ".[dev]"`) |
| `npm run dev` | Start backend and frontend (no Docker) |
| `npm run dev:backend` / `npm run dev:frontend` | Start one side only |
| `npm run test` | Backend `pytest` + frontend `vitest` |
| `npm run test:backend:cov` | Backend tests with HTML + terminal coverage |
| `npm run lint` | `ruff check` + `biome check --write` (**rewrites files**: ruff has `fix = true` in `backend/pyproject.toml`) |
| `npm run format` | `ruff format` + `ruff check --fix` + `biome format --write` (**rewrites files**) |
| `npm run build` | Build the frontend for production |
| `npm run clean` | Remove caches and build output |

The `npm run docker:*` scripts call `docker-compose` without a profile, so they start nothing
useful. Use the commands below instead.

## Docker Commands

The project uses Docker Compose profiles to separate dev and prod services.

```bash
# Development (--profile dev)
docker-compose --profile dev up -d                # Start all dev services
docker-compose --profile dev down                 # Stop dev services
docker-compose --profile dev logs -f backend-dev  # Backend logs
docker-compose --profile dev restart backend-dev  # Restart backend
docker-compose --profile dev up -d --build        # Rebuild and start
docker-compose --profile dev down -v              # Remove containers and volumes (wipes the DB)

# Production (--profile prod)
docker-compose --profile prod up -d
docker-compose --profile prod down
```

## Code Style

### Backend (Python)

- PEP 8, type hints everywhere, `ruff` (line-length 88, double quotes). Config in
  `backend/pyproject.toml`.
- Format only the files you change (`ruff format <files>`): a few existing files are not
  ruff-formatted yet, and formatting whole directories pulls unrelated changes into a commit.
- `pyproject.toml` sets `fix = true`, so plain `ruff check` rewrites files. Check without changing
  anything with `ruff check --no-fix <files>`.

### Frontend (TypeScript)

- TypeScript in strict mode; formatting and linting with Biome (`frontend/biome.json`). There is
  no ESLint.
- `npx biome check <files>` checks without changing anything. `npm run lint` / `npm run format`
  write fixes.

### Pre-commit hook

Husky runs lint-staged on commit: `ruff format` + `ruff check --fix` on staged backend Python,
and Biome format + `check --write` on staged frontend files. The hook needs `ruff` on `PATH`:

```bash
export PATH=$PWD/backend/.venv/bin:$PATH
```

### Commit Messages

Conventional commits, with the Linear issue key in feature commits and PR titles:

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `refactor:` Code refactoring
- `test:` Tests
- `chore:` Maintenance (including `develop` → `staging` promotions)

## Project Architecture

### Backend Structure

```
backend/src/
├── domain/
│   ├── services/     # Scheduling engines (scheduler.py = DSATUR, annealing_scheduler.py),
│   │                 # conflict detection, schedule analysis
│   ├── validation/   # Schedule Validator checks (independent of the engines)
│   ├── adapters/     # CSV parsing + column-alias detection
│   ├── assemblers/   # API response shapes
│   └── models/, factories/, value_objects/
├── api/
│   ├── routes/       # FastAPI routers (schedule, datasets, validation, auth, admin)
│   └── deps.py       # Dependency injection, auth
├── core/             # Config, database engine + startup columns, exceptions, logging
├── services/         # Application services
├── repo/             # Database repositories
└── schemas/          # SQLAlchemy models (db.py) and reset_database.py
```

### Frontend Structure

```
frontend/src/
├── app/            # Next.js app router pages (dashboard/[id] = schedule view)
├── components/     # React components
│   ├── ui/         # Shadcn/ui components
│   └── ...         # Feature components, with *.test.tsx alongside
└── lib/
    ├── api/        # API client
    ├── store/      # Zustand state
    └── hooks/      # Custom hooks
```

## Troubleshooting

### Port Conflicts

```bash
# Check what's using a port
lsof -i :3000

# Or remap the host port in docker-compose.override.yml (don't commit machine-specific changes)
```

### Database Issues

```bash
# Start over with an empty database (wipes all data, including pgadmin settings)
docker-compose --profile dev down -v
docker-compose --profile dev up -d

# Or keep the containers and drop + recreate all tables (run inside the container;
# on the host, backend/.env points at port 5432 instead of the override's 5434)
docker-compose --profile dev exec backend-dev python src/schemas/reset_database.py
```

### Python Import Errors

```bash
cd backend
pip install -e ".[dev]"
```
