
from src.domain.constants import EARLY_WEEK_CUTOFF, LARGE_COURSE_THRESHOLD
from src.domain.models import SchedulingDataset
from src.domain.value_objects import SchedulingState, SoftPenalty


class SoftConstraintEvaluator:
    """
    Evaluates soft constraint penalties for time slot selection.

    Soft constraints are preferences we minimize but don't block placement.
    """

    def __init__(
        self,
        dataset: SchedulingDataset,
        state: SchedulingState,
        weight_large_late: int = 1,
        weight_b2b_student: int = 6,
        weight_b2b_instructor: int = 2,
    ):
        self.dataset = dataset
        self.weight_large_late = weight_large_late
        self.weight_b2b_student = weight_b2b_student
        self.weight_b2b_instructor = weight_b2b_instructor
        self.state = state

    def evaluate(self, crn: str, day: int, block: int) -> SoftPenalty:
        penalty = SoftPenalty()

        enrollment = self.dataset.get_enrollment_count(crn)
        # 1. Large course late penalty
        if enrollment >= LARGE_COURSE_THRESHOLD:
            days_late = max(0, day - EARLY_WEEK_CUTOFF + 1)
            penalty.large_course_late = days_late * self.weight_large_late

        # 2. Back-to-back students
        b2b_students = 0
        students = self.dataset.students_by_crn.get(crn, frozenset())

        for student_id in students:
            day_blocks = [
                b for d, b in self.state.student_schedule[student_id] if d == day
            ]
            if (block - 1 in day_blocks) or (block + 1 in day_blocks):
                b2b_students += 1
        penalty.back_to_back_students = b2b_students * self.weight_b2b_student

        # 3. Back-to-back instructors
        b2b_instructors = 0
        instructors = self.dataset.instructors_by_crn.get(crn, frozenset())

        for instructor in instructors:
            day_blocks = [
                b for d, b in self.state.instructor_schedule[instructor] if d == day
            ]
            if (block - 1 in day_blocks) or (block + 1 in day_blocks):
                b2b_instructors += 1
        penalty.back_to_back_instructors = b2b_instructors * self.weight_b2b_instructor

        # 4. Instructor load
        instr_load = 0
        for instructor in instructors:
            day_count = sum(
                1 for d, _ in self.state.instructor_schedule[instructor] if d == day
            )
            instr_load += day_count
        penalty.instructor_load = instr_load

        # 5-6. Slot load
        slot = (day, block)
        penalty.slot_seat_load = self.state.slot_seat_load[slot]
        penalty.slot_exam_count = self.state.slot_exam_count[slot]

        return penalty
