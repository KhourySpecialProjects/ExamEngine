import io
from typing import Any
from uuid import UUID

import pandas as pd

from src.domain.adapters import (
    DatasetBuilder,
    DataValidationError,
    SchemaDetectionError,
)
from src.domain.models import Dataset


class ValidationResult:
    """Result of CSV validation with detailed feedback."""

    def __init__(self):
        self.errors: dict[str, list[str]] = {}
        self.warnings: dict[str, list[str]] = {}
        self.statistics: dict[str, Any] = {}

    def add_error(self, file_type: str, message: str):
        """Add an error for a specific file."""
        if file_type not in self.errors:
            self.errors[file_type] = []
        self.errors[file_type].append(message)

    def add_warning(self, file_type: str, message: str):
        """Add a warning for a specific file."""
        if file_type not in self.warnings:
            self.warnings[file_type] = []
        self.warnings[file_type].append(message)

    def is_valid(self) -> bool:
        """Check if validation passed (no errors)."""
        return len(self.errors) == 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "valid": self.is_valid(),
            "errors": self.errors,
            "warnings": self.warnings,
            "statistics": self.statistics,
        }


class DatasetValidator:
    """
    Validates uploaded CSV files and converts to domain models.

    This is your new validation service that replaces the old one.
    It handles all CSV format variations automatically using the adapter system.
    """

    @staticmethod
    async def validate_and_parse_upload(
        files: dict[str, Any],  # FastAPI UploadFile objects
        dataset_id: UUID,
        dataset_name: str,
    ) -> tuple[Dataset, ValidationResult]:
        """
        Validate uploaded files and create a Dataset domain object.

        This is the main entry point for CSV validation.
        It replaces the old _validate_and_parse_files method.

        Args:
            files: Dictionary with keys "courses", "enrollments", "rooms"
            dataset_id: UUID for the dataset
            dataset_name: Human-readable name

        Returns:
            Tuple of (Dataset object, ValidationResult)

        Raises:
            Exception: If validation fails critically
        """
        result = ValidationResult()
        dataframes = {}

        # Step 1: Load and parse CSV files
        for file_type, upload_file in files.items():
            try:
                # Read file content
                content = await upload_file.read()
                if not content:
                    result.add_error(file_type, "File is empty")
                    continue

                # Parse CSV
                df = pd.read_csv(io.BytesIO(content))

                if df.empty:
                    result.add_error(file_type, "CSV has no data rows")
                    continue

                dataframes[file_type] = df

                # Collect basic statistics
                result.statistics[file_type] = {
                    "rows": len(df),
                    "columns": list(df.columns),
                    "filename": upload_file.filename,
                }

            except pd.errors.ParserError as e:
                result.add_error(file_type, f"Invalid CSV format: {str(e)}")
            except Exception as e:
                result.add_error(file_type, f"Error reading file: {str(e)}")

        # If any file failed to load, stop here
        if not result.is_valid():
            raise ValidationError("File parsing failed", result.to_dict())

        # Step 2: Build Dataset using adapters (validates schema automatically)
        try:
            dataset = DatasetBuilder.from_dataframes(
                dataset_id=dataset_id,
                dataset_name=dataset_name,
                course_df=dataframes["courses"],
                enrollment_df=dataframes["enrollments"],
                room_df=dataframes["rooms"],
            )

            # Add domain-level statistics
            result.statistics["dataset"] = {
                "total_courses": len(dataset.courses),
                "total_students": len(dataset.students),
                "total_rooms": len(dataset.rooms),
                "largest_course": max(
                    (c.enrollment_count for c in dataset.courses.values()), default=0
                ),
                "total_enrollment": sum(
                    c.enrollment_count for c in dataset.courses.values()
                ),
            }

        except SchemaDetectionError as e:
            # CSV format doesn't match any known schema
            result.add_error("schema", str(e))
            result.add_error(
                "schema",
                "Please check that your CSV files match the expected format. "
                "If Northeastern changed their CSV format, contact support.",
            )
            raise ValidationError("Schema validation failed", result.to_dict()) from e

        except DataValidationError as e:
            # Data is in correct format but values are invalid
            result.add_error("data", str(e))
            raise ValidationError("Data validation failed", result.to_dict()) from e

        # Step 3: Run dataset-level integrity checks
        integrity_issues = dataset.validate()
        for issue in integrity_issues:
            result.add_warning("dataset", issue)

        return dataset, result


class ValidationError(Exception):
    """Custom exception for validation failures."""

    def __init__(self, message: str, details: dict[str, Any]):
        self.message = message
        self.details = details
        super().__init__(message)


def validate_csv_schema(df: pd.DataFrame, file_type: str) -> list[str]:
    """
    DEPRECATED: Use DatasetValidator.validate_and_parse_upload instead.

    This function is kept for backward compatibility during migration.
    It will be removed once all code is updated to use the new system.
    """
    from src.domain.adapters import CSVSchemaDetector

    try:
        # Try to detect schema raise if does not match schema
        CSVSchemaDetector.detect_schema_version(df, file_type)
        return []  # No missing columns
    except SchemaDetectionError as e:
        return [str(e)]


def get_file_statistics(
    df: pd.DataFrame, file_type: str, file_size: int, filename: str
) -> dict[str, Any]:
    """
    DEPRECATED: Statistics are now generated automatically by DatasetValidator.

    Kept for backward compatibility during migration.
    """
    stats = {
        "filename": filename,
        "rows": len(df),
        "columns": list(df.columns),
        "size_bytes": file_size,
    }

    if file_type == "courses":
        stats["unique_crns"] = int(df["CRN"].nunique())
        stats["total_students"] = int(df["num_students"].sum())
        stats["avg_class_size"] = float(df["num_students"].mean())

    elif file_type == "enrollments":
        # Check for both naming conventions
        student_col = "Student_PIDM" if "Student_PIDM" in df.columns else "student_id"
        stats["unique_students"] = int(df[student_col].nunique())
        stats["unique_crns"] = int(df["CRN"].nunique())
        stats["total_enrollments"] = len(df)

    elif file_type == "rooms":
        stats["unique_rooms"] = int(df["room_name"].nunique())
        stats["total_capacity"] = int(df["capacity"].sum())
        stats["avg_capacity"] = float(df["capacity"].mean())
        stats["max_capacity"] = int(df["capacity"].max())

    return stats
