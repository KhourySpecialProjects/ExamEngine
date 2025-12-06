from dataclasses import dataclass, field

from .room import Room
from .time_slot import TimeSlot


@dataclass(frozen=True)
class ExamAssignment:
    """
    Represents a scheduled exam with all details.

    This is the output of the scheduling algorithm.
    """

    crn: str
    course_code: str
    time_slot: TimeSlot
    room: Room
    enrollment_count: int
    instructor_names: set[str] = field(default_factory=set)
    is_valid: bool = True  # False if there are conflicts

    def __post_init__(self):
        """Validate and normalize data."""
        if not self.crn or not self.crn.strip():
            raise ValueError("CRN cannot be empty")
        if not isinstance(self.instructor_names, set):
            object.__setattr__(self, "instructor_names", set(self.instructor_names))
