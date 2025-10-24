# DSATUR Algorithm Testing Suite

This directory contains comprehensive tests for the Enhanced DSATUR scheduling algorithm and related validation components.

## Test Structure

```
backend/tests/
├── conftest.py                           # Pytest configuration and shared fixtures
├── test_enhanced_dsatur_algorithm.py     # Core algorithm tests
├── test_master_validation.py            # Master validation script tests
├── test_summary_generation.py           # Summary generation tests
├── manual_summary_generation.py         # Manual summary generation utility
├── run_tests.py                         # Test runner script
└── README.md                            # This file
```

## Test Categories

### 1. Unit Tests (`test_enhanced_dsatur_algorithm.py`)
- **Algorithm Initialization**: Test data loading and preprocessing
- **Graph Building**: Test conflict graph construction
- **DSATUR Coloring**: Test graph coloring algorithm
- **Hard Constraints**: Test constraint enforcement (no double-booking)
- **Soft Penalties**: Test penalty calculation for preferences
- **Scheduling Process**: Test complete scheduling workflow
- **Room Assignment**: Test room allocation logic
- **Summary Generation**: Test algorithm summary statistics
- **Data Normalization**: Test handling of different column formats
- **Edge Cases**: Test error handling and empty data

### 2. Integration Tests (`test_master_validation.py`)
- **Data Loading**: Test loading of cleaned data files
- **Scheduling Algorithm**: Test with real data
- **Conflict Analysis**: Test student conflict detection
- **Capacity Analysis**: Test room capacity violation detection
- **Report Generation**: Test comprehensive report creation
- **Mock Data Workflow**: Test with synthetic data

### 3. Summary Generation Tests (`test_summary_generation.py`)
- **Summary Creation**: Test algorithm summary generation
- **Report Validation**: Test report content and structure

## Running Tests

### Quick Start
```bash
# Run all tests
python run_tests.py

# Run specific test categories
python run_tests.py --unit
python run_tests.py --integration
python run_tests.py --algorithm
python run_tests.py --validation
```

### Using Pytest Directly
```bash
# Run all tests
pytest -v

# Run specific test files
pytest test_enhanced_dsatur_algorithm.py -v
pytest test_master_validation.py -v

# Run with markers
pytest -m integration -v
pytest -m slow -v
```

### Individual Test Execution
```bash
# Run algorithm tests with real data
python test_enhanced_dsatur_algorithm.py --integration

# Run validation tests
python test_master_validation.py

# Test summary generation
python test_summary_generation.py
```

## Test Data

### Sample Data (Unit Tests)
- **Small Dataset**: 5 courses, 10 enrollments, 5 classrooms
- **Mock Data**: Synthetic data for isolated testing
- **Edge Cases**: Empty data, missing columns, invalid formats

### Real Data (Integration Tests)
- **Cleaned Data**: Uses `final_classcensus.csv`, `final_enrollment.csv`, `final_classrooms.csv`
- **Full Workflow**: Complete algorithm execution with real data
- **Performance Testing**: Large dataset stress testing

## Test Validation Criteria

### Hard Constraints (Must be 0)
- **Student Conflicts**: No student double-booked in same time slot
- **Instructor Conflicts**: No instructor teaching multiple courses simultaneously
- **Student Limits**: No student with >2 exams per day

### Soft Constraints (Optimization Goals)
- **Back-to-Back Prevention**: Minimize consecutive exams for students/instructors
- **Large Course Scheduling**: Prefer early days for large courses (≥100 students)
- **Room Utilization**: Efficient use of available classroom space

### Performance Metrics
- **Scheduling Success Rate**: Percentage of courses successfully scheduled
- **Room Utilization**: Average capacity utilization across all rooms
- **Time Distribution**: Balanced distribution across days and time blocks
- **Conflict Minimization**: Reduced soft constraint violations

## Test Configuration

### Pytest Markers
- `@pytest.mark.integration`: Tests requiring real data files
- `@pytest.mark.slow`: Tests that may take longer to run
- `@pytest.mark.stress`: Stress tests with large datasets

### Fixtures
- `sample_census_data`: Small census dataset for unit tests
- `sample_enrollment_data`: Small enrollment dataset for unit tests
- `sample_classroom_data`: Small classroom dataset for unit tests
- `large_census_data`: Large dataset for stress testing
- `mock_schedule_data`: Mock schedule for testing analysis functions

## Expected Test Results

### Successful Test Run Should Show:
```
Running Unit Tests
==================================================
Algorithm initialization test passed
Graph building test passed
DSATUR coloring test passed
Hard constraints test passed
Soft penalty calculation test passed
Scheduling process test passed
Room assignment test passed
Summary generation test passed

Running Integration Tests
==================================================
Data loading test passed
Scheduling algorithm test passed
Conflict analysis test passed
Capacity violation analysis test passed
Report generation test passed

Test Results Summary
==================================================
Unit Tests           PASSED
Algorithm Tests      PASSED
Validation Tests     PASSED
Integration Tests    PASSED

