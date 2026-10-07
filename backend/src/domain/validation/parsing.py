"""Parse a dataset's uploaded CSV bytes into validation records.

Uses the upload parsing and schema detection shared with the rest of the app,
but keeps every row (duplicates included) instead of building domain objects,
so the data checks can report what is actually in the files.
"""

import logging
from collections.abc import Callable, Mapping
from typing import Any

import pandas as pd

from src.domain.adapters import CSVSchemaDetector, RoomBlockoutAdapter, read_upload_csv
from src.domain.validation.snapshot import (
    COURSES,
    ENROLLMENTS,
    ROOM_BLOCKOUTS,
    ROOMS,
    CourseRecord,
    DatasetFiles,
    EnrollmentRecord,
    RoomRecord,
)


logger = logging.getLogger("examengine.validation")


def _canonical_columns(content: bytes, file_type: str) -> dict[str, list[Any]]:
    """Read a file and return canonical column name -> transformed cell values."""
    df = read_upload_csv(content, file_type)
    schema, column_mapping = CSVSchemaDetector.detect_schema_version(df, file_type)
    df = df.rename(columns=column_mapping)
    columns: dict[str, list[Any]] = {}
    for col_def in schema:
        if col_def.canonical_name not in df.columns:
            continue
        values = df[col_def.canonical_name].tolist()
        transform: Callable[[Any], Any] = col_def.transformer or _identity
        columns[col_def.canonical_name] = [_none_if_nan(transform(v)) for v in values]
    return columns


def _identity(value: Any) -> Any:
    return value


def _none_if_nan(value: Any) -> Any:
    if value is None:
        return None
    try:
        return None if pd.isna(value) else value
    except (TypeError, ValueError):
        return value


def parse_courses(content: bytes) -> tuple[CourseRecord, ...]:
    """Courses file rows with a CRN (enrollment None when blank/unparseable)."""
    columns = _canonical_columns(content, COURSES)
    crns = columns["Course_Reference_Number"]
    enrollments = columns.get("Total_Enrollment", [None] * len(crns))
    instructors = columns.get("Primary_Instructor_PIDM", [None] * len(crns))
    return tuple(
        CourseRecord(crn=str(crn), total_enrollment=enrollment, instructor=instructor)
        for crn, enrollment, instructor in zip(
            crns, enrollments, instructors, strict=True
        )
        if crn
    )


def parse_enrollments(content: bytes) -> tuple[EnrollmentRecord, ...]:
    """Enrollment rows with both a student ID and a CRN."""
    columns = _canonical_columns(content, ENROLLMENTS)
    return tuple(
        EnrollmentRecord(student_id=str(student), crn=str(crn))
        for student, crn in zip(
            columns["Student_PIDM"], columns["Course_Reference_Number"], strict=True
        )
        if student and crn
    )


def parse_rooms(content: bytes) -> tuple[RoomRecord, ...]:
    """Room rows with a name and a positive capacity (as the app loads them)."""
    columns = _canonical_columns(content, ROOMS)
    names = columns["Location Name"]
    large_only = columns.get("LargeOnly", [False] * len(names))
    return tuple(
        RoomRecord(name=str(name), capacity=int(capacity), large_only=bool(flag))
        for name, capacity, flag in zip(
            names, columns["Capacity"], large_only, strict=True
        )
        if name and capacity
    )


def parse_blockouts(content: bytes) -> dict[str, frozenset[tuple[int, int]]]:
    """Room name -> blocked (day_index, block_index) slots."""
    raw = RoomBlockoutAdapter.from_dataframe(read_upload_csv(content, ROOM_BLOCKOUTS))
    return {room: frozenset(slots) for room, slots in raw.items()}


_PARSERS: dict[str, Callable[[bytes], Any]] = {
    COURSES: parse_courses,
    ENROLLMENTS: parse_enrollments,
    ROOMS: parse_rooms,
    ROOM_BLOCKOUTS: parse_blockouts,
}


def parse_dataset_files(contents: Mapping[str, bytes]) -> DatasetFiles:
    """Parse downloaded files keyed by file type.

    A required file that is missing or fails to parse is marked unreadable (and
    logged); other files are still parsed.
    """
    parsed: dict[str, Any] = {}
    unreadable: set[str] = set()
    for file_type, parser in _PARSERS.items():
        content = contents.get(file_type)
        if content is None:
            if file_type != ROOM_BLOCKOUTS:
                unreadable.add(file_type)
            continue
        try:
            parsed[file_type] = parser(content)
        except Exception as exc:
            logger.warning(
                "Could not parse uploaded %s file for validation: %s: %s",
                file_type,
                type(exc).__name__,
                exc,
            )
            unreadable.add(file_type)

    return DatasetFiles(
        courses=parsed.get(COURSES),
        enrollments=parsed.get(ENROLLMENTS),
        rooms=parsed.get(ROOMS),
        blockouts=parsed.get(ROOM_BLOCKOUTS),
        blockouts_uploaded=ROOM_BLOCKOUTS in contents,
        unreadable=frozenset(unreadable),
    )
