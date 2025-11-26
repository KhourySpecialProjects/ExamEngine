from dataclasses import dataclass


@dataclass(frozen=True)
class Enrollment:
    """
    Represents a single student-course enrollment record.

    This is extracted from enrollment CSV and used to build
    both Student and Course objects with full relationships.
    """

    student_id: str
    crn: str
    instructor_name: str | None = None

    def __post_init__(self):
        """Validate data."""
        if not self.student_id or not self.student_id.strip():
            raise ValueError("Student ID cannot be empty")
        if not self.crn or not self.crn.strip():
            raise ValueError("CRN cannot be empty")
