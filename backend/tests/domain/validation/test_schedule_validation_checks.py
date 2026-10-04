"""Schedule validation checks against small hand-built snapshots."""

from dataclasses import replace

import pytest

from src.domain.validation import (
    CHECKS,
    Check,
    CheckFinished,
    CheckStarted,
    CourseRecord,
    DatasetFiles,
    EnrollmentRecord,
    RoomRecord,
    RunParameters,
    ScheduleRow,
    ValidationSnapshot,
    parse_dataset_files,
    run_check,
    run_checks,
)
from src.domain.validation.context import ValidationContext
from src.domain.validation.snapshot import late_additions_from_stored


CHECK_BY_ID = {check.id: check for check in CHECKS}
FILES_GONE = "The dataset's uploaded files are no longer available."


# Baseline: a schedule that agrees with its files and stored analysis.
#   CRN 100 (Ada, 2 students) Monday block 0 in R1
#   CRN 200 (Bob, 2 students) Tuesday block 0 in R1
#   CRN 300 (Ada, 1 student)  Monday block 2 in R2
#   CRN 400 has zero enrollment and is not scheduled.
# Student 001234567 takes 100 and 200.


def row(
    crn: str,
    day: int | None = 0,
    block: int | None = 0,
    room: str | None = "R1",
    capacity: int | None = 10,
    enrollment: int = 2,
    instructor: str | None = "Ada",
    course_code: str | None = None,
) -> ScheduleRow:
    return ScheduleRow(
        crn=crn,
        day_index=day,
        block_index=block,
        room=room,
        room_capacity=capacity if room is not None else None,
        enrollment_count=enrollment,
        instructor=instructor,
        course_code=course_code,
    )


def course(crn: str, total: int | None, instructor: str | None) -> CourseRecord:
    return CourseRecord(crn=crn, total_enrollment=total, instructor=instructor)


def enrolled(student: str, crn: str) -> EnrollmentRecord:
    return EnrollmentRecord(student_id=student, crn=crn)


BASE_ROWS = (
    row("100", 0, 0, "R1", enrollment=2, instructor="Ada"),
    row("200", 1, 0, "R1", enrollment=2, instructor="Bob"),
    row("300", 0, 2, "R2", enrollment=1, instructor="Ada"),
)
BASE_FILES = DatasetFiles(
    courses=(
        course("100", 2, "Ada"),
        course("200", 2, "Bob"),
        course("300", 1, "Ada"),
        course("400", 0, "Cy"),
    ),
    enrollments=(
        enrolled("001234567", "100"),
        enrolled("s2", "100"),
        enrolled("001234567", "200"),
        enrolled("s3", "200"),
        enrolled("s4", "300"),
    ),
    rooms=(RoomRecord("R1", 10), RoomRecord("R2", 10)),
    blockouts=None,
    blockouts_uploaded=False,
)


def analysis(
    hard: dict | None = None,
    soft: dict | None = None,
    unscheduled: list | None = None,
    **stats: int,
) -> dict:
    hard_lists = {
        "student_double_book": [],
        "instructor_double_book": [],
        "student_gt_max_per_day": [],
        "instructor_gt_max_per_day": [],
        **(hard or {}),
    }
    soft_lists = {
        "back_to_back_students": [],
        "back_to_back_instructors": [],
        "large_courses_not_early": [],
        **(soft or {}),
    }
    statistics = {
        "num_classes": 3,
        "num_students": 4,
        "num_rooms": 2,
        "slots_used": 3,
        "unplaced_exams": 0,
        "total_hard_conflicts": sum(len(v) for v in hard_lists.values()),
        "total_soft_conflicts": sum(len(v) for v in soft_lists.values()),
        **{f"{name}_count": len(v) for name, v in hard_lists.items()},
        **{f"{name}_count": len(v) for name, v in soft_lists.items()},
        **stats,
    }
    return {
        "hard_conflicts": hard_lists,
        "soft_conflicts": soft_lists,
        "statistics": statistics,
        "unscheduled_groups": unscheduled or [],
    }


def snapshot(**changes) -> ValidationSnapshot:
    base = ValidationSnapshot(
        rows=BASE_ROWS,
        parameters=RunParameters(),
        analysis=analysis(),
        combined_groups={},
        common_groups={},
        files=BASE_FILES,
    )
    return replace(base, **changes)


def files(**changes) -> DatasetFiles:
    return replace(BASE_FILES, **changes)


def rows(*replacements: ScheduleRow, drop: tuple[str, ...] = ()) -> tuple:
    """Baseline rows with rows of the same CRN replaced, others appended."""
    by_crn = {r.crn: r for r in replacements}
    kept = [by_crn.pop(r.crn, r) for r in BASE_ROWS if r.crn not in drop]
    return (*kept, *by_crn.values())


def run(check_id: str, snap: ValidationSnapshot):
    return run_check(CHECK_BY_ID[check_id], ValidationContext(snap))


# ----------------------------------------------------------------------
# Catalog and runner
# ----------------------------------------------------------------------


def test_consistent_schedule_passes_every_applicable_check():
    results = {
        check.id: run_check(check, ValidationContext(snapshot())) for check in CHECKS
    }

    not_passing = {cid: r.status for cid, r in results.items() if r.status != "pass"}
    assert not_passing == {
        "coverage.late_additions": "skipped",
        "rooms.blockouts": "skipped",
        "groups.combined_together": "skipped",
        "groups.common_same_slot": "skipped",
    }
    assert all(r.count == 0 and not r.examples for r in results.values())


def test_run_checks_starts_then_finishes_each_check_and_survives_a_crash():
    def crash(ctx):
        raise RuntimeError("boom")

    checks = (
        Check("a.crash", "Crash", "Raises.", "data", crash),
        CHECK_BY_ID["coverage.crn_single_row"],
    )

    events = list(run_checks(snapshot(), checks))

    assert [(type(e), e.check.id) for e in events] == [
        (CheckStarted, "a.crash"),
        (CheckFinished, "a.crash"),
        (CheckStarted, "coverage.crn_single_row"),
        (CheckFinished, "coverage.crn_single_row"),
    ]
    crashed = events[1].result
    assert crashed.status == "fail"
    assert crashed.summary == "Check crashed: RuntimeError"
    assert isinstance(crashed.error, RuntimeError)
    assert events[3].result.status == "pass"


FILE_CHECKS = [
    check.id
    for check in CHECKS
    if check.id
    not in {
        "coverage.crn_single_row",
        "coverage.late_additions",
        "coverage.exams_have_rooms",
        "coverage.within_window",
        "rooms.capacity",
        "rooms.no_double_booking",
        "groups.combined_together",
        "groups.common_same_slot",
        "groups.unscheduled_consistent",
        "data.stored_statistics",
    }
]


@pytest.mark.parametrize("check_id", FILE_CHECKS)
def test_file_checks_skip_when_files_are_gone(check_id):
    result = run(check_id, snapshot(files=None))

    assert result.status == "skipped"
    assert result.summary == FILES_GONE


def test_check_needing_an_unreadable_file_names_it():
    snap = snapshot(files=files(courses=None, unreadable=frozenset({"courses"})))

    result = run("coverage.crn_in_courses_file", snap)

    assert result.status == "skipped"
    assert result.summary == "The uploaded courses file could not be read."
    # Checks that don't need the courses file still run.
    assert run("conflicts.student_double_book", snap).status == "pass"


def test_examples_are_capped_but_count_is_complete():
    many = tuple(row(str(1000 + i), room=None) for i in range(25))

    result = run("coverage.exams_have_rooms", snapshot(rows=many))

    assert result.status == "warn"
    assert result.count == 25
    assert len(result.examples) == 20


# ----------------------------------------------------------------------
# Coverage
# ----------------------------------------------------------------------


def test_crn_with_two_rows_fails():
    snap = snapshot(rows=(*BASE_ROWS, row("100", 3, 1, "R2")))

    result = run("coverage.crn_single_row", snap)

    assert result.status == "fail"
    assert result.examples == ("CRN 100 appears 2 times",)


def test_scheduled_crn_missing_from_courses_file_fails():
    result = run("coverage.crn_in_courses_file", snapshot(rows=rows(row("999"))))

    assert result.status == "fail"
    assert result.examples == ("CRN 999 is not in the courses file",)


def test_crn_accounted_reports_breakdown():
    result = run("coverage.crn_accounted", snapshot())

    assert result.status == "pass"
    assert "3 placed, 0 in unscheduled groups, 1 excluded" in result.summary


def test_course_missing_from_schedule_fails():
    result = run("coverage.crn_accounted", snapshot(rows=rows(drop=("300",))))

    assert result.status == "fail"
    assert result.examples == ("CRN 300 (1 students) is missing from the schedule",)


def test_unscheduled_course_needs_a_listed_reason():
    unplaced = rows(row("300", None, None, None))
    no_reason = snapshot(rows=unplaced)
    with_reason = snapshot(
        rows=unplaced,
        analysis=analysis(
            unscheduled=[
                {"kind": "combined", "group": "G", "reason": "Too big", "crns": ["300"]}
            ]
        ),
    )

    assert run("coverage.crn_accounted", no_reason).status == "fail"
    result = run("coverage.crn_accounted", with_reason)
    assert result.status == "pass"
    assert "2 placed, 1 in unscheduled groups" in result.summary


def test_placed_exam_without_room_warns():
    result = run(
        "coverage.exams_have_rooms", snapshot(rows=rows(row("300", 0, 2, None)))
    )

    assert result.status == "warn"
    assert result.examples == ("CRN 300 at Monday 2PM-4PM has no room",)


def test_exam_outside_window_fails():
    params = RunParameters(max_days=5, blocks_per_day=4)

    late_day = run(
        "coverage.within_window",
        snapshot(rows=rows(row("300", 5, 0)), parameters=params),
    )
    late_block = run(
        "coverage.within_window",
        snapshot(rows=rows(row("300", 0, 4)), parameters=params),
    )
    last_slot = run(
        "coverage.within_window",
        snapshot(rows=rows(row("300", 4, 3)), parameters=params),
    )

    assert late_day.status == late_block.status == "fail"
    assert late_block.examples == ("CRN 300 at Monday 7PM-9PM",)
    assert last_slot.status == "pass"


# ----------------------------------------------------------------------
# Rooms
# ----------------------------------------------------------------------


def test_room_not_in_file_or_with_other_capacity_fails():
    snap = snapshot(
        rows=rows(row("200", 1, 0, "R9"), row("300", 0, 2, "R2", capacity=99))
    )

    result = run("rooms.in_rooms_file", snap)

    assert result.status == "fail"
    assert result.examples == (
        "Room R2: stored capacity 99, rooms file 10",
        "Room R9 is not in the rooms file",
    )


def test_over_capacity_room_fails_using_file_values():
    snap = snapshot(files=files(rooms=(RoomRecord("R1", 1), RoomRecord("R2", 10))))

    result = run("rooms.capacity", snap)

    assert result.status == "fail"
    assert result.count == 2
    assert result.examples[0] == (
        "Room R1 at Monday 9AM-11AM: 2 students, capacity 1 (CRN 100)"
    )


def test_capacity_uses_stored_values_without_files():
    fits = snapshot(files=None)
    overfull = snapshot(files=None, rows=rows(row("300", 0, 2, "R2", capacity=1)))

    assert run("rooms.capacity", fits).status == "pass"
    assert run("rooms.capacity", overfull).status == "fail"


def test_two_exams_in_one_room_at_once_fail_but_one_combined_exam_does_not():
    shared = rows(row("300", 0, 0, "R1", enrollment=1))

    separate = run("rooms.no_double_booking", snapshot(rows=shared))
    combined = run(
        "rooms.no_double_booking",
        snapshot(rows=shared, combined_groups={"G": ("100", "300")}),
    )

    assert separate.status == "fail"
    assert separate.examples == ("Room R1 at Monday 9AM-11AM: CRN 100, CRN 300",)
    assert combined.status == "pass"


def test_exam_in_blocked_room_fails():
    blocked = files(blockouts={"R1": frozenset({(0, 0)})}, blockouts_uploaded=True)
    elsewhere = files(blockouts={"R1": frozenset({(0, 1)})}, blockouts_uploaded=True)

    result = run("rooms.blockouts", snapshot(files=blocked))

    assert result.status == "fail"
    assert result.examples == ("CRN 100 in R1 at Monday 9AM-11AM, which is blocked",)
    assert run("rooms.blockouts", snapshot(files=elsewhere)).status == "pass"


def test_blockouts_skip_without_a_blockout_file():
    result = run("rooms.blockouts", snapshot())

    assert result.status == "skipped"
    assert result.summary == "No room blockout file was uploaded."


# ----------------------------------------------------------------------
# Groups
# ----------------------------------------------------------------------


def test_combined_group_must_share_slot_and_room():
    group = {"G": ("100", "200")}
    split = snapshot(combined_groups=group)
    together = snapshot(combined_groups=group, rows=rows(row("200", 0, 0, "R1")))

    result = run("groups.combined_together", split)

    assert result.status == "fail"
    assert result.examples == (
        "Combined group 'G': CRN 100 at Monday 9AM-11AM in R1; "
        "CRN 200 at Tuesday 9AM-11AM in R1",
    )
    assert run("groups.combined_together", together).status == "pass"


def test_combined_group_listed_unscheduled_is_not_required_together():
    snap = snapshot(
        combined_groups={"G": ("100", "200")},
        rows=rows(row("100", None, None, None), row("200", None, None, None)),
        analysis=analysis(
            unscheduled=[
                {
                    "kind": "combined",
                    "group": "G",
                    "reason": "No room",
                    "crns": ["100", "200"],
                }
            ]
        ),
    )

    assert run("groups.combined_together", snap).status == "pass"
    assert run("groups.unscheduled_consistent", snap).status == "pass"


def test_common_group_must_share_slot_in_distinct_rooms():
    group = {"C": ("100", "300")}
    split = snapshot(common_groups=group)
    same_room = snapshot(common_groups=group, rows=rows(row("300", 0, 0, "R1")))
    ok = snapshot(common_groups=group, rows=rows(row("300", 0, 0, "R2")))

    assert run("groups.common_same_slot", split).status == "fail"
    shared = run("groups.common_same_slot", same_room)
    assert shared.status == "fail"
    assert shared.examples == ("Common group 'C' shares room R1: CRN 100, CRN 300",)
    assert run("groups.common_same_slot", ok).status == "pass"


def test_common_group_includes_whole_combined_groups_of_its_members():
    # Listing 200 brings its combined partner 300 into the common group.
    snap = snapshot(
        common_groups={"C": ("100", "200")},
        combined_groups={"G": ("200", "300")},
        rows=rows(row("200", 0, 0, "R2"), row("300", 1, 0, "R2")),
    )

    result = run("groups.common_same_slot", snap)

    assert result.status == "fail"
    assert "CRN 300 at Tuesday 9AM-11AM in R2" in result.examples[0]


def test_common_group_sections_of_one_combined_exam_may_share_a_room():
    snap = snapshot(
        common_groups={"C": ("100", "200", "300")},
        combined_groups={"G": ("200", "300")},
        rows=rows(row("200", 0, 0, "R2"), row("300", 0, 0, "R2")),
    )

    assert run("groups.common_same_slot", snap).status == "pass"


@pytest.mark.parametrize(
    ("entry", "problem"),
    [
        (
            {"kind": "common", "group": "C", "reason": "x", "crns": ["100", "200"]},
            "lists CRN 200 not in the group and omits CRN 300",
        ),
        (
            {"kind": "common", "group": "C", "reason": " ", "crns": ["100", "300"]},
            "has no reason",
        ),
        (
            {"kind": "common", "group": "Z", "reason": "x", "crns": ["100"]},
            "is not a common group of this dataset",
        ),
    ],
)
def test_inconsistent_unscheduled_group_fails(entry, problem):
    snap = snapshot(
        common_groups={"C": ("100", "300")},
        rows=rows(row("100", None, None, None), row("300", None, None, None)),
        analysis=analysis(unscheduled=[entry]),
    )

    result = run("groups.unscheduled_consistent", snap)

    assert result.status == "fail"
    assert any(problem in example for example in result.examples)


def test_unscheduled_group_with_placed_exam_fails():
    entry = {"kind": "combined", "group": "G", "reason": "x", "crns": ["100", "300"]}
    snap = snapshot(
        combined_groups={"G": ("100", "300")},
        rows=rows(row("100", None, None, None)),
        analysis=analysis(unscheduled=[entry]),
    )

    result = run("groups.unscheduled_consistent", snap)

    assert result.status == "fail"
    assert result.examples == (
        "Unscheduled combined group 'G' has placed exams: CRN 300",
    )


def _section(crn: str, crns: list[str] | None = None) -> dict:
    return {"kind": "section", "group": crn, "reason": "Too big", "crns": crns or [crn]}


def test_unscheduled_section_accounts_for_its_crn():
    snap = snapshot(
        rows=rows(row("300", None, None, None)),
        analysis=analysis(unscheduled=[_section("300")]),
    )

    assert run("groups.unscheduled_consistent", snap).status == "pass"
    accounted = run("coverage.crn_accounted", snap)
    assert accounted.status == "pass"
    assert "2 placed, 1 in unscheduled groups" in accounted.summary


@pytest.mark.parametrize(
    ("entry", "problem"),
    [
        (_section("300", ["300", "100"]), "lists CRN 100 not in the group"),
        (_section("999"), "is not a section of this dataset"),
        (_section("100"), "is in combined group 'G'"),
        (_section("200"), "has placed exams: CRN 200"),
    ],
)
def test_inconsistent_unscheduled_section_fails(entry, problem):
    snap = snapshot(
        combined_groups={"G": ("100", "300")},
        rows=rows(row("100", None, None, None), row("300", None, None, None)),
        analysis=analysis(unscheduled=[entry]),
    )

    result = run("groups.unscheduled_consistent", snap)

    assert result.status == "fail"
    assert any(problem in example for example in result.examples)


def test_group_checks_skip_without_groups():
    assert run("groups.combined_together", snapshot()).summary == (
        "This dataset has no combined exam groups."
    )
    assert run("groups.common_same_slot", snapshot()).status == "skipped"


# ----------------------------------------------------------------------
# Conflicts
# ----------------------------------------------------------------------


def _hard(entity: str, day: str, block: int) -> dict:
    return {"entity_id": entity, "day": day, "block": block, "crn": "x"}


def test_unreported_student_double_booking_fails():
    snap = snapshot(rows=rows(row("200", 0, 0, "R2")))

    result = run("conflicts.student_double_book", snap)

    assert result.status == "fail"
    assert result.examples == (
        "Missed: student 001234567, Monday 9AM-11AM: CRN 100, CRN 200",
    )


def test_reported_student_double_booking_warns():
    snap = snapshot(
        rows=rows(row("200", 0, 0, "R2")),
        analysis=analysis(
            hard={"student_double_book": [_hard("001234567", "Monday", 0)]}
        ),
    )

    result = run("conflicts.student_double_book", snap)

    assert result.status == "warn"
    assert result.count == 1


def test_invented_student_double_booking_fails():
    snap = snapshot(
        analysis=analysis(hard={"student_double_book": [_hard("s2", "Friday", 1)]})
    )

    result = run("conflicts.student_double_book", snap)

    assert result.status == "fail"
    assert result.examples == ("Not real: student s2, Friday 11:30AM-1:30PM",)


def test_combined_sections_at_one_time_are_not_a_double_booking():
    snap = snapshot(
        rows=rows(row("200", 0, 0, "R1")), combined_groups={"G": ("100", "200")}
    )

    assert run("conflicts.student_double_book", snap).status == "pass"


def test_unreadable_stored_conflict_entry_fails():
    snap = snapshot(
        analysis=analysis(hard={"student_double_book": [{"entity_id": "s2"}]})
    )

    result = run("conflicts.student_double_book", snap)

    assert result.status == "fail"
    assert result.examples == ("Unreadable stored student_double_book entry #1",)


def test_conflict_checks_skip_without_stored_analysis():
    result = run("conflicts.student_double_book", snapshot(analysis=None))

    assert result.status == "skipped"
    assert result.summary == "This schedule has no stored conflict analysis."


def test_instructor_double_booking_counts_time_groups():
    clash = rows(row("300", 0, 0, "R2"))

    missed = run("conflicts.instructor_double_book", snapshot(rows=clash))
    common = run(
        "conflicts.instructor_double_book",
        snapshot(rows=clash, common_groups={"C": ("100", "300")}),
    )

    assert missed.status == "fail"
    assert missed.examples == (
        "Missed: instructor Ada, Monday 9AM-11AM: CRN 100, CRN 300",
    )
    assert common.status == "pass"


def test_student_over_daily_limit():
    same_day = rows(row("200", 0, 2, "R1"))
    params = RunParameters(student_max_per_day=1)
    stored = analysis(
        hard={"student_gt_max_per_day": [_hard("001234567", "Monday", 2)]}
    )

    missed = run(
        "conflicts.student_over_max_per_day",
        snapshot(rows=same_day, parameters=params),
    )
    reported = run(
        "conflicts.student_over_max_per_day",
        snapshot(rows=same_day, parameters=params, analysis=stored),
    )
    within = run("conflicts.student_over_max_per_day", snapshot(rows=same_day))

    assert missed.status == "fail"
    assert missed.examples == ("Missed: student 001234567, Monday: 2 exams (limit 1)",)
    assert reported.status == "warn"
    assert within.status == "pass"


def test_instructor_over_daily_limit():
    params = RunParameters(instructor_max_per_day=1)

    result = run("conflicts.instructor_over_max_per_day", snapshot(parameters=params))

    assert result.status == "fail"
    assert result.examples == ("Missed: instructor Ada, Monday: 2 exams (limit 1)",)


def test_student_back_to_back_same_day_adjacent_blocks():
    adjacent = snapshot(rows=rows(row("200", 0, 1, "R1")))

    result = run("conflicts.student_back_to_back", adjacent)

    assert result.status == "fail"
    assert result.examples == (
        "Missed: student 001234567, Monday: 9AM-11AM, 11:30AM-1:30PM",
    )


@pytest.mark.parametrize("blocks_per_day", [4, 5])
def test_last_block_then_next_morning_is_not_back_to_back(blocks_per_day):
    last = blocks_per_day - 1
    overnight = snapshot(
        rows=rows(row("100", 0, last, "R1"), row("200", 1, 0, "R1")),
        parameters=RunParameters(blocks_per_day=blocks_per_day),
    )

    result = run("conflicts.student_back_to_back", overnight)

    assert result.status == "pass"
    assert result.count == 0
    assert result.examples == ()


def test_reported_instructor_back_to_back_warns():
    stored = analysis(
        soft={
            "back_to_back_instructors": [
                {"instructor_name": "Ada", "day": "Monday", "blocks": [1, 2]}
            ]
        }
    )

    result = run(
        "conflicts.instructor_back_to_back",
        snapshot(rows=rows(row("100", 0, 1, "R1")), analysis=stored),
    )

    assert result.status == "warn"


def test_missed_instructor_back_to_back_fails():
    # Ada: CRN 100 Monday block 1, CRN 300 Monday block 2; nothing stored.
    result = run(
        "conflicts.instructor_back_to_back",
        snapshot(rows=rows(row("100", 0, 1, "R1"))),
    )

    assert result.status == "fail"
    assert result.examples == (
        "Missed: instructor Ada, Monday: 11:30AM-1:30PM, 2PM-4PM",
    )


@pytest.mark.parametrize("blocks_per_day", [4, 5])
def test_instructor_last_block_then_next_morning_is_not_back_to_back(
    blocks_per_day,
):
    # Ada: CRN 300 in Monday's last block, CRN 100 first thing Tuesday.
    overnight = snapshot(
        rows=rows(
            row("300", 0, blocks_per_day - 1, "R2", enrollment=1),
            row("100", 1, 0, "R2"),
            row("200", 1, 1, "R1", instructor="Bob"),
        ),
        parameters=RunParameters(blocks_per_day=blocks_per_day),
    )

    result = run("conflicts.instructor_back_to_back", overnight)

    assert result.status == "pass"
    assert result.examples == ()


def test_instructor_cell_containing_semicolon_matches_as_stored():
    co_taught = "Doe, J; Roe, R"
    snap = snapshot(
        rows=rows(row("100", instructor=co_taught)),
        files=files(courses=(course("100", 2, co_taught), *BASE_FILES.courses[1:])),
    )

    assert run("data.stored_course_matches_file", snap).status == "pass"


def test_without_stored_analysis_unscheduled_reasons_are_not_judged():
    unscheduled = snapshot(
        rows=rows(row("300", None, None, None, enrollment=1)), analysis=None
    )

    accounted = run("coverage.crn_accounted", unscheduled)
    groups = run("groups.unscheduled_consistent", unscheduled)

    assert accounted.status == "warn"
    assert accounted.examples == ("CRN 300 is unscheduled",)
    assert groups.status == "skipped"


def test_large_course_late_in_week():
    big = files(courses=(course("100", 150, "Ada"), *BASE_FILES.courses[1:]))
    thursday = snapshot(files=big, rows=rows(row("100", 3, 0, "R1")))
    wednesday = snapshot(files=big, rows=rows(row("100", 2, 0, "R1")))

    result = run("conflicts.large_course_late", thursday)

    assert result.status == "fail"
    assert result.examples == ("Missed: CRN 100: 150 students on Thursday",)
    assert run("conflicts.large_course_late", wednesday).status == "pass"


# ----------------------------------------------------------------------
# Data consistency
# ----------------------------------------------------------------------


def test_stored_course_differing_from_file_fails():
    snap = snapshot(
        rows=rows(
            row("100", 0, 0, "R1", enrollment=5, instructor="Ada"),
            row("200", 1, 0, "R1", enrollment=2, instructor="Bob; Eve"),
        )
    )

    result = run("data.stored_course_matches_file", snap)

    assert result.status == "fail"
    assert result.examples == (
        "CRN 100: enrollment 5 stored, 2 in file",
        "CRN 200: instructor 'Bob; Eve' stored, 'Bob' in file",
    )


def test_stored_statistics_must_match_lists_and_schedule():
    snap = snapshot(
        analysis=analysis(num_classes=4, student_double_book_count=2, slots_used=3)
    )

    result = run("data.stored_statistics", snap)

    assert result.status == "fail"
    assert sorted(result.examples) == [
        "num_classes: stored 4, expected 3",
        "student_double_book_count: stored 2, expected 0",
    ]


def test_enrollment_total_differing_from_enrolled_students_warns():
    snap = snapshot(
        files=files(courses=(course("100", 5, "Ada"), *BASE_FILES.courses[1:]))
    )

    result = run("data.enrollment_totals", snap)

    assert result.status == "warn"
    assert result.examples == ("CRN 100: Total_Enrollment 5, 2 students enrolled",)


def test_enrollments_for_unknown_crn_warn_counting_rows():
    snap = snapshot(
        files=files(
            enrollments=(
                *BASE_FILES.enrollments,
                enrolled("s9", "999"),
                enrolled("s8", "999"),
            )
        )
    )

    result = run("data.enrollment_unknown_crns", snap)

    assert result.status == "warn"
    assert result.count == 2
    assert result.examples == ("CRN 999: 2 enrollment rows",)


def test_duplicate_courses_and_enrollments_warn():
    snap = snapshot(
        files=files(
            courses=(*BASE_FILES.courses, course("100", 2, "Ada")),
            enrollments=(*BASE_FILES.enrollments, enrolled("s2", "100")),
        )
    )

    result = run("data.duplicates", snap)

    assert result.status == "warn"
    assert result.examples == (
        "CRN 100 appears 2 times in the courses file",
        "Student s2 is enrolled in CRN 100 2 times",
    )


# ----------------------------------------------------------------------
# Late additions
# ----------------------------------------------------------------------

# Late-add versions of the baseline on files where
#   CRN 900 (2 students) is in the enrollments only, and
#   CRN 400 (zero enrollment in the courses file) has 1 enrolled student.
# v2 adds CRN 900 (Dee) Wednesday block 0 in R1;
# v3 also adds CRN 400 (Cy) Thursday block 0 in R2.
LATE_FILES = files(
    enrollments=(
        *BASE_FILES.enrollments,
        enrolled("s5", "900"),
        enrolled("s6", "900"),
        enrolled("s7", "400"),
    )
)


def late(
    crn: str,
    day: int,
    block: int,
    room: str,
    size: int,
    instructor: str = "Dee",
    course_code: str = "LATE 1",
) -> dict:
    """A stored late_additions record (the save step's format)."""
    return {
        "crn": crn,
        "course_code": course_code,
        "instructor_id": instructor,
        "size": size,
        "day": day,
        "day_name": "unused",
        "block": block,
        "block_time": "unused",
        "room": room,
        "outcome": "clear",
        "conflicts": {},
        "added_by": "u1",
        "added_by_name": "User",
        "added_at": "2026-01-01T00:00:00",
        "schedule_id": "s1",
    }


def late_row(
    crn: str,
    day: int,
    block: int,
    room: str,
    size: int,
    instructor: str = "Dee",
    course_code: str = "LATE 1",
) -> ScheduleRow:
    """The schedule row the save step stores for a late addition."""
    return row(
        crn,
        day,
        block,
        room,
        enrollment=size,
        instructor=instructor,
        course_code=course_code,
    )


V2_LATE = (late("900", 2, 0, "R1", 2),)
V2_ROWS = rows(late_row("900", 2, 0, "R1", 2))
V3_LATE = (*V2_LATE, late("400", 3, 0, "R2", 1, "Cy", "LATE 4"))
V3_ROWS = rows(
    late_row("900", 2, 0, "R1", 2), late_row("400", 3, 0, "R2", 1, "Cy", "LATE 4")
)


def late_snapshot(late_additions: tuple = V2_LATE, **changes) -> ValidationSnapshot:
    placed = len(changes.get("rows", V2_ROWS))
    defaults = {
        "rows": V2_ROWS,
        "files": LATE_FILES,
        "analysis": analysis(num_classes=placed, slots_used=placed),
        "late_additions": late_additions,
    }
    return snapshot(**{**defaults, **changes})


def _statuses(snap: ValidationSnapshot) -> dict[str, str]:
    ctx = ValidationContext(snap)
    return {check.id: run_check(check, ctx).status for check in CHECKS}


@pytest.mark.parametrize(
    ("late_additions", "late_rows"), [(V2_LATE, V2_ROWS), (V3_LATE, V3_ROWS)]
)
def test_late_add_versions_pass_with_no_new_problems(late_additions, late_rows):
    stored = {"late_additions": list(late_additions)}
    base = _statuses(snapshot(files=LATE_FILES))
    version = late_snapshot(
        late_additions_from_stored(stored),
        rows=late_rows,
        parameters=RunParameters.from_stored(stored),
    )

    statuses = _statuses(version)

    assert statuses["coverage.late_additions"] == "pass"
    worse = {
        cid: status
        for cid, status in statuses.items()
        if status != "pass" and status != base[cid]
    }
    assert worse == {}
    note = run("coverage.crn_in_courses_file", version).summary
    assert "late add" in note
    assert "CRN 900" in note


_COURSE_ROW_CHECKS = (
    "coverage.crn_accounted",
    "data.stored_course_matches_file",
    "data.enrollment_totals",
    "data.enrollment_unknown_crns",
)


def test_course_row_checks_say_when_late_additions_count_as_courses():
    version = late_snapshot(V3_LATE, rows=V3_ROWS)
    generated = snapshot(files=LATE_FILES)

    for check_id in _COURSE_ROW_CHECKS:
        late_result = run(check_id, version)
        assert late_result.status == "pass", (check_id, late_result.summary)
        assert "late addition" in late_result.summary, check_id
        assert "late addition" not in run(check_id, generated).summary, check_id


def test_late_addition_check_skips_on_generated_schedules():
    result = run("coverage.late_additions", snapshot())

    assert result.status == "skipped"
    assert result.summary == "This schedule has no late additions."


def test_late_addition_check_skips_when_files_are_gone():
    result = run("coverage.late_additions", late_snapshot(files=None))

    assert result.status == "skipped"
    assert result.summary == FILES_GONE


def test_late_addition_at_other_block_fails():
    snap = late_snapshot((late("900", 2, 1, "R1", 2),))

    result = run("coverage.late_additions", snap)

    assert result.status == "fail"
    assert result.examples == (
        "CRN 900 is recorded at Wednesday 11:30AM-1:30PM in R1 but is "
        "Wednesday 9AM-11AM in R1",
    )


def test_late_addition_with_wrong_size_fails():
    snap = late_snapshot(
        (late("900", 2, 0, "R1", 3),), rows=rows(late_row("900", 2, 0, "R1", 3))
    )

    result = run("coverage.late_additions", snap)

    assert result.status == "fail"
    assert result.examples == (
        "CRN 900 is recorded with size 3 but has 2 enrolled students",
    )


def test_late_addition_of_a_scheduled_course_fails():
    snap = late_snapshot(
        (late("100", 0, 0, "R1", 2, "Ada", "CS1"),),
        rows=rows(late_row("100", 0, 0, "R1", 2, "Ada", "CS1")),
    )

    result = run("coverage.late_additions", snap)

    assert result.status == "fail"
    assert result.examples == (
        "CRN 100 is a scheduled course in the courses file (2 students), "
        "not a late addition",
    )


def test_late_addition_must_match_its_stored_course_row_and_enrollments():
    snap = late_snapshot(
        (late("900", 2, 0, "R1", 2), late("950", 4, 0, "R1", 0)),
        rows=rows(
            late_row("900", 2, 0, "R1", 5, instructor="Eve", course_code="OTHER"),
            late_row("950", 4, 0, "R1", 0),
        ),
    )

    result = run("coverage.late_additions", snap)

    assert result.status == "fail"
    assert result.examples == (
        "CRN 900: course code 'OTHER' stored, 'LATE 1' recorded; instructor 'Eve' "
        "stored, 'Dee' recorded; size 5 stored, 2 recorded",
        "CRN 950 has no enrollment rows",
    )


def test_late_addition_missing_repeated_or_malformed_fails():
    snap = late_snapshot(
        (late("900", 2, 0, "R1", 2), late("900", 2, 0, "R1", 2), {"crn": "901"}),
        rows=rows(drop=()),
    )

    result = run("coverage.late_additions", snap)

    assert result.status == "fail"
    assert result.examples == (
        "Late addition #3 lacks crn, course_code, instructor_id or room",
        "CRN 900 is recorded as a late addition 2 times",
        "CRN 900 should appear once at Wednesday 9AM-11AM in R1 but has "
        "0 schedule rows",
    )


def test_unrecorded_late_crn_still_fails_crn_in_courses_file():
    result = run("coverage.crn_in_courses_file", late_snapshot(late_additions=()))

    assert result.status == "fail"
    assert result.examples == ("CRN 900 is not in the courses file",)


def test_late_addition_instructor_takes_part_in_instructor_conflicts():
    # Ada already has CRN 100 on Monday block 0; the late exam joins her there.
    snap = late_snapshot(
        (late("900", 0, 0, "R2", 2, "Ada"),),
        rows=rows(late_row("900", 0, 0, "R2", 2, "Ada")),
    )
    stored = analysis(
        hard={"instructor_double_book": [_hard("Ada", "Monday", 0)]},
        num_classes=4,
        slots_used=3,
    )

    missed = run("conflicts.instructor_double_book", snap)
    reported = run("conflicts.instructor_double_book", replace(snap, analysis=stored))

    assert missed.examples == (
        "Missed: instructor Ada, Monday 9AM-11AM: CRN 100, CRN 900",
    )
    assert reported.status == "warn"


@pytest.mark.parametrize("nan", ["NaN", " NAN "])
def test_late_addition_nan_instructor_is_no_instructor(nan):
    # Two late exams in one block whose instructor cell is "nan" in any case.
    snap = late_snapshot(
        (late("900", 2, 0, "R1", 2, nan), late("400", 2, 0, "R2", 1, nan, "LATE 4")),
        rows=rows(
            late_row("900", 2, 0, "R1", 2, nan),
            late_row("400", 2, 0, "R2", 1, nan, "LATE 4"),
        ),
    )

    assert run("conflicts.instructor_double_book", snap).status == "pass"


def test_late_addition_size_counts_for_room_capacity():
    # The stored row claims 0 seats; the late addition's size (2) is what counts.
    snap = late_snapshot(
        (late("900", 2, 0, "R3", 2),),
        rows=rows(late_row("900", 2, 0, "R3", 0)),
        files=replace(LATE_FILES, rooms=(*LATE_FILES.rooms, RoomRecord("R3", 1))),
    )

    result = run("rooms.capacity", snap)

    assert result.status == "fail"
    assert result.count == 1


# ----------------------------------------------------------------------
# Parsing uploaded files
# ----------------------------------------------------------------------


def test_parse_dataset_files_keeps_ids_and_marks_unreadable_files():
    parsed = parse_dataset_files(
        {
            "courses": b"CRN,CourseID,num_students,Instructor Name\n"
            b"100,CS1,2, Ada \n400,CS4,,\n",
            "enrollments": b"Student_PIDM,CRN\n001234567,100\n",
            "rooms": b"not,a,rooms,file\n1,2,3,4\n",
            "room_blockouts": b"Room,Day,Block\nR1,Monday,9AM-11AM\n",
        }
    )

    assert parsed.courses == (course("100", 2, "Ada"), course("400", None, None))
    assert parsed.enrollments == (enrolled("001234567", "100"),)
    assert parsed.rooms is None
    assert parsed.unreadable == frozenset({"rooms"})
    assert parsed.blockouts == {"R1": frozenset({(0, 0)})}
    assert parsed.blockouts_uploaded


def test_parse_dataset_files_without_blockout_file():
    parsed = parse_dataset_files(
        {
            "courses": b"CRN,CourseID,num_students\n100,CS1,2\n",
            "enrollments": b"Student_PIDM,CRN\ns1,100\n",
            "rooms": b"room_name,capacity\nR1,30\nR2,0\n",
        }
    )

    assert parsed.rooms == (RoomRecord("R1", 30),)
    assert parsed.blockouts is None
    assert not parsed.blockouts_uploaded
    assert parsed.unreadable == frozenset()
