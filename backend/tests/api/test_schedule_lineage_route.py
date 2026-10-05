"""Late-add lineage in GET /api/schedule/{id} and GET /api/schedule (Postgres test DB).

Late-add versions are built directly from the `runs.parameters` the save step
stores: the base's resolved settings plus `based_on_schedule_id`,
`original_schedule_id` and the cumulative `late_additions`.
"""

import datetime
import uuid

from src.repo.schedule import ScheduleRepo
from tests.api.test_compare_schedules_route import _app, _get
from tests.db.builders import make_dataset, make_schedule, make_user, share_schedule


BASE_SETTINGS = {
    "algorithm": "annealing",
    "blocks_per_day": 4,
    "max_days": 5,
    "student_max_per_day": 2,
    "instructor_max_per_day": 2,
    "avoid_back_to_back": True,
    "prioritize_large_courses": False,
    "time_budget_seconds": 15,
}


def _entry(crn: str, version_id: uuid.UUID) -> dict:
    return {
        "crn": crn,
        "course_code": f"TEST {crn}",
        "instructor_id": "i1",
        "size": 12,
        "day": 1,
        "day_name": "Tuesday",
        "block": 2,
        "block_time": "1PM-3PM",
        "room": "Hall",
        "outcome": "clear",
        "conflicts": {},
        "added_by": "u",
        "added_by_name": "Me",
        "added_at": "2026-01-01T09:00:00",
        "schedule_id": str(version_id),
    }


def _late_add(db, owner, base, name, crn, *, created_at=None):
    """A late-add version of ``base`` as the save step stores it."""
    base_params = base.run.parameters
    version = make_schedule(
        db,
        owner,
        name,
        dataset=base.run.dataset,
        algorithm_name="Late add",
        parameters={
            **{k: v for k, v in base_params.items() if k in BASE_SETTINGS},
            "based_on_schedule_id": str(base.schedule_id),
            "original_schedule_id": base_params.get(
                "original_schedule_id", str(base.schedule_id)
            ),
        },
    )
    version.run.parameters["late_additions"] = [
        *base_params.get("late_additions", []),
        _entry(crn, version.schedule_id),
    ]
    if created_at is not None:
        version.created_at = created_at
    db.flush()
    return version


def _lineage(db, user, schedule_id) -> dict:
    status, body = _get(_app(db, user), f"/api/schedule/{schedule_id}", [])
    assert status == 200
    return body


def _chain(db, me):
    t0 = datetime.datetime(2026, 1, 1, 9)
    v1 = make_schedule(
        db, me, "V1", dataset=make_dataset(db, me), parameters=dict(BASE_SETTINGS)
    )
    v2 = _late_add(db, me, v1, "V2", "901", created_at=t0)
    v3 = _late_add(db, me, v2, "V3", "902", created_at=t0 + datetime.timedelta(hours=1))
    return v1, v2, v3


def test_generated_schedule_has_empty_lineage(db_session):
    me = make_user(db_session, "Me")
    sched = make_schedule(db_session, me, "Generated")

    assert _lineage(db_session, me, sched.schedule_id)["lineage"] == {
        "based_on": None,
        "original": None,
        "late_additions": [],
        "newer_versions": [],
    }


def test_v3_points_at_v2_and_v1_with_cumulative_additions(db_session):
    me = make_user(db_session, "Me")
    v1, v2, v3 = _chain(db_session, me)

    lineage = _lineage(db_session, me, v3.schedule_id)["lineage"]
    assert lineage["based_on"] == {
        "id": str(v2.schedule_id),
        "name": "V2",
        "available": True,
    }
    assert lineage["original"] == {
        "id": str(v1.schedule_id),
        "name": "V1",
        "available": True,
    }
    assert [(e["crn"], e["schedule_id"]) for e in lineage["late_additions"]] == [
        ("901", str(v2.schedule_id)),
        ("902", str(v3.schedule_id)),
    ]
    v2_lineage = _lineage(db_session, me, v2.schedule_id)["lineage"]
    assert (
        v2_lineage["based_on"]["id"]
        == v2_lineage["original"]["id"]
        == str(v1.schedule_id)
    )
    assert [e["crn"] for e in v2_lineage["late_additions"]] == ["901"]


def test_newer_versions_are_direct_children_the_caller_can_view_newest_first(
    db_session,
):
    me = make_user(db_session, "Me")
    colleague = make_user(db_session, "Colleague")
    v1, v2, _v3 = _chain(db_session, me)
    branch = _late_add(
        db_session,
        me,
        v1,
        "Branch",
        "903",
        created_at=datetime.datetime(2026, 1, 2, 9),
    )

    newer = _lineage(db_session, me, v1.schedule_id)["lineage"]["newer_versions"]
    # V3 is based on V2, not on V1.
    assert [(n["id"], n["name"]) for n in newer] == [
        (str(branch.schedule_id), "Branch"),
        (str(v2.schedule_id), "V2"),
    ]
    assert newer[0]["created_at"] == "2026-01-02T09:00:00"

    # A colleague who can see V1 and V2 but not the branch sees only V2.
    share_schedule(db_session, v1, me, colleague)
    share_schedule(db_session, v2, me, colleague)
    newer = _lineage(db_session, colleague, v1.schedule_id)["lineage"]["newer_versions"]
    assert [n["name"] for n in newer] == ["V2"]


def test_deleted_base_is_unavailable_with_no_name(db_session):
    me = make_user(db_session, "Me")
    v1, v2, v3 = _chain(db_session, me)
    assert ScheduleRepo(db_session).delete_schedule_cascade(v2.schedule_id, me.user_id)

    lineage = _lineage(db_session, me, v3.schedule_id)["lineage"]
    assert lineage["based_on"] == {
        "id": str(v2.schedule_id),
        "name": None,
        "available": False,
    }
    assert lineage["original"]["available"] is True
    assert [e["crn"] for e in lineage["late_additions"]] == ["901", "902"]


def test_base_not_viewable_by_caller_reveals_no_name(db_session):
    me = make_user(db_session, "Me")
    colleague = make_user(db_session, "Colleague")
    v1, v2, v3 = _chain(db_session, me)
    share_schedule(db_session, v3, me, colleague)

    body = _lineage(db_session, colleague, v3.schedule_id)
    assert body["lineage"]["based_on"] == {
        "id": str(v2.schedule_id),
        "name": None,
        "available": False,
    }
    assert body["lineage"]["original"] == {
        "id": str(v1.schedule_id),
        "name": None,
        "available": False,
    }

    status, items = _get(_app(db_session, colleague), "/api/schedule", [])
    assert status == 200
    [item] = items
    assert (item["late_add_count"], item["based_on_name"]) == (2, None)


def test_list_items_carry_late_add_count_and_base_name(db_session):
    me = make_user(db_session, "Me")
    _chain(db_session, me)

    status, items = _get(_app(db_session, me), "/api/schedule", [])

    assert status == 200
    by_name = {i["schedule_name"]: i for i in items}
    assert (by_name["V1"]["late_add_count"], by_name["V1"]["based_on_name"]) == (
        0,
        None,
    )
    assert (by_name["V2"]["late_add_count"], by_name["V2"]["based_on_name"]) == (
        1,
        "V1",
    )
    assert (by_name["V3"]["late_add_count"], by_name["V3"]["based_on_name"]) == (
        2,
        "V2",
    )


def test_late_add_version_shows_its_base_engine_and_unused_settings(db_session):
    me = make_user(db_session, "Me")
    v1, v2, _v3 = _chain(db_session, me)
    v1.run.algorithm_name = "Annealing"
    db_session.flush()

    base = _lineage(db_session, me, v1.schedule_id)["summary"]
    version = _lineage(db_session, me, v2.schedule_id)["summary"]

    assert version["settings"]["algorithm"] == "annealing"
    assert version["settings"] == base["settings"]
    assert (
        version["settings_unused"]
        == base["settings_unused"]
        == ["prioritize_large_courses"]
    )
    assert version["settings_assumed"] == []
