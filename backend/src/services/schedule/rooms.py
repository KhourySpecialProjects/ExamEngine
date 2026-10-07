"""A schedule's rooms with their capacity and blocked times (Explore tab).

Rooms come from the dataset's rooms table. Per-room blocked times are never
stored in the database, so they are parsed from the dataset's uploaded
room_blockouts file; only that file is downloaded. Access is the schedule-view
check (owner or shared with the user). Share recipients see the blocked slots,
never the file.
"""

import asyncio
import logging
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from src.core.exceptions import StorageError
from src.domain.constants import BLOCK_TIMES, DAY_NAMES
from src.domain.validation.parsing import parse_blockouts
from src.domain.validation.snapshot import ROOM_BLOCKOUTS
from src.repo.dataset import DatasetRepo
from src.repo.exam_assignment import ExamAssignmentRepo
from src.repo.room import RoomRepo
from src.repo.schedule import ScheduleRepo
from src.services.dataset.uploaded_files import download_uploaded_file
from src.services.schedule.slots import calendar_window
from src.services.storage.interface import IStorage


logger = logging.getLogger("examengine.schedule_rooms")

BlockoutsStatus = Literal["ok", "none_uploaded", "unavailable"]


class BlockedSlot(BaseModel):
    day: int
    """Day index, Monday = 0."""
    day_name: str
    block: int
    """Block index, 0 = the first block of the day."""
    block_time: str


class ScheduleRoom(BaseModel):
    name: str
    capacity: int
    blocked: list[BlockedSlot]
    """By day, then block. Empty when the room has none or they're unknown."""


class ScheduleRoomsResponse(BaseModel):
    rooms: list[ScheduleRoom]
    """Every room in the schedule's dataset, by name."""
    blockouts: BlockoutsStatus
    """"ok" when the room_blockouts file was read, "none_uploaded" when the
    dataset has none, "unavailable" when it was deleted or can't be read."""
    days: list[str]
    """The schedule's exam days, Monday first, for drawing its week."""
    block_times: list[str]
    """The schedule's blocks per day, earliest first."""


class ScheduleRoomsService:
    """Lists the rooms of a schedule the user may view."""

    def __init__(
        self,
        schedule_repo: ScheduleRepo,
        exam_assignment_repo: ExamAssignmentRepo,
        dataset_repo: DatasetRepo,
        room_repo: RoomRepo,
        storage: IStorage,
    ):
        self.schedule_repo = schedule_repo
        self.exam_assignment_repo = exam_assignment_repo
        self.dataset_repo = dataset_repo
        self.room_repo = room_repo
        self.storage = storage

    async def get(
        self, schedule_id: UUID, user_id: UUID
    ) -> ScheduleRoomsResponse | None:
        """The schedule's rooms, or None if the schedule isn't viewable."""
        schedule = self.schedule_repo.get_with_run_details(schedule_id, user_id)
        if schedule is None:
            return None
        run = schedule.run
        blockouts_status, blockouts = await self._blockouts(run.dataset_id, schedule_id)
        rooms = sorted(
            self.room_repo.get_all_for_dataset(run.dataset_id),
            key=lambda room: room.location,
        )
        assignments = self.exam_assignment_repo.get_all_for_schedule(schedule_id)
        days, block_times = calendar_window(run, assignments)
        return ScheduleRoomsResponse(
            rooms=[
                ScheduleRoom(
                    name=room.location,
                    capacity=room.capacity,
                    blocked=[
                        _blocked_slot(day, block)
                        for day, block in sorted(blockouts.get(room.location, ()))
                    ],
                )
                for room in rooms
            ],
            blockouts=blockouts_status,
            days=days,
            block_times=block_times,
        )

    async def _blockouts(
        self, dataset_id: UUID, schedule_id: UUID
    ) -> tuple[BlockoutsStatus, dict[str, frozenset[tuple[int, int]]]]:
        dataset = self.dataset_repo.get_by_id(dataset_id)
        if dataset is None:
            return "unavailable", {}
        context = f"Rooms of schedule {schedule_id}"
        try:
            content = await download_uploaded_file(
                dataset, self.storage, ROOM_BLOCKOUTS, context
            )
        except StorageError:
            return "unavailable", {}
        if content is None:
            return "none_uploaded", {}
        try:
            return "ok", await asyncio.to_thread(parse_blockouts, content)
        except Exception as exc:
            logger.warning(
                "%s: could not parse the room_blockouts file: %s: %s",
                context,
                type(exc).__name__,
                exc,
            )
            return "unavailable", {}


def _blocked_slot(day: int, block: int) -> BlockedSlot:
    return BlockedSlot(
        day=day,
        day_name=DAY_NAMES[day],
        block=block,
        block_time=BLOCK_TIMES[block],
    )
