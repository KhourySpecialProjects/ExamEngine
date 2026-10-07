"""
Tests for the optional LargeOnly column in rooms.csv at upload.

Storage and the dataset repository are faked (see conftest); the real
validation and adapters run end to end.
"""

import io
from uuid import uuid4

import pytest
from fastapi import UploadFile

from src.core.exceptions import ValidationError
from src.services.dataset.service import DatasetService


COURSES_CSV = b"""CRN,CourseID,Enrollment
1001,CS 1000,30
1002,MATH 2000,60
"""

ENROLLMENTS_CSV = b"""Student_PIDM,CRN
S1,1001
S2,1002
"""


def _file(content: bytes, filename: str) -> UploadFile:
    return UploadFile(file=io.BytesIO(content), filename=filename)


async def _upload(repo, rooms: bytes):
    return await DatasetService(repo).upload_dataset(
        dataset_name="Fall",
        courses_file=_file(COURSES_CSV, "courses.csv"),
        enrollments_file=_file(ENROLLMENTS_CSV, "enrollments.csv"),
        rooms_file=_file(rooms, "rooms.csv"),
        user_id=uuid4(),
    )


async def _rejected(repo, storage, rooms: bytes) -> str:
    with pytest.raises(ValidationError) as exc_info:
        await _upload(repo, rooms)
    assert storage.uploaded_keys == []
    assert repo.created == []
    return exc_info.value.detail["errors"]["rooms"]


async def test_metadata_names_large_only_room_and_cutoff(repo, storage):
    result = await _upload(
        repo,
        b"Room,Capacity,large only\nHall A,500,YeS\nRoom B,80,n\n"
        b"Room C,60,\nRoom D,40,0\n",
    )

    assert result["files"]["rooms"]["large_only_room"] == {
        "name": "Hall A",
        "capacity": 500,
        "cutoff": 80,
    }


@pytest.mark.parametrize("header", ["LargeOnly", "Large_Only", "Large-Only"])
@pytest.mark.parametrize("yes", ["y", "1", "TRUE"])
async def test_accepts_aliases_and_yes_spellings(repo, storage, header, yes):
    rooms = f"Room,Capacity,{header}\nHall A,500,{yes}\nRoom B,80,No\n".encode()

    result = await _upload(repo, rooms)

    assert result["files"]["rooms"]["large_only_room"]["name"] == "Hall A"


@pytest.mark.parametrize(
    "rooms",
    [
        b"Room,Capacity\nHall A,500\nRoom B,80\n",
        b"Room,Capacity,LargeOnly\nHall A,500,no\nRoom B,80,\n",
    ],
    ids=["column absent", "all no"],
)
async def test_without_marked_room_metadata_has_no_large_only_key(repo, storage, rooms):
    result = await _upload(repo, rooms)

    assert "large_only_room" not in result["files"]["rooms"]


async def test_rejects_invalid_values_with_row_numbers(repo, storage):
    error = await _rejected(
        repo,
        storage,
        b"Room,Capacity,LargeOnly\nHall A,500,maybe\nRoom B,80,no\nRoom C,60,2\n",
    )

    assert "row 2 'maybe'" in error
    assert "row 4 '2'" in error
    assert "y/yes/1/true or n/no/0/false" in error


async def test_rejects_pandas_missing_value_tokens(repo, storage):
    error = await _rejected(
        repo,
        storage,
        b"Room,Capacity,LargeOnly\nHall A,500,NA\nRoom B,80,null\n"
        b"Room C,60,N/A\nRoom D,50,\n",
    )

    assert "row 2 'NA'" in error
    assert "row 3 'null'" in error
    assert "row 4 'N/A'" in error
    assert "row 5" not in error


async def test_invalid_value_row_counts_blank_lines(repo, storage):
    error = await _rejected(
        repo,
        storage,
        b"Room,Capacity,LargeOnly\r\nHall A,500,yes\r\n\r\nRoom B,80,maybe\r\n",
    )

    assert "row 4 'maybe'" in error


async def test_blank_lines_are_not_rooms(repo, storage):
    result = await _upload(
        repo, b"Room,Capacity,LargeOnly\nHall A,500,yes\n\nRoom B,80,\n\n"
    )

    assert result["files"]["rooms"]["rows"] == 2
    assert result["files"]["rooms"]["large_only_room"] == {
        "name": "Hall A",
        "capacity": 500,
        "cutoff": 80,
    }


async def test_rejects_two_marked_rooms(repo, storage):
    error = await _rejected(
        repo, storage, b"Room,Capacity,LargeOnly\nHall A,500,yes\nHall B,400,yes\n"
    )

    assert "Only one room may be marked LargeOnly" in error


async def test_rejects_marked_room_not_strictly_largest(repo, storage):
    error = await _rejected(
        repo, storage, b"Room,Capacity,LargeOnly\nHall A,500,yes\nHall B,500,no\n"
    )

    assert "must seat more than every other room" in error
