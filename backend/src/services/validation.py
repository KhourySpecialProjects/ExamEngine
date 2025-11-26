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
    """Generate statistics for a validated CSV file."""
    stats = {
        "filename": filename,
        "rows": len(df),
        "columns": list(df.columns),
        "size_bytes": file_size,
    }

    if file_type == "courses":
        stats["unique_crns"] = int(df["CRN"].nunique())
        if "num_students" in df.columns:
            stats["total_students"] = int(df["num_students"].sum())
            stats["avg_class_size"] = float(df["num_students"].mean())

    elif file_type == "enrollments":
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
