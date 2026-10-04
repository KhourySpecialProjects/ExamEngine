from collections import defaultdict
from dataclasses import dataclass, field

import networkx as nx

from src.domain.constants import BLOCKS_PER_DAY
from src.domain.models import Room, SchedulingDataset
from src.domain.services.conflict_detector import Conflict, ConflictDetector
from src.domain.services.constraint_evaluator import SoftConstraintEvaluator
from src.domain.value_objects import SchedulingState, SoftPenalty


# Internal ids are namespaced so that a combined label, a common label and a CRN
# that happen to share the same text never collide.
_COMBINED_PREFIX = "combined:"
_CRN_PREFIX = "crn:"
_COMMON_PREFIX = "common:"


def seats_fit(sizes_desc: list[int], capacities_desc: list[int]) -> bool:
    """True if every exam can have its own room at least its size.

    Both lists are sorted largest first. Rooms that fit an exam also fit every
    smaller exam, so a seating exists iff the k-th largest exam fits the k-th
    largest room for every k.
    """
    return len(sizes_desc) <= len(capacities_desc) and all(
        size <= capacity
        for size, capacity in zip(sizes_desc, capacities_desc, strict=False)
    )


@dataclass(frozen=True)
class UnscheduledGroup:
    """A combined group, common group or single section left unscheduled, and why."""

    kind: str  # "combined", "common" or "section"
    label: str  # group label, or the CRN for a section
    reason: str
    crns: list[str]

    def to_dict(self) -> dict[str, object]:
        """JSON form used in API responses and the saved conflict analysis."""
        return {
            "kind": self.kind,
            "group": self.label,
            "reason": self.reason,
            "crns": list(self.crns),
        }


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

    # Combined groups, common groups and single sections left unscheduled, with
    # the reason. A combined group inside an unscheduled common group is reported
    # once, under the common group.
    unscheduled_groups: list[UnscheduledGroup] = field(default_factory=list)
    # CRNs with neither slot nor room because they could not be seated
    unscheduled_crns: set[str] = field(default_factory=set)


class Scheduler:
    """
    Graph coloring based exam scheduler.

    This class orchestrates the scheduling workflow using domain objects:
    1. Build conflict graph from SchedulingDataset
    2. Color graph using coloring algorithm (time groups contracted)
    3. Assign time slots minimizing conflicts and penalties (common groups
       first); a slot is only used if every exam there still fits its own room
    4. Seat each slot's exams, largest first, in rooms at least their size

    Terminology:
    - Combined group (``merges``): CRNs sharing one exam — same slot, same room.
    - Common group (``common_groups``): CRNs sharing one slot but each room unit
      in its own room. A common group containing any member of a combined group
      contains the whole combined group.
    - Room unit: a combined group or a lone CRN; it gets exactly one room.
    - Time group: a common group (its room units) or a lone room unit; all its
      CRNs get the same slot.

    Rooms are never over capacity. Every exam is placed except combined groups,
    common groups and single sections that cannot be seated; those are left
    unscheduled as a whole, with a reason.
    """

    def __init__(
        self,
        dataset: SchedulingDataset,
        max_days: int = 7,
        blocks_per_day: int = BLOCKS_PER_DAY,
        student_max_per_day: int = 2,
        instructor_max_per_day: int = 2,
        weight_large_late: int = 1,
        weight_b2b_student: int = 6,
        weight_b2b_instructor: int = 2,
        merges: dict[str, list[str]] | None = None,
        common_groups: dict[str, list[str]] | None = None,
    ):
        """
        Initialize scheduler.

        Args:
            dataset: Scheduling dataset with courses, students, rooms
            max_days: Maximum number of days to schedule across
            blocks_per_day: Exam blocks used each day, the earliest first
                (1..BLOCKS_PER_DAY); later blocks are never assigned.
            student_max_per_day: Maximum exams per student per day
            instructor_max_per_day: Maximum exams per instructor per day
            weight_large_late: Penalty weight for large courses scheduled late
            weight_b2b_student: Penalty weight for student back-to-back exams
            weight_b2b_instructor: Penalty weight for instructor back-to-back exams
            merges: Combined groups, label → CRNs sharing one slot and one room.
            common_groups: Common groups, label → CRNs sharing one slot in
                distinct rooms.

        Raises:
            ValueError: blocks_per_day is outside 1..BLOCKS_PER_DAY, a CRN is in
                two combined groups or two common groups, or a combined group is
                split across common groups.
        """
        if not 1 <= blocks_per_day <= BLOCKS_PER_DAY:
            raise ValueError(
                f"blocks_per_day must be between 1 and {BLOCKS_PER_DAY}, "
                f"got {blocks_per_day}"
            )
        self.dataset = dataset
        self.max_days = max_days
        self.state = SchedulingState()
        self.merges = merges or {}
        self.common_groups = common_groups or {}
        # One entry per room name (last row wins, as when rooms are saved): a
        # name listed twice is still one room and can hold one exam at a time.
        self.rooms: list[Room] = list(
            {room.name: room for room in dataset.rooms}.values()
        )

        self._build_groups()

        # Time groups (keyed by internal id) and CRNs that will not be scheduled
        self.unscheduled_groups: dict[str, UnscheduledGroup] = {}
        self.unscheduled_crns: set[str] = set()
        self._identify_unschedulable_groups()

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
            (day, block) for day in range(max_days) for block in range(blocks_per_day)
        ]
        # Room capacities usable at each slot (blockouts applied), largest first,
        # and the room units placed at each slot. A group is only placed where
        # every unit at that slot can still have its own room at least its size.
        blockouts = dataset.room_blockouts
        self.slot_capacities: dict[tuple[int, int], list[int]] = {
            slot: sorted(
                (
                    room.capacity
                    for room in self.rooms
                    if slot not in blockouts.get(room.name, frozenset())
                ),
                reverse=True,
            )
            for slot in self.available_slots
        }
        self.slot_units: dict[tuple[int, int], list[str]] = defaultdict(list)

        # State
        self.graph: nx.Graph | None = None
        self.colors: dict[str, int] = {}
        self.assignments: dict[str, tuple[int, int]] = {}
        self.conflicts: list[Conflict] = []

    # ------------------------------------------------------------------
    # Group structure
    # ------------------------------------------------------------------

    def _build_groups(self) -> None:
        """Build room units and time groups from combined and common groups."""
        courses = self.dataset.courses

        crn_to_merge_label: dict[str, str] = {}
        for label, crns in self.merges.items():
            for crn in crns:
                if crn_to_merge_label.get(crn, label) != label:
                    raise ValueError(f"CRN {crn} appears in multiple merge groups")
                crn_to_merge_label[crn] = label

        crn_to_common_label: dict[str, str] = {}
        merge_to_common_label: dict[str, str] = {}
        for label, crns in self.common_groups.items():
            for crn in crns:
                if crn_to_common_label.get(crn, label) != label:
                    raise ValueError(f"CRN {crn} appears in multiple common groups")
                crn_to_common_label[crn] = label
                merge_label = crn_to_merge_label.get(crn)
                if merge_label is None:
                    continue
                other = merge_to_common_label.setdefault(merge_label, label)
                if other != label:
                    raise ValueError(
                        f"Combined group {merge_label} is split across common "
                        f"groups {other} and {label}"
                    )

        # Room units: combined groups (present members only), then lone CRNs
        self.room_units: dict[str, list[str]] = {}
        self.crn_to_room_unit: dict[str, str] = {}
        self.unit_to_merge_label: dict[str, str] = {}
        for label, crns in self.merges.items():
            present = [crn for crn in dict.fromkeys(crns) if crn in courses]
            if not present:
                continue
            unit = _COMBINED_PREFIX + label
            self.room_units[unit] = present
            self.unit_to_merge_label[unit] = label
            for crn in present:
                self.crn_to_room_unit[crn] = unit
        for crn in courses:
            if crn not in self.crn_to_room_unit:
                unit = _CRN_PREFIX + crn
                self.room_units[unit] = [crn]
                self.crn_to_room_unit[crn] = unit

        self.unit_enrollment: dict[str, int] = {
            unit: sum(self.dataset.get_enrollment_count(crn) for crn in crns)
            for unit, crns in self.room_units.items()
        }

        # Time groups: common groups (closed over combined groups), then lone units
        self.time_groups: dict[str, list[str]] = {}
        self.time_group_label: dict[str, str] = {}
        self.common_time_groups: set[str] = set()
        unit_to_time_group: dict[str, str] = {}
        for label, crns in self.common_groups.items():
            units = list(
                dict.fromkeys(
                    self.crn_to_room_unit[crn] for crn in crns if crn in courses
                )
            )
            if not units:
                continue
            tg = _COMMON_PREFIX + label
            self.time_groups[tg] = units
            self.time_group_label[tg] = label
            self.common_time_groups.add(tg)
            for unit in units:
                unit_to_time_group[unit] = tg
        for unit in self.room_units:
            if unit not in unit_to_time_group:
                self.time_groups[unit] = [unit]
                self.time_group_label[unit] = self.unit_to_merge_label.get(
                    unit, unit.removeprefix(_CRN_PREFIX)
                )
                unit_to_time_group[unit] = unit

        self.time_group_crns: dict[str, list[str]] = {
            tg: [crn for unit in units for crn in self.room_units[unit]]
            for tg, units in self.time_groups.items()
        }
        self.crn_to_time_group: dict[str, str] = {
            crn: unit_to_time_group[unit] for crn, unit in self.crn_to_room_unit.items()
        }

    def _mark_unscheduled(self, tg: str, reason: str) -> None:
        """Leave a whole time group unscheduled, recording why."""
        crns = self.time_group_crns[tg]
        if tg in self.common_time_groups:
            kind = "common"
        elif tg in self.unit_to_merge_label:
            kind = "combined"
        else:
            kind = "section"
        self.unscheduled_groups[tg] = UnscheduledGroup(
            kind=kind,
            label=self.time_group_label[tg],
            reason=reason,
            crns=sorted(crns),
        )
        self.unscheduled_crns.update(crns)

    def _identify_unschedulable_groups(self) -> None:
        """Mark groups and sections that no room inventory can ever seat."""
        rooms = self.rooms
        max_capacity = max((room.capacity for room in rooms), default=0)
        # Capacities can be parsed as floats; show whole seats.
        seats = f"{max_capacity:g}"

        for unit, crns in self.room_units.items():
            tg = self.crn_to_time_group[crns[0]]
            if unit in self.unit_to_merge_label or tg in self.common_time_groups:
                continue
            enrollment = self.unit_enrollment[unit]
            if not rooms:
                self._mark_unscheduled(tg, "No rooms are available")
            elif enrollment > max_capacity:
                self._mark_unscheduled(
                    tg, f"{enrollment} students; largest room seats {seats}"
                )
        oversized_units: dict[str, str] = {}
        for unit in self.unit_to_merge_label:
            enrollment = self.unit_enrollment[unit]
            if not rooms:
                oversized_units[unit] = "No rooms are available"
            elif enrollment > max_capacity:
                oversized_units[unit] = (
                    f"Combined enrollment {enrollment} exceeds the largest room "
                    f"capacity {seats}"
                )
            else:
                continue
            tg = self.crn_to_time_group[self.room_units[unit][0]]
            if tg not in self.common_time_groups:
                self._mark_unscheduled(tg, oversized_units[unit])

        for tg in self.common_time_groups:
            units = self.time_groups[tg]
            if not rooms:
                self._mark_unscheduled(tg, "No rooms are available")
                continue
            oversized = next((u for u in units if u in oversized_units), None)
            if oversized is not None:
                self._mark_unscheduled(
                    tg,
                    f"Contains combined group "
                    f"{self.unit_to_merge_label[oversized]} with "
                    f"{self.unit_enrollment[oversized]} students, more than the "
                    f"largest room capacity {seats}",
                )
            elif self._pack_units(units, rooms) is None:
                self._mark_unscheduled(
                    tg,
                    f"Its {len(units)} exams cannot be seated in {len(units)} "
                    "distinct rooms at the same time",
                )

    def _pack_units(self, units: list[str], rooms: list[Room]) -> dict[str, str] | None:
        """Give each room unit its own room, or None if impossible.

        Greedy: units by enrollment (largest first), each into the smallest unused
        room that fits.
        """
        free = sorted(rooms, key=lambda r: r.capacity)
        plan: dict[str, str] = {}
        for unit in sorted(units, key=lambda u: self.unit_enrollment[u], reverse=True):
            enrollment = self.unit_enrollment[unit]
            idx = next(
                (i for i, r in enumerate(free) if r.capacity >= enrollment), None
            )
            if idx is None:
                return None
            plan[unit] = free.pop(idx).name
        return plan

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------

    def schedule(self, prioritize_large_courses: bool = False) -> ScheduleResult:
        """
        Execute complete scheduling workflow.

        Returns ScheduleResult with all assignments and detected conflicts.
        """
        # Handle empty dataset
        if not self.dataset.courses:
            return ScheduleResult(
                assignments={},
                room_assignments={},
                conflicts=[],
                colors={},
                unscheduled_groups=list(self.unscheduled_groups.values()),
                unscheduled_crns=set(self.unscheduled_crns),
            )

        self._build_conflict_graph()
        self._color_graph()
        self._assign_time_slots(prioritize_large_courses)
        room_assignments = self._assign_rooms()

        return ScheduleResult(
            assignments=dict(self.assignments),
            room_assignments=room_assignments,
            conflicts=list(self.conflicts),
            colors=dict(self.colors),
            unscheduled_groups=list(self.unscheduled_groups.values()),
            unscheduled_crns=set(self.unscheduled_crns),
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

        for _student_id, student in self.dataset.students.items():
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

    def _contract_for_coloring(self) -> tuple[nx.Graph, dict[str, str]]:
        """
        Contract each multi-CRN time group into a single virtual node for coloring.

        In graph coloring an edge means "must be different colors". CRNs of one
        time group (combined or common) need the opposite guarantee — same color —
        so they must NOT appear as separate nodes connected by edges. Instead each
        group is replaced by one virtual node that inherits the union of all
        members' external edges (max weight). Edges inside the group are dropped.

        Returns:
            contracted: copy of the conflict graph with time groups collapsed
            virtual_node_map: virtual_node_id -> time group id (for color expansion)
        """
        contracted = self.graph.copy()
        virtual_node_map: dict[str, str] = {}

        for tg, crns in self.time_group_crns.items():
            if len(crns) < 2:
                continue
            members = set(crns)

            # Unique virtual node id — prefix avoids collision with CRN strings
            virtual_id = f"__vgroup__{tg}"
            virtual_node_map[virtual_id] = tg

            # Union of external edges: for each neighbor outside the group keep
            # the maximum edge weight seen from any member.
            external_edges: dict[str, int] = {}
            for crn in crns:
                for neighbor, data in contracted[crn].items():
                    if neighbor not in members:
                        weight = data.get("weight", 1)
                        external_edges[neighbor] = max(
                            external_edges.get(neighbor, 0), weight
                        )

            contracted.remove_nodes_from(crns)
            contracted.add_node(
                virtual_id,
                size=sum(self.dataset.get_enrollment_count(crn) for crn in crns),
            )
            for neighbor, weight in external_edges.items():
                if neighbor in contracted.nodes:
                    contracted.add_edge(virtual_id, neighbor, weight=weight)

        return contracted, virtual_node_map

    def _color_graph(self):
        """Apply DSATUR graph coloring via node contraction for time groups."""
        if self.graph is None or self.graph.number_of_nodes() == 0:
            raise RuntimeError("Build graph before coloring")

        # Contract time groups so DSATUR sees each group as a single atomic node.
        contracted, virtual_node_map = self._contract_for_coloring()

        # https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.coloring.greedy_color.html
        contracted_colors = nx.coloring.greedy_color(contracted, strategy="DSATUR")

        # Expand: virtual node color → all CRNs in its time group.
        for node, color in contracted_colors.items():
            if node in virtual_node_map:
                for crn in self.time_group_crns[virtual_node_map[node]]:
                    self.colors[crn] = color
            else:
                self.colors[node] = color

    def _assign_time_slots(self, prioritize_large: bool):
        """Assign each time group to a time slot (common groups first)."""
        if not self.colors:
            raise RuntimeError("Color graph before scheduling")

        placed: set[str] = set()

        for crn in self._get_course_ordering(prioritize_large):
            tg = self.crn_to_time_group[crn]
            if tg in placed or tg in self.unscheduled_groups:
                continue

            choice = self._find_best_slot(crn)
            if choice is None:
                units = self.time_groups[tg]
                if len(units) == 1:
                    reason = (
                        "No time block has a free, unblocked room large enough "
                        f"for its {self.unit_enrollment[units[0]]} students"
                    )
                else:
                    reason = (
                        f"No time block has {len(units)} free, unblocked rooms "
                        "large enough for its exams"
                    )
                self._mark_unscheduled(tg, reason)
                continue

            (day, block), slot_conflicts = choice
            placed.add(tg)
            self.conflicts.extend(slot_conflicts)
            for member in self.time_group_crns[tg]:
                self.assignments[member] = (day, block)
                self.state.record_placement(member, day, block, self.dataset)
            self.slot_units[(day, block)].extend(self.time_groups[tg])

    def _get_course_ordering(self, prioritize_large: bool) -> list[str]:
        """
        Get ordering of courses for scheduling, one representative per time group.

        Common groups come first (most room units, then largest total enrollment),
        so their room units claim seats before anything else competes for them. The
        remaining time groups follow the color-based (or size-based) ordering.
        """
        common_reps: list[str] = []
        other_reps: list[str] = []
        seen: set[str] = set()

        for crn in self.colors:
            tg = self.crn_to_time_group[crn]
            if tg in seen:
                continue
            seen.add(tg)
            if tg in self.common_time_groups:
                common_reps.append(crn)
            else:
                other_reps.append(crn)

        common_reps.sort(
            key=lambda crn: (
                len(self.time_groups[self.crn_to_time_group[crn]]),
                self._get_total_enrollment(crn),
            ),
            reverse=True,
        )

        if prioritize_large:
            return common_reps + sorted(
                other_reps,
                key=lambda crn: self._get_total_enrollment(crn),
                reverse=True,
            )

        # Group by color
        color_groups = defaultdict(list)
        for crn in other_reps:
            color_groups[self.colors[crn]].append(crn)

        ordered_colors = sorted(
            color_groups.keys(),
            key=lambda c: sum(
                self._get_total_enrollment(crn) for crn in color_groups[c]
            ),
            reverse=True,
        )

        ordered_crns = list(common_reps)
        for color in ordered_colors:
            ordered_crns.extend(
                sorted(
                    color_groups[color],
                    key=lambda crn: self._get_total_enrollment(crn),
                    reverse=True,
                )
            )

        return ordered_crns

    def _get_total_enrollment(self, crn: str) -> int:
        """Get total enrollment of the CRN's whole time group."""
        tg = self.crn_to_time_group.get(crn)
        if tg is None:
            return self.dataset.get_enrollment_count(crn)
        return sum(self.unit_enrollment[unit] for unit in self.time_groups[tg])

    def _find_best_slot(
        self, crn: str
    ) -> tuple[tuple[int, int], list[Conflict]] | None:
        """Find the slot with minimum conflicts and penalties for the CRN's group.

        Conflicts and penalties are summed over every CRN in the time group. A
        slot is admissible only if every room unit already there plus the group's
        own can each have a distinct, unblocked room at least its size.

        Returns:
            (slot, conflicts), or None if no slot is admissible.
        """
        tg = self.crn_to_time_group[crn]
        crns_to_check = self.time_group_crns[tg]
        units = self.time_groups[tg]

        candidates = []

        for day, block in self.available_slots:
            if not self._units_fit((day, block), units):
                continue

            all_conflicts = []
            for check_crn in crns_to_check:
                all_conflicts.extend(
                    self.conflict_detector.check_placement(check_crn, day, block)
                )

            # Sum soft-constraint penalties across every CRN in the group so that
            # back-to-back and instructor-load costs are accounted for all members,
            # not just the representative CRN.
            combined = SoftPenalty()
            for check_crn in crns_to_check:
                p = self.constraint_evaluator.evaluate(check_crn, day, block)
                combined.large_course_late += p.large_course_late
                combined.back_to_back_students += p.back_to_back_students
                combined.back_to_back_instructors += p.back_to_back_instructors
                combined.instructor_load += p.instructor_load
                combined.slot_seat_load += p.slot_seat_load
                combined.slot_exam_count += p.slot_exam_count

            key = (len(all_conflicts), combined.as_tuple(day, block))
            candidates.append((key, day, block, all_conflicts))

        if not candidates:
            return None

        _, day, block, conflicts = min(candidates, key=lambda x: x[0])
        conflicts = conflicts + self._intra_group_conflicts(tg, day, block)
        return (day, block), conflicts

    def _units_fit(self, slot: tuple[int, int], units: list[str]) -> bool:
        """True if ``units`` can join the room units already placed at ``slot``."""
        sizes = sorted(
            (self.unit_enrollment[u] for u in (*self.slot_units[slot], *units)),
            reverse=True,
        )
        return seats_fit(sizes, self.slot_capacities[slot])

    def _intra_group_conflicts(self, tg: str, day: int, block: int) -> list[Conflict]:
        """Double-bookings forced by a student sitting 2+ room units of one group.

        Such students must be in two rooms at once wherever the group is placed;
        each extra room unit is reported against the student's first one.
        """
        units = self.time_groups[tg]
        if len(units) < 2:
            return []

        students_by_crn = self.dataset.students_by_crn
        first_crn_by_student: dict[str, str] = {}
        conflicts: list[Conflict] = []
        for unit in units:
            seen_in_unit: set[str] = set()
            for crn in self.room_units[unit]:
                for student_id in students_by_crn.get(crn, frozenset()):
                    if student_id in seen_in_unit:
                        continue
                    seen_in_unit.add(student_id)
                    first = first_crn_by_student.setdefault(student_id, crn)
                    if first == crn:
                        continue
                    conflicts.append(
                        Conflict(
                            conflict_type="student_double_book",
                            entity_id=student_id,
                            crn=crn,
                            conflicting_crn=first,
                            day=day,
                            block=block,
                        )
                    )
        return conflicts

    def _assign_rooms(self) -> dict[str, str]:
        """Seat every placed room unit, slot by slot, largest unit first.

        Slots were only chosen where their units fit (``_units_fit``), so every
        unit gets a distinct, unblocked room at least its size; no room is ever
        over capacity.

        Returns:
            CRN → room name for every placed course.
        """
        blockouts = self.dataset.room_blockouts
        room_assignments: dict[str, str] = {}
        for slot, units in self.slot_units.items():
            rooms = [
                room
                for room in self.rooms
                if slot not in blockouts.get(room.name, frozenset())
            ]
            plan = self._pack_units(units, rooms)
            if plan is None:
                raise RuntimeError(f"Exams placed at slot {slot} do not fit its rooms")
            for unit, room_name in plan.items():
                for crn in self.room_units[unit]:
                    room_assignments[crn] = room_name
        return room_assignments
