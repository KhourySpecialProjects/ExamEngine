from typing import Any

import pandas as pd

from src.domain.adapters import CSVSchemaDetector
from src.domain.exceptions import SchemaDetectionError


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


class ValidationError(Exception):
    """Custom exception for validation failures."""

    def __init__(self, message: str, details: dict[str, Any]):
        self.message = message
        self.details = details
        super().__init__(message)


def validate_csv_schema(df: pd.DataFrame, file_type: str) -> list[str]:
    """
    Validate CSV schema using the adapter's schema detector.

    Returns list of error messages (empty if valid).
    """
    try:
        CSVSchemaDetector.detect_schema_version(df, file_type)
        return []
    except SchemaDetectionError as e:
        return [str(e)]


def get_file_statistics(
    df: pd.DataFrame, file_type: str, file_size: int, filename: str
) -> dict[str, Any]:
    """
    Generate statistics for a validated CSV file.

    """
    stats = {
        "filename": filename,
        "rows": len(df),
        "columns": list(df.columns),
        "size_bytes": file_size,
    }

    # Detect schema and get column mapping (CSV column -> canonical name)
    try:
        _, column_mapping = CSVSchemaDetector.detect_schema_version(df, file_type)
    except SchemaDetectionError:
        # Schema detection failed, return basic stats only
        return stats

    # Invert mapping: canonical_name -> actual CSV column name
    canonical_to_csv = {v: k for k, v in column_mapping.items()}

    def get_column(canonical_name: str) -> str | None:
        """Get actual CSV column name for a canonical name."""
        return canonical_to_csv.get(canonical_name)

    def safe_col(canonical_name: str) -> pd.Series | None:
        """Safely get column data by canonical name."""
        csv_col = get_column(canonical_name)
        return df[csv_col] if csv_col and csv_col in df.columns else None

    if file_type == "courses":
        crn_col = safe_col("Course_Reference_Number")
        if crn_col is not None:
            stats["unique_crns"] = int(crn_col.nunique())

        enrollment_col = safe_col("Total_Enrollment")
        if enrollment_col is not None:
            stats["total_students"] = int(enrollment_col.sum())
            stats["avg_class_size"] = round(float(enrollment_col.mean()), 2)

    elif file_type == "enrollments":
        student_col = safe_col("Student_PIDM")
        if student_col is not None:
            stats["unique_students"] = int(student_col.nunique())

        crn_col = safe_col("Course_Reference_Number")
        if crn_col is not None:
            stats["unique_crns"] = int(crn_col.nunique())

        stats["total_enrollments"] = len(df)

    elif file_type == "rooms":
        room_col = safe_col("Location Name")
        if room_col is not None:
            stats["unique_rooms"] = int(room_col.nunique())

        capacity_col = safe_col("Capacity")
        if capacity_col is not None:
            stats["total_capacity"] = int(capacity_col.sum())
            stats["avg_capacity"] = round(float(capacity_col.mean()), 2)
            stats["max_capacity"] = int(capacity_col.max())

    return stats
