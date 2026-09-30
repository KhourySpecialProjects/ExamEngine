"""
Tests for read_upload_csv, the shared parser for uploaded dataset CSVs.

Tests cover:
- Student IDs keep their leading zeros (canonical and alias headers)
- Numeric columns are still inferred as numbers
- Zero-padded IDs flow unchanged through the scheduler and analyzer
"""

import pandas as pd
import pytest

from src.domain.adapters import read_upload_csv
from src.domain.factories.dataset_factory import DatasetFactory
from src.domain.services.schedule_analyzer import ScheduleAnalyzer
from src.domain.services.scheduler import Scheduler


class TestReadUploadCsv:
    """Parsing behavior per file type."""

    @pytest.mark.parametrize(
        "header",
        ["Student_PIDM,CRN", "student_id,crn", "Student ID,Course Registration Number"],
    )
    def test_student_ids_keep_leading_zeros(self, header):
        content = f"{header}\n001234567,11310\n000000042,11311\n".encode()

        df = read_upload_csv(content, "enrollments")

        assert df.iloc[:, 0].tolist() == ["001234567", "000000042"]
        assert df.iloc[:, 1].tolist() == ["11310", "11311"]

    def test_numeric_columns_still_inferred(self):
        courses = read_upload_csv(
            b"CRN,CourseID,Enrollment\n11310,CS 2500,30\n11311,CS 2510,25\n",
            "courses",
        )
        rooms = read_upload_csv(b"Room,Capacity\nHall A,70\n", "rooms")

        assert pd.api.types.is_integer_dtype(courses["Enrollment"])
        assert courses["Enrollment"].sum() == 55
        assert pd.api.types.is_integer_dtype(rooms["Capacity"])

    def test_common_exams_read_fully_as_text(self):
        df = read_upload_csv(b"ExamGroup,CRN\n01,11310\n01,11311\n", "common_exams")

        assert df["ExamGroup"].tolist() == ["01", "01"]
        assert df["CRN"].tolist() == ["11310", "11311"]


def test_zero_padded_student_id_reported_in_conflicts():
    """
    One student in six courses with a single exam day (five blocks) forces a
    double-book; the analyzer must report the student by the uploaded ID.
    """
    crns = [str(11310 + i) for i in range(6)]
    courses_csv = "CRN,CourseID,Enrollment\n" + "".join(
        f"{crn},CS {crn},1\n" for crn in crns
    )
    enrollments_csv = "Student_PIDM,CRN\n" + "".join(
        f"001234567,{crn}\n" for crn in crns
    )
    dataset = DatasetFactory.from_dataframes_to_scheduling_dataset(
        courses_df=read_upload_csv(courses_csv.encode(), "courses"),
        enrollment_df=read_upload_csv(enrollments_csv.encode(), "enrollments"),
        rooms_df=read_upload_csv(b"Room,Capacity\nHall A,10\n", "rooms"),
    )
    assert set(dataset.students) == {"001234567"}

    result = Scheduler(dataset=dataset, max_days=1).schedule()
    analysis = ScheduleAnalyzer(dataset).analyze(result)

    double_books = analysis.hard_conflicts.student_double_book
    assert double_books
    assert {c["entity_id"] for c in double_books} == {"001234567"}
    back_to_back = analysis.soft_conflicts.back_to_back_students
    assert [c["student_id"] for c in back_to_back] == ["001234567"]
