from collections import defaultdict

from src.domain.constants import (
    BLOCK_TIMES,
    DAY_NAMES,
    EARLY_WEEK_CUTOFF,
    LARGE_COURSE_THRESHOLD,
)
from src.domain.models import SchedulingDataset
from src.domain.services.conflict_detector import Conflict
from src.domain.services.scheduler import ScheduleResult
from src.domain.value_objects import (
    HardConflicts,
    ScheduleAnalysis,
    ScheduleStatistics,
    SoftConflicts,
)


class ScheduleAnalyzer:
    """
    Analyzes a completed schedule to compute conflicts and statistics.

    This is a stateless service - it takes a ScheduleResult and SchedulingDataset
    and produces a ScheduleAnalysis.
    """

    def __init__(self, dataset: SchedulingDataset):
        self.dataset = dataset

    def analyze(
        self,
        schedule: ScheduleResult,
    ) -> ScheduleAnalysis:
        """
        Perform complete analysis of a schedule.

        Args:
            assignments: CRN -> (day_idx, block_idx)
            room_assignments: CRN -> room_name
            conflicts: List of hard conflicts from scheduling
            course_codes: CRN -> course code string
            course_sizes: CRN -> enrollment count

        Returns:
            Complete ScheduleAnalysis with hard/soft conflicts and statistics
        """
        assignments = schedule.assignments
        room_assignments = schedule.room_assignments
        conflicts = schedule.conflicts
        course_codes = schedule.course_codes
        course_sizes = schedule.course_sizes

        hard_conflicts = self._categorize_hard_conflicts(conflicts, course_codes)
        soft_conflicts = self._compute_soft_conflicts(
            assignments, course_codes, course_sizes
        )
        statistics = self._compute_statistics(
            assignments, room_assignments, hard_conflicts, soft_conflicts
        )

        return ScheduleAnalysis(
            hard_conflicts=hard_conflicts,
            soft_conflicts=soft_conflicts,
            statistics=statistics,
        )

    def _categorize_hard_conflicts(
        self, conflicts: list[Conflict], course_codes: dict[str, str]
    ) -> HardConflicts:
        """Categorize hard conflicts by type."""
        result = HardConflicts()

        for conflict in conflicts:
            entry = {
                "entity_id": conflict.entity_id,
                "day": DAY_NAMES[conflict.day],
                "block": conflict.block,
                "block_time": BLOCK_TIMES.get(conflict.block, ""),
                "crn": conflict.crn,
                "course": course_codes.get(conflict.crn, ""),
                "conflicting_crn": conflict.conflicting_crn,
                "conflicting_course": course_codes.get(conflict.conflicting_crn, "")
                if conflict.conflicting_crn
                else None,
            }

            if conflict.conflict_type == "student_double_book":
                result.student_double_book.append(entry)
            elif conflict.conflict_type == "instructor_double_book":
                result.instructor_double_book.append(entry)
            elif conflict.conflict_type == "student_gt_max_per_day":
                result.student_gt_max_per_day.append(entry)
            elif conflict.conflict_type == "instructor_gt_max_per_day":
                result.instructor_gt_max_per_day.append(entry)

        return result

    def _compute_soft_conflicts(
        self,
        assignments: dict[str, tuple[int, int]],
        course_codes: dict[str, str],
        course_sizes: dict[str, int],
    ) -> SoftConflicts:
        """Compute soft constraint violations from final schedule."""
        result = SoftConflicts()

        # Build schedule views by entity and day
        student_day_blocks: dict[str, dict[int, list[int]]] = defaultdict(
            lambda: defaultdict(list)
        )
        instructor_day_blocks: dict[str, dict[int, list[int]]] = defaultdict(
            lambda: defaultdict(list)
        )

        for crn, (day_idx, block_idx) in assignments.items():
            # Track student schedules
            for student_id in self.dataset.students_by_crn.get(crn, frozenset()):
                student_day_blocks[student_id][day_idx].append(block_idx)

            # Track instructor schedules
            for instructor in self.dataset.instructors_by_crn.get(crn, frozenset()):
                instructor_day_blocks[instructor][day_idx].append(block_idx)

        # Detect back-to-back for students
        for student_id, day_blocks in student_day_blocks.items():
            for day_idx, blocks in day_blocks.items():
                blocks_sorted = sorted(blocks)
                has_b2b = any(
                    blocks_sorted[i] == blocks_sorted[i - 1] + 1
                    for i in range(1, len(blocks_sorted))
                )
                if has_b2b:
                    result.back_to_back_students.append(
                        {
                            "student_id": student_id,
                            "day": DAY_NAMES[day_idx],
                            "blocks": blocks_sorted,
                            "block_times": [
                                BLOCK_TIMES.get(b, "") for b in blocks_sorted
                            ],
                        }
                    )

        # Detect back-to-back for instructors
        for instructor, day_blocks in instructor_day_blocks.items():
            for day_idx, blocks in day_blocks.items():
                blocks_sorted = sorted(blocks)
                has_b2b = any(
                    blocks_sorted[i] == blocks_sorted[i - 1] + 1
                    for i in range(1, len(blocks_sorted))
                )
                if has_b2b:
                    result.back_to_back_instructors.append(
                        {
                            "instructor_name": instructor,
                            "day": DAY_NAMES[day_idx],
                            "blocks": blocks_sorted,
                            "block_times": [
                                BLOCK_TIMES.get(b, "") for b in blocks_sorted
                            ],
                        }
                    )

        # Detect large courses scheduled late (after Wednesday)
        for crn, (day_idx, block_idx) in assignments.items():
            size = course_sizes.get(crn, 0)
            if size >= LARGE_COURSE_THRESHOLD and day_idx >= EARLY_WEEK_CUTOFF:
                result.large_courses_not_early.append(
                    {
                        "crn": crn,
                        "course": course_codes.get(crn, ""),
                        "size": size,
                        "day": DAY_NAMES[day_idx],
                        "block": block_idx,
                        "block_time": BLOCK_TIMES.get(block_idx, ""),
                    }
                )

        return result

    def _compute_statistics(
        self,
        assignments: dict[str, tuple[int, int]],
        room_assignments: dict[str, str],
        hard_conflicts: HardConflicts,
        soft_conflicts: SoftConflicts,
    ) -> ScheduleStatistics:
        """Compute summary statistics."""
        # Count unique students
        all_students = set()
        for crn in assignments:
            students = self.dataset.students_by_crn.get(crn, frozenset())
            all_students.update(students)

        return ScheduleStatistics(
            num_classes=len(assignments),
            num_students=len(all_students),
            num_rooms=len(set(room_assignments.values())),
            slots_used=len(set(assignments.values())),
            unplaced_exams=0,  # All exams are placed in current implementation
            total_hard_conflicts=hard_conflicts.total_count,
            total_soft_conflicts=soft_conflicts.total_count,
        )
