"""Algorithm selection query params on POST /api/schedule/generate/{dataset_id}."""

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi import FastAPI

from src.api.deps import get_current_user, get_schedule_service
from src.api.routes import schedule


def _post(app: FastAPI, path: str, query: str) -> tuple[int, dict]:
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
        "method": "POST",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": query.encode(),
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


def _app(service: AsyncMock) -> FastAPI:
    app = FastAPI()
    app.include_router(schedule.router, prefix="/api")
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        user_id=uuid4()
    )
    app.dependency_overrides[get_schedule_service] = lambda: service
    return app


def test_unknown_algorithm_is_rejected():
    service = AsyncMock()
    status, _ = _post(
        _app(service),
        f"/api/schedule/generate/{uuid4()}",
        "schedule_name=s&algorithm=bogus",
    )

    assert status == 422
    service.generate_schedule.assert_not_called()


def test_time_budget_above_limit_is_rejected():
    service = AsyncMock()
    status, _ = _post(
        _app(service),
        f"/api/schedule/generate/{uuid4()}",
        "schedule_name=s&algorithm=annealing&time_budget_seconds=121",
    )

    assert status == 422


def test_annealing_with_zero_budget_reaches_service():
    service = AsyncMock()
    service.generate_schedule.return_value = {"ok": True}
    status, body = _post(
        _app(service),
        f"/api/schedule/generate/{uuid4()}",
        "schedule_name=s&algorithm=annealing&time_budget_seconds=0",
    )

    assert status == 200
    assert body == {"ok": True}
    args = service.generate_schedule.await_args.args
    assert args[-2:] == ("annealing", 0)


def test_defaults_to_dsatur_with_fifteen_second_budget():
    service = AsyncMock()
    service.generate_schedule.return_value = {}
    _post(_app(service), f"/api/schedule/generate/{uuid4()}", "schedule_name=s")

    assert service.generate_schedule.await_args.args[-2:] == ("dsatur", 15)
