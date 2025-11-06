from datetime import time
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.schemas.db import DayEnum, TimeSlots

from .base import BaseRepo


class TimeSlotRepo(BaseRepo[TimeSlots]):
    """Repository for time slot operations."""

    def __init__(self, db: Session):
        super().__init__(TimeSlots, db)

    def get_or_create_slot(
        self, dataset_id: UUID, day: str, block_index: int
    ) -> TimeSlots:
        """
        Get or create time slot for day and block.

        Maps DSATUR output (day_index, block_index) to TimeSlot records.
        """
        # Map day names to enum
        day_map = {
            "Mon": DayEnum.Monday,
            "Tue": DayEnum.Tuesday,
            "Wed": DayEnum.Wednesday,
            "Thu": DayEnum.Thursday,
            "Fri": DayEnum.Friday,
        }

        # Map block index to time ranges
        block_times = {
            0: (time(9, 0), time(11, 0), "9AM-11AM"),
            1: (time(11, 30), time(13, 30), "11:30AM-1:30PM"),
            2: (time(14, 0), time(16, 0), "2PM-4PM"),
            3: (time(16, 30), time(18, 30), "4:30PM-6:30PM"),
            4: (time(19, 0), time(21, 0), "7PM-9PM"),
        }

        day_enum = day_map.get(day)
        start_time, end_time, label = block_times.get(
            block_index, (time(9, 0), time(11, 0), "9AM-11AM")
        )

        # Try to find existing slot
        stmt = select(TimeSlots).where(
            TimeSlots.dataset_id == dataset_id,
            TimeSlots.day == day_enum,
            TimeSlots.start_time == start_time,
        )
        existing = self.db.execute(stmt).scalars().first()

        if existing:
            return existing

        # Create new slot
        slot = TimeSlots(
            slot_label=label,
            day=day_enum,
            start_time=start_time,
            end_time=end_time,
            dataset_id=dataset_id,
        )
        self.db.add(slot)
        self.db.flush()

        return slot
