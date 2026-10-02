"""Tests for the `Valid` flag of exported schedule rows."""

import pytest

from src.domain.assemblers import ScheduleAssembler


def _record(capacity: int, size: int, has_conflict: bool = False) -> dict:
    return ScheduleAssembler.build_exam_record(
        crn="1001",
        course_code="CS 1000",
        day="Mon",
        block_label="0 (9AM-11AM)",
        room="Hall A",
        capacity=capacity,
        size=size,
        instructor="",
        has_conflict=has_conflict,
    )


@pytest.mark.parametrize(
    ("capacity", "size", "valid"),
    [
        (70, 71, False),  # over capacity
        (70, 70, True),  # exactly full
        (0, 71, True),  # capacity unknown
    ],
)
def test_room_smaller_than_exam_is_invalid(capacity, size, valid):
    assert _record(capacity, size)["Valid"] is valid


def test_conflict_is_invalid_even_when_room_fits():
    assert _record(70, 30, has_conflict=True)["Valid"] is False
