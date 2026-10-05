"""Late add: the stored conflict analysis of a new version (base + late exam).

Pure domain code. A late add never re-runs the analysis: the new version's
`conflict_analyses.conflicts` is a deep copy of the base's plus the late
exam's delta, in the shapes `ScheduleAnalyzer` stores:

- hard conflicts `{entity_id, day, block, block_time, crn, course,
  conflicting_crn, conflicting_course}` with `crn` = the late exam. A
  double-book is one entry per (person, base CRN in the block), the pair
  convention of generation; a daily-limit entry is one per person over the
  limit, with `conflicting_*` = None.
- back-to-back entries are one per (person, day): an existing entry gets the
  late block added to its `blocks`/`block_times`, otherwise a new entry lists
  the person's sorted blocks that day.
- a `large_courses_not_early` entry when the late exam is large and late.
- `statistics`: every `*_count`, both totals, `num_classes`, `num_students`,
  `num_rooms` and `slots_used` recomputed from the lists and the exams.
"""

import copy
from collections.abc import Callable, Iterable, Mapping
from typing import Any

from src.domain.constants import BLOCK_TIMES, DAY_NAMES
from src.domain.services.late_add import (
    BaseSchedule,
    BlockEvaluation,
    LateExam,
    instructor_key,
)


HARD_TYPES = (
    "student_double_book",
    "instructor_double_book",
    "student_gt_max_per_day",
    "instructor_gt_max_per_day",
)
SOFT_TYPES = (
    "back_to_back_students",
    "back_to_back_instructors",
    "large_courses_not_early",
)


def late_exam_analysis(
    stored: Mapping[str, Any] | None,
    base: BaseSchedule,
    late: LateExam,
    placement: BlockEvaluation,
    room: str,
) -> dict[str, Any]:
    """The base's stored `conflicts` plus the late exam placed at `placement`.

    `stored` is the base's `conflict_analyses.conflicts` (None or {} when the
    base has none); it is not modified.
    """
    analysis = copy.deepcopy(dict(stored or {}))
    hard = _section(analysis, "hard_conflicts", HARD_TYPES)
    soft = _section(analysis, "soft_conflicts", SOFT_TYPES)
    analysis.setdefault("unscheduled_groups", [])

    day, block = placement.day, placement.block
    course_by_crn = {exam.crn: exam.course_code for exam in base.exams}

    def hard_entry(entity: str, conflicting_crn: str | None) -> dict[str, Any]:
        return {
            "entity_id": entity,
            "day": DAY_NAMES[day],
            "block": block,
            "block_time": BLOCK_TIMES.get(block, ""),
            "crn": late.crn,
            "course": late.course_code,
            "conflicting_crn": conflicting_crn,
            "conflicting_course": (
                course_by_crn.get(conflicting_crn, "") if conflicting_crn else None
            ),
        }

    for student in sorted(placement.student_double_book):
        hard["student_double_book"].extend(
            hard_entry(student, crn) for crn in placement.student_double_book[student]
        )
    hard["student_gt_max_per_day"].extend(
        hard_entry(student, None)
        for student in sorted(placement.student_over_daily_limit)
    )

    instructor = instructor_key(late.instructor_id)
    if instructor is not None:
        hard["instructor_double_book"].extend(
            hard_entry(instructor, crn) for crn in placement.instructor_double_book
        )
        if placement.instructor_over_daily_limit:
            hard["instructor_gt_max_per_day"].append(hard_entry(instructor, None))

    for student in sorted(placement.student_day_blocks):
        _add_back_to_back(
            soft["back_to_back_students"],
            "student_id",
            student,
            lambda value, student=student: _text(value) == student,
            day,
            block,
            placement.student_day_blocks[student],
            new=student in placement.student_back_to_back,
        )
    if instructor is not None:
        _add_back_to_back(
            soft["back_to_back_instructors"],
            "instructor_name",
            instructor,
            lambda value: instructor_key(_text(value)) == instructor,
            day,
            block,
            placement.instructor_day_blocks,
            new=placement.instructor_back_to_back,
        )

    if placement.large_course_late:
        soft["large_courses_not_early"].append(
            {
                "crn": late.crn,
                "course": late.course_code,
                "size": late.size,
                "day": DAY_NAMES[day],
                "block": block,
                "block_time": BLOCK_TIMES.get(block, ""),
            }
        )

    analysis["statistics"] = _statistics(
        analysis.get("statistics"), hard, soft, base, late, placement, room
    )
    return analysis


def _section(
    analysis: dict[str, Any], name: str, types: Iterable[str]
) -> dict[str, list[Any]]:
    section = analysis.get(name)
    if not isinstance(section, dict):
        section = analysis[name] = {}
    for conflict_type in types:
        if not isinstance(section.get(conflict_type), list):
            section[conflict_type] = []
    return section


def _text(value: Any) -> str | None:
    return None if value is None else str(value)


def _same_day(value: Any, day: int) -> bool:
    if isinstance(value, bool):
        return False
    return value == DAY_NAMES[day] or value == day


def _block_fields(blocks: Iterable[int]) -> dict[str, list[Any]]:
    ordered = sorted(set(blocks))
    return {
        "blocks": ordered,
        "block_times": [BLOCK_TIMES.get(b, "") for b in ordered],
    }


def _add_back_to_back(
    entries: list[Any],
    key: str,
    person: str,
    matches: Callable[[Any], bool],
    day: int,
    block: int,
    day_blocks: tuple[int, ...],
    *,
    new: bool,
) -> None:
    """Add the late block to the person's entry that day, or add an entry."""
    for entry in entries:
        if (
            isinstance(entry, dict)
            and matches(entry.get(key))
            and _same_day(entry.get("day"), day)
        ):
            existing = [
                b
                for b in entry.get("blocks") or ()
                if isinstance(b, int) and not isinstance(b, bool)
            ]
            entry.update(_block_fields([*existing, block]))
            return
    if new:
        entries.append(
            {key: person, "day": DAY_NAMES[day], **_block_fields(day_blocks)}
        )


def _statistics(
    stored: Any,
    hard: Mapping[str, list[Any]],
    soft: Mapping[str, list[Any]],
    base: BaseSchedule,
    late: LateExam,
    placement: BlockEvaluation,
    room: str,
) -> dict[str, Any]:
    stats = dict(stored) if isinstance(stored, Mapping) else {}
    placed = [exam for exam in base.exams if exam.slot is not None]
    students: set[str] = set(late.students)
    for exam in placed:
        students.update(base.students_by_crn.get(exam.crn, ()))

    stats.update(
        {
            "num_classes": len({exam.crn for exam in placed} | {late.crn}),
            "num_students": len(students),
            "num_rooms": len({exam.room for exam in placed if exam.room} | {room}),
            "slots_used": len(
                {exam.slot for exam in placed} | {(placement.day, placement.block)}
            ),
            "total_hard_conflicts": sum(len(hard[t]) for t in HARD_TYPES),
            "total_soft_conflicts": sum(len(soft[t]) for t in SOFT_TYPES),
            **{f"{t}_count": len(hard[t]) for t in HARD_TYPES},
            **{f"{t}_count": len(soft[t]) for t in SOFT_TYPES},
        }
    )
    stats.setdefault("unplaced_exams", 0)
    return stats
