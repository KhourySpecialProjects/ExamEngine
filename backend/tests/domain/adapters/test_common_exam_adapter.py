"""
Tests for the CommonExamAdapter and common_exams schema.

Tests cover:
- Schema detection for canonical and alias headers
- Grouping output and CRN normalization
- Silent deduplication of exact duplicate rows
- Validation errors: blank cells, CRN in two groups, singleton groups
"""

import pandas as pd
import pytest

from src.domain.adapters import CommonExamAdapter
from src.domain.exceptions import DataValidationError, SchemaDetectionError


class TestCommonExamSchemaDetection:
    """Tests for header detection of the common_exams file type."""

    def test_canonical_headers(self):
        df = pd.DataFrame(
            {
                "Exam_Group": ["A", "A"],
                "Course_Reference_Number": ["100", "101"],
            }
        )
        assert CommonExamAdapter.from_dataframe(df) == {"A": ["100", "101"]}

    @pytest.mark.parametrize(
        ("group_header", "crn_header"),
        [
            ("ExamGroup", "CRN"),
            ("Exam Group", "crn"),
            ("Common Exam", "Course Registration Number"),
            ("merge_group", "CRN"),
            ("merge_group_id", "CRN"),
            ("group", "CRN"),
            ("group_id", "CRN"),
        ],
    )
    def test_alias_headers(self, group_header, crn_header):
        df = pd.DataFrame({group_header: ["A", "A"], crn_header: ["100", "101"]})
        assert CommonExamAdapter.from_dataframe(df) == {"A": ["100", "101"]}

    def test_missing_crn_column_raises(self):
        df = pd.DataFrame({"ExamGroup": ["A", "A"], "Course": ["CS1", "CS2"]})
        with pytest.raises(SchemaDetectionError):
            CommonExamAdapter.from_dataframe(df)


class TestCommonExamAdapter:
    """Tests for CommonExamAdapter.from_dataframe()."""

    def test_groups_crns_in_first_appearance_order(self):
        df = pd.DataFrame(
            {
                "ExamGroup": [
                    "CS Foundations Final",
                    "Calculus Common Exam",
                    "CS Foundations Final",
                    "Calculus Common Exam",
                    "CS Foundations Final",
                ],
                "CRN": ["11311", "20002", "11310", "20001", "11312"],
            }
        )
        assert CommonExamAdapter.from_dataframe(df) == {
            "CS Foundations Final": ["11311", "11310", "11312"],
            "Calculus Common Exam": ["20002", "20001"],
        }

    def test_float_crns_and_padded_labels_are_normalized(self):
        df = pd.DataFrame(
            {
                "ExamGroup": ["  Final A ", "Final A"],
                "CRN": [11310.0, 11311.0],
            }
        )
        assert CommonExamAdapter.from_dataframe(df) == {"Final A": ["11310", "11311"]}

    def test_exact_duplicate_rows_are_deduplicated(self):
        df = pd.DataFrame(
            {
                "ExamGroup": ["A", "A", "A"],
                "CRN": ["100", "101", "100"],
            }
        )
        assert CommonExamAdapter.from_dataframe(df) == {"A": ["100", "101"]}

    def test_duplicate_does_not_rescue_singleton_group(self):
        df = pd.DataFrame(
            {
                "ExamGroup": ["A", "A", "B", "B"],
                "CRN": ["100", "100", "200", "201"],
            }
        )
        with pytest.raises(DataValidationError, match="'A'"):
            CommonExamAdapter.from_dataframe(df)

    def test_blank_group_reports_row_number(self):
        df = pd.DataFrame(
            {
                "ExamGroup": ["A", "A", "  "],
                "CRN": ["100", "101", "102"],
            }
        )
        with pytest.raises(DataValidationError) as exc_info:
            CommonExamAdapter.from_dataframe(df)
        assert str(exc_info.value) == "row 4: missing exam group"

    def test_blank_crn_reports_row_number(self):
        df = pd.DataFrame(
            {
                "ExamGroup": ["A", "A", "A"],
                "CRN": ["100", None, "101"],
            }
        )
        with pytest.raises(DataValidationError) as exc_info:
            CommonExamAdapter.from_dataframe(df)
        assert str(exc_info.value) == "row 3: missing CRN"

    def test_crn_in_two_groups_names_crn_and_groups(self):
        df = pd.DataFrame(
            {
                "ExamGroup": ["A", "A", "B", "B"],
                "CRN": ["100", "101", "101", "102"],
            }
        )
        with pytest.raises(DataValidationError) as exc_info:
            CommonExamAdapter.from_dataframe(df)
        message = str(exc_info.value)
        assert "101" in message
        assert "'A'" in message
        assert "'B'" in message

    def test_singleton_group_raises(self):
        df = pd.DataFrame(
            {
                "ExamGroup": ["A", "A", "Solo"],
                "CRN": ["100", "101", "200"],
            }
        )
        with pytest.raises(DataValidationError) as exc_info:
            CommonExamAdapter.from_dataframe(df)
        assert "'Solo'" in str(exc_info.value)
        assert "'A'" not in str(exc_info.value)

    def test_all_problems_reported_together(self):
        df = pd.DataFrame(
            {
                "ExamGroup": ["A", "A", None, "B", "B", "Solo"],
                "CRN": ["100", "101", "102", "101", "103", "200"],
            }
        )
        with pytest.raises(DataValidationError) as exc_info:
            CommonExamAdapter.from_dataframe(df)
        problems = str(exc_info.value).split("; ")
        assert len(problems) == 3
        assert problems[0] == "row 4: missing exam group"
        assert "CRN 101" in problems[1]
        assert "'Solo'" in problems[2]

    def test_fractional_crn_rejected_not_truncated(self):
        df = pd.DataFrame({"ExamGroup": ["A", "A"], "CRN": ["11315", "11316.9"]})
        with pytest.raises(DataValidationError) as exc_info:
            CommonExamAdapter.from_dataframe(df)
        assert "row 3: CRN '11316.9' is not a whole number" in str(exc_info.value)

    def test_labels_differing_only_in_case_or_spacing_rejected(self):
        df = pd.DataFrame(
            {
                "ExamGroup": ["MATH Final", "MATH Final", "math  final", "math  final"],
                "CRN": ["100", "101", "102", "103"],
            }
        )
        with pytest.raises(DataValidationError) as exc_info:
            CommonExamAdapter.from_dataframe(df)
        message = str(exc_info.value)
        assert "'MATH Final'" in message and "'math  final'" in message
        assert "differ only in capitalization or spacing" in message

    def test_file_with_no_groups_rejected(self):
        df = pd.DataFrame({"ExamGroup": [], "CRN": []})
        with pytest.raises(DataValidationError, match="no exam groups found"):
            CommonExamAdapter.from_dataframe(df)


class TestCommonExamReadCsv:
    """Tests for parsing raw CSV bytes with CommonExamAdapter.read_csv()."""

    def test_numeric_looking_labels_stay_distinct(self):
        df = CommonExamAdapter.read_csv(
            b"ExamGroup,CRN\n01,100\n01,101\n1,102\n1,103\n"
        )
        assert CommonExamAdapter.from_dataframe(df) == {
            "01": ["100", "101"],
            "1": ["102", "103"],
        }

    def test_blank_lines_ignored_and_row_numbers_match_file_lines(self):
        df = CommonExamAdapter.read_csv(b"ExamGroup,CRN\nA,100\n\nA,\nA,101\n\n")
        with pytest.raises(DataValidationError) as exc_info:
            CommonExamAdapter.from_dataframe(df)
        assert str(exc_info.value) == "row 4: missing CRN"

    def test_excel_bom_and_crlf(self):
        df = CommonExamAdapter.read_csv(
            b"\xef\xbb\xbfExamGroup,CRN\r\nA,100\r\nA,101\r\n"
        )
        assert CommonExamAdapter.from_dataframe(df) == {"A": ["100", "101"]}
