"""GET /api/schedule/compare against the Postgres test database."""

import asyncio
import json
import uuid
from urllib.parse import urlencode

from fastapi import FastAPI

from src.api.deps import get_current_user, get_db
from src.api.routes import schedule
from tests.db.builders import (
    add_exam,
    make_dataset,
    make_schedule,
    make_user,
    save_analysis,
    share_schedule,
)


def _get(app: FastAPI, path: str, params: list[tuple[str, str]]) -> tuple[int, dict]:
    """Drive the ASGI app directly (httpx is not a test dependency)."""
    messages: list[dict] = []

    async def receive() -> dict:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict) -> None:
        messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": urlencode(params).encode(),
        "root_path": "",
        "headers": [],
        "client": ("test", 1),
        "server": ("test", 80),
    }
    asyncio.run(app(scope, receive, send))
    status = next(m["status"] for m in messages if m["type"] == "http.response.start")
    body = b"".join(
        m.get("body", b"") for m in messages if m["type"] == "http.response.body"
    )
    return status, json.loads(body)


def _app(db_session, user) -> FastAPI:
    app = FastAPI()
    app.include_router(schedule.router, prefix="/api")
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: user
    return app


def _compare(app: FastAPI, *ids) -> tuple[int, dict]:
    return _get(app, "/api/schedule/compare", [("ids", str(i)) for i in ids])


def test_unviewable_and_missing_schedules_are_unavailable_and_reveal_nothing(
    db_session,
):
    me = make_user(db_session, "Me")
    colleague = make_user(db_session, "Colleague")
    mine = make_schedule(db_session, me, name="Mine")
    shared = make_schedule(db_session, colleague, name="Shared with me")
    share_schedule(db_session, shared, colleague, me)
    private = make_schedule(db_session, colleague, name="Private")
    missing = uuid.uuid4()

    status, body = _compare(
        _app(db_session, me),
        private.schedule_id,
        mine.schedule_id,
        missing,
        shared.schedule_id,
    )

    assert status == 200
    items = body["schedules"]
    assert [i["schedule_id"] for i in items] == [
        str(private.schedule_id),
        str(mine.schedule_id),
        str(missing),
        str(shared.schedule_id),
    ]
    assert [i["status"] for i in items] == ["unavailable", "ok", "unavailable", "ok"]
    assert items[0] == {
        "schedule_id": str(private.schedule_id),
        "status": "unavailable",
    }
    assert items[2] == {"schedule_id": str(missing), "status": "unavailable"}
    assert (items[1]["schedule_name"], items[1]["is_owner"]) == ("Mine", True)
    assert items[3]["is_shared"] is True
    assert items[3]["shared_by_user_name"] == "Colleague"


def test_duplicate_ids_are_dropped_keeping_first_order(db_session):
    me = make_user(db_session, "Me")
    a = make_schedule(db_session, me, name="A")
    b = make_schedule(db_session, me, name="B")

    status, body = _compare(
        _app(db_session, me), b.schedule_id, a.schedule_id, b.schedule_id
    )

    assert status == 200
    assert [i["schedule_name"] for i in body["schedules"]] == ["B", "A"]


def test_more_than_four_distinct_schedules_is_rejected_one_is_allowed(db_session):
    me = make_user(db_session, "Me")
    ids = [make_schedule(db_session, me, name=f"S{n}").schedule_id for n in range(5)]
    app = _app(db_session, me)

    assert _compare(app, *ids)[0] == 422
    assert _compare(app, *ids[:4], ids[0])[0] == 200
    # The page names the schedule left after the others were removed.
    status, body = _compare(app, ids[0], ids[0])
    assert status == 200
    assert [i["schedule_name"] for i in body["schedules"]] == ["S0"]


def test_compare_and_schedule_page_report_the_same_summary(db_session):
    me = make_user(db_session, "Me")
    dataset = make_dataset(db_session, me)
    dataset.course_merges = {"Combined 1": ["101", "102"]}
    dataset.file_paths = [
        {"type": "enrollments", "metadata": {"unique_students": 40}},
        {
            "type": "room_blockouts",
            "metadata": {"unique_rooms_blocked": 2, "total_blockout_entries": 5},
        },
    ]
    sched = make_schedule(db_session, me, dataset=dataset, parameters={"max_days": 5})
    add_exam(db_session, sched, "101", 30, slot=("Tuesday", 9), room=("Hall", 40))
    add_exam(db_session, sched, "102", 50, slot=("Monday", 14), room=("Lab", 40))
    add_exam(db_session, sched, "103", 20, slot=("Monday", 9))
    add_exam(db_session, sched, "104", 10)
    pair = {"entity_id": "s1", "day": "Monday", "block": 0}
    save_analysis(
        db_session,
        sched,
        {
            "hard_conflicts": {
                "student_double_book": [
                    {**pair, "crn": "101", "conflicting_crn": "102"},
                    {**pair, "crn": "101", "conflicting_crn": "103"},
                    {**pair, "crn": "102", "conflicting_crn": "103"},
                ]
            },
            "soft_conflicts": {},
            "statistics": {"total_hard_conflicts": 3},
        },
    )
    other = make_schedule(db_session, me, dataset=dataset)
    app = _app(db_session, me)

    status, body = _compare(app, sched.schedule_id, other.schedule_id)
    page_status, page = _get(app, f"/api/schedule/{sched.schedule_id}", [])

    assert (status, page_status) == (200, 200)
    summary = body["schedules"][0]["summary"]
    assert summary == page["summary"]
    assert summary["exams"] == {
        "total": 4,
        "placed": 2,
        "unscheduled": 1,
        "unroomed": 1,
        "over_capacity": 1,
    }
    assert summary["conflicts"]["student_double_book"] == {
        "people": 1,
        "instances": 1,
    }
    assert summary["groups"]["combined"] == {
        "groups": 1,
        "sections": 2,
        "students": 80,
    }
    assert summary["unique_students"] == 40
    assert summary["blockouts"] == {"rooms": 2, "slots": 5}
    assert summary["settings"]["max_days"] == 5
