from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.domain.models import Room
from src.schemas.db import Rooms

from .base import BaseRepo


class RoomRepo(BaseRepo[Rooms]):
    """Repository for room operations."""

    def __init__(self, db: Session):
        super().__init__(Rooms, db)

    def get_by_name(self, room_name: str, dataset_id: UUID) -> Rooms | None:
        """Find room by name within a dataset."""
        stmt = select(Rooms).where(
            Rooms.location == room_name,
            Rooms.dataset_id == dataset_id,
        )
        return self.db.execute(stmt).scalars().first()

    def get_all_for_dataset(self, dataset_id: UUID) -> list[Rooms]:
        """Get all rooms for a dataset."""
        stmt = select(Rooms).where(Rooms.dataset_id == dataset_id)
        return list(self.db.execute(stmt).scalars().all())

    def bulk_create_from_domain(
        self,
        dataset_id: UUID,
        rooms: list[Room],
    ) -> dict[str, UUID]:
        """
        Create room records from domain Room objects.

        Args:
            dataset_id: UUID of the dataset
            rooms: List of Room domain objects

        Returns:
            Mapping of room_name -> room_id
        """
        room_objs = []

        for room in rooms:
            db_room = Rooms(
                room_id=uuid4(),
                location=room.name,
                capacity=room.capacity,
                dataset_id=dataset_id,
            )
            room_objs.append(db_room)

        if room_objs:
            self.db.bulk_save_objects(room_objs, return_defaults=True)
            self.db.commit()

        return {obj.location: obj.room_id for obj in room_objs}
