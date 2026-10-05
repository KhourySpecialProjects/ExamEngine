from uuid import UUID

from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session, joinedload

from src.repo.base import BaseRepo
from src.schemas.db import (
    ExamAssignments,
    Runs,
    Schedules,
    ScheduleShares,
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

    @staticmethod
    def _viewable_by(user_id: UUID):
        """Condition: the user owns the schedule's run or it is shared with them.

        The one visibility rule for every lookup on behalf of a user. Needs
        `Runs` joined.
        """
        shared = exists().where(
            ScheduleShares.schedule_id == Schedules.schedule_id,
            ScheduleShares.shared_with_user_id == user_id,
        )
        return or_(Runs.user_id == user_id, shared)

    def get_by_id_for_user(self, schedule_id: UUID, user_id: UUID) -> Schedules | None:
        """The schedule if the user owns it or it is shared with them."""
        stmt = (
            select(Schedules)
            .join(Runs, Schedules.run_id == Runs.run_id)
            .where(Schedules.schedule_id == schedule_id, self._viewable_by(user_id))
        )
        return self.db.execute(stmt).scalars().first()

    def get_with_run_details(
        self, schedule_id: UUID, user_id: UUID
    ) -> Schedules | None:
        """`get_by_id_for_user` with the run and its user eagerly loaded."""
        stmt = (
            select(Schedules)
            .join(Runs, Schedules.run_id == Runs.run_id)
            .options(joinedload(Schedules.run).joinedload(Runs.user))
            .where(Schedules.schedule_id == schedule_id, self._viewable_by(user_id))
        )
        return self.db.execute(stmt).scalars().first()

    def get_all_for_user(self, user_id: UUID) -> list[Schedules]:
        """Every schedule the user owns or that is shared with them, newest first."""
        stmt = (
            select(Schedules)
            .join(Runs, Schedules.run_id == Runs.run_id)
            .options(
                joinedload(Schedules.run).joinedload(Runs.user),
                joinedload(Schedules.run).joinedload(Runs.dataset),
            )
            .where(self._viewable_by(user_id))
            .order_by(Schedules.created_at.desc())
        )
        return list(self.db.execute(stmt).scalars().unique().all())

    def get_viewable_names(
        self, schedule_ids: list[UUID], user_id: UUID
    ) -> dict[UUID, str]:
        """Names of those schedules the user can view; others are left out."""
        if not schedule_ids:
            return {}
        stmt = (
            select(Schedules.schedule_id, Schedules.schedule_name)
            .join(Runs, Schedules.run_id == Runs.run_id)
            .where(Schedules.schedule_id.in_(schedule_ids), self._viewable_by(user_id))
        )
        return dict(self.db.execute(stmt).tuples().all())

    def get_newer_versions(self, schedule_id: UUID, user_id: UUID) -> list[Schedules]:
        """Viewable schedules saved as late adds based on this one, newest first."""
        stmt = (
            select(Schedules)
            .join(Runs, Schedules.run_id == Runs.run_id)
            .where(
                Runs.parameters["based_on_schedule_id"].astext == str(schedule_id),
                self._viewable_by(user_id),
            )
            .order_by(Schedules.created_at.desc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def name_exists(self, schedule_name: str, user_id: UUID) -> bool:
        """Check if schedule name is already taken by a specific user."""
        stmt = (
            select(Schedules.schedule_id)
            .join(Runs, Schedules.run_id == Runs.run_id)
            .where(Schedules.schedule_name == schedule_name, Runs.user_id == user_id)
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
