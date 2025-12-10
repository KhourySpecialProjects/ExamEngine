from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from src.api.deps import get_current_user, get_dataset_service
from src.core.exceptions import (
    DatasetExistsError,
    DatasetNotFoundError,
    StorageError,
    ValidationError,
)
from src.schemas.db import Users
from src.services.dataset import DatasetService


class MergeValidationRequest(BaseModel):
    """Request model for merge validation."""

    crns_to_merge: list[str] | None = None
    crns: list[str] | None = None  # Support both field names for compatibility

    def get_crns(self) -> list[str]:
        """Get CRNs from either field name."""
        result = self.crns_to_merge or self.crns or []
        if not result:
            raise ValueError("Either 'crns_to_merge' or 'crns' must be provided with at least one CRN")
        return result


class SetMergesRequest(BaseModel):
    """Request model for setting course merges."""

    merges: dict[str, list[str]]
    # Format: {"merge_group_1": ["CRN1", "CRN2"], "merge_group_2": ["CRN3", "CRN4"]}


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


@router.post("/{dataset_id}/merges/validate")
async def validate_merge(
    dataset_id: UUID,
    request: MergeValidationRequest,
    current_user: Users = Depends(get_current_user),
    dataset_service: DatasetService = Depends(get_dataset_service),
):
    """Validate if merging multiple CRNs is feasible."""
    try:
        crns = request.get_crns()
        if not crns:
            raise HTTPException(
                status_code=400, detail="No CRNs provided for validation. Please provide 'crns_to_merge' or 'crns' field."
            )
        result = await dataset_service.validate_merge(
            dataset_id, current_user.user_id, crns
        )
        # Transform to match frontend expectations
        warning_type = None
        if not result.get("is_valid"):
            warning_type = "room_capacity_exceeded"
        
        return {
            "is_valid": result.get("is_valid", False),
            "message": result.get("warning_message") or result.get("suggested_action") or "Merge is valid",
            "warning_type": warning_type,
            "total_enrollment": result.get("total_enrollment"),
            "max_room_capacity": result.get("max_room_capacity"),
        }
    except DatasetNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/{dataset_id}/merges")
async def set_merges(
    dataset_id: UUID,
    request: SetMergesRequest,
    current_user: Users = Depends(get_current_user),
    dataset_service: DatasetService = Depends(get_dataset_service),
):
    """Set course merges for a dataset."""
    try:
        from src.domain.factories.dataset_factory import DatasetFactory
        from src.services.merge_validator import MergeValidator

        # Validate all merge groups
        files = await dataset_service.get_dataset_files(dataset_id, current_user.user_id)
        scheduling_dataset = DatasetFactory.from_dataframes_to_scheduling_dataset(
            courses_df=files["courses"],
            enrollment_df=files["enrollments"],
            rooms_df=files["rooms"],
        )
        validator = MergeValidator(scheduling_dataset)
        validation_results = validator.validate_multiple_merges(request.merges)

        # Convert validation results to dict format
        validation_dict = {
            merge_id: result.to_dict()
            for merge_id, result in validation_results.items()
        }

        # Save merges
        merges = dataset_service.set_merges(
            dataset_id, current_user.user_id, request.merges
        )
        return {
            "message": "Merges updated successfully",
            "validation": validation_dict,
            "merges": merges,
        }
    except DatasetNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e


@router.delete("/{dataset_id}/merges")
async def clear_merges(
    dataset_id: UUID,
    current_user: Users = Depends(get_current_user),
    dataset_service: DatasetService = Depends(get_dataset_service),
):
    """Clear all course merges for a dataset."""
    try:
        return dataset_service.clear_merges(dataset_id, current_user.user_id)
    except DatasetNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e
