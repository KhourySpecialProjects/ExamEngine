"""Rooms: real rooms, enough seats, one exam per room per slot, no blockouts."""

import math
from collections import defaultdict

from src.domain.validation.context import (
    ValidationContext,
    slot_label,
    unit_label,
    unreadable_summary,
)
from src.domain.validation.results import (
    CheckResult,
    CheckSkippedError,
    passed,
    plural,
    problems,
)
from src.domain.validation.snapshot import RoomRecord, ScheduleRow


def _roomed_rows_by_slot(
    ctx: ValidationContext,
) -> dict[tuple[str, int, int], list[ScheduleRow]]:
    """(room, day, block) -> placed rows seated there."""
    seated: dict[tuple[str, int, int], list[ScheduleRow]] = defaultdict(list)
    for row in ctx.placed_rows:
        if row.room is not None:
            seated[(row.room, *row.slot)].append(row)
    return seated


def _rooms_by_name(ctx: ValidationContext) -> dict[str, RoomRecord]:
    """The rooms file, one room per name (the last row of a name wins)."""
    return {room.name: room for room in ctx.rooms()}


def _large_only_rule(rooms: dict[str, RoomRecord]) -> tuple[list[str], float]:
    """(large-only room names, cutoff) for the rooms file.

    Exams larger than the cutoff (the largest unmarked room) may only use a
    large-only room, and only they may. Without one the cutoff is infinite.
    """
    marked = sorted(name for name, room in rooms.items() if room.large_only)
    if not marked:
        return [], math.inf
    cutoff = max(
        (room.capacity for room in rooms.values() if not room.large_only), default=0
    )
    return marked, cutoff


def in_rooms_file(ctx: ValidationContext) -> CheckResult:
    ctx.rooms()
    capacities = ctx.file_room_capacity or {}
    issues: dict[str, str] = {}
    for row in ctx.snapshot.rows:
        if row.room is None or row.room in issues:
            continue
        if row.room not in capacities:
            issues[row.room] = f"Room {row.room} is not in the rooms file"
        elif row.room_capacity != capacities[row.room]:
            issues[row.room] = (
                f"Room {row.room}: stored capacity {row.room_capacity}, "
                f"rooms file {capacities[row.room]}"
            )
    if issues:
        return problems(
            "fail",
            f"Found {plural(len(issues), 'room')} missing from the rooms file or "
            "with a different capacity.",
            [issues[room] for room in sorted(issues)],
        )
    used = {row.room for row in ctx.snapshot.rows if row.room is not None}
    return passed(
        f"Checked {plural(len(used), 'room')}: all are in the rooms file with the "
        "same capacity."
    )


def capacity(ctx: ValidationContext) -> CheckResult:
    file_capacity = ctx.file_room_capacity
    over: list[tuple[int, str]] = []
    for (room, day, block), rows in _roomed_rows_by_slot(ctx).items():
        seats = sum(ctx.enrollment_of(row) for row in rows)
        room_capacity = file_capacity.get(room) if file_capacity is not None else None
        if room_capacity is None:
            room_capacity = rows[0].room_capacity
        if room_capacity is not None and seats > room_capacity:
            crns = ", ".join(f"CRN {row.crn}" for row in sorted(rows, key=_crn))
            over.append(
                (
                    room_capacity - seats,
                    f"Room {room} at {slot_label(day, block)}: {seats} students, "
                    f"capacity {room_capacity} ({crns})",
                )
            )
    if over:
        return problems(
            "fail",
            f"Found {plural(len(over), 'room')} seating more students than they hold.",
            [text for _, text in sorted(over)],
        )
    return passed("Every room holds the exams seated in it.")


def large_only(ctx: ValidationContext) -> CheckResult:
    marked, cutoff = _large_only_rule(_rooms_by_name(ctx))
    if not marked:
        return passed("No room is marked LargeOnly in the rooms file.")
    wrong: list[str] = []
    for (room, day, block), rows in sorted(_roomed_rows_by_slot(ctx).items()):
        seats = sum(ctx.enrollment_of(row) for row in rows)
        in_large = room in marked
        if in_large == (seats > cutoff):
            continue
        crns = ", ".join(f"CRN {row.crn}" for row in sorted(rows, key=_crn))
        reason = (
            f"only {seats} students, fits a regular room (largest {cutoff})"
            if in_large
            else f"{seats} students, needs large-only room {marked[0]}"
        )
        wrong.append(f"Room {room} at {slot_label(day, block)}: {reason} ({crns})")
    if wrong:
        return problems(
            "fail",
            f"Found {plural(len(wrong), 'exam')} breaking the large-only room rule.",
            wrong,
        )
    return passed(
        f"Only exams larger than every other room are in large-only room "
        f"{marked[0]}, and none are seated elsewhere."
    )


def unscheduled_had_no_room(ctx: ValidationContext) -> CheckResult:
    files = ctx.files()
    if files.blockouts_uploaded and files.blockouts is None:
        raise CheckSkippedError(unreadable_summary("room_blockouts"))
    blockouts = files.blockouts or {}
    rooms = _rooms_by_name(ctx)
    marked, cutoff = _large_only_rule(rooms)

    # Unscheduled exams that need one room: lone sections and combined groups
    # outside common groups (a common group needs several rooms at once).
    units: dict[str, list[ScheduleRow]] = defaultdict(list)
    for row in ctx.snapshot.rows:
        if not row.placed and row.crn not in ctx.common_label_by_crn:
            units[ctx.exam_unit(row.crn)].append(row)
    if not units:
        return passed("No unscheduled section or combined group to check.")

    occupied = set(_roomed_rows_by_slot(ctx))
    by_size = sorted(rooms.values(), key=lambda room: (room.capacity, room.name))
    slots = [
        (day, block)
        for day in range(ctx.params.max_days)
        for block in range(ctx.params.blocks_per_day)
    ]
    seatable: list[str] = []
    for unit, unit_rows in sorted(units.items()):
        size = sum(ctx.enrollment_of(row) for row in unit_rows)
        if size <= 0:
            continue  # excluded for zero enrollment, not for lack of a room
        allowed = [
            room
            for room in by_size
            if room.capacity >= size and (room.name in marked) == (size > cutoff)
        ]
        free = next(
            (
                (room, day, block)
                for day, block in slots
                for room in allowed
                if (room.name, day, block) not in occupied
                and (day, block) not in blockouts.get(room.name, frozenset())
            ),
            None,
        )
        if free is not None:
            room, day, block = free
            seatable.append(
                f"{unit_label(unit)} ({plural(size, 'student')}): {room.name} "
                f"({room.capacity} seats) was free at {slot_label(day, block)}"
            )
    if seatable:
        return problems(
            "warn",
            f"Found {plural(len(seatable), 'unscheduled exam')} that a free room "
            "could have seated.",
            seatable,
        )
    return passed(
        f"Checked {plural(len(units), 'unscheduled exam')}: none had a free room "
        "it was allowed to use in any block."
    )


def no_double_booking(ctx: ValidationContext) -> CheckResult:
    shared: list[str] = []
    for (room, day, block), rows in sorted(_roomed_rows_by_slot(ctx).items()):
        units = sorted({ctx.exam_unit(row.crn) for row in rows})
        if len(units) > 1:
            shared.append(
                f"Room {room} at {slot_label(day, block)}: "
                + ", ".join(unit_label(unit) for unit in units)
            )
    if shared:
        return problems(
            "fail",
            f"Found {plural(len(shared), 'room')} holding more than one exam at "
            "the same time.",
            shared,
        )
    return passed("No room holds more than one exam at a time.")


def blockouts(ctx: ValidationContext) -> CheckResult:
    blocked = ctx.blockouts()
    hits = sorted(
        f"CRN {row.crn} in {row.room} at {slot_label(*row.slot)}, which is blocked"
        for row in ctx.placed_rows
        if row.room is not None and row.slot in blocked.get(row.room, frozenset())
    )
    if hits:
        return problems(
            "fail",
            f"Found {plural(len(hits), 'exam')} in a room during its blockout.",
            hits,
        )
    return passed("No exam is in a room while it is blocked out.")


def _crn(row: ScheduleRow) -> str:
    return row.crn
