"""Shared fakes for dataset upload tests."""

import pytest

import src.services.dataset.service as service_module


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
