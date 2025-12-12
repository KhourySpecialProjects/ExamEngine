"""
Service for validating course merges.

Checks if merging multiple CRNs is feasible based on room capacity
and other constraints.
"""

from dataclasses import dataclass
from typing import Any

from src.domain.models import SchedulingDataset


@dataclass
class MergeValidationResult:
    """Result of validating a course merge."""

    is_valid: bool
    """True if merged courses fit in largest available room."""
    has_suitable_room: bool
    """True if there's a room that can fit the merged enrollment."""
    total_enrollment: int
    """Sum of enrollment counts for all CRNs in merge."""
    max_room_capacity: int
    """Largest room capacity available."""
    crns: list[str]
    """List of CRNs being merged."""
    warning_message: str | None = None
    """Warning message if merge exceeds room capacity."""
    can_proceed: bool = True
    """Whether user can proceed with merge anyway (will be unscheduled if no room fits)."""
    suggested_action: str | None = None
    """Suggested action if merge is problematic."""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "is_valid": self.is_valid,
            "has_suitable_room": self.has_suitable_room,
            "total_enrollment": self.total_enrollment,
            "max_room_capacity": self.max_room_capacity,
            "crns": self.crns,
            "warning_message": self.warning_message,
            "can_proceed": self.can_proceed,
            "suggested_action": self.suggested_action,
        }


class MergeValidator:
    """Validates course merges against dataset constraints."""

    def __init__(self, dataset: SchedulingDataset):
        """
        Initialize validator with dataset.

        Args:
            dataset: The scheduling dataset containing courses and rooms
        """
        self.dataset = dataset

    def validate_merge(self, crns: list[str]) -> MergeValidationResult:
        """
        Validate if merging multiple CRNs is feasible.

        Args:
            crns: List of CRNs to merge together

        Returns:
            MergeValidationResult with validation details

        Raises:
            ValueError: If any CRN doesn't exist in dataset
        """
        if not crns:
            raise ValueError("Cannot merge empty list of CRNs")

        if len(crns) < 2:
            raise ValueError("Need at least 2 CRNs to merge")

        # Validate all CRNs exist
        missing_crns = [crn for crn in crns if crn not in self.dataset.courses]
        if missing_crns:
            raise ValueError(f"CRNs not found in dataset: {missing_crns}")

        # Calculate total enrollment
        total_enrollment = sum(
            self.dataset.get_enrollment_count(crn) for crn in crns
        )

        # Find maximum room capacity
        max_room_capacity = (
            max((room.capacity for room in self.dataset.rooms), default=0)
            if self.dataset.rooms
            else 0
        )

        # Check if merge fits
        is_valid = total_enrollment <= max_room_capacity
        has_suitable_room = max_room_capacity > 0 and total_enrollment <= max_room_capacity

        # Generate warning message if needed
        warning_message = None
        suggested_action = None

        if not has_suitable_room:
            if max_room_capacity == 0:
                warning_message = (
                    f"No rooms available in dataset. Merged courses cannot be scheduled."
                )
                suggested_action = "Add rooms to the dataset or remove this merge group."
            else:
                warning_message = (
                    f"Merged courses require room with {total_enrollment} capacity, "
                    f"but largest available room is {max_room_capacity}. "
                    f"This merge cannot be scheduled with a room."
                )
                suggested_action = (
                    "You can still save this merge, but it will not be assigned a time slot or room. "
                    "It will appear in the schedule as unscheduled."
                )

        return MergeValidationResult(
            is_valid=is_valid,
            has_suitable_room=has_suitable_room,
            total_enrollment=total_enrollment,
            max_room_capacity=max_room_capacity,
            crns=crns,
            warning_message=warning_message,
            can_proceed=True,  # Always allow proceeding (will be unscheduled if no room fits)
            suggested_action=suggested_action,
        )

    def validate_multiple_merges(
        self, merges: dict[str, list[str]]
    ) -> dict[str, MergeValidationResult]:
        """
        Validate multiple merge groups at once.

        Args:
            merges: Dictionary mapping merge_group_id to list of CRNs

        Returns:
            Dictionary mapping merge_group_id to validation result
        """
        results = {}
        for merge_id, crns in merges.items():
            try:
                results[merge_id] = self.validate_merge(crns)
            except ValueError as e:
                # Create invalid result for error case
                results[merge_id] = MergeValidationResult(
                    is_valid=False,
                    has_suitable_room=False,
                    total_enrollment=0,
                    max_room_capacity=0,
                    crns=crns,
                    warning_message=str(e),
                    can_proceed=False,
                )
        return results

