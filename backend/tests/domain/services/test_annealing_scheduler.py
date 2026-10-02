"""Tests for Algorithm 2: AnnealingScheduler (MRV construction + annealing)."""

import random
from collections import Counter, defaultdict

import pytest

from src.domain.factories.dataset_factory import DatasetFactory
from src.domain.models import Course, Room, SchedulingDataset, Student
from src.domain.services.annealing_scheduler import HARD, AnnealingScheduler
from src.domain.services.scheduler import Scheduler


pytestmark = pytest.mark.unit


def _dataset(
    enrollments: dict[str, int],
    rooms: dict[str, int],
    students: dict[str, list[str]] | None = None,
    instructors: dict[str, str] | None = None,
    blockouts: dict[str, frozenset[tuple[int, int]]] | None = None,
) -> SchedulingDataset:
    """Small dataset: CRN → size, room → capacity, student → CRNs, CRN → instructor."""
    instructors = instructors or {}
    courses = {
        crn: Course(
            crn=crn,
            course_code=f"BIOL {crn}",
            enrollment_count=size,
            instructor_names={instructors[crn]} if crn in instructors else set(),
            department="BIOL",
            examination_term="202510",
        )
        for crn, size in enrollments.items()
    }
    students = students or {}
    students_by_crn: dict[str, set[str]] = defaultdict(set)
    for sid, crns in students.items():
        for crn in crns:
            students_by_crn[crn].add(sid)
    return SchedulingDataset(
        courses=courses,
        students={
            sid: Student(student_id=sid, enrolled_crns=frozenset(crns))
            for sid, crns in students.items()
        },
        rooms=[Room(name=name, capacity=cap) for name, cap in rooms.items()],
        students_by_crn={crn: frozenset(s) for crn, s in students_by_crn.items()},
        instructors_by_crn={
            crn: frozenset({name}) for crn, name in instructors.items()
        },
        room_blockouts=blockouts or {},
    )


def _hard_conflicts(result):
    return [
        c
        for c in result.conflicts
        if "double_book" in c.conflict_type or "gt_max" in c.conflict_type
    ]


class TestObjective:
    def test_incremental_cost_matches_recompute_after_random_moves(
        self, sample_census_data, sample_enrollment_data, sample_classroom_data
    ):
        dataset = DatasetFactory.from_dataframes_to_scheduling_dataset(
            sample_census_data, sample_enrollment_data, sample_classroom_data
        )
        s = AnnealingScheduler(dataset, max_days=3, time_budget_seconds=0)
        s._build_conflict_graph()
        s._init_model()
        s._construct()
        rng = random.Random(7)  # noqa: S311
        n = len(s._tgs)
        for _ in range(300):
            s._move(rng.randrange(n), rng.randrange(-1, s.nslots))
        assert s.cost == s.recompute_cost()

    def test_hard_violations_cost_more_than_any_soft_term(self):
        # Two exams sharing a student: same slot costs HARD, adjacent costs 6.
        dataset = _dataset({"A": 10, "B": 10}, {"R": 20, "S": 20}, {"s1": ["A", "B"]})
        s = AnnealingScheduler(
            dataset, max_days=1, weight_slot_balance=0, time_budget_seconds=0
        )
        s._build_conflict_graph()
        s._init_model()
        a, b = s._tg_index["crn:A"], s._tg_index["crn:B"]
        s._move(a, 0)
        assert s._delta(b, 0) == HARD
        assert s._delta(b, 1) == s.weight_b2b_student
        assert s._delta(b, 2) == 0

    def test_slot_balance_charges_quadratic_block_load(self):
        dataset = _dataset({"A": 10, "B": 10, "C": 10}, {"R": 20, "S": 20, "T": 20})
        s = AnnealingScheduler(
            dataset, max_days=1, weight_slot_balance=3, time_budget_seconds=0
        )
        s._build_conflict_graph()
        s._init_model()
        a, b, c = (s._tg_index[f"crn:{x}"] for x in "ABC")
        s._move(a, 0)
        s._move(b, 0)
        # third exam into a block of 2: 3 * (3² - 2²); into an empty block: 3 * 1
        assert s._delta(c, 0) == 15
        assert s._delta(c, 1) == 3

    def test_independent_exams_spread_over_every_block(self):
        # No shared students: without balancing everything lands in block 0.
        exams = {f"C{i}": 10 for i in range(10)}
        rooms = {f"R{i}": 20 for i in range(10)}
        spread = AnnealingScheduler(
            _dataset(exams, rooms), max_days=1, time_budget_seconds=0
        ).schedule()
        packed = AnnealingScheduler(
            _dataset(exams, rooms),
            max_days=1,
            weight_slot_balance=0,
            time_budget_seconds=0,
        ).schedule()

        assert sorted(Counter(spread.assignments.values()).values()) == [2] * 5
        assert set(packed.assignments.values()) == {(0, 0)}


class TestSchedule:
    def test_fixture_dataset_has_no_hard_conflicts(
        self, sample_census_data, sample_enrollment_data, sample_classroom_data
    ):
        dataset = DatasetFactory.from_dataframes_to_scheduling_dataset(
            sample_census_data, sample_enrollment_data, sample_classroom_data
        )
        result = AnnealingScheduler(dataset, time_budget_seconds=0).schedule()

        assert set(result.assignments) == set(dataset.courses)
        assert not _hard_conflicts(result)
        assert set(result.room_assignments) == set(dataset.courses)
        assert not result.unscheduled_crns

    def test_zero_budget_is_construction_and_budget_never_worsens_it(self):
        rng = random.Random(3)  # noqa: S311
        crns = [f"C{i}" for i in range(30)]
        students = {f"s{i}": rng.sample(crns, 4) for i in range(120)}
        dataset = _dataset(
            dict.fromkeys(crns, 20), {f"R{i}": 25 for i in range(8)}, students
        )
        base = AnnealingScheduler(dataset, max_days=2, time_budget_seconds=0)
        base.schedule()
        improved = AnnealingScheduler(dataset, max_days=2, time_budget_seconds=1)
        improved.schedule()

        assert base.cost == base.recompute_cost()
        assert improved.cost == improved.recompute_cost()
        assert improved.cost <= base.cost

    def test_conflicts_are_recomputed_from_final_assignment(self):
        # One day, one block: both exams must share the slot → reported.
        dataset = _dataset({"A": 10, "B": 10}, {"R": 20, "S": 20}, {"s1": ["A", "B"]})
        result = AnnealingScheduler(
            dataset, max_days=1, blocks_per_day=1, time_budget_seconds=0
        ).schedule()

        assert result.assignments["A"] == result.assignments["B"] == (0, 0)
        [conflict] = result.conflicts
        assert conflict.conflict_type == "student_double_book"
        assert conflict.entity_id == "s1"
        assert {conflict.crn, conflict.conflicting_crn} == {"A", "B"}

    def test_over_max_per_day_reported(self):
        dataset = _dataset(
            {"A": 10, "B": 10, "C": 10},
            {"R": 20},
            {"s1": ["A", "B", "C"]},
        )
        result = AnnealingScheduler(
            dataset,
            max_days=1,
            blocks_per_day=5,
            student_max_per_day=2,
            time_budget_seconds=0,
        ).schedule()

        over = [
            c for c in result.conflicts if c.conflict_type == "student_gt_max_per_day"
        ]
        assert len(over) == 1
        assert not [c for c in result.conflicts if "double_book" in c.conflict_type]


class TestGroups:
    def test_combined_group_shares_slot_and_room(self):
        dataset = _dataset({"X": 20, "Y": 15, "Z": 10}, {"Big": 40, "Small": 12})
        result = AnnealingScheduler(
            dataset, max_days=2, merges={"M": ["X", "Y"]}, time_budget_seconds=0
        ).schedule()

        assert result.assignments["X"] == result.assignments["Y"]
        assert result.room_assignments["X"] == result.room_assignments["Y"] == "Big"
        assert not result.unscheduled_groups

    def test_common_group_shares_slot_with_distinct_rooms(self):
        dataset = _dataset(
            {"A": 30, "B": 30, "C": 30, "D": 5},
            {"R1": 40, "R2": 40, "R3": 40, "R4": 10},
        )
        result = AnnealingScheduler(
            dataset,
            max_days=2,
            common_groups={"G": ["A", "B", "C"]},
            time_budget_seconds=0,
        ).schedule()

        assert result.assignments["A"] == result.assignments["B"]
        assert result.assignments["A"] == result.assignments["C"]
        assert sorted(result.room_assignments[c] for c in "ABC") == ["R1", "R2", "R3"]
        assert not result.unscheduled_groups

    def test_same_instructor_across_common_group_is_not_a_conflict(self):
        # Three sections of one common exam, one instructor, one slot: by design,
        # so neither double-booking nor over-max is reported (as in Algorithm 1).
        # A student in two of its sections is still double-booked.
        dataset = _dataset(
            {"A": 30, "B": 30, "C": 30},
            {"R1": 40, "R2": 40, "R3": 40},
            students={"s1": ["A", "B"]},
            instructors={"A": "Dr. X", "B": "Dr. X", "C": "Dr. X"},
        )
        result = AnnealingScheduler(
            dataset,
            max_days=1,
            instructor_max_per_day=2,
            common_groups={"G": ["A", "B", "C"]},
            time_budget_seconds=0,
        ).schedule()

        assert len({result.assignments[c] for c in "ABC"}) == 1
        assert [c.conflict_type for c in result.conflicts] == ["student_double_book"]
        assert result.conflicts[0].entity_id == "s1"

    def test_common_group_with_combined_member_three_rooms_one_block(self):
        dataset = _dataset(
            {"11111": 20, "22222": 15, "33333": 25, "44444": 10},
            {"Big": 40, "Mid1": 30, "Mid2": 30, "Small": 20},
        )
        result = AnnealingScheduler(
            dataset,
            max_days=2,
            merges={"M1": ["11111", "22222"]},
            common_groups={"BIOL101": ["11111", "33333", "44444"]},
            time_budget_seconds=1,
        ).schedule()

        assert len({result.assignments[c] for c in dataset.courses}) == 1
        assert result.room_assignments["11111"] == result.room_assignments["22222"]
        rooms = {result.room_assignments[c] for c in ("11111", "33333", "44444")}
        assert len(rooms) == 3

    def test_two_common_groups_never_share_a_room_in_the_same_block(self):
        # Four 30-seat exams, two 40-seat rooms: with one block per day and
        # two days, G1 and G2 must land on different days or fail to pack.
        dataset = _dataset({"A": 30, "B": 30, "C": 30, "D": 30}, {"R1": 40, "R2": 40})
        result = AnnealingScheduler(
            dataset,
            max_days=2,
            blocks_per_day=1,
            common_groups={"G1": ["A", "B"], "G2": ["C", "D"]},
            time_budget_seconds=1,
        ).schedule()

        assert not result.unscheduled_groups
        assert result.assignments["A"] != result.assignments["C"]
        by_slot: dict[tuple[int, int], set[str]] = defaultdict(set)
        for crn, slot in result.assignments.items():
            room = result.room_assignments[crn]
            assert room not in by_slot[slot]
            by_slot[slot].add(room)

    def test_unschedulable_groups_match_classic_scheduler(self):
        dataset = _dataset({"X": 50, "Y": 50, "Z": 10}, {"R": 60})
        kwargs = {"max_days": 2, "merges": {"M": ["X", "Y"]}}
        classic = Scheduler(dataset, **kwargs).schedule()
        annealed = AnnealingScheduler(
            dataset, time_budget_seconds=1, **kwargs
        ).schedule()

        assert annealed.unscheduled_groups == classic.unscheduled_groups
        assert annealed.unscheduled_crns == {"X", "Y"}
        assert annealed.assignments.keys() == {"Z"}

    def test_common_group_with_no_fitting_block_is_left_unscheduled(self):
        # Only one room is ever free; the common group needs two at once.
        dataset = _dataset(
            {"A": 30, "B": 30},
            {"R1": 40, "R2": 40},
            blockouts={"R2": frozenset({(0, 0), (1, 0)})},
        )
        result = AnnealingScheduler(
            dataset,
            max_days=2,
            blocks_per_day=1,
            common_groups={"G": ["A", "B"]},
            time_budget_seconds=0,
        ).schedule()

        assert [g.label for g in result.unscheduled_groups] == ["G"]
        assert "2 free, unblocked rooms" in result.unscheduled_groups[0].reason
        assert not result.assignments


class TestBlockouts:
    def test_blocked_room_never_used_at_blocked_slot(self):
        blocked = frozenset((0, b) for b in range(5))
        dataset = _dataset(
            {"A": 30, "B": 30, "C": 30},
            {"Big": 50, "Tiny": 5},
            blockouts={"Big": blocked},
        )
        result = AnnealingScheduler(
            dataset, max_days=2, time_budget_seconds=0
        ).schedule()

        for crn, slot in result.assignments.items():
            if slot in blocked:
                assert result.room_assignments[crn] != "Big"


class TestValidation:
    def test_negative_budget_rejected(self):
        dataset = _dataset({"A": 10}, {"R": 20})
        with pytest.raises(ValueError):
            AnnealingScheduler(dataset, time_budget_seconds=-1)

    def test_empty_dataset(self):
        dataset = _dataset({}, {"R": 20})
        result = AnnealingScheduler(dataset).schedule()
        assert result.assignments == {}
        assert result.conflicts == []
