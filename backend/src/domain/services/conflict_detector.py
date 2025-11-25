from collections import defaultdict
from dataclasses import dataclass

from src.domain.models import SchedulingDataset


@dataclass(frozen=True)
class Conflict:
    """Represents a detected scheduling conflict."""

    conflict_type: str
    entity_id: str
    crn: str
    conflicting_crn: str | None
    day: int
    block: int


class ConflictDetector:
    """
    Detects hard constraint violations in exam scheduling.

    CRITICAL: This class maintains INCREMENTAL STATE that must be updated
    via record_placement() after each scheduling decision.
    """

    def __init__(
        self,
        dataset: SchedulingDataset,
        student_max_per_day: int = 2,
        instructor_max_per_day: int = 2,
    ):
        self.dataset = dataset
        self.student_max_per_day = student_max_per_day
        self.instructor_max_per_day = instructor_max_per_day

        # INCREMENTAL STATE - these get updated by record_placement()
        self.student_schedule: dict[str, list[tuple[int, int]]] = defaultdict(list)
        self.instructor_schedule: dict[str, list[tuple[int, int]]] = defaultdict(list)
        self.slot_to_crns: dict[tuple[int, int], list[str]] = defaultdict(list)

    def check_placement(self, crn: str, day: int, block: int) -> list[Conflict]:
        """
        Check conflicts for placing CRN at (day, block).

        """
        conflicts = []

        students = self.dataset.students_by_crn.get(crn, frozenset())
        instructors = self.dataset.instructors_by_crn.get(crn, frozenset())

        # Check student conflicts
        for student_id in students:
            student_slots = self.student_schedule[student_id]

            # Double-booking
            if (day, block) in student_slots:
                conflicting = self._find_conflicting_crn(
                    student_id, day, block, "student"
                )
                conflicts.append(
                    Conflict(
                        conflict_type="student_double_book",
                        entity_id=student_id,
                        crn=crn,
                        conflicting_crn=conflicting,
                        day=day,
                        block=block,
                    )
                )

            # Max per day
            day_count = sum(1 for d, _ in student_slots if d == day)
            if day_count >= self.student_max_per_day:
                conflicts.append(
                    Conflict(
                        conflict_type="student_gt_max_per_day",
                        entity_id=student_id,
                        crn=crn,
                        conflicting_crn=None,
                        day=day,
                        block=block,
                    )
                )

        # Check instructor conflicts
        for instructor in instructors:
            instr_slots = self.instructor_schedule[instructor]

            if (day, block) in instr_slots:
                conflicting = self._find_conflicting_crn(
                    instructor, day, block, "instructor"
                )
                conflicts.append(
                    Conflict(
                        conflict_type="instructor_double_book",
                        entity_id=instructor,
                        crn=crn,
                        conflicting_crn=conflicting,
                        day=day,
                        block=block,
                    )
                )

            day_count = sum(1 for d, _ in instr_slots if d == day)
            if day_count >= self.instructor_max_per_day:
                conflicts.append(
                    Conflict(
                        conflict_type="instructor_gt_max_per_day",
                        entity_id=instructor,
                        crn=crn,
                        conflicting_crn=None,
                        day=day,
                        block=block,
                    )
                )

        return conflicts

    def record_placement(self, crn: str, day: int, block: int):
        """
        Record that CRN was placed at (day, block).

        MUST be called after each placement to keep state synchronized.
        This is what makes the algorithm O(n) instead of O(n²).
        """
        slot = (day, block)

        for student_id in self.dataset.students_by_crn.get(crn, frozenset()):
            self.student_schedule[student_id].append(slot)

        for instructor in self.dataset.instructors_by_crn.get(crn, frozenset()):
            self.instructor_schedule[instructor].append(slot)

        self.slot_to_crns[slot].append(crn)

    def _find_conflicting_crn(
        self, entity_id: str, day: int, block: int, entity_type: str
    ) -> str | None:
        """Find which CRN at (day, block) involves this entity."""
        entity_by_crn = (
            self.dataset.students_by_crn
            if entity_type == "student"
            else self.dataset.instructors_by_crn
        )

        for existing_crn in self.slot_to_crns[(day, block)]:
            if entity_id in entity_by_crn.get(existing_crn, frozenset()):
                return existing_crn
        return None
