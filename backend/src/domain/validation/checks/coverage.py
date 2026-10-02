"""Coverage: every course has exactly one exam, placed inside the exam window."""

from collections import Counter

from src.domain.validation.context import ValidationContext, slot_label
from src.domain.validation.results import CheckResult, passed, plural, problems


def crn_single_row(ctx: ValidationContext) -> CheckResult:
    counts = Counter(row.crn for row in ctx.snapshot.rows)
    repeated = sorted(crn for crn, n in counts.items() if n > 1)
    if repeated:
        return problems(
            "fail",
            f"Found {plural(len(repeated), 'CRN')} with more than one schedule row.",
            [f"CRN {crn} appears {counts[crn]} times" for crn in repeated],
        )
    return passed(f"Each of the {len(counts)} scheduled CRNs has exactly one row.")


def crn_in_courses_file(ctx: ValidationContext) -> CheckResult:
    known = ctx.course_by_crn
    unknown = sorted({row.crn for row in ctx.snapshot.rows} - known.keys())
    if unknown:
        return problems(
            "fail",
            f"Found {plural(len(unknown), 'scheduled CRN')} not in the courses file.",
            [f"CRN {crn} is not in the courses file" for crn in unknown],
        )
    return passed("Every scheduled CRN is in the courses file.")


def crn_accounted(ctx: ValidationContext) -> CheckResult:
    courses = ctx.course_by_crn
    placed = ctx.placements.keys()
    with_reason = ctx.unscheduled_crns_with_reason
    has_reasons = ctx.snapshot.analysis is not None

    n_placed = n_unscheduled = n_zero = 0
    missing: list[str] = []
    unexplained: list[str] = []
    no_analysis: list[str] = []
    for crn in sorted(courses):
        if crn in placed:
            n_placed += 1
        elif crn in ctx.rows_by_crn:
            if crn in with_reason:
                n_unscheduled += 1
            elif not has_reasons:
                no_analysis.append(f"CRN {crn} is unscheduled")
            else:
                unexplained.append(
                    f"CRN {crn} is unscheduled but no unscheduled group gives a reason"
                )
        elif crn in ctx.zero_enrollment_crns:
            n_zero += 1
        else:
            enrollment = courses[crn].total_enrollment
            missing.append(
                f"CRN {crn} ({enrollment} students) is missing from the schedule"
            )

    if missing or unexplained:
        return problems(
            "fail",
            f"Found {plural(len(missing), 'CRN')} missing from the schedule and "
            f"{len(unexplained)} unscheduled without a reason.",
            missing + unexplained,
        )
    if no_analysis:
        return problems(
            "warn",
            f"Found {plural(len(no_analysis), 'unscheduled CRN')}; this schedule "
            "has no stored conflict analysis to give their reasons.",
            no_analysis,
        )
    return passed(
        f"All {len(courses)} CRNs are accounted for: {n_placed} placed, "
        f"{n_unscheduled} in unscheduled groups, {n_zero} excluded for zero "
        "enrollment."
    )


def exams_have_rooms(ctx: ValidationContext) -> CheckResult:
    unroomed = sorted(
        (row for row in ctx.placed_rows if row.room is None), key=lambda r: r.crn
    )
    if unroomed:
        return problems(
            "warn",
            f"Found {plural(len(unroomed), 'placed exam')} without a room; the "
            "schedule statistics report these as unplaced.",
            [
                f"CRN {row.crn} at {slot_label(*row.slot)} has no room"
                for row in unroomed
            ],
        )
    return passed(f"All {len(ctx.placed_rows)} placed exams have a room.")


def within_window(ctx: ValidationContext) -> CheckResult:
    params = ctx.params
    outside = sorted(
        (
            row
            for row in ctx.placed_rows
            if not 0 <= row.slot[0] < params.max_days
            or not 0 <= row.slot[1] < params.blocks_per_day
        ),
        key=lambda r: r.crn,
    )
    window = (
        f"{plural(params.max_days, 'day')} x {plural(params.blocks_per_day, 'block')}"
    )
    if outside:
        return problems(
            "fail",
            f"Found {plural(len(outside), 'exam')} outside the {window} exam window.",
            [f"CRN {row.crn} at {slot_label(*row.slot)}" for row in outside],
        )
    return passed(f"All placed exams fall inside the {window} exam window.")
