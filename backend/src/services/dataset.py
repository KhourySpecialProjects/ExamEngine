import asyncio
import io
import uuid
from datetime import datetime
from typing import Any
from uuid import UUID

import pandas as pd
from fastapi import UploadFile

from src.core.exceptions import DatasetNotFoundError, StorageError, ValidationError
from src.repo.dataset import DatasetRepo
from src.schemas.db import Datasets
from src.services.storage import storage
from src.services.validation import get_file_statistics, validate_csv_schema


class DatasetService:
    """Business logic for dataset management."""

    def __init__(self, dataset_repo: DatasetRepo):
        self.dataset_repo = dataset_repo

    async def upload_dataset(
        self,
        dataset_name: str,
        courses_file: UploadFile,
        enrollments_file: UploadFile,
        rooms_file: UploadFile,
        user_id: UUID,
    ) -> dict[str, Any]:
        """
        Upload and validate complete dataset.

        Orchestrates: validation → S3 upload → database record creation
        """
        dataset_uuid = uuid.uuid4()

        uploaded_files = {
            "courses": courses_file,
            "enrollments": enrollments_file,
            "rooms": rooms_file,
        }

        validated_files = await self._validate_and_parse_files(uploaded_files)

        try:
            storage_keys = await self._upload_files_to_storage(
                validated_files["contents"], dataset_uuid
            )
        except Exception as e:
            raise StorageError(f"Failed to upload files: {str(e)}") from e

        try:
            # Create dataset record
            dataset = await self._create_dataset_record(
                dataset_uuid=dataset_uuid,
                dataset_name=dataset_name,
                user_id=user_id,
                file_metadata=validated_files["metadata"],
                storage_keys=storage_keys,
            )
        except Exception as e:
            # Cleanup uploaded files
            storage.delete_directory(str(dataset_uuid))
            raise StorageError(f"Database save failed: {str(e)}") from e

        return {
            "dataset_id": str(dataset.dataset_id),
            "dataset_name": dataset.dataset_name,
            "created_at": dataset.upload_date.isoformat(),
            "files": validated_files["metadata"],
            "user_id": str(user_id),
        }

    def get_dataset_info(self, dataset_id: UUID, user_id: UUID) -> dict[str, Any]:
        """
        Get dataset metadata without downloading files.

        Useful for displaying dataset information in the UI
        without the overhead of downloading CSV files from S3.

        Args:
            dataset_id: UUID of dataset
            user_id: ID of user (for authorization)

        Returns:
            Dataset metadata including file statistics

        Raises:
            DatasetNotFoundError: If dataset doesn't exist or user lacks access
        """
        dataset = self.dataset_repo.get_by_id_for_user(dataset_id, user_id)
        if not dataset:
            raise DatasetNotFoundError(
                f"Dataset {dataset_id} not found or access denied"
            )

        return {
            "dataset_id": str(dataset.dataset_id),
            "dataset_name": dataset.dataset_name,
            "created_at": dataset.upload_date.isoformat(),
            "files": {entry["type"]: entry["metadata"] for entry in dataset.file_paths},
        }

    async def _validate_and_parse_files(
        self, files: dict[str, UploadFile]
    ) -> dict[str, Any]:
        """Validate all uploaded files and extract metadata."""
        validation_errors = {}
        file_metadata = {}
        file_contents = {}

        # TODO parallelize
        for file_type, upload_file in files.items():
            try:
                content = await upload_file.read()
                if not content:
                    validation_errors[file_type] = "File is empty"
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

            except pd.errors.ParserError as e:
                validation_errors[file_type] = f"Invalid CSV: {str(e)}"
            except Exception as e:
                validation_errors[file_type] = f"Validation error: {str(e)}"

        if validation_errors:
            raise ValidationError(
                "File validation failed", detail={"errors": validation_errors}
            )

        return {"contents": file_contents, "metadata": file_metadata}

    async def _upload_files_to_storage(
        self, file_contents: dict[str, bytes], dataset_uuid: UUID
    ) -> dict[str, str]:
        """Upload all files to S3."""
        storage_keys = {}
        uploaded_keys = []

        # TODO parallelize
        try:
            for file_type, content in file_contents.items():
                key = f"{dataset_uuid}/{file_type}.csv"
                error, storage_key = await storage.upload_file(content, key)

                if error:
                    for cleanup_key in uploaded_keys:
                        storage.delete_file(cleanup_key)
                    raise StorageError(f"Upload failed for {file_type}: {error}")

                storage_keys[file_type] = storage_key
                uploaded_keys.append(storage_key)

            return storage_keys

        except Exception:
            for cleanup_key in uploaded_keys:
                storage.delete_file(cleanup_key)
            raise

    async def _create_dataset_record(
        self,
        dataset_uuid: UUID,
        dataset_name: str,
        user_id: UUID,
        file_metadata: dict[str, Any],
        storage_keys: dict[str, str],
    ) -> Datasets:
        """Create database record for dataset."""
        file_paths = [
            {
                "type": file_type,
                "storage_key": storage_keys[file_type],
                "metadata": file_metadata[file_type],
            }
            for file_type in ["courses", "enrollments", "rooms"]
        ]

        dataset = Datasets(
            dataset_id=dataset_uuid,
            dataset_name=dataset_name,
            upload_date=datetime.now(),
            user_id=user_id,
            file_paths=file_paths,
        )

        return self.dataset_repo.create(dataset)

    def list_datasets_for_user(
        self, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[dict[str, Any]]:
        """List all datasets for user with formatted metadata."""
        datasets = self.dataset_repo.get_all_for_user(user_id, skip, limit)

        return [
            {
                "dataset_id": str(d.dataset_id),
                "dataset_name": d.dataset_name,
                "created_at": d.upload_date.isoformat(),
                "files": {entry["type"]: entry["metadata"] for entry in d.file_paths},
            }
            for d in datasets
        ]

    async def delete_dataset(self, dataset_id: UUID, user_id: UUID) -> dict[str, Any]:
        """Delete dataset from storage and database."""
        dataset = self.dataset_repo.get_by_id_for_user(dataset_id, user_id)
        if not dataset:
            raise DatasetNotFoundError(
                f"Dataset {dataset_id} not found or access denied"
            )

        # Delete from external storage (S3, etc)
        storage_success = storage.delete_directory(str(dataset_id))

        # Delete from database
        self.dataset_repo.delete(dataset)

        return {
            "message": "Dataset deleted",
            "dataset_id": str(dataset_id),
            "removed_from_storage": storage_success,
        }

    async def get_dataset_files(
        self, dataset_id: UUID, user_id: UUID
    ) -> dict[str, pd.DataFrame]:
        """Download and parse dataset CSV files."""
        dataset = self.dataset_repo.get_by_id_for_user(dataset_id, user_id)
        if not dataset:
            raise DatasetNotFoundError(f"Dataset {dataset_id} not found")
        tasks = [
            self._download_and_parse(file_entry) for file_entry in dataset.file_paths
        ]
        results = await asyncio.gather(*tasks)

        files_data = dict(results)

        return files_data

    async def _download_and_parse(self, file_entry: dict) -> tuple[str, pd.DataFrame]:
        """Download one file and parse it."""
        file_type = file_entry["type"]
        storage_key = file_entry["storage_key"]

        content = await asyncio.to_thread(storage.download_file, storage_key)

        if not content:
            raise StorageError(
                f"Failed to download {file_type}",
                detail={"storage_key": storage_key},
            )

        try:
            df = await asyncio.to_thread(pd.read_csv, io.BytesIO(content))
            return file_type, df
        except Exception as e:
            raise ValidationError(
                f"Failed to parse {file_type}", detail={"error": str(e)}
            ) from e
