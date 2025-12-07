from unittest.mock import MagicMock
from src.repo.base import BaseRepo


class Model:
    pass


def test_create():
    session = MagicMock()
    repo = BaseRepo(Model, session)

    exp_res = MagicMock()
    act_res = repo.create()

    assert act_res is exp_res

    session.add.assert_called_once_with(exp_res)
    session.commit.assert_called_once()
    session.refresh.assert_called_once_with(exp_res)
