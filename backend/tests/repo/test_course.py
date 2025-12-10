from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from src.repo.course import CourseRepo


@pytest.fixture
def session():
    return MagicMock()


@pytest.fixture
def repo(session):
    return CourseRepo(session)


def test_get_by_crn(repo, session):
    dataset_id = uuid4()
    crn = "123"

    expected_course = MagicMock()
    session.execute.return_value.scalars.return_value.first.return_value = (
        expected_course
    )

    result = repo.get_by_crn(crn, dataset_id)

    session.execute.assert_called_once()
    session.execute.return_value.scalars.assert_called_once()
    session.execute.return_value.scalars.return_value.first.assert_called_once()
    assert result is expected_course


def test_get_by_crn_not_found(repo, session):
    dataset_id = uuid4()
    crn = "123"

    session.execute.return_value.scalars.return_value.first.return_value = None

    result = repo.get_by_crn(crn, dataset_id)

    session.execute.assert_called_once()
    session.execute.return_value.scalars.assert_called_once()
    session.execute.return_value.scalars.return_value.first.assert_called_once()
    assert result is None
