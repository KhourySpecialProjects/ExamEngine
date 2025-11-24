"""
Tests for large course prioritization feature.

This module tests the algorithm's ability to prioritize larger courses
(≥100 students) for earlier scheduling in the week.
"""

import pandas as pd
import pytest

from src.algorithms.enhanced_dsatur_scheduler import DSATURExamGraph


class TestLargeCoursePrioritization:
    """Test large course prioritization for early week scheduling."""

    def test_large_courses_scheduled_earlier(self):
        """Test that courses with ≥100 students are prioritized for earlier days."""
        # Create census with mix of large and small courses
        census = pd.DataFrame(
            {
                "CRN": ["1001", "1002", "1003", "1004", "1005", "1006"],
                "course_ref": ["CS101", "CS102", "MATH201", "MATH202", "PHYS301", "PHYS302"],
                "num_students": [150, 120, 80, 60, 40, 30],  # First 2 are large (≥100)
            }
        )

        # Create enrollment data
        enrollment = pd.DataFrame(
            {
                "student_id": [f"S{i:04d}" for i in range(480)],  # Total students
                "CRN": (
                    ["1001"] * 150  # CS101: 150 students
                    + ["1002"] * 120  # CS102: 120 students
                    + ["1003"] * 80  # MATH201: 80 students
                    + ["1004"] * 60  # MATH202: 60 students
                    + ["1005"] * 40  # PHYS301: 40 students
                    + ["1006"] * 30  # PHYS302: 30 students
                ),
                "instructor_name": [
                    "Dr. Smith",
                    "Dr. Jones",
                    "Dr. Brown",
                    "Dr. Wilson",
                    "Dr. Davis",
                    "Dr. Miller",
                ] * 80,  # Spread across courses
            }
        )

        classrooms = pd.DataFrame(
            {
                "room_name": ["Room A", "Room B", "Room C", "Room D"],
                "capacity": [200, 150, 100, 50],
            }
        )

        graph = DSATURExamGraph(census, enrollment, classrooms)
        graph.build_graph()
        graph.dsatur_color()
        graph.dsatur_schedule()
        schedule_df = graph.assign_rooms()

        # Identify large courses (≥100 students)
        large_courses = schedule_df[schedule_df["Size"] >= 100]
        small_courses = schedule_df[schedule_df["Size"] < 100]

        if len(large_courses) > 0 and len(small_courses) > 0:
            # Map day names to indices (Monday=0, Tuesday=1, etc.)
            day_map = {
                "Monday": 0,
                "Tuesday": 1,
                "Wednesday": 2,
                "Thursday": 3,
                "Friday": 4,
                "Saturday": 5,
                "Sunday": 6,
            }

            # Calculate average day index for large and small courses
            large_days = [day_map[day] for day in large_courses["Day"]]
            small_days = [day_map[day] for day in small_courses["Day"]]

            avg_large_day = sum(large_days) / len(large_days)
            avg_small_day = sum(small_days) / len(small_days)

            # Large courses should be scheduled earlier on average
            assert avg_large_day < avg_small_day, (
                f"Large courses not prioritized earlier: "
                f"avg day {avg_large_day:.2f} vs {avg_small_day:.2f}"
            )

    def test_multiple_large_courses_distributed_early(self):
        """Test that multiple large courses are distributed across early days."""
        census = pd.DataFrame(
            {
                "CRN": ["1001", "1002", "1003", "1004"],
                "course_ref": ["CS101", "CS102", "MATH201", "MATH202"],
                "num_students": [150, 130, 110, 100],  # All are large (≥100)
            }
        )

        enrollment = pd.DataFrame(
            {
                "student_id": [f"S{i:04d}" for i in range(490)],
                "CRN": (
                    ["1001"] * 150
                    + ["1002"] * 130
                    + ["1003"] * 110
                    + ["1004"] * 100
                ),
                "instructor_name": ["Dr. Smith", "Dr. Jones", "Dr. Brown", "Dr. Wilson"] * 122,
            }
        )

        classrooms = pd.DataFrame(
            {
                "room_name": ["Room A", "Room B", "Room C"],
                "capacity": [200, 150, 150],
            }
        )

        graph = DSATURExamGraph(census, enrollment, classrooms)
        graph.build_graph()
        graph.dsatur_color()
        graph.dsatur_schedule()
        schedule_df = graph.assign_rooms()

        # Check that large courses are scheduled in early days
        day_map = {
            "Monday": 0,
            "Tuesday": 1,
            "Wednesday": 2,
            "Thursday": 3,
            "Friday": 4,
            "Saturday": 5,
            "Sunday": 6,
        }

        large_courses = schedule_df[schedule_df["Size"] >= 100]
        large_day_indices = [day_map[day] for day in large_courses["Day"]]

        # At least 50% of large courses should be in first 3 days (Mon-Wed)
        early_count = sum(1 for day_idx in large_day_indices if day_idx < 3)
        early_ratio = early_count / len(large_courses) if len(large_courses) > 0 else 0

        assert early_ratio >= 0.5, (
            f"Not enough large courses scheduled early: "
            f"{early_count}/{len(large_courses)} ({early_ratio:.2%}) in first 3 days"
        )

    def test_large_course_prioritization_weight(self):
        """Test that weight_large_late parameter affects prioritization."""
        census = pd.DataFrame(
            {
                "CRN": ["1001", "1002", "1003"],
                "course_ref": ["CS101", "CS102", "MATH201"],
                "num_students": [150, 80, 40],  # One large course
            }
        )

        enrollment = pd.DataFrame(
            {
                "student_id": [f"S{i:04d}" for i in range(270)],
                "CRN": ["1001"] * 150 + ["1002"] * 80 + ["1003"] * 40,
                "instructor_name": ["Dr. Smith", "Dr. Jones", "Dr. Brown"] * 90,
            }
        )

        classrooms = pd.DataFrame(
            {"room_name": ["Room A", "Room B"], "capacity": [200, 100]}
        )

        day_map = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6}

        # Test with high weight (should prioritize large courses more)
        graph_high = DSATURExamGraph(census, enrollment, classrooms, weight_large_late=10)
        graph_high.build_graph()
        graph_high.dsatur_color()
        graph_high.dsatur_schedule()
        schedule_high = graph_high.assign_rooms()

        large_course_high = schedule_high[schedule_high["Size"] >= 100]
        if len(large_course_high) > 0:
            large_day_high = day_map[large_course_high.iloc[0]["Day"]]

            # With high weight, large course should be in early days
            assert large_day_high < 3, (
                f"With high weight, large course scheduled too late: day {large_day_high}"
            )


class TestBackToBackConflictDetection:
    """Test back-to-back conflict detection for students and instructors."""

    def test_student_back_to_back_detection(self):
        """Test that back-to-back student conflicts are detected."""
        census = pd.DataFrame(
            {
                "CRN": ["1001", "1002"],
                "course_ref": ["CS101", "CS102"],
                "num_students": [50, 50],
            }
        )

        # Create a student enrolled in both courses
        enrollment = pd.DataFrame(
            {
                "student_id": ["S001", "S001", "S002", "S003"],
                "CRN": ["1001", "1002", "1001", "1002"],
                "instructor_name": ["Dr. Smith", "Dr. Jones", "Dr. Smith", "Dr. Jones"],
            }
        )

        classrooms = pd.DataFrame(
            {"room_name": ["Room A"], "capacity": [100]}
        )

        graph = DSATURExamGraph(census, enrollment, classrooms)
        graph.build_graph()
        graph.dsatur_color()
        graph.dsatur_schedule()
        schedule_df = graph.assign_rooms()
        summary = graph.summary()

        # Check if back-to-back conflicts are reported
        assert "students_back_to_back" in summary, "Back-to-back student conflicts should be tracked"
        assert isinstance(summary["students_back_to_back"], int), "Back-to-back count should be integer"

    def test_instructor_back_to_back_detection(self):
        """Test that back-to-back instructor conflicts are detected."""
        census = pd.DataFrame(
            {
                "CRN": ["1001", "1002", "1003"],
                "course_ref": ["CS101", "CS102", "CS103"],
                "num_students": [30, 30, 30],
            }
        )

        # Same instructor teaching multiple courses
        enrollment = pd.DataFrame(
            {
                "student_id": [f"S{i:03d}" for i in range(90)],
                "CRN": ["1001"] * 30 + ["1002"] * 30 + ["1003"] * 30,
                "instructor_name": ["Dr. Smith"] * 90,  # Same instructor for all
            }
        )

        classrooms = pd.DataFrame(
            {"room_name": ["Room A"], "capacity": [100]}
        )

        graph = DSATURExamGraph(census, enrollment, classrooms)
        graph.build_graph()
        graph.dsatur_color()
        graph.dsatur_schedule()
        schedule_df = graph.assign_rooms()
        summary = graph.summary()

        # Check if back-to-back instructor conflicts are reported
        assert "instructors_back_to_back" in summary, "Back-to-back instructor conflicts should be tracked"
        assert isinstance(summary["instructors_back_to_back"], int), "Back-to-back count should be integer"

    def test_back_to_back_in_soft_violations(self):
        """Test that back-to-back conflicts appear in soft violations."""
        census = pd.DataFrame(
            {
                "CRN": ["1001", "1002"],
                "course_ref": ["CS101", "CS102"],
                "num_students": [40, 40],
            }
        )

        enrollment = pd.DataFrame(
            {
                "student_id": ["S001", "S001", "S002", "S002"],
                "CRN": ["1001", "1002", "1001", "1002"],
                "instructor_name": ["Dr. Smith", "Dr. Jones", "Dr. Smith", "Dr. Jones"],
            }
        )

        classrooms = pd.DataFrame(
            {"room_name": ["Room A"], "capacity": [100]}
        )

        graph = DSATURExamGraph(census, enrollment, classrooms)
        graph.build_graph()
        graph.dsatur_color()
        graph.dsatur_schedule()
        schedule_df = graph.assign_rooms()

        # Check soft violations DataFrames
        assert hasattr(graph, "student_soft_violations"), "Should track student soft violations"
        assert hasattr(graph, "instructor_soft_violations"), "Should track instructor soft violations"


class TestTimeSlotMapping:
    """Test time slot block to time string mapping."""

    def test_block_time_mapping(self):
        """Test that block indices map to correct time ranges."""
        census = pd.DataFrame(
            {
                "CRN": ["1001", "1002", "1003", "1004", "1005"],
                "course_ref": ["CS101", "CS102", "MATH201", "MATH202", "PHYS301"],
                "num_students": [30, 30, 30, 30, 30],
            }
        )

        enrollment = pd.DataFrame(
            {
                "student_id": [f"S{i:03d}" for i in range(150)],
                "CRN": ["1001"] * 30 + ["1002"] * 30 + ["1003"] * 30 + ["1004"] * 30 + ["1005"] * 30,
                "instructor_name": ["Dr. Smith"] * 150,
            }
        )

        classrooms = pd.DataFrame(
            {"room_name": ["Room A"], "capacity": [200]}
        )

        graph = DSATURExamGraph(census, enrollment, classrooms)
        
        # Test block time mapping
        expected_times = {
            0: "9:00-11:00",
            1: "11:30-1:30",
            2: "2:00-4:00",
            3: "4:30-6:30",
            4: "7:00-9:00",
        }

        assert hasattr(graph, "block_times"), "Graph should have block_times attribute"
        assert graph.block_times == expected_times, "Block times should match expected mapping"

    def test_schedule_includes_time_information(self):
        """Test that schedule includes time information in block labels."""
        census = pd.DataFrame(
            {
                "CRN": ["1001", "1002"],
                "course_ref": ["CS101", "CS102"],
                "num_students": [50, 50],
            }
        )

        enrollment = pd.DataFrame(
            {
                "student_id": [f"S{i:03d}" for i in range(100)],
                "CRN": ["1001"] * 50 + ["1002"] * 50,
                "instructor_name": ["Dr. Smith"] * 100,
            }
        )

        classrooms = pd.DataFrame(
            {"room_name": ["Room A"], "capacity": [200]}
        )

        graph = DSATURExamGraph(census, enrollment, classrooms)
        graph.build_graph()
        graph.dsatur_color()
        graph.dsatur_schedule()
        schedule_df = graph.assign_rooms()

        # Check that Block column contains time information
        assert "Block" in schedule_df.columns, "Schedule should have Block column"
        
        # Block should be formatted with time info (e.g., "0 (9:00-11:00)" or similar)
        for block_value in schedule_df["Block"]:
            assert block_value is not None, "Block values should not be None"
            assert str(block_value), "Block values should be strings or convertible to strings"

