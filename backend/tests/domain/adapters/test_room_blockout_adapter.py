"""
Tests for the RoomBlockoutAdapter and related schema/parser utilities.

Tests cover:
- CSV schema detection for room_blockouts
- Day parsing (integer index and day name)
- Block parsing (integer index and time string)
- Adapter output structure and deduplication
- Graceful handling of invalid / missing data
- Integration with DatasetFactory
"""

import pandas as pd
import pytest

from src.domain.adapters import RoomBlockoutAdapter
from src.domain.adapters.schemas import get_schema, parse_block, parse_day
from src.domain.exceptions import SchemaDetectionError
from src.domain.factories.dataset_factory import DatasetFactory


class TestParseDay:
    """Tests for the parse_day helper."""

    def test_integer_zero(self):
        assert parse_day(0) == 0

    def test_integer_six(self):
        assert parse_day(6) == 6

    def test_float_string(self):
        assert parse_day("2.0") == 2

    def test_day_name_monday(self):
        assert parse_day("Monday") == 0

    def test_day_name_sunday(self):
        assert parse_day("Sunday") == 6

    def test_day_name_case_insensitive(self):
        assert parse_day("FRIDAY") == 4
        assert parse_day("friday") == 4

    def test_out_of_range_returns_none(self):
        assert parse_day(7) is None
        assert parse_day(-1) is None

    def test_nan_returns_none(self):
        import numpy as np

        assert parse_day(float("nan")) is None

    def test_invalid_string_returns_none(self):
        assert parse_day("not-a-day") is None


class TestParseBlock:
    """Tests for the parse_block helper."""

    def test_integer_zero(self):
        assert parse_block(0) == 0

    def test_integer_four(self):
        assert parse_block(4) == 4

    def test_float_string(self):
        assert parse_block("3.0") == 3

    def test_time_string_first_block(self):
        assert parse_block("9AM-11AM") == 0

    def test_time_string_last_block(self):
        assert parse_block("7PM-9PM") == 4

    def test_time_string_case_insensitive(self):
        assert parse_block("9am-11am") == 0

    def test_time_string_with_spaces(self):
        assert parse_block("9AM - 11AM") == 0

    def test_out_of_range_returns_none(self):
        assert parse_block(5) is None
        assert parse_block(-1) is None

    def test_nan_returns_none(self):
        assert parse_block(float("nan")) is None

    def test_invalid_string_returns_none(self):
        assert parse_block("not-a-block") is None


class TestRoomBlockoutSchemaDetection:
    """Tests for schema detection of room_blockouts file type."""

    def test_schema_registered(self):
        schema_class = get_schema("room_blockouts")
        assert schema_class is not None

    def test_detects_canonical_columns(self):
        from src.domain.adapters.schemas_detector import CSVSchemaDetector

        df = pd.DataFrame({"Room": ["A"], "Day": [0], "Block": [1]})
        schema, mapping = CSVSchemaDetector.detect_schema_version(df, "room_blockouts")
        assert "Room" in mapping.values()
        assert "Day" in mapping.values()
        assert "Block" in mapping.values()

    def test_detects_alias_columns(self):
        from src.domain.adapters.schemas_detector import CSVSchemaDetector

        df = pd.DataFrame({"room_name": ["A"], "Weekday": [0], "block_index": [1]})
        schema, mapping = CSVSchemaDetector.detect_schema_version(df, "room_blockouts")
        assert "Room" in mapping.values()
        assert "Day" in mapping.values()
        assert "Block" in mapping.values()

    def test_raises_on_missing_required_column(self):
        from src.domain.adapters.schemas_detector import CSVSchemaDetector

        df = pd.DataFrame({"Room": ["A"], "Day": [0]})  # missing Block
        with pytest.raises(SchemaDetectionError):
            CSVSchemaDetector.detect_schema_version(df, "room_blockouts")


class TestRoomBlockoutAdapter:
    """Tests for RoomBlockoutAdapter.from_dataframe()."""

    def _make_df(self, data):
        return pd.DataFrame(data)

    def test_basic_integer_days_and_blocks(self):
        df = self._make_df(
            {"Room": ["Room A", "Room A"], "Day": [0, 1], "Block": [2, 3]}
        )
        result = RoomBlockoutAdapter.from_dataframe(df)

        assert "Room A" in result
        assert (0, 2) in result["Room A"]
        assert (1, 3) in result["Room A"]

    def test_accepts_day_names(self):
        df = self._make_df({"Room": ["Room B"], "Day": ["Tuesday"], "Block": [0]})
        result = RoomBlockoutAdapter.from_dataframe(df)

        assert "Room B" in result
        assert (1, 0) in result["Room B"]

    def test_accepts_block_time_strings(self):
        df = self._make_df({"Room": ["Room C"], "Day": [0], "Block": ["9AM-11AM"]})
        result = RoomBlockoutAdapter.from_dataframe(df)

        assert "Room C" in result
        assert (0, 0) in result["Room C"]

    def test_mixed_formats(self):
        df = self._make_df(
            {
                "Room": ["Lab 1", "Lab 1", "Lab 2"],
                "Day": [0, "Monday", 2],
                "Block": ["9AM-11AM", 1, 3],
            }
        )
        result = RoomBlockoutAdapter.from_dataframe(df)

        # Lab 1: day 0 block 0 and day 0 block 1 (Monday==0)
        assert (0, 0) in result["Lab 1"]
        assert (0, 1) in result["Lab 1"]
        # Lab 2: day 2 block 3
        assert (2, 3) in result["Lab 2"]

    def test_deduplicates_identical_entries(self):
        df = self._make_df(
            {
                "Room": ["Room A", "Room A", "Room A"],
                "Day": [0, 0, 0],
                "Block": [1, 1, 1],
            }
        )
        result = RoomBlockoutAdapter.from_dataframe(df)

        assert len(result["Room A"]) == 1

    def test_multiple_rooms(self):
        df = self._make_df(
            {
                "Room": ["Room A", "Room B", "Room C"],
                "Day": [0, 1, 2],
                "Block": [0, 0, 0],
            }
        )
        result = RoomBlockoutAdapter.from_dataframe(df)

        assert len(result) == 3
        assert "Room A" in result
        assert "Room B" in result
        assert "Room C" in result

    def test_skips_rows_with_missing_values(self):
        df = self._make_df(
            {
                "Room": ["Room A", None, "Room B"],
                "Day": [0, 1, 2],
                "Block": [0, 0, None],
            }
        )
        result = RoomBlockoutAdapter.from_dataframe(df)

        # Only Room A should be present; Room B row has None block
        assert "Room A" in result
        assert None not in result
        assert "Room B" not in result

    def test_skips_out_of_range_day(self):
        df = self._make_df({"Room": ["Room A"], "Day": [99], "Block": [0]})
        result = RoomBlockoutAdapter.from_dataframe(df)

        assert "Room A" not in result

    def test_skips_out_of_range_block(self):
        df = self._make_df({"Room": ["Room A"], "Day": [0], "Block": [99]})
        result = RoomBlockoutAdapter.from_dataframe(df)

        assert "Room A" not in result

    def test_empty_dataframe_returns_empty_dict(self):
        df = self._make_df({"Room": [], "Day": [], "Block": []})
        result = RoomBlockoutAdapter.from_dataframe(df)

        assert result == {}

    def test_result_values_are_sets_of_tuples(self):
        df = self._make_df({"Room": ["Room A"], "Day": [0], "Block": [1]})
        result = RoomBlockoutAdapter.from_dataframe(df)

        assert isinstance(result["Room A"], set)
        entry = list(result["Room A"])[0]
        assert isinstance(entry, tuple)
        assert len(entry) == 2


class TestDatasetFactoryWithBlockouts:
    """Tests for DatasetFactory accepting an optional blockouts DataFrame."""

    @pytest.fixture
    def base_dfs(self):
        courses = pd.DataFrame(
            {
                "CRN": ["C1", "C2"],
                "CourseID": ["CS 101", "CS 102"],
                "num_students": [10, 5],
                "Instructor Name": ["Dr. A", "Dr. B"],
                "examination_term": ["202510", "202510"],
                "department": ["CS", "CS"],
            }
        )
        enrollments = pd.DataFrame(
            {
                "Student_PIDM": ["S1", "S2"],
                "CRN": ["C1", "C2"],
            }
        )
        rooms = pd.DataFrame(
            {
                "room_name": ["Room A", "Room B"],
                "capacity": [20, 10],
            }
        )
        return courses, enrollments, rooms

    def test_without_blockouts_field_is_empty(self, base_dfs):
        courses, enrollments, rooms = base_dfs
        dataset = DatasetFactory.from_dataframes_to_scheduling_dataset(
            courses, enrollments, rooms
        )
        assert dataset.room_blockouts == {}

    def test_with_blockouts_df(self, base_dfs):
        courses, enrollments, rooms = base_dfs
        blockouts_df = pd.DataFrame(
            {
                "Room": ["Room A"],
                "Day": [0],
                "Block": [2],
            }
        )
        dataset = DatasetFactory.from_dataframes_to_scheduling_dataset(
            courses, enrollments, rooms, blockouts_df=blockouts_df
        )
        assert "Room A" in dataset.room_blockouts
        assert (0, 2) in dataset.room_blockouts["Room A"]

    def test_blockouts_are_frozensets(self, base_dfs):
        courses, enrollments, rooms = base_dfs
        blockouts_df = pd.DataFrame(
            {
                "Room": ["Room A", "Room A"],
                "Day": [0, 1],
                "Block": [0, 0],
            }
        )
        dataset = DatasetFactory.from_dataframes_to_scheduling_dataset(
            courses, enrollments, rooms, blockouts_df=blockouts_df
        )
        assert isinstance(dataset.room_blockouts["Room A"], frozenset)
