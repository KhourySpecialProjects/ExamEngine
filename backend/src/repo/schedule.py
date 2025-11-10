from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from src.repo.base import BaseRepo
from src.schemas.db import (
    ExamAssignments,
    Runs,
    Schedules,
    StatusEnum,
)


class ScheduleRepo(BaseRepo[Schedules]):
    """Repository for schedule data access operations."""

    def __init__(self, db: Session):
        super().__init__(Schedules, db)

    def get_by_id(self, schedule_id: UUID) -> Schedules | None:
        """Get schedule by ID without relationships."""
        stmt = select(Schedules).where(Schedules.schedule_id == schedule_id)
        return self.db.execute(stmt).scalars().first()

    def get_by_id_for_user(self, schedule_id: UUID, user_id: UUID) -> Schedules | None:
        """
        Get schedule with authorization check.

        Joins through Runs to verify user owns this schedule.
        """
        stmt = (
            select(Schedules)
            .join(Runs, Schedules.run_id == Runs.run_id)
            .where(Schedules.schedule_id == schedule_id, Runs.user_id == user_id)
        )
        return self.db.execute(stmt).scalars().first()

    def get_with_run_details(
        self, schedule_id: UUID, user_id: UUID
    ) -> Schedules | None:
        """
        Get schedule with run metadata eagerly loaded.

        Efficient single query that loads schedule + run data.
        """
        stmt = (
            select(Schedules)
            .join(Runs)
            .options(joinedload(Schedules.run))
            .where(Schedules.schedule_id == schedule_id, Runs.user_id == user_id)
        )
        return self.db.execute(stmt).scalars().first()

    def get_all_for_user(self, user_id: UUID) -> list[Schedules]:
        """Get all schedules for user with pagination."""
        stmt = (
            select(Schedules)
            .join(Runs)
            .options(joinedload(Schedules.run))
            .where(Runs.user_id == user_id)
            .order_by(Schedules.created_at.desc())
        )
        return list(self.db.execute(stmt).scalars().unique().all())

    def name_exists(self, schedule_name: str) -> bool:
        """Check if schedule name is already taken."""
        stmt = select(Schedules.schedule_id).where(
            Schedules.schedule_name == schedule_name
        )
        return self.db.execute(stmt).first() is not None

    def create_schedule_with_run(
        self,
        schedule_name: str,
        dataset_id: UUID,
        user_id: UUID,
        algorithm_name: str,
        parameters: dict,
    ) -> tuple[Schedules, Runs]:
        """
        Create schedule and run in single transaction.

        Returns both objects so service can update run status later.
        """
        run = Runs(
            dataset_id=dataset_id,
            user_id=user_id,
            algorithm_name=algorithm_name,
            parameters=parameters,
            status=StatusEnum.Running,
        )
        self.db.add(run)
        self.db.flush()

        schedule = Schedules(schedule_name=schedule_name, run_id=run.run_id)
        self.db.add(schedule)
        self.db.commit()

        self.db.refresh(run)
        self.db.refresh(schedule)

        return schedule, run

    def get_exam_assignments_count(self, schedule_id: UUID) -> int:
        """Count exam assignments for a schedule."""
        stmt = select(func.count(ExamAssignments.exam_assignment_id)).where(
            ExamAssignments.schedule_id == schedule_id
        )
        count = self.db.execute(stmt).scalar()
        return count or 0

    def get_schedule_summary(self, schedule_id: UUID, user_id: UUID) -> dict | None:
        """
        Get schedule summary with counts.

        Efficient query that doesn't load all exam assignments.
        """
        schedule = self.get_with_run_details(schedule_id, user_id)
        if not schedule:
            return None

        exam_count = self.get_exam_assignments_count(schedule_id)

        return {
            "schedule_id": str(schedule.schedule_id),
            "schedule_name": schedule.schedule_name,
            "created_at": schedule.created_at.isoformat(),
            "total_exams": exam_count,
            "algorithm": schedule.run.algorithm_name,
            "parameters": schedule.run.parameters,
            "status": schedule.run.status.value,
            "dataset_id": str(schedule.run.dataset_id),
        }

    def delete_schedule_cascade(self, schedule_id: UUID, user_id: UUID) -> bool:
        """
        Delete schedule and all related data.

        Deletes in order:
        1. Exam assignments (references schedule)
        2. Conflicts (references schedule)
        3. Schedule itself
        4. Optionally Run (if you want to remove history)
        """
        schedule = self.get_by_id_for_user(schedule_id, user_id)
        if not schedule:
            return False

        self.db.query(ExamAssignments).filter(
            ExamAssignments.schedule_id == schedule_id
        ).delete(synchronize_session=False)

        self.db.delete(schedule)

        self.db.commit()
        return True
