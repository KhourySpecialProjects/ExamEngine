"""Sharing a late-add chain as one unit.

A chain is a generated schedule plus every late-add version made from it (their
runs record it as `original_schedule_id`). Its group is the owner of that
original plus everyone a schedule of the chain is shared with. Sharing or
unsharing any schedule of the chain applies to every schedule in it, and a new
version is shared with the whole group, so the group always sees the same
schedules. Owners of later versions are members through their shares of the
rest of the chain, so removing someone (which deletes all their shares) keeps
them out of later versions; they keep the versions they own.

Saving a version and sharing or unsharing hold the chain lock
(`ScheduleRepo.lock_chain`), so none of them works from a stale group. Nothing
here commits: every method flushes and the caller commits.
"""

from uuid import UUID

from src.repo.schedule import ScheduleRepo
from src.repo.schedule_share import ScheduleShareRepo
from src.schemas.db import Schedules, ScheduleShares


SHARE_PERMISSION = "view"


class ChainSharing:
    def __init__(self, schedule_repo: ScheduleRepo, share_repo: ScheduleShareRepo):
        self.schedule_repo = schedule_repo
        self.share_repo = share_repo

    def _shares(self, chain: list[Schedules]) -> list[ScheduleShares]:
        return self.share_repo.get_shares_for_schedules([s.schedule_id for s in chain])

    def share_new_version(
        self, base: Schedules, new_schedule_id: UUID, saved_by: UUID
    ) -> None:
        """Share a version just saved from `base` with the chain's group.

        The caller holds the chain lock.
        """
        chain = self.schedule_repo.get_chain(base)
        original_id = UUID(self.schedule_repo.chain_original_id(base))
        members = {s.run.user_id for s in chain if s.schedule_id == original_id} | {
            share.shared_with_user_id for share in self._shares(chain)
        }
        for user_id in members - {saved_by}:
            self.share_repo.add_share(
                new_schedule_id,
                shared_with_user_id=user_id,
                permission=SHARE_PERMISSION,
                shared_by_user_id=saved_by,
            )

    def share_chain(
        self, schedule: Schedules, user_id: UUID, shared_by: UUID, permission: str
    ) -> None:
        """Share every schedule of the chain the user doesn't own or have yet."""
        self.schedule_repo.lock_chain(schedule)
        chain = self.schedule_repo.get_chain(schedule)
        has = {
            share.schedule_id
            for share in self._shares(chain)
            if share.shared_with_user_id == user_id
        }
        for s in chain:
            if s.run.user_id != user_id and s.schedule_id not in has:
                self.share_repo.add_share(
                    s.schedule_id,
                    shared_with_user_id=user_id,
                    permission=permission,
                    shared_by_user_id=shared_by,
                )

    def unshare_chain(self, schedule: Schedules, user_id: UUID) -> None:
        """Remove the user's shares of every schedule in the chain."""
        self.schedule_repo.lock_chain(schedule)
        chain = self.schedule_repo.get_chain(schedule)
        self.share_repo.delete_shares_for_user([s.schedule_id for s in chain], user_id)
