"""One person's exams in a schedule, against the Postgres test database."""

import datetime

import pytest

from src.core.exceptions import DatasetDeletedError, StorageError, ValidationError
from src.repo.dataset import DatasetRepo
from src.repo.exam_assignment import ExamAssignmentRepo
from src.repo.schedule import ScheduleRepo
from src.services.schedule.person_exams import PersonExamsService
from tests.db.builders import (
    add_exam,
    make_dataset,
    make_schedule,
    make_user,
    share_schedule,
)


FILES = {
    "k/courses.csv": b"CRN,CourseID,num_students,Instructor Name\n"
    b"100,CS1,2,I-1\n200,CS2,2,I-2\n300,CS3,1,I-1\n400,CS4,1,I-2\n",
    # 900 is enrolled but not in the schedule.
    "k/enrollments.csv": b"Student_PIDM,CRN\n"
    b"001234567,100\n001234567,200\n001234567,400\n001234567,900\n"
    b"007654321,300\n",
    "k/rooms.csv": b"room_name,capacity\nHall,40\n",
}


class FakeStorage:
    def __init__(self, files: dict[str, bytes]):
        self.files = files
        self.downloaded: list[str] = []

    def download_file(self, key: str) -> bytes | None:
        self.downloaded.append(key)
        return self.files.get(key)


@pytest.fixture
def world(db_session):
    """A schedule with a double-book for student 001234567 and instructor I-1.

    100 and 200 share Monday 9AM; 400 is unscheduled; 300 is Tuesday's last
    block without a room.
    """
    owner = make_user(db_session, "Owner")
    dataset = make_dataset(db_session, owner)
    dataset.file_paths = [
        {"type": file_type, "storage_key": f"k/{file_type}.csv", "metadata": {}}
        for file_type in ("courses", "enrollments", "rooms")
    ]
    schedule = make_schedule(
        db_session,
        owner,
        dataset=dataset,
        parameters={"max_days": 3, "blocks_per_day": 4},
    )
    add_exam(
        db_session,
        schedule,
        "200",
        2,
        block=("Monday", 0),
        room=("Hall", 40),
        instructor="I-2",
    )
    add_exam(
        db_session,
        schedule,
        "100",
        2,
        block=("Monday", 0),
        room=("Lab", 40),
        instructor="I-1",
    )
    add_exam(db_session, schedule, "300", 1, block=("Tuesday", 3), instructor="I-1")
    add_exam(db_session, schedule, "400", 1, instructor=" I-2 ")
    storage = FakeStorage(FILES)
    service = PersonExamsService(
        ScheduleRepo(db_session),
        ExamAssignmentRepo(db_session),
        DatasetRepo(db_session),
        storage,
    )
    return {
        "owner": owner,
        "dataset": dataset,
        "schedule": schedule,
        "service": service,
        "storage": storage,
    }


def _rows(result):
    return [(e.crn, e.day_name, e.block_time, e.room) for e in result.exams]


async def test_student_exams_come_from_the_enrollments_file_in_week_order(world):
    result = await world["service"].get(
        world["schedule"].schedule_id, world["owner"].user_id, "student", "001234567"
    )

    # Leading zeros kept; same-block exams both listed; unscheduled last;
    # an enrolled CRN that isn't in the schedule is skipped.
    assert _rows(result) == [
        ("100", "Monday", "9AM-11AM", "Lab"),
        ("200", "Monday", "9AM-11AM", "Hall"),
        ("400", None, None, None),
    ]
    assert result.exams[0].course_code == "TEST 100"
    assert (result.exams[0].day, result.exams[0].block) == (0, 0)
    assert result.days == ["Monday", "Tuesday", "Wednesday"]
    assert result.block_times == [
        "9AM-11AM",
        "11:30AM-1:30PM",
        "2PM-4PM",
        "4:30PM-6:30PM",
    ]


async def test_instructor_exams_come_from_the_schedule_without_reading_files(world):
    result = await world["service"].get(
        world["schedule"].schedule_id, world["owner"].user_id, "instructor", " I-1 "
    )

    assert result.person_id == "I-1"
    assert _rows(result) == [
        ("100", "Monday", "9AM-11AM", "Lab"),
        ("300", "Tuesday", "4:30PM-6:30PM", None),
    ]
    assert world["storage"].downloaded == []


async def test_stored_instructor_ids_are_matched_trimmed(world):
    result = await world["service"].get(
        world["schedule"].schedule_id, world["owner"].user_id, "instructor", "I-2"
    )

    assert [e.crn for e in result.exams] == ["200", "400"]


async def test_share_recipient_may_look_but_a_stranger_gets_none(world, db_session):
    recipient = make_user(db_session, "Recipient")
    stranger = make_user(db_session, "Stranger")
    share_schedule(db_session, world["schedule"], world["owner"], recipient)
    schedule_id = world["schedule"].schedule_id

    shared = await world["service"].get(
        schedule_id, recipient.user_id, "student", "007654321"
    )
    assert [e.crn for e in shared.exams] == ["300"]
    assert (
        await world["service"].get(
            schedule_id, stranger.user_id, "student", "007654321"
        )
        is None
    )
    assert world["storage"].downloaded.count("k/enrollments.csv") == 1


async def test_unknown_id_gets_an_empty_list(world):
    result = await world["service"].get(
        world["schedule"].schedule_id, world["owner"].user_id, "student", "999"
    )

    assert result.exams == []


async def test_grid_covers_exams_past_the_recorded_window(world, db_session):
    """Old runs record no max_days; the week still reaches the last used day."""
    schedule = make_schedule(db_session, world["owner"], dataset=world["dataset"])
    add_exam(db_session, schedule, "100", 2, block=("Thursday", 4), instructor="I-1")

    result = await world["service"].get(
        schedule.schedule_id, world["owner"].user_id, "instructor", "I-1"
    )

    assert result.days == ["Monday", "Tuesday", "Wednesday", "Thursday"]
    assert len(result.block_times) == 5


async def test_blank_id_is_rejected(world):
    with pytest.raises(ValidationError):
        await world["service"].get(
            world["schedule"].schedule_id, world["owner"].user_id, "student", "  "
        )


async def test_student_lookup_fails_clearly_without_the_enrollments_file(world):
    world["storage"].files = {k: v for k, v in FILES.items() if "enroll" not in k}
    with pytest.raises(StorageError):
        await world["service"].get(
            world["schedule"].schedule_id, world["owner"].user_id, "student", "1"
        )

    world["dataset"].deleted_at = datetime.datetime.now()
    with pytest.raises(DatasetDeletedError):
        await world["service"].get(
            world["schedule"].schedule_id, world["owner"].user_id, "student", "1"
        )
    # Instructors don't need the files.
    result = await world["service"].get(
        world["schedule"].schedule_id, world["owner"].user_id, "instructor", "I-1"
    )
    assert len(result.exams) == 2


async def test_student_lookup_reads_only_the_enrollments_file(world):
    """Another file failing to download doesn't break (or get blamed for) it."""
    world["storage"].files = {k: v for k, v in FILES.items() if "rooms" not in k}

    result = await world["service"].get(
        world["schedule"].schedule_id, world["owner"].user_id, "student", "007654321"
    )

    assert [e.crn for e in result.exams] == ["300"]
    assert world["storage"].downloaded == ["k/enrollments.csv"]
