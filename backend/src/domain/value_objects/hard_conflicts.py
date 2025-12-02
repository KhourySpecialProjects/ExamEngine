from dataclasses import dataclass, field


@dataclass
class HardConflicts:
    """Hard constraint violations detected during scheduling."""

    student_double_book: list[dict] = field(default_factory=list)
    instructor_double_book: list[dict] = field(default_factory=list)
    student_gt_max_per_day: list[dict] = field(default_factory=list)
    instructor_gt_max_per_day: list[dict] = field(default_factory=list)

    @property
    def total_count(self) -> int:
        return (
            len(self.student_double_book)
            + len(self.instructor_double_book)
            + len(self.student_gt_max_per_day)
            + len(self.instructor_gt_max_per_day)
        )

    def to_dict(self) -> dict:
        return {
            "student_double_book": self.student_double_book,
            "instructor_double_book": self.instructor_double_book,
            "student_gt_max_per_day": self.student_gt_max_per_day,
            "instructor_gt_max_per_day": self.instructor_gt_max_per_day,
        }
