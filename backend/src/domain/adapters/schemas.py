from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

import pandas as pd


class ColumnType(Enum):
    """Data types for CSV columns."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"


@dataclass
class ColumnDefinition:
    """
    Definition of a single CSV column.

    Attributes:
        canonical_name: The standardized name used internally
        aliases: Alternative names this column might have in CSVs
        data_type: Expected data type
        required: Whether this column must be present
        transformer: Optional function to clean/transform the value
        validator: Optional function to validate the value
    """

    canonical_name: str
    aliases: list[str]
    data_type: ColumnType
    required: bool = True
    transformer: Callable[[Any], Any] | None = None
    validator: Callable[[Any], bool] | None = None

    def matches(self, column_name: str) -> bool:
        """Check if a CSV column name matches this definition."""
        normalized = column_name.strip().lower()
        canonical_lower = self.canonical_name.lower()

        if normalized == canonical_lower:
            return True

        return any(alias.lower() == normalized for alias in self.aliases)


# Functions to clean and normalize data
def clean_crn(value: Any) -> str | None:
    """
    Clean CRN values from various formats to standard string.

    Handles:
    - Float from Excel: 11310.0 -> "11310"
    - String with spaces: " 11310 " -> "11310"
    - Empty/null values: -> None
    """
    if pd.isna(value):
        return None

    try:
        # Try converting to float first (handles Excel format)
        return str(int(float(value))).strip()
    except (ValueError, TypeError):
        # Fall back to string conversion
        result = str(value).strip()
        return result if result else None


def clean_student_id(value: Any) -> str | None:
    """Clean student ID to standard string format."""
    if pd.isna(value):
        return None

    result = str(value).strip()
    return result if result else None


def clean_instructor_name(value: Any) -> str | None:
    """Clean instructor name, handling empty strings."""
    if pd.isna(value):
        return None

    result = str(value).strip()
    return result if result else None


def clean_string(value: Any) -> str | None:
    """Clean string, handling empty strings."""
    if pd.isna(value):
        return None

    result = str(value).strip()
    return result if result else None


def parse_int(value: Any) -> int | None:
    """Parse integer value, returning None for invalid data."""
    if pd.isna(value):
        return None

    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def parse_capacity(value: Any) -> int | None:
    """Parse room capacity, ensuring it's positive."""
    capacity = parse_int(value)
    return capacity if capacity and capacity > 0 else None


#  Functions to check if data is valid
def validate_positive_int(value: Any) -> bool:
    """Validate that value is a positive integer."""
    try:
        return int(value) > 0
    except (ValueError, TypeError):
        return False


def validate_non_empty_string(value: Any) -> bool:
    """Validate that value is a non-empty string."""
    return bool(str(value).strip()) if not pd.isna(value) else False


# CSV SCHEMA DEFINITIONS


class CourseSchema:
    """
    Schema for course CSV files.

    Defines all possible formats for course data that the system can accept.
    """

    # Version 1: Original Northeastern format
    V1_COLUMNS = [
        ColumnDefinition(
            canonical_name="crn",
            aliases=["CRN", "Course Registration Number", "crn"],
            data_type=ColumnType.STRING,
            required=True,
            transformer=clean_crn,
            validator=validate_non_empty_string,
        ),
        ColumnDefinition(
            canonical_name="course_code",
            aliases=[
                "CourseID",
                "Course ID",
                "Course Code",
                "course_subject_code",
            ],
            data_type=ColumnType.STRING,
            required=True,
            transformer=lambda x: str(x).strip() if not pd.isna(x) else None,
            validator=validate_non_empty_string,
        ),
        ColumnDefinition(
            canonical_name="enrollment_count",
            aliases=[
                "num_students",
                "Enrollment",
                "Student Count",
                "Size",
                "enrollment_count",
            ],
            data_type=ColumnType.INTEGER,
            required=True,
            transformer=parse_int,
            validator=validate_positive_int,
        ),
        ColumnDefinition(
            canonical_name="instructor_name",
            aliases=[
                "Instructor Name",
                "Instructor",
                "Faculty Name",
                "Professor",
                "instructor_name",
            ],
            data_type=ColumnType.STRING,
            required=True,
            transformer=clean_instructor_name,
            validator=None,
        ),
        ColumnDefinition(
            canonical_name="examination_term",
            aliases=[
                "exam_term",
                "examination_term",
            ],
            data_type=ColumnType.STRING,
            required=True,
            transformer=clean_string,
            validator=None,
        ),
        ColumnDefinition(
            canonical_name="department",
            aliases=[
                "department",
                "dept",
            ],
            data_type=ColumnType.STRING,
            required=True,
            transformer=clean_string,
            validator=None,
        ),
    ]

    @classmethod
    def get_all_versions(cls) -> list[list[ColumnDefinition]]:
        """Return all known schema versions."""
        return [cls.V1_COLUMNS]


class EnrollmentSchema:
    """Schema for enrollment CSV files."""

    V1_COLUMNS = [
        ColumnDefinition(
            canonical_name="student_id",
            aliases=[
                "Student_PIDM",
                "Student ID",
                "PIDM",
                "Student Number",
                "student_id",
                "student_pidm",
            ],
            data_type=ColumnType.STRING,
            required=True,
            transformer=clean_student_id,
            validator=validate_non_empty_string,
        ),
        ColumnDefinition(
            canonical_name="crn",
            aliases=["CRN", "Course Registration Number", "crn"],
            data_type=ColumnType.STRING,
            required=True,
            transformer=clean_crn,
            validator=validate_non_empty_string,
        ),
    ]

    @classmethod
    def get_all_versions(cls) -> list[list[ColumnDefinition]]:
        """Return all known schema versions."""
        return [cls.V1_COLUMNS]


class RoomSchema:
    """Schema for room CSV files."""

    V1_COLUMNS = [
        ColumnDefinition(
            canonical_name="room_name",
            aliases=["room_name", "Room", "Room Name", "Location", "Building + Room"],
            data_type=ColumnType.STRING,
            required=True,
            transformer=lambda x: str(x).strip() if not pd.isna(x) else None,
            validator=validate_non_empty_string,
        ),
        ColumnDefinition(
            canonical_name="capacity",
            aliases=["capacity", "Capacity", "Seats", "Max Capacity"],
            data_type=ColumnType.INTEGER,
            required=True,
            transformer=parse_capacity,
            validator=validate_positive_int,
        ),
    ]

    @classmethod
    def get_all_versions(cls) -> list[list[ColumnDefinition]]:
        """Return all known schema versions."""
        return [cls.V1_COLUMNS]


# SCHEMA REGISTRY

SCHEMA_REGISTRY = {
    "courses": CourseSchema,
    "enrollments": EnrollmentSchema,
    "rooms": RoomSchema,
}


def get_schema(file_type: str) -> type | None:
    """
    Get schema class for a file type.

    Args:
        file_type: One of "courses", "enrollments", "rooms"

    Returns:
        Schema class or None if not found
    """
    return SCHEMA_REGISTRY.get(file_type)
