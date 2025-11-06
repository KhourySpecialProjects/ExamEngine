from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.schemas.db import Rooms

from .base import BaseRepo


class RoomRepo(BaseRepo[Rooms]):
    """Repository for room operations."""

    def __init__(self, db: Session):
        super().__init__(Rooms, db)

    def get_by_name(self, room_name: str, dataset_id: UUID) -> Rooms | None:
        """Find room by name within a dataset."""
        stmt = select(Rooms).where(
            Rooms.location == room_name, Rooms.dataset_id == dataset_id
        )
        return self.db.execute(stmt).scalars().first()

    def get_all_for_dataset(self, dataset_id: UUID) -> list[Rooms]:
        """Get all rooms for a dataset."""
        stmt = select(Rooms).where(Rooms.dataset_id == dataset_id)
        return list(self.db.execute(stmt).scalars().all())

    def bulk_create_from_dataframe(self, dataset_id: UUID, rooms_df) -> dict[str, UUID]:
        """
        Create room records from rooms DataFrame.

        Returns mapping of room_name -> room_id.
        """
        room_objs = []
        for _, row in rooms_df.iterrows():
            room = Rooms(
                location=row["room_name"],
                capacity=int(row["capacity"]),
                dataset_id=dataset_id,
            )
            room_objs.append(room)

        self.db.bulk_save_objects(room_objs, return_defaults=True)
        self.db.commit()

        # Build mapping
        mapping = {}
        for obj in room_objs:
            mapping[obj.location] = obj.room_id

        return mapping
