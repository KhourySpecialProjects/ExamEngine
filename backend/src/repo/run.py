from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.schemas.db import Runs, StatusEnum

from .base import BaseRepo


class RunRepo(BaseRepo[Runs]):
    """Repository for algorithm run tracking."""

    def __init__(self, db: Session):
        super().__init__(Runs, db)

    def get_by_id(self, run_id: UUID) -> Runs | None:
        """Get run by ID."""
        stmt = select(Runs).where(Runs.run_id == run_id)
        return self.db.execute(stmt).scalars().first()

    def get_by_id_for_user(self, run_id: UUID, user_id: UUID) -> Runs | None:
        """Get run with authorization check."""
        stmt = select(Runs).where(Runs.run_id == run_id, Runs.user_id == user_id)
        return self.db.execute(stmt).scalars().first()

    def update_status(self, run_id: UUID, status: StatusEnum) -> Runs | None:
        """Update run status (Running -> Completed/Failed)."""
        run = self.get_by_id(run_id)
        if run:
            run.status = status
            self.db.commit()
            self.db.refresh(run)
        return run

    def get_all_for_dataset(self, dataset_id: UUID, user_id: UUID) -> list[Runs]:
        """Get all runs for a dataset (scheduling history)."""
        stmt = (
            select(Runs)
            .where(Runs.dataset_id == dataset_id, Runs.user_id == user_id)
            .order_by(Runs.run_timestamp.desc())
        )
        return list(self.db.execute(stmt).scalars().all())
