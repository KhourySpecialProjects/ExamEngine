import io
import math

import pandas as pd

from src.domain.exceptions import DataValidationError
from src.domain.models import Course, Enrollment, Room
from src.domain.services.room_fit import large_only_problem

from .schemas import ColumnType, get_schema, validate_non_empty_string
from .schemas_detector import CSVSchemaDetector


class RoomBlockoutAdapter:
    """Converts room blockout CSV to a dict mapping room name to blocked (day, block) pairs."""

    @staticmethod
    def from_dataframe(df: pd.DataFrame) -> dict[str, set[tuple[int, int]]]:
        """
        Convert blockout DataFrame to dict of room_name -> set of (day_idx, block_idx).

        Args:
            df: Blockout data from CSV

        Returns:
            Dict mapping room name to a set of (day_idx, block_idx) tuples
        """
        schema, column_mapping = CSVSchemaDetector.detect_schema_version(
            df, "room_blockouts"
        )

        col_defs = {cd.canonical_name: cd for cd in schema}
        df_normalized = df.rename(columns=column_mapping)

        for canonical_name, col_def in col_defs.items():
            if canonical_name in df_normalized.columns and col_def.transformer:
                df_normalized[canonical_name] = df_normalized[canonical_name].apply(
                    col_def.transformer
                )

        df_clean = df_normalized.dropna(subset=["Room", "Day", "Block"])

        blockouts: dict[str, set[tuple[int, int]]] = {}

        for _, row in df_clean.iterrows():
            try:
                room = row["Room"]
                day = int(row["Day"])
                block = int(row["Block"])

                # Validate each field using schema validators (consistent with other adapters)
                valid = True
                for canonical_name, value in [
                    ("Room", room),
                    ("Day", day),
                    ("Block", block),
                ]:
                    col_def = col_defs.get(canonical_name)
                    if col_def and col_def.validator and not col_def.validator(value):
                        valid = False
                        break
                if not valid:
                    continue

                if room not in blockouts:
                    blockouts[room] = set()
                blockouts[room].add((day, block))
            except (ValueError, TypeError):
                continue

        return blockouts


def _read_text_csv(content: bytes) -> pd.DataFrame:
    """
    Parse group CSV bytes without type inference.

    Every cell stays a string, so group labels like "01" and "1" remain
    distinct and CRNs keep their original text. Blank lines are kept so
    reported row numbers match the file's line numbers.
    """
    return pd.read_csv(
        io.BytesIO(content),
        dtype=str,
        keep_default_na=False,
        skip_blank_lines=False,
    )


def _group_crns(
    df: pd.DataFrame, file_type: str, group_column: str, noun: str
) -> dict[str, list[str]]:
    """
    Convert a long-format (group, CRN) DataFrame to group label -> CRNs.

    Fully blank rows and exact duplicate (group, CRN) rows are ignored. CRNs
    within a group keep their order of first appearance.

    Args:
        df: Group data from CSV, ideally parsed with `_read_text_csv`
        file_type: Schema registry key used for header detection
        group_column: Canonical name of the group label column
        noun: How groups are named in error messages (e.g. "exam group")

    Raises:
        SchemaDetectionError: If CSV format is unknown
        DataValidationError: If the file has no groups, a row has a blank
            group or a blank/non-whole-number CRN, a CRN is in more than one
            group, a group has fewer than 2 distinct CRNs, or two group labels
            differ only in capitalization/spacing. The message lists every
            problem found.
    """
    schema, column_mapping = CSVSchemaDetector.detect_schema_version(df, file_type)

    col_defs = {cd.canonical_name: cd for cd in schema}
    df_normalized = df.rename(columns=column_mapping)
    raw_crns = df_normalized["Course_Reference_Number"].copy()

    for canonical_name, col_def in col_defs.items():
        if canonical_name in df_normalized.columns and col_def.transformer:
            df_normalized[canonical_name] = df_normalized[canonical_name].apply(
                col_def.transformer
            )

    problems: list[str] = []
    groups: dict[str, list[str]] = {}
    crn_groups: dict[str, list[str]] = {}

    # Row numbers match spreadsheet lines: header is line 1.
    for position, (group, crn, raw_crn) in enumerate(
        zip(
            df_normalized[group_column],
            df_normalized["Course_Reference_Number"],
            raw_crns,
            strict=True,
        )
    ):
        row_number = position + 2
        has_group = validate_non_empty_string(group)
        has_crn = validate_non_empty_string(crn)
        if not has_group and not has_crn:
            continue  # blank line
        missing = []
        if not has_group:
            missing.append(noun)
        if not has_crn:
            missing.append("CRN")
        if missing:
            problems.append(f"row {row_number}: missing {' and '.join(missing)}")
            continue
        if _has_fraction(raw_crn):
            problems.append(
                f"row {row_number}: CRN '{str(raw_crn).strip()}' is not a whole number"
            )
            continue

        crns = groups.setdefault(group, [])
        if crn in crns:
            continue
        crns.append(crn)

        labels = crn_groups.setdefault(crn, [])
        if group not in labels:
            labels.append(group)

    labels_by_key: dict[str, list[str]] = {}
    for group in groups:
        key = " ".join(group.split()).casefold()
        labels_by_key.setdefault(key, []).append(group)
    for labels in labels_by_key.values():
        if len(labels) > 1:
            listed = ", ".join(f"'{g}'" for g in labels)
            problems.append(
                f"{noun}s {listed} differ only in capitalization or spacing"
            )

    for crn, labels in crn_groups.items():
        if len(labels) > 1:
            listed = ", ".join(f"'{g}'" for g in labels)
            problems.append(f"CRN {crn} is in multiple {noun}s: {listed}")

    for group, crns in groups.items():
        if len(crns) < 2:
            problems.append(
                f"{noun} '{group}' needs at least 2 distinct CRNs (found {len(crns)})"
            )

    if not groups and not problems:
        problems.append(f"no {noun}s found")

    if problems:
        raise DataValidationError("; ".join(problems))

    return groups


class CombinedExamAdapter:
    """Converts combined exam CSV to a dict mapping exam group to its CRNs."""

    @staticmethod
    def read_csv(content: bytes) -> pd.DataFrame:
        """Parse combined exam CSV bytes as text (see `_read_text_csv`)."""
        return _read_text_csv(content)

    @staticmethod
    def from_dataframe(df: pd.DataFrame) -> dict[str, list[str]]:
        """
        Convert combined exam DataFrame to dict of group label -> list of CRNs.

        Each group's CRNs sit one exam: same time block, same room.

        Raises:
            SchemaDetectionError: If CSV format is unknown
            DataValidationError: If any row or group is invalid (see
                `_group_crns`)
        """
        return _group_crns(df, "combined_exams", "Exam_Group", "exam group")


class CommonExamAdapter:
    """Converts common exam CSV to a dict mapping common group to its CRNs."""

    @staticmethod
    def read_csv(content: bytes) -> pd.DataFrame:
        """Parse common exam CSV bytes as text (see `_read_text_csv`)."""
        return _read_text_csv(content)

    @staticmethod
    def from_dataframe(df: pd.DataFrame) -> dict[str, list[str]]:
        """
        Convert common exam DataFrame to dict of group label -> list of CRNs.

        Each group's CRNs sit in the same time block but in different rooms
        (combined groups among them still share one room). CRNs are kept as
        listed; combined-group closure is applied by callers.

        Raises:
            SchemaDetectionError: If CSV format is unknown
            DataValidationError: If any row or group is invalid (see
                `_group_crns`)
        """
        return _group_crns(df, "common_exams", "Common_Group", "common group")


def _has_fraction(value: object) -> bool:
    """True if value is a number with a non-zero fractional part (e.g. 11316.9)."""
    try:
        number = float(str(value).strip())
    except ValueError:
        return False
    return math.isfinite(number) and not number.is_integer()


def read_upload_csv(content: bytes, file_type: str) -> pd.DataFrame:
    """
    Parse uploaded CSV bytes, keeping text columns as text.

    Columns the schema declares as strings (student IDs, CRNs, names, ...) are
    read verbatim so identifiers like "001234567" keep their leading zeros.
    Other columns (enrollment, capacity, day/block) are still type-inferred.
    Combined and common exam files are read fully as text.

    Yes/no columns (rooms.csv LargeOnly) are read as raw text, so only an empty
    cell is blank and tokens such as "NA" or "null" reach the parser and are
    rejected. Files with one keep the file's line numbers: row index + 2 is
    the line (header is line 1), with fully blank lines dropped.

    Args:
        content: Raw CSV bytes
        file_type: One of the keys in SCHEMA_REGISTRY (e.g. "enrollments")

    Returns:
        Parsed DataFrame with the file's original column names
    """
    if file_type in ("combined_exams", "common_exams"):
        return _read_text_csv(content)

    schema_class = get_schema(file_type)
    if schema_class is None:
        return pd.read_csv(io.BytesIO(content))

    col_defs = [
        col_def for version in schema_class.get_all_versions() for col_def in version
    ]
    header = pd.read_csv(io.BytesIO(content), nrows=0).columns

    def columns_of(data_type: ColumnType) -> list[str]:
        return [
            column
            for column in header
            if any(
                col_def.data_type is data_type and col_def.matches(str(column))
                for col_def in col_defs
            )
        ]

    text_columns = dict.fromkeys(columns_of(ColumnType.STRING), str)
    yes_no_columns = dict.fromkeys(columns_of(ColumnType.BOOLEAN), str)
    if not yes_no_columns:
        return pd.read_csv(io.BytesIO(content), dtype=text_columns or None)

    df = pd.read_csv(
        io.BytesIO(content),
        dtype=text_columns or None,
        converters=yes_no_columns,
        skip_blank_lines=False,
    )
    blank = df.apply(lambda column: column.isna() | column.eq("")).all(axis=1)
    return df[~blank]


class CourseAdapter:
    """Converts course CSV data to Course domain objects."""

    @staticmethod
    def from_dataframe(df: pd.DataFrame) -> dict[str, Course]:
        """
        Convert course DataFrame to dictionary of Course objects.

        Args:
            df: Course data from CSV

        Returns:
            Dictionary mapping CRN to Course objects

        Raises:
            SchemaDetectionError: If CSV format is unknown
            DataValidationError: If data fails validation
        """
        # Detect schema and get column mapping
        schema, column_mapping = CSVSchemaDetector.detect_schema_version(df, "courses")

        # Create lookup for column definitions by canonical name
        col_defs = {cd.canonical_name: cd for cd in schema}

        # Normalize DataFrame to canonical column names
        df_normalized = df.rename(columns=column_mapping)

        # Apply transformers to each column
        for canonical_name, col_def in col_defs.items():
            if canonical_name in df_normalized.columns and col_def.transformer:
                df_normalized[canonical_name] = df_normalized[canonical_name].apply(
                    col_def.transformer
                )

        # Build Course objects
        courses = {}
        validation_errors = []

        for idx, row in df_normalized.iterrows():
            try:
                # Extract required fields
                crn = row.get("Course_Reference_Number")
                course_code = row.get("Course_Identification")
                enrollment_count = row.get("Total_Enrollment")
                instructor_name = row.get("Primary_Instructor_PIDM")
                department = row.get("Course_Department_Code")
                examination_term = row.get("Academic_Period_NUFreeze")

                # Validate required fields are present
                if crn is None:
                    validation_errors.append(f"Row {idx}: Missing CRN")
                    continue
                if course_code is None:
                    validation_errors.append(f"Row {idx}: Missing course code")
                    continue
                if enrollment_count is None:
                    validation_errors.append(f"Row {idx}: Missing enrollment count")
                    continue

                instructor_names = set()
                if instructor_name:
                    instructor_names.add(str(instructor_name))

                # Apply validators
                for canonical_name, col_def in col_defs.items():
                    if col_def.validator and canonical_name in row:
                        value = row[canonical_name]
                        if value is not None and not col_def.validator(value):
                            validation_errors.append(
                                f"Row {idx}: Invalid {canonical_name} value: {value}"
                            )
                            continue

                # Create Course object (will raise ValueError if invalid)
                course = Course(
                    crn=crn,
                    course_code=course_code,
                    enrollment_count=enrollment_count,
                    instructor_names=instructor_names,
                    department=department,
                    examination_term=examination_term,
                )

                courses[crn] = course

            except ValueError as e:
                validation_errors.append(f"Row {idx}: {str(e)}")

        if validation_errors:
            raise DataValidationError(
                "Course data validation failed:\n" + "\n".join(validation_errors[:10])
            )

        return courses


class EnrollmentAdapter:
    """Converts enrollment CSV data to Enrollment domain objects."""

    @staticmethod
    def from_dataframe(df: pd.DataFrame) -> list[Enrollment]:
        """
        Convert enrollment DataFrame to list of Enrollment objects.

        Args:
            df: Enrollment data from CSV

        Returns:
            List of Enrollment objects

        Raises:
            SchemaDetectionError: If CSV format is unknown
            DataValidationError: If data fails validation
        """
        # Detect schema and get column mapping
        schema, column_mapping = CSVSchemaDetector.detect_schema_version(
            df, "enrollments"
        )

        # Create lookup for column definitions
        col_defs = {cd.canonical_name: cd for cd in schema}

        # Normalize DataFrame
        df_normalized = df.rename(columns=column_mapping)

        # Apply transformers
        for canonical_name, col_def in col_defs.items():
            if canonical_name in df_normalized.columns and col_def.transformer:
                df_normalized[canonical_name] = df_normalized[canonical_name].apply(
                    col_def.transformer
                )

        # Remove rows with missing required fields
        df_clean = df_normalized.dropna(
            subset=["Student_PIDM", "Course_Reference_Number"]
        )

        # Build Enrollment objects
        enrollments = []

        for _, row in df_clean.iterrows():
            try:
                enrollment = Enrollment(
                    student_id=row["Student_PIDM"],
                    crn=row["Course_Reference_Number"],
                )
                enrollments.append(enrollment)
            except ValueError:
                # Skip invalid rows
                continue

        return enrollments


class RoomAdapter:
    """Converts room CSV data to Room domain objects."""

    @staticmethod
    def from_dataframe(df: pd.DataFrame) -> list[Room]:
        """
        Convert room DataFrame to list of Room objects.

        Args:
            df: Room data from CSV

        Returns:
            List of Room objects

        Raises:
            SchemaDetectionError: If CSV format is unknown
            DataValidationError: If data fails validation
        """
        # Detect schema and get column mapping
        schema, column_mapping = CSVSchemaDetector.detect_schema_version(df, "rooms")

        # Create lookup for column definitions
        col_defs = {cd.canonical_name: cd for cd in schema}

        # Normalize DataFrame
        df_normalized = df.rename(columns=column_mapping)
        has_large_only = "LargeOnly" in df_normalized.columns
        raw_large_only = df_normalized["LargeOnly"].copy() if has_large_only else None

        # Apply transformers
        for canonical_name, col_def in col_defs.items():
            if canonical_name in df_normalized.columns and col_def.transformer:
                df_normalized[canonical_name] = df_normalized[canonical_name].apply(
                    col_def.transformer
                )

        if raw_large_only is not None:
            # read_upload_csv indexes this file by line: index + 2 is the line
            # number (header is line 1).
            parsed = df_normalized["LargeOnly"]
            invalid = [
                f"row {index + 2} '{str(raw).strip()}'"
                for index, raw in raw_large_only.items()
                if parsed[index] is None
            ]
            if invalid:
                raise DataValidationError(
                    "LargeOnly must be y/yes/1/true or n/no/0/false (blank means "
                    f"no); invalid values: {', '.join(invalid)}"
                )

        # Remove rows with missing required fields
        df_clean = df_normalized.dropna(subset=["Location Name", "Capacity"])

        # Build Room objects
        rooms = []
        validation_errors = []

        for idx, row in df_clean.iterrows():
            try:
                room = Room(
                    name=row["Location Name"],
                    # Whole after parse_capacity, but float when the column
                    # had a blank capacity (NaN).
                    capacity=int(row["Capacity"]),
                    large_only=bool(row["LargeOnly"]) if has_large_only else False,
                )
                rooms.append(room)
            except ValueError as e:
                validation_errors.append(f"Row {idx}: {str(e)}")

        problem = large_only_problem({room.name: room for room in rooms}.values())
        if problem:
            raise DataValidationError(problem)

        if validation_errors and len(rooms) == 0:
            # Only raise error if ALL rooms failed
            raise DataValidationError(
                "Room data validation failed:\n" + "\n".join(validation_errors[:10])
            )

        return rooms
