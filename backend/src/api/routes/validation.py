import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from src.api.deps import get_current_user, get_schedule_validation_service
from src.domain.validation import CHECKS
from src.schemas.db import Users
from src.services.schedule_validation import (
    ScheduleValidationService,
    validation_stream,
)


logger = logging.getLogger("examengine.validation")

router = APIRouter(prefix="/validation", tags=["validation"])


@router.get("/checks")
def list_checks(
    current_user: Users = Depends(get_current_user),
) -> dict[str, list[dict[str, str]]]:
    """Every validation check, in run order."""
    return {"checks": [check.to_dict() for check in CHECKS]}


@router.post("/schedules/{schedule_id}")
async def validate_schedule(
    schedule_id: UUID,
    current_user: Users = Depends(get_current_user),
    service: ScheduleValidationService = Depends(get_schedule_validation_service),
) -> StreamingResponse:
    """
    Re-check a schedule against its dataset's uploaded files.

    Anyone who can view the schedule may run it. Streams NDJSON: a `start` and
    a `result` event per check in catalog order, then `done` (or `error`).
    """
    try:
        snapshot = await service.build_snapshot(schedule_id, current_user.user_id)
    except Exception as e:
        logger.exception("Loading schedule %s for validation failed", schedule_id)
        raise HTTPException(
            status_code=500, detail="Failed to load the schedule for validation"
        ) from e
    if snapshot is None:
        raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")

    return StreamingResponse(
        validation_stream(snapshot, schedule_id, current_user.user_id),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
