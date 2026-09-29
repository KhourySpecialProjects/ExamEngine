import io
import math

import pandas as pd

from src.domain.exceptions import DataValidationError
from src.domain.models import Course, Enrollment, Room

from .schemas import validate_non_empty_string
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


class CommonExamAdapter:
    """Converts common exam CSV to a dict mapping exam group to its CRNs."""

    @staticmethod
    def read_csv(content: bytes) -> pd.DataFrame:
        """
        Parse common exam CSV bytes without type inference.

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

    @staticmethod
    def from_dataframe(df: pd.DataFrame) -> dict[str, list[str]]:
        """
        Convert common exam DataFrame to dict of group label -> list of CRNs.

        Fully blank rows and exact duplicate (group, CRN) rows are ignored. CRNs
        within a group keep their order of first appearance.

        Args:
            df: Common exam data from CSV (one row per group/CRN pair), ideally
                parsed with `read_csv` so labels and row numbers are exact

        Returns:
            Dict mapping exam group label to the CRNs that share one exam

        Raises:
            SchemaDetectionError: If CSV format is unknown
            DataValidationError: If the file has no groups, a row has a blank
                group or a blank/non-whole-number CRN, a CRN is in more than one
                group, a group has fewer than 2 distinct CRNs, or two group labels
                differ only in capitalization/spacing. The message lists every
                problem found.
        """
        schema, column_mapping = CSVSchemaDetector.detect_schema_version(
            df, "common_exams"
        )

        col_defs = {cd.canonical_name: cd for cd in schema}
        df_normalized = df.rename(columns=column_mapping)
        raw_crns = df_normalized["Course_Reference_Number"].copy()

        for canonical_name, col_def in col_defs.items():
            if canonical_name in df_normalized.columns and col_def.transformer:
                df_normalized[canonical_name] = df_normalized[canonical_name].apply(
                    col_def.transformer
                )

        problems: list[str] = []
        merges: dict[str, list[str]] = {}
        crn_groups: dict[str, list[str]] = {}

        # Row numbers match spreadsheet lines: header is line 1.
        for position, (group, crn, raw_crn) in enumerate(
            zip(
                df_normalized["Exam_Group"],
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
                missing.append("exam group")
            if not has_crn:
                missing.append("CRN")
            if missing:
                problems.append(f"row {row_number}: missing {' and '.join(missing)}")
                continue
            if _has_fraction(raw_crn):
                problems.append(
                    f"row {row_number}: CRN '{str(raw_crn).strip()}' is not a whole "
                    "number"
                )
                continue

            crns = merges.setdefault(group, [])
            if crn in crns:
                continue
            crns.append(crn)

            groups = crn_groups.setdefault(crn, [])
            if group not in groups:
                groups.append(group)

        labels_by_key: dict[str, list[str]] = {}
        for group in merges:
            key = " ".join(group.split()).casefold()
            labels_by_key.setdefault(key, []).append(group)
        for labels in labels_by_key.values():
            if len(labels) > 1:
                listed = ", ".join(f"'{g}'" for g in labels)
                problems.append(
                    f"exam groups {listed} differ only in capitalization or spacing"
                )

        for crn, groups in crn_groups.items():
            if len(groups) > 1:
                listed = ", ".join(f"'{g}'" for g in groups)
                problems.append(f"CRN {crn} is in multiple exam groups: {listed}")

        for group, crns in merges.items():
            if len(crns) < 2:
                problems.append(
                    f"exam group '{group}' needs at least 2 distinct CRNs "
                    f"(found {len(crns)})"
                )

        if not merges and not problems:
            problems.append("no exam groups found")

        if problems:
            raise DataValidationError("; ".join(problems))

        return merges


def _has_fraction(value: object) -> bool:
    """True if value is a number with a non-zero fractional part (e.g. 11316.9)."""
    try:
        number = float(str(value).strip())
    except ValueError:
        return False
    return math.isfinite(number) and not number.is_integer()


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

        # Apply transformers
        for canonical_name, col_def in col_defs.items():
            if canonical_name in df_normalized.columns and col_def.transformer:
                df_normalized[canonical_name] = df_normalized[canonical_name].apply(
                    col_def.transformer
                )

        # Remove rows with missing required fields
        df_clean = df_normalized.dropna(subset=["Location Name", "Capacity"])

        # Build Room objects
        rooms = []
        validation_errors = []

        for idx, row in df_clean.iterrows():
            try:
                room = Room(name=row["Location Name"], capacity=row["Capacity"])
                rooms.append(room)
            except ValueError as e:
                validation_errors.append(f"Row {idx}: {str(e)}")

        if validation_errors and len(rooms) == 0:
            # Only raise error if ALL rooms failed
            raise DataValidationError(
                "Room data validation failed:\n" + "\n".join(validation_errors[:10])
            )

        return rooms
