from dataclasses import dataclass


@dataclass(frozen=True)
class Room:
    """Canonical representation of an exam room.

    ``large_only``: the room only seats exams no other room can (see
    ``domain/services/room_fit.py``).
    """

    name: str
    capacity: int
    large_only: bool = False

    def __post_init__(self):
        """Validate data."""
        if not self.name or not self.name.strip():
            raise ValueError("Room name cannot be empty")
        if self.capacity <= 0:
            raise ValueError("Room capacity must be positive")
