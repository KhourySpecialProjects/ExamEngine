"""
Test configuration and fixtures for database tests.
"""

import enum
import json
import uuid
from datetime import datetime, time

import pytest
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Time, create_engine
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool


# Create a test-compatible base
class TestBase(DeclarativeBase):
    pass


# Test-compatible models that work with SQLite
class TestUsers(TestBase):
    __tablename__ = "users"
    user_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(25), nullable=False)
    email: Mapped[str] = mapped_column(String(25), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(50), nullable=False)


class TestDatasets(TestBase):
    __tablename__ = "datasets"
    dataset_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    semester: Mapped[str] = mapped_column(String(10))
    upload_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"))
    file_paths: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # JSON as string for SQLite


class TestStudents(TestBase):
    __tablename__ = "students"
    student_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.dataset_id"))


class TestCourses(TestBase):
    __tablename__ = "courses"
    course_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    course_subject_code: Mapped[str] = mapped_column(String)
    enrollment_count: Mapped[int] = mapped_column(Integer)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.dataset_id"))


class TestConflicts(TestBase):
    __tablename__ = "conflicts"
    conflict_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    student_id: Mapped[str] = mapped_column(ForeignKey("students.student_id"))
    exam_assignment_ids: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # JSON as string
    conflict_type: Mapped[str] = mapped_column(String)
    schedule_id: Mapped[str] = mapped_column(ForeignKey("schedules.schedule_id"))


class TestExamAssignments(TestBase):
    __tablename__ = "exam_assignments"
    exam_assignment_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.course_id"))
    time_slot_id: Mapped[str] = mapped_column(ForeignKey("time_slots.time_slot_id"))
    room_id: Mapped[str] = mapped_column(ForeignKey("rooms.room_id"))
    schedule_id: Mapped[str] = mapped_column(ForeignKey("schedules.schedule_id"))


class TestRooms(TestBase):
    __tablename__ = "rooms"
    room_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    location: Mapped[str] = mapped_column(String(50))
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.dataset_id"))


class TestDayEnum(enum.Enum):
    Monday = "Monday"
    Tuesday = "Tuesday"
    Wednesday = "Wednesday"
    Thursday = "Thursday"
    Friday = "Friday"


class TestTimeSlots(TestBase):
    __tablename__ = "time_slots"
    time_slot_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    slot_label: Mapped[str] = mapped_column(String(10))
    day: Mapped[TestDayEnum] = mapped_column(SQLEnum(TestDayEnum))
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.dataset_id"))


class TestSchedules(TestBase):
    __tablename__ = "schedules"
    schedule_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    schedule_name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.run_id"))


class TestStatusEnum(enum.Enum):
    Running = "Running"
    Completed = "Completed"
    Failed = "Failed"


class TestRuns(TestBase):
    __tablename__ = "runs"
    run_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.dataset_id"))
    run_timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"))
    algorithm_name: Mapped[str] = mapped_column(String(50))
    parameters: Mapped[str] = mapped_column(Text, nullable=True)  # JSON as string
    status: Mapped[TestStatusEnum] = mapped_column(SQLEnum(TestStatusEnum))


@pytest.fixture(scope="function")
def test_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestBase.metadata.create_all(engine)

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_user(test_db):
    """Create a sample user for testing."""
    user = TestUsers(
        name="Test User", email="test@example.com", password_hash="hashed_password"
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def sample_dataset(test_db, sample_user):
    """Create a sample dataset for testing."""
    dataset = TestDatasets(
        semester="Fall 2024",
        user_id=sample_user.user_id,
        file_paths=json.dumps(["path1.csv", "path2.csv"]),
    )
    test_db.add(dataset)
    test_db.commit()
    test_db.refresh(dataset)
    return dataset


@pytest.fixture
def sample_student(test_db, sample_dataset):
    """Create a sample student for testing."""
    student = TestStudents(dataset_id=sample_dataset.dataset_id)
    test_db.add(student)
    test_db.commit()
    test_db.refresh(student)
    return student


@pytest.fixture
def sample_course(test_db, sample_dataset):
    """Create a sample course for testing."""
    course = TestCourses(
        course_subject_code="CS101",
        enrollment_count=25,
        dataset_id=sample_dataset.dataset_id,
    )
    test_db.add(course)
    test_db.commit()
    test_db.refresh(course)
    return course


@pytest.fixture
def sample_room(test_db, sample_dataset):
    """Create a sample room for testing."""
    room = TestRooms(
        capacity=50, location="Room A101", dataset_id=sample_dataset.dataset_id
    )
    test_db.add(room)
    test_db.commit()
    test_db.refresh(room)
    return room


@pytest.fixture
def sample_time_slot(test_db, sample_dataset):
    """Create a sample time slot for testing."""
    time_slot = TestTimeSlots(
        slot_label="9AM-11AM",
        day=TestDayEnum.Monday,
        start_time=time(9, 0),
        end_time=time(11, 0),
        dataset_id=sample_dataset.dataset_id,
    )
    test_db.add(time_slot)
    test_db.commit()
    test_db.refresh(time_slot)
    return time_slot


@pytest.fixture
def sample_run(test_db, sample_dataset, sample_user):
    """Create a sample run for testing."""
    run = TestRuns(
        dataset_id=sample_dataset.dataset_id,
        user_id=sample_user.user_id,
        algorithm_name="Genetic Algorithm",
        parameters=json.dumps({"population_size": 100, "generations": 50}),
        status=TestStatusEnum.Completed,
    )
    test_db.add(run)
    test_db.commit()
    test_db.refresh(run)
    return run


@pytest.fixture
def sample_schedule(test_db, sample_run):
    """Create a sample schedule for testing."""
    schedule = TestSchedules(schedule_name="Test Schedule", run_id=sample_run.run_id)
    test_db.add(schedule)
    test_db.commit()
    test_db.refresh(schedule)
    return schedule
