from dataclasses import dataclass


@dataclass(frozen=True)
class SchedulingConfig:
    """Immutable scheduling parameters."""

    blocks_per_day: int = 5
    max_days: int = 7
    large_course_threshold: int = 100
    early_week_cutoff: int = 3  # Wednesday
    student_max_per_day: int = 2
    instructor_max_per_day: int = 2
