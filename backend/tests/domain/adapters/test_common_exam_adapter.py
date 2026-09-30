"""
Tests for the CommonExamAdapter and common_exams schema.

Row-level parsing is shared with the combined exam adapter (see
test_combined_exam_adapter.py); these tests cover what differs: headers and
the "common group" wording of errors.
"""

import pandas as pd
import pytest

from src.domain.adapters import CommonExamAdapter
from src.domain.exceptions import DataValidationError, SchemaDetectionError


class TestCommonExamSchemaDetection:
    """Tests for header detection of the common_exams file type."""

    @pytest.mark.parametrize(
        ("group_header", "crn_header"),
        [
            ("Common_Group", "Course_Reference_Number"),
            ("CommonGroup", "CRN"),
            ("Common Group", "crn"),
            ("common_group", "Course Registration Number"),
        ],
    )
    def test_accepted_headers(self, group_header, crn_header):
        df = pd.DataFrame({group_header: ["A", "A"], crn_header: ["100", "101"]})
        assert CommonExamAdapter.from_dataframe(df) == {"A": ["100", "101"]}

    @pytest.mark.parametrize(
        "group_header", ["ExamGroup", "Exam Group", "Common Exam", "Group"]
    )
    def test_combined_exam_headers_rejected(self, group_header):
        df = pd.DataFrame({group_header: ["A", "A"], "CRN": ["100", "101"]})
        with pytest.raises(SchemaDetectionError):
            CommonExamAdapter.from_dataframe(df)


class TestCommonExamAdapter:
    """Tests for CommonExamAdapter.from_dataframe()."""

    def test_groups_crns_in_first_appearance_order(self):
        df = CommonExamAdapter.read_csv(
            b"Common_Group,CRN\nBIOL Final,33333\n01,1\nBIOL Final,11111\n"
            b"\n01,2\nBIOL Final,33333\n"
        )
        assert CommonExamAdapter.from_dataframe(df) == {
            "BIOL Final": ["33333", "11111"],
            "01": ["1", "2"],
        }

    def test_problems_use_common_group_wording(self):
        df = CommonExamAdapter.read_csv(
            b"Common_Group,CRN\nA,100\nA,101\n,102\nB,101\nB,103\nSolo,200\n"
            b"a,300\na,301\n"
        )
        with pytest.raises(DataValidationError) as exc_info:
            CommonExamAdapter.from_dataframe(df)
        assert str(exc_info.value).split("; ") == [
            "row 4: missing common group",
            "common groups 'A', 'a' differ only in capitalization or spacing",
            "CRN 101 is in multiple common groups: 'A', 'B'",
            "common group 'Solo' needs at least 2 distinct CRNs (found 1)",
        ]

    def test_fractional_crn_rejected(self):
        df = CommonExamAdapter.read_csv(b"Common_Group,CRN\nA,100\nA,101.5\n")
        with pytest.raises(DataValidationError, match="row 3: CRN '101.5'"):
            CommonExamAdapter.from_dataframe(df)

    def test_file_with_no_groups_rejected(self):
        df = CommonExamAdapter.read_csv(b"Common_Group,CRN\n\n")
        with pytest.raises(DataValidationError, match="no common groups found"):
            CommonExamAdapter.from_dataframe(df)
