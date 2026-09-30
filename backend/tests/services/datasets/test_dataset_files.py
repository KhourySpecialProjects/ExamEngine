"""
Tests for loading stored dataset files back for scheduling.

Storage and the dataset repository are faked; the real parsing and
zero-enrollment filtering run.
"""

from types import SimpleNamespace
from uuid import uuid4

import pytest

import src.services.dataset.service as service_module
from src.domain.factories.dataset_factory import DatasetFactory
from src.services.dataset.service import DatasetService


STORED_FILES = {
    "courses/key": b"CRN,CourseID,Enrollment\n11310,CS 2500,2\n11311,CS 2510,0\n",
    "enrollments/key": (
        b"Student_PIDM,CRN\n001234567,11310\n000000042,11310\n000000042,11311\n"
    ),
    "rooms/key": b"Room,Capacity\nHall A,70\n",
}


class FakeDatasetRepo:
    """Returns one dataset whose files live in FakeStorage."""

    def get_by_id_for_user(self, dataset_id, user_id):
        return SimpleNamespace(
            file_paths=[
                {"type": key.split("/")[0], "storage_key": key} for key in STORED_FILES
            ]
        )


class FakeStorage:
    """Serves STORED_FILES instead of talking to S3."""

    def download_file(self, key):
        return STORED_FILES[key]


@pytest.fixture(autouse=True)
def storage(monkeypatch):
    monkeypatch.setattr(service_module, "storage", FakeStorage())


async def test_stored_student_ids_keep_leading_zeros_for_scheduling():
    service = DatasetService(FakeDatasetRepo())

    files = await service.drop_zero_enrollment(uuid4(), uuid4())

    assert files["enrollments"]["Student_PIDM"].tolist() == [
        "001234567",
        "000000042",
    ]
    dataset = DatasetFactory.from_dataframes_to_scheduling_dataset(
        courses_df=files["courses"],
        enrollment_df=files["enrollments"],
        rooms_df=files["rooms"],
    )
    assert dataset.students_by_crn == {"11310": frozenset({"001234567", "000000042"})}
