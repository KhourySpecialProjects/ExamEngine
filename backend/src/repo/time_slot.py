from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.domain.constants import EXAM_BLOCKS
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
        # Map day names to enum (handle multiple formats)
        day_map = {
            "Mon": DayEnum.Monday,
            "Monday": DayEnum.Monday,
            "Tue": DayEnum.Tuesday,
            "Tuesday": DayEnum.Tuesday,
            "Wed": DayEnum.Wednesday,
            "Wednesday": DayEnum.Wednesday,
            "Thu": DayEnum.Thursday,
            "Thursday": DayEnum.Thursday,
            "Fri": DayEnum.Friday,
            "Friday": DayEnum.Friday,
            "Sat": DayEnum.Saturday,
            "Saturday": DayEnum.Saturday,
            "Sun": DayEnum.Sunday,
            "Sunday": DayEnum.Sunday,
        }

        # Get day enum
        day_enum = day_map.get(day)

        # If day not found in map, raise a clear error
        if day_enum is None:
            raise ValueError(
                f"Invalid day name: '{day}'. Expected one of: {list(day_map.keys())}"
            )

        if not 0 <= block_index < len(EXAM_BLOCKS):
            raise ValueError(
                f"Invalid block_index: {block_index}. "
                f"Expected 0-{len(EXAM_BLOCKS) - 1}."
            )
        block = EXAM_BLOCKS[block_index]
        start_time, end_time, label = block.start, block.end, block.label

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
