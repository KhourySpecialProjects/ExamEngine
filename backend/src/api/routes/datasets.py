import io
import uuid
from datetime import datetime

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from src.schemas.db import Datasets, Users
from src.services.auth import get_current_user, get_session
from src.services.storage import storage_service
from src.services.validation import get_file_statistics, validate_csv_schema


router = APIRouter(prefix="/datasets", tags=["datasets"])


def get_db():
    """Database session dependency"""
    db = get_session()
    try:
        yield db
    finally:
        db.close()


@router.post("/upload")
async def upload_dataset(
    dataset_name: str = Form(...),
    courses: UploadFile = File(...),
    enrollments: UploadFile = File(...),
    rooms: UploadFile = File(...),
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload dataset to S3, validate, and save metadata to database."""

    uploaded_files = {"courses": courses, "enrollments": enrollments, "rooms": rooms}

    dataset_uuid = str(uuid.uuid4())
    validation_errors = {}
    file_metadata = {}
    file_contents = {}

    for file_type, upload_file in uploaded_files.items():
        try:
            content = await upload_file.read()
            if not content:
                validation_errors[file_type] = "empty_file"
                continue

            df = pd.read_csv(io.BytesIO(content))

            missing_cols = validate_csv_schema(df, file_type)
            if missing_cols:
                validation_errors[file_type] = (
                    f"Missing columns: {', '.join(missing_cols)}"
                )
                continue

            stats = get_file_statistics(
                df, file_type, len(content), upload_file.filename
            )
            file_metadata[file_type] = stats

            file_contents[file_type] = content

        except Exception as e:
            validation_errors[file_type] = f"validation_error: {str(e)}"

    if validation_errors:
        raise HTTPException(
            status_code=400,
            detail={"message": "Validation failed", "errors": validation_errors},
        )

    storage_keys = {}
    for file_type, content in file_contents.items():
        key = f"{dataset_uuid}/{file_type}.csv"
        error, storage_key = await storage_service.upload_file(content, key)

        if error:
            storage_service.delete_directory(dataset_uuid)
            raise HTTPException(500, f"Upload failed for {file_type}: {error}")

        storage_keys[file_type] = storage_key

    complete_file_paths = []
    for file_type in ["courses", "enrollments", "rooms"]:
        complete_file_paths.append(
            {
                "type": file_type,
                "storage_key": storage_keys[file_type],
                "metadata": file_metadata[file_type],
            }
        )

    try:
        now = datetime.now()

        new_dataset = Datasets(
            dataset_id=uuid.UUID(dataset_uuid),
            dataset_name=dataset_name,
            upload_date=now,
            user_id=current_user.user_id,
            file_paths=complete_file_paths,
        )

        db.add(new_dataset)
        db.commit()
        db.refresh(new_dataset)

        return {
            "dataset_id": dataset_uuid,
            "dataset_name": dataset_name,
            "created_at": now,
            "files": file_metadata,
            "user_id": str(current_user.user_id),
        }

    except Exception as e:
        db.rollback()
        storage_service.delete_directory(dataset_uuid)
        raise HTTPException(500, f"Database error: {str(e)}") from e


@router.get("")
async def list_datasets(
    current_user: Users = Depends(get_current_user), db: Session = Depends(get_db)
):
    """List all datasets for current user."""
    try:
        datasets = (
            db.query(Datasets)
            .filter(Datasets.user_id == current_user.user_id)
            .order_by(Datasets.upload_date.desc())
            .all()
        )

        result = []
        for dataset in datasets:
            files_info = {}
            for file_entry in dataset.file_paths:
                files_info[file_entry["type"]] = file_entry["metadata"]

            result.append(
                {
                    "dataset_id": str(dataset.dataset_id),
                    "dataset_name": dataset.dataset_name,
                    "created_at": dataset.upload_date.isoformat(),
                    "files": files_info,
                }
            )

        return result

    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)}") from e


@router.delete("/{dataset_id}")
async def delete_dataset(
    dataset_id: str,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete dataset from both S3 and database."""
    try:
        dataset = (
            db.query(Datasets)
            .filter(
                Datasets.dataset_id == uuid.UUID(dataset_id),
                Datasets.user_id == current_user.user_id,
            )
            .first()
        )

        if not dataset:
            raise HTTPException(404, "Dataset not found or access denied")

        storage_success = storage_service.delete_directory(dataset_id)

        db.delete(dataset)
        db.commit()

        return {
            "message": "Dataset deleted",
            "dataset_id": dataset_id,
            "removed_from_storage": storage_success,
        }

    except ValueError as e:
        raise HTTPException(400, "Invalid dataset ID format") from e
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Delete error: {str(e)}") from e
