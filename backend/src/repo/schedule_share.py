"""
Repository for schedule sharing operations.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.schemas.db import Schedules, ScheduleShares

from .base import BaseRepo


class ScheduleShareRepo(BaseRepo[ScheduleShares]):
    """Repository for schedule share data access operations."""

    def __init__(self, db: Session):
        super().__init__(ScheduleShares, db)

    def create_share(
        self,
        schedule_id: UUID,
        shared_with_user_id: UUID,
        permission: str,
        shared_by_user_id: UUID,
    ) -> ScheduleShares:
        """
        Create a new schedule share.

        Args:
            schedule_id: Schedule to share
            shared_with_user_id: User to share with
            permission: "view" or "edit"
            shared_by_user_id: User creating the share

        Returns:
            Created share
        """
        share = ScheduleShares(
            schedule_id=schedule_id,
            shared_with_user_id=shared_with_user_id,
            permission=permission,
            shared_by_user_id=shared_by_user_id,
        )
        return self.create(share)

    def get_share(self, share_id: UUID) -> ScheduleShares | None:
        """Get share by ID."""
        stmt = select(ScheduleShares).where(ScheduleShares.share_id == share_id)
        return self.db.execute(stmt).scalars().first()

    def get_shares_for_schedule(self, schedule_id: UUID) -> list[ScheduleShares]:
        """Get all shares for a schedule."""
        stmt = (
            select(ScheduleShares)
            .where(ScheduleShares.schedule_id == schedule_id)
            .order_by(ScheduleShares.shared_at.desc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_shared_schedules_for_user(self, user_id: UUID) -> list[ScheduleShares]:
        """Get all schedules shared with a user."""
        from sqlalchemy.orm import joinedload

        stmt = (
            select(ScheduleShares)
            .options(
                joinedload(ScheduleShares.schedule),
                joinedload(ScheduleShares.shared_by_user),
            )
            .where(ScheduleShares.shared_with_user_id == user_id)
            .order_by(ScheduleShares.shared_at.desc())
        )
        return list(self.db.execute(stmt).scalars().unique().all())

    def get_share_by_schedule_and_user(
        self, schedule_id: UUID, shared_with_user_id: UUID
    ) -> ScheduleShares | None:
        """Get share for a specific schedule and user."""
        from sqlalchemy.orm import joinedload

        stmt = (
            select(ScheduleShares)
            .options(joinedload(ScheduleShares.shared_by_user))
            .where(
                ScheduleShares.schedule_id == schedule_id,
                ScheduleShares.shared_with_user_id == shared_with_user_id,
            )
        )
        return self.db.execute(stmt).scalars().first()

    def update_share_permission(
        self, share_id: UUID, permission: str
    ) -> ScheduleShares | None:
        """Update share permission."""
        share = self.get_share(share_id)
        if share:
            share.permission = permission
            return self.update(share)
        return None

    def delete_share(self, share_id: UUID) -> bool:
        """Delete a share."""
        share = self.get_share(share_id)
        if share:
            self.delete(share)
            return True
        return False

    def delete_share_by_schedule_and_user(
        self, schedule_id: UUID, shared_with_user_id: UUID
    ) -> bool:
        """Delete share for a specific schedule and user."""
        share = self.get_share_by_schedule_and_user(schedule_id, shared_with_user_id)
        if share:
            self.delete(share)
            return True
        return False

    def user_has_access(
        self, schedule_id: UUID, user_id: UUID, required_permission: str = "view"
    ) -> bool:
        """
        Check if user has access to schedule (either owns it or has share).

        Args:
            schedule_id: Schedule to check
            user_id: User to check access for
            required_permission: "view" or "edit"

        Returns:
            True if user has required permission or better
        """
        # Check if user owns the schedule (through run)
        from src.schemas.db import Runs

        stmt = (
            select(Schedules)
            .join(Runs, Schedules.run_id == Runs.run_id)
            .where(
                Schedules.schedule_id == schedule_id,
                Runs.user_id == user_id,
            )
        )
        if self.db.execute(stmt).scalars().first():
            return True  # Owner has full access

        # Check if user has share
        share = self.get_share_by_schedule_and_user(schedule_id, user_id)
        if not share:
            return False

        # Check permission level
        if required_permission == "view":
            return True  # Both view and edit can view
        elif required_permission == "edit":
            return share.permission == "edit"
        else:
            return False
