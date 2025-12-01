from dataclasses import dataclass


@dataclass
class SoftPenalty:
    """
    Penalty scores for soft constraint evaluation.

    Used for lexicographic comparison when choosing time slots.
    Lower is better for each component.
    """

    large_course_late: int = 0  # Large courses prefer early week
    back_to_back_students: int = 0  # Students with consecutive blocks
    back_to_back_instructors: int = 0
    instructor_load: int = 0  # Instructor workload balancing
    slot_seat_load: int = 0  # Total students in slot
    slot_exam_count: int = 0  # Number of exams in slot

    def as_tuple(self, day: int, block: int) -> tuple:
        """Return tuple for lexicographic comparison."""
        return (
            self.large_course_late,
            self.back_to_back_students,
            self.back_to_back_instructors,
            self.instructor_load,
            self.slot_seat_load,
            self.slot_exam_count,
            day,  # Tie-breaker
            block,
        )
