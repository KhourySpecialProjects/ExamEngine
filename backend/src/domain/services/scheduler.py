from collections import defaultdict
from dataclasses import dataclass, field

import networkx as nx

from src.domain.constants import BLOCKS_PER_DAY
from src.domain.models import SchedulingDataset
from src.domain.services.conflict_detector import Conflict, ConflictDetector
from src.domain.services.constraint_evaluator import SoftConstraintEvaluator
from src.domain.value_objects import SchedulingState


@dataclass
class ScheduleResult:
    """
    Complete output of the scheduling algorithm.

    This is a simple data container - no methods, no presentation logic.
    The service layer reads these fields directly.
    """

    # Core scheduling output
    assignments: dict[str, tuple[int, int]]  # CRN → (day_idx, block_idx)
    room_assignments: dict[str, str]  # CRN → room_name
    conflicts: list[Conflict]  # Hard constraint violations
    colors: dict[str, int]  # CRN → DSATUR color (for debugging)

    # Metadata needed for saving/display (populated by scheduler)
    course_sizes: dict[str, int] = field(default_factory=dict)  # CRN → enrollment
    course_codes: dict[str, str] = field(default_factory=dict)  # CRN → "CS 4535"
    room_capacities: dict[str, int] = field(
        default_factory=dict
    )  # room_name → capacity
    instructors_by_crn: dict[str, set[str]] = field(
        default_factory=dict
    )  # CRN → {names}

    # Unplaced courses (empty if all placed)
    unassigned: set[str] = field(default_factory=set)
    unscheduled_merges: set[str] = field(default_factory=set)  # merge_group_ids


class Scheduler:
    """
    Graph coloring based exam scheduler.

    This class orchestrates the scheduling workflow using domain objects:
    1. Build conflict graph from SchedulingDataset
    2. Color graph using coloring algorithm
    3. Assign time slots minimizing conflicts and penalties
    4. Assign rooms based on capacity

    All exams are always placed.
    """

    def __init__(
        self,
        dataset: SchedulingDataset,
        max_days: int = 7,
        student_max_per_day: int = 2,
        instructor_max_per_day: int = 2,
        weight_large_late: int = 1,
        weight_b2b_student: int = 6,
        weight_b2b_instructor: int = 2,
        merges: dict[str, list[str]] | None = None,
    ):
        """
        Initialize scheduler.

        Args:
            dataset: Scheduling dataset with courses, students, rooms
            max_days: Maximum number of days to schedule across
            student_max_per_day: Maximum exams per student per day
            instructor_max_per_day: Maximum exams per instructor per day
            weight_large_late: Penalty weight for large courses scheduled late
            weight_b2b_student: Penalty weight for student back-to-back exams
            weight_b2b_instructor: Penalty weight for instructor back-to-back exams
            merges: Dictionary mapping merge_group_id to list of CRNs to merge together
                   Format: {"merge_group_1": ["CRN1", "CRN2"], "merge_group_2": ["CRN3", "CRN4"]}
        """
        self.dataset = dataset
        self.max_days = max_days
        self.state = SchedulingState()
        self.merges = merges or {}

        # Build reverse mapping: CRN -> merge_group_id (for quick lookup)
        self.crn_to_merge_group: dict[str, str] = {}
        for merge_id, crns in self.merges.items():
            for crn in crns:
                if crn in self.crn_to_merge_group:
                    raise ValueError(f"CRN {crn} appears in multiple merge groups")
                self.crn_to_merge_group[crn] = merge_id

        # Track merges without suitable rooms (will not be scheduled)
        self.unscheduled_merges: set[str] = set()
        self._identify_unscheduled_merges()

        # Initialize focused services
        self.conflict_detector = ConflictDetector(
            dataset, self.state, student_max_per_day, instructor_max_per_day
        )
        self.constraint_evaluator = SoftConstraintEvaluator(
            dataset,
            self.state,
            weight_large_late,
            weight_b2b_student,
            weight_b2b_instructor,
        )

        # Build available time slots
        self.available_slots = [
            (day, block) for day in range(max_days) for block in range(BLOCKS_PER_DAY)
        ]

        # State
        self.graph: nx.Graph | None = None
        self.colors: dict[str, int] = {}
        self.assignments: dict[str, tuple[int, int]] = {}
        self.conflicts: list[Conflict] = []

    def _identify_unscheduled_merges(self):
        """Identify merge groups that don't have suitable rooms."""
        if not self.dataset.rooms:
            # No rooms available - mark all merges as unscheduled
            self.unscheduled_merges = set(self.merges.keys())
            return

        max_room_capacity = max(room.capacity for room in self.dataset.rooms)

        for merge_id, crns in self.merges.items():
            # Calculate total enrollment for this merge group
            total_enrollment = sum(
                self.dataset.get_enrollment_count(crn)
                for crn in crns
                if crn in self.dataset.courses
            )

            # If enrollment exceeds max room capacity, mark as unscheduled
            if total_enrollment > max_room_capacity:
                self.unscheduled_merges.add(merge_id)

    def schedule(self, prioritize_large_courses: bool = False) -> ScheduleResult:
        """
        Execute complete scheduling workflow.

        Returns ScheduleResult with all assignments and detected conflicts.
        """
        self._build_conflict_graph()
        self._color_graph()
        self._assign_time_slots(prioritize_large_courses)
        room_assignments = self._assign_rooms()

        return ScheduleResult(
            assignments=dict(self.assignments),
            room_assignments=room_assignments,
            conflicts=list(self.conflicts),
            colors=dict(self.colors),
            unscheduled_merges=self.unscheduled_merges,
        )

    def _build_conflict_graph(self):
        """Build conflict graph using student-centric approach."""

        self.graph = nx.Graph()

        # Step 1: Add nodes
        for crn, course in self.dataset.courses.items():
            self.graph.add_node(
                crn,
                course_code=course.course_code,
                size=course.enrollment_count,
            )

        # Step 2: Build edges from students
        edge_weights: dict[tuple[str, str], int] = {}

        student_count = 0
        for _student_id, student in self.dataset.students.items():
            student_count += 1
            # Get courses this student is enrolled in
            student_courses = [
                crn for crn in student.enrolled_crns if crn in self.dataset.courses
            ]

            # Create edges for all pairs of this student's courses
            for i in range(len(student_courses)):
                for j in range(i + 1, len(student_courses)):
                    crn1, crn2 = student_courses[i], student_courses[j]
                    edge_key = (crn1, crn2) if crn1 < crn2 else (crn2, crn1)
                    edge_weights[edge_key] = edge_weights.get(edge_key, 0) + 1

        # Step 3: Add edges to graph
        for (crn1, crn2), weight in edge_weights.items():
            self.graph.add_edge(crn1, crn2, weight=weight)

        # Step 4: Force edges between merged CRNs (ensure they get same color)
        # All CRNs in a merge group must be scheduled together, so they need edges
        for _merge_id, crns in self.merges.items():
            # Add edges between all pairs in the merge group
            for i in range(len(crns)):
                for j in range(i + 1, len(crns)):
                    crn1, crn2 = crns[i], crns[j]
                    # Only add edge if both CRNs exist in dataset
                    if crn1 in self.dataset.courses and crn2 in self.dataset.courses:
                        # Use high weight to ensure they're strongly connected
                        if not self.graph.has_edge(crn1, crn2):
                            self.graph.add_edge(
                                crn1, crn2, weight=9999
                            )  # High weight for merged courses
                        else:
                            # Increase existing edge weight
                            current_weight = self.graph[crn1][crn2].get("weight", 1)
                            self.graph[crn1][crn2]["weight"] = max(current_weight, 9999)

    def _color_graph(self):
        """Apply DSATUR graph coloring."""
        if self.graph is None or self.graph.number_of_nodes() == 0:
            raise RuntimeError("Build graph before coloring")

        # https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.coloring.greedy_color.html#networkx.algorithms.coloring.greedy_color
        # TODO dynamic strategy?
        self.colors = nx.coloring.greedy_color(self.graph, strategy="DSATUR")

        # Ensure all merged CRNs have the same color
        # (They should already due to forced edges, but enforce it explicitly)
        for _merge_id, crns in self.merges.items():
            # Get colors for all CRNs in this merge group
            merge_colors = {
                crn: self.colors.get(crn)
                for crn in crns
                if crn in self.colors and crn in self.dataset.courses
            }

            if not merge_colors:
                continue

            # Use the color of the first CRN for all merged CRNs
            # (or the most common color if they differ)
            if merge_colors:
                # Find most common color, or use first
                color_counts = {}
                for color in merge_colors.values():
                    color_counts[color] = color_counts.get(color, 0) + 1
                target_color = max(color_counts.items(), key=lambda x: x[1])[0]

                # Assign same color to all merged CRNs
                for crn in crns:
                    if crn in self.dataset.courses:
                        self.colors[crn] = target_color

    def _assign_time_slots(self, prioritize_large: bool):
        """Assign each course to a time slot."""
        if not self.colors:
            raise RuntimeError("Color graph before scheduling")

        # Get the ordering
        ordered_crns = self._get_course_ordering(prioritize_large)

        # Track which merge groups have been assigned
        assigned_merge_groups: set[str] = set()

        # Assign each course to best available slot
        for _idx, crn in enumerate(ordered_crns):
            # Skip if this CRN is part of a merge group that's already been assigned
            merge_group = self.crn_to_merge_group.get(crn)
            if merge_group and merge_group in assigned_merge_groups:
                continue  # Already assigned as part of merge group

            # Skip merges without suitable rooms (they won't be scheduled)
            if merge_group and merge_group in self.unscheduled_merges:
                continue  # Will be saved as unscheduled

            (day, block), slot_conflicts = self._find_best_slot(crn)
            self.assignments[crn] = (day, block)
            self.conflicts.extend(slot_conflicts)

            self.state.record_placement(crn, day, block, self.dataset)

            # If this CRN is part of a merge group, assign all others in the group to the same slot
            if merge_group:
                assigned_merge_groups.add(merge_group)
                for other_crn in self.merges[merge_group]:
                    if other_crn != crn and other_crn in self.dataset.courses:
                        self.assignments[other_crn] = (day, block)
                        # Record placement for each merged CRN
                        self.state.record_placement(other_crn, day, block, self.dataset)

    def _get_course_ordering(self, prioritize_large: bool) -> list[str]:
        """
        Get ordering of courses for scheduling.

        For merged courses, only include one representative CRN per merge group
        (the others will be assigned automatically).
        """
        # Filter out CRNs that are part of merge groups (except the first one)
        crns_to_order = []
        seen_merge_groups: set[str] = set()

        for crn in self.colors.keys():
            merge_group = self.crn_to_merge_group.get(crn)
            if merge_group:
                if merge_group not in seen_merge_groups:
                    # Include first CRN from each merge group
                    crns_to_order.append(crn)
                    seen_merge_groups.add(merge_group)
                # Skip other CRNs in the merge group
            else:
                # Not part of a merge group, include it
                crns_to_order.append(crn)

        if prioritize_large:
            ordered_crns = sorted(
                crns_to_order,
                key=lambda crn: self._get_total_enrollment(crn),
                reverse=True,
            )
            return ordered_crns

        # Group by color
        color_groups = defaultdict(list)
        for crn in crns_to_order:
            color = self.colors.get(crn)
            if color is not None:
                color_groups[color].append(crn)

        ordered_colors = sorted(
            color_groups.keys(),
            key=lambda c: sum(
                self._get_total_enrollment(crn) for crn in color_groups[c]
            ),
            reverse=True,
        )

        ordered_crns = []
        for color in ordered_colors:
            crns = sorted(
                color_groups[color],
                key=lambda crn: self._get_total_enrollment(crn),
                reverse=True,
            )
            ordered_crns.extend(crns)

        return ordered_crns

    def _get_total_enrollment(self, crn: str) -> int:
        """Get total enrollment for a CRN, including merged CRNs if applicable."""
        merge_group = self.crn_to_merge_group.get(crn)
        if merge_group:
            # Sum enrollment for all CRNs in merge group
            return sum(
                self.dataset.get_enrollment_count(m_crn)
                for m_crn in self.merges[merge_group]
                if m_crn in self.dataset.courses
            )
        return self.dataset.get_enrollment_count(crn)

    def _find_best_slot(self, crn: str) -> tuple[tuple[int, int], list[Conflict]]:
        """Find the slot with minimum conflicts and penalties for this course."""
        # Get all CRNs that need to be scheduled together (merge group or just this CRN)
        crns_to_check = [crn]
        merge_group = self.crn_to_merge_group.get(crn)
        if merge_group:
            # Check all CRNs in the merge group
            crns_to_check = [
                m_crn
                for m_crn in self.merges[merge_group]
                if m_crn in self.dataset.courses
            ]

        candidates = []

        for day, block in self.available_slots:
            # Check conflicts for all CRNs in the merge group
            all_conflicts = []
            for check_crn in crns_to_check:
                conflicts = self.conflict_detector.check_placement(
                    check_crn, day, block
                )
                all_conflicts.extend(conflicts)

            # Use the first CRN for penalty evaluation (enrollment will be summed in room assignment)
            penalty = self.constraint_evaluator.evaluate(crn, day, block)

            key = (len(all_conflicts), penalty.as_tuple(day, block))
            candidates.append((key, day, block, all_conflicts))

        _, day, block, conflicts = min(candidates, key=lambda x: x[0])

        return (day, block), conflicts

    def _assign_rooms(self) -> dict[str, str]:
        """Assign rooms to courses based on capacity."""
        room_assignments = {}
        used_rooms: dict[tuple[int, int], set[str]] = defaultdict(set)

        # Sort rooms by capacity
        rooms_by_capacity = sorted(self.dataset.rooms, key=lambda r: r.capacity)

        # Track which merge groups have been assigned rooms
        assigned_merge_groups: set[str] = set()

        for crn, (day, block) in self.assignments.items():
            # Skip if this CRN is part of a merge group that's already been assigned a room
            merge_group = self.crn_to_merge_group.get(crn)
            if merge_group and merge_group in assigned_merge_groups:
                continue  # Room already assigned to this merge group

            # Skip merges without suitable rooms (they won't get room assignments)
            if merge_group and merge_group in self.unscheduled_merges:
                continue  # Will be saved without room assignment

            slot = (day, block)

            # Calculate enrollment: sum for merged courses, single for others
            if merge_group:
                # Sum enrollment for all CRNs in merge group
                enrollment = sum(
                    self.dataset.get_enrollment_count(m_crn)
                    for m_crn in self.merges[merge_group]
                    if m_crn in self.dataset.courses
                )
                assigned_merge_groups.add(merge_group)
            else:
                enrollment = self.dataset.get_enrollment_count(crn)

            # Find smallest room that fits and is available
            room = None
            for r in rooms_by_capacity:
                if r.capacity >= enrollment and r.name not in used_rooms[slot]:
                    room = r
                    break

            # Fallback: largest available room
            if room is None:
                for r in reversed(rooms_by_capacity):
                    if r.name not in used_rooms[slot]:
                        room = r
                        break

            # Last resort: reuse largest room
            if room is None:
                room = rooms_by_capacity[-1] if rooms_by_capacity else None

            if room is None:
                # No rooms available (shouldn't happen, but handle gracefully)
                continue

            # Assign room to this CRN and all others in its merge group
            if merge_group:
                for m_crn in self.merges[merge_group]:
                    if m_crn in self.dataset.courses:
                        room_assignments[m_crn] = room.name
            else:
                room_assignments[crn] = room.name

            used_rooms[slot].add(room.name)

        return room_assignments
