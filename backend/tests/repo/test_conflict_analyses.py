from uuid import uuid4
from unittest.mock import MagicMock

import pytest

from src.repo.conflict_analyses import ConflictAnalysesRepo

@pytest.fixture
def session():
    return MagicMock()

@pytest.fixture
def repo(session):
    return ConflictAnalysesRepo(session)

def test_get_by_schedule_id(repo, session):
    schedule_id = uuid4()
    expected_analysis = MagicMock()
    session.execute.return_value.scalars.return_value.first.return_value = expected_analysis

    result = repo.get_by_schedule_id(schedule_id)

    session.execute.assert_called_once()
    assert result == expected_analysis

def test_create_analysis(repo, session):
    schedule_id = uuid4()
    conflicts_data = {"conflict_count": 5}

    result = repo.create_analysis(schedule_id, conflicts_data)

    session.add.assert_called_once()
    session.commit.assert_called_once()
    session.refresh.assert_called_once_with(result)
    assert result.schedule_id == schedule_id
    assert result.conflicts == conflicts_data