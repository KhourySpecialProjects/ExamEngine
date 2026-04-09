# Testing Guide

Test execution and CI/CD workflows for ExamEngine.

## Test Structure

```
backend/tests/
├── conftest.py              # Fixtures and configuration
├── pytest.ini               # Pytest settings
└── test_simple_models.py    # Model unit tests

frontend/
├── src/test/setup.ts        # Test setup
├── e2e/                     # Playwright E2E tests
└── vitest.config.mts        # Vitest configuration
```

## Running Tests

### Backend Tests

```bash
# All tests
cd backend && pytest

# With coverage
pytest --cov=src --cov-report=html

# Specific file
pytest tests/test_simple_models.py

# By marker
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests
pytest -m "not slow"    # Skip slow tests

# Verbose output
pytest -vvv --tb=long
```

### Frontend Tests

```bash
cd frontend

# Unit tests (Vitest)
npm test

# Watch mode
npm run test:watch

# E2E tests (Playwright)
npx playwright test

# E2E with UI
npx playwright test --ui

# Specific browser
npx playwright test --project=chromium
```

## Test Markers

| Marker                     | Description                |
| -------------------------- | -------------------------- |
| `@pytest.mark.unit`        | Fast, isolated unit tests  |
| `@pytest.mark.integration` | Database integration tests |
| `@pytest.mark.slow`        | Long-running tests         |

Example:

```python
@pytest.mark.unit
def test_schedule_creation():
    """Fast unit test."""
    pass

@pytest.mark.integration
def test_database_save():
    """Requires database connection."""
    pass
```

## CI/CD Workflows

All workflows run on push and PRs to `main` and `staging`, scoped to relevant paths so only affected checks run.

### Backend Lint (`.github/workflows/backend-lint.yml`)

Triggers on `backend/**` changes.

- Runs **Ruff** lint and format check against `backend/` using Python 3.12 and `uv`

### Backend Tests (`.github/workflows/backend-tests.yml`)

Triggers on `backend/**` changes.

- Runs **Pytest** against `backend/tests/` using Python 3.12 and `uv`
- Domain-level tests only — no real DB or AWS required

### Frontend Lint (`.github/workflows/frontend-lint.yml`)

Triggers on `frontend/**` changes.

- Runs **Biome** lint and format check against `frontend/` using Node 20

### Frontend Unit Tests (`.github/workflows/frontend-unit-tests.yml`)

Triggers on `frontend/**` changes.

- Runs **Vitest** unit tests against `frontend/` using Node 20

### Frontend Build (`.github/workflows/frontend-build.yml`)

Triggers on `frontend/**` changes.

- Runs `next build` to verify the Next.js app compiles and TypeScript is valid

### Frontend E2E Tests (`.github/workflows/frontend-e2e-tests.yml`)

Triggers on `frontend/**` changes.

- Installs **Playwright** browsers with system dependencies
- Runs the full E2E test suite via `npm run test:e2e --workspace=frontend`
- Uploads the Playwright HTML report as an artifact (retained 30 days)

### Deploy to Staging (`.github/workflows/deploy-staging.yml`)

Runs on push to `staging` only:

- Authenticates to AWS via OIDC (no long-lived credentials)
- Fetches config (cluster, service names, ECR URIs, domain) from SSM Parameter Store
- Builds and pushes backend and frontend Docker images to ECR
- Force-deploys both ECS services

### Deploy to Production (`.github/workflows/deploy-prod.yml`)

Runs on push to `main` only — same steps as staging with prod AWS role and SSM paths.

### Viewing Results

1. Go to **Actions** tab in GitHub
2. Click on a workflow run
3. Download **playwright-report** artifact for E2E test results

## Writing Tests

### Backend Unit Test

```python
# tests/test_schedule_service.py
import pytest
from src.services.schedule import ScheduleService

@pytest.mark.unit
def test_schedule_validation():
    service = ScheduleService()
    result = service.validate_constraints(mock_data)
    assert result.is_valid
    assert len(result.conflicts) == 0
```

### Frontend Component Test

```typescript
// src/components/__tests__/ScheduleRunner.test.tsx
import { render, screen } from '@testing-library/react'
import { ScheduleRunner } from '../schedule/ScheduleRunner'

describe('ScheduleRunner', () => {
  it('renders generate button', () => {
    render(<ScheduleRunner />)
    expect(screen.getByRole('button', { name: /generate/i })).toBeInTheDocument()
  })
})
```

### E2E Test

```typescript
// frontend/e2e/schedule.spec.ts
import { test, expect } from "@playwright/test";

test("can generate schedule", async ({ page }) => {
  await page.goto("/dashboard");
  await page.click('[data-testid="generate-btn"]');
  await expect(page.locator(".schedule-grid")).toBeVisible();
});
```

## Test Coverage

Generate HTML coverage reports:

```bash
# Backend
cd backend
pytest --cov=src --cov-report=html
open htmlcov/index.html

# Frontend
cd frontend
npm run test:coverage
```

## Troubleshooting

### Docker not running

```bash
# Start Docker Desktop, then retry
docker-compose --profile dev up -d
```

### Port conflicts

```bash
# Stop other PostgreSQL instances
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
