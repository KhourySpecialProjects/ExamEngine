# Testing Guide

How to run and write tests for ExamEngine, and what CI does (and doesn't) cover.

## Test Structure

```
backend/
├── pyproject.toml            # [tool.pytest.ini_options]: paths, markers, coverage addopts
└── tests/
    ├── conftest.py           # Shared fixtures; auto-adds markers by test name
    ├── fixtures/             # Synthetic CSV fixtures
    ├── api/                  # Route tests (FastAPI TestClient, service overrides)
    ├── core/
    ├── domain/
    │   ├── adapters/         # CSV parsing, column aliases
    │   ├── assemblers/
    │   ├── services/         # Scheduling engines, room capacity, analyzers
    │   └── validation/       # Schedule Validator checks
    ├── repo/
    └── services/             # Application services (datasets, schedule)

frontend/
├── vitest.config.mts         # jsdom, setup file, v8 coverage
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
```

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
`real_data`, `slow` to tests whose name contains `large` or `stress`, and `stress` to tests whose
name contains `stress`. A module can mark all of its tests with `pytestmark = pytest.mark.unit`.
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

from src.domain.services.scheduler import seats_fit


@pytest.mark.unit
def test_each_exam_needs_its_own_room():
    assert seats_fit([30, 30], [40, 40])
    assert not seats_fit([30, 30], [40])
```

### Frontend Test

```typescript
// src/components/schedule/ScheduleDetails.test.tsx
import { describe, expect, it } from "vitest";
import { generationSettings } from "./ScheduleDetails";

describe("generationSettings", () => {
  it("labels the optimized algorithm", () => {
    const [algorithm] = generationSettings({
      algorithm: "Annealing",
      parameters: { algorithm: "annealing" },
    });
    expect(algorithm.value).toBe("Optimized (annealing)");
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
