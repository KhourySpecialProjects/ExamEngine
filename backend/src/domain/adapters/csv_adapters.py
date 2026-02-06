import pandas as pd

from src.domain.exceptions import DataValidationError
from src.domain.models import Course, Enrollment, Room

from .schemas_detector import CSVSchemaDetector


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
                if examination_term is None:
                    validation_errors.append(f"Row {idx}: Missing examination term")
                    continue
                if department is None:
                    validation_errors.append(f"Row {idx}: Missing department")
                    continue

                instructor_names = set()
                if instructor_name:
                    instructor_names.add(instructor_name)

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
        df_clean = df_normalized.dropna(subset=["Student_PIDM", "Course_Reference_Number"])

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
