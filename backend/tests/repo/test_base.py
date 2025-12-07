from unittest.mock import MagicMock

import pytest

from src.repo.base import BaseRepo


class Model:
    pass


@pytest.fixture
def session():
    return MagicMock()


@pytest.fixture
def repo(session):
    return BaseRepo(Model, session)


def test_create(repo, session):
    object = Model()
    res = repo.create(object)

    assert res is object
    session.add.assert_called_once_with(object)
    session.commit.assert_called_once()
    session.refresh.assert_called_once_with(object)


def test_update(repo, session):
    object = Model()
    res = repo.update(object)

    assert res is object
    session.commit.assert_called_once()
    session.refresh.assert_called_once_with(object)


def test_delete(repo, session):
    object = Model()
    repo.delete(object)

    session.delete.assert_called_once_with(object)
    session.commit.assert_called_once()
