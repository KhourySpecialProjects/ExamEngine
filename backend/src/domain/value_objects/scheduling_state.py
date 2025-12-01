from collections import defaultdict
from dataclasses import dataclass, field

from src.domain.models import SchedulingDataset


@dataclass
class SchedulingState:
    """
    Single source of truth for incremental scheduling state.

    This class maintains all state needed during the scheduling process,
    ensuring ConflictDetector and SoftConstraintEvaluator operate on
    consistent data without duplication.

    The state tracks:
    - Which time slots each student/instructor is assigned to
    - Which CRNs are placed in each slot
    - Load metrics per slot (seat count, exam count)

    Usage:
        state = SchedulingState()
        detector = ConflictDetector(dataset, state, ...)
        evaluator = SoftConstraintEvaluator(dataset, state, ...)

        # After placing a course, update state ONCE
        state.record_placement(crn, day, block, dataset)
    """

    # Core scheduling state - tracks assignments
    student_schedule: dict[str, list[tuple[int, int]]] = field(
        default_factory=lambda: defaultdict(list)
    )
    instructor_schedule: dict[str, list[tuple[int, int]]] = field(
        default_factory=lambda: defaultdict(list)
    )
    slot_to_crns: dict[tuple[int, int], list[str]] = field(
        default_factory=lambda: defaultdict(list)
    )

    # Load metrics for soft constraint evaluation
    slot_seat_load: dict[tuple[int, int], int] = field(
        default_factory=lambda: defaultdict(int)
    )
    slot_exam_count: dict[tuple[int, int], int] = field(
        default_factory=lambda: defaultdict(int)
    )

    def record_placement(
        self, crn: str, day: int, block: int, dataset: SchedulingDataset
    ) -> None:
        """
        Record that a CRN was placed at (day, block).

        This is the ONLY method that should modify scheduling state.
        Call this once after each placement decision.

        Args:
            crn: Course registration number being placed
            day: Day index (0-based)
            block: Block index within day (0-based)
            dataset: SchedulingDataset for looking up enrollments
        """
        slot = (day, block)

        # Update student schedules
        for student_id in dataset.students_by_crn.get(crn, frozenset()):
            self.student_schedule[student_id].append(slot)

        # Update instructor schedules
        for instructor in dataset.instructors_by_crn.get(crn, frozenset()):
            self.instructor_schedule[instructor].append(slot)

        # Update slot tracking
        self.slot_to_crns[slot].append(crn)

        # Update load metrics
        enrollment = dataset.get_enrollment_count(crn)
        self.slot_seat_load[slot] += enrollment
        self.slot_exam_count[slot] += 1

    def get_student_slots(self, student_id: str) -> list[tuple[int, int]]:
        """Get all slots assigned to a student."""
        return self.student_schedule[student_id]

    def get_instructor_slots(self, instructor: str) -> list[tuple[int, int]]:
        """Get all slots assigned to an instructor."""
        return self.instructor_schedule[instructor]

    def get_crns_in_slot(self, day: int, block: int) -> list[str]:
        """Get all CRNs placed in a specific slot."""
        return self.slot_to_crns[(day, block)]

    def get_slot_load(self, day: int, block: int) -> tuple[int, int]:
        """Get (seat_load, exam_count) for a slot."""
        slot = (day, block)
        return self.slot_seat_load[slot], self.slot_exam_count[slot]

    def reset(self) -> None:
        """Clear all state for a fresh scheduling run."""
        self.student_schedule.clear()
        self.instructor_schedule.clear()
        self.slot_to_crns.clear()
        self.slot_seat_load.clear()
        self.slot_exam_count.clear()
