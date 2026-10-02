"""Data consistency: stored data against the files, and the files themselves."""

from collections import Counter
from collections.abc import Mapping
from typing import Any

from src.domain.validation.context import ValidationContext
from src.domain.validation.results import CheckResult, passed, plural, problems


_HARD_TYPES = (
    "student_double_book",
    "instructor_double_book",
    "student_gt_max_per_day",
    "instructor_gt_max_per_day",
)
_SOFT_TYPES = (
    "back_to_back_students",
    "back_to_back_instructors",
    "large_courses_not_early",
)


def stored_course_matches_file(ctx: ValidationContext) -> CheckResult:
    courses = ctx.course_by_crn
    mismatches: list[str] = []
    seen: set[str] = set()
    for row in sorted(ctx.snapshot.rows, key=lambda r: r.crn):
        course = courses.get(row.crn)
        if course is None or row.crn in seen:
            continue
        seen.add(row.crn)
        parts = []
        if row.enrollment_count != course.total_enrollment:
            parts.append(
                f"enrollment {row.enrollment_count} stored, "
                f"{course.total_enrollment} in file"
            )
        # The app stores the file's instructor cell as-is (never split on ';').
        if (row.instructor or "") != (course.instructor or ""):
            parts.append(
                f"instructor '{row.instructor or ''}' stored, "
                f"'{course.instructor or ''}' in file"
            )
        if parts:
            mismatches.append(f"CRN {row.crn}: " + "; ".join(parts))
    if mismatches:
        return problems(
            "fail",
            f"Found {plural(len(mismatches), 'scheduled course')} whose stored "
            "enrollment or instructor differs from the courses file.",
            mismatches,
        )
    return passed(
        f"Stored enrollment and instructor match the courses file for all "
        f"{plural(len(seen), 'scheduled course')}."
    )


def _list_len(section: Any, name: str) -> int | None:
    if not isinstance(section, Mapping):
        return None
    entries = section.get(name, [])
    return len(entries) if isinstance(entries, list) else None


def _total(lengths: list[int | None]) -> int | None:
    """Sum of list lengths, or None if any list is unreadable."""
    if any(n is None for n in lengths):
        return None
    return sum(n for n in lengths if n is not None)


def stored_statistics(ctx: ValidationContext) -> CheckResult:
    analysis = ctx.analysis()
    stats = analysis.get("statistics")
    if not isinstance(stats, Mapping):
        return problems("fail", "The stored analysis has no statistics.", [], count=1)

    hard, soft = analysis.get("hard_conflicts"), analysis.get("soft_conflicts")
    expected: dict[str, int | None] = {}
    for section, names in ((hard, _HARD_TYPES), (soft, _SOFT_TYPES)):
        for name in names:
            expected[f"{name}_count"] = _list_len(section, name)
    expected["total_hard_conflicts"] = _total(
        [_list_len(hard, name) for name in _HARD_TYPES]
    )
    expected["total_soft_conflicts"] = _total(
        [_list_len(soft, name) for name in _SOFT_TYPES]
    )
    # Generation counts every exam with a time slot (unroomed ones included).
    placed = ctx.placed_rows
    expected["num_classes"] = len(ctx.placements)
    expected["slots_used"] = len({row.slot for row in placed})
    expected["num_rooms"] = len({row.room for row in placed if row.room is not None})

    mismatches = [
        f"{key}: stored {stats[key]!r}, expected {value}"
        for key, value in expected.items()
        if value is not None and key in stats and stats[key] != value
    ]
    checked = sum(
        1 for key, value in expected.items() if value is not None and key in stats
    )
    if mismatches:
        return problems(
            "fail",
            f"Found {plural(len(mismatches), 'stored statistic')} that disagree "
            "with the stored conflicts or the schedule.",
            mismatches,
        )
    return passed(
        f"All {plural(checked, 'stored statistic')} agree with the stored "
        "conflicts and the schedule."
    )


def enrollment_totals(ctx: ValidationContext) -> CheckResult:
    students = ctx.students_by_crn
    differences: list[tuple[int, str, str]] = []
    for crn, course in ctx.course_by_crn.items():
        total = course.total_enrollment or 0
        actual = len(students.get(crn, ()))
        if total != actual:
            differences.append(
                (
                    -abs(total - actual),
                    crn,
                    f"CRN {crn}: Total_Enrollment {total}, "
                    f"{plural(actual, 'student')} enrolled",
                )
            )
    if differences:
        return problems(
            "warn",
            f"Found {plural(len(differences), 'course')} whose Total_Enrollment "
            "differs from the number of students enrolled.",
            [text for *_, text in sorted(differences)],
        )
    return passed("Every course's Total_Enrollment matches its enrolled students.")


def enrollment_unknown_crns(ctx: ValidationContext) -> CheckResult:
    known = ctx.course_by_crn.keys()
    unknown = Counter(
        enrollment.crn
        for enrollment in ctx.enrollments()
        if enrollment.crn not in known
    )
    if unknown:
        rows = sum(unknown.values())
        return problems(
            "warn",
            f"Found {plural(rows, 'enrollment row')} for "
            f"{plural(len(unknown), 'CRN')} not in the courses file.",
            [
                f"CRN {crn}: {plural(n, 'enrollment row')}"
                for crn, n in sorted(unknown.items(), key=lambda kv: (-kv[1], kv[0]))
            ],
            count=rows,
        )
    return passed("Every enrollment row is for a CRN in the courses file.")


def duplicates(ctx: ValidationContext) -> CheckResult:
    crn_counts = Counter(course.crn for course in ctx.courses())
    pair_counts = Counter(
        (enrollment.student_id, enrollment.crn) for enrollment in ctx.enrollments()
    )
    repeated_crns = sorted(crn for crn, n in crn_counts.items() if n > 1)
    repeated_pairs = sorted(pair for pair, n in pair_counts.items() if n > 1)
    if repeated_crns or repeated_pairs:
        return problems(
            "warn",
            f"Found {plural(len(repeated_crns), 'CRN')} repeated in the courses "
            f"file and {plural(len(repeated_pairs), 'enrollment')} repeated in the "
            "enrollments file.",
            [
                f"CRN {crn} appears {crn_counts[crn]} times in the courses file"
                for crn in repeated_crns
            ]
            + [
                f"Student {student} is enrolled in CRN {crn} "
                f"{pair_counts[(student, crn)]} times"
                for student, crn in repeated_pairs
            ],
        )
    return passed("No duplicate courses or enrollments.")
