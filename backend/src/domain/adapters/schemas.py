from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

import pandas as pd

from src.domain.constants import EXAM_BLOCKS, LEGACY_EXAM_BLOCKS


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


_YES = {"y", "yes", "1", "true"}
_NO = {"n", "no", "0", "false", ""}


def parse_yes_no(value: Any) -> bool | None:
    """Parse a yes/no cell: y/yes/1/true or n/no/0/false, any case.

    Blank means no. Returns None for anything else so callers can report it.
    """
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return False
    if isinstance(value, int | float):
        return {1: True, 0: False}.get(value)
    text = str(value).strip().lower()
    if text in _YES:
        return True
    if text in _NO:
        return False
    return None


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
            canonical_name="Course_Reference_Number",
            aliases=["crn", "CRN", "Course Registration Number"],
            data_type=ColumnType.STRING,
            required=True,
            transformer=clean_crn,
            validator=validate_non_empty_string,
        ),
        ColumnDefinition(
            canonical_name="Course_Identification",
            aliases=[
                "course_code",
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
            canonical_name="Total_Enrollment",
            aliases=[
                "enrollment_count",
                "num_students",
                "Enrollment",
                "Student Count",
                "Size",
                "UG_Enrollment",
            ],
            data_type=ColumnType.INTEGER,
            required=True,
            transformer=parse_int,
            validator=validate_positive_int,
        ),
        ColumnDefinition(
            canonical_name="Primary_Instructor_PIDM",
            aliases=[
                "instructor_name",
                "Instructor Name",
                "Instructor",
                "Faculty Name",
                "Professor",
            ],
            data_type=ColumnType.STRING,
            required=False,
            transformer=clean_instructor_name,
            validator=None,
        ),
        ColumnDefinition(
            canonical_name="Academic_Period_NUFreeze",
            aliases=[
                "exam_term",
                "examination_term",
                "Academic_Period",
            ],
            data_type=ColumnType.STRING,
            required=False,
            transformer=clean_string,
            validator=None,
        ),
        ColumnDefinition(
            canonical_name="Course_Department_Code",
            aliases=[
                "department",
                "dept",
                "Course_Department_Desc",
            ],
            data_type=ColumnType.STRING,
            required=False,
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
            canonical_name="Student_PIDM",
            aliases=[
                "NUID",
                "NU ID",
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
            canonical_name="Course_Reference_Number",
            aliases=["crn", "CRN", "Course Registration Number"],
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
            canonical_name="Location Name",
            aliases=[
                "room_name",
                "Room",
                "Room Name",
                "Location",
                "Building + Room",
                "Location Formal Name",
            ],
            data_type=ColumnType.STRING,
            required=True,
            transformer=lambda x: str(x).strip() if not pd.isna(x) else None,
            validator=validate_non_empty_string,
        ),
        ColumnDefinition(
            canonical_name="Capacity",
            aliases=["capacity", "Seats", "Max Capacity"],
            data_type=ColumnType.INTEGER,
            required=True,
            transformer=parse_capacity,
            validator=validate_positive_int,
        ),
        ColumnDefinition(
            canonical_name="LargeOnly",
            aliases=["Large Only", "Large_Only", "Large-Only"],
            data_type=ColumnType.BOOLEAN,
            required=False,
            transformer=parse_yes_no,
            validator=None,
        ),
    ]

    @classmethod
    def get_all_versions(cls) -> list[list[ColumnDefinition]]:
        """Return all known schema versions."""
        return [cls.V1_COLUMNS]


_DAY_NAME_TO_INDEX = {
    name.lower(): idx
    for idx, name in enumerate(
        ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    )
}
# Block labels, current and legacy, by index; lowercase without spaces.
_BLOCK_TIME_TO_INDEX = {
    block.label.lower(): index
    for blocks in (EXAM_BLOCKS, LEGACY_EXAM_BLOCKS)
    for index, block in enumerate(blocks)
}


def parse_day(value: Any) -> int | None:
    """Parse day value: accepts 0-6 integer or day name string."""
    if pd.isna(value):
        return None
    s = str(value).strip().lower()
    if s in _DAY_NAME_TO_INDEX:
        return _DAY_NAME_TO_INDEX[s]
    try:
        idx = int(float(s))
        return idx if 0 <= idx <= 6 else None
    except (ValueError, TypeError):
        return None


def parse_block(value: Any) -> int | None:
    """Parse block value: accepts 0-4 integer or time string like '8AM-10AM'.

    The labels the app used before the times were corrected ('9AM-11AM', ...)
    still parse, to the same block index.
    """
    if pd.isna(value):
        return None
    s = str(value).strip().lower().replace(" ", "")
    if s in _BLOCK_TIME_TO_INDEX:
        return _BLOCK_TIME_TO_INDEX[s]
    try:
        idx = int(float(s))
        return idx if 0 <= idx <= 4 else None
    except (ValueError, TypeError):
        return None


class RoomBlockoutSchema:
    """Schema for room blockout CSV files.

    Expected CSV format:
        Room,Day,Block
        Shillman 105,0,2
        West Village H 212,Monday,8AM-10AM

    Day accepts 0-6 (Mon=0) or full day names.
    Block accepts 0-4 or time strings (e.g. '8AM-10AM').
    """

    V1_COLUMNS = [
        ColumnDefinition(
            canonical_name="Room",
            aliases=["room", "Location Name", "Location", "Room Name", "room_name"],
            data_type=ColumnType.STRING,
            required=True,
            transformer=lambda x: str(x).strip() if not pd.isna(x) else None,
            validator=validate_non_empty_string,
        ),
        ColumnDefinition(
            canonical_name="Day",
            aliases=["day", "day_index", "Day Index", "Weekday"],
            data_type=ColumnType.INTEGER,
            required=True,
            transformer=parse_day,
            validator=lambda x: x is not None and 0 <= x <= 6,
        ),
        ColumnDefinition(
            canonical_name="Block",
            aliases=["block", "block_index", "Block Index", "Time Block"],
            data_type=ColumnType.INTEGER,
            required=True,
            transformer=parse_block,
            validator=lambda x: x is not None and 0 <= x <= 4,
        ),
    ]

    @classmethod
    def get_all_versions(cls) -> list[list[ColumnDefinition]]:
        """Return all known schema versions."""
        return [cls.V1_COLUMNS]


class CombinedExamSchema:
    """Schema for combined exam (merged sections) CSV files.

    Expected CSV format (one row per group/CRN pair):
        ExamGroup,CRN
        CS Foundations Final,11310
        CS Foundations Final,11311

    Sections that share an Exam_Group label sit one exam: same time block and
    same room.
    """

    V1_COLUMNS = [
        ColumnDefinition(
            canonical_name="Exam_Group",
            aliases=[
                "ExamGroup",
                "Exam Group",
                "Common Exam",
                "merge_group",
                "merge_group_id",
                "Group",
                "group_id",
            ],
            data_type=ColumnType.STRING,
            required=True,
            transformer=clean_string,
            validator=validate_non_empty_string,
        ),
        ColumnDefinition(
            canonical_name="Course_Reference_Number",
            aliases=["crn", "CRN", "Course Registration Number"],
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


class CommonExamSchema:
    """Schema for common exam CSV files.

    Expected CSV format (one row per group/CRN pair):
        Common_Group,CRN
        BIOL 1101 Final,11111
        BIOL 1101 Final,33333

    Sections that share a Common_Group label sit in the same time block but in
    different rooms. The group header aliases are deliberately disjoint from the
    combined exam file's, so a combined file uploaded as common exams fails.
    """

    V1_COLUMNS = [
        ColumnDefinition(
            canonical_name="Common_Group",
            aliases=["CommonGroup", "Common Group", "Common_Group", "common_group"],
            data_type=ColumnType.STRING,
            required=True,
            transformer=clean_string,
            validator=validate_non_empty_string,
        ),
        ColumnDefinition(
            canonical_name="Course_Reference_Number",
            aliases=["crn", "CRN", "Course Registration Number"],
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


# SCHEMA REGISTRY

SCHEMA_REGISTRY = {
    "courses": CourseSchema,
    "enrollments": EnrollmentSchema,
    "rooms": RoomSchema,
    "room_blockouts": RoomBlockoutSchema,
    "combined_exams": CombinedExamSchema,
    "common_exams": CommonExamSchema,
}


def get_schema(file_type: str) -> type | None:
    """
    Get schema class for a file type.

    Args:
        file_type: One of "courses", "enrollments", "rooms", "room_blockouts",
            "combined_exams", "common_exams"

    Returns:
        Schema class or None if not found
    """
    return SCHEMA_REGISTRY.get(file_type)
