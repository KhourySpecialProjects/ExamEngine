"""/api/validation routes: access, the NDJSON stream, logging and snapshot loading."""

import asyncio
import json
import logging
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI

from src.api.deps import get_current_user, get_schedule_validation_service
from src.api.routes import validation
from src.domain.validation import (
    CHECKS,
    RunParameters,
    ScheduleRow,
    ValidationSnapshot,
)
from src.schemas.db import DayEnum
from src.services.schedule_validation import ScheduleValidationService


USER_ID = uuid4()


async def _request(
    app: FastAPI, method: str, path: str
) -> tuple[int, dict[str, str], bytes]:
    """Drive the ASGI app directly (httpx is not a test dependency)."""
    messages: list[dict] = []
    finished = asyncio.Event()
    requested = False

    async def receive() -> dict:
        nonlocal requested
        if not requested:
            requested = True
            return {"type": "http.request", "body": b"", "more_body": False}
        await finished.wait()
        return {"type": "http.disconnect"}

    async def send(message: dict) -> None:
        messages.append(message)
        if message["type"] == "http.response.body" and not message.get("more_body"):
            finished.set()

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": [],
        "client": ("test", 1),
        "server": ("test", 80),
    }
    await app(scope, receive, send)
    start = next(m for m in messages if m["type"] == "http.response.start")
    headers = {k.decode(): v.decode() for k, v in start["headers"]}
    body = b"".join(
        m.get("body", b"") for m in messages if m["type"] == "http.response.body"
    )
    return start["status"], headers, body


def _app(service: object | None = None, logged_in: bool = True) -> FastAPI:
    app = FastAPI()
    app.include_router(validation.router, prefix="/api")
    if logged_in:
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
            user_id=USER_ID
        )
    if service is not None:
        app.dependency_overrides[get_schedule_validation_service] = lambda: service
    return app


def _snapshot() -> ValidationSnapshot:
    """CRN 100 has two rows (a fail); the dataset files are gone (skips)."""
    rows = tuple(
        ScheduleRow(
            crn=crn,
            day_index=day,
            block_index=0,
            room="R1",
            room_capacity=50,
            enrollment_count=10,
            instructor=None,
        )
        for crn, day in (("100", 0), ("100", 1), ("200", 2))
    )
    return ValidationSnapshot(
        rows=rows,
        parameters=RunParameters(),
        analysis=None,
        combined_groups={},
        common_groups={},
        files=None,
    )


def _fake_builder(snapshot: ValidationSnapshot | None) -> MagicMock:
    service = MagicMock()
    service.build_snapshot = AsyncMock(return_value=snapshot)
    return service


# ----------------------------------------------------------------------
# Routes
# ----------------------------------------------------------------------


async def test_catalog_lists_checks_in_run_order():
    status, _, body = await _request(_app(), "GET", "/api/validation/checks")

    assert status == 200
    checks = json.loads(body)["checks"]
    assert [c["id"] for c in checks] == [c.id for c in CHECKS]
    assert {c["category"] for c in checks} == {
        "coverage",
        "rooms",
        "groups",
        "conflicts",
        "data",
    }


async def test_unauthenticated_request_is_rejected():
    status, _, _ = await _request(
        _app(_fake_builder(_snapshot()), logged_in=False),
        "POST",
        f"/api/validation/schedules/{uuid4()}",
    )

    assert status == 401


async def test_user_who_cannot_view_the_schedule_gets_404_and_no_data_is_loaded():
    schedule_repo, assignments, analyses, datasets = (MagicMock() for _ in range(4))
    schedule_repo.get_with_run_details.return_value = None
    service = ScheduleValidationService(schedule_repo, assignments, analyses, datasets)
    schedule_id = uuid4()

    with patch("src.services.schedule_validation.storage") as storage:
        status, _, body = await _request(
            _app(service), "POST", f"/api/validation/schedules/{schedule_id}"
        )

    assert status == 404
    assert json.loads(body) == {"detail": f"Schedule {schedule_id} not found"}
    schedule_repo.get_with_run_details.assert_called_once_with(schedule_id, USER_ID)
    datasets.get_by_id.assert_not_called()
    assignments.get_all_for_schedule.assert_not_called()
    storage.download_file.assert_not_called()


async def test_stream_emits_start_and_result_per_check_in_order_then_done():
    status, headers, body = await _request(
        _app(_fake_builder(_snapshot())), "POST", f"/api/validation/schedules/{uuid4()}"
    )

    assert status == 200
    assert headers["content-type"] == "application/x-ndjson"
    assert headers["x-accel-buffering"] == "no"
    assert headers["cache-control"] == "no-cache"
    assert body.endswith(b"\n")
    events = [json.loads(line) for line in body.decode().splitlines()]

    expected_order = [
        (kind, check.id) for check in CHECKS for kind in ("start", "result")
    ]
    assert [(e["type"], e["check_id"]) for e in events[:-1]] == expected_order

    results = [e for e in events if e["type"] == "result"]
    for result in results:
        assert set(result) == {
            "type",
            "check_id",
            "status",
            "summary",
            "count",
            "examples",
        }
        assert len(result["examples"]) <= 20
    by_id = {r["check_id"]: r for r in results}
    assert by_id["coverage.crn_single_row"]["status"] == "fail"
    assert by_id["coverage.crn_single_row"]["examples"] == ["CRN 100 appears 2 times"]
    assert by_id["coverage.crn_in_courses_file"]["summary"] == (
        "The dataset's uploaded files are no longer available."
    )

    done = events[-1]
    assert done["type"] == "done"
    tally = dict.fromkeys(("pass", "warn", "fail", "skipped"), 0)
    for result in results:
        tally[result["status"]] += 1
    assert done["counts"] == tally
    assert isinstance(done["duration_ms"], int)


async def test_failed_check_is_logged_and_run_is_summarised(caplog):
    schedule_id = uuid4()

    with caplog.at_level(logging.INFO, logger="examengine.validation"):
        await _request(
            _app(_fake_builder(_snapshot())),
            "POST",
            f"/api/validation/schedules/{schedule_id}",
        )

    records = [r for r in caplog.records if r.name == "examengine.validation"]
    warnings = [r for r in records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    message = warnings[0].getMessage()
    assert "coverage.crn_single_row" in message
    assert str(schedule_id) in message
    assert str(USER_ID) in message
    assert "CRN 100 appears 2 times" in message
    summaries = [r for r in records if r.levelno == logging.INFO]
    assert len(summaries) == 1
    assert "1 fail" in summaries[0].getMessage()


# ----------------------------------------------------------------------
# Snapshot loading
# ----------------------------------------------------------------------


FILES = {
    "k/courses.csv": b"CRN,CourseID,num_students,Instructor Name\n"
    b"100,CS1,2,Ada\n200,CS2,1,Bob\n",
    "k/enrollments.csv": b"Student_PIDM,CRN\n001234567,100\n",
    "k/rooms.csv": b"room_name,capacity\nR1,10\n",
}


def _assignment(crn, day=None, label=None, room=None, capacity=None):
    return SimpleNamespace(
        course=SimpleNamespace(
            crn=crn,
            course_subject_code="CS1",
            enrollment_count=2,
            instructor_name="Ada",
        ),
        time_slot=(
            SimpleNamespace(day=day, slot_label=label) if day is not None else None
        ),
        room=SimpleNamespace(location=room, capacity=capacity) if room else None,
    )


def _service(dataset) -> ScheduleValidationService:
    schedule_repo, assignments, analyses, datasets = (MagicMock() for _ in range(4))
    schedule_repo.get_with_run_details.return_value = SimpleNamespace(
        run=SimpleNamespace(
            dataset_id=dataset.dataset_id,
            parameters={"max_days": 5, "late_additions": [{"crn": "200"}]},
        )
    )
    assignments.get_all_for_schedule.return_value = [
        _assignment("100", DayEnum.Wednesday, "2PM-4PM", "R1", 10),
        _assignment("200"),
    ]
    analyses.get_by_schedule_id.return_value = SimpleNamespace(
        conflicts={"unscheduled_groups": [{"kind": "combined", "group": "G"}]}
    )
    datasets.get_by_id.return_value = dataset
    return ScheduleValidationService(schedule_repo, assignments, analyses, datasets)


def _dataset(deleted_at=None):
    return SimpleNamespace(
        dataset_id=uuid4(),
        deleted_at=deleted_at,
        file_paths=[
            {"type": "courses", "storage_key": "k/courses.csv", "metadata": {}},
            {"type": "enrollments", "storage_key": "k/enrollments.csv", "metadata": {}},
            {"type": "rooms", "storage_key": "k/rooms.csv", "metadata": {}},
            # Legacy combined exam file, stored under the "common_exams" type.
            {
                "type": "common_exams",
                "storage_key": "k/combined.csv",
                "metadata": {"exam_groups": 1},
            },
        ],
        course_merges={"G": ["100", "200"]},
        common_exam_groups=None,
    )


async def test_snapshot_reads_stored_schedule_and_uploaded_files():
    with patch("src.services.schedule_validation.storage") as storage:
        storage.download_file.side_effect = FILES.get
        snapshot = await _service(_dataset()).build_snapshot(uuid4(), USER_ID)

    assert snapshot.rows == (
        ScheduleRow("100", 2, 2, "R1", 10, 2, "Ada", "CS1"),
        ScheduleRow("200", None, None, None, None, 2, "Ada", "CS1"),
    )
    assert snapshot.parameters == RunParameters(
        max_days=5, blocks_per_day=5, student_max_per_day=3, instructor_max_per_day=3
    )
    assert snapshot.late_additions == ({"crn": "200"},)
    assert snapshot.combined_groups == {"G": ("100", "200")}
    assert snapshot.unscheduled_groups == [{"kind": "combined", "group": "G"}]
    assert [c.crn for c in snapshot.files.courses] == ["100", "200"]
    assert snapshot.files.enrollments[0].student_id == "001234567"
    assert not snapshot.files.blockouts_uploaded
    downloaded = {call.args[0] for call in storage.download_file.call_args_list}
    assert downloaded == set(FILES)  # the combined exam file isn't needed


@pytest.mark.parametrize(
    ("deleted_at", "files"),
    [(datetime(2026, 1, 1), FILES), (None, {**FILES, "k/rooms.csv": None})],
)
async def test_snapshot_has_no_files_when_dataset_deleted_or_download_fails(
    deleted_at, files
):
    with patch("src.services.schedule_validation.storage") as storage:
        storage.download_file.side_effect = files.get
        snapshot = await _service(_dataset(deleted_at)).build_snapshot(uuid4(), USER_ID)

    assert snapshot.files is None
    assert len(snapshot.rows) == 2
