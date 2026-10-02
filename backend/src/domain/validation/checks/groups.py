"""Combined and common groups: kept together, or listed as unscheduled."""

from collections import defaultdict
from collections.abc import Iterable

from src.domain.validation.context import (
    ValidationContext,
    crn_list,
    slot_label,
    unit_label,
)
from src.domain.validation.results import (
    CheckResult,
    CheckSkipped,
    passed,
    plural,
    problems,
    skipped,
)
from src.domain.validation.snapshot import ScheduleRow


def _placement_text(row: ScheduleRow) -> str:
    if not row.placed:
        return f"CRN {row.crn} has no time slot"
    room = row.room or "no room"
    return f"CRN {row.crn} at {slot_label(*row.slot)} in {room}"


def _scheduled_rows(ctx: ValidationContext, crns: Iterable[str]) -> list[ScheduleRow]:
    """Schedule rows of the group members that are in the schedule at all."""
    return [row for crn in sorted(crns) for row in ctx.rows_by_crn.get(crn, [])]


def combined_together(ctx: ValidationContext) -> CheckResult:
    groups = ctx.snapshot.combined_groups
    if not groups:
        return skipped("This dataset has no combined exam groups.")

    split: list[str] = []
    checked = 0
    for label in sorted(groups):
        if ctx.combined_group_listed_unscheduled(label):
            continue
        rows = _scheduled_rows(ctx, groups[label])
        if not rows:
            continue
        checked += 1
        placements = {(row.day_index, row.block_index, row.room) for row in rows}
        if len(placements) > 1 or not rows[0].placed:
            split.append(
                f"Combined group '{label}': "
                + "; ".join(_placement_text(row) for row in rows)
            )
    if split:
        return problems(
            "fail",
            f"Found {plural(len(split), 'combined group')} not sharing one time "
            "slot and room.",
            split,
        )
    return passed(
        f"Checked {plural(checked, 'scheduled combined group')}: each shares one "
        "time slot and room."
    )


def common_same_slot(ctx: ValidationContext) -> CheckResult:
    groups = ctx.common_group_crns
    if not groups:
        return skipped("This dataset has no common exam groups.")

    broken: list[str] = []
    checked = 0
    for label in sorted(groups):
        if ctx.common_group_listed_unscheduled(label):
            continue
        rows = _scheduled_rows(ctx, groups[label])
        if not rows:
            continue
        checked += 1
        slots = {(row.day_index, row.block_index) for row in rows}
        if len(slots) > 1 or not rows[0].placed:
            broken.append(
                f"Common group '{label}' is split: "
                + "; ".join(_placement_text(row) for row in rows)
            )
            continue

        units_by_room: dict[str, set[str]] = defaultdict(set)
        for row in rows:
            if row.room is not None:
                units_by_room[row.room].add(ctx.exam_unit(row.crn))
        for room in sorted(units_by_room):
            units = units_by_room[room]
            if len(units) > 1:
                broken.append(
                    f"Common group '{label}' shares room {room}: "
                    + ", ".join(unit_label(unit) for unit in sorted(units))
                )
    if broken:
        return problems(
            "fail",
            f"Found {plural(len(broken), 'common group problem')}: split across "
            "time slots or sections sharing a room.",
            broken,
        )
    return passed(
        f"Checked {plural(checked, 'scheduled common group')}: each shares one "
        "time slot, its exams in distinct rooms."
    )


def unscheduled_consistent(ctx: ValidationContext) -> CheckResult:
    entries, malformed = ctx.unscheduled_entries
    if not entries and not malformed:
        return passed("No groups are listed as unscheduled.")

    issues = list(malformed)
    in_schedule = set(ctx.rows_by_crn)
    try:
        in_schedule |= set(ctx.course_by_crn) - ctx.zero_enrollment_crns
    except CheckSkipped:
        pass  # Without the courses file, the schedule rows define what exists.

    seen: set[tuple[str, str]] = set()
    for entry in entries:
        name = f"Unscheduled {entry.kind} group '{entry.label}'"
        if (entry.kind, entry.label) in seen:
            issues.append(f"{name} is listed more than once")
        seen.add((entry.kind, entry.label))

        if entry.kind == "combined":
            members = ctx.snapshot.combined_groups.get(entry.label)
        elif entry.kind == "common":
            members = ctx.common_group_crns.get(entry.label)
        else:
            issues.append(f"{name}: unknown kind")
            continue
        if members is None:
            issues.append(f"{name} is not a {entry.kind} group of this dataset")
        else:
            expected = set(members) & in_schedule
            if entry.crns != expected:
                extra, absent = entry.crns - expected, expected - entry.crns
                parts = []
                if extra:
                    parts.append(f"lists {crn_list(extra)} not in the group")
                if absent:
                    parts.append(f"omits {crn_list(absent)}")
                issues.append(f"{name} {' and '.join(parts)}")
        if not entry.reason:
            issues.append(f"{name} has no reason")
        placed = sorted(crn for crn in entry.crns if crn in ctx.placements)
        if placed:
            issues.append(f"{name} has placed exams: {crn_list(placed)}")

    if issues:
        return problems(
            "fail",
            f"Found {plural(len(issues), 'problem')} with the groups listed as "
            "unscheduled.",
            issues,
        )
    return passed(
        f"Checked {plural(len(entries), 'unscheduled group')}: each matches the "
        "dataset, gives a reason and has no placed exams."
    )
