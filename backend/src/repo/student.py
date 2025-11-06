from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.schemas.db import Students

from .base import BaseRepo


class StudentRepo(BaseRepo[Students]):
    """Repository for student operations."""

    def __init__(self, db: Session):
        super().__init__(Students, db)

    def get_by_student_id(self, student_id: str, dataset_id: UUID) -> Students | None:
        """Find student by ID within a dataset."""
        stmt = select(Students).where(
            Students.student_id == student_id, Students.dataset_id == dataset_id
        )
        return self.db.execute(stmt).scalars().first()

    def bulk_create_from_dataframe(self, dataset_id: UUID, enrollment_df) -> set[str]:
        """
        Create student records from enrollment DataFrame.

        Extracts unique student IDs and creates Student records.

        Args:
            dataset_id: Dataset these students belong to
            enrollment_df: Enrollment DataFrame with student_id column

        Returns:
            Set of created student IDs
        """
        # Get unique student IDs from enrollment data
        unique_student_ids = enrollment_df["student_id"].unique()

        # Create Student records
        student_objs = [
            Students(
                student_id=str(sid),
                dataset_id=dataset_id,
            )
            for sid in unique_student_ids
        ]

        self.db.bulk_save_objects(student_objs)
        self.db.commit()

        return set(unique_student_ids)

    def get_all_for_dataset(self, dataset_id: UUID) -> list[Students]:
        """Get all students for a dataset."""
        stmt = select(Students).where(Students.dataset_id == dataset_id)
        return list(self.db.execute(stmt).scalars().all())
