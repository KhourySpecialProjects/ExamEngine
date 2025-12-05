"""
Tests for database schema models and relationships.

Tests cover:
- Model creation and validation
- Foreign key relationships
- Cascade deletions
- Enum types
- JSONB fields
- Unique constraints
"""

import datetime
import uuid

import pytest
from sqlalchemy import JSON, String, create_engine, event
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler
from sqlalchemy.orm import sessionmaker

from src.schemas.db import (
    Base,
    ConflictAnalyses,
    Courses,
    Datasets,
    DayEnum,
    ExamAssignments,
    Rooms,
    Runs,
    ScheduleShares,
    Schedules,
    StatusEnum,
    TimeSlots,
    Users,
)


# Monkey patch SQLite to support JSONB by converting it to JSON
def visit_JSONB(self, type_, **kw):
    """Convert JSONB to JSON for SQLite compatibility."""
    return self.visit_JSON(type_, **kw)


# Monkey patch SQLite to support UUID by converting it to String
def visit_UUID(self, type_, **kw):
    """Convert UUID to String for SQLite compatibility."""
    return self.visit_string(String(36), **kw)


SQLiteTypeCompiler.visit_JSONB = visit_JSONB
SQLiteTypeCompiler.visit_UUID = visit_UUID


@pytest.fixture
def test_db():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    
    # Enable foreign keys in SQLite
    @event.listens_for(engine, "connect", insert=True)
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_user(test_db):
    """Create a sample user for testing."""
    user = Users(
        user_id=uuid.uuid4(),
        name="Test User",
        email="test@northeastern.edu",
        password_hash="hashed_password",
        role="user",
        status="approved",
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def sample_admin(test_db):
    """Create a sample admin user for testing."""
    admin = Users(
        user_id=uuid.uuid4(),
        name="Admin User",
        email="admin@northeastern.edu",
        password_hash="hashed_password",
        role="admin",
        status="approved",
    )
    test_db.add(admin)
    test_db.commit()
    test_db.refresh(admin)
    return admin


@pytest.fixture
def sample_dataset(test_db, sample_user):
    """Create a sample dataset for testing."""
    dataset = Datasets(
        dataset_id=uuid.uuid4(),
        dataset_name="Test Dataset",
        user_id=sample_user.user_id,
        file_paths=[{"courses": "path/to/courses.csv", "enrollments": "path/to/enrollments.csv", "rooms": "path/to/rooms.csv"}],
    )
    test_db.add(dataset)
    test_db.commit()
    test_db.refresh(dataset)
    return dataset


class TestUsers:
    """Tests for Users model."""

    def test_create_user(self, test_db):
        """Test creating a user."""
        user = Users(
            user_id=uuid.uuid4(),
            name="John Doe",
            email="john@northeastern.edu",
            password_hash="hashed_password",
            role="user",
            status="pending",
        )
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)

        assert user.user_id is not None
        assert user.name == "John Doe"
        assert user.email == "john@northeastern.edu"
        assert user.role == "user"
        assert user.status == "pending"

    def test_user_email_unique(self, test_db, sample_user):
        """Test that email must be unique."""
        duplicate = Users(
            user_id=uuid.uuid4(),
            name="Another User",
            email=sample_user.email,  # Same email
            password_hash="hashed_password",
            role="user",
            status="pending",
        )
        test_db.add(duplicate)
        
        with pytest.raises(Exception):  # Should raise IntegrityError
            test_db.commit()

    def test_user_invitation_relationship(self, test_db, sample_admin):
        """Test user invitation relationships."""
        invited_user = Users(
            user_id=uuid.uuid4(),
            name="Invited User",
            email="invited@northeastern.edu",
            password_hash="hashed_password",
            role="user",
            status="pending",
            invited_by=sample_admin.user_id,
            invited_at=datetime.datetime.now(),
        )
        test_db.add(invited_user)
        test_db.commit()
        test_db.refresh(invited_user)

        assert invited_user.invited_by == sample_admin.user_id
        
        # Query the relationship directly to verify it works
        from sqlalchemy import select
        invited_users = test_db.scalars(
            select(Users).where(Users.invited_by == sample_admin.user_id)
        ).all()
        assert len(invited_users) == 1
        assert invited_users[0].user_id == invited_user.user_id

    def test_user_approval_relationship(self, test_db, sample_admin, sample_user):
        """Test user approval relationships."""
        sample_user.approved_by = sample_admin.user_id
        sample_user.approved_at = datetime.datetime.now()
        sample_user.status = "approved"
        test_db.commit()
        test_db.refresh(sample_user)

        assert sample_user.approved_by == sample_admin.user_id
        assert sample_user.status == "approved"
        
        # Query the relationship directly to verify it works
        from sqlalchemy import select
        approved_users = test_db.scalars(
            select(Users).where(Users.approved_by == sample_admin.user_id)
        ).all()
        assert len(approved_users) == 1
        assert approved_users[0].user_id == sample_user.user_id


class TestDatasets:
    """Tests for Datasets model."""

    def test_create_dataset(self, test_db, sample_user):
        """Test creating a dataset."""
        dataset = Datasets(
            dataset_id=uuid.uuid4(),
            dataset_name="Spring 2025 Courses",
            user_id=sample_user.user_id,
            file_paths=[{"courses": "s3://bucket/courses.csv"}],
        )
        test_db.add(dataset)
        test_db.commit()
        test_db.refresh(dataset)

        assert dataset.dataset_id is not None
        assert dataset.dataset_name == "Spring 2025 Courses"
        assert dataset.user_id == sample_user.user_id
        assert len(dataset.file_paths) == 1

    def test_dataset_user_relationship(self, test_db, sample_user):
        """Test dataset belongs to user."""
        dataset = Datasets(
            dataset_id=uuid.uuid4(),
            dataset_name="Test Dataset",
            user_id=sample_user.user_id,
            file_paths=[],
        )
        test_db.add(dataset)
        test_db.commit()
        test_db.refresh(sample_user)

        assert len(sample_user.datasets) == 1
        assert sample_user.datasets[0].dataset_id == dataset.dataset_id

    def test_dataset_soft_delete(self, test_db, sample_dataset):
        """Test dataset soft delete."""
        assert sample_dataset.deleted_at is None
        
        sample_dataset.deleted_at = datetime.datetime.now()
        test_db.commit()
        test_db.refresh(sample_dataset)

        assert sample_dataset.deleted_at is not None


class TestCourses:
    """Tests for Courses model."""

    def test_create_course(self, test_db, sample_dataset):
        """Test creating a course."""
        course = Courses(
            course_id=uuid.uuid4(),
            crn="12345",
            course_subject_code="CS 4535",
            enrollment_count=150,
            dataset_id=sample_dataset.dataset_id,
        )
        test_db.add(course)
        test_db.commit()
        test_db.refresh(course)

        assert course.course_id is not None
        assert course.crn == "12345"
        assert course.course_subject_code == "CS 4535"
        assert course.enrollment_count == 150

    def test_course_dataset_relationship(self, test_db, sample_dataset):
        """Test course belongs to dataset."""
        course = Courses(
            course_id=uuid.uuid4(),
            crn="12345",
            course_subject_code="CS 4535",
            enrollment_count=150,
            dataset_id=sample_dataset.dataset_id,
        )
        test_db.add(course)
        test_db.commit()
        test_db.refresh(sample_dataset)

        assert len(sample_dataset.courses) == 1
        assert sample_dataset.courses[0].course_id == course.course_id

    def test_course_cascade_delete(self, test_db, sample_dataset):
        """Test that courses are deleted when dataset is deleted."""
        course = Courses(
            course_id=uuid.uuid4(),
            crn="12345",
            course_subject_code="CS 4535",
            enrollment_count=150,
            dataset_id=sample_dataset.dataset_id,
        )
        test_db.add(course)
        test_db.commit()

        course_id = course.course_id
        test_db.delete(sample_dataset)
        test_db.commit()

        # Course should be deleted due to cascade
        deleted_course = test_db.query(Courses).filter_by(course_id=course_id).first()
        assert deleted_course is None


class TestRooms:
    """Tests for Rooms model."""

    def test_create_room(self, test_db, sample_dataset):
        """Test creating a room."""
        room = Rooms(
            room_id=uuid.uuid4(),
            capacity=100,
            location="WVH 101",
            dataset_id=sample_dataset.dataset_id,
        )
        test_db.add(room)
        test_db.commit()
        test_db.refresh(room)

        assert room.room_id is not None
        assert room.capacity == 100
        assert room.location == "WVH 101"

    def test_room_dataset_relationship(self, test_db, sample_dataset):
        """Test room belongs to dataset."""
        room = Rooms(
            room_id=uuid.uuid4(),
            capacity=100,
            location="WVH 101",
            dataset_id=sample_dataset.dataset_id,
        )
        test_db.add(room)
        test_db.commit()
        test_db.refresh(sample_dataset)

        assert len(sample_dataset.rooms) == 1
        assert sample_dataset.rooms[0].room_id == room.room_id


class TestTimeSlots:
    """Tests for TimeSlots model."""

    def test_create_time_slot(self, test_db, sample_dataset):
        """Test creating a time slot."""
        time_slot = TimeSlots(
            time_slot_id=uuid.uuid4(),
            slot_label="Monday 9:00-11:00",
            day=DayEnum.Monday,
            start_time=datetime.time(9, 0),
            end_time=datetime.time(11, 0),
            dataset_id=sample_dataset.dataset_id,
        )
        test_db.add(time_slot)
        test_db.commit()
        test_db.refresh(time_slot)

        assert time_slot.time_slot_id is not None
        assert time_slot.day == DayEnum.Monday
        assert time_slot.start_time == datetime.time(9, 0)

    def test_time_slot_enum(self, test_db, sample_dataset):
        """Test that DayEnum is properly used."""
        for day in DayEnum:
            time_slot = TimeSlots(
                time_slot_id=uuid.uuid4(),
                slot_label=f"{day.value} 9:00-11:00",
                day=day,
                start_time=datetime.time(9, 0),
                end_time=datetime.time(11, 0),
                dataset_id=sample_dataset.dataset_id,
            )
            test_db.add(time_slot)
        
        test_db.commit()
        
        slots = test_db.query(TimeSlots).filter_by(dataset_id=sample_dataset.dataset_id).all()
        assert len(slots) == len(DayEnum)


class TestRuns:
    """Tests for Runs model."""

    def test_create_run(self, test_db, sample_dataset, sample_user):
        """Test creating a run."""
        run = Runs(
            run_id=uuid.uuid4(),
            dataset_id=sample_dataset.dataset_id,
            user_id=sample_user.user_id,
            algorithm_name="DSATUR",
            parameters={"max_days": 7, "student_max_per_day": 3},
            status=StatusEnum.Running,
        )
        test_db.add(run)
        test_db.commit()
        test_db.refresh(run)

        assert run.run_id is not None
        assert run.algorithm_name == "DSATUR"
        assert run.status == StatusEnum.Running
        assert run.parameters["max_days"] == 7

    def test_run_status_enum(self, test_db, sample_dataset, sample_user):
        """Test that StatusEnum is properly used."""
        for status in StatusEnum:
            run = Runs(
                run_id=uuid.uuid4(),
                dataset_id=sample_dataset.dataset_id,
                user_id=sample_user.user_id,
                algorithm_name="DSATUR",
                parameters={},
                status=status,
            )
            test_db.add(run)
        
        test_db.commit()
        
        runs = test_db.query(Runs).filter_by(dataset_id=sample_dataset.dataset_id).all()
        assert len(runs) == len(StatusEnum)


class TestSchedules:
    """Tests for Schedules model."""

    def test_create_schedule(self, test_db, sample_dataset, sample_user):
        """Test creating a schedule."""
        run = Runs(
            run_id=uuid.uuid4(),
            dataset_id=sample_dataset.dataset_id,
            user_id=sample_user.user_id,
            algorithm_name="DSATUR",
            parameters={},
            status=StatusEnum.Completed,
        )
        test_db.add(run)
        test_db.commit()

        schedule = Schedules(
            schedule_id=uuid.uuid4(),
            schedule_name="Spring 2025 Schedule",
            run_id=run.run_id,
        )
        test_db.add(schedule)
        test_db.commit()
        test_db.refresh(schedule)

        assert schedule.schedule_id is not None
        assert schedule.schedule_name == "Spring 2025 Schedule"
        assert schedule.run_id == run.run_id

    def test_schedule_run_relationship(self, test_db, sample_dataset, sample_user):
        """Test schedule belongs to run."""
        run = Runs(
            run_id=uuid.uuid4(),
            dataset_id=sample_dataset.dataset_id,
            user_id=sample_user.user_id,
            algorithm_name="DSATUR",
            parameters={},
            status=StatusEnum.Completed,
        )
        test_db.add(run)
        test_db.commit()

        schedule = Schedules(
            schedule_id=uuid.uuid4(),
            schedule_name="Test Schedule",
            run_id=run.run_id,
        )
        test_db.add(schedule)
        test_db.commit()
        test_db.refresh(run)

        assert len(run.schedules) == 1
        assert run.schedules[0].schedule_id == schedule.schedule_id


class TestExamAssignments:
    """Tests for ExamAssignments model."""

    def test_create_exam_assignment(self, test_db, sample_dataset, sample_user):
        """Test creating an exam assignment."""
        # Create dependencies
        course = Courses(
            course_id=uuid.uuid4(),
            crn="12345",
            course_subject_code="CS 4535",
            enrollment_count=150,
            dataset_id=sample_dataset.dataset_id,
        )
        room = Rooms(
            room_id=uuid.uuid4(),
            capacity=200,
            location="WVH 101",
            dataset_id=sample_dataset.dataset_id,
        )
        time_slot = TimeSlots(
            time_slot_id=uuid.uuid4(),
            slot_label="Monday 9:00-11:00",
            day=DayEnum.Monday,
            start_time=datetime.time(9, 0),
            end_time=datetime.time(11, 0),
            dataset_id=sample_dataset.dataset_id,
        )
        run = Runs(
            run_id=uuid.uuid4(),
            dataset_id=sample_dataset.dataset_id,
            user_id=sample_user.user_id,
            algorithm_name="DSATUR",
            parameters={},
            status=StatusEnum.Completed,
        )
        schedule = Schedules(
            schedule_id=uuid.uuid4(),
            schedule_name="Test Schedule",
            run_id=run.run_id,
        )
        
        test_db.add_all([course, room, time_slot, run, schedule])
        test_db.commit()

        # Create exam assignment
        exam_assignment = ExamAssignments(
            exam_assignment_id=uuid.uuid4(),
            course_id=course.course_id,
            time_slot_id=time_slot.time_slot_id,
            room_id=room.room_id,
            schedule_id=schedule.schedule_id,
        )
        test_db.add(exam_assignment)
        test_db.commit()
        test_db.refresh(exam_assignment)

        assert exam_assignment.exam_assignment_id is not None
        assert exam_assignment.course_id == course.course_id
        assert exam_assignment.time_slot_id == time_slot.time_slot_id
        assert exam_assignment.room_id == room.room_id

    def test_exam_assignment_relationships(self, test_db, sample_dataset, sample_user):
        """Test exam assignment relationships."""
        course = Courses(
            course_id=uuid.uuid4(),
            crn="12345",
            course_subject_code="CS 4535",
            enrollment_count=150,
            dataset_id=sample_dataset.dataset_id,
        )
        room = Rooms(
            room_id=uuid.uuid4(),
            capacity=200,
            location="WVH 101",
            dataset_id=sample_dataset.dataset_id,
        )
        time_slot = TimeSlots(
            time_slot_id=uuid.uuid4(),
            slot_label="Monday 9:00-11:00",
            day=DayEnum.Monday,
            start_time=datetime.time(9, 0),
            end_time=datetime.time(11, 0),
            dataset_id=sample_dataset.dataset_id,
        )
        run = Runs(
            run_id=uuid.uuid4(),
            dataset_id=sample_dataset.dataset_id,
            user_id=sample_user.user_id,
            algorithm_name="DSATUR",
            parameters={},
            status=StatusEnum.Completed,
        )
        schedule = Schedules(
            schedule_id=uuid.uuid4(),
            schedule_name="Test Schedule",
            run_id=run.run_id,
        )
        
        test_db.add_all([course, room, time_slot, run, schedule])
        test_db.commit()

        exam_assignment = ExamAssignments(
            exam_assignment_id=uuid.uuid4(),
            course_id=course.course_id,
            time_slot_id=time_slot.time_slot_id,
            room_id=room.room_id,
            schedule_id=schedule.schedule_id,
        )
        test_db.add(exam_assignment)
        test_db.commit()
        test_db.refresh(exam_assignment)

        # Test relationships
        assert exam_assignment.course.course_id == course.course_id
        assert exam_assignment.room.room_id == room.room_id
        assert exam_assignment.time_slot.time_slot_id == time_slot.time_slot_id
        assert exam_assignment.schedule.schedule_id == schedule.schedule_id


class TestConflictAnalyses:
    """Tests for ConflictAnalyses model."""

    def test_create_conflict_analysis(self, test_db, sample_dataset, sample_user):
        """Test creating a conflict analysis."""
        run = Runs(
            run_id=uuid.uuid4(),
            dataset_id=sample_dataset.dataset_id,
            user_id=sample_user.user_id,
            algorithm_name="DSATUR",
            parameters={},
            status=StatusEnum.Completed,
        )
        schedule = Schedules(
            schedule_id=uuid.uuid4(),
            schedule_name="Test Schedule",
            run_id=run.run_id,
        )
        test_db.add_all([run, schedule])
        test_db.commit()

        conflicts_data = {
            "hard_conflicts": {
                "student_double_book": [
                    {
                        "entity_id": "2003575",
                        "day": "Monday",
                        "block": 0,
                        "crn": "10001",
                        "conflicting_crn": "10002",
                    }
                ],
            },
            "soft_conflicts": {},
            "statistics": {
                "student_double_book_count": 1,
                "total_hard_conflicts": 1,
            },
        }

        analysis = ConflictAnalyses(
            analysis_id=uuid.uuid4(),
            schedule_id=schedule.schedule_id,
            conflicts=conflicts_data,
        )
        test_db.add(analysis)
        test_db.commit()
        test_db.refresh(analysis)

        assert analysis.analysis_id is not None
        assert analysis.schedule_id == schedule.schedule_id
        assert analysis.conflicts["statistics"]["total_hard_conflicts"] == 1

    def test_conflict_analysis_unique_schedule(self, test_db, sample_dataset, sample_user):
        """Test that each schedule can only have one conflict analysis."""
        run = Runs(
            run_id=uuid.uuid4(),
            dataset_id=sample_dataset.dataset_id,
            user_id=sample_user.user_id,
            algorithm_name="DSATUR",
            parameters={},
            status=StatusEnum.Completed,
        )
        schedule = Schedules(
            schedule_id=uuid.uuid4(),
            schedule_name="Test Schedule",
            run_id=run.run_id,
        )
        test_db.add_all([run, schedule])
        test_db.commit()

        analysis1 = ConflictAnalyses(
            analysis_id=uuid.uuid4(),
            schedule_id=schedule.schedule_id,
            conflicts={},
        )
        test_db.add(analysis1)
        test_db.commit()

        # Try to create second analysis for same schedule
        analysis2 = ConflictAnalyses(
            analysis_id=uuid.uuid4(),
            schedule_id=schedule.schedule_id,
            conflicts={},
        )
        test_db.add(analysis2)
        
        with pytest.raises(Exception):  # Should raise IntegrityError due to unique constraint
            test_db.commit()


class TestScheduleShares:
    """Tests for ScheduleShares model."""

    def test_create_schedule_share(self, test_db, sample_dataset, sample_user, sample_admin):
        """Test creating a schedule share."""
        run = Runs(
            run_id=uuid.uuid4(),
            dataset_id=sample_dataset.dataset_id,
            user_id=sample_user.user_id,
            algorithm_name="DSATUR",
            parameters={},
            status=StatusEnum.Completed,
        )
        schedule = Schedules(
            schedule_id=uuid.uuid4(),
            schedule_name="Test Schedule",
            run_id=run.run_id,
        )
        test_db.add_all([run, schedule])
        test_db.commit()

        share = ScheduleShares(
            share_id=uuid.uuid4(),
            schedule_id=schedule.schedule_id,
            shared_with_user_id=sample_admin.user_id,
            shared_by_user_id=sample_user.user_id,
            permission="view",
        )
        test_db.add(share)
        test_db.commit()
        test_db.refresh(share)

        assert share.share_id is not None
        assert share.schedule_id == schedule.schedule_id
        assert share.shared_with_user_id == sample_admin.user_id
        assert share.permission == "view"

    def test_schedule_share_relationships(self, test_db, sample_dataset, sample_user, sample_admin):
        """Test schedule share relationships."""
        run = Runs(
            run_id=uuid.uuid4(),
            dataset_id=sample_dataset.dataset_id,
            user_id=sample_user.user_id,
            algorithm_name="DSATUR",
            parameters={},
            status=StatusEnum.Completed,
        )
        schedule = Schedules(
            schedule_id=uuid.uuid4(),
            schedule_name="Test Schedule",
            run_id=run.run_id,
        )
        test_db.add_all([run, schedule])
        test_db.commit()

        share = ScheduleShares(
            share_id=uuid.uuid4(),
            schedule_id=schedule.schedule_id,
            shared_with_user_id=sample_admin.user_id,
            shared_by_user_id=sample_user.user_id,
            permission="edit",
        )
        test_db.add(share)
        test_db.commit()
        test_db.refresh(share)

        # Test relationships
        assert share.schedule.schedule_id == schedule.schedule_id
        assert share.shared_with_user.user_id == sample_admin.user_id
        assert share.shared_by_user.user_id == sample_user.user_id


