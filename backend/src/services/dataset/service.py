import asyncio
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
from src.domain.adapters import (
    CombinedExamAdapter,
    CommonExamAdapter,
    CSVSchemaDetector,
    read_upload_csv,
)
from src.domain.adapters.schemas import clean_crn
from src.domain.exceptions import DataValidationError, SchemaDetectionError
from src.domain.models import SchedulingDataset
from src.repo.dataset import DatasetRepo
from src.schemas.db import Datasets
from src.services.dataset.merge_validator import CommonExamValidator, MergeValidator
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
        room_blockouts_file: UploadFile | None = None,
        combined_exams_file: UploadFile | None = None,
        common_exams_file: UploadFile | None = None,
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

        uploaded_files: dict[str, UploadFile] = {
            "courses": courses_file,
            "enrollments": enrollments_file,
            "rooms": rooms_file,
        }
        if room_blockouts_file:
            uploaded_files["room_blockouts"] = room_blockouts_file
        if combined_exams_file:
            uploaded_files["combined_exams"] = combined_exams_file
        if common_exams_file:
            uploaded_files["common_exams"] = common_exams_file

        validated_files = await self._validate_and_parse_files(uploaded_files)

        course_merges, common_exam_groups = self._validate_exam_groups(validated_files)

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
                course_merges=course_merges,
                common_exam_groups=common_exam_groups,
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
            "files": _files_metadata(dataset.file_paths),
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

                df = read_upload_csv(content, file_type)
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
            except DataValidationError as e:
                validation_errors[file_type] = str(e)
            except Exception as e:
                validation_errors[file_type] = f"Validation error: {str(e)}"

        if validation_errors:
            raise ValidationError(
                "File validation failed", detail={"errors": validation_errors}
            )

        return {"contents": file_contents, "metadata": file_metadata}

    def _validate_exam_groups(
        self, validated_files: dict[str, Any]
    ) -> tuple[dict[str, list[str]] | None, dict[str, list[str]] | None]:
        """
        Check combined and common exam groups against courses and rooms.

        Both files already passed their own file-level checks. Reference
        problems (unknown or zero-enrollment CRNs, a combined group split across
        common groups, a common group with fewer than 2 room units) fail the
        upload. Feasibility problems are kept and reported in metadata:
        `combined_exams.over_capacity_groups`, `common_exams.infeasible_groups`
        and `common_exams.student_overlap_groups`.

        Returns:
            (combined groups, common groups); each None if its file is absent

        Raises:
            ValidationError: If any group fails a reference check
        """
        contents = validated_files["contents"]
        metadata = validated_files["metadata"]
        has_combined = "combined_exams" in contents
        has_common = "common_exams" in contents
        if not has_combined and not has_common:
            return None, None

        dataset, zero_enrollment_crns = self._load_reference_dataset(
            contents, "combined_exams" if has_combined else "common_exams"
        )
        errors: dict[str, str] = {}

        merges = None
        if has_combined:
            merges = CombinedExamAdapter.from_dataframe(
                CombinedExamAdapter.read_csv(contents["combined_exams"])
            )
            problems, over_capacity = self._check_combined_exams(
                merges, dataset, zero_enrollment_crns
            )
            if problems:
                errors["combined_exams"] = "; ".join(problems)
            metadata["combined_exams"]["over_capacity_groups"] = over_capacity

        common_groups = None
        if has_common:
            common_groups = CommonExamAdapter.from_dataframe(
                CommonExamAdapter.read_csv(contents["common_exams"])
            )
            problems, infeasible, overlap = self._check_common_exams(
                common_groups, merges or {}, dataset, zero_enrollment_crns
            )
            if problems:
                errors["common_exams"] = "; ".join(problems)
            metadata["common_exams"]["infeasible_groups"] = infeasible
            metadata["common_exams"]["student_overlap_groups"] = overlap

        if errors:
            raise ValidationError("File validation failed", detail={"errors": errors})

        return merges, common_groups

    def _load_reference_dataset(
        self, contents: dict[str, bytes], error_key: str
    ) -> tuple[SchedulingDataset, set[str]]:
        """
        Build the SchedulingDataset the scheduler will see for this upload.

        Zero-enrollment courses are dropped, matching `drop_zero_enrollment`.

        Returns:
            (scheduling dataset, CRNs dropped for zero enrollment)

        Raises:
            ValidationError: Under `error_key` if the dataset cannot be built
        """
        from src.domain.factories.dataset_factory import DatasetFactory

        def read(file_type: str) -> pd.DataFrame:
            return read_upload_csv(contents[file_type], file_type)

        raw_courses_df = read("courses")
        courses_df, allowed_crns = self._filter_nonzero_enrollment(raw_courses_df)
        enrollments_df = read("enrollments")
        if allowed_crns is not None:
            enrollments_df = self._filter_by_allowed_crns(enrollments_df, allowed_crns)

        # Courses passed schema validation already, so detection cannot fail here.
        _, course_mapping = CSVSchemaDetector.detect_schema_version(
            raw_courses_df, "courses"
        )
        crn_col = next(
            csv_col
            for csv_col, canonical in course_mapping.items()
            if canonical == "Course_Reference_Number"
        )
        dropped_df = raw_courses_df.drop(index=courses_df.index)
        # A CRN repeated with a nonzero row is still a real course.
        zero_enrollment_crns = {clean_crn(v) for v in dropped_df[crn_col]} - (
            allowed_crns or set()
        )

        try:
            dataset = DatasetFactory.from_dataframes_to_scheduling_dataset(
                courses_df=courses_df,
                enrollment_df=enrollments_df,
                rooms_df=read("rooms"),
            )
        except (DataValidationError, SchemaDetectionError) as e:
            raise ValidationError(
                "File validation failed",
                detail={
                    "errors": {
                        error_key: (
                            f"Could not check exam groups against courses/rooms: {e}"
                        )
                    }
                },
            ) from e
        return dataset, zero_enrollment_crns

    @staticmethod
    def _crn_reference_problems(
        crns: list[str],
        dataset: SchedulingDataset,
        zero_enrollment_crns: set[str],
        zero_reason: str,
    ) -> list[str]:
        """Describe CRNs missing from courses or dropped for zero enrollment."""
        empty = [c for c in crns if c in zero_enrollment_crns]
        unknown = [c for c in crns if c not in dataset.courses and c not in empty]
        reasons = []
        if unknown:
            reasons.append(f"CRNs not found in courses: {unknown}")
        if empty:
            reasons.append(f"CRNs with zero enrollment {zero_reason}: {empty}")
        return reasons

    def _check_combined_exams(
        self,
        merges: dict[str, list[str]],
        dataset: SchedulingDataset,
        zero_enrollment_crns: set[str],
    ) -> tuple[list[str], list[dict[str, Any]]]:
        """
        Check combined groups against courses and rooms.

        Returns:
            (problems failing the upload, over-capacity groups for metadata)
        """
        results = MergeValidator(dataset).validate_multiple_merges(merges)

        problems = []
        for group, result in results.items():
            if result.can_proceed:
                continue
            reasons = self._crn_reference_problems(
                merges[group], dataset, zero_enrollment_crns, "cannot be merged"
            )
            reason = "; ".join(reasons) or result.warning_message
            problems.append(f"exam group '{group}': {reason}")

        over_capacity = [
            {
                "group": group,
                "total_enrollment": result.total_enrollment,
                "max_room_capacity": result.max_room_capacity,
            }
            for group, result in results.items()
            if result.can_proceed and not result.has_suitable_room
        ]
        return problems, over_capacity

    def _check_common_exams(
        self,
        common_groups: dict[str, list[str]],
        merges: dict[str, list[str]],
        dataset: SchedulingDataset,
        zero_enrollment_crns: set[str],
    ) -> tuple[list[str], list[dict[str, Any]], list[dict[str, Any]]]:
        """
        Check common groups against courses, rooms and combined groups.

        Returns:
            (problems failing the upload, infeasible groups, groups with
            students enrolled in more than one of their room units)
        """
        validator = CommonExamValidator(dataset, merges)
        problems = validator.cross_group_problems(common_groups)
        infeasible: list[dict[str, Any]] = []
        overlap: list[dict[str, Any]] = []
        for group, crns in common_groups.items():
            reasons = self._crn_reference_problems(
                crns, dataset, zero_enrollment_crns, "cannot be in a common exam"
            )
            if reasons:
                problems.append(f"common group '{group}': {'; '.join(reasons)}")
                continue
            try:
                result = validator.validate(crns)
            except ValueError as e:
                problems.append(f"common group '{group}': {e}")
                continue
            if not result.fits_rooms:
                infeasible.append({"group": group, "reason": result.warning_message})
            if result.overlapping_students:
                overlap.append(
                    {"group": group, "students": result.overlapping_students}
                )
        return problems, infeasible, overlap

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
        course_merges: dict[str, list[str]] | None = None,
        common_exam_groups: dict[str, list[str]] | None = None,
    ) -> Datasets:
        """Create database record for dataset."""
        file_paths = [
            {
                "type": file_type,
                "storage_key": storage_keys[file_type],
                "metadata": file_metadata[file_type],
            }
            for file_type in storage_keys
        ]

        dataset = Datasets(
            dataset_id=dataset_uuid,
            dataset_name=dataset_name,
            upload_date=datetime.now(),
            user_id=user_id,
            file_paths=file_paths,
            course_merges=course_merges,
            common_exam_groups=common_exam_groups,
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
                "files": _files_metadata(d.file_paths),
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

        filtered_courses_df, allowed_crns = self._filter_nonzero_enrollment(courses_df)

        # If we couldn't determine CRNs/columns, keep enrollments as-is.
        filtered_enrollments_df = (
            self._filter_by_allowed_crns(enrollments_df, allowed_crns)
            if allowed_crns is not None
            else enrollments_df
        )

        result: dict[str, pd.DataFrame] = {
            "courses": filtered_courses_df,
            "enrollments": filtered_enrollments_df,
            "rooms": files["rooms"],
        }
        if "room_blockouts" in files:
            result["room_blockouts"] = files["room_blockouts"]
        return result

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
        enrollment_transformer = (
            col_defs.get("Total_Enrollment").transformer
            if col_defs.get("Total_Enrollment")
            else None
        )
        crn_transformer = (
            col_defs.get("Course_Reference_Number").transformer
            if col_defs.get("Course_Reference_Number")
            else None
        )

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
        crn_transformer = (
            col_defs.get("Course_Reference_Number").transformer
            if col_defs.get("Course_Reference_Number")
            else None
        )

        crn_series = enrollments_df[crn_col]
        if crn_transformer:
            crn_series = crn_series.apply(crn_transformer)

        mask = crn_series.isin(allowed_crns)
        return enrollments_df.loc[mask].copy()

    async def _download_and_parse(self, file_entry: dict) -> tuple[str, pd.DataFrame]:
        """Download one file and parse it."""
        file_type = _entry_type(file_entry)
        storage_key = file_entry["storage_key"]

        content = await asyncio.to_thread(storage.download_file, storage_key)

        if not content:
            raise StorageError(
                f"Failed to download {file_type}",
                detail={"storage_key": storage_key},
            )

        try:
            df = await asyncio.to_thread(read_upload_csv, content, file_type)
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

    def get_merges(
        self, dataset_id: UUID, user_id: UUID
    ) -> dict[str, list[str]] | None:
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

    async def _common_exam_validator(
        self, dataset_id: UUID, user_id: UUID
    ) -> CommonExamValidator:
        """Build a common exam validator from the stored files and merges."""
        from src.domain.factories.dataset_factory import DatasetFactory

        files = await self.get_dataset_files(dataset_id, user_id)
        scheduling_dataset = DatasetFactory.from_dataframes_to_scheduling_dataset(
            courses_df=files["courses"],
            enrollment_df=files["enrollments"],
            rooms_df=files["rooms"],
        )
        merges = self.get_merges(dataset_id, user_id) or {}
        return CommonExamValidator(scheduling_dataset, merges)

    async def validate_common_exam(
        self, dataset_id: UUID, user_id: UUID, crns: list[str]
    ) -> dict[str, Any]:
        """
        Validate one common exam group against the dataset and its merges.

        Returns:
            Validation result dictionary (`is_valid` is False when the group's
            room units cannot all be seated at once)

        Raises:
            ValueError: If a CRN is unknown or the group has fewer than 2 room
                units after combined-group closure
        """
        if not crns:
            raise ValueError("Cannot validate an empty common exam group")
        validator = await self._common_exam_validator(dataset_id, user_id)
        return validator.validate(crns).to_dict()

    async def validate_common_exam_groups(
        self, dataset_id: UUID, user_id: UUID, groups: dict[str, list[str]]
    ) -> dict[str, dict[str, Any]]:
        """
        Validate a full set of common exam groups before saving it.

        Returns:
            Validation result dictionary per group label

        Raises:
            ValueError: Listing every structural problem (unknown CRN, CRN in
                several groups, combined group split across groups, group with
                fewer than 2 room units). Infeasible groups are not errors.
        """
        validator = await self._common_exam_validator(dataset_id, user_id)
        problems = validator.cross_group_problems(groups)
        results: dict[str, dict[str, Any]] = {}
        for label, crns in groups.items():
            try:
                results[label] = validator.validate(crns).to_dict()
            except ValueError as e:
                problems.append(f"common group '{label}': {e}")
        if problems:
            raise ValueError("; ".join(problems))
        return results

    def get_common_exams(
        self, dataset_id: UUID, user_id: UUID
    ) -> dict[str, list[str]] | None:
        """Get common exam groups for a dataset."""
        dataset = self.dataset_repo.get_by_id_for_user(dataset_id, user_id)
        if not dataset:
            raise DatasetNotFoundError(f"Dataset {dataset_id} not found")
        return dataset.common_exam_groups

    def set_common_exams(
        self, dataset_id: UUID, user_id: UUID, groups: dict[str, list[str]]
    ) -> dict[str, list[str]] | None:
        """
        Set common exam groups for a dataset.

        Args:
            dataset_id: Dataset ID
            user_id: User ID for authorization
            groups: Dictionary mapping common group label to its CRNs

        Returns:
            Updated common exam groups
        """
        dataset = self.dataset_repo.get_by_id_for_user(dataset_id, user_id)
        if not dataset:
            raise DatasetNotFoundError(f"Dataset {dataset_id} not found")

        updated = self.dataset_repo.set_common_exams(dataset_id, groups)
        return updated.common_exam_groups if updated else None

    def clear_common_exams(self, dataset_id: UUID, user_id: UUID) -> dict[str, Any]:
        """Clear all common exam groups for a dataset."""
        dataset = self.dataset_repo.get_by_id_for_user(dataset_id, user_id)
        if not dataset:
            raise DatasetNotFoundError(f"Dataset {dataset_id} not found")

        success = self.dataset_repo.clear_common_exams(dataset_id)
        return {"success": success, "message": "Common exams cleared"}


def _entry_type(file_entry: dict[str, Any]) -> str:
    """
    File type of a stored `file_paths` entry.

    Datasets uploaded before the combined/common split stored the combined exam
    file under type "common_exams" (metadata with `exam_groups`); report those
    as "combined_exams".
    """
    file_type = file_entry["type"]
    if file_type == "common_exams" and "exam_groups" in file_entry["metadata"]:
        return "combined_exams"
    return file_type


def _files_metadata(file_paths: list[dict[str, Any]]) -> dict[str, Any]:
    """Map each stored file's type to its upload metadata."""
    return {_entry_type(entry): entry["metadata"] for entry in file_paths}
