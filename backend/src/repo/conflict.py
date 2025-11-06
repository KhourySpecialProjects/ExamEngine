from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from src.schemas.db import Conflicts

from .base import BaseRepo


class ConflictRepo(BaseRepo[Conflicts]):
    """Repository for conflict tracking."""

    def __init__(self, db: Session):
        super().__init__(Conflicts, db)

    def bulk_create(self, schedule_id: UUID, conflicts: list[dict]) -> list[Conflicts]:
        """
        Bulk create conflicts efficiently.

        Args:
            schedule_id: Schedule these conflicts belong to
            conflicts: List of dicts with student_id, exam_assignment_ids, conflict_type
        """
        conflict_objs = [
            Conflicts(
                schedule_id=schedule_id,
                student_id=c["student_id"],
                exam_assignment_ids=c["exam_assignment_ids"],
                conflict_type=c["conflict_type"],
            )
            for c in conflicts
        ]

        self.db.bulk_save_objects(conflict_objs, return_defaults=True)
        self.db.commit()

        return conflict_objs

    def get_all_for_schedule(self, schedule_id: UUID) -> list[Conflicts]:
        """Get all conflicts for a schedule."""
        stmt = (
            select(Conflicts)
            .options(joinedload(Conflicts.student))
            .where(Conflicts.schedule_id == schedule_id)
        )
        return list(self.db.execute(stmt).scalars().unique().all())
