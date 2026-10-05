"""POST /api/schedule/{id}/late-add/search against the Postgres test database."""

import asyncio
import datetime
import json
import uuid
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from sqlalchemy import func, select

from src.api.deps import get_current_user, get_db
from src.api.routes import schedule
from src.domain.constants import BLOCK_TIMES
from src.schemas.db import (
    Courses,
    Datasets,
    DayEnum,
    ExamAssignments,
    Rooms,
    Runs,
    Schedules,
    TimeSlots,
)
from tests.db.builders import make_dataset, make_schedule, make_user, share_schedule


SETTINGS = {
    "algorithm": "dsatur",
    "max_days": 1,
    "blocks_per_day": 4,
    "student_max_per_day": 3,
    "instructor_max_per_day": 3,
}

FILES = {
    "k/courses.csv": b"CRN,CourseID,num_students,Instructor Name\n"
    b"101,SUBJ 1001,1,I-1\n102,SUBJ 1002,1,I-1\n103,LATE 2000,1,I-2\n"
    b"950,SUBJ 9500,0,I-9\n960,SUBJ 9600,0,I-9\n970,SUBJ 9700,1,I-9\n",
    "k/enrollments.csv": b"Student_PIDM,CRN\n"
    b"S1,101\nS3,103\nS1,900\nS2,900\nS3,900\nS2,900\nS4,950\nS4,970\n"
    + b"".join(f"B{n},990\n".encode() for n in range(60)),
    "k/rooms.csv": b"room_name,capacity\nHall A,50\nRoom B,5\n",
    "k/room_blockouts.csv": b"Room,Day,Block\nRoom B,0,1\n",
}

LATE = {"crn": "900", "course_code": "LATE 2000", "instructor_id": "I-1"}


def _post(app: FastAPI, path: str, body: dict) -> tuple[int, dict]:
    """Drive the ASGI app directly (httpx is not a test dependency)."""
    messages: list[dict] = []
    payload = json.dumps(body).encode()

    async def receive() -> dict:
        return {"type": "http.request", "body": payload, "more_body": False}

    async def send(message: dict) -> None:
        messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [(b"content-type", b"application/json")],
        "client": ("test", 1),
        "server": ("test", 80),
    }
    asyncio.run(app(scope, receive, send))
    status = next(m["status"] for m in messages if m["type"] == "http.response.start")
    raw = b"".join(
        m.get("body", b"") for m in messages if m["type"] == "http.response.body"
    )
    return status, json.loads(raw)


def _app(db_session, user) -> FastAPI:
    app = FastAPI()
    app.include_router(schedule.router, prefix="/api")
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: user
    return app


def _add(db, sched, rooms, crn, course, instructor, slot=None, room=None):
    """An exam with a real block label; ``slot`` is (day name, block index)."""
    dataset_id = sched.run.dataset_id
    course_row = Courses(
        crn=crn,
        course_subject_code=course,
        instructor_name=instructor,
        enrollment_count=1,
        dataset_id=dataset_id,
    )
    db.add(course_row)
    time_slot = None
    if slot is not None:
        day, block = slot
        time_slot = TimeSlots(
            slot_label=BLOCK_TIMES[block],
            day=DayEnum(day),
            start_time=datetime.time(9 + block),
            end_time=datetime.time(11 + block),
            dataset_id=dataset_id,
        )
        db.add(time_slot)
    db.flush()
    db.add(
        ExamAssignments(
            course_id=course_row.course_id,
            time_slot_id=time_slot.time_slot_id if time_slot else None,
            room_id=rooms[room].room_id if room else None,
            schedule_id=sched.schedule_id,
        )
    )
    db.flush()


def _base_schedule(db, owner):
    """Monday, 4 blocks: CRN 101 at 9AM in Hall A, 103 at 2PM in Room B, 102
    unscheduled. Room B is blocked out at 11:30AM."""
    dataset = make_dataset(db, owner)
    dataset.file_paths = [
        {"type": file_type, "storage_key": f"k/{file_type}.csv", "metadata": {}}
        for file_type in ("courses", "enrollments", "rooms", "room_blockouts")
    ]
    sched = make_schedule(db, owner, dataset=dataset, parameters=SETTINGS)
    rooms = {
        name: Rooms(location=name, capacity=capacity, dataset_id=dataset.dataset_id)
        for name, capacity in (("Hall A", 50), ("Room B", 5))
    }
    db.add_all(rooms.values())
    db.flush()
    _add(db, sched, rooms, "101", "SUBJ 1001", "I-1", ("Monday", 0), "Hall A")
    _add(db, sched, rooms, "102", "SUBJ 1002", "I-1")
    _add(db, sched, rooms, "103", "LATE 2000", "I-2", ("Monday", 2), "Room B")
    return sched


def _search(db, user, sched, body=LATE, files=FILES):
    with patch("src.api.deps.storage") as storage:
        storage.download_file.side_effect = files.get
        status, payload = _post(
            _app(db, user), f"/api/schedule/{sched.schedule_id}/late-add/search", body
        )
    return status, payload, storage


def _count(db, model) -> int:
    return db.execute(select(func.count()).select_from(model)).scalar_one()


def _slots(candidates) -> list[tuple[int, int]]:
    return [(c["day"], c["block"]) for c in candidates]


def test_owner_gets_ranked_clear_blocks_and_nothing_is_written(db_session):
    owner = make_user(db_session, "Owner")
    sched = _base_schedule(db_session, owner)
    runs, schedules = _count(db_session, Runs), _count(db_session, Schedules)

    status, body, _ = _search(db_session, owner, sched)

    assert status == 200, body
    assert (_count(db_session, Runs), _count(db_session, Schedules)) == (
        runs,
        schedules,
    )
    assert body["outcome"] == "clear"
    assert body["size"] == 3  # distinct students
    assert body["settings"] == {
        "max_days": 1,
        "blocks_per_day": 4,
        "student_max_per_day": 3,
        "instructor_max_per_day": 3,
    }
    # 9AM double-books S1 and the instructor; 2PM double-books S3.
    # 4:30PM: one back-to-back; 11:30AM: two, plus the instructor's.
    assert _slots(body["candidates"]) == [(0, 3), (0, 1)]
    best, second = body["candidates"]
    assert best["block_time"] == "4:30PM-6:30PM"
    assert best["room"] == {"name": "Room B", "capacity": 5}
    assert best["other_rooms"] == [{"name": "Hall A", "capacity": 50}]
    assert best["clear"] is True
    # Room B is blocked out at 11:30AM
    assert second["room"] == {"name": "Hall A", "capacity": 50}
    assert second["other_rooms"] == []
    assert second["conflicts"] == {
        "student_double_book": 0,
        "student_over_daily_limit": 0,
        "instructor_double_book": 0,
        "instructor_over_daily_limit": 0,
        "back_to_back_students": 2,
        "back_to_back_instructor": 1,
        "large_course_late": 0,
    }
    assert second["students"]["back_to_back"] == [
        {
            "student_id": "S1",
            "blocks": [0, 1],
            "block_times": ["9AM-11AM", "11:30AM-1:30PM"],
        },
        {
            "student_id": "S3",
            "blocks": [1, 2],
            "block_times": ["11:30AM-1:30PM", "2PM-4PM"],
        },
    ]
    assert second["instructor"]["back_to_back"] is True
    assert second["instructor"]["day_blocks"] == [0, 1]
    assert second["instructor"]["day_block_times"] == ["9AM-11AM", "11:30AM-1:30PM"]
    assert body["no_room_blocks"] == []
    assert [e["crn"] for e in body["instructor_exams"]] == ["101", "102"]
    assert body["instructor_exams"][1]["day"] is None
    assert [e["crn"] for e in body["sibling_sections"]] == ["103"]
    assert body["sibling_sections"][0]["room"] == "Room B"
    assert body["notes"] == []


def test_no_room_reports_largest_free_room_per_block(db_session):
    owner = make_user(db_session, "Owner")
    sched = _base_schedule(db_session, owner)

    status, body, _ = _search(
        db_session, owner, sched, {**LATE, "crn": "990", "course_code": "BIG 1"}
    )

    assert status == 200, body
    assert body["outcome"] == "no_room"
    assert body["candidates"] == []
    assert [
        (b["block"], b["largest_free_room"]["name"]) for b in body["no_room_blocks"]
    ] == [(0, "Room B"), (1, "Hall A"), (2, "Hall A"), (3, "Hall A")]


def test_courses_file_crn_with_zero_enrollment_is_allowed_with_a_note(db_session):
    owner = make_user(db_session, "Owner")
    sched = _base_schedule(db_session, owner)

    status, body, _ = _search(
        db_session, owner, sched, {**LATE, "crn": " 950 ", "course_code": "SUBJ 9500"}
    )

    assert status == 200, body
    assert body["crn"] == "950"
    assert any("zero enrollment" in note for note in body["notes"])


def test_unknown_instructor_is_noted(db_session):
    owner = make_user(db_session, "Owner")
    sched = _base_schedule(db_session, owner)

    status, body, _ = _search(
        db_session, owner, sched, {**LATE, "instructor_id": "I-404"}
    )

    assert status == 200, body
    assert body["instructor_exams"] == []
    assert any("I-404" in note for note in body["notes"])


def test_shared_viewer_and_stranger_get_404_and_nothing_is_downloaded(db_session):
    owner = make_user(db_session, "Owner")
    viewer = make_user(db_session, "Viewer")
    stranger = make_user(db_session, "Stranger")
    sched = _base_schedule(db_session, owner)
    share_schedule(db_session, sched, owner, viewer)

    for user in (viewer, stranger):
        status, body, storage = _search(db_session, user, sched)
        assert status == 404
        assert body["detail"] == f"Schedule {sched.schedule_id} not found"
        storage.download_file.assert_not_called()

    missing = SimpleNamespace(schedule_id=uuid.uuid4())
    assert _search(db_session, owner, missing)[0] == 404


def test_deleted_dataset_is_409_before_any_input_check(db_session):
    owner = make_user(db_session, "Owner")
    sched = _base_schedule(db_session, owner)
    db_session.get(Datasets, sched.run.dataset_id).deleted_at = datetime.datetime.now()
    db_session.flush()

    status, body, storage = _search(db_session, owner, sched, {**LATE, "crn": ""})

    assert status == 409
    assert body["detail"] == "The dataset's uploaded files are no longer available"
    storage.download_file.assert_not_called()


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"crn": " "}, "Enter the CRN."),
        ({"course_code": ""}, "Enter the course code."),
        ({"instructor_id": "  "}, "Enter the instructor ID."),
        ({"instructor_id": " NaN "}, "Enter the instructor ID."),
        ({"instructor_id": "nan"}, "Enter the instructor ID."),
        (
            {"crn": "101"},
            "CRN 101 is already in this schedule (Monday 9AM-11AM in Hall A).",
        ),
        ({"crn": "102"}, "CRN 102 is already in this schedule, unscheduled."),
        ({"crn": "960"}, "CRN 960 has no rows in enrollments.csv."),
        (
            {"crn": "970"},
            "CRN 970 is a scheduled course in courses.csv, not a late add.",
        ),
    ],
)
def test_bad_input_is_400_with_a_clear_message(db_session, change, message):
    owner = make_user(db_session, "Owner")
    sched = _base_schedule(db_session, owner)

    status, body, _ = _search(db_session, owner, sched, {**LATE, **change})

    assert status == 400
    assert body["detail"].startswith(message)


def test_unavailable_enrollments_file_is_an_error_not_an_empty_result(db_session):
    owner = make_user(db_session, "Owner")
    sched = _base_schedule(db_session, owner)
    files = {k: v for k, v in FILES.items() if "enrollments" not in k}

    status, body, _ = _search(db_session, owner, sched, files=files)

    assert status == 500
    assert "uploaded files" in body["detail"]
