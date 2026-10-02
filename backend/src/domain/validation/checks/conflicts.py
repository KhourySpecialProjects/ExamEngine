"""Conflicts: recompute from the enrollments and compare with the stored analysis.

Stored entries (conflict_analyses.conflicts) are reduced to keys:
- hard_conflicts.<type>: {"entity_id", "day": day name, "block": int, ...}
- soft_conflicts.back_to_back_students: {"student_id", "day", "blocks", ...}
- soft_conflicts.back_to_back_instructors: {"instructor_name", "day", ...}
- soft_conflicts.large_courses_not_early: {"crn", "size", "day", "block", ...}
"""

from collections import defaultdict
from collections.abc import Callable, Mapping
from typing import Any

from src.domain.constants import (
    BLOCK_TIMES,
    DAY_NAMES,
    EARLY_WEEK_CUTOFF,
    LARGE_COURSE_THRESHOLD,
)
from src.domain.validation.context import (
    Slot,
    ValidationContext,
    day_label,
    slot_label,
    unit_label,
)
from src.domain.validation.results import CheckResult, passed, plural, problems


Key = tuple[Any, ...]


# ----------------------------------------------------------------------
# Stored entries
# ----------------------------------------------------------------------


def _text(value: Any) -> str:
    """Stored entity id/name/CRN as text (numbers from older JSON are accepted)."""
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if not isinstance(value, str) or not value:
        raise ValueError("expected a non-empty string")
    return value


def _day(value: Any) -> int:
    """Stored day: a day name (as saved) or a day index."""
    if isinstance(value, str) and value in DAY_NAMES:
        return DAY_NAMES.index(value)
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    raise ValueError(f"unknown day {value!r}")


def _block(value: Any) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    raise ValueError(f"unknown block {value!r}")


def _stored_keys(
    ctx: ValidationContext,
    section: str,
    name: str,
    parse: Callable[[Mapping[str, Any]], Key],
) -> tuple[set[Key], list[str]]:
    """Keys of the stored `section.name` entries, and unreadable-entry notes."""
    stored = ctx.analysis().get(section)
    if stored is None:
        return set(), []
    if not isinstance(stored, Mapping):
        return set(), [f"Stored {section} is not an object"]
    entries = stored.get(name, [])
    if not isinstance(entries, list):
        return set(), [f"Stored {section}.{name} is not a list"]

    keys: set[Key] = set()
    unreadable: list[str] = []
    for index, entry in enumerate(entries):
        try:
            if not isinstance(entry, Mapping):
                raise TypeError("entry is not an object")
            keys.add(parse(entry))
        except (KeyError, TypeError, ValueError):
            unreadable.append(f"Unreadable stored {name} entry #{index + 1}")
    return keys, unreadable


def _compare(
    recomputed: Mapping[Key, str],
    stored: set[Key],
    unreadable: list[str],
    describe: Callable[[Key], str],
    noun: str,
    nouns: str,
) -> CheckResult:
    """fail on any missed/invented key, warn if all reported, else pass."""
    missed = sorted(recomputed.keys() - stored)
    phantom = sorted(stored - recomputed.keys())
    if missed or phantom or unreadable:
        examples = (
            [f"Missed: {describe(key)}: {recomputed[key]}" for key in missed]
            + [f"Not real: {describe(key)}" for key in phantom]
            + unreadable
        )
        summary = (
            f"The stored analysis missed {plural(len(missed), noun, nouns)} and "
            f"reported {len(phantom)} that are not real."
        )
        if unreadable:
            summary += f" {plural(len(unreadable), 'stored entry', 'stored entries')}"
            summary += " could not be read."
        return problems(
            "fail",
            summary,
            examples,
            count=len(missed) + len(phantom) + len(unreadable),
        )
    if recomputed:
        return problems(
            "warn",
            f"Found {plural(len(recomputed), noun, nouns)}; all reported in the "
            "stored analysis.",
            [f"{describe(key)}: {recomputed[key]}" for key in sorted(recomputed)],
        )
    return passed(f"No {nouns}, and none reported.")


def _hard_key(entry: Mapping[str, Any]) -> Key:
    return (_text(entry["entity_id"]), _day(entry["day"]), _block(entry["block"]))


def _hard_day_key(entry: Mapping[str, Any]) -> Key:
    return (_text(entry["entity_id"]), _day(entry["day"]))


def _units_text(units: set[str]) -> str:
    return ", ".join(unit_label(unit) for unit in sorted(units))


# ----------------------------------------------------------------------
# Recomputation
# ----------------------------------------------------------------------


def _double_booked(schedule: Mapping[str, Mapping[Slot, set[str]]]) -> dict[Key, str]:
    return {
        (entity, day, block): _units_text(units)
        for entity, slots in schedule.items()
        for (day, block), units in slots.items()
        if len(units) >= 2
    }


def _over_daily_limit(
    schedule: Mapping[str, Mapping[Slot, set[str]]], limit: int
) -> dict[Key, str]:
    """(entity, day) with more than `limit` exams that day."""
    over: dict[Key, str] = {}
    for entity, slots in schedule.items():
        per_day: dict[int, set[tuple[str, int]]] = defaultdict(set)
        for (day, block), units in slots.items():
            per_day[day].update((unit, block) for unit in units)
        for day, exams in per_day.items():
            if len(exams) > limit:
                over[(entity, day)] = f"{len(exams)} exams (limit {limit})"
    return over


def _back_to_back(schedule: Mapping[str, Mapping[Slot, set[str]]]) -> dict[Key, str]:
    """(entity, day) with exams in adjacent blocks of that same day.

    The last block of one day and the first block of the next are not
    back-to-back.
    """
    found: dict[Key, str] = {}
    for entity, slots in schedule.items():
        blocks_by_day: dict[int, set[int]] = defaultdict(set)
        for day, block in slots:
            blocks_by_day[day].add(block)
        for day, blocks in blocks_by_day.items():
            if any(block + 1 in blocks for block in blocks):
                found[(entity, day)] = ", ".join(
                    BLOCK_TIMES.get(block, f"block {block}") for block in sorted(blocks)
                )
    return found


def _student_slot(key: Key) -> str:
    return f"student {key[0]}, {slot_label(key[1], key[2])}"


def _student_day(key: Key) -> str:
    return f"student {key[0]}, {day_label(key[1])}"


def _instructor_slot(key: Key) -> str:
    return f"instructor {key[0]}, {slot_label(key[1], key[2])}"


def _instructor_day(key: Key) -> str:
    return f"instructor {key[0]}, {day_label(key[1])}"


# ----------------------------------------------------------------------
# Checks
# ----------------------------------------------------------------------


def student_double_book(ctx: ValidationContext) -> CheckResult:
    recomputed = _double_booked(ctx.student_slot_units)
    stored, unreadable = _stored_keys(
        ctx, "hard_conflicts", "student_double_book", _hard_key
    )
    return _compare(
        recomputed,
        stored,
        unreadable,
        _student_slot,
        "student double-booking",
        "student double-bookings",
    )


def instructor_double_book(ctx: ValidationContext) -> CheckResult:
    recomputed = _double_booked(ctx.instructor_slot_groups)
    stored, unreadable = _stored_keys(
        ctx, "hard_conflicts", "instructor_double_book", _hard_key
    )
    return _compare(
        recomputed,
        stored,
        unreadable,
        _instructor_slot,
        "instructor double-booking",
        "instructor double-bookings",
    )


def student_over_max_per_day(ctx: ValidationContext) -> CheckResult:
    recomputed = _over_daily_limit(
        ctx.student_slot_units, ctx.params.student_max_per_day
    )
    stored, unreadable = _stored_keys(
        ctx, "hard_conflicts", "student_gt_max_per_day", _hard_day_key
    )
    return _compare(
        recomputed,
        stored,
        unreadable,
        _student_day,
        "student day over the daily limit",
        "student days over the daily limit",
    )


def instructor_over_max_per_day(ctx: ValidationContext) -> CheckResult:
    recomputed = _over_daily_limit(
        ctx.instructor_slot_groups, ctx.params.instructor_max_per_day
    )
    stored, unreadable = _stored_keys(
        ctx, "hard_conflicts", "instructor_gt_max_per_day", _hard_day_key
    )
    return _compare(
        recomputed,
        stored,
        unreadable,
        _instructor_day,
        "instructor day over the daily limit",
        "instructor days over the daily limit",
    )


def student_back_to_back(ctx: ValidationContext) -> CheckResult:
    recomputed = _back_to_back(ctx.student_slot_units)
    stored, unreadable = _stored_keys(
        ctx,
        "soft_conflicts",
        "back_to_back_students",
        lambda entry: (_text(entry["student_id"]), _day(entry["day"])),
    )
    return _compare(
        recomputed,
        stored,
        unreadable,
        _student_day,
        "student day with back-to-back exams",
        "student days with back-to-back exams",
    )


def instructor_back_to_back(ctx: ValidationContext) -> CheckResult:
    recomputed = _back_to_back(ctx.instructor_slot_groups)
    stored, unreadable = _stored_keys(
        ctx,
        "soft_conflicts",
        "back_to_back_instructors",
        lambda entry: (_text(entry["instructor_name"]), _day(entry["day"])),
    )
    return _compare(
        recomputed,
        stored,
        unreadable,
        _instructor_day,
        "instructor day with back-to-back exams",
        "instructor days with back-to-back exams",
    )


def large_course_late(ctx: ValidationContext) -> CheckResult:
    ctx.courses()
    recomputed: dict[Key, str] = {}
    for row in ctx.placed_rows:
        day = row.slot[0]
        size = ctx.enrollment_of(row)
        if size >= LARGE_COURSE_THRESHOLD and day >= EARLY_WEEK_CUTOFF:
            recomputed[(row.crn,)] = f"{size} students on {day_label(day)}"
    stored, unreadable = _stored_keys(
        ctx,
        "soft_conflicts",
        "large_courses_not_early",
        lambda entry: (_text(entry["crn"]),),
    )
    return _compare(
        recomputed,
        stored,
        unreadable,
        lambda key: f"CRN {key[0]}",
        f"course of {LARGE_COURSE_THRESHOLD}+ students placed after "
        f"{DAY_NAMES[EARLY_WEEK_CUTOFF - 1]}",
        f"courses of {LARGE_COURSE_THRESHOLD}+ students placed after "
        f"{DAY_NAMES[EARLY_WEEK_CUTOFF - 1]}",
    )
