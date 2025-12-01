from dataclasses import dataclass


@dataclass(frozen=True)
class Conflict:
    """Represents a detected scheduling conflict."""

    conflict_type: str
    entity_id: str
    crn: str
    conflicting_crn: str | None
    day: int
    block: int
