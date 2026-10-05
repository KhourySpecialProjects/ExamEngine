"""Late add placement search for one exam against a saved schedule (EXENG-121)."""

import pytest

from src.domain.services.late_add import (
    BaseExam,
    BaseSchedule,
    LateAddSettings,
    LateExam,
    Outcome,
    RoomOption,
    evaluate_placement,
    search_placements,
)


MON, TUE, THU = 0, 1, 3


def _settings(**overrides: int) -> LateAddSettings:
    values = {
        "max_days": 2,
        "blocks_per_day": 5,
        "student_max_per_day": 2,
        "instructor_max_per_day": 2,
    }
    values.update(overrides)
    return LateAddSettings(**values)


def _exam(
    crn: str,
    slot: tuple[int, int] | None,
    room: str | None = None,
    *,
    instructor: str | None = None,
    course: str | None = None,
    size: int = 10,
) -> BaseExam:
    day, block = slot if slot else (None, None)
    return BaseExam(
        crn=crn,
        course_code=course or f"C {crn}",
        instructor=instructor,
        size=size,
        day=day,
        block=block,
        room=room,
    )


def _base(
    exams: list[BaseExam],
    students: dict[str, set[str]] | None = None,
    rooms: dict[str, int] | None = None,
    blockouts: dict[str, set[tuple[int, int]]] | None = None,
    **settings: int,
) -> BaseSchedule:
    return BaseSchedule(
        exams=exams,
        students_by_crn=students or {},
        rooms=rooms if rooms is not None else {"BIG": 500},
        blockouts=blockouts or {},
        settings=_settings(**settings),
    )


def _late(
    students: set[str] | None = None,
    instructor: str = "I1",
    course: str = "LATE 1000",
) -> LateExam:
    return LateExam(
        crn="900",
        course_code=course,
        instructor_id=instructor,
        students=frozenset(students or {"s1"}),
    )


def _slots(evaluations) -> list[tuple[int, int]]:
    return [(ev.day, ev.block) for ev in evaluations]


# ----------------------------------------------------------------------
# Rooms
# ----------------------------------------------------------------------


def test_best_fit_is_smallest_fitting_room_and_others_are_listed_smallest_first():
    base = _base([], rooms={"HUGE": 300, "TINY": 1, "MID": 50, "SMALL": 3})
    ev = evaluate_placement(base, _late({"a", "b", "c"}), MON, 0)
    assert ev.best_room == RoomOption("SMALL", 3)
    assert ev.other_rooms == (RoomOption("MID", 50), RoomOption("HUGE", 300))
    assert ev.largest_free_room == RoomOption("HUGE", 300)


def test_room_used_by_a_base_exam_in_that_block_is_not_free():
    base = _base([_exam("1", (MON, 0), "SMALL")], rooms={"SMALL": 5, "LARGE": 50})
    late = _late()
    taken = evaluate_placement(base, late, MON, 0)
    assert taken.best_room == RoomOption("LARGE", 50)
    assert not taken.fits_room("SMALL")
    # the same room is free in another block
    assert evaluate_placement(base, late, MON, 1).best_room == RoomOption("SMALL", 5)


def test_unroomed_and_unscheduled_base_exams_occupy_nothing():
    exams = [_exam("1", (MON, 0), None), _exam("2", None, "R")]
    base = _base(exams, students={"1": {"s1"}, "2": {"s1"}}, rooms={"R": 5})
    ev = evaluate_placement(base, _late(), MON, 0)
    assert ev.best_room == RoomOption("R", 5)
    # the unscheduled exam is no sitting; the unroomed one still is
    assert ev.student_double_book == {"s1": ("1",)}
    assert evaluate_placement(base, _late(), TUE, 0).counts.hard == 0


def test_blocked_out_room_is_not_free_in_that_block_only():
    base = _base([], rooms={"R": 5, "S": 50}, blockouts={"R": {(MON, 2)}})
    late = _late()
    assert evaluate_placement(base, late, MON, 2).best_room == RoomOption("S", 50)
    assert evaluate_placement(base, late, MON, 3).best_room == RoomOption("R", 5)


def test_no_fitting_room_keeps_largest_free_room():
    base = _base([], rooms={"A": 1, "B": 2})
    ev = evaluate_placement(base, _late({"x", "y", "z"}), MON, 0)
    assert ev.best_room is None
    assert ev.fitting_rooms == ()
    assert ev.largest_free_room == RoomOption("B", 2)
    assert not ev.is_clear


def test_room_fits_exactly_at_capacity():
    base = _base([], rooms={"R": 2})
    ev = evaluate_placement(base, _late({"x", "y"}), MON, 0)
    assert ev.best_room == RoomOption("R", 2)


# ----------------------------------------------------------------------
# Student conflicts
# ----------------------------------------------------------------------


def test_student_double_book_names_the_clashing_crns():
    exams = [_exam("1", (MON, 0), "R1"), _exam("2", (MON, 0), "R2")]
    students = {"1": {"s1", "s2"}, "2": {"s1"}}
    base = _base(exams, students, rooms={"R1": 5, "R2": 5, "R3": 5})
    ev = evaluate_placement(base, _late({"s1", "s2", "s3"}), MON, 0)
    assert ev.student_double_book == {"s1": ("1", "2"), "s2": ("1",)}
    assert ev.counts.student_double_book == 2


def test_student_over_daily_limit_counts_distinct_blocks_plus_the_late_exam():
    exams = [_exam("1", (MON, 0), "R"), _exam("2", (MON, 2), "R")]
    students = {"1": {"s1", "s2"}, "2": {"s1"}}
    base = _base(exams, students, student_max_per_day=2)
    ev = evaluate_placement(base, _late({"s1", "s2"}), MON, 4)
    assert ev.student_over_daily_limit == {"s1": 3}
    # the limit itself is allowed
    assert "s2" not in ev.student_over_daily_limit
    # other days are unaffected
    assert evaluate_placement(base, _late({"s1"}), TUE, 4).counts.hard == 0


def test_combined_exam_counts_once_per_student():
    # two CRNs of one combined exam share a block and room
    exams = [_exam("1", (MON, 0), "R"), _exam("2", (MON, 0), "R")]
    students = {"1": {"s1"}, "2": {"s1"}}
    base = _base(exams, students, student_max_per_day=2)
    ev = evaluate_placement(base, _late({"s1"}), MON, 3)
    assert ev.student_over_daily_limit == {}
    assert ev.student_day_blocks == {"s1": (0, 3)}


def test_late_exam_that_double_books_still_counts_toward_daily_limit():
    exams = [_exam("1", (MON, 0), "R"), _exam("2", (MON, 2), "R")]
    students = {"1": {"s1"}, "2": {"s1"}}
    base = _base(exams, students, rooms={"R": 5, "S": 5}, student_max_per_day=2)
    ev = evaluate_placement(base, _late({"s1"}), MON, 2)
    assert ev.student_double_book == {"s1": ("2",)}
    assert ev.student_over_daily_limit == {"s1": 3}


def test_student_back_to_back_is_adjacent_block_on_the_same_day_only():
    exams = [
        _exam("1", (MON, 1), "R"),
        _exam("2", (MON, 4), "R"),
        _exam("3", (TUE, 0), "R"),
    ]
    students = {"1": {"before"}, "2": {"last_block"}, "3": {"next_day"}}
    base = _base(exams, students, student_max_per_day=5)
    late = _late({"before", "last_block", "next_day"})
    ev = evaluate_placement(base, late, MON, 2)
    assert ev.student_back_to_back == {"before": (1, 2)}
    end_of_day = evaluate_placement(base, late, MON, 3)
    assert end_of_day.student_back_to_back == {"last_block": (3, 4)}
    # the last block of Monday and the first of Tuesday are not back-to-back
    assert "next_day" not in evaluate_placement(base, late, MON, 4).student_back_to_back


def test_students_not_in_the_late_exam_are_ignored():
    base = _base([_exam("1", (MON, 0), "R")], {"1": {"other"}}, rooms={"R": 5, "S": 5})
    assert evaluate_placement(base, _late({"s1"}), MON, 0).counts.hard == 0


# ----------------------------------------------------------------------
# Instructor conflicts
# ----------------------------------------------------------------------


def test_instructor_double_book_matches_trimmed_instructor_id():
    exams = [_exam("1", (MON, 0), "R", instructor="  I1 ")]
    base = _base(exams, rooms={"R": 5, "S": 5})
    ev = evaluate_placement(base, _late(instructor="I1"), MON, 0)
    assert ev.instructor_double_book == ("1",)
    assert ev.counts.instructor_double_book == 1


def test_instructor_match_is_exact():
    exams = [_exam("1", (MON, 0), "R", instructor="I10")]
    base = _base(exams, rooms={"R": 5, "S": 5})
    result = search_placements(base, _late(instructor="I1"))
    assert result.instructor_exams == ()
    assert evaluate_placement(base, _late(instructor="i1"), MON, 0).counts.hard == 0


def test_instructor_over_daily_limit_and_back_to_back():
    exams = [
        _exam("1", (MON, 0), "R", instructor="I1"),
        _exam("2", (MON, 2), "R", instructor="I1"),
    ]
    base = _base(exams, instructor_max_per_day=2)
    ev = evaluate_placement(base, _late(instructor="I1"), MON, 3)
    assert ev.instructor_exams_that_day == 3
    assert ev.instructor_over_daily_limit
    assert ev.instructor_back_to_back
    assert ev.instructor_day_blocks == (0, 2, 3)
    assert ev.counts.instructor_over_daily_limit == 1
    assert ev.counts.back_to_back_instructor == 1
    # at the limit is allowed
    relaxed = _base(exams, instructor_max_per_day=3)
    assert not evaluate_placement(
        relaxed, _late(instructor="I1"), MON, 3
    ).instructor_over_daily_limit


def test_instructor_sections_of_one_block_count_once_toward_daily_limit():
    exams = [
        _exam("1", (MON, 0), "R", instructor="I1"),
        _exam("2", (MON, 0), "S", instructor="I1"),
    ]
    base = _base(exams, rooms={"R": 5, "S": 5, "T": 5}, instructor_max_per_day=2)
    ev = evaluate_placement(base, _late(instructor="I1"), MON, 3)
    assert ev.instructor_exams_that_day == 2
    assert not ev.instructor_over_daily_limit
    assert evaluate_placement(
        base, _late(instructor="I1"), MON, 0
    ).instructor_double_book == (
        "1",
        "2",
    )


@pytest.mark.parametrize("stored", ["", "  ", "nan", "NaN", None])
def test_blank_and_nan_instructors_never_match(stored):
    exams = [_exam("1", (MON, 0), "R", instructor=stored)]
    base = _base(exams, rooms={"R": 5, "S": 5}, instructor_max_per_day=1)
    for late_id in ("nan", " "):
        result = search_placements(base, _late(instructor=late_id))
        assert result.instructor_exams == ()
        ev = evaluate_placement(base, _late(instructor=late_id), MON, 0)
        assert ev.instructor_double_book == ()
        assert not ev.instructor_back_to_back


def test_instructor_not_found_has_no_conflicts_and_no_exams():
    exams = [_exam("1", (MON, 0), "R", instructor="I2")]
    base = _base(exams, rooms={"R": 5, "S": 5}, instructor_max_per_day=1)
    result = search_placements(base, _late(instructor="I1"))
    assert result.instructor_exams == ()
    assert result.outcome is Outcome.CLEAR
    assert len(result.candidates) == len(result.blocks)


def test_instructor_exams_lists_placed_then_unscheduled():
    exams = [
        _exam("3", None, instructor="I1"),
        _exam("2", (TUE, 0), "R", instructor="I1"),
        _exam("1", (MON, 4), "R", instructor="I1"),
        _exam("4", (MON, 0), "R", instructor="I2"),
    ]
    result = search_placements(_base(exams), _late(instructor="I1"))
    assert [e.crn for e in result.instructor_exams] == ["1", "2", "3"]


# ----------------------------------------------------------------------
# Large course late, siblings, window
# ----------------------------------------------------------------------


def test_large_course_late_uses_analyzer_threshold_and_cutoff():
    students = {f"s{i}" for i in range(100)}
    base = _base([], max_days=5)
    assert evaluate_placement(base, _late(students), THU, 0).large_course_late
    assert not evaluate_placement(base, _late(students), THU - 1, 4).large_course_late
    smaller = _late(set(list(students)[:99]))
    assert not evaluate_placement(base, smaller, THU, 0).large_course_late


def test_sibling_sections_match_course_code():
    exams = [
        _exam("1", (TUE, 1), "R", course="LATE 1000"),
        _exam("2", None, course="LATE 1000"),
        _exam("3", (MON, 0), "R", course="LATE 1001"),
    ]
    result = search_placements(_base(exams), _late(course="LATE 1000"))
    assert [e.crn for e in result.sibling_sections] == ["1", "2"]


@pytest.mark.parametrize("blocks_per_day", [4, 5])
def test_window_covers_max_days_by_blocks_per_day(blocks_per_day):
    result = search_placements(
        _base([], max_days=3, blocks_per_day=blocks_per_day), _late()
    )
    assert _slots(result.blocks) == [
        (d, b) for d in range(3) for b in range(blocks_per_day)
    ]


@pytest.mark.parametrize("slot", [(0, 4), (2, 0), (-1, 0), (0, -1)])
def test_evaluate_outside_window_raises(slot):
    base = _base([], max_days=2, blocks_per_day=4)
    with pytest.raises(ValueError, match="outside"):
        evaluate_placement(base, _late(), *slot)


# ----------------------------------------------------------------------
# Outcomes and ranking
# ----------------------------------------------------------------------


def test_clear_outcome_lists_only_clear_blocks_ranked_by_soft_conflicts():
    exams = [_exam("1", (MON, 1), "R"), _exam("2", (MON, 3), "R")]
    students = {"1": {"s1"}, "2": {"s2"}}
    base = _base(exams, students, max_days=1, blocks_per_day=5)
    result = search_placements(base, _late({"s1", "s2"}))
    assert result.outcome is Outcome.CLEAR
    # 1 and 3 double-book; 0 and 4 have one back-to-back; 2 has two
    assert _slots(result.candidates) == [(MON, 0), (MON, 4), (MON, 2)]


def test_least_conflicts_when_no_block_is_clear():
    # s1 sits every block of the window
    exams = [_exam(str(b), (MON, b), "R") for b in range(2)]
    students = {"0": {"s1"}, "1": {"s1", "s2"}}
    base = _base(
        exams,
        students,
        rooms={"R": 5, "S": 5},
        max_days=1,
        blocks_per_day=2,
        student_max_per_day=5,
    )
    result = search_placements(base, _late({"s1", "s2"}))
    assert result.outcome is Outcome.LEAST_CONFLICTS
    assert _slots(result.candidates) == [(MON, 0), (MON, 1)]
    assert [ev.counts.student_double_book for ev in result.candidates] == [1, 2]


def test_least_conflicts_skips_blocks_without_a_fitting_room():
    exams = [_exam("1", (MON, 0), "R")]
    base = _base(exams, {"1": {"s1"}}, rooms={"R": 5}, max_days=1, blocks_per_day=2)
    # block 1 is clear but its only room is blocked
    blocked = _base(
        exams,
        {"1": {"s1"}},
        rooms={"R": 5, "S": 5},
        blockouts={"R": {(MON, 1)}, "S": {(MON, 1)}},
        max_days=1,
        blocks_per_day=2,
    )
    result = search_placements(blocked, _late({"s1"}))
    assert result.outcome is Outcome.LEAST_CONFLICTS
    assert _slots(result.candidates) == [(MON, 0)]
    assert search_placements(base, _late({"s1"})).outcome is Outcome.CLEAR


def test_no_room_outcome_has_no_candidates_but_every_block_evaluated():
    base = _base([], rooms={"A": 1}, max_days=1, blocks_per_day=4)
    result = search_placements(base, _late({"x", "y"}))
    assert result.outcome is Outcome.NO_ROOM
    assert result.candidates == ()
    assert [ev.largest_free_room for ev in result.blocks] == [RoomOption("A", 1)] * 4


def test_ranking_weighs_students_over_instructor_and_hard_over_soft():
    # limits of 1: a late exam on Monday puts student "a" over the limit,
    # one on Tuesday puts the instructor over it
    exams = [
        _exam("1", (MON, 0), "R"),
        _exam("2", (TUE, 0), "R", instructor="I1"),
    ]
    base = _base(
        exams,
        {"1": {"a"}},
        rooms={"R": 5, "S": 5},
        max_days=2,
        blocks_per_day=3,
        student_max_per_day=1,
        instructor_max_per_day=1,
    )
    result = search_placements(base, _late({"a"}, instructor="I1"))
    assert result.outcome is Outcome.LEAST_CONFLICTS
    assert _slots(result.candidates) == [
        (TUE, 2),  # instructor over limit
        (TUE, 1),  # + instructor back-to-back
        (TUE, 0),  # instructor double-book + over limit
        (MON, 2),  # student over limit
        (MON, 1),  # + student back-to-back
        (MON, 0),  # student double-book + over limit
    ]
