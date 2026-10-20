"""POST /api/schedule/{id}/share and DELETE /api/schedule/shares/{id} on late-add
chains, against the Postgres test database (EXENG-214).

A chain is a generated schedule plus the late-add versions made from it; sharing
or unsharing any schedule of a chain applies to all of them.
"""

import asyncio
import json

import pytest
from fastapi import FastAPI
from sqlalchemy import select

from src.api.deps import get_current_user, get_db
from src.api.routes import schedule
from src.schemas.db import ScheduleShares
from tests.db.builders import make_dataset, make_schedule, make_user, share_schedule


def _call(app: FastAPI, method: str, path: str, body: dict | None = None):
    """Drive the ASGI app directly (httpx is not a test dependency)."""
    messages: list[dict] = []
    payload = json.dumps(body).encode() if body is not None else b""

    async def receive() -> dict:
        return {"type": "http.request", "body": payload, "more_body": False}

    async def send(message: dict) -> None:
        messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
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


def _app(db, user) -> FastAPI:
    app = FastAPI()
    app.include_router(schedule.router, prefix="/api")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    return app


def _share(db, by, schedule_id, user):
    return _call(
        _app(db, by),
        "POST",
        f"/api/schedule/{schedule_id}/share",
        {"user_id": str(user.user_id), "permission": "view"},
    )


def _version(db, owner, base, name):
    """A late-add version of ``base`` as the save step stores its run."""
    params = base.run.parameters
    return make_schedule(
        db,
        owner,
        name,
        dataset=base.run.dataset,
        algorithm_name="Late add",
        parameters={
            "based_on_schedule_id": str(base.schedule_id),
            "original_schedule_id": params.get(
                "original_schedule_id", str(base.schedule_id)
            ),
        },
    )


def _has(db, user) -> set[str]:
    """Names of the schedules shared with the user."""
    return {
        share.schedule.schedule_name
        for share in db.execute(
            select(ScheduleShares).where(
                ScheduleShares.shared_with_user_id == user.user_id
            )
        ).scalars()
    }


@pytest.fixture
def chain(db_session):
    """Bob's V1, shared with Jane and Sam; Jane's V2 from V1; Sam's V3 from V2.

    Every version is shared with the rest of the group, as late adds leave it.
    Bob also has an unrelated schedule.
    """
    bob, jane, sam = (make_user(db_session, n) for n in ("Bob", "Jane", "Sam"))
    v1 = make_schedule(
        db_session, bob, "V1", dataset=make_dataset(db_session, bob), parameters={}
    )
    v2 = _version(db_session, jane, v1, "V2")
    v3 = _version(db_session, sam, v2, "V3")
    for sched, owner, others in ((v1, bob, (jane, sam)), (v2, jane, (bob, sam))):
        for other in others:
            share_schedule(db_session, sched, owner, other)
    for other in (bob, jane):
        share_schedule(db_session, v3, sam, other)
    make_schedule(db_session, bob, "Unrelated")
    db_session.commit()
    return {"bob": bob, "jane": jane, "sam": sam, "v1": v1, "v2": v2, "v3": v3}


@pytest.mark.parametrize(("sharer", "shared"), [("bob", "v1"), ("sam", "v3")])
def test_sharing_any_version_shares_the_whole_chain(db_session, chain, sharer, shared):
    tom = make_user(db_session, "Tom")

    status, body = _share(db_session, chain[sharer], chain[shared].schedule_id, tom)

    assert status == 200, body
    assert body["schedule_id"] == str(chain[shared].schedule_id)
    assert _has(db_session, tom) == {"V1", "V2", "V3"}


def test_resharing_fills_gaps_and_skips_the_users_own_version(db_session, chain):
    tom = make_user(db_session, "Tom")
    share_schedule(db_session, chain["v2"], chain["jane"], tom)
    db_session.commit()

    assert _share(db_session, chain["bob"], chain["v1"].schedule_id, tom)[0] == 200
    assert _share(db_session, chain["bob"], chain["v1"].schedule_id, tom)[0] == 200

    shares = db_session.execute(
        select(ScheduleShares).where(ScheduleShares.shared_with_user_id == tom.user_id)
    ).scalars()
    assert sorted(s.schedule.schedule_name for s in shares) == ["V1", "V2", "V3"]

    # Jane owns V2: she gets no share of it, and keeps V1 and V3.
    jane = chain["jane"]
    _share(db_session, chain["sam"], chain["v3"].schedule_id, jane)
    assert _has(db_session, jane) == {"V1", "V3"}


def test_unsharing_from_any_version_removes_the_user_from_the_chain(db_session, chain):
    sam, jane = chain["sam"], chain["jane"]
    v1 = chain["v1"]
    share_id = db_session.execute(
        select(ScheduleShares.share_id).where(
            ScheduleShares.schedule_id == v1.schedule_id,
            ScheduleShares.shared_with_user_id == jane.user_id,
        )
    ).scalar_one()

    status, _ = _call(
        _app(db_session, chain["bob"]), "DELETE", f"/api/schedule/shares/{share_id}"
    )

    assert status == 200
    # Jane keeps V2, which she owns; Sam's shares are untouched.
    assert _has(db_session, jane) == set()
    assert _has(db_session, sam) == {"V1", "V2"}


def test_only_the_schedules_owner_may_share_it(db_session, chain):
    tom = make_user(db_session, "Tom")

    status, body = _share(db_session, chain["jane"], chain["v1"].schedule_id, tom)

    assert status == 403, body
    assert _has(db_session, tom) == set()
