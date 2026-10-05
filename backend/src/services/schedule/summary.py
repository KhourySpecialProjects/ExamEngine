"""Every number shown about one schedule, built from saved rows only.

The schedule page (Statistics tab, the Conflicts tab's summary cards, the
settings in its header) and the compare page read this; the browser does not
compute its own. Inputs are the schedule's exam assignments, the formatted
conflict breakdown, the stored unscheduled groups, the run and the dataset's
stored metadata, so it never reads the uploaded files.
"""

import math
from collections import defaultdict
from collections.abc import Hashable, Mapping, Sequence
from typing import Any

from src.domain.constants import DAY_NAMES


# Blocks per day every schedule used before the setting was recorded.
LEGACY_BLOCKS_PER_DAY = 5

# Summary conflict metric for each breakdown conflict type that counts people.
_PERSON_METRICS = {
    "student_double_book": "student_double_book",
    "instructor_double_book": "instructor_double_book",
    "student_gt_max_per_day": "student_over_daily_limit",
    "instructor_gt_max_per_day": "instructor_over_daily_limit",
    "back_to_back": "student_back_to_back",
    "back_to_back_instructor": "instructor_back_to_back",
}
_INSTRUCTOR_TYPES = {
    "instructor_double_book",
    "instructor_gt_max_per_day",
    "back_to_back_instructor",
}
# Per-day limit records name only the exam that went over the limit, so a
# person's occurrence is the whole day.
_PER_DAY_TYPES = {"student_gt_max_per_day", "instructor_gt_max_per_day"}
_LARGE_COURSE_TYPE = "large_course_not_early"

# Room fill buckets: (key, lower bound in percent), checked from the top.
_FILL_BUCKETS = (
    ("from_90_to_100", 90),
    ("from_75_to_90", 75),
    ("from_50_to_75", 50),
    ("under_50", 0),
)

_SETTING_KEYS = (
    "time_budget_seconds",
    "max_days",
    "student_max_per_day",
    "instructor_max_per_day",
    "avoid_back_to_back",
    "prioritize_large_courses",
)

# Recorded settings each engine ignores. Classic runs still store the time
# budget's default; Optimized accepts prioritize-large but its ordering
# supersedes it.
_UNUSED_SETTINGS = {
    "dsatur": ("time_budget_seconds", "avoid_back_to_back"),
    "annealing": ("prioritize_large_courses",),
}


def build_schedule_summary(
    *,
    assignments: Sequence[Any],
    breakdown: Sequence[Mapping[str, Any]],
    unscheduled_groups: Sequence[Mapping[str, Any]],
    run: Any,
    dataset: Any,
) -> dict[str, Any]:
    """The summary of one schedule (see `docs/DATA.md`, "Schedule summary").

    Args:
        assignments: The schedule's `ExamAssignments` rows with course,
            time_slot and room loaded. No time slot = unscheduled; a time slot
            but no room = unroomed; both = placed.
        breakdown: `ConflictAssembler.format_conflicts(...)["breakdown"]`.
        unscheduled_groups: The groups stored with the conflict analysis.
        run: The schedule's `Runs` row (algorithm_name, parameters).
        dataset: The run's `Datasets` row (file_paths, course_merges,
            common_exam_groups).
    """
    settings, assumed = resolve_settings(run.algorithm_name, run.parameters)
    metadata = {
        entry.get("type"): entry.get("metadata") or {}
        for entry in dataset.file_paths or []
    }
    blockouts = metadata.get("room_blockouts", {})

    return {
        "settings": settings,
        "settings_assumed": assumed,
        "settings_unused": list(_UNUSED_SETTINGS.get(settings["algorithm"], ())),
        "unique_students": metadata.get("enrollments", {}).get("unique_students"),
        **_exam_stats(assignments, unscheduled_groups),
        "conflicts": count_conflicts(breakdown),
        "groups": _group_stats(
            assignments, dataset.course_merges or {}, dataset.common_exam_groups or {}
        ),
        "blockouts": {
            "rooms": blockouts.get("unique_rooms_blocked", 0),
            "slots": blockouts.get("total_blockout_entries", 0),
        },
    }


def resolve_settings(
    algorithm_name: str | None, parameters: Mapping[str, Any] | None
) -> tuple[dict[str, Any], list[str]]:
    """The settings a run used, and which of them were assumed.

    `parameters.algorithm` exists only since the algorithm became selectable;
    earlier runs were all DSATUR, recorded in `algorithm_name`. Runs from before
    blocks per day was recorded used 5 (assumed). Other settings a run did not
    record are None.
    """
    params = parameters or {}
    algorithm = params.get("algorithm") or (algorithm_name or "dsatur").lower()
    settings: dict[str, Any] = {"algorithm": algorithm}
    assumed: list[str] = []

    blocks = params.get("blocks_per_day")
    if blocks is None:
        blocks = LEGACY_BLOCKS_PER_DAY
        assumed.append("blocks_per_day")
    settings["blocks_per_day"] = blocks

    for key in _SETTING_KEYS:
        settings[key] = params.get(key)
    return settings, assumed


def count_conflicts(
    breakdown: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, int]]:
    """Distinct people and their occurrences per conflict type.

    Matches the Conflicts tab: a person's records merge into one occurrence per
    day and time (so an N-way double-book, stored as pairs, is one), per day
    for the daily limits, and per block pair for back-to-back. A record without
    a person counts as its own person. Large courses late counts distinct exams
    and their records.
    """
    people: dict[str, set[Hashable]] = defaultdict(set)
    occurrences: dict[str, set[Hashable]] = defaultdict(set)
    large_exams: set[Hashable] = set()
    large_records = 0

    for index, record in enumerate(breakdown):
        conflict_type = record.get("conflict_type")
        if conflict_type == _LARGE_COURSE_TYPE:
            crn = record.get("crn")
            large_exams.add(str(crn) if crn not in (None, "") else ("record", index))
            large_records += 1
            continue
        metric = _PERSON_METRICS.get(conflict_type)
        if metric is None:
            continue
        person = _person(record, conflict_type) or ("record", index)
        people[metric].add(person)
        occurrences[metric].add((person, _occurrence(record, conflict_type)))

    counts = {
        metric: {
            "people": len(people[metric]),
            "instances": len(occurrences[metric]),
        }
        for metric in _PERSON_METRICS.values()
    }
    counts["large_courses_late"] = {
        "people": len(large_exams),
        "instances": large_records,
    }
    return counts


def _person(record: Mapping[str, Any], conflict_type: str) -> str | None:
    """Instructor name or student ID; IDs stay strings (leading zeros)."""
    if conflict_type in _INSTRUCTOR_TYPES:
        entity = record.get("instructor_name") or record.get("entity_id")
    else:
        entity = record.get("student_id") or record.get("entity_id")
    return str(entity) if entity not in (None, "") else None


def _occurrence(record: Mapping[str, Any], conflict_type: str) -> tuple:
    day = record.get("day") or ""
    if conflict_type in _PER_DAY_TYPES:
        return (day,)
    if record.get("block_time"):
        return (day, record["block_time"])
    block_times = tuple(t for t in record.get("block_times") or () if t)
    if block_times:
        return (day, *block_times)
    blocks = record.get("blocks") or (
        [record["block"]] if record.get("block") is not None else []
    )
    return (day, *(f"Block {b}" for b in blocks))


def _exam_issue(assignment: Any) -> dict[str, Any]:
    return {
        "crn": str(assignment.course.crn),
        "course": assignment.course.course_subject_code or "",
        "size": assignment.course.enrollment_count or 0,
    }


def _round1(value: float) -> float:
    """Round half up to one decimal (as the UI always has)."""
    return math.floor(value * 10 + 0.5) / 10


def _exam_stats(
    assignments: Sequence[Any], unscheduled_groups: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    unscheduled: list[dict[str, Any]] = []
    unroomed: list[dict[str, Any]] = []
    over_capacity: list[dict[str, Any]] = []
    rooms: set[str] = set()
    slots: set[tuple[str, str]] = set()
    days_with_slots: set[str] = set()
    day_exams: dict[str, int] = defaultdict(int)
    day_seats: dict[str, int] = defaultdict(int)
    block_start: dict[str, Any] = {}
    cell_exams: dict[tuple[str, str], int] = defaultdict(int)
    fill_total = 0.0
    fill_count = 0
    buckets = {key: 0 for key, _ in reversed(_FILL_BUCKETS)}

    for a in assignments:
        if a.time_slot is None:
            unscheduled.append(_exam_issue(a))
            continue
        day = a.time_slot.day.value
        label = a.time_slot.slot_label
        slots.add((day, label))
        days_with_slots.add(day)
        if a.room is None:
            unroomed.append(_exam_issue(a))
            continue

        size = a.course.enrollment_count or 0
        capacity = a.room.capacity or 0
        rooms.add(a.room.location)
        day_exams[day] += 1
        day_seats[day] += size
        block_start.setdefault(label, a.time_slot.start_time)
        cell_exams[(day, label)] += 1
        # Rooms without a known capacity have no fill and are never over it.
        if capacity > 0:
            fill = min(size / capacity, 1) * 100
            fill_total += fill
            fill_count += 1
            # Integer comparison: no float error at a bucket's lower bound.
            seats_pct = min(size, capacity) * 100
            bucket = next(k for k, low in _FILL_BUCKETS if seats_pct >= low * capacity)
            buckets[bucket] += 1
            if size > capacity:
                over_capacity.append(
                    {**_exam_issue(a), "room": a.room.location, "capacity": capacity}
                )

    grouped = {str(crn) for g in unscheduled_groups for crn in g.get("crns", [])}
    days = sorted(day_exams, key=_day_rank)
    blocks = sorted(block_start, key=lambda label: block_start[label])
    placed = len(assignments) - len(unscheduled) - len(unroomed)

    return {
        "exams": {
            "total": len(assignments),
            "placed": placed,
            "unscheduled": len(unscheduled),
            "unroomed": len(unroomed),
            "over_capacity": len(over_capacity),
        },
        "unscheduled": {
            "exams": unscheduled,
            "students": sum(e["size"] for e in unscheduled),
            "groups": list(unscheduled_groups),
            "other_crns": [e["crn"] for e in unscheduled if e["crn"] not in grouped],
        },
        "unroomed": {
            "exams": unroomed,
            "students": sum(e["size"] for e in unroomed),
        },
        "over_capacity": sorted(
            over_capacity, key=lambda e: e["size"] - e["capacity"], reverse=True
        ),
        "rooms": {
            "used": len(rooms),
            "average_fill": _round1(fill_total / fill_count) if fill_count else 0,
            "fill_buckets": buckets,
        },
        "calendar": {
            "slots_used": len(slots),
            "days_used": len(days_with_slots),
            "days": [
                {"day": d, "exams": day_exams[d], "seats": day_seats[d]} for d in days
            ],
            "blocks": [
                {"label": b, "exams": sum(cell_exams[(d, b)] for d in days)}
                for b in blocks
            ],
            "matrix": [[cell_exams[(d, b)] for b in blocks] for d in days],
        },
    }


def _day_rank(day: str) -> int:
    return DAY_NAMES.index(day) if day in DAY_NAMES else len(DAY_NAMES)


def _group_stats(
    assignments: Sequence[Any],
    merges: Mapping[str, Sequence[Any]],
    common_groups: Mapping[str, Sequence[Any]],
) -> dict[str, dict[str, int]]:
    """Combined and common groups, and the exams (any state) belonging to them.

    A combined group with any CRN listed in a common group belongs to that
    common group as a whole.
    """
    combined_crns = {str(c).strip() for crns in merges.values() for c in crns}
    common_crns = {str(c).strip() for crns in common_groups.values() for c in crns}
    for crns in merges.values():
        members = {str(c).strip() for c in crns}
        if members & common_crns:
            common_crns |= members

    def stats(groups: int, crns: set[str]) -> dict[str, int]:
        members = [a for a in assignments if str(a.course.crn).strip() in crns]
        return {
            "groups": groups,
            "sections": len(members),
            "students": sum(a.course.enrollment_count or 0 for a in members),
        }

    return {
        "combined": stats(len(merges), combined_crns),
        "common": stats(len(common_groups), common_crns),
    }
