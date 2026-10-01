from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from src.api.deps import get_current_user, get_dataset_service
from src.core.exceptions import (
    DatasetExistsError,
    DatasetNotFoundError,
    StorageError,
    ValidationError,
)
from src.schemas.db import Users
from src.services.dataset import DatasetService


router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post("/upload")
async def upload_dataset(
    dataset_name: str = Form(...),
    courses: UploadFile = File(...),
    enrollments: UploadFile = File(...),
    rooms: UploadFile = File(...),
    room_blockouts: UploadFile | None = File(None),
    combined_exams: UploadFile | None = File(None),
    common_exams: UploadFile | None = File(None),
    current_user: Users = Depends(get_current_user),
    dataset_service: DatasetService = Depends(get_dataset_service),
):
    """Upload dataset to S3, validate, and save metadata to database."""
    try:
        results = await dataset_service.upload_dataset(
            dataset_name=dataset_name,
            courses_file=courses,
            enrollments_file=enrollments,
            rooms_file=rooms,
            user_id=current_user.user_id,
            room_blockouts_file=room_blockouts
            if room_blockouts and room_blockouts.filename
            else None,
            combined_exams_file=combined_exams
            if combined_exams and combined_exams.filename
            else None,
            common_exams_file=common_exams
            if common_exams and common_exams.filename
            else None,
        )
        return results

    except DatasetExistsError as e:
        raise HTTPException(
            status_code=400,
            detail={"message": e.message},
        ) from e

    except ValidationError as e:
        raise HTTPException(
            status_code=400,
            detail={"message": e.message, "errors": e.detail.get("errors", {})},
        ) from e
    except StorageError as e:
        raise HTTPException(status_code=500, detail=e.message) from e


@router.get("")
async def list_datasets(
    current_user: Users = Depends(get_current_user),
    dataset_service: DatasetService = Depends(get_dataset_service),
):
    """List all datasets for current user."""
    return dataset_service.list_datasets_for_user(current_user.user_id)


@router.delete("/{dataset_id}")
async def delete_dataset(
    dataset_id: UUID,
    current_user: Users = Depends(get_current_user),
    dataset_service: DatasetService = Depends(get_dataset_service),
):
    """Delete dataset from both S3 and database."""
    try:
        return await dataset_service.delete_dataset(dataset_id, current_user.user_id)
    except DatasetNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e


@router.get("/{dataset_id}/merges")
async def get_merges(
    dataset_id: UUID,
    current_user: Users = Depends(get_current_user),
    dataset_service: DatasetService = Depends(get_dataset_service),
):
    """Get all course merges for a dataset."""
    try:
        merges = dataset_service.get_merges(dataset_id, current_user.user_id)
        return merges or {}  # Return merges directly, not wrapped
    except DatasetNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e


@router.get("/{dataset_id}/common-exams")
async def get_common_exams(
    dataset_id: UUID,
    current_user: Users = Depends(get_current_user),
    dataset_service: DatasetService = Depends(get_dataset_service),
):
    """Get all common exam groups for a dataset."""
    try:
        groups = dataset_service.get_common_exams(dataset_id, current_user.user_id)
        return groups or {}
    except DatasetNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e
