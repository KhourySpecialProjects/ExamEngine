from uuid import UUID

from src.domain.value_objects import SchedulePermissions
from src.repo.schedule_share import ScheduleShareRepo
from src.schemas.db import Schedules


class SchedulePermissionService:
    """
    Handles schedule ownership and sharing permission checks.

    """

    def __init__(self, share_repo: ScheduleShareRepo):
        self.share_repo = share_repo

    def get_permissions(
        self, schedule: Schedules, user_id: UUID
    ) -> SchedulePermissions:
        """
        Determine user's relationship to a schedule.

        Returns a SchedulePermissions dataclass with all ownership/sharing info
        needed for API responses.

        Args:
            schedule: Schedule with run relationship loaded
            user_id: User to check permissions for

        Returns:
            SchedulePermissions with is_owner, is_shared, and creator info
        """
        is_owner = schedule.run.user_id == user_id
        created_by_user_id = str(schedule.run.user_id)
        created_by_user_name = (
            schedule.run.user.name if schedule.run.user else "Unknown"
        )

        # Default: not shared
        is_shared = False
        shared_by_user_id = None
        shared_by_user_name = None

        # If not owner, check for share
        if not is_owner:
            share = self.share_repo.get_share_by_schedule_and_user(
                schedule.schedule_id, user_id
            )
            if share and share.shared_by_user:
                is_shared = True
                shared_by_user_id = str(share.shared_by_user_id)
                shared_by_user_name = share.shared_by_user.name

        return SchedulePermissions(
            is_owner=is_owner,
            is_shared=is_shared,
            created_by_user_id=created_by_user_id,
            created_by_user_name=created_by_user_name,
            shared_by_user_id=shared_by_user_id,
            shared_by_user_name=shared_by_user_name,
        )

    def can_view(self, schedule: Schedules, user_id: UUID) -> bool:
        """
        Check if user can view a schedule.

        User can view if they own it or have any share (view or edit).
        """
        perms = self.get_permissions(schedule, user_id)
        return perms.is_owner or perms.is_shared

    def can_edit(self, schedule: Schedules, user_id: UUID) -> bool:
        """
        Check if user can edit a schedule.

        User can edit if they own it or have an 'edit' permission share.
        """
        # Owner can always edit
        if schedule.run.user_id == user_id:
            return True

        # Check for edit permission share
        share = self.share_repo.get_share_by_schedule_and_user(
            schedule.schedule_id, user_id
        )
        return share is not None and share.permission == "edit"

    def can_delete(self, schedule: Schedules, user_id: UUID) -> bool:
        """
        Check if user can delete a schedule.

        Only owners can delete schedules.
        """
        return schedule.run.user_id == user_id

    def can_share(self, schedule: Schedules, user_id: UUID) -> bool:
        """
        Check if user can share a schedule with others.

        Only owners can share schedules.
        """
        return schedule.run.user_id == user_id
