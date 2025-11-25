from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from src.api.deps import get_current_user, get_dataset_service
from src.core.exceptions import DatasetNotFoundError, StorageError, ValidationError, DatasetExistsError
from src.schemas.db import Users
from src.services.dataset import DatasetService


router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post("/upload")
async def upload_dataset(
    dataset_name: str = Form(...),
    courses: UploadFile = File(...),
    enrollments: UploadFile = File(...),
    rooms: UploadFile = File(...),
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
