"""
Tests for uploading a dataset with an optional common_exams.csv.

Storage and the dataset repository are faked; the real validation, adapters,
DatasetFactory and MergeValidator run end to end.
"""

import io
from uuid import uuid4

import pytest
from fastapi import UploadFile

import src.services.dataset.service as service_module
from src.core.exceptions import ValidationError
from src.services.dataset.service import DatasetService


COURSES_CSV = b"""CRN,CourseID,Enrollment
1001,CS 1000,30
1002,CS 1000,25
1003,MATH 2000,60
1004,PHYS 1000,20
"""

ENROLLMENTS_CSV = b"""Student_PIDM,CRN
S1,1001
S2,1002
S3,1003
S4,1004
"""

ROOMS_CSV = b"""Room,Capacity
Hall A,70
Room B,40
"""


class FakeDatasetRepo:
    """In-memory stand-in for DatasetRepo."""

    def __init__(self):
        self.created = []

    def dataset_exists(self, dataset_name, user_id):
        return False

    def create(self, dataset):
        self.created.append(dataset)
        return dataset


class FakeStorage:
    """Records storage calls instead of talking to S3."""

    def __init__(self):
        self.uploaded_keys = []

    async def upload_file(self, content, key):
        self.uploaded_keys.append(key)
        return None, key

    def delete_file(self, key):
        return True

    def delete_directory(self, prefix):
        return True


@pytest.fixture
def storage(monkeypatch):
    fake = FakeStorage()
    monkeypatch.setattr(service_module, "storage", fake)
    return fake


@pytest.fixture
def repo():
    return FakeDatasetRepo()


def _file(content: bytes, filename: str) -> UploadFile:
    return UploadFile(file=io.BytesIO(content), filename=filename)


async def _upload(repo, common_exams: bytes | None, courses: bytes = COURSES_CSV):
    service = DatasetService(repo)
    return await service.upload_dataset(
        dataset_name="Fall",
        courses_file=_file(courses, "courses.csv"),
        enrollments_file=_file(ENROLLMENTS_CSV, "enrollments.csv"),
        rooms_file=_file(ROOMS_CSV, "rooms.csv"),
        user_id=uuid4(),
        common_exams_file=(
            _file(common_exams, "common_exams.csv")
            if common_exams is not None
            else None
        ),
    )


async def test_valid_common_exams_saved_as_course_merges(repo, storage):
    result = await _upload(
        repo,
        b"ExamGroup,CRN\nCS Final,1001\nCS Final,1002\n",
    )

    assert repo.created[0].course_merges == {"CS Final": ["1001", "1002"]}
    metadata = result["files"]["common_exams"]
    assert metadata["exam_groups"] == 1
    assert metadata["merged_crns"] == 2
    assert metadata["over_capacity_groups"] == []
    assert any(key.endswith("/common_exams.csv") for key in storage.uploaded_keys)


async def test_unknown_crn_rejects_upload_before_storage(repo, storage):
    with pytest.raises(ValidationError) as exc_info:
        await _upload(repo, b"ExamGroup,CRN\nCS Final,1001\nCS Final,9999\n")

    error = exc_info.value.detail["errors"]["common_exams"]
    assert "CS Final" in error
    assert "9999" in error
    assert storage.uploaded_keys == []
    assert repo.created == []


async def test_crn_in_two_groups_rejects_upload_before_storage(repo, storage):
    with pytest.raises(ValidationError) as exc_info:
        await _upload(
            repo,
            b"ExamGroup,CRN\nA,1001\nA,1002\nB,1002\nB,1004\n",
        )

    error = exc_info.value.detail["errors"]["common_exams"]
    assert "1002" in error
    assert "'A'" in error
    assert "'B'" in error
    assert storage.uploaded_keys == []
    assert repo.created == []


async def test_over_capacity_group_is_saved_with_warning(repo, storage):
    result = await _upload(
        repo,
        b"ExamGroup,CRN\nCS Final,1001\nCS Final,1002\n"
        b"Science Final,1003\nScience Final,1004\n",
    )

    assert repo.created[0].course_merges == {
        "CS Final": ["1001", "1002"],
        "Science Final": ["1003", "1004"],
    }
    assert result["files"]["common_exams"]["over_capacity_groups"] == [
        {"group": "Science Final", "total_enrollment": 80, "max_room_capacity": 70}
    ]


async def test_zero_enrollment_course_does_not_block_validation(repo, storage):
    courses = COURSES_CSV + b"1005,ART 1000,0\n"

    await _upload(
        repo,
        b"ExamGroup,CRN\nCS Final,1001\nCS Final,1002\n",
        courses=courses,
    )

    assert repo.created[0].course_merges == {"CS Final": ["1001", "1002"]}


async def test_zero_enrollment_crn_in_group_rejected_with_clear_reason(repo, storage):
    courses = COURSES_CSV + b"1005,ART 1000,0\n"

    with pytest.raises(ValidationError) as exc_info:
        await _upload(
            repo,
            b"ExamGroup,CRN\nMixed,1001\nMixed,1005\nMixed,9999\n",
            courses=courses,
        )

    error = exc_info.value.detail["errors"]["common_exams"]
    assert "zero enrollment" in error and "1005" in error
    assert "not found in courses: ['9999']" in error
    assert storage.uploaded_keys == []


async def test_no_common_exams_file_leaves_course_merges_unset(repo, storage):
    result = await _upload(repo, None)

    assert repo.created[0].course_merges is None
    assert "common_exams" not in result["files"]
