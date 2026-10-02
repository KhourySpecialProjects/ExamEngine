"""Admin-only access and the zip response of /api/admin/datasets routes."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI

from src.api.deps import get_current_user, get_dataset_service
from src.api.routes import admin


async def _get(app: FastAPI, path: str) -> tuple[int, dict[str, str], bytes]:
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


def _app(role: str, service: MagicMock) -> FastAPI:
    app = FastAPI()
    app.include_router(admin.router, prefix="/api")
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role=role)
    app.dependency_overrides[get_dataset_service] = lambda: service
    return app


def _service() -> MagicMock:
    service = MagicMock()
    service.build_dataset_zip = AsyncMock(return_value=("Fall_2026.zip", b"PK"))
    return service


@pytest.mark.parametrize(
    "path", ["/api/admin/datasets", f"/api/admin/datasets/{uuid4()}/download"]
)
async def test_non_admin_is_forbidden(path):
    service = _service()

    status, _, _ = await _get(_app("user", service), path)

    assert status == 403
    service.list_all_datasets.assert_not_called()
    service.build_dataset_zip.assert_not_called()


async def test_admin_download_is_a_zip_attachment():
    status, headers, body = await _get(
        _app("admin", _service()), f"/api/admin/datasets/{uuid4()}/download"
    )

    assert status == 200
    assert headers["content-type"] == "application/zip"
    assert headers["content-disposition"] == 'attachment; filename="Fall_2026.zip"'
    assert body == b"PK"
