# Testing Guide

This document explains how to run tests for the ExamEngine project.

## Prerequisites

### Required Software
- **Python 3.12+** - The backend is built with Python
- **Docker & Docker Compose** - For running the full application stack
- **Git** - For version control

### Optional (for local development)
- **PostgreSQL** - If you want to run tests against a real database instead of SQLite
- **Node.js 18+** - For frontend development (tests run in Docker)

## Test Structure

The project uses **pytest** for testing with the following structure:

```
backend/tests/
├── conftest.py          # Test configuration and fixtures
├── pytest.ini          # Pytest configuration
└── test_simple_models.py # Model unit tests
```

### Test Types
- **Unit Tests**: Test individual model functionality using in-memory SQLite
- **Integration Tests**: Test database interactions (marked with `@pytest.mark.integration`)
- **Slow Tests**: Long-running tests (marked with `@pytest.mark.slow`)

## Running Tests

### Option 1: Using Docker (Recommended)

This is the easiest way to run tests as it handles all dependencies automatically.

#### Start the test environment:
```bash
# Start only the database service
docker-compose up db -d

# Or start the full stack (optional)
docker-compose up -d
```

#### Run tests in Docker:
```bash
# Run all tests
docker-compose exec backend pytest

# Run with verbose output
docker-compose exec backend pytest -v

# Run specific test file
docker-compose exec backend pytest tests/test_simple_models.py

# Run tests with coverage
docker-compose exec backend pytest --cov=src --cov-report=html

# Run only unit tests (exclude slow/integration tests)
docker-compose exec backend pytest -m "not slow and not integration"
```

### Option 2: Local Development

If you prefer to run tests locally without Docker:

#### 1. Set up Python environment:
```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### 2. Run tests:
```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_simple_models.py

# Run with coverage
pytest --cov=src --cov-report=html

# Run only fast tests
pytest -m "not slow"
```

## Test Configuration

### Pytest Configuration (`pytest.ini`)
- **Test Discovery**: Automatically finds `test_*.py` files
- **Verbose Output**: Shows detailed test results
- **Color Output**: Colored terminal output for better readability
- **Markers**: Supports `slow`, `integration`, and `unit` test markers

### Test Database
- **In-Memory SQLite**: Tests use SQLite in-memory database for speed
- **Isolated Tests**: Each test gets a fresh database session
- **Test Models**: Special test-compatible models in `conftest.py`

## Test Fixtures

The test suite includes several fixtures for common test data:

- `test_db`: In-memory SQLite database session
- `sample_user`: Test user with valid data
- `sample_dataset`: Test dataset linked to a user
- `sample_student`: Test student record
- `sample_course`: Test course with enrollment data
- `sample_room`: Test room with capacity
- `sample_time_slot`: Test time slot with day/time
- `sample_run`: Test algorithm run
- `sample_schedule`: Test exam schedule

## Writing New Tests

### Basic Test Structure:
```python
def test_model_creation(test_db, sample_user):
    """Test creating a new model instance."""
    # Arrange
    new_model = TestModel(
        name="Test Name",
        user_id=sample_user.user_id
    )
    
    # Act
    test_db.add(new_model)
    test_db.commit()
    test_db.refresh(new_model)
    
    # Assert
    assert new_model.name == "Test Name"
    assert new_model.user_id == sample_user.user_id
```

### Test Markers:
```python
@pytest.mark.slow
def test_expensive_operation():
    """This test takes a long time to run."""
    pass

@pytest.mark.integration
def test_database_integration():
    """This test requires database integration."""
    pass
```

## Troubleshooting

### Common Issues

#### 1. Docker not running
**Error**: `Cannot connect to the Docker daemon`
**Solution**: Start Docker Desktop or Docker service

#### 2. Port conflicts
**Error**: `Port 5432 is already in use`
**Solution**: Stop other PostgreSQL instances or change port in `docker-compose.yml`

#### 3. Permission issues (Linux/macOS)
**Error**: `Permission denied` when running Docker commands
**Solution**: Add your user to the docker group or use `sudo`

#### 4. Python import errors
**Error**: `ModuleNotFoundError`
**Solution**: Ensure you're in the correct directory and have activated the virtual environment

### Debug Mode
Run tests with maximum verbosity for debugging:
```bash
docker-compose exec backend pytest -vvv --tb=long
```

### Test Coverage
Generate HTML coverage report:
```bash
docker-compose exec backend pytest --cov=src --cov-report=html
# Open htmlcov/index.html in your browser
```

## Continuous Integration

The test suite is designed to run in CI/CD environments:

- **Fast execution**: Most tests complete in seconds
- **No external dependencies**: Uses in-memory SQLite
- **Deterministic**: Tests produce consistent results
- **Isolated**: Each test is independent

## Performance

- **Unit Tests**: ~1-5 seconds total
- **Integration Tests**: ~5-15 seconds total
- **Full Test Suite**: ~10-30 seconds total

## Next Steps

1. **Add more test coverage** for business logic
2. **Implement integration tests** for API endpoints
3. **Add performance tests** for large datasets
4. **Set up automated testing** in CI/CD pipeline

For questions or issues, check the project's main README or create an issue in the repository.
