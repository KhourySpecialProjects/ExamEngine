"""
Full algorithm correctness tests for the DSATUR exam scheduling algorithm.

Each test class targets a distinct correctness property:

  TestGraphColoringCorrectness  - DSATUR produces a valid coloring
  TestHardConstraints           - No student or instructor is ever double-booked
  TestScheduleCompleteness      - Every course gets a slot and a room
  TestDeterminism               - Same input always produces same output
  TestScheduleAnalyzerIntegration - Analyzer correctly interprets ScheduleResult
  TestAlgorithmQuality          - Schedule quality (slot efficiency, room fit, priority)
"""

import json
import random
from collections import defaultdict

import pandas as pd
import pytest

from src.domain.factories.dataset_factory import DatasetFactory
from src.domain.models import SchedulingDataset
from src.domain.services.schedule_analyzer import ScheduleAnalyzer
from src.domain.services.scheduler import Scheduler, ScheduleResult


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _rooms_df(specs: list[tuple[str, int]]) -> pd.DataFrame:
    return pd.DataFrame(
        {"room_name": [s[0] for s in specs], "capacity": [s[1] for s in specs]}
    )


def _find_student_double_bookings(
    dataset: SchedulingDataset, assignments: dict
) -> list[tuple]:
    """Return (student_id, slot, [crn1, crn2]) for every double-booking."""
    slot_to_students: dict = defaultdict(lambda: defaultdict(list))
    for crn, slot in assignments.items():
        for sid in dataset.students_by_crn.get(crn, frozenset()):
            slot_to_students[slot][sid].append(crn)

    return [
        (sid, slot, crns)
        for slot, by_student in slot_to_students.items()
        for sid, crns in by_student.items()
        if len(crns) > 1
    ]


def _find_instructor_double_bookings(
    dataset: SchedulingDataset, assignments: dict
) -> list[tuple]:
    """Return (instructor, slot, [crn1, crn2]) for every double-booking."""
    slot_to_instructors: dict = defaultdict(lambda: defaultdict(list))
    for crn, slot in assignments.items():
        for inst in dataset.instructors_by_crn.get(crn, frozenset()):
            slot_to_instructors[slot][inst].append(crn)

    return [
        (inst, slot, crns)
        for slot, by_inst in slot_to_instructors.items()
        for inst, crns in by_inst.items()
        if len(crns) > 1
    ]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def four_group_dataset():
    """
    20 courses in 4 independent groups of 5.
    200 students each take one course from every group (4 enrolments each).

    Because courses within the same group share students, the conflict graph
    has a known chromatic number of exactly 4.  This is our ground-truth
    fixture for verifying coloring quality and constraint correctness.
    """
    crns = [f"{1000 + i}" for i in range(20)]
    groups = [list(range(i * 5, i * 5 + 5)) for i in range(4)]

    courses_df = pd.DataFrame(
        {
            "CRN": crns,
            "CourseID": [f"CS{100 + i}" for i in range(20)],
            "num_students": [30] * 20,
            "Instructor Name": [f"Dr.{i}" for i in range(20)],
            "examination_term": ["202510"] * 20,
            "department": ["CS"] * 20,
        }
    )

    enrollments = []
    for student_idx in range(200):
        rng = random.Random(student_idx)  # noqa: S311
        for group in groups:
            crn_idx = rng.choice(group)
            enrollments.append(
                {
                    "Student_PIDM": f"S{student_idx:04d}",
                    "CRN": crns[crn_idx],
                }
            )

    rooms_df = _rooms_df(
        [
            ("Hall A", 50),
            ("Hall B", 50),
            ("Hall C", 50),
            ("Hall D", 50),
            ("Hall E", 50),
            ("Hall F", 50),
        ]
    )

    return DatasetFactory.from_dataframes_to_scheduling_dataset(
        courses_df, pd.DataFrame(enrollments), rooms_df
    )


@pytest.fixture(scope="module")
def dense_realistic_dataset():
    """
    30 courses, 400 students each enrolled in 4 randomly-chosen courses.
    Seeded so results are reproducible.  Creates a dense conflict graph that
    forces DSATUR to work hard across realistic scheduling pressure.
    """
    rng = random.Random(42)  # noqa: S311
    n_courses = 30
    crns = [f"{2000 + i}" for i in range(n_courses)]

    courses_df = pd.DataFrame(
        {
            "CRN": crns,
            "CourseID": [f"DEPT{i // 5}{i % 5 + 101}" for i in range(n_courses)],
            "num_students": [rng.randint(20, 60) for _ in range(n_courses)],
            "Instructor Name": [f"Prof.{chr(65 + i % 26)}" for i in range(n_courses)],
            "examination_term": ["202510"] * n_courses,
            "department": [f"DEPT{i // 5}" for i in range(n_courses)],
        }
    )

    enrollments = []
    for student_idx in range(400):
        for crn in rng.sample(crns, 4):
            enrollments.append({"Student_PIDM": f"S{student_idx:05d}", "CRN": crn})

    rooms_df = _rooms_df(
        [
            ("Room 101", 80),
            ("Room 102", 60),
            ("Room 103", 40),
            ("Room 201", 70),
            ("Room 202", 50),
            ("Room 203", 35),
            ("Room 301", 90),
            ("Room 302", 45),
        ]
    )

    return DatasetFactory.from_dataframes_to_scheduling_dataset(
        courses_df, pd.DataFrame(enrollments), rooms_df
    )


@pytest.fixture(scope="module")
def instructor_conflict_dataset():
    """
    6 courses where Prof.A teaches C1/C2/C3 and Prof.B teaches C4/C5.
    Each course has entirely distinct students, so only instructor conflicts
    can arise.  Used to verify instructor double-booking detection.
    """
    courses_df = pd.DataFrame(
        {
            "CRN": ["C1", "C2", "C3", "C4", "C5", "C6"],
            "CourseID": ["CS 101", "CS 102", "CS 103", "CS 201", "CS 202", "CS 203"],
            "num_students": [20] * 6,
            "Instructor Name": [
                "Prof.A",
                "Prof.A",
                "Prof.A",
                "Prof.B",
                "Prof.B",
                "Prof.C",
            ],
            "examination_term": ["202510"] * 6,
            "department": ["CS"] * 6,
        }
    )

    enrollments = []
    for i, crn in enumerate(["C1", "C2", "C3", "C4", "C5", "C6"]):
        for j in range(20):
            enrollments.append({"Student_PIDM": f"S{i * 20 + j:04d}", "CRN": crn})

    rooms_df = _rooms_df([("Room A", 30), ("Room B", 30), ("Room C", 30)])

    return DatasetFactory.from_dataframes_to_scheduling_dataset(
        courses_df, pd.DataFrame(enrollments), rooms_df
    )


# ---------------------------------------------------------------------------
# 1. Graph coloring correctness
# ---------------------------------------------------------------------------


class TestGraphColoringCorrectness:
    """DSATUR must produce a valid proper graph coloring."""

    def test_all_nodes_receive_a_color(self, four_group_dataset):
        scheduler = Scheduler(dataset=four_group_dataset, max_days=7)
        scheduler._build_conflict_graph()
        scheduler._color_graph()

        for crn in four_group_dataset.courses:
            assert crn in scheduler.colors, f"CRN {crn} has no color assigned"

    def test_no_adjacent_courses_share_a_color(self, four_group_dataset):
        """Core DSATUR invariant: every edge (u, v) has colors[u] != colors[v]."""
        scheduler = Scheduler(dataset=four_group_dataset, max_days=7)
        scheduler._build_conflict_graph()
        scheduler._color_graph()

        violations = [
            (u, v)
            for u, v in scheduler.graph.edges()
            if scheduler.colors[u] == scheduler.colors[v]
        ]
        assert violations == [], (
            f"Coloring violations (same color on edge): {violations[:5]}"
        )

    def test_coloring_valid_on_dense_graph(self, dense_realistic_dataset):
        """Coloring invariant holds under a dense, realistic conflict graph."""
        scheduler = Scheduler(dataset=dense_realistic_dataset, max_days=7)
        scheduler._build_conflict_graph()
        scheduler._color_graph()

        violations = [
            (u, v)
            for u, v in scheduler.graph.edges()
            if scheduler.colors[u] == scheduler.colors[v]
        ]
        assert violations == [], f"{len(violations)} coloring violation(s) found"

    def test_four_group_uses_at_most_four_colors(self, four_group_dataset):
        """
        The 4-group conflict graph has chromatic number 4.
        DSATUR should achieve that optimum (or very close to it).
        """
        scheduler = Scheduler(dataset=four_group_dataset, max_days=7)
        scheduler._build_conflict_graph()
        scheduler._color_graph()

        n_colors = len(set(scheduler.colors.values()))
        assert n_colors == 4, (
            f"Expected exactly 4 colors for a 4-chromatic graph, got {n_colors}"
        )

    def test_graph_node_count_matches_course_count(self, dense_realistic_dataset):
        scheduler = Scheduler(dataset=dense_realistic_dataset, max_days=7)
        scheduler._build_conflict_graph()

        assert scheduler.graph.number_of_nodes() == len(dense_realistic_dataset.courses)

    def test_graph_has_edges_for_shared_students(self, four_group_dataset):
        """Courses sharing students must be connected in the conflict graph."""
        scheduler = Scheduler(dataset=four_group_dataset, max_days=7)
        scheduler._build_conflict_graph()

        # For each student, every pair of their courses must have an edge
        for student in four_group_dataset.students.values():
            crn_list = list(student.enrolled_crns)
            for i in range(len(crn_list)):
                for j in range(i + 1, len(crn_list)):
                    u, v = crn_list[i], crn_list[j]
                    assert scheduler.graph.has_edge(u, v) or scheduler.graph.has_edge(
                        v, u
                    ), (
                        f"Missing edge between {u} and {v} which share student "
                        f"{student.student_id}"
                    )


# ---------------------------------------------------------------------------
# 2. Hard constraint: zero double-bookings
# ---------------------------------------------------------------------------


class TestHardConstraints:
    """No student or instructor may have two exams at the same time slot."""

    def test_zero_student_double_bookings_four_group(self, four_group_dataset):
        result = Scheduler(dataset=four_group_dataset, max_days=7).schedule()
        violations = _find_student_double_bookings(
            four_group_dataset, result.assignments
        )
        assert violations == [], f"Student double-bookings: {violations[:3]}"

    def test_zero_student_double_bookings_dense(self, dense_realistic_dataset):
        result = Scheduler(dataset=dense_realistic_dataset, max_days=7).schedule()
        violations = _find_student_double_bookings(
            dense_realistic_dataset, result.assignments
        )
        assert violations == [], (
            f"{len(violations)} student double-booking(s): {violations[:3]}"
        )

    def test_zero_instructor_double_bookings(self, instructor_conflict_dataset):
        """An instructor teaching multiple courses must not be double-booked."""
        result = Scheduler(dataset=instructor_conflict_dataset, max_days=7).schedule()
        violations = _find_instructor_double_bookings(
            instructor_conflict_dataset, result.assignments
        )
        assert violations == [], f"Instructor double-bookings: {violations}"

    def test_prof_a_three_courses_all_different_slots(
        self, instructor_conflict_dataset
    ):
        """Prof.A's three courses must land in three distinct time slots."""
        result = Scheduler(dataset=instructor_conflict_dataset, max_days=7).schedule()
        slots = {crn: result.assignments[crn] for crn in ["C1", "C2", "C3"]}
        assert len(set(slots.values())) == 3, f"Prof.A courses share a slot: {slots}"

    def test_conflict_list_consistent_with_actual_violations(
        self, dense_realistic_dataset
    ):
        """
        If the assignment contains no student double-bookings,
        the conflicts list must also report none.
        """
        result = Scheduler(dataset=dense_realistic_dataset, max_days=7).schedule()
        actual = _find_student_double_bookings(
            dense_realistic_dataset, result.assignments
        )

        reported = [
            c for c in result.conflicts if c.conflict_type == "student_double_book"
        ]

        if not actual:
            assert not reported, (
                f"No real double-bookings but {len(reported)} were reported"
            )

    def test_coloring_implies_no_student_conflicts(self, four_group_dataset):
        """
        A valid graph coloring guarantees no student is double-booked:
        if two courses share a student they have an edge, so different colors,
        so different slots.
        """
        scheduler = Scheduler(dataset=four_group_dataset, max_days=7)
        scheduler._build_conflict_graph()
        scheduler._color_graph()
        scheduler._assign_time_slots(prioritize_large=False)

        violations = _find_student_double_bookings(
            four_group_dataset, scheduler.assignments
        )
        assert violations == [], (
            "Valid coloring should guarantee zero student double-bookings"
        )


# ---------------------------------------------------------------------------
# 3. Completeness: every course gets a slot and a room
# ---------------------------------------------------------------------------


class TestScheduleCompleteness:
    """All courses must appear in assignments and room_assignments."""

    def test_all_courses_assigned_four_group(self, four_group_dataset):
        result = Scheduler(dataset=four_group_dataset, max_days=7).schedule()
        assert set(result.assignments.keys()) == set(four_group_dataset.courses.keys())

    def test_all_courses_have_rooms_four_group(self, four_group_dataset):
        result = Scheduler(dataset=four_group_dataset, max_days=7).schedule()
        missing = set(four_group_dataset.courses) - set(result.room_assignments)
        assert missing == set(), f"Courses without a room: {missing}"

    def test_all_courses_assigned_dense(self, dense_realistic_dataset):
        result = Scheduler(dataset=dense_realistic_dataset, max_days=7).schedule()
        assert len(result.assignments) == len(dense_realistic_dataset.courses)

    def test_all_courses_have_rooms_dense(self, dense_realistic_dataset):
        result = Scheduler(dataset=dense_realistic_dataset, max_days=7).schedule()
        assert len(result.room_assignments) == len(dense_realistic_dataset.courses)

    def test_all_slots_within_valid_range(self, dense_realistic_dataset):
        result = Scheduler(dataset=dense_realistic_dataset, max_days=7).schedule()
        for crn, (day, block) in result.assignments.items():
            assert 0 <= day < 7, f"{crn}: day {day} out of [0, 7)"
            assert 0 <= block < 5, f"{crn}: block {block} out of [0, 5)"

    def test_all_rooms_exist_in_dataset(self, dense_realistic_dataset):
        result = Scheduler(dataset=dense_realistic_dataset, max_days=7).schedule()
        valid_rooms = {r.name for r in dense_realistic_dataset.rooms}
        unknown = {
            room for room in result.room_assignments.values() if room not in valid_rooms
        }
        assert unknown == set(), f"Unknown rooms assigned: {unknown}"

    def test_unassigned_empty_without_blockouts(self, dense_realistic_dataset):
        """With no room blockouts every course should receive a room."""
        result = Scheduler(dataset=dense_realistic_dataset, max_days=7).schedule()
        assert result.unassigned == set()


# ---------------------------------------------------------------------------
# 4. Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    """Running the algorithm twice on the same input must give the same output."""

    def test_assignments_are_deterministic(self, four_group_dataset):
        r1 = Scheduler(dataset=four_group_dataset, max_days=7).schedule()
        r2 = Scheduler(dataset=four_group_dataset, max_days=7).schedule()
        assert r1.assignments == r2.assignments

    def test_room_assignments_are_deterministic(self, four_group_dataset):
        r1 = Scheduler(dataset=four_group_dataset, max_days=7).schedule()
        r2 = Scheduler(dataset=four_group_dataset, max_days=7).schedule()
        assert r1.room_assignments == r2.room_assignments

    def test_colors_are_deterministic(self, dense_realistic_dataset):
        s1 = Scheduler(dataset=dense_realistic_dataset, max_days=7)
        s1._build_conflict_graph()
        s1._color_graph()

        s2 = Scheduler(dataset=dense_realistic_dataset, max_days=7)
        s2._build_conflict_graph()
        s2._color_graph()

        assert s1.colors == s2.colors

    def test_deterministic_under_different_max_days(self, four_group_dataset):
        """Determinism should hold regardless of how many days are available."""
        r1 = Scheduler(dataset=four_group_dataset, max_days=5).schedule()
        r2 = Scheduler(dataset=four_group_dataset, max_days=5).schedule()
        assert r1.assignments == r2.assignments


# ---------------------------------------------------------------------------
# 5. ScheduleAnalyzer integration
# ---------------------------------------------------------------------------


class TestScheduleAnalyzerIntegration:
    """ScheduleAnalyzer must correctly interpret the ScheduleResult produced by Scheduler."""

    def test_analyzer_runs_without_error(self, dense_realistic_dataset):
        result = Scheduler(dataset=dense_realistic_dataset, max_days=7).schedule()
        analysis = ScheduleAnalyzer(dense_realistic_dataset).analyze(result)
        assert analysis is not None

    def test_statistics_num_classes_matches_assignments(self, four_group_dataset):
        result = Scheduler(dataset=four_group_dataset, max_days=7).schedule()
        analysis = ScheduleAnalyzer(four_group_dataset).analyze(result)
        assert analysis.statistics.num_classes == len(result.assignments)

    def test_statistics_slots_used_matches_assignments(self, four_group_dataset):
        result = Scheduler(dataset=four_group_dataset, max_days=7).schedule()
        analysis = ScheduleAnalyzer(four_group_dataset).analyze(result)
        assert analysis.statistics.slots_used == len(set(result.assignments.values()))

    def test_statistics_num_rooms_matches_assignments(self, four_group_dataset):
        result = Scheduler(dataset=four_group_dataset, max_days=7).schedule()
        analysis = ScheduleAnalyzer(four_group_dataset).analyze(result)
        assert analysis.statistics.num_rooms == len(
            set(result.room_assignments.values())
        )

    def test_hard_conflict_counts_are_non_negative(self, dense_realistic_dataset):
        result = Scheduler(dataset=dense_realistic_dataset, max_days=7).schedule()
        analysis = ScheduleAnalyzer(dense_realistic_dataset).analyze(result)
        assert analysis.statistics.total_hard_conflicts >= 0
        assert analysis.statistics.total_soft_conflicts >= 0

    def test_analysis_to_dict_is_json_serializable(self, four_group_dataset):
        result = Scheduler(dataset=four_group_dataset, max_days=7).schedule()
        analysis = ScheduleAnalyzer(four_group_dataset).analyze(result)
        json.dumps(analysis.to_dict())  # raises TypeError if not serializable

    def test_back_to_back_detection(self):
        """Analyzer correctly identifies a forced back-to-back situation."""
        courses_df = pd.DataFrame(
            {
                "CRN": ["A1", "A2"],
                "CourseID": ["CS 101", "CS 102"],
                "num_students": [5, 5],
                "Instructor Name": ["Prof.X", "Prof.Y"],
                "examination_term": ["202510", "202510"],
                "department": ["CS", "CS"],
            }
        )
        rooms_df = pd.DataFrame({"room_name": ["R1"], "capacity": [10]})
        base_dataset = DatasetFactory.from_dataframes_to_scheduling_dataset(
            courses_df,
            pd.DataFrame({"Student_PIDM": ["S1", "S2"], "CRN": ["A1", "A2"]}),
            rooms_df,
        )
        # Force S1 into both courses so a back-to-back can be detected
        tweaked = SchedulingDataset(
            courses=base_dataset.courses,
            students=base_dataset.students,
            rooms=base_dataset.rooms,
            students_by_crn={"A1": frozenset(["S1"]), "A2": frozenset(["S1"])},
            instructors_by_crn={},
        )
        # Manually construct a result with consecutive blocks
        result = ScheduleResult(
            assignments={"A1": (0, 0), "A2": (0, 1)},
            room_assignments={"A1": "R1", "A2": "R1"},
            conflicts=[],
            colors={"A1": 0, "A2": 1},
        )

        analysis = ScheduleAnalyzer(tweaked).analyze(result)

        assert len(analysis.soft_conflicts.back_to_back_students) == 1
        assert analysis.soft_conflicts.back_to_back_students[0]["student_id"] == "S1"

    def test_zero_student_double_books_in_analysis(self, four_group_dataset):
        """A correctly-colored schedule should have zero hard student conflicts."""
        result = Scheduler(dataset=four_group_dataset, max_days=7).schedule()
        analysis = ScheduleAnalyzer(four_group_dataset).analyze(result)
        assert analysis.hard_conflicts.student_double_book == []

    def test_zero_instructor_double_books_in_analysis(
        self, instructor_conflict_dataset
    ):
        result = Scheduler(dataset=instructor_conflict_dataset, max_days=7).schedule()
        analysis = ScheduleAnalyzer(instructor_conflict_dataset).analyze(result)
        assert analysis.hard_conflicts.instructor_double_book == []


# ---------------------------------------------------------------------------
# 6. Algorithm quality
# ---------------------------------------------------------------------------


class TestAlgorithmQuality:
    """The schedule should be efficient, not just valid."""

    def test_four_group_uses_exactly_four_colors(self, four_group_dataset):
        """
        The 4-group dataset has chromatic number 4.
        DSATUR should assign exactly 4 distinct colors (one per independent group).

        Note: the soft-constraint penalty spreads same-color courses across
        different time slots to avoid room bottlenecks, so the *slot* count is
        allowed to exceed the color count — the color count is the correctness
        signal.
        """
        result = Scheduler(dataset=four_group_dataset, max_days=7).schedule()
        n_colors = len(set(result.colors.values()))
        assert n_colors == 4, (
            f"Expected 4 colors for a 4-chromatic graph, got {n_colors}"
        )

    def test_independent_courses_get_same_color(self):
        """
        Courses that share no students must be assigned the same color
        (they can always be scheduled together without conflicts).
        Two isolated courses → chromatic number 1 → exactly 1 color.
        """
        courses_df = pd.DataFrame(
            {
                "CRN": ["A1", "A2"],
                "CourseID": ["CS 101", "CS 102"],
                "num_students": [10, 10],
                "Instructor Name": ["Prof.X", "Prof.Y"],
                "examination_term": ["202510"] * 2,
                "department": ["CS"] * 2,
            }
        )
        # No enrollments → no shared students → no conflict edges
        enrollments_df = pd.DataFrame({"Student_PIDM": [], "CRN": []})
        rooms_df = _rooms_df([("Hall A", 30)])
        dataset = DatasetFactory.from_dataframes_to_scheduling_dataset(
            courses_df, enrollments_df, rooms_df
        )
        result = Scheduler(dataset=dataset, max_days=7).schedule()
        n_colors = len(set(result.colors.values()))
        assert n_colors == 1, (
            f"Two isolated courses should share 1 color, got {n_colors}"
        )

    def test_room_capacity_preference_smallest_fit(self):
        """Scheduler should pick the smallest room that fits the enrollment."""
        courses_df = pd.DataFrame(
            {
                "CRN": ["C1"],
                "CourseID": ["CS 101"],
                "num_students": [20],
                "Instructor Name": ["Prof.A"],
                "examination_term": ["202510"],
                "department": ["CS"],
            }
        )
        enrollments_df = pd.DataFrame(
            {
                "Student_PIDM": [f"S{i}" for i in range(20)],
                "CRN": ["C1"] * 20,
            }
        )
        rooms_df = _rooms_df([("Small Room", 25), ("Big Hall", 500)])
        dataset = DatasetFactory.from_dataframes_to_scheduling_dataset(
            courses_df, enrollments_df, rooms_df
        )

        result = Scheduler(dataset=dataset, max_days=7).schedule()
        assert result.room_assignments["C1"] == "Small Room", (
            "Should prefer the smallest room that fits over a large one"
        )

    def test_prioritize_large_courses_places_them_early(self):
        """With prioritize_large_courses=True, the largest courses get early days."""
        courses_df = pd.DataFrame(
            {
                "CRN": [str(i) for i in range(10)],
                "CourseID": [f"CS{i}" for i in range(10)],
                # Descending enrollment: CRN "0" is the biggest
                "num_students": [200, 150, 100, 80, 60, 30, 25, 20, 15, 10],
                "Instructor Name": [f"Prof.{i}" for i in range(10)],
                "examination_term": ["202510"] * 10,
                "department": ["CS"] * 10,
            }
        )
        # Fully disjoint student sets so every course is independent
        enrollments = []
        base = 0
        for i in range(10):
            size = courses_df["num_students"].iloc[i]
            for j in range(size):
                enrollments.append({"Student_PIDM": f"S{base + j:05d}", "CRN": str(i)})
            base += size

        rooms_df = _rooms_df([("Big Hall", 300)])
        dataset = DatasetFactory.from_dataframes_to_scheduling_dataset(
            courses_df, pd.DataFrame(enrollments), rooms_df
        )

        result = Scheduler(dataset=dataset, max_days=7).schedule(
            prioritize_large_courses=True
        )

        # The two largest courses (CRN "0" = 200 seats, "1" = 150 seats)
        # should land on day 0 or day 1
        for crn in ["0", "1"]:
            day, _ = result.assignments[crn]
            assert day <= 2, (
                f"Large course CRN {crn} placed on day {day} with prioritization on"
            )

    def test_no_two_courses_in_same_room_at_same_slot(self, dense_realistic_dataset):
        """Two different exams must never share the exact same room and slot."""
        result = Scheduler(dataset=dense_realistic_dataset, max_days=7).schedule()

        slot_room_to_crns: dict = defaultdict(list)
        for crn, slot in result.assignments.items():
            room = result.room_assignments.get(crn)
            if room:
                slot_room_to_crns[(slot, room)].append(crn)

        collisions = {k: v for k, v in slot_room_to_crns.items() if len(v) > 1}
        assert collisions == {}, f"Room/slot collisions detected: {collisions}"
