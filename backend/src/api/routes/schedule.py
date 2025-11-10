from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from src.api.deps import get_current_user, get_schedule_service
from src.schemas.db import Users
from src.services.schedule import ScheduleService


router = APIRouter(prefix="/schedule", tags=["Scheduling"])


@router.post("/generate/{dataset_id}")
async def generate_schedule_from_dataset(
    dataset_id: UUID,
    schedule_name: str,
    student_max_per_day: int = 3,
    instructor_max_per_day: int = 3,
    avoid_back_to_back: bool = True,
    max_days: int = 7,
    current_user: Users = Depends(get_current_user),
    schedule_service: ScheduleService = Depends(get_schedule_service),
):
    """
    Generate complete schedule from a stored dataset

    Returns:
        Complete schedule with all exams, conflicts, and metadata
    """
    try:
        result = await schedule_service.generate_schedule(
            dataset_id,
            current_user.user_id,
            schedule_name,
            student_max_per_day,
            instructor_max_per_day,
            avoid_back_to_back,
            max_days,
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Schedule generation failed: {e}"
        ) from e
