"""Where a late-add version came from, read from `runs.parameters` (DB only).

A late add saves a new schedule whose run parameters record
`based_on_schedule_id`, `original_schedule_id` and the cumulative
`late_additions`. Generated schedules have none of these.
"""

from typing import Any
from uuid import UUID

from src.repo.schedule import ScheduleRepo


def _uuid(value: Any) -> UUID | None:
    try:
        return UUID(str(value)) if value else None
    except ValueError:
        return None


def late_additions(parameters: dict[str, Any] | None) -> list[dict[str, Any]]:
    return list((parameters or {}).get("late_additions") or [])


def based_on_id(parameters: dict[str, Any] | None) -> UUID | None:
    return _uuid((parameters or {}).get("based_on_schedule_id"))


def _ref(schedule_id: UUID | None, names: dict[UUID, str]) -> dict[str, Any] | None:
    """`{id, name, available}`; a deleted or unviewable schedule has no name."""
    if schedule_id is None:
        return None
    name = names.get(schedule_id)
    return {"id": str(schedule_id), "name": name, "available": name is not None}


def build_lineage(
    repo: ScheduleRepo,
    schedule_id: UUID,
    parameters: dict[str, Any] | None,
    user_id: UUID,
) -> dict[str, Any]:
    """The `lineage` field of `GET /api/schedule/{id}`."""
    params = parameters or {}
    based_on = based_on_id(params)
    original = _uuid(params.get("original_schedule_id"))
    names = repo.get_viewable_names(
        [i for i in (based_on, original) if i is not None], user_id
    )
    return {
        "based_on": _ref(based_on, names),
        "original": _ref(original, names),
        "late_additions": late_additions(params),
        "newer_versions": [
            {
                "id": str(s.schedule_id),
                "name": s.schedule_name,
                "created_at": s.created_at.isoformat(),
            }
            for s in repo.get_newer_versions(schedule_id, user_id)
        ],
    }
