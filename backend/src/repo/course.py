from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.domain.models import Course
from src.schemas.db import Courses

from .base import BaseRepo


class CourseRepo(BaseRepo[Courses]):
    """Repository for course data access."""

    def __init__(self, db: Session):
        super().__init__(Courses, db)

    def get_by_crn(self, crn: str, dataset_id: UUID) -> Courses | None:
        """Find course by CRN within a dataset."""
        stmt = select(Courses).where(
            Courses.crn == crn,
            Courses.dataset_id == dataset_id,
        )
        return self.db.execute(stmt).scalars().first()

    def get_all_for_dataset(self, dataset_id: UUID) -> list[Courses]:
        """Get all courses for a dataset."""
        stmt = select(Courses).where(Courses.dataset_id == dataset_id)
        return list(self.db.execute(stmt).scalars().all())

    def bulk_create_from_domain(
        self,
        dataset_id: UUID,
        courses: dict[str, Course],
    ) -> dict[str, UUID]:
        """
        Create course records from domain Course objects.

        Args:
            dataset_id: UUID of the dataset
            courses: Dict mapping CRN to Course domain objects

        Returns:
            Mapping of crn -> course_id
        """
        course_objs = []

        for _crn, course in courses.items():
            db_course = Courses(
                course_id=uuid4(),
                crn=course.crn,
                course_subject_code=course.course_code,
                enrollment_count=course.enrollment_count,
                instructor_name="; ".join(sorted(course.instructor_names))
                if course.instructor_names
                else None,
                department=course.department,
                examination_term=course.examination_term,
                dataset_id=dataset_id,
            )
            course_objs.append(db_course)

        if course_objs:
            self.db.bulk_save_objects(course_objs, return_defaults=True)
            self.db.commit()

        return {obj.crn: obj.course_id for obj in course_objs}
