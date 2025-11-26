from collections import defaultdict
from typing import Any

import pandas as pd

from src.domain.adapters import CourseAdapter, EnrollmentAdapter, RoomAdapter
from src.domain.models import Course, Dataset, Enrollment, SchedulingDataset, Student


class DatasetFactory:
    """
    Builds SchedulingDataset from raw DataFrames.

    This is the ONE place where DataFrames enter the domain layer.
    Uses the existing adapters and schema detection.
    """

    @staticmethod
    def from_dataframes_to_scheduling_dataset(
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
            DatasetFactory._build_relationships(courses, enrollments)
        )

        return SchedulingDataset(
            courses=courses,
            students=students,
            rooms=rooms,
            students_by_crn=students_by_crn,
            instructors_by_crn=instructors_by_crn,
        )

    @staticmethod
    def from_dataframes_to_dataset(
        dataset_id: Any,
        dataset_name: str,
        course_df: pd.DataFrame,
        enrollment_df: pd.DataFrame,
        room_df: pd.DataFrame,
    ) -> Dataset:
        """
        Build a complete Dataset from three CSV DataFrames.

        Args:
            dataset_id: UUID for the dataset
            dataset_name: Human-readable name
            course_df: Course CSV data
            enrollment_df: Enrollment CSV data
            room_df: Room CSV data

        Returns:
            Complete Dataset object with all relationships populated
        """
        # Convert each CSV to domain objects
        courses = CourseAdapter.from_dataframe(course_df)
        enrollments = EnrollmentAdapter.from_dataframe(enrollment_df)
        rooms = RoomAdapter.from_dataframe(room_df)

        # Build student objects from enrollments
        student_enrollments = defaultdict(set)
        course_instructors = defaultdict(set)

        for enrollment in enrollments:
            student_enrollments[enrollment.student_id].add(enrollment.crn)
            if enrollment.instructor_name:
                course_instructors[enrollment.crn].add(enrollment.instructor_name)

        students = {
            student_id: Student(student_id=student_id, enrolled_crns=frozenset(crns))
            for student_id, crns in student_enrollments.items()
        }

        # Enrich courses with instructor information
        enriched_courses = {}
        for crn, course in courses.items():
            enriched_courses[crn] = Course(
                crn=course.crn,
                course_code=course.course_code,
                enrollment_count=course.enrollment_count,
                instructor_names=course_instructors.get(crn, set()),
            )

        # Build final dataset
        return Dataset(
            dataset_id=dataset_id,
            name=dataset_name,
            courses=enriched_courses,
            students=students,
            rooms=rooms,
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
