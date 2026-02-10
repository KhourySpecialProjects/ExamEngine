import asyncio
import io
import uuid
from datetime import datetime
from typing import Any
from uuid import UUID

import pandas as pd
from fastapi import UploadFile

from src.core.exceptions import (
    DatasetExistsError,
    DatasetNotFoundError,
    StorageError,
    ValidationError,
)
from src.domain.adapters import CSVSchemaDetector
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

        if self.dataset_repo.dataset_exists(dataset_name, user_id):
            raise DatasetExistsError(
                f"Dataset of name: {dataset_name} already exists",
            )

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
                print(df.head())

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

        # Delete from external storage (S3, etc) with prefix
        storage_success = storage.delete_directory(prefix=str(dataset_id))

        # Soft delete from database
        is_deleted = self.dataset_repo.soft_delete(
            dataset_id=dataset_id, user_id=user_id
        )

        return {
            "message": "Dataset deleted",
            "dataset_id": str(dataset_id),
            "removed_from_storage": storage_success,
            "soft_deleted?": is_deleted,
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

    async def drop_zero_enrollment(
        self, dataset_id: UUID, user_id: UUID
    ) -> dict[str, pd.DataFrame]:
        """
        Return dataset files with zero-enrollment courses removed.

        Args:
            dataset_id: Dataset ID
            user_id: User ID for authorization
        
        Returns:
            Dictionary with filtered courses, enrollments, and rooms dataframes
        """
        files = await self.get_dataset_files(dataset_id, user_id)

        courses_df = files["courses"]
        enrollments_df = files["enrollments"]

        filtered_courses_df, allowed_crns = self._filter_nonzero_enrollment(
            courses_df
        )

        # If we couldn't determine CRNs/columns, keep enrollments as-is.
        filtered_enrollments_df = (
            self._filter_by_allowed_crns(enrollments_df, allowed_crns)
            if allowed_crns is not None
            else enrollments_df
        )

        return {
            "courses": filtered_courses_df,
            "enrollments": filtered_enrollments_df,
            "rooms": files["rooms"],
        }

    def _filter_nonzero_enrollment(
        self, courses_df: pd.DataFrame
    ) -> tuple[pd.DataFrame, set[str] | None]:
        """
        Filter the courses DataFrame to remove rows where Total_Enrollment == 0.

        Returns:
            (filtered_df, allowed_crns)
        """
        try:
            schema, column_mapping = CSVSchemaDetector.detect_schema_version(
                courses_df, "courses"
            )
        except Exception:
            # If schema detection fails, don't change behavior.
            return courses_df.copy(), None

        canonical_to_csv = {canonical: csv for csv, canonical in column_mapping.items()}
        enrollment_col = canonical_to_csv.get("Total_Enrollment")
        crn_col = canonical_to_csv.get("Course_Reference_Number")
        if not enrollment_col or not crn_col:
            return courses_df.copy(), None

        col_defs = {cd.canonical_name: cd for cd in schema}
        enrollment_transformer = col_defs.get("Total_Enrollment").transformer if col_defs.get("Total_Enrollment") else None
        crn_transformer = col_defs.get("Course_Reference_Number").transformer if col_defs.get("Course_Reference_Number") else None

        enrollment_series = courses_df[enrollment_col]
        if enrollment_transformer:
            enrollment_series = enrollment_series.apply(enrollment_transformer)

        # Keep only nonzero enrollments; treat None/NaN as zero for this filter.
        try:
            nonzero_mask = enrollment_series.fillna(0).astype(int) != 0
        except Exception:
            nonzero_mask = enrollment_series.fillna(0) != 0

        filtered_df = courses_df.loc[nonzero_mask].copy()

        crn_series = filtered_df[crn_col]
        if crn_transformer:
            crn_series = crn_series.apply(crn_transformer)

        allowed_crns = {crn for crn in crn_series.tolist() if crn}
        return filtered_df, allowed_crns

    def _filter_by_allowed_crns(
        self, enrollments_df: pd.DataFrame, allowed_crns: set[str]
    ) -> pd.DataFrame:
        """
        Filter enrollments to only those whose CRN is in allowed_crns.

        This keeps enrollments consistent with a temporarily filtered course list.
        """
        if not allowed_crns:
            return enrollments_df.copy()

        try:
            schema, column_mapping = CSVSchemaDetector.detect_schema_version(
                enrollments_df, "enrollments"
            )
        except Exception:
            return enrollments_df.copy()

        canonical_to_csv = {canonical: csv for csv, canonical in column_mapping.items()}
        crn_col = canonical_to_csv.get("Course_Reference_Number")
        if not crn_col:
            return enrollments_df.copy()

        col_defs = {cd.canonical_name: cd for cd in schema}
        crn_transformer = col_defs.get("Course_Reference_Number").transformer if col_defs.get("Course_Reference_Number") else None

        crn_series = enrollments_df[crn_col]
        if crn_transformer:
            crn_series = crn_series.apply(crn_transformer)

        mask = crn_series.isin(allowed_crns)
        return enrollments_df.loc[mask].copy()

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

    async def validate_merge(
        self, dataset_id: UUID, user_id: UUID, crns: list[str]
    ) -> dict[str, Any]:
        """
        Validate if merging multiple CRNs is feasible.

        Args:
            dataset_id: Dataset ID
            user_id: User ID for authorization
            crns: List of CRNs to merge

        Returns:
            Validation result dictionary
        """
        from src.domain.factories.dataset_factory import DatasetFactory
        from src.services.dataset.merge_validator import MergeValidator

        # Load dataset files
        files = await self.get_dataset_files(dataset_id, user_id)

        # Build SchedulingDataset for validation
        scheduling_dataset = DatasetFactory.from_dataframes_to_scheduling_dataset(
            courses_df=files["courses"],
            enrollment_df=files["enrollments"],
            rooms_df=files["rooms"],
        )

        # Validate merge
        validator = MergeValidator(scheduling_dataset)
        result = validator.validate_merge(crns)

        return result.to_dict()

    def get_merges(self, dataset_id: UUID, user_id: UUID) -> dict[str, list[str]] | None:
        """Get course merges for a dataset."""
        dataset = self.dataset_repo.get_by_id_for_user(dataset_id, user_id)
        if not dataset:
            raise DatasetNotFoundError(f"Dataset {dataset_id} not found")
        return dataset.course_merges

    def set_merges(
        self, dataset_id: UUID, user_id: UUID, merges: dict[str, list[str]]
    ) -> dict[str, Any]:
        """
        Set course merges for a dataset.

        Args:
            dataset_id: Dataset ID
            user_id: User ID for authorization
            merges: Dictionary mapping merge_group_id to list of CRNs

        Returns:
            Updated merges dictionary
        """
        dataset = self.dataset_repo.get_by_id_for_user(dataset_id, user_id)
        if not dataset:
            raise DatasetNotFoundError(f"Dataset {dataset_id} not found")

        updated = self.dataset_repo.set_merges(dataset_id, merges)
        return updated.course_merges if updated else None

    def clear_merges(self, dataset_id: UUID, user_id: UUID) -> dict[str, Any]:
        """Clear all course merges for a dataset."""
        dataset = self.dataset_repo.get_by_id_for_user(dataset_id, user_id)
        if not dataset:
            raise DatasetNotFoundError(f"Dataset {dataset_id} not found")

        success = self.dataset_repo.clear_merges(dataset_id)
        return {"success": success, "message": "Merges cleared"}