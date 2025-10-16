"""
Simple unit tests for SQLAlchemy models using test-compatible models.
"""
import pytest
import uuid
import json
from datetime import datetime, time

from .conftest import (
    TestUsers, TestDatasets, TestStudents, TestCourses, TestRooms, TestTimeSlots, 
    TestDayEnum, TestExamAssignments, TestConflicts, TestSchedules, TestRuns, TestStatusEnum
)


class TestUsersModel:
    """Test cases for Users model."""
    
    def test_create_user(self, test_db):
        """Test creating a user with valid data."""
        user = TestUsers(
            name="John Doe",
            email="john@example.com",
            password_hash="hashed_password"
        )
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        assert user.name == "John Doe"
        assert user.email == "john@example.com"
        assert user.password_hash == "hashed_password"
        assert isinstance(user.user_id, str)
        assert len(user.user_id) == 36  # UUID string length
    
    def test_user_unique_email(self, test_db):
        """Test that email must be unique."""
        user1 = TestUsers(
            name="User 1",
            email="same@example.com",
            password_hash="hash1"
        )
        user2 = TestUsers(
            name="User 2",
            email="same@example.com",
            password_hash="hash2"
        )
        
        test_db.add(user1)
        test_db.commit()
        
        test_db.add(user2)
        with pytest.raises(Exception):  # Should raise integrity error
            test_db.commit()


class TestDatasetsModel:
    """Test cases for Datasets model."""
    
    def test_create_dataset(self, test_db, sample_user):
        """Test creating a dataset with valid data."""
        dataset = TestDatasets(
            semester="Spring 2024",
            user_id=sample_user.user_id,
            file_paths=json.dumps(["file1.csv", "file2.csv"])
        )
        test_db.add(dataset)
        test_db.commit()
        test_db.refresh(dataset)
        
        assert dataset.semester == "Spring 2024"
        assert dataset.user_id == sample_user.user_id
        assert json.loads(dataset.file_paths) == ["file1.csv", "file2.csv"]
        assert isinstance(dataset.dataset_id, str)
        assert isinstance(dataset.upload_date, datetime)


class TestStudentsModel:
    """Test cases for Students model."""
    
    def test_create_student(self, test_db, sample_dataset):
        """Test creating a student with valid dataset."""
        student = TestStudents(dataset_id=sample_dataset.dataset_id)
        test_db.add(student)
        test_db.commit()
        test_db.refresh(student)
        
        assert student.dataset_id == sample_dataset.dataset_id
        assert isinstance(student.student_id, str)


class TestCoursesModel:
    """Test cases for Courses model."""
    
    def test_create_course(self, test_db, sample_dataset):
        """Test creating a course with valid data."""
        course = TestCourses(
            course_subject_code="MATH101",
            enrollment_count=30,
            dataset_id=sample_dataset.dataset_id
        )
        test_db.add(course)
        test_db.commit()
        test_db.refresh(course)
        
        assert course.course_subject_code == "MATH101"
        assert course.enrollment_count == 30
        assert course.dataset_id == sample_dataset.dataset_id
        assert isinstance(course.course_id, str)


class TestRoomsModel:
    """Test cases for Rooms model."""
    
    def test_create_room(self, test_db, sample_dataset):
        """Test creating a room with valid data."""
        room = TestRooms(
            capacity=75,
            location="Building B, Room 205",
            dataset_id=sample_dataset.dataset_id
        )
        test_db.add(room)
        test_db.commit()
        test_db.refresh(room)
        
        assert room.capacity == 75
        assert room.location == "Building B, Room 205"
        assert room.dataset_id == sample_dataset.dataset_id
        assert isinstance(room.room_id, str)
    
    def test_room_capacity_required(self, test_db, sample_dataset):
        """Test that room capacity is required."""
        room = TestRooms(
            location="Test Room",
            dataset_id=sample_dataset.dataset_id
        )
        test_db.add(room)
        with pytest.raises(Exception):  # Should raise validation error
            test_db.commit()


class TestTimeSlotsModel:
    """Test cases for TimeSlots model."""
    
    def test_create_time_slot(self, test_db, sample_dataset):
        """Test creating a time slot with valid data."""
        time_slot = TestTimeSlots(
            slot_label="2PM-4PM",
            day=TestDayEnum.Tuesday,
            start_time=time(14, 0),
            end_time=time(16, 0),
            dataset_id=sample_dataset.dataset_id
        )
        test_db.add(time_slot)
        test_db.commit()
        test_db.refresh(time_slot)
        
        assert time_slot.slot_label == "2PM-4PM"
        assert time_slot.day == TestDayEnum.Tuesday
        assert time_slot.start_time == time(14, 0)
        assert time_slot.end_time == time(16, 0)
        assert isinstance(time_slot.time_slot_id, str)
    
    def test_all_day_enum_values(self, test_db, sample_dataset):
        """Test that all day enum values work."""
        days = [TestDayEnum.Monday, TestDayEnum.Tuesday, TestDayEnum.Wednesday, 
                TestDayEnum.Thursday, TestDayEnum.Friday]
        
        for day in days:
            time_slot = TestTimeSlots(
                slot_label=f"{day.value} Slot",
                day=day,
                start_time=time(9, 0),
                end_time=time(11, 0),
                dataset_id=sample_dataset.dataset_id
            )
            test_db.add(time_slot)
        
        test_db.commit()
        
        # Verify all were created
        created_slots = test_db.query(TestTimeSlots).all()
        assert len(created_slots) == len(days)


class TestRunsModel:
    """Test cases for Runs model."""
    
    def test_create_run(self, test_db, sample_dataset, sample_user):
        """Test creating a run with valid data."""
        run = TestRuns(
            dataset_id=sample_dataset.dataset_id,
            user_id=sample_user.user_id,
            algorithm_name="Simulated Annealing",
            parameters=json.dumps({"temperature": 1000, "cooling_rate": 0.95}),
            status=TestStatusEnum.Running
        )
        test_db.add(run)
        test_db.commit()
        test_db.refresh(run)
        
        assert run.dataset_id == sample_dataset.dataset_id
        assert run.user_id == sample_user.user_id
        assert run.algorithm_name == "Simulated Annealing"
        assert json.loads(run.parameters) == {"temperature": 1000, "cooling_rate": 0.95}
        assert run.status == TestStatusEnum.Running
        assert isinstance(run.run_id, str)
        assert isinstance(run.run_timestamp, datetime)
    
    def test_all_status_enum_values(self, test_db, sample_dataset, sample_user):
        """Test that all status enum values work."""
        statuses = [TestStatusEnum.Running, TestStatusEnum.Completed, TestStatusEnum.Failed]
        
        for status in statuses:
            run = TestRuns(
                dataset_id=sample_dataset.dataset_id,
                user_id=sample_user.user_id,
                algorithm_name=f"Test Algorithm {status.value}",
                status=status
            )
            test_db.add(run)
        
        test_db.commit()
        
        # Verify all were created
        created_runs = test_db.query(TestRuns).all()
        assert len(created_runs) == len(statuses)


class TestSchedulesModel:
    """Test cases for Schedules model."""
    
    def test_create_schedule(self, test_db, sample_run):
        """Test creating a schedule with valid data."""
        schedule = TestSchedules(
            schedule_name="Final Exam Schedule 2024",
            run_id=sample_run.run_id
        )
        test_db.add(schedule)
        test_db.commit()
        test_db.refresh(schedule)
        
        assert schedule.schedule_name == "Final Exam Schedule 2024"
        assert schedule.run_id == sample_run.run_id
        assert isinstance(schedule.schedule_id, str)
        assert isinstance(schedule.created_at, datetime)
    
    def test_schedule_name_unique(self, test_db, sample_run):
        """Test that schedule name must be unique."""
        schedule1 = TestSchedules(
            schedule_name="Unique Schedule",
            run_id=sample_run.run_id
        )
        schedule2 = TestSchedules(
            schedule_name="Unique Schedule",
            run_id=sample_run.run_id
        )
        
        test_db.add(schedule1)
        test_db.commit()
        
        test_db.add(schedule2)
        with pytest.raises(Exception):  # Should raise integrity error
            test_db.commit()


class TestExamAssignmentsModel:
    """Test cases for ExamAssignments model."""
    
    def test_create_exam_assignment(self, test_db, sample_course, sample_time_slot, sample_room, sample_schedule):
        """Test creating an exam assignment with all required relationships."""
        assignment = TestExamAssignments(
            course_id=sample_course.course_id,
            time_slot_id=sample_time_slot.time_slot_id,
            room_id=sample_room.room_id,
            schedule_id=sample_schedule.schedule_id
        )
        test_db.add(assignment)
        test_db.commit()
        test_db.refresh(assignment)
        
        assert assignment.course_id == sample_course.course_id
        assert assignment.time_slot_id == sample_time_slot.time_slot_id
        assert assignment.room_id == sample_room.room_id
        assert assignment.schedule_id == sample_schedule.schedule_id
        assert isinstance(assignment.exam_assignment_id, str)


class TestConflictsModel:
    """Test cases for Conflicts model."""
    
    def test_create_conflict(self, test_db, sample_student, sample_schedule):
        """Test creating a conflict with exam assignment IDs."""
        assignment_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
        
        conflict = TestConflicts(
            student_id=sample_student.student_id,
            exam_assignment_ids=json.dumps(assignment_ids),
            conflict_type="Time Conflict",
            schedule_id=sample_schedule.schedule_id
        )
        test_db.add(conflict)
        test_db.commit()
        test_db.refresh(conflict)
        
        assert conflict.student_id == sample_student.student_id
        assert json.loads(conflict.exam_assignment_ids) == assignment_ids
        assert conflict.conflict_type == "Time Conflict"
        assert conflict.schedule_id == sample_schedule.schedule_id
        assert isinstance(conflict.conflict_id, str)
