from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.schemas.db import ConflictAnalyses

from .base import BaseRepo


class ConflictAnalysesRepo(BaseRepo[ConflictAnalyses]):
    """Repository for conflict analysis operations."""

    def __init__(self, db: Session):
        super().__init__(ConflictAnalyses, db)

    def get_by_schedule_id(self, schedule_id: UUID) -> ConflictAnalyses | None:
        """Get conflict analysis for a schedule."""
        stmt = select(ConflictAnalyses).where(
            ConflictAnalyses.schedule_id == schedule_id
        )
        return self.db.execute(stmt).scalars().first()

    def create_analysis(
        self,
        schedule_id: UUID,
        conflicts_data: dict,
    ) -> ConflictAnalyses:
        """Create new conflict analysis record."""
        analysis = self.add_analysis(schedule_id, conflicts_data)
        self.db.commit()
        self.db.refresh(analysis)
        return analysis

    def add_analysis(self, schedule_id: UUID, conflicts_data: dict) -> ConflictAnalyses:
        """`create_analysis` without the commit; the caller commits."""
        analysis = ConflictAnalyses(
            schedule_id=schedule_id,
            conflicts=conflicts_data,
        )
        self.db.add(analysis)
        self.db.flush()
        return analysis
