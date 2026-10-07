# Testing Guide

How to run and write tests for ExamEngine, and what CI does (and doesn't) cover.

## Test Structure

```
backend/
├── pyproject.toml            # [tool.pytest.ini_options]: paths, markers, coverage addopts
└── tests/
    ├── conftest.py           # Shared fixtures (incl. db_session); auto-adds markers
    ├── db/                   # Postgres test-database harness, row builders, guard tests
    ├── fixtures/             # Synthetic CSV fixtures
    ├── api/                  # Route tests (FastAPI TestClient, service overrides)
    ├── core/
    ├── domain/
    │   ├── adapters/         # CSV parsing, column aliases
    │   ├── assemblers/
    │   ├── services/         # Scheduling engines, room capacity, analyzers
    │   └── validation/       # Schedule Validator checks
    ├── repo/                 # Repository tests (mocked session, or db_session)
    └── services/             # Application services (datasets, schedule)

frontend/
├── vitest.config.mts         # jsdom, setup file, v8 coverage, testTimeout 15 s
├── src/test/setup.ts         # Test setup
├── src/**/*.test.ts(x)       # Unit/component tests, next to the code they test
├── playwright.config.ts
└── e2e/                      # Playwright (currently only the generated example spec)
```

## Running Tests

### Backend

```bash
cd backend

# All tests (pyproject addopts always add coverage: terminal report + htmlcov/)
.venv/bin/pytest

# Fast run without coverage or cache files
.venv/bin/pytest -q -p no:cacheprovider --no-cov

# Specific file or test
.venv/bin/pytest tests/domain/services/test_room_capacity.py
.venv/bin/pytest -k blocks_per_day

# By marker
.venv/bin/pytest -m unit
.venv/bin/pytest -m "not slow"

# Without the Postgres test database (no Docker needed)
.venv/bin/pytest -m "not integration"
```

#### Database tests

Tests that take the `db_session` fixture run against a real Postgres **test database** on the
dev stack's Postgres server (`docker-compose --profile dev up -d`). Local only: nothing runs
them on develop, staging or Coolify.

- **Which database:** `TEST_DATABASE_URL`, default
  `postgresql+psycopg2://postgres:postgres@localhost:5434/exam_engine_test` (port 5434 from the
  committed override). Never `DATABASE_URL`. The database is created on first use.
- **Guard:** the harness refuses (error, not skip) a database whose name doesn't end in `_test`
  or is the one `DATABASE_URL` names, and checks `current_database()` again before it drops and
  rebuilds the schema. Don't weaken these checks.
- **Schema:** dropped and rebuilt once per run with the app's `init_db`, so it always matches the
  models.
- **Isolation:** each test runs in one transaction that is rolled back afterwards. Code under test
  may `commit()`; that only releases a savepoint. The test database stays empty between runs.
  Overlapping runs (worktrees, parallel agents) take turns: each run holds a Postgres advisory
  lock on the test database until it finishes.
- **No server:** DB tests are skipped with the reason shown under `-rs`.
- Tests using `db_session` get the `integration` marker automatically.

### Frontend

```bash
cd frontend

npx vitest run                          # Run once
npm test                                # = vitest: watch mode in a terminal, single run in CI
npx vitest run src/components/schedule  # One directory
npx tsc --noEmit --incremental false    # Type check
npx biome check <files>                 # Lint without rewriting files

npm run test:e2e                        # Playwright (run `npx playwright install` once)
npx playwright test --ui
```

`tsc --incremental false` avoids writing `tsconfig.tsbuildinfo`, which can be owned by root
when the dev container created it.

## Test Markers

Registered in `backend/pyproject.toml` and `tests/conftest.py` (`--strict-markers` is on, so
unregistered markers fail):

| Marker | Description |
| --- | --- |
| `@pytest.mark.unit` | Fast, isolated unit tests |
| `@pytest.mark.integration` | Integration tests |
| `@pytest.mark.slow` | Long-running tests |
| `@pytest.mark.stress` | Stress tests (registered in `conftest.py`) |

`conftest.py` also adds `integration` to tests whose name contains `integration` or
`real_data` and to tests that use the `db_session` fixture, `slow` to tests whose name contains
`large` or `stress`, and `stress` to tests whose name contains `stress`. A module can mark all of
its tests with `pytestmark = pytest.mark.unit`.
Tests that run the annealing engine with a real time budget should be marked `slow`.

## CI Workflows

**Neither workflow runs for our day-to-day branches.** Both trigger only on pushes and PRs to
`main`/`master`, so PRs into `develop` and `staging` get no CI (tracked in EXENG-40). Run the
suites locally before merging (see `AGENTS.md`, "Verify your changes").

### Unit Tests (`.github/workflows/unit-test.yml`)

- Sets up Python 3.12 and Node.js 20
- `npm run install:all`
- `npm run test` (backend pytest + frontend Vitest)

### E2E Tests (`.github/workflows/e2e.yml`)

Runs when `frontend/**` changes:

- Installs Playwright browsers
- Runs the Playwright suite
- Uploads the report as an artifact (Actions tab → workflow run → artifacts)

## Writing Tests

- Use synthetic data (made-up CRNs, names and counts). Never copy real or local dataset values
  into tests or fixtures.
- Test behaviour a user or caller can observe: results, boundaries, error paths. Avoid tests
  that only restate wiring or default values.

### Backend Unit Test

```python
# tests/domain/services/test_example.py
import pytest

from src.domain.services.room_fit import seats_fit


@pytest.mark.unit
def test_each_exam_needs_its_own_room():
    assert seats_fit([30, 30], [40, 40])
    assert not seats_fit([30, 30], [40])
```

### Backend Database Test

Use the builders in `tests/db/builders.py` for rows; they flush so ids are set.

```python
# tests/repo/test_example.py
from src.repo.schedule import ScheduleRepo
from tests.db.builders import make_schedule, make_user


def test_a_stranger_cannot_read_a_schedule(db_session):
    owner = make_user(db_session, "Owner")
    stranger = make_user(db_session, "Stranger")
    schedule = make_schedule(db_session, owner)

    repo = ScheduleRepo(db_session)
    assert repo.get_by_id_for_user(schedule.schedule_id, stranger.user_id) is None
```

### Frontend Test

```typescript
// src/lib/scheduleSettings.test.ts
import { describe, expect, it } from "vitest";
import { makeSummary } from "@/test/summary";
import { settingRows } from "./scheduleSettings";

describe("settingRows", () => {
  it("names the algorithm that ignores a setting", () => {
    const rows = settingRows(makeSummary());
    const time = rows.find((row) => row.key === "time_budget_seconds");
    expect(time?.value).toBe("Not used by Classic");
  });
});
```

## Test Coverage

```bash
# Backend: every pytest run writes htmlcov/ (addopts); or from the repo root:
npm run test:backend:cov
open backend/htmlcov/index.html

# Frontend (@vitest/coverage-v8)
cd frontend
npx vitest run --coverage
```

## Troubleshooting

### Docker not running

```bash
docker-compose --profile dev up -d
```

### Port conflicts

```bash
docker-compose --profile dev down
docker ps  # Check for conflicting containers
```

### Module not found

```bash
cd backend
pip install -e ".[dev]"
```

### Playwright browsers missing

```bash
cd frontend
npx playwright install
```
