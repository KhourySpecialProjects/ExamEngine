from dataclasses import dataclass, field


@dataclass
class SoftConflicts:
    """Soft constraint violations detected in a schedule."""

    back_to_back_students: list[dict] = field(default_factory=list)
    back_to_back_instructors: list[dict] = field(default_factory=list)
    large_courses_not_early: list[dict] = field(default_factory=list)

    @property
    def total_count(self) -> int:
        return (
            len(self.back_to_back_students)
            + len(self.back_to_back_instructors)
            + len(self.large_courses_not_early)
        )

    def to_dict(self) -> dict:
        return {
            "back_to_back_students": self.back_to_back_students,
            "back_to_back_instructors": self.back_to_back_instructors,
            "large_courses_not_early": self.large_courses_not_early,
        }
