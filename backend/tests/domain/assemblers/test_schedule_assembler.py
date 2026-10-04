"""Tests for ScheduleAssembler response shapes."""

import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.domain.assemblers import ScheduleAssembler
from src.domain.value_objects import SchedulePermissions


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


def _list_item(dataset: SimpleNamespace) -> dict:
    run = SimpleNamespace(
        algorithm_name="DSATUR",
        parameters={},
        status=SimpleNamespace(value="Completed"),
        dataset_id=uuid4(),
        dataset=dataset,
    )
    schedule = SimpleNamespace(
        schedule_id=uuid4(),
        schedule_name="Finals",
        created_at=datetime.datetime(2026, 1, 2, 9, 30),
        run=run,
    )
    permissions = SchedulePermissions(
        is_owner=True, is_shared=False, created_by_user_id="u", created_by_user_name="U"
    )
    return ScheduleAssembler.build_list_item(schedule, 12, permissions)


def test_list_item_summarizes_its_dataset_from_upload_metadata():
    dataset = SimpleNamespace(
        dataset_name="Spring",
        upload_date=datetime.datetime(2026, 1, 1, 8, 0),
        deleted_at=None,
        file_paths=[
            {"type": "courses", "metadata": {"unique_crns": 40}},
            {"type": "enrollments", "metadata": {"unique_students": 900}},
            {"type": "rooms", "metadata": {"unique_rooms": 12}},
        ],
    )

    assert _list_item(dataset)["dataset"] == {
        "name": "Spring",
        "uploaded_at": "2026-01-01T08:00:00",
        "deleted": False,
        "courses": 40,
        "students": 900,
        "rooms": 12,
    }


def test_list_item_marks_a_deleted_dataset_and_missing_counts():
    dataset = SimpleNamespace(
        dataset_name="Old",
        upload_date=datetime.datetime(2025, 9, 1),
        deleted_at=datetime.datetime(2025, 12, 1),
        file_paths=[{"type": "courses", "metadata": {}}],
    )

    summary = _list_item(dataset)["dataset"]

    assert summary["deleted"] is True
    assert (summary["courses"], summary["students"], summary["rooms"]) == (
        None,
        None,
        None,
    )
