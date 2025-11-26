from dataclasses import dataclass
from typing import Any


@dataclass
class SchedulePermissions:
    """Encapsulates ownership and sharing information for a schedule."""

    is_owner: bool
    is_shared: bool
    created_by_user_id: str
    created_by_user_name: str
    shared_by_user_id: str | None = None
    shared_by_user_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for API response spreading."""
        return {
            "is_owner": self.is_owner,
            "is_shared": self.is_shared,
            "created_by_user_id": self.created_by_user_id,
            "created_by_user_name": self.created_by_user_name,
            "shared_by_user_id": self.shared_by_user_id,
            "shared_by_user_name": self.shared_by_user_name,
        }
