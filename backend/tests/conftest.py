import pandas as pd
import pytest


@pytest.fixture(scope="session")
def sample_census_data():
    """Sample census data for testing."""
    return pd.DataFrame(
        {
            "CRN": ["1001", "1002", "1003", "1004", "1005", "1006", "1007", "1008"],
            "course_ref": [
                "CS101",
                "MATH201",
                "PHYS301",
                "CHEM401",
                "BIO501",
                "CS102",
                "MATH202",
                "PHYS302",
            ],
            "num_students": [30, 25, 40, 20, 35, 28, 22, 45],
        }
    )


@pytest.fixture(scope="session")
def sample_enrollment_data():
    """Sample enrollment data for testing."""
    return pd.DataFrame(
        {
            "student_id": [
                "S001",
                "S001",
                "S001",  # Student S001 takes 3 courses
                "S002",
                "S002",
                "S002",  # Student S002 takes 3 courses
                "S003",
                "S003",  # Student S003 takes 2 courses
                "S004",
                "S004",  # Student S004 takes 2 courses
                "S005",
                "S005",  # Student S005 takes 2 courses
                "S006",
                "S006",  # Student S006 takes 2 courses
                "S007",
                "S007",  # Student S007 takes 2 courses
                "S008",
                "S008",  # Student S008 takes 2 courses
            ],
            "CRN": [
                "1001",
                "1002",
                "1003",  # S001's courses
                "1001",
                "1004",
                "1005",  # S002's courses
                "1002",
                "1006",  # S003's courses
                "1003",
                "1007",  # S004's courses
                "1004",
                "1008",  # S005's courses
                "1005",
                "1006",  # S006's courses
                "1007",
                "1008",  # S007's courses
                "1001",
                "1002",  # S008's courses
            ],
            "instructor_name": [
                "Dr. Smith",
                "Dr. Smith",
                "Dr. Jones",  # S001's instructors
                "Dr. Smith",
                "Dr. Brown",
                "Dr. Brown",  # S002's instructors
                "Dr. Smith",
                "Dr. Wilson",  # S003's instructors
                "Dr. Jones",
                "Dr. Wilson",  # S004's instructors
                "Dr. Brown",
                "Dr. Davis",  # S005's instructors
                "Dr. Brown",
                "Dr. Wilson",  # S006's instructors
                "Dr. Wilson",
                "Dr. Davis",  # S007's instructors
                "Dr. Smith",
                "Dr. Smith",  # S008's instructors
            ],
        }
    )


@pytest.fixture(scope="session")
def sample_classroom_data():
    """Sample classroom data for testing."""
    return pd.DataFrame(
        {
            "room_name": ["Room A", "Room B", "Room C", "Room D", "Room E", "Room F"],
            "capacity": [50, 40, 30, 25, 45, 35],
        }
    )


@pytest.fixture(scope="session")
def large_census_data():
    """Large census dataset for stress testing."""
    crns = [f"{1000 + i}" for i in range(100)]
    courses = [f"CS{100 + i}" for i in range(100)]
    sizes = [20 + (i % 50) for i in range(100)]  # Sizes between 20-69

    return pd.DataFrame({"CRN": crns, "course_ref": courses, "num_students": sizes})


@pytest.fixture(scope="session")
def large_enrollment_data(large_census_data):
    """Large enrollment dataset for stress testing."""
    # Create 500 students, each taking 2-4 courses
    enrollments = []
    student_id = 1

    for crn in large_census_data["CRN"]:
        # Each course has 20-69 students
        course_size = large_census_data[large_census_data["CRN"] == crn][
            "num_students"
        ].iloc[0]

        for _i in range(course_size):
            enrollments.append(
                {
                    "student_id": f"S{student_id:04d}",
                    "CRN": crn,
                    "instructor_name": f"Dr. Instructor{(student_id % 20) + 1}",
                }
            )
            student_id += 1

    return pd.DataFrame(enrollments)


@pytest.fixture(scope="session")
def large_classroom_data():
    """Large classroom dataset for stress testing."""
    rooms = [
        f"Room {chr(65 + i)}" for i in range(50)
    ]  # Room A through Room Z, then Room AA, etc.
    capacities = [30 + (i % 40) for i in range(50)]  # Capacities between 30-69

    return pd.DataFrame({"room_name": rooms, "capacity": capacities})


@pytest.fixture
def mock_schedule_data():
    """Mock schedule data for testing."""
    return pd.DataFrame(
        {
            "CRN": ["1001", "1002", "1003", "1004", "1005"],
            "Course": ["CS101", "MATH201", "PHYS301", "CHEM401", "BIO501"],
            "Day": ["Mon", "Tue", "Wed", "Thu", "Fri"],
            "Block": [
                "0 (9:00-11:00)",
                "1 (11:30-1:30)",
                "2 (2:00-4:00)",
                "3 (4:30-6:30)",
                "4 (7:00-9:00)",
            ],
            "Room": ["Room A", "Room B", "Room C", "Room D", "Room E"],
            "Capacity": [50, 40, 30, 25, 45],
            "Size": [30, 25, 40, 20, 35],
            "Valid": [True, True, True, True, True],
        }
    )


@pytest.fixture
def mock_conflict_data():
    """Mock conflict data for testing."""
    return pd.DataFrame(
        {
            "Student_ID": ["S001", "S002", "S003"],
            "CRN_1": ["1001", "1002", "1003"],
            "CRN_2": ["1002", "1003", "1004"],
            "Day": ["Mon", "Tue", "Wed"],
            "Block": ["0 (9:00-11:00)", "1 (11:30-1:30)", "2 (2:00-4:00)"],
        }
    )


@pytest.fixture
def mock_capacity_violations():
    """Mock capacity violation data for testing."""
    return pd.DataFrame(
        {
            "CRN": ["1001", "1002"],
            "Size": [60, 45],
            "Capacity": [50, 40],
            "Overflow": [10, 5],
        }
    )


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "stress: mark test as stress test")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test names."""
    for item in items:
        # Add integration marker to tests that use real data
        if "integration" in item.name or "real_data" in item.name:
            item.add_marker(pytest.mark.integration)

        # Add slow marker to tests that might be slow
        if "large" in item.name or "stress" in item.name:
            item.add_marker(pytest.mark.slow)

        # Add stress marker to stress tests
        if "stress" in item.name:
            item.add_marker(pytest.mark.stress)
