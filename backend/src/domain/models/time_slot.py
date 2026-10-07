from dataclasses import dataclass


@dataclass(frozen=True)
class TimeSlot:
    """Represents a specific exam time slot."""

    day: str  # e.g., "Monday", "Tuesday"
    block: str  # e.g., "8AM-10AM", "10:30AM-12:30PM"

    def __post_init__(self):
        """Validate data."""
        if not self.day or not self.day.strip():
            raise ValueError("Day cannot be empty")
        if not self.block or not self.block.strip():
            raise ValueError("Block cannot be empty")
