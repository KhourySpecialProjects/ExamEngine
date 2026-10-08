"""Rooms are never over capacity, for both scheduling algorithms (EXENG-58)."""

import random
from collections import defaultdict

import pytest

from src.domain.models import Course, Room, SchedulingDataset, Student
from src.domain.services.annealing_scheduler import AnnealingScheduler
from src.domain.services.scheduler import Scheduler


def _dataset(
    sizes: dict[str, int],
    rooms: dict[str, int],
    students: dict[str, list[str]] | None = None,
    blockouts: dict[str, frozenset[tuple[int, int]]] | None = None,
    large_only: str | None = None,
) -> SchedulingDataset:
    students = students or {}
    by_crn: dict[str, set[str]] = defaultdict(set)
    for sid, crns in students.items():
        for crn in crns:
            by_crn[crn].add(sid)
    return SchedulingDataset(
        courses={
            crn: Course(
                crn=crn,
                course_code=f"C {crn}",
                enrollment_count=size,
                instructor_names=set(),
                department="C",
                examination_term="202610",
            )
            for crn, size in sizes.items()
        },
        students={
            sid: Student(student_id=sid, enrolled_crns=frozenset(crns))
            for sid, crns in students.items()
        },
        rooms=[
            Room(name=name, capacity=cap, large_only=name == large_only)
            for name, cap in rooms.items()
        ],
        students_by_crn={crn: frozenset(s) for crn, s in by_crn.items()},
        instructors_by_crn={},
        room_blockouts=blockouts or {},
    )


ALGORITHMS = ["dsatur", "annealing"]


def _scheduler(algorithm: str, dataset, **kwargs):
    if algorithm == "dsatur":
        return Scheduler(dataset=dataset, **kwargs)
    return AnnealingScheduler(dataset=dataset, time_budget_seconds=0.2, **kwargs)


def _seated(dataset, result):
    """(slot, room) → students seated there."""
    seated: dict[tuple, int] = defaultdict(int)
    for crn, room in result.room_assignments.items():
        seated[(result.assignments[crn], room)] += dataset.get_enrollment_count(crn)
    return seated


def _random_dataset(seed: int, large_only: bool = False):
    rng = random.Random(seed)  # noqa: S311 - reproducible test data
    rooms = {
        f"R{i}": rng.choice([20, 40, 60, 90, 150]) for i in range(rng.randint(3, 7))
    }
    largest = max(rooms.values())
    if large_only:
        rooms["Hall"] = largest + 60
    sizes = {f"{100 + i}": rng.randint(5, largest + 40) for i in range(30)}
    crns = list(sizes)
    students = {f"s{i}": rng.sample(crns, rng.randint(2, 4)) for i in range(60)}
    merges = {"M": crns[0:2]}
    commons = {"G": crns[2:5]}
    blocked = {
        name: frozenset({(0, rng.randint(0, 4))}) for name in rng.sample(list(rooms), 2)
    }
    dataset = _dataset(
        sizes, rooms, students, blocked, large_only="Hall" if large_only else None
    )
    return dataset, merges, commons


@pytest.mark.parametrize("algorithm", ALGORITHMS)
@pytest.mark.parametrize("seed", range(8))
@pytest.mark.parametrize("large_only", [False, True])
@pytest.mark.parametrize("promote_rooms", [False, True])
def test_no_room_is_ever_over_capacity(algorithm, seed, large_only, promote_rooms):
    dataset, merges, commons = _random_dataset(seed, large_only)
    capacity = {room.name: room.capacity for room in dataset.rooms}
    scheduler = _scheduler(
        algorithm,
        dataset,
        max_days=2,
        merges=merges,
        common_groups=commons,
        promote_rooms=promote_rooms,
    )

    result = scheduler.schedule()

    for (slot, room), students in _seated(dataset, result).items():
        assert students <= capacity[room], (slot, room)
        assert slot not in dataset.room_blockouts.get(room, frozenset())
    # Every course is either seated or reported unscheduled, never roomless.
    for crn in dataset.courses:
        assert (crn in result.room_assignments) != (crn in result.unscheduled_crns)
    assert set(result.assignments) == set(result.room_assignments)
    if large_only:
        # Exams above the largest ordinary room sit in Hall, and only they do.
        cutoff = max(r.capacity for r in dataset.rooms if not r.large_only)
        for (slot, room), students in _seated(dataset, result).items():
            assert (room == "Hall") == (students > cutoff), (slot, room, students)


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_promotion_moves_a_combined_group_as_one_and_skips_blocked_rooms(algorithm):
    # One slot. M (C1 + C2 = 40) fills Small; Big is blocked out, so M takes Mid.
    dataset = _dataset(
        {"C1": 20, "C2": 20},
        {"Small": 40, "Mid": 70, "Big": 80},
        blockouts={"Big": frozenset({(0, 0)})},
    )

    def rooms(promote_rooms: bool) -> dict[str, str]:
        return (
            _scheduler(
                algorithm,
                dataset,
                max_days=1,
                blocks_per_day=1,
                merges={"M": ["C1", "C2"]},
                promote_rooms=promote_rooms,
            )
            .schedule()
            .room_assignments
        )

    assert rooms(False) == {"C1": "Small", "C2": "Small"}
    assert rooms(True) == {"C1": "Mid", "C2": "Mid"}


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_section_larger_than_every_room_is_unscheduled_with_reason(algorithm):
    dataset = _dataset({"BIG": 130, "OK": 50}, {"Hall": 100})

    result = _scheduler(algorithm, dataset, max_days=1).schedule()

    assert "BIG" not in result.assignments
    assert [g.to_dict() for g in result.unscheduled_groups] == [
        {
            "kind": "section",
            "group": "BIG",
            "reason": "130 students; largest room seats 100",
            "crns": ["BIG"],
        }
    ]
    assert result.room_assignments == {"OK": "Hall"}


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_section_keeps_the_one_room_that_fits_it(algorithm):
    # One slot. HUGE fits no room; MID fits only the 100-seat room.
    dataset = _dataset(
        {"HUGE": 120, "MID": 95}, {"Big": 100, "Small": 90}, {"s1": ["HUGE", "MID"]}
    )

    result = _scheduler(algorithm, dataset, max_days=1, blocks_per_day=1).schedule()

    assert result.room_assignments == {"MID": "Big"}
    assert result.unscheduled_crns == {"HUGE"}


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_two_sections_competing_for_one_room_never_share_or_overflow(algorithm):
    # Both need the 100-seat room; with one slot only one can be seated.
    dataset = _dataset({"A": 90, "B": 80}, {"Big": 100, "Small": 30})

    result = _scheduler(algorithm, dataset, max_days=1, blocks_per_day=1).schedule()

    assert list(result.room_assignments.values()) == ["Big"]
    assert len(result.unscheduled_crns) == 1
    (group,) = result.unscheduled_groups
    assert group.kind == "section"
    assert "room large enough" in group.reason


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_room_listed_twice_still_holds_one_exam_at_a_time(algorithm):
    dataset = _dataset({"A": 40, "B": 40}, {"Hall": 50})
    dataset.rooms.append(Room(name="Hall", capacity=50))

    result = _scheduler(algorithm, dataset, max_days=1, blocks_per_day=1).schedule()

    assert list(result.room_assignments.values()) == ["Hall"]
    assert len(result.unscheduled_crns) == 1


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_large_only_room_never_takes_an_exam_another_room_could_seat(algorithm):
    # One slot, one ordinary room: the empty large-only Hall may not take B.
    dataset = _dataset(
        {"A": 90, "B": 80}, {"Hall": 500, "Small": 100}, large_only="Hall"
    )

    result = _scheduler(algorithm, dataset, max_days=1, blocks_per_day=1).schedule()

    assert list(result.room_assignments.values()) == ["Small"]
    (group,) = result.unscheduled_groups
    assert "large-only room Hall" in group.reason


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_exams_above_the_cutoff_use_only_the_large_only_room(algorithm):
    # Cutoff 150 (largest ordinary room). A and B both need Hall; one slot.
    dataset = _dataset(
        {"A": 200, "B": 160, "C": 140},
        {"Hall": 300, "Big": 150, "Small": 100},
        large_only="Hall",
    )

    result = _scheduler(algorithm, dataset, max_days=1, blocks_per_day=1).schedule()

    assert result.room_assignments["C"] == "Big"
    (seated,) = {"A", "B"} & set(result.room_assignments)
    assert result.room_assignments[seated] == "Hall"
    (group,) = result.unscheduled_groups
    assert "large-only room Hall free and unblocked" in group.reason


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_combined_group_above_the_cutoff_goes_to_the_large_only_room(algorithm):
    dataset = _dataset(
        {"C1": 90, "C2": 90, "D": 120},
        {"Hall": 300, "Big": 150, "Small": 100},
        large_only="Hall",
    )

    result = _scheduler(
        algorithm, dataset, max_days=1, blocks_per_day=1, merges={"M": ["C1", "C2"]}
    ).schedule()

    assert result.room_assignments == {"C1": "Hall", "C2": "Hall", "D": "Big"}


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_common_group_cannot_spill_a_small_exam_into_the_large_only_room(algorithm):
    # Without the rule the 120 section would take Hall; with it, no room is left.
    dataset = _dataset(
        {"G1": 140, "G2": 130, "G3": 120},
        {"Hall": 300, "Big": 150, "Mid": 140, "Small": 100},
        large_only="Hall",
    )

    result = _scheduler(
        algorithm, dataset, max_days=1, common_groups={"G": ["G1", "G2", "G3"]}
    ).schedule()

    assert not result.room_assignments
    (group,) = result.unscheduled_groups
    assert group.kind == "common"
    assert "large-only room Hall" in group.reason
