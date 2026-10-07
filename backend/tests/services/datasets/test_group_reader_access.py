"""Who may read a dataset's combined/common groups, against the Postgres test DB."""

import pytest

from src.core.exceptions import DatasetNotFoundError
from src.repo.dataset import DatasetRepo
from src.services.dataset.service import DatasetService
from tests.db.builders import make_dataset, make_schedule, make_user, share_schedule


@pytest.fixture
def world(db_session):
    owner = make_user(db_session, "Owner")
    dataset = make_dataset(db_session, owner)
    dataset.course_merges = {"CS 1 Combined": ["100", "101"]}
    dataset.common_exam_groups = {"CS 2 Common": ["200", "201"]}
    other_dataset = make_dataset(db_session, owner)
    db_session.flush()
    return {
        "owner": owner,
        "dataset": dataset,
        "schedule": make_schedule(db_session, owner, dataset=dataset),
        "other_schedule": make_schedule(db_session, owner, dataset=other_dataset),
        "service": DatasetService(DatasetRepo(db_session)),
    }


def test_owner_and_a_recipient_of_one_of_its_schedules_read_the_groups(
    world, db_session
):
    recipient = make_user(db_session, "Recipient")
    share_schedule(db_session, world["schedule"], world["owner"], recipient)
    dataset_id = world["dataset"].dataset_id

    for user in (world["owner"], recipient):
        dataset = world["service"].get_groups_for_viewer(dataset_id, user.user_id)
        assert dataset.course_merges == {"CS 1 Combined": ["100", "101"]}
        assert dataset.common_exam_groups == {"CS 2 Common": ["200", "201"]}


def test_a_recipient_of_another_datasets_schedule_or_a_stranger_gets_none(
    world, db_session
):
    other_recipient = make_user(db_session, "Other recipient")
    share_schedule(db_session, world["other_schedule"], world["owner"], other_recipient)
    stranger = make_user(db_session, "Stranger")

    for user in (other_recipient, stranger):
        with pytest.raises(DatasetNotFoundError):
            world["service"].get_groups_for_viewer(
                world["dataset"].dataset_id, user.user_id
            )


def test_generation_still_reads_groups_for_the_owner_only(world, db_session):
    recipient = make_user(db_session, "Recipient")
    share_schedule(db_session, world["schedule"], world["owner"], recipient)

    with pytest.raises(DatasetNotFoundError):
        world["service"].get_merges(world["dataset"].dataset_id, recipient.user_id)
