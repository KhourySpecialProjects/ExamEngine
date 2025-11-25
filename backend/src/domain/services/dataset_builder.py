from collections import defaultdict

import pandas as pd

from src.domain.adapters import CourseAdapter, EnrollmentAdapter, RoomAdapter
from src.domain.models import Course, Enrollment, SchedulingDataset, Student


class DatasetBuilder:
    """
    Builds SchedulingDataset from raw DataFrames.

    This is the ONE place where DataFrames enter the domain layer.
    Uses the existing adapters and schema detection.
    """

    @staticmethod
    def from_dataframes(
        courses_df: pd.DataFrame,
        enrollment_df: pd.DataFrame,
        rooms_df: pd.DataFrame,
    ) -> SchedulingDataset:
        """
        Convert raw CSVs to a complete SchedulingDataset.

        All column name variations, data cleaning, and validation
        happen here through the adapter layer.
        """
        # Use existing adapters—they handle schema detection
        courses = CourseAdapter.from_dataframe(courses_df)
        enrollments = EnrollmentAdapter.from_dataframe(enrollment_df)
        rooms = RoomAdapter.from_dataframe(rooms_df)

        # Build student objects and relationship lookups
        students, students_by_crn, instructors_by_crn = (
            DatasetBuilder._build_relationships(courses, enrollments)
        )

        return SchedulingDataset(
            courses=courses,
            students=students,
            rooms=rooms,
            students_by_crn=students_by_crn,
            instructors_by_crn=instructors_by_crn,
        )

    @staticmethod
    def _build_relationships(
        courses: dict[str, Course],
        enrollments: list[Enrollment],
    ) -> tuple[
        dict[str, Student], dict[str, frozenset[str]], dict[str, frozenset[str]]
    ]:
        """
        Build bidirectional relationship lookups from enrollment records.
        """
        # Aggregate by student
        student_courses: dict[str, set[str]] = defaultdict(set)
        crn_students: dict[str, set[str]] = defaultdict(set)
        crn_instructors: dict[str, set[str]] = defaultdict(set)

        valid_crns = set(courses.keys())

        for enrollment in enrollments:
            # Skip enrollments for courses not in census
            if enrollment.crn not in valid_crns:
                continue

            student_courses[enrollment.student_id].add(enrollment.crn)
            crn_students[enrollment.crn].add(enrollment.student_id)

            if enrollment.instructor_name:
                crn_instructors[enrollment.crn].add(enrollment.instructor_name)

        # Build Student domain objects
        students = {
            sid: Student(student_id=sid, enrolled_crns=frozenset(crns))
            for sid, crns in student_courses.items()
        }

        # Convert to frozensets for immutability
        students_by_crn = {crn: frozenset(sids) for crn, sids in crn_students.items()}
        instructors_by_crn = {
            crn: frozenset(names) for crn, names in crn_instructors.items()
        }

        return students, students_by_crn, instructors_by_crn
