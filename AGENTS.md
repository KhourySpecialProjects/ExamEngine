# AGENTS.md

Orientation for AI agents working in **ExamEngine** — an automated final-exam scheduler for
Northeastern University. It models scheduling as **graph coloring** (course sections = nodes,
shared-student conflicts = edges, time slots = colors). Users pick one of two engines when
generating: **Classic** (DSATUR greedy) or **Optimized** (saturation construction + simulated
annealing).

## Architecture

Monorepo, three deployable pieces + IaC:

| Path | Stack | Role |
| --- | --- | --- |
| `backend/` | FastAPI, Python 3.12, SQLAlchemy 2.0, pandas, networkx | REST API + scheduling engines |
| `frontend/` | Next.js 15 (app router), React 19, TypeScript, Zustand, Shadcn/ui, Tailwind v4 | Web UI |
| `docker-compose.yml` | Postgres 15, LocalStack (S3), nginx, pgadmin | Local dev (`--profile dev`) and prod-style (`--profile prod`) |
| `docker-compose.coolify-{dev,staging}.yml` | Postgres, MinIO (S3), backend, frontend, proxy | Coolify deployments of `develop` and `staging` |
| `infrastructure/terraform/` | Terraform, AWS (ECS Fargate, RDS, S3, ALB) | Former production infra: **not in use and likely out of date**, kept for reference |

Data flow: user uploads CSVs → backend validates, stores the files in S3 (LocalStack locally,
MinIO on Coolify) and records metadata in Postgres → the chosen engine assigns time slots +
rooms → schedule and conflict analysis are saved and returned to the UI. Required files:
`courses`, `enrollments`, `rooms`. Optional: `room_blockouts`, `combined_exams` (same block +
same room), `common_exams` (same block, different rooms). CSV contracts and the DB schema are in
`docs/DATA.md`; the algorithms and constraints in `docs/ALGORITHM.md`.

## Where the important code lives

**Backend** (`backend/src/`):
- `domain/services/scheduler.py` — **Classic engine (DSATUR)**; also the shared group/room-seating
  logic (`seats_fit`, `_assign_rooms`). Rooms are never filled over capacity.
- `domain/services/annealing_scheduler.py` — **Optimized engine** (`AnnealingScheduler`,
  subclasses `Scheduler`).
- `domain/services/` — also `constraint_evaluator.py`, `conflict_detector.py`, `schedule_analyzer.py`,
  `late_add.py` (late add: place one exam into a saved schedule, see `docs/ALGORITHM.md`).
- `domain/validation/` — Schedule Validator: independent checks that re-verify a saved schedule
  against its uploaded files. Deliberately imports no scheduler/analyzer code.
- `domain/value_objects/` — hard/soft conflicts, penalties, scheduling config + state.
- `domain/adapters/` — CSV parsing + column-alias schema detection (`csv_adapters.py`, `schemas_detector.py`).
- `domain/models/`, `domain/factories/`, `domain/assemblers/` — domain entities, construction,
  API response shapes.
- `api/routes/` — `schedule.py`, `datasets.py`, `validation.py`, `auth.py`, `admin.py`; all
  mounted under `/api` in `main.py`.
- `schemas/db.py` — SQLAlchemy DB schema. `core/` — config, DB engine, exceptions, logging.
- `services/`, `repo/` — app-level business logic and DB repositories.

**Frontend** (`frontend/src/`): `app/` (routes; schedules list is `app/dashboard/page.tsx` with
List and By-dataset views, schedule view is `app/dashboard/[id]/page.tsx` with its view and
conflict type in the URL (`?view=conflicts&type=…`, `lib/scheduleView.ts`), Compare is
`app/dashboard/compare` with its columns in the URL via `nuqs`, the first being the baseline),
`components/` (feature dirs, `common/` shared pieces such as `table/PaginationBar`, `ui/`
Shadcn), `lib/api/` (API client), `lib/store/` (Zustand), `lib/hooks/`. Generation settings are
listed once in `lib/scheduleSettings.ts`. Tests sit next to the code as `*.test.ts(x)`.

## Branches and environments

| Branch | Deploys to | Notes |
| --- | --- | --- |
| feature branches | local only | One per Linear issue, cut from `develop` |
| `develop` | Coolify dev | Integration branch; every feature PR targets it |
| `staging` | Coolify staging | Promoted from `develop` by PR. In informal use: **its data must survive deploys** |
| `main` | — | **Not in use.** It is GitHub's default branch, so always pass `--base` to `gh pr create` |

## Development workflow

Follow this for every bug, feature or improvement.

1. **Discuss first.** Talk the problem through with the user and agree on the fix before writing
   code. Investigate (code, DB, history) to ground the discussion.
2. **Linear issues before code.** Team "Exam Engine" (key `EXENG`). Create the issue(s) In
   Progress, assigned to the user, in the current cycle, labeled Feature / Improvement / Bug.
   Multi-part work: a parent issue plus sub-issues (`parentId`).
3. **Feature branch.** Cut from up-to-date `origin/develop`, named with the issue's Linear
   `gitBranchName` (e.g. `exeng-87-schedule-view-...`). Never commit to `develop` or `staging`
   directly. For stacked sub-issues, branch the later one off the earlier and merge in order.
4. **Implement and verify.** Run the checks in "Verify your changes", then smoke-test the changed
   path against the local stack (API calls and/or the browser). The dev containers hot-reload from
   the main checkout, so the user can look at the branch right away (frontend on host port 3100
   with the committed override).
5. **User review.** Let the user try it locally before opening a PR.
6. **PR into `develop`.** Conventional-commit title with the issue key, e.g.
   `feat(schedule): ... (EXENG-87)`. Body: "Closes EXENG-N", then What / Verification. Move the
   issue to In Review. CodeRabbit may review (rate-limited, ~1 review/hour; pushes re-trigger it).
7. **Merge.** Merge commit (`gh pr merge --merge`); squash only when the branch has `wip:`-style
   commits. Then delete the branch locally and on GitHub (the repo does not auto-delete).
   "Closes EXENG-N" moves the issue to Done.
8. **Promote `develop` → `staging`** only when the user asks:
   - Check `git merge-tree --write-tree origin/staging origin/develop` merges cleanly.
   - Data safety: list changes to schema, `core/database.py`, `main.py`, compose files,
     Dockerfiles, env examples, nginx, dependency manifests; grep added backend code for DB writes
     and storage calls. Staging data must survive.
   - Run the full backend and frontend test suites on `develop`.
   - Code review on two axes, standards and spec (the `code-review` skill), with the findings
     posted as a PR comment.
   - PR titled `chore: promote develop to staging (...)` with sections What's included / Data
     safety / Verification / Deploy checklist (see #135, #138).
   - Merge with `gh pr merge --merge --match-head-commit <develop sha>`.
   - The user redeploys the existing Coolify staging resource and smoke-tests it.
9. **Session notes.** `.session-notes.md` is an untracked, local file with the current state,
   NEXT UP list, recent history and local tips, carried between agent sessions. Read it at the
   start of every session. Update it without being asked after each merge or promotion and when
   the user is wrapping up: what shipped, branch and environment state, open findings, NEXT UP.
   Never commit it.

**Never put local dataset specifics** (dataset names, CRNs, rooms, student or instructor IDs,
counts) in PRs, PR comments, issues or committed files. Use synthetic values in tests.

## Setup

```bash
cp .env.example .env
cp backend/.env.example backend/.env
docker-compose --profile dev up -d
```

The committed `docker-compose.override.yml` remaps host ports (backend **8100**, db **5434**,
LocalStack **4576**; frontend 3100) and pins LocalStack to the community v4 image. Container
ports are unchanged. Live API contract: `http://localhost:<backend port>/docs` (FastAPI OpenAPI).

Local (non-Docker): `npm run install:all` then `npm run dev` (runs backend + frontend concurrently).

## Verify your changes

**No CI runs on PRs into `develop` or `staging`** — `.github/workflows/{unit-test,e2e}.yml`
trigger only on `main`/`master` (EXENG-40). Run the checks locally before claiming done:

| Command | Scope |
| --- | --- |
| `cd backend && .venv/bin/pytest -q -p no:cacheprovider --no-cov` | all backend tests (DB tests need the dev stack's Postgres; they skip without it) |
| `cd backend && .venv/bin/ruff check --no-fix <files>` | backend lint (`pyproject.toml` sets `fix = true`, so plain `ruff check` rewrites files) |
| `cd frontend && npx vitest run` | frontend unit tests (bare `vitest` starts watch mode) |
| `cd frontend && npx tsc --noEmit --incremental false` | frontend type check |
| `cd frontend && npx biome check <files>` | frontend lint (read-only without `--write`) |
| `cd frontend && npm run test:e2e` | Playwright e2e (needs `npx playwright install` once) |

Backend markers: `unit` (set by hand; currently only `test_annealing_scheduler.py`), `integration`,
`slow`, `stress`. `tests/conftest.py` adds the last three from test names ("integration" or
"real_data"; "large" or "stress") and adds `integration` to every test using the `db_session`
fixture, e.g. `pytest -m "not slow"`. Backend runs from `backend/`
(`pythonpath=["."]`, `testpaths=["tests"]`); if imports fail: `cd backend && pip install -e ".[dev]"`.

**Database tests** (`db_session` fixture; harness and row builders in `tests/db/`) use a separate
`_test` database (`TEST_DATABASE_URL`, default `exam_engine_test` on the dev Postgres, host port
5434), never `DATABASE_URL`. Each test is rolled back; overlapping runs wait for each other. The
harness refuses any database not named `*_test`; never weaken that guard. Details:
`docs/TESTING.md`.

## Conventions & gotchas

- **Pre-commit hook** (`.husky/pre-commit` → lint-staged) runs `ruff format` + `ruff check --fix`
  on staged `backend/**/*.py` and Biome format + `check --write` on staged
  `frontend/**/*.{ts,tsx,js,jsx,json}`. It needs `ruff` on `PATH`:
  `export PATH=$PWD/backend/.venv/bin:$PATH`. Check `git show --stat` after committing.
- **`npm run lint` and `npm run format` rewrite files.** `lint` runs `biome check --write` on the
  frontend and `ruff check .` (with `fix = true` from `backend/pyproject.toml`) on the whole
  backend. `format` runs `biome format --write` on the frontend and `ruff format . && ruff check
  --fix .` on the whole backend, so it also reformats files that aren't ruff-formatted yet (next
  bullet): avoid it.
  Use the read-only commands above for verification.
- Don't `ruff format` whole directories: a few backend files are not ruff-formatted yet.
  Format only the files you touch.
- Backend style: PEP 8, type hints everywhere, `ruff` (line-length 88, double quotes). Config in
  `backend/pyproject.toml`. Frontend: TypeScript + Biome (`frontend/biome.json`).
- Conventional commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`).
- Docker uses **profiles**: `--profile dev` vs `--profile prod`. Bare `docker-compose up` (and the
  root `npm run docker:*` scripts, which pass no profile) start nothing meaningful.
- Local edits to `docker-compose.override.yml` are machine-specific port tweaks: don't commit them.
- DB reset (drops + recreates all tables):
  `docker-compose --profile dev exec backend-dev python src/schemas/reset_database.py`. Run it in
  the container: on the host, `backend/.env` points at port 5432, not the override's 5434.
- Schema changes have no migration tool: `init_db` runs `create_all` plus explicit
  `ADD COLUMN IF NOT EXISTS` statements at startup. Prefer JSONB fields on existing tables, and
  treat any schema change as a staging data-safety item.
- Timestamps are naive `datetime.now` in the container (UTC) and serialized without a zone.
- `bcrypt` is pinned to `3.2.0` for passlib compatibility — do not bump casually.

## Reference docs

`docs/DEVELOPMENT.md` (setup, scripts, environments) · `docs/ALGORITHM.md` (engines + constraints) ·
`docs/DATA.md` (CSV formats, DB schema) · `docs/TESTING.md` · `docs/INFRASTRUCTURE.md` (AWS/Terraform,
not in use).
Docs can drift; verify against code when it matters.
