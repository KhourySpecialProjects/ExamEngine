from uuid import UUID

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.schemas.db import Courses

from .base import BaseRepo


class CourseRepo(BaseRepo[Courses]):
    """Repository for course operations."""

    def __init__(self, db: Session):
        super().__init__(Courses, db)

    def get_by_subject_code(
        self, course_subject_code: str, dataset_id: UUID
    ) -> Courses | None:
        """Find course by subject code within a dataset."""
        stmt = select(Courses).where(
            Courses.course_subject_code == course_subject_code,
            Courses.dataset_id == dataset_id,
        )
        return self.db.execute(stmt).scalars().first()

    def get_all_for_dataset(self, dataset_id: UUID) -> list[Courses]:
        """Get all courses for a dataset."""
        stmt = select(Courses).where(Courses.dataset_id == dataset_id)
        return list(self.db.execute(stmt).scalars().all())

    def bulk_create_from_dataframe(
        self, dataset_id: UUID, courses_df, enrollment_df=None
    ) -> dict[str, UUID]:
        """
        Create course records from census DataFrame.

        Returns mapping of course_ref -> course_id for assignment creation.
        """
        instructor_map = _build_instructor_map(enrollment_df)

        course_objs = []
        for _, row in courses_df.iterrows():
            crn = _clean_crn(row.get("CRN"))

            course = Courses(
                course_subject_code=str(row.get("CourseID", "")),
                crn=crn,
                enrollment_count=int(row.get("num_students", 0)),
                instructor_name=instructor_map.get(crn),
                dataset_id=dataset_id,
            )
            course_objs.append(course)

        self.db.bulk_save_objects(course_objs, return_defaults=True)
        self.db.commit()

        # Build mapping: course_ref -> course_id
        mapping = {}
        for obj in course_objs:
            mapping[obj.course_subject_code] = obj.course_id

        return mapping


# Temporary solution until we change the csv
def _clean_crn(value) -> str | None:
    """
    Normalize CRN values to consistent string format.

    Handles various input formats:
    - Float: 11310.0 -> "11310"
    - String: "11310" -> "11310"
    - NaN/None: -> None
    """
    try:
        if pd.isna(value):
            return None
        return str(int(float(value))).strip()
    except (ValueError, TypeError):
        return str(value).strip() if value else None


def _build_instructor_map(enrollment_df: pd.DataFrame) -> dict[str, str]:
    """
    Build mapping of CRN -> instructor names from enrollment data.

    Returns:
        Dictionary mapping cleaned CRNs to semicolon-separated instructor names
    """
    if enrollment_df is None or enrollment_df.empty:
        return {}

    enroll = enrollment_df.copy()
    if "Instructor Name" in enroll.columns:
        enroll = enroll.rename(columns={"Instructor Name": "instructor_name"})

    if "instructor_name" not in enroll.columns or "CRN" not in enroll.columns:
        return {}

    enroll["CRN"] = enroll["CRN"].apply(_clean_crn)

    instructor_map = (
        enroll[enroll["instructor_name"].notna()]
        .groupby("CRN")["instructor_name"]
        .apply(
            lambda names: "; ".join(
                sorted(
                    {str(name).strip() for name in names if name and str(name).strip()}
                )
            )
        )
        .to_dict()
    )

    return instructor_map
