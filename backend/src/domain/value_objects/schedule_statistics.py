from dataclasses import dataclass


@dataclass
class ScheduleStatistics:
    """Summary statistics for a schedule."""

    num_classes: int = 0
    num_students: int = 0
    num_rooms: int = 0
    slots_used: int = 0
    unplaced_exams: int = 0
    total_hard_conflicts: int = 0
    total_soft_conflicts: int = 0
