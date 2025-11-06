from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from src.schemas.db import ExamAssignments

from .base import BaseRepo


class ExamAssignmentRepo(BaseRepo[ExamAssignments]):
    """Repository for exam assignment operations."""

    def __init__(self, db: Session):
        super().__init__(ExamAssignments, db)

    def bulk_create(
        self, schedule_id: UUID, assignments: list[dict]
    ) -> list[ExamAssignments]:
        """
        Bulk create exam assignments efficiently.

        Args:
            schedule_id: Schedule these assignments belong to
            assignments: List of dicts with course_id, time_slot_id, room_id

        Returns:
            List of created ExamAssignment objects
        """
        exam_objs = [
            ExamAssignments(
                schedule_id=schedule_id,
                course_id=assignment["course_id"],
                time_slot_id=assignment["time_slot_id"],
                room_id=assignment["room_id"],
            )
            for assignment in assignments
        ]

        self.db.bulk_save_objects(exam_objs, return_defaults=True)
        self.db.commit()

        return exam_objs

    def get_all_for_schedule(self, schedule_id: UUID) -> list[ExamAssignments]:
        """
        Get all exam assignments for a schedule.

        Eagerly loads related course, time slot, and room data.
        """
        stmt = (
            select(ExamAssignments)
            .options(
                joinedload(ExamAssignments.course),
                joinedload(ExamAssignments.time_slot),
                joinedload(ExamAssignments.room),
            )
            .where(ExamAssignments.schedule_id == schedule_id)
        )
        return list(self.db.execute(stmt).scalars().unique().all())
