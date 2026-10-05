"""Coverage: every course has exactly one exam, placed inside the exam window."""

from collections import Counter
from collections.abc import Mapping

from src.domain.validation.context import (
    LateAdditionEntry,
    ValidationContext,
    crn_list,
    slot_label,
)
from src.domain.validation.results import (
    CheckResult,
    CheckSkippedError,
    passed,
    plural,
    problems,
)
from src.domain.validation.snapshot import CourseRecord


NO_LATE_ADDITIONS = "This schedule has no late additions."


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
    known = ctx.file_course_by_crn
    late = ctx.late_addition_by_crn
    outside_file = {row.crn for row in ctx.snapshot.rows} - known.keys()
    unknown = sorted(outside_file - late.keys())
    if unknown:
        return problems(
            "fail",
            f"Found {plural(len(unknown), 'scheduled CRN')} not in the courses file.",
            [f"CRN {crn} is not in the courses file" for crn in unknown],
        )
    late_added = outside_file & late.keys()
    if late_added:
        return passed(
            "Every scheduled CRN is in the courses file, except "
            f"{plural(len(late_added), 'late add')} ({crn_list(late_added)})."
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
    source = " (courses file and late additions)" if ctx.late_course_crns else ""
    return passed(
        f"All {len(courses)} CRNs{source} are accounted for: {n_placed} placed, "
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


def late_additions(ctx: ValidationContext) -> CheckResult:
    entries, malformed = ctx.late_addition_entries
    if not entries and not malformed:
        raise CheckSkippedError(NO_LATE_ADDITIONS)
    file_courses = ctx.file_course_by_crn
    students = ctx.students_by_crn

    found = list(malformed)
    repeated = Counter(entry.crn for entry in entries)
    found += [
        f"CRN {crn} is recorded as a late addition {n} times"
        for crn, n in sorted(repeated.items())
        if n > 1
    ]
    for entry in sorted(ctx.late_addition_by_crn.values(), key=lambda e: e.crn):
        found += _late_addition_problems(ctx, entry, file_courses, students)

    if found:
        return problems(
            "fail",
            f"Found {plural(len(found), 'problem')} with the recorded late additions.",
            found,
        )
    return passed(
        f"All {plural(len(entries), 'late addition')} are placed where recorded, "
        "are not scheduled courses in the courses file, and match their "
        "enrollments and stored course rows."
    )


def _late_addition_problems(
    ctx: ValidationContext,
    entry: LateAdditionEntry,
    file_courses: Mapping[str, CourseRecord],
    students: Mapping[str, set[str]],
) -> list[str]:
    crn = f"CRN {entry.crn}"
    found: list[str] = []
    recorded = f"{slot_label(entry.day, entry.block)} in {entry.room}"
    rows = ctx.rows_by_crn.get(entry.crn, [])
    if len(rows) != 1:
        found.append(
            f"{crn} should appear once at {recorded} but has "
            f"{plural(len(rows), 'schedule row')}"
        )
    else:
        row = rows[0]
        if (row.day_index, row.block_index, row.room) != (
            entry.day,
            entry.block,
            entry.room,
        ):
            actual = (
                f"{slot_label(*row.slot)} in {row.room or 'no room'}"
                if row.placed
                else "unplaced"
            )
            found.append(f"{crn} is recorded at {recorded} but is {actual}")
        stored = []
        if (row.course_code or "") != entry.course_code:
            stored.append(
                f"course code '{row.course_code or ''}' stored, "
                f"'{entry.course_code}' recorded"
            )
        if (row.instructor or "").strip() != (entry.instructor or ""):
            stored.append(
                f"instructor '{row.instructor or ''}' stored, "
                f"'{entry.instructor or ''}' recorded"
            )
        if row.enrollment_count != entry.size:
            stored.append(f"size {row.enrollment_count} stored, {entry.size} recorded")
        if stored:
            found.append(f"{crn}: " + "; ".join(stored))

    course = file_courses.get(entry.crn)
    if course is not None and course.total_enrollment:
        found.append(
            f"{crn} is a scheduled course in the courses file "
            f"({course.total_enrollment} students), not a late addition"
        )
    enrolled = len(students.get(entry.crn, ()))
    if not enrolled:
        found.append(f"{crn} has no enrollment rows")
    elif enrolled != entry.size:
        found.append(
            f"{crn} is recorded with size {entry.size} but has "
            f"{plural(enrolled, 'enrolled student')}"
        )
    return found
