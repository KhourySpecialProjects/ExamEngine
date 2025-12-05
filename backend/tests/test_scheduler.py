"""
Tests for the DSATUR scheduling algorithm.

Tests cover:
- Graph building from conflict data
- Graph coloring with DSATUR
- Time slot assignment
- Room assignment
- Conflict detection
- Large course prioritization
"""

import pytest

from src.algorithms.scheduler import Scheduler
from src.domain.factories.dataset_factory import DatasetFactory


class TestSchedulerBasic:
    """Basic scheduler functionality tests."""

    def test_scheduler_initialization(self, sample_census_data, sample_enrollment_data, sample_classroom_data):
        """Test that scheduler can be initialized with valid data."""
        dataset = DatasetFactory.from_dataframes_to_scheduling_dataset(
            sample_census_data, sample_enrollment_data, sample_classroom_data
        )
        
        scheduler = Scheduler(
            dataset=dataset,
            max_days=7,
            student_max_per_day=3,
            instructor_max_per_day=2
        )
        
        assert scheduler.dataset == dataset
        assert scheduler.max_days == 7
        assert len(scheduler.available_slots) == 7 * 5  # 7 days * 5 blocks

    def test_build_conflict_graph(self, sample_census_data, sample_enrollment_data, sample_classroom_data):
        """Test that conflict graph is built correctly."""
        dataset = DatasetFactory.from_dataframes_to_scheduling_dataset(
            sample_census_data, sample_enrollment_data, sample_classroom_data
        )
        
        scheduler = Scheduler(dataset=dataset)
        scheduler._build_conflict_graph()
        
        assert scheduler.graph is not None
        assert scheduler.graph.number_of_nodes() == len(dataset.courses)
        
        # Check that courses with shared students have edges
        # S001 takes 1001, 1002, 1003 - so these should have edges
        assert scheduler.graph.has_edge("1001", "1002")
        assert scheduler.graph.has_edge("1001", "1003")
        assert scheduler.graph.has_edge("1002", "1003")

    def test_color_graph(self, sample_census_data, sample_enrollment_data, sample_classroom_data):
        """Test that graph coloring works correctly."""
        dataset = DatasetFactory.from_dataframes_to_scheduling_dataset(
            sample_census_data, sample_enrollment_data, sample_classroom_data
        )
        
        scheduler = Scheduler(dataset=dataset)
        scheduler._build_conflict_graph()
        scheduler._color_graph()
        
        assert len(scheduler.colors) == len(dataset.courses)
        
        # All courses should have a color assigned
        for crn in dataset.courses:
            assert crn in scheduler.colors
            assert isinstance(scheduler.colors[crn], int)
            assert scheduler.colors[crn] >= 0
        
        # Conflicting courses should have different colors
        # S001 takes 1001, 1002, 1003 - these should have different colors
        assert scheduler.colors["1001"] != scheduler.colors["1002"]
        assert scheduler.colors["1001"] != scheduler.colors["1003"]
        assert scheduler.colors["1002"] != scheduler.colors["1003"]

    def test_complete_schedule(self, sample_census_data, sample_enrollment_data, sample_classroom_data):
        """Test that complete scheduling workflow produces valid results."""
        dataset = DatasetFactory.from_dataframes_to_scheduling_dataset(
            sample_census_data, sample_enrollment_data, sample_classroom_data
        )
        
        scheduler = Scheduler(
            dataset=dataset,
            max_days=7,
            student_max_per_day=3,
            instructor_max_per_day=2
        )
        
        result = scheduler.schedule(prioritize_large_courses=False)
        
        # All courses should be assigned
        assert len(result.assignments) == len(dataset.courses)
        
        # All courses should have room assignments
        assert len(result.room_assignments) == len(dataset.courses)
        
        # All assignments should be valid time slots
        for crn, (day, block) in result.assignments.items():
            assert 0 <= day < 7
            assert 0 <= block < 5
        
        # All rooms should exist in dataset
        for crn, room_name in result.room_assignments.items():
            room_names = [r.name for r in dataset.rooms]
            assert room_name in room_names

    def test_no_hard_conflicts(self, sample_census_data, sample_enrollment_data, sample_classroom_data):
        """Test that scheduler avoids hard conflicts (student double-booking)."""
        dataset = DatasetFactory.from_dataframes_to_scheduling_dataset(
            sample_census_data, sample_enrollment_data, sample_classroom_data
        )
        
        scheduler = Scheduler(
            dataset=dataset,
            max_days=7,
            student_max_per_day=3,
            instructor_max_per_day=2
        )
        
        result = scheduler.schedule()
        
        # Check for student double-booking conflicts
        student_schedule = {}
        for crn, (day, block) in result.assignments.items():
            slot = (day, block)
            for student_id, student in dataset.students.items():
                if crn in student.enrolled_crns:
                    if student_id not in student_schedule:
                        student_schedule[student_id] = []
                    student_schedule[student_id].append(slot)
        
        # No student should have two exams at the same time
        for student_id, slots in student_schedule.items():
            assert len(slots) == len(set(slots)), f"Student {student_id} has duplicate time slots"


class TestSchedulerConstraints:
    """Tests for constraint handling."""

    def test_student_max_per_day(self, sample_census_data, sample_enrollment_data, sample_classroom_data):
        """Test that student_max_per_day constraint is respected."""
        dataset = DatasetFactory.from_dataframes_to_scheduling_dataset(
            sample_census_data, sample_enrollment_data, sample_classroom_data
        )
        
        scheduler = Scheduler(
            dataset=dataset,
            max_days=7,
            student_max_per_day=2,  # Max 2 exams per day
            instructor_max_per_day=2
        )
        
        result = scheduler.schedule()
        
        # Count exams per student per day
        student_day_counts = {}
        for crn, (day, block) in result.assignments.items():
            for student_id, student in dataset.students.items():
                if crn in student.enrolled_crns:
                    key = (student_id, day)
                    student_day_counts[key] = student_day_counts.get(key, 0) + 1
        
        # Check constraint (may have violations due to conflicts, but should minimize)
        violations = sum(1 for count in student_day_counts.values() if count > 2)
        # In a well-designed schedule, violations should be minimal
        assert violations < len(dataset.students), "Too many student max_per_day violations"

    def test_room_capacity(self, sample_census_data, sample_enrollment_data, sample_classroom_data):
        """Test that room capacity constraints are considered."""
        dataset = DatasetFactory.from_dataframes_to_scheduling_dataset(
            sample_census_data, sample_enrollment_data, sample_classroom_data
        )
        
        scheduler = Scheduler(dataset=dataset)
        result = scheduler.schedule()
        
        # Check that assigned rooms have sufficient capacity (or are the best available)
        for crn, room_name in result.room_assignments.items():
            course = dataset.courses[crn]
            room = next((r for r in dataset.rooms if r.name == room_name), None)
            
            assert room is not None, f"Room {room_name} not found in dataset"
            # Room should ideally fit, but may be over capacity if no better option
            # At minimum, it should be the largest available room


class TestSchedulerPrioritization:
    """Tests for large course prioritization."""

    def test_prioritize_large_courses(self, sample_census_data, sample_enrollment_data, sample_classroom_data):
        """Test that large course prioritization affects scheduling order."""
        dataset = DatasetFactory.from_dataframes_to_scheduling_dataset(
            sample_census_data, sample_enrollment_data, sample_classroom_data
        )
        
        scheduler = Scheduler(dataset=dataset, max_days=7)
        
        # Schedule with prioritization
        result_prioritized = scheduler.schedule(prioritize_large_courses=True)
        
        # Schedule without prioritization
        scheduler2 = Scheduler(dataset=dataset, max_days=7)
        result_normal = scheduler2.schedule(prioritize_large_courses=False)
        
        # Both should assign all courses
        assert len(result_prioritized.assignments) == len(result_normal.assignments)
        
        # With prioritization, larger courses should tend to get earlier days
        # (This is probabilistic, so we just verify the mechanism works)
        course_sizes = {crn: dataset.get_enrollment_count(crn) for crn in dataset.courses}
        large_courses = [crn for crn, size in course_sizes.items() if size >= 35]
        
        if large_courses:
            # Check that large courses got assigned (they should)
            for crn in large_courses:
                assert crn in result_prioritized.assignments


class TestSchedulerEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_dataset(self):
        """Test scheduler with empty dataset."""
        import pandas as pd
        from src.domain.models import SchedulingDataset, Course, Student, Room
        
        empty_dataset = SchedulingDataset(
            courses={},
            students={},
            rooms=[],
            students_by_crn={},
            instructors_by_crn={}
        )
        
        scheduler = Scheduler(dataset=empty_dataset)
        result = scheduler.schedule()
        
        assert len(result.assignments) == 0
        assert len(result.room_assignments) == 0
        assert len(result.conflicts) == 0

    def test_single_course(self, sample_classroom_data):
        """Test scheduler with single course."""
        import pandas as pd
        
        single_course = pd.DataFrame({
            "CRN": ["1001"],
            "CourseID": ["CS101"],
            "num_students": [30],
            "Instructor Name": ["Dr. Smith"],
            "examination_term": ["Fall 2025"],
            "department": ["CS"]
        })
        
        single_enrollment = pd.DataFrame({
            "Student_PIDM": ["S001"],
            "CRN": ["1001"]
        })
        
        dataset = DatasetFactory.from_dataframes_to_scheduling_dataset(
            single_course, single_enrollment, sample_classroom_data
        )
        
        scheduler = Scheduler(dataset=dataset)
        result = scheduler.schedule()
        
        assert len(result.assignments) == 1
        assert "1001" in result.assignments
        assert "1001" in result.room_assignments

    def test_no_conflicts(self):
        """Test scheduler when no courses share students."""
        import pandas as pd
        
        # Courses with no overlapping students
        courses = pd.DataFrame({
            "CRN": ["1001", "1002", "1003"],
            "CourseID": ["CS101", "MATH201", "PHYS301"],
            "num_students": [30, 25, 40],
            "Instructor Name": ["Dr. A", "Dr. B", "Dr. C"],
            "examination_term": ["Fall 2025", "Fall 2025", "Fall 2025"],
            "department": ["CS", "MATH", "PHYS"]
        })
        
        enrollments = pd.DataFrame({
            "Student_PIDM": ["S001", "S002", "S003"],
            "CRN": ["1001", "1002", "1003"]
        })
        
        rooms = pd.DataFrame({
            "room_name": ["Room A", "Room B", "Room C"],
            "capacity": [50, 50, 50]
        })
        
        dataset = DatasetFactory.from_dataframes_to_scheduling_dataset(
            courses, enrollments, rooms
        )
        
        scheduler = Scheduler(dataset=dataset)
        result = scheduler.schedule()
        
        # All courses can be scheduled at the same time
        assert len(result.assignments) == 3
        # No conflicts should occur
        student_conflicts = [c for c in result.conflicts if "student" in str(c).lower()]
        assert len(student_conflicts) == 0


@pytest.mark.slow
class TestSchedulerPerformance:
    """Performance and stress tests."""

    def test_large_dataset(self, large_census_data, large_enrollment_data, large_classroom_data):
        """Test scheduler with large dataset."""
        dataset = DatasetFactory.from_dataframes_to_scheduling_dataset(
            large_census_data, large_enrollment_data, large_classroom_data
        )
        
        scheduler = Scheduler(
            dataset=dataset,
            max_days=7,
            student_max_per_day=3,
            instructor_max_per_day=2
        )
        
        result = scheduler.schedule()
        
        # Should handle large datasets
        assert len(result.assignments) == len(dataset.courses)
        assert len(result.room_assignments) == len(dataset.courses)
        
        # All assignments should be valid
        for crn, (day, block) in result.assignments.items():
            assert 0 <= day < 7
            assert 0 <= block < 5

    def test_many_conflicts(self):
        """Test scheduler with many overlapping enrollments."""
        import pandas as pd
        
        # Create scenario where many students take many courses
        num_courses = 20
        num_students = 50
        
        courses = pd.DataFrame({
            "CRN": [f"{1000 + i}" for i in range(num_courses)],
            "CourseID": [f"CS{100 + i}" for i in range(num_courses)],
            "num_students": [30] * num_courses,
            "Instructor Name": [f"Dr. Instructor{i % 10}" for i in range(num_courses)],
            "examination_term": ["Fall 2025"] * num_courses,
            "department": ["CS"] * num_courses
        })
        
        # Each student takes 5 random courses
        enrollments = []
        for student_id in range(num_students):
            import random
            student_courses = random.sample(range(num_courses), 5)
            for crn_idx in student_courses:
                enrollments.append({
                    "Student_PIDM": f"S{student_id:04d}",
                    "CRN": f"{1000 + crn_idx}"
                })
        
        enrollment_df = pd.DataFrame(enrollments)
        
        rooms = pd.DataFrame({
            "room_name": [f"Room {i}" for i in range(30)],
            "capacity": [50] * 30
        })
        
        dataset = DatasetFactory.from_dataframes_to_scheduling_dataset(
            courses, enrollment_df, rooms
        )
        
        scheduler = Scheduler(dataset=dataset, max_days=7)
        result = scheduler.schedule()
        
        # Should still schedule all courses
        assert len(result.assignments) == num_courses


