from dataclasses import dataclass, field


@dataclass(frozen=True)
class Course:
    """
    Canonical representation of a course section.

    This is what the rest of the application works with internally.
    All CSV formats are converted to this structure.
    """

    crn: str  # Course Registration Number (unique identifier)
    course_code: str  # e.g., "CS 4535"
    enrollment_count: int  # Number of students enrolled
    instructor_names: set[str] = field(
        default_factory=set
    )  # May be multiple instructors

    def __post_init__(self):
        """Validate data after initialization."""
        if not self.crn or not self.crn.strip():
            raise ValueError("CRN cannot be empty")
        if self.enrollment_count < 0:
            raise ValueError("Enrollment count cannot be negative")
        # Ensure instructor_names is a set (immutable due to frozen=True)
        if not isinstance(self.instructor_names, set):
            object.__setattr__(self, "instructor_names", set(self.instructor_names))
