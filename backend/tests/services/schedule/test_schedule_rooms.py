"""A schedule's rooms and blocked times, against the Postgres test database."""

import datetime

import pytest

from src.repo.dataset import DatasetRepo
from src.repo.exam_assignment import ExamAssignmentRepo
from src.repo.room import RoomRepo
from src.repo.schedule import ScheduleRepo
from src.schemas.db import Rooms
from src.services.schedule.rooms import ScheduleRoomsService
from tests.db.builders import (
    add_exam,
    make_dataset,
    make_schedule,
    make_user,
    share_schedule,
)


BLOCKOUTS_KEY = "k/room_blockouts.csv"
# Hall: Monday 2PM and Monday 9AM (out of order); Lab: Tuesday 9AM; "Ghost" is
# not a room of the dataset.
BLOCKOUTS = b"Room,Day,Block\nHall,0,2\nHall,Monday,9AM-11AM\nLab,Tuesday,0\n"
BLOCKOUTS += b"Ghost,Monday,1\n"


class FakeStorage:
    def __init__(self, files: dict[str, bytes]):
        self.files = files
        self.downloaded: list[str] = []

    def download_file(self, key: str) -> bytes | None:
        self.downloaded.append(key)
        return self.files.get(key)


@pytest.fixture
def world(db_session):
    """Rooms Lab (30) and Hall (40, two exams on Monday 9AM), and Empty (10)."""
    owner = make_user(db_session, "Owner")
    dataset = make_dataset(db_session, owner)
    dataset.file_paths = [
        {"type": file_type, "storage_key": f"k/{file_type}.csv", "metadata": {}}
        for file_type in ("courses", "enrollments", "rooms", "room_blockouts")
    ]
    schedule = make_schedule(
        db_session,
        owner,
        dataset=dataset,
        parameters={"max_days": 3, "blocks_per_day": 4},
    )
    add_exam(db_session, schedule, "100", 20, block=("Monday", 0), room=("Hall", 40))
    db_session.add_all(
        [
            Rooms(location="Lab", capacity=30, dataset_id=dataset.dataset_id),
            Rooms(location="Empty", capacity=10, dataset_id=dataset.dataset_id),
        ]
    )
    db_session.flush()
    storage = FakeStorage({BLOCKOUTS_KEY: BLOCKOUTS})
    service = ScheduleRoomsService(
        ScheduleRepo(db_session),
        ExamAssignmentRepo(db_session),
        DatasetRepo(db_session),
        RoomRepo(db_session),
        storage,
    )
    return {
        "owner": owner,
        "dataset": dataset,
        "schedule": schedule,
        "service": service,
        "storage": storage,
    }


def _blocked(result):
    return {
        room.name: [(s.day_name, s.block_time) for s in room.blocked]
        for room in result.rooms
    }


async def test_every_room_with_its_blocked_slots_from_the_blockouts_file(world):
    result = await world["service"].get(
        world["schedule"].schedule_id, world["owner"].user_id
    )

    assert [(r.name, r.capacity) for r in result.rooms] == [
        ("Empty", 10),
        ("Hall", 40),
        ("Lab", 30),
    ]
    assert result.blockouts == "ok"
    assert _blocked(result) == {
        "Empty": [],
        "Hall": [("Monday", "9AM-11AM"), ("Monday", "2PM-4PM")],
        "Lab": [("Tuesday", "9AM-11AM")],
    }
    assert result.days == ["Monday", "Tuesday", "Wednesday"]
    assert len(result.block_times) == 4
    assert world["storage"].downloaded == [BLOCKOUTS_KEY]


async def test_share_recipient_may_look_but_a_stranger_gets_none(world, db_session):
    recipient = make_user(db_session, "Recipient")
    stranger = make_user(db_session, "Stranger")
    share_schedule(db_session, world["schedule"], world["owner"], recipient)
    schedule_id = world["schedule"].schedule_id

    shared = await world["service"].get(schedule_id, recipient.user_id)

    assert _blocked(shared)["Lab"] == [("Tuesday", "9AM-11AM")]
    assert await world["service"].get(schedule_id, stranger.user_id) is None


async def test_rooms_without_an_uploaded_blockouts_file(world):
    world["dataset"].file_paths = [
        entry
        for entry in world["dataset"].file_paths
        if entry["type"] != "room_blockouts"
    ]

    result = await world["service"].get(
        world["schedule"].schedule_id, world["owner"].user_id
    )

    assert result.blockouts == "none_uploaded"
    assert len(result.rooms) == 3
    assert world["storage"].downloaded == []


@pytest.mark.parametrize(
    "break_files",
    [
        pytest.param(lambda world: world["storage"].files.clear(), id="missing"),
        pytest.param(
            lambda world: world["storage"].files.update(
                {BLOCKOUTS_KEY: b"no,such,columns\n1,2,3\n"}
            ),
            id="unparseable",
        ),
        pytest.param(
            lambda world: setattr(
                world["dataset"], "deleted_at", datetime.datetime.now()
            ),
            id="dataset-deleted",
        ),
    ],
)
async def test_unreadable_blockouts_still_list_the_rooms(world, break_files):
    break_files(world)

    result = await world["service"].get(
        world["schedule"].schedule_id, world["owner"].user_id
    )

    assert result.blockouts == "unavailable"
    assert [r.name for r in result.rooms] == ["Empty", "Hall", "Lab"]
    assert all(r.blocked == [] for r in result.rooms)
