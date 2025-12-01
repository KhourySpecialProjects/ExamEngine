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
    ):
        self.dataset = dataset
        self.max_days = max_days
        self.state = SchedulingState()

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

    def _color_graph(self):
        """Apply DSATUR graph coloring."""
        if self.graph is None or self.graph.number_of_nodes() == 0:
            raise RuntimeError("Build graph before coloring")

        # https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.coloring.greedy_color.html#networkx.algorithms.coloring.greedy_color
        # TODO dynamic strategy?
        self.colors = nx.coloring.greedy_color(self.graph, strategy="DSATUR")

    def _assign_time_slots(self, prioritize_large: bool):
        """Assign each course to a time slot."""
        if not self.colors:
            raise RuntimeError("Color graph before scheduling")

        # Get the ordering
        ordered_crns = self._get_course_ordering(prioritize_large)

        # Assign each course to best available slot
        for _idx, crn in enumerate(ordered_crns):
            (day, block), slot_conflicts = self._find_best_slot(crn)
            self.assignments[crn] = (day, block)
            self.conflicts.extend(slot_conflicts)

            self.state.record_placement(crn, day, block, self.dataset)

    def _get_course_ordering(self, prioritize_large: bool) -> list[str]:
        if prioritize_large:
            ordered_crns = sorted(
                self.colors.keys(),
                key=lambda crn: self.dataset.get_enrollment_count(crn),
                reverse=True,
            )
            return ordered_crns

        # Group by color
        color_groups = defaultdict(list)
        for crn, color in self.colors.items():
            color_groups[color].append(crn)

        ordered_colors = sorted(
            color_groups.keys(),
            key=lambda c: sum(
                self.dataset.get_enrollment_count(crn) for crn in color_groups[c]
            ),
            reverse=True,
        )

        ordered_crns = []
        for color in ordered_colors:
            crns = sorted(
                color_groups[color],
                key=lambda crn: self.dataset.get_enrollment_count(crn),
                reverse=True,
            )
            ordered_crns.extend(crns)

        return ordered_crns

    def _find_best_slot(self, crn: str) -> tuple[tuple[int, int], list[Conflict]]:
        """Find the slot with minimum conflicts and penalties for this course."""
        candidates = []

        for day, block in self.available_slots:
            conflicts = self.conflict_detector.check_placement(crn, day, block)

            penalty = self.constraint_evaluator.evaluate(crn, day, block)

            key = (len(conflicts), penalty.as_tuple(day, block))
            candidates.append((key, day, block, conflicts))

        _, day, block, conflicts = min(candidates, key=lambda x: x[0])

        return (day, block), conflicts

    def _assign_rooms(self) -> dict[str, str]:
        """Assign rooms to courses based on capacity."""
        room_assignments = {}
        used_rooms: dict[tuple[int, int], set[str]] = defaultdict(set)

        # Sort rooms by capacity
        rooms_by_capacity = sorted(self.dataset.rooms, key=lambda r: r.capacity)

        for crn, (day, block) in self.assignments.items():
            enrollment = self.dataset.get_enrollment_count(crn)
            slot = (day, block)

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
                room = rooms_by_capacity[-1]

            room_assignments[crn] = room.name
            used_rooms[slot].add(room.name)

        return room_assignments
