"""
Tests for uploading a dataset with an optional common_exams.csv.

Common groups share one time block but sit in separate rooms; a listed CRN
that belongs to a combined group brings its whole combined group along.
Storage and the dataset repository are faked (see conftest); the real
validation, adapters, DatasetFactory and validators run end to end.
"""

import io
from uuid import uuid4

import pytest
from fastapi import UploadFile

from src.core.exceptions import ValidationError
from src.services.dataset.service import DatasetService


COURSES_CSV = b"""CRN,CourseID,Enrollment
1001,CS 1000,30
1002,CS 1000,25
1003,MATH 2000,60
1004,PHYS 1000,20
"""

# S6 takes both 1001 and 1004.
ENROLLMENTS_CSV = b"""Student_PIDM,CRN
S1,1001
S2,1002
S3,1003
S4,1004
S6,1001
S6,1004
"""

ROOMS_CSV = b"""Room,Capacity
Hall A,70
Room B,40
Room C,35
"""


def _file(content: bytes, filename: str) -> UploadFile:
    return UploadFile(file=io.BytesIO(content), filename=filename)


async def _upload(repo, common_exams: bytes, combined_exams: bytes | None = None):
    service = DatasetService(repo)
    return await service.upload_dataset(
        dataset_name="Fall",
        courses_file=_file(COURSES_CSV, "courses.csv"),
        enrollments_file=_file(ENROLLMENTS_CSV, "enrollments.csv"),
        rooms_file=_file(ROOMS_CSV, "rooms.csv"),
        user_id=uuid4(),
        combined_exams_file=(
            _file(combined_exams, "combined_exams.csv") if combined_exams else None
        ),
        common_exams_file=_file(common_exams, "common_exams.csv"),
    )


async def _rejected(repo, storage, common_exams, combined_exams=None) -> str:
    with pytest.raises(ValidationError) as exc_info:
        await _upload(repo, common_exams, combined_exams)
    assert storage.uploaded_keys == []
    assert repo.created == []
    return exc_info.value.detail["errors"]["common_exams"]


async def test_valid_common_exams_saved_separately_from_merges(repo, storage):
    result = await _upload(
        repo, b"Common_Group,CRN\nBIOL Final,1003\nBIOL Final,1002\n"
    )

    dataset = repo.created[0]
    assert dataset.common_exam_groups == {"BIOL Final": ["1003", "1002"]}
    assert dataset.course_merges is None
    metadata = result["files"]["common_exams"]
    assert metadata["common_groups"] == 1
    assert metadata["common_crns"] == 2
    assert metadata["infeasible_groups"] == []
    assert metadata["student_overlap_groups"] == []
    assert any(key.endswith("/common_exams.csv") for key in storage.uploaded_keys)


async def test_crn_in_two_common_groups_rejected(repo, storage):
    error = await _rejected(
        repo,
        storage,
        b"Common_Group,CRN\nA,1001\nA,1002\nB,1002\nB,1004\n",
    )

    assert "CRN 1002 is in multiple common groups: 'A', 'B'" in error


async def test_unknown_crn_rejected(repo, storage):
    error = await _rejected(repo, storage, b"Common_Group,CRN\nA,1001\nA,9999\n")

    assert "common group 'A'" in error and "9999" in error


async def test_combined_group_split_across_common_groups_rejected(repo, storage):
    error = await _rejected(
        repo,
        storage,
        b"Common_Group,CRN\nA,1001\nA,1003\nB,1002\nB,1004\n",
        combined_exams=b"ExamGroup,CRN\nCS,1001\nCS,1002\n",
    )

    assert "combined group 'CS' is split across common groups 'A', 'B'" in error


async def test_group_of_one_combined_group_has_too_few_room_units(repo, storage):
    error = await _rejected(
        repo,
        storage,
        b"Common_Group,CRN\nA,1001\nA,1002\n",
        combined_exams=b"ExamGroup,CRN\nCS,1001\nCS,1002\n",
    )

    assert "common group 'A'" in error
    assert "at least 2 room units" in error


async def test_closure_seats_whole_combined_group_in_one_room(repo, storage):
    # Listing only 1002 pulls in its combined partner 1001: room units of 55
    # and 60 need Hall A (70) twice, so the group cannot be seated at once.
    # Without closure, 1002 alone (25) would fit Room B.
    result = await _upload(
        repo,
        b"Common_Group,CRN\nFinal,1002\nFinal,1003\n",
        combined_exams=b"ExamGroup,CRN\nCS,1001\nCS,1002\n",
    )

    dataset = repo.created[0]
    assert dataset.course_merges == {"CS": ["1001", "1002"]}
    assert dataset.common_exam_groups == {"Final": ["1002", "1003"]}
    infeasible = result["files"]["common_exams"]["infeasible_groups"]
    assert [entry["group"] for entry in infeasible] == ["Final"]
    assert "['1001', '1002'] (55 students)" in infeasible[0]["reason"]


async def test_group_needing_more_rooms_than_fit_is_saved_as_infeasible(repo, storage):
    # Units 60, 30, 25, 20 vs rooms 70, 40, 35: the fourth unit has no room.
    result = await _upload(
        repo,
        b"Common_Group,CRN\nBig,1001\nBig,1002\nBig,1003\nBig,1004\n",
    )

    assert repo.created[0].common_exam_groups == {
        "Big": ["1001", "1002", "1003", "1004"]
    }
    infeasible = result["files"]["common_exams"]["infeasible_groups"]
    assert [entry["group"] for entry in infeasible] == ["Big"]
    assert "unscheduled" in infeasible[0]["reason"]


async def test_exact_fit_in_distinct_rooms_is_feasible(repo, storage):
    # Units 60, 30, 25 fit Hall A, Room C (35) and Room B (40) exactly once each.
    result = await _upload(repo, b"Common_Group,CRN\nTri,1001\nTri,1002\nTri,1003\n")

    assert result["files"]["common_exams"]["infeasible_groups"] == []


async def test_student_in_two_room_units_reported_as_warning(repo, storage):
    result = await _upload(repo, b"Common_Group,CRN\nPair,1001\nPair,1004\n")

    assert repo.created[0].common_exam_groups == {"Pair": ["1001", "1004"]}
    assert result["files"]["common_exams"]["student_overlap_groups"] == [
        {"group": "Pair", "students": 1}
    ]


async def test_combined_file_in_common_slot_fails_header_detection(repo, storage):
    error = await _rejected(repo, storage, b"ExamGroup,CRN\nCS,1001\nCS,1002\n")

    assert error.startswith("Missing columns:")
    assert "common_exams" in error


async def test_errors_in_both_files_reported_together(repo, storage):
    with pytest.raises(ValidationError) as exc_info:
        await _upload(
            repo,
            b"Common_Group,CRN\nA,1003\nA,8888\n",
            combined_exams=b"ExamGroup,CRN\nCS,1001\nCS,9999\n",
        )

    errors = exc_info.value.detail["errors"]
    assert "9999" in errors["combined_exams"]
    assert "8888" in errors["common_exams"]
