"""Schedule read access and deletion against the Postgres test database."""

from sqlalchemy import select

from src.repo.schedule import ScheduleRepo
from src.schemas.db import Schedules, ScheduleShares
from tests.db.builders import make_schedule, make_user, share_schedule


def test_owner_and_recipient_can_read_a_shared_schedule_but_a_stranger_cannot(
    db_session,
):
    owner = make_user(db_session, "Owner")
    recipient = make_user(db_session, "Recipient")
    stranger = make_user(db_session, "Stranger")
    schedule = make_schedule(db_session, owner)
    share_schedule(db_session, schedule, owner, recipient)
    repo = ScheduleRepo(db_session)

    assert repo.get_by_id_for_user(schedule.schedule_id, owner.user_id) is schedule
    assert repo.get_by_id_for_user(schedule.schedule_id, recipient.user_id) is schedule
    assert repo.get_by_id_for_user(schedule.schedule_id, stranger.user_id) is None


def test_schedule_list_has_own_and_shared_schedules_only(db_session):
    me = make_user(db_session, "Me")
    colleague = make_user(db_session, "Colleague")
    mine = make_schedule(db_session, me, name="Mine")
    shared_with_me = make_schedule(db_session, colleague, name="Shared with me")
    make_schedule(db_session, colleague, name="Not shared")
    share_schedule(db_session, shared_with_me, colleague, me)

    listed = ScheduleRepo(db_session).get_all_for_user(me.user_id)

    assert {s.schedule_id for s in listed} == {
        mine.schedule_id,
        shared_with_me.schedule_id,
    }


def test_owner_delete_removes_the_schedule_and_its_shares(db_session):
    owner = make_user(db_session, "Owner")
    recipient = make_user(db_session, "Recipient")
    schedule = make_schedule(db_session, owner)
    share_schedule(db_session, schedule, owner, recipient)
    schedule_id = schedule.schedule_id

    assert ScheduleRepo(db_session).delete_schedule_cascade(schedule_id, owner.user_id)

    assert db_session.get(Schedules, schedule_id) is None
    shares = db_session.execute(
        select(ScheduleShares).where(ScheduleShares.schedule_id == schedule_id)
    ).all()
    assert shares == []
