from dataclasses import dataclass

from .hard_conflicts import HardConflicts
from .schedule_statistics import ScheduleStatistics
from .soft_conflicts import SoftConflicts


@dataclass
class ScheduleAnalysis:
    """Complete analysis of a schedule."""

    hard_conflicts: HardConflicts
    soft_conflicts: SoftConflicts
    statistics: ScheduleStatistics

    def to_dict(self) -> dict:
        return {
            "hard_conflicts": self.hard_conflicts.to_dict(),
            "soft_conflicts": self.soft_conflicts.to_dict(),
            "statistics": {
                "num_classes": self.statistics.num_classes,
                "num_students": self.statistics.num_students,
                "num_rooms": self.statistics.num_rooms,
                "slots_used": self.statistics.slots_used,
                "unplaced_exams": self.statistics.unplaced_exams,
                "total_hard_conflicts": self.statistics.total_hard_conflicts,
                "total_soft_conflicts": self.statistics.total_soft_conflicts,
                "student_double_book_count": len(
                    self.hard_conflicts.student_double_book
                ),
                "instructor_double_book_count": len(
                    self.hard_conflicts.instructor_double_book
                ),
                "student_gt_max_per_day_count": len(
                    self.hard_conflicts.student_gt_max_per_day
                ),
                "instructor_gt_max_per_day_count": len(
                    self.hard_conflicts.instructor_gt_max_per_day
                ),
                "back_to_back_students_count": len(
                    self.soft_conflicts.back_to_back_students
                ),
                "back_to_back_instructors_count": len(
                    self.soft_conflicts.back_to_back_instructors
                ),
                "large_courses_not_early_count": len(
                    self.soft_conflicts.large_courses_not_early
                ),
            },
        }
