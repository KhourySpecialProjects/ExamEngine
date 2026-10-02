"""Rooms: real rooms, enough seats, one exam per room per slot, no blockouts."""

from collections import defaultdict

from src.domain.validation.context import ValidationContext, slot_label, unit_label
from src.domain.validation.results import CheckResult, passed, plural, problems
from src.domain.validation.snapshot import ScheduleRow


def _roomed_rows_by_slot(
    ctx: ValidationContext,
) -> dict[tuple[str, int, int], list[ScheduleRow]]:
    """(room, day, block) -> placed rows seated there."""
    seated: dict[tuple[str, int, int], list[ScheduleRow]] = defaultdict(list)
    for row in ctx.placed_rows:
        if row.room is not None:
            seated[(row.room, *row.slot)].append(row)
    return seated


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
