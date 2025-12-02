import pandas as pd

from src.domain.exceptions import SchemaDetectionError

from .schemas import ColumnDefinition, get_schema


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
