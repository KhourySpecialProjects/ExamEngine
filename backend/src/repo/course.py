from uuid import UUID

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
        self, dataset_id: UUID, courses_df
    ) -> dict[str, UUID]:
        """
        Create course records from census DataFrame.

        Returns mapping of course_ref -> course_id for assignment creation.
        """
        course_objs = []
        for _, row in courses_df.iterrows():
            course = Courses(
                course_subject_code=str(row.get("CourseID", "")),
                crn=str(row.get("CRN", "")),
                enrollment_count=int(row.get("num_students", 0)),
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
