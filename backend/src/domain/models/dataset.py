from dataclasses import dataclass
from uuid import UUID

from .course import Course
from .room import Room
from .student import Student


@dataclass
class Dataset:
    """
    Complete dataset for exam scheduling.

    This aggregates all the data needed for scheduling in one place.
    """

    dataset_id: UUID
    name: str
    courses: dict[str, Course]  # Keyed by CRN
    students: dict[str, Student]  # Keyed by student_id
    rooms: list[Room]

    def get_course(self, crn: str) -> Course | None:
        """Safely retrieve a course by CRN."""
        return self.courses.get(crn)

    def get_student(self, student_id: str) -> Student | None:
        """Safely retrieve a student by ID."""
        return self.students.get(student_id)

    def validate(self) -> list[str]:
        """
        Validate dataset integrity and return list of warnings/errors.

        Returns empty list if dataset is valid.
        """
        issues = []

        # Check for courses with no students
        empty_courses = [
            crn for crn, course in self.courses.items() if course.enrollment_count == 0
        ]
        if empty_courses:
            issues.append(f"Found {len(empty_courses)} courses with zero enrollment")

        # Check for students enrolled in non-existent courses
        all_crns = set(self.courses.keys())
        for student in self.students.values():
            invalid_crns = student.enrolled_crns - all_crns
            if invalid_crns:
                issues.append(
                    f"Student {student.student_id} enrolled in non-existent "
                    f"courses: {invalid_crns}"
                )

        # Check for insufficient room capacity
        max_course_size = max(
            (c.enrollment_count for c in self.courses.values()), default=0
        )
        max_room_capacity = max((r.capacity for r in self.rooms), default=0)
        if max_course_size > max_room_capacity:
            issues.append(
                f"Largest course ({max_course_size} students) exceeds "
                f"largest room capacity ({max_room_capacity})"
            )

        return issues
