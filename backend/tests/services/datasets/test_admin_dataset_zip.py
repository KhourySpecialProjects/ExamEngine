"""
Tests for the admin dataset zip download.

Storage and the dataset repository are faked; the real zip building runs.
"""

import io
import zipfile
from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

import src.services.dataset.service as service_module
from src.core.exceptions import DatasetNotFoundError, StorageError
from src.services.dataset.service import DatasetService


STORED_FILES = {
    "d/courses.csv": b"CRN,CourseID,Enrollment\n11310,CS 2500,2\n",
    "d/enrollments.csv": b"Student_PIDM,CRN\n001234567,11310\n",
    "d/rooms.csv": b"Room,Capacity\nHall A,70\n",
    # Uploaded before the combined/common split: a combined file stored as
    # "common_exams" with exam_groups metadata.
    "d/common_exams.csv": b"Group,CRN\nG1,11310\n",
}

FILE_PATHS = [
    {"type": "courses", "storage_key": "d/courses.csv", "metadata": {}},
    {"type": "enrollments", "storage_key": "d/enrollments.csv", "metadata": {}},
    {"type": "rooms", "storage_key": "d/rooms.csv", "metadata": {}},
    {
        "type": "common_exams",
        "storage_key": "d/common_exams.csv",
        "metadata": {"exam_groups": 1},
    },
]


class FakeDatasetRepo:
    """Returns the given dataset for any id, ignoring ownership."""

    def __init__(self, dataset):
        self.dataset = dataset

    def get_by_id(self, dataset_id):
        return self.dataset


class FakeStorage:
    """Serves STORED_FILES; unknown keys behave like a failed S3 download."""

    def download_file(self, key):
        return STORED_FILES.get(key)


@pytest.fixture(autouse=True)
def storage(monkeypatch):
    monkeypatch.setattr(service_module, "storage", FakeStorage())


def make_dataset(file_paths=FILE_PATHS, name="Fall 2026", deleted_at=None):
    return SimpleNamespace(
        dataset_name=name, deleted_at=deleted_at, file_paths=file_paths
    )


async def test_zip_holds_every_stored_file_named_by_type():
    service = DatasetService(FakeDatasetRepo(make_dataset()))

    _, content = await service.build_dataset_zip(uuid4())

    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
    assert files == {
        "courses.csv": STORED_FILES["d/courses.csv"],
        "enrollments.csv": STORED_FILES["d/enrollments.csv"],
        "rooms.csv": STORED_FILES["d/rooms.csv"],
        "combined_exams.csv": STORED_FILES["d/common_exams.csv"],
    }


@pytest.mark.parametrize(
    ("dataset_name", "filename"),
    [
        ("Fall 2026", "Fall_2026.zip"),
        ('Spring "26" / final', "Spring_26_final.zip"),
        ("../..", "dataset.zip"),
    ],
)
async def test_download_filename_is_header_safe(dataset_name, filename):
    service = DatasetService(FakeDatasetRepo(make_dataset(name=dataset_name)))

    name, _ = await service.build_dataset_zip(uuid4())

    assert name == filename


@pytest.mark.parametrize(
    "dataset", [None, make_dataset(deleted_at=datetime(2026, 9, 1))]
)
async def test_missing_or_deleted_dataset_is_not_found(dataset):
    service = DatasetService(FakeDatasetRepo(dataset))

    with pytest.raises(DatasetNotFoundError):
        await service.build_dataset_zip(uuid4())


async def test_missing_stored_object_fails_instead_of_partial_zip():
    missing = {"type": "rooms", "storage_key": "d/gone.csv", "metadata": {}}
    service = DatasetService(
        FakeDatasetRepo(make_dataset(file_paths=[*FILE_PATHS[:2], missing]))
    )

    with pytest.raises(StorageError):
        await service.build_dataset_zip(uuid4())
