"""
Services for validating combined exams (course merges) and common exams.

Combined exams merge CRNs into one exam (same time, same room); feasibility
depends on room capacity. Common exams put CRNs in the same time block but in
different rooms; feasibility depends on seating every room unit at once.
"""

from collections import Counter
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
        total_enrollment = sum(self.dataset.get_enrollment_count(crn) for crn in crns)

        # Find maximum room capacity
        max_room_capacity = (
            max((room.capacity for room in self.dataset.rooms), default=0)
            if self.dataset.rooms
            else 0
        )

        # Check if merge fits
        is_valid = total_enrollment <= max_room_capacity
        has_suitable_room = (
            max_room_capacity > 0 and total_enrollment <= max_room_capacity
        )

        # Generate warning message if needed
        warning_message = None
        suggested_action = None

        if not has_suitable_room:
            if max_room_capacity == 0:
                warning_message = (
                    "No rooms available in dataset. Merged courses cannot be scheduled."
                )
                suggested_action = (
                    "Add rooms to the dataset or remove this merge group."
                )
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


def expand_room_units(crns: list[str], merges: dict[str, list[str]]) -> list[list[str]]:
    """
    Apply the combined-group closure to a common group's listed CRNs.

    Each listed CRN becomes its whole combined group (one room unit) if it
    belongs to one, otherwise a room unit of its own. Units keep the order in
    which their first CRN is listed; listing several members of the same
    combined group yields that group once.
    """
    merge_of = {crn: label for label, members in merges.items() for crn in members}
    units: list[list[str]] = []
    seen_merges: set[str] = set()
    seen_crns: set[str] = set()
    for crn in crns:
        label = merge_of.get(crn)
        if label is not None:
            if label not in seen_merges:
                seen_merges.add(label)
                units.append(list(merges[label]))
        elif crn not in seen_crns:
            seen_crns.add(crn)
            units.append([crn])
    return units


def find_unseated_unit(sizes: list[int], capacities: list[int]) -> int | None:
    """
    Check whether every unit can get its own room at the same time.

    Greedy: largest unit first, each into the smallest free room that fits.
    This is optimal for single-threshold matching, so a failure means no
    assignment exists.

    Returns:
        Index (into `sizes`) of the first unit left without a room, or None if
        all units are seated.
    """
    free = sorted(capacities)
    for index in sorted(range(len(sizes)), key=lambda i: sizes[i], reverse=True):
        room = next((r for r, cap in enumerate(free) if cap >= sizes[index]), None)
        if room is None:
            return index
        free.pop(room)
    return None


@dataclass
class CommonExamValidationResult:
    """Result of validating one common exam group."""

    crns: list[str]
    """CRNs as listed for the group."""
    room_units: list[list[str]]
    """Room units after combined-group closure; each needs its own room."""
    unit_enrollments: list[int]
    """Enrollment of each room unit, aligned with `room_units`."""
    fits_rooms: bool
    """True if all room units can be seated in distinct rooms at once."""
    overlapping_students: int
    """Students enrolled in two or more room units of this group."""
    warning_message: str | None = None

    @property
    def total_enrollment(self) -> int:
        """Sum of all room unit enrollments."""
        return sum(self.unit_enrollments)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "is_valid": self.fits_rooms,
            "room_units": len(self.room_units),
            "room_unit_crns": self.room_units,
            "unit_enrollments": self.unit_enrollments,
            "total_enrollment": self.total_enrollment,
            "overlapping_students": self.overlapping_students,
            "crns": self.crns,
            "warning_message": self.warning_message,
            # Infeasible groups may still be saved; they stay unscheduled.
            "can_proceed": True,
        }


class CommonExamValidator:
    """Validates common exam groups against a dataset and its combined groups."""

    def __init__(self, dataset: SchedulingDataset, merges: dict[str, list[str]]):
        """
        Initialize validator.

        Args:
            dataset: The scheduling dataset containing courses, rooms, students
            merges: Combined groups (label -> CRNs) used for closure
        """
        self.dataset = dataset
        self.merges = merges

    def validate(self, crns: list[str]) -> CommonExamValidationResult:
        """
        Validate one common group.

        Groups whose room units cannot all be seated at once are returned with
        `fits_rooms=False` (the scheduler leaves them unscheduled).

        Raises:
            ValueError: If a CRN is unknown or the group has fewer than 2 room
                units after closure.
        """
        missing = [crn for crn in crns if crn not in self.dataset.courses]
        if missing:
            raise ValueError(f"CRNs not found in dataset: {missing}")

        units = expand_room_units(crns, self.merges)
        if len(units) < 2:
            raise ValueError(
                "needs at least 2 room units (separate CRNs or combined groups) "
                f"after including combined groups (found {len(units)})"
            )

        sizes = [
            sum(self.dataset.get_enrollment_count(crn) for crn in unit)
            for unit in units
        ]
        capacities = [room.capacity for room in self.dataset.rooms]
        unseated = find_unseated_unit(sizes, capacities)

        unit_of_student: Counter[str] = Counter()
        for unit in units:
            students: set[str] = set()
            for crn in unit:
                students |= self.dataset.students_by_crn.get(crn, frozenset())
            unit_of_student.update(students)
        overlapping = sum(1 for count in unit_of_student.values() if count > 1)

        warning = None
        if unseated is not None:
            warning = (
                f"Needs {len(units)} rooms at once (room unit sizes "
                f"{sorted(sizes, reverse=True)}) but the {len(capacities)} rooms "
                f"cannot seat them simultaneously: room unit {units[unseated]} "
                f"({sizes[unseated]} students) has no free room large enough. "
                "The whole group will be left unscheduled."
            )
        elif overlapping:
            warning = (
                f"{overlapping} students are enrolled in more than one section of "
                "this common group and will have simultaneous exams."
            )

        return CommonExamValidationResult(
            crns=crns,
            room_units=units,
            unit_enrollments=sizes,
            fits_rooms=unseated is None,
            overlapping_students=overlapping,
            warning_message=warning,
        )

    def cross_group_problems(self, groups: dict[str, list[str]]) -> list[str]:
        """
        Problems spanning groups: a CRN listed in several common groups, or a
        combined group whose members are listed in different common groups.
        """
        problems: list[str] = []
        groups_of_crn: dict[str, list[str]] = {}
        for label, crns in groups.items():
            for crn in crns:
                labels = groups_of_crn.setdefault(crn, [])
                if label not in labels:
                    labels.append(label)
        for crn, labels in groups_of_crn.items():
            if len(labels) > 1:
                listed = ", ".join(f"'{g}'" for g in labels)
                problems.append(f"CRN {crn} is in multiple common groups: {listed}")

        for merge_label, members in self.merges.items():
            labels: list[str] = []
            for crn in members:
                for label in groups_of_crn.get(crn, []):
                    if label not in labels:
                        labels.append(label)
            if len(labels) > 1:
                listed = ", ".join(f"'{g}'" for g in labels)
                problems.append(
                    f"combined group '{merge_label}' is split across common "
                    f"groups {listed}; a combined group must stay in one "
                    "common group"
                )
        return problems
