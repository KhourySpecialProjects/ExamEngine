"""
Datasets uploaded before combined and common exams were split stored the
combined (merge) file under type "common_exams" with `exam_groups` metadata.
They must keep loading as combined exams, not be parsed as the new common file.
"""

from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

import src.services.dataset.service as service_module
from src.services.dataset.service import DatasetService


STORED_FILES = {
    "courses/key": b"CRN,CourseID,Enrollment\n11310,CS 2500,2\n11311,CS 2510,3\n",
    "enrollments/key": b"Student_PIDM,CRN\n000000001,11310\n000000002,11311\n",
    "rooms/key": b"Room,Capacity\nHall A,70\n",
    "legacy/key": b"ExamGroup,CRN\nCS Final,11310\nCS Final,11311\n",
}

LEGACY_METADATA = {"rows": 2, "exam_groups": 1, "merged_crns": 2}


class FakeDatasetRepo:
    def get_by_id_for_user(self, dataset_id, user_id):
        return SimpleNamespace(
            dataset_id=dataset_id,
            dataset_name="Uploaded before the split",
            upload_date=datetime(2026, 9, 26),
            file_paths=[
                {"type": "courses", "storage_key": "courses/key", "metadata": {}},
                {
                    "type": "enrollments",
                    "storage_key": "enrollments/key",
                    "metadata": {},
                },
                {"type": "rooms", "storage_key": "rooms/key", "metadata": {}},
                {
                    "type": "common_exams",
                    "storage_key": "legacy/key",
                    "metadata": LEGACY_METADATA,
                },
            ],
        )


class FakeStorage:
    def download_file(self, key):
        return STORED_FILES[key]


@pytest.fixture(autouse=True)
def storage(monkeypatch):
    monkeypatch.setattr(service_module, "storage", FakeStorage())


async def test_legacy_file_loads_as_combined_exams():
    files = await DatasetService(FakeDatasetRepo()).get_dataset_files(uuid4(), uuid4())

    assert "common_exams" not in files
    assert files["combined_exams"]["ExamGroup"].tolist() == ["CS Final", "CS Final"]


def test_legacy_file_is_reported_as_combined_exams():
    info = DatasetService(FakeDatasetRepo()).get_dataset_info(uuid4(), uuid4())

    assert "common_exams" not in info["files"]
    assert info["files"]["combined_exams"] == LEGACY_METADATA
