from collections import defaultdict
from typing import Any

import pandas as pd

from .models import Course, Dataset, Enrollment, Room, Student
from .schemas import ColumnDefinition, get_schema


class SchemaDetectionError(Exception):
    """Raised when CSV doesn't match any known schema."""

    pass


class DataValidationError(Exception):
    """Raised when data fails validation rules."""

    pass


class CSVSchemaDetector:
    """
    Detects which schema version a CSV file matches.

    This allows the system to automatically handle different CSV formats
    without requiring users to specify which version they're uploading.
    """

    @staticmethod
    def detect_schema_version(
        df: pd.DataFrame, file_type: str
    ) -> tuple[list[ColumnDefinition], dict[str, str]]:
        """
        Detect which schema version matches the DataFrame columns.

        Args:
            df: DataFrame loaded from CSV
            file_type: One of "courses", "enrollments", "rooms"

        Returns:
            Tuple of (matched_schema, column_mapping)
            - matched_schema: List of ColumnDefinition objects
            - column_mapping: Dict mapping CSV columns to canonical names

        Raises:
            SchemaDetectionError: If no schema matches
        """
        schema_class = get_schema(file_type)
        if not schema_class:
            raise SchemaDetectionError(f"Unknown file type: {file_type}")

        csv_columns = set(df.columns)

        # Try each schema version
        for schema_version in schema_class.get_all_versions():
            mapping = CSVSchemaDetector._try_match_schema(csv_columns, schema_version)

            if mapping is not None:
                return schema_version, mapping

        # No schema matched
        raise SchemaDetectionError(
            f"CSV columns {csv_columns} don't match any known schema for {file_type}"
        )

    @staticmethod
    def _try_match_schema(
        csv_columns: set[str], schema: list[ColumnDefinition]
    ) -> dict[str, str] | None:
        """
        Try to match CSV columns to a schema version.

        Returns:
            Dict mapping CSV column names to canonical names, or None if no match
        """
        mapping = {}

        for col_def in schema:
            # Find matching CSV column
            matched_csv_col = None
            for csv_col in csv_columns:
                if col_def.matches(csv_col):
                    matched_csv_col = csv_col
                    break

            # If required column not found, this schema doesn't match
            if col_def.required and matched_csv_col is None:
                return None

            # Add to mapping if found
            if matched_csv_col:
                mapping[matched_csv_col] = col_def.canonical_name

        return mapping


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
                crn = row.get("crn")
                course_code = row.get("course_code")
                enrollment_count = row.get("enrollment_count")

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
                    instructor_names=set(),  # Will be populated from enrollment data
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
        df_clean = df_normalized.dropna(subset=["student_id", "crn"])

        # Build Enrollment objects
        enrollments = []

        for _, row in df_clean.iterrows():
            try:
                enrollment = Enrollment(
                    student_id=row["student_id"],
                    crn=row["crn"],
                    instructor_name=row["instructor_name"],
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
        df_clean = df_normalized.dropna(subset=["room_name", "capacity"])

        # Build Room objects
        rooms = []
        validation_errors = []

        for idx, row in df_clean.iterrows():
            try:
                room = Room(name=row["room_name"], capacity=row["capacity"])
                rooms.append(room)
            except ValueError as e:
                validation_errors.append(f"Row {idx}: {str(e)}")

        if validation_errors and len(rooms) == 0:
            # Only raise error if ALL rooms failed
            raise DataValidationError(
                "Room data validation failed:\n" + "\n".join(validation_errors[:10])
            )

        return rooms


class DatasetBuilder:
    """
    Builds complete Dataset objects from raw CSV data.

    This orchestrates the conversion process and enriches domain objects
    with relationships (e.g., adding instructor names to courses).
    """

    @staticmethod
    def from_dataframes(
        dataset_id: Any,
        dataset_name: str,
        course_df: pd.DataFrame,
        enrollment_df: pd.DataFrame,
        room_df: pd.DataFrame,
    ) -> Dataset:
        """
        Build a complete Dataset from three CSV DataFrames.

        Args:
            dataset_id: UUID for the dataset
            dataset_name: Human-readable name
            course_df: Course CSV data
            enrollment_df: Enrollment CSV data
            room_df: Room CSV data

        Returns:
            Complete Dataset object with all relationships populated
        """
        # Convert each CSV to domain objects
        courses = CourseAdapter.from_dataframe(course_df)
        enrollments = EnrollmentAdapter.from_dataframe(enrollment_df)
        rooms = RoomAdapter.from_dataframe(room_df)

        # Build student objects from enrollments
        student_enrollments = defaultdict(set)
        course_instructors = defaultdict(set)

        for enrollment in enrollments:
            student_enrollments[enrollment.student_id].add(enrollment.crn)
            if enrollment.instructor_name:
                course_instructors[enrollment.crn].add(enrollment.instructor_name)

        students = {
            student_id: Student(student_id=student_id, enrolled_crns=frozenset(crns))
            for student_id, crns in student_enrollments.items()
        }

        # Enrich courses with instructor information
        enriched_courses = {}
        for crn, course in courses.items():
            enriched_courses[crn] = Course(
                crn=course.crn,
                course_code=course.course_code,
                enrollment_count=course.enrollment_count,
                instructor_names=course_instructors.get(crn, set()),
            )

        # Build final dataset
        return Dataset(
            dataset_id=dataset_id,
            name=dataset_name,
            courses=enriched_courses,
            students=students,
            rooms=rooms,
        )
