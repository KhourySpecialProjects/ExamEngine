"""Unit tests for common exam validation (closure, room packing, conflicts)."""

from dataclasses import replace

import pytest

from src.domain.models import Course, Room, SchedulingDataset
from src.services.dataset.merge_validator import (
    CommonExamValidator,
    expand_room_units,
    find_unseated_unit,
)


def _dataset(enrollments: dict[str, int], capacities: list[int]) -> SchedulingDataset:
    return SchedulingDataset(
        courses={
            crn: Course(
                crn=crn,
                course_code="X 1",
                enrollment_count=count,
                department="X",
                examination_term="Fall 2025",
            )
            for crn, count in enrollments.items()
        },
        students={},
        rooms=[Room(name=f"R{i}", capacity=c) for i, c in enumerate(capacities)],
        students_by_crn={},
        instructors_by_crn={},
    )


def test_expand_room_units_pulls_in_whole_combined_group_once():
    merges = {"M": ["2", "1"]}

    assert expand_room_units(["3", "1", "2", "3"], merges) == [["3"], ["2", "1"]]


def _rooms(*capacities: int, large_only: int | None = None) -> list[Room]:
    return [
        Room(name=f"R{i}", capacity=c, large_only=c == large_only)
        for i, c in enumerate(capacities)
    ]


def test_packing_seats_largest_first_so_small_units_do_not_steal_big_rooms():
    # In listed order a first-fit would put 30 into the 60 room and strand 50.
    assert find_unseated_unit([30, 50], _rooms(60, 35)) is None


def test_packing_reports_unit_left_without_room():
    assert find_unseated_unit([40, 40], _rooms(40, 39)) == 1


def test_packing_keeps_units_at_or_below_cutoff_out_of_large_only_room():
    # Cutoff 50: the second unit of 50 may not spill into the 500 room.
    assert find_unseated_unit([50, 50], _rooms(500, 50, large_only=500)) == 1


def test_packing_puts_units_above_cutoff_only_in_large_only_room():
    assert find_unseated_unit([60, 70], _rooms(500, 50, large_only=500)) == 0
    assert find_unseated_unit([60, 40], _rooms(500, 50, large_only=500)) is None


def test_warning_explains_large_only_rule_when_it_blocks_the_group():
    dataset = replace(
        _dataset({"1": 40, "2": 40}, []), rooms=_rooms(500, 50, large_only=500)
    )

    warning = CommonExamValidator(dataset, {}).validate(["1", "2"]).warning_message

    assert "Exams of 50 or fewer students cannot use the large-only room R0" in (
        warning
    )


def test_validate_rejects_group_that_collapses_to_one_room_unit():
    validator = CommonExamValidator(
        _dataset({"1": 10, "2": 10}, [50]), {"M": ["1", "2"]}
    )

    with pytest.raises(ValueError, match="at least 2 room units"):
        validator.validate(["1", "2"])


def test_validate_reports_infeasible_group_without_raising():
    validator = CommonExamValidator(
        _dataset({"1": 10, "2": 10, "3": 30}, [100, 15]), {"M": ["1", "2"]}
    )

    result = validator.validate(["2", "3"]).to_dict()

    assert result["is_valid"] is False
    assert result["room_units"] == 2
    assert result["total_enrollment"] == 50
    assert result["can_proceed"] is True
    assert "unscheduled" in result["warning_message"]


def test_cross_group_problems_flag_shared_crn_and_split_combined_group():
    validator = CommonExamValidator(
        _dataset(dict.fromkeys("12345", 5), [50]), {"M": ["1", "2"]}
    )

    problems = validator.cross_group_problems(
        {"A": ["1", "3", "5"], "B": ["2", "4", "5"]}
    )

    assert problems == [
        "CRN 5 is in multiple common groups: 'A', 'B'",
        "combined group 'M' is split across common groups 'A', 'B'; a combined "
        "group must stay in one common group",
    ]
