from dataclasses import dataclass, field


@dataclass(frozen=True)
class Student:
    """Canonical representation of a student."""

    student_id: str
    enrolled_crns: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self):
        """Validate and normalize data."""
        if not self.student_id or not self.student_id.strip():
            raise ValueError("Student ID cannot be empty")
        if not isinstance(self.enrolled_crns, frozenset):
            object.__setattr__(self, "enrolled_crns", frozenset(self.enrolled_crns))
