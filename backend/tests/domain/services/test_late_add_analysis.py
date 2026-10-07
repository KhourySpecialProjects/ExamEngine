"""The stored analysis of a late-add version: base copy + late exam delta (EXENG-124)."""

import copy

from src.domain.constants import EARLY_WEEK_CUTOFF, LARGE_COURSE_THRESHOLD
from src.domain.services.late_add import (
    BaseExam,
    BaseSchedule,
    LateAddSettings,
    LateExam,
    evaluate_placement,
)
from src.domain.services.late_add_analysis import late_exam_analysis


MON, TUE = 0, 1


def _exam(crn, slot, room=None, instructor=None):
    day, block = slot if slot else (None, None)
    return BaseExam(
        crn=crn,
        course_code=f"C {crn}",
        instructor=instructor,
        size=1,
        day=day,
        block=block,
        room=room,
    )


# Monday: 101 (I1) and 102 (I2) at 8AM, 107 (I2) at 10:30AM, 103 (I1) at 1PM,
# 106 at 3:30PM. Tuesday: 104 at 8AM. 105 is unscheduled.
BASE = BaseSchedule(
    exams=[
        _exam("101", (MON, 0), "R1", "I1"),
        _exam("102", (MON, 0), "R2", "I2"),
        _exam("107", (MON, 1), "R2", "I2"),
        _exam("103", (MON, 2), "R1", "I1"),
        _exam("106", (MON, 3), "R1"),
        _exam("104", (TUE, 0), "R1"),
        _exam("105", None),
    ],
    students_by_crn={
        "101": {"s1", "s2"},
        "102": {"s1"},
        "103": {"s3"},
        "106": {"s3"},
        "104": {"s4"},
        "105": {"s5"},
    },
    rooms={"R1": 50, "R2": 50, "R3": 500},
    blockouts={},
    settings=LateAddSettings(
        max_days=5, blocks_per_day=5, student_max_per_day=1, instructor_max_per_day=2
    ),
)

# What generation stored for BASE: s3 (1PM, 3:30PM) and I2 (8AM, 10:30AM)
# have back-to-back exams on Monday; s1 is over the daily limit of 1.
STORED = {
    "hard_conflicts": {
        "student_double_book": [],
        "instructor_double_book": [],
        "student_gt_max_per_day": [
            {
                "entity_id": "s1",
                "day": "Monday",
                "block": 0,
                "block_time": "8AM-10AM",
                "crn": "102",
                "course": "C 102",
                "conflicting_crn": None,
                "conflicting_course": None,
            }
        ],
        "instructor_gt_max_per_day": [],
    },
    "soft_conflicts": {
        "back_to_back_students": [
            {
                "student_id": "s3",
                "day": "Monday",
                "blocks": [2, 3],
                "block_times": ["1PM-3PM", "3:30PM-5:30PM"],
            }
        ],
        "back_to_back_instructors": [
            {
                "instructor_name": "I2",
                "day": "Monday",
                "blocks": [0, 1],
                "block_times": ["8AM-10AM", "10:30AM-12:30PM"],
            }
        ],
        "large_courses_not_early": [],
    },
    "statistics": {
        "num_classes": 6,
        "num_students": 4,
        "num_rooms": 2,
        "slots_used": 5,
        "unplaced_exams": 0,
        "total_hard_conflicts": 1,
        "total_soft_conflicts": 2,
        "student_double_book_count": 0,
        "instructor_double_book_count": 0,
        "student_gt_max_per_day_count": 1,
        "instructor_gt_max_per_day_count": 0,
        "back_to_back_students_count": 1,
        "back_to_back_instructors_count": 1,
        "large_courses_not_early_count": 0,
    },
    "unscheduled_groups": [
        {"kind": "combined", "group": "G1", "reason": "No room", "crns": ["105"]}
    ],
}


def _late(students, instructor="I1"):
    return LateExam(
        crn="900",
        course_code="LATE 900",
        instructor_id=instructor,
        students=frozenset(students),
    )


def _analysis(late, day, block, room="R3", stored=STORED, base=BASE):
    placement = evaluate_placement(base, late, day, block)
    return late_exam_analysis(stored, base, late, placement, room)


def _hard(entity, crn=None, block=0):
    return {
        "entity_id": entity,
        "day": "Monday",
        "block": block,
        "block_time": {0: "8AM-10AM", 1: "10:30AM-12:30PM"}[block],
        "crn": "900",
        "course": "LATE 900",
        "conflicting_crn": crn,
        "conflicting_course": f"C {crn}" if crn else None,
    }


def test_hard_entries_are_pairs_per_base_crn_and_one_per_person_over_the_limit():
    before = copy.deepcopy(STORED)

    result = _analysis(_late({"s1", "s3", "s9"}), MON, 0)

    assert STORED == before  # the base analysis is not modified
    hard = result["hard_conflicts"]
    # s1 sits 101 and 102 at 8AM: one pair each; the instructor sits 101.
    assert hard["student_double_book"] == [_hard("s1", "101"), _hard("s1", "102")]
    assert hard["instructor_double_book"] == [_hard("I1", "101")]
    # The existing s1 entry stays; the late exam adds one per person over.
    assert hard["student_gt_max_per_day"] == [
        *STORED["hard_conflicts"]["student_gt_max_per_day"],
        _hard("s1"),
        _hard("s3"),
    ]
    # I1: 8AM, 1PM and the late exam is 3 > 2.
    assert hard["instructor_gt_max_per_day"] == [_hard("I1")]


def test_statistics_are_recomputed_from_the_lists_and_the_exams():
    result = _analysis(_late({"s1", "s3", "s9"}), MON, 0)

    stats = result["statistics"]
    assert stats == {
        # 6 placed CRNs + the late one; 105 is unscheduled.
        "num_classes": 7,
        # s1, s2, s3, s4 from placed CRNs + s9; s5 only sits 105.
        "num_students": 5,
        "num_rooms": 3,  # R1, R2 and the late exam's R3
        "slots_used": 5,  # Monday 8AM is already used
        "unplaced_exams": 0,
        "student_double_book_count": 2,
        "instructor_double_book_count": 1,
        "student_gt_max_per_day_count": 3,
        "instructor_gt_max_per_day_count": 1,
        "back_to_back_students_count": 1,
        "back_to_back_instructors_count": 1,
        "large_courses_not_early_count": 0,
        "total_hard_conflicts": 7,
        "total_soft_conflicts": 2,
    }
    assert result["unscheduled_groups"] == STORED["unscheduled_groups"]


def test_back_to_back_entries_are_extended_in_place_or_added_per_person_and_day():
    # Monday 10:30AM: s1 (8AM) and I1 (8AM, 1PM) become back-to-back; s3
    # already is (1PM, 3:30PM) and gains 10:30AM.
    result = _analysis(_late({"s1", "s3"}), MON, 1)

    students = result["soft_conflicts"]["back_to_back_students"]
    assert students == [
        {
            "student_id": "s3",
            "day": "Monday",
            "blocks": [1, 2, 3],
            "block_times": ["10:30AM-12:30PM", "1PM-3PM", "3:30PM-5:30PM"],
        },
        {
            "student_id": "s1",
            "day": "Monday",
            "blocks": [0, 1],
            "block_times": ["8AM-10AM", "10:30AM-12:30PM"],
        },
    ]
    instructors = result["soft_conflicts"]["back_to_back_instructors"]
    assert instructors[1] == {
        "instructor_name": "I1",
        "day": "Monday",
        "blocks": [0, 1, 2],
        "block_times": ["8AM-10AM", "10:30AM-12:30PM", "1PM-3PM"],
    }
    assert len(instructors) == 2
    assert result["statistics"]["back_to_back_students_count"] == 2
    assert result["statistics"]["total_soft_conflicts"] == 4


def test_existing_back_to_back_entry_gains_a_non_adjacent_late_block():
    # s3 (1PM, 3:30PM) and I2 (8AM, 10:30AM) at 6PM: s3 gets an adjacent
    # block, I2 does not, but the late exam is one more exam that day for both.
    result = _analysis(_late({"s3"}, instructor=" I2 "), MON, 4)

    soft = result["soft_conflicts"]
    assert [e["blocks"] for e in soft["back_to_back_students"]] == [[2, 3, 4]]
    assert soft["back_to_back_instructors"] == [
        {
            "instructor_name": "I2",
            "day": "Monday",
            "blocks": [0, 1, 4],
            "block_times": ["8AM-10AM", "10:30AM-12:30PM", "6PM-8PM"],
        }
    ]


def test_people_without_an_exam_that_day_get_no_back_to_back_entry():
    result = _analysis(_late({"s9"}, instructor="I9"), TUE, 1)

    assert result["soft_conflicts"] == STORED["soft_conflicts"]
    assert result["hard_conflicts"] == STORED["hard_conflicts"]


def test_large_late_exam_on_or_after_the_cutoff_is_listed():
    students = {f"x{n}" for n in range(LARGE_COURSE_THRESHOLD)}
    late = _late(students, instructor="I9")

    early = _analysis(late, EARLY_WEEK_CUTOFF - 1, 0)
    result = _analysis(late, EARLY_WEEK_CUTOFF, 2)

    assert early["soft_conflicts"]["large_courses_not_early"] == []
    assert result["soft_conflicts"]["large_courses_not_early"] == [
        {
            "crn": "900",
            "course": "LATE 900",
            "size": LARGE_COURSE_THRESHOLD,
            "day": "Thursday",
            "block": 2,
            "block_time": "1PM-3PM",
        }
    ]
    assert result["statistics"]["large_courses_not_early_count"] == 1


def test_blank_or_nan_instructor_adds_no_instructor_entries():
    result = _analysis(_late({"s9"}, instructor="nan"), MON, 0)

    assert result["hard_conflicts"]["instructor_double_book"] == []
    assert result["hard_conflicts"]["instructor_gt_max_per_day"] == []
    assert (
        result["soft_conflicts"]["back_to_back_instructors"]
        == STORED["soft_conflicts"]["back_to_back_instructors"]
    )


def test_base_without_an_analysis_gets_a_complete_one():
    result = _analysis(_late({"s1"}), MON, 1, stored=None)

    assert set(result) == {
        "hard_conflicts",
        "soft_conflicts",
        "statistics",
        "unscheduled_groups",
    }
    assert result["unscheduled_groups"] == []
    assert result["soft_conflicts"]["back_to_back_students"][0]["student_id"] == "s1"
    assert result["statistics"]["total_soft_conflicts"] == 2  # s1 and I1
    assert result["statistics"]["total_hard_conflicts"] == 2  # s1 and I1 over
    assert result["statistics"]["unplaced_exams"] == 0


def test_base_double_book_counts_each_sitting_in_the_daily_limit_delta():
    # s1 sits 101 (R1) and 102 (R2) at 8AM: two exams, as the Validator counts
    base = BaseSchedule(
        exams=[
            _exam("101", (MON, 0), "R1"),
            _exam("102", (MON, 0), "R2"),
            _exam("103", (MON, 2), "R1"),
        ],
        students_by_crn={"101": {"s1"}, "102": {"s1"}, "103": {"s1"}},
        rooms={"R1": 50, "R2": 50, "R3": 500},
        blockouts={},
        settings=LateAddSettings(
            max_days=5,
            blocks_per_day=5,
            student_max_per_day=3,
            instructor_max_per_day=2,
        ),
    )
    stored = copy.deepcopy(STORED)
    stored["hard_conflicts"]["student_gt_max_per_day"] = []

    result = _analysis(_late({"s1"}, instructor=""), MON, 1, stored=stored, base=base)

    assert result["hard_conflicts"]["student_gt_max_per_day"] == [_hard("s1", block=1)]
    assert result["statistics"]["student_gt_max_per_day_count"] == 1
