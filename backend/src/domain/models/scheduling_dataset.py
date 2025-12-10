from dataclasses import dataclass

from .course import Course
from .room import Room
from .student import Student


@dataclass(frozen=True)
class SchedulingDataset:
    """
    Complete input for a scheduling problem.

    This is what the algorithm operates on—pure domain objects,
    no DataFrame knowledge, no CSV column awareness.
    """

    courses: dict[str, Course]  # CRN → Course
    students: dict[str, Student]  # student_id → Student
    rooms: list[Room]

    # Pre-computed relationships for algorithm efficiency
    students_by_crn: dict[str, frozenset[str]]  # CRN → {student_ids}
    instructors_by_crn: dict[str, frozenset[str]]  # CRN → {instructor_names}

    def get_course(self, crn: str) -> Course | None:
        return self.courses.get(crn)

    def get_enrollment_count(self, crn: str) -> int:
        """Helper for algorithm to get course size without knowing Course internals."""
        course = self.courses.get(crn)
        return course.enrollment_count if course else 0

    def get_shared_students(self, crn1: str, crn2: str) -> frozenset[str]:
        """Find students enrolled in both courses (for conflict graph edges)."""
        s1 = self.students_by_crn.get(crn1, frozenset())
        s2 = self.students_by_crn.get(crn2, frozenset())
        return s1 & s2
