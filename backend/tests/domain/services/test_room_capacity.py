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
        rooms=[Room(name=name, capacity=cap) for name, cap in rooms.items()],
        students_by_crn={crn: frozenset(s) for crn, s in by_crn.items()},
        instructors_by_crn={},
        room_blockouts=blockouts or {},
    )


def _schedulers(dataset, **kwargs):
    return [
        Scheduler(dataset=dataset, **kwargs),
        AnnealingScheduler(dataset=dataset, time_budget_seconds=0.2, **kwargs),
    ]


ALGORITHMS = ["dsatur", "annealing"]


def _seated(dataset, result):
    """(slot, room) → students seated there."""
    seated: dict[tuple, int] = defaultdict(int)
    for crn, room in result.room_assignments.items():
        seated[(result.assignments[crn], room)] += dataset.get_enrollment_count(crn)
    return seated


def _random_dataset(seed: int):
    rng = random.Random(seed)  # noqa: S311 - reproducible test data
    rooms = {
        f"R{i}": rng.choice([20, 40, 60, 90, 150]) for i in range(rng.randint(3, 7))
    }
    largest = max(rooms.values())
    sizes = {f"{100 + i}": rng.randint(5, largest + 40) for i in range(30)}
    crns = list(sizes)
    students = {f"s{i}": rng.sample(crns, rng.randint(2, 4)) for i in range(60)}
    merges = {"M": crns[0:2]}
    commons = {"G": crns[2:5]}
    blocked = {
        name: frozenset({(0, rng.randint(0, 4))}) for name in rng.sample(list(rooms), 2)
    }
    return _dataset(sizes, rooms, students, blocked), merges, commons


@pytest.mark.parametrize("seed", range(8))
def test_no_room_is_ever_over_capacity(seed):
    dataset, merges, commons = _random_dataset(seed)
    capacity = {room.name: room.capacity for room in dataset.rooms}

    for scheduler in _schedulers(
        dataset, max_days=2, merges=merges, common_groups=commons
    ):
        result = scheduler.schedule()

        for (slot, room), students in _seated(dataset, result).items():
            assert students <= capacity[room], (type(scheduler).__name__, slot, room)
            assert slot not in dataset.room_blockouts.get(room, frozenset())
        # Every course is either seated or reported unscheduled, never roomless.
        for crn in dataset.courses:
            assert (crn in result.room_assignments) != (crn in result.unscheduled_crns)
        assert set(result.assignments) == set(result.room_assignments)


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_section_larger_than_every_room_is_unscheduled_with_reason(algorithm):
    dataset = _dataset({"BIG": 579, "OK": 50}, {"Hall": 400})
    scheduler = dict(zip(ALGORITHMS, _schedulers(dataset, max_days=1), strict=True))[
        algorithm
    ]

    result = scheduler.schedule()

    assert "BIG" not in result.assignments
    assert [g.to_dict() for g in result.unscheduled_groups] == [
        {
            "kind": "section",
            "group": "BIG",
            "reason": "579 students; largest room seats 400",
            "crns": ["BIG"],
        }
    ]
    assert result.room_assignments == {"OK": "Hall"}


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_section_keeps_the_one_room_that_fits_it(algorithm):
    # One slot. 451 fits no room; 273 fits only the 275-seat room.
    dataset = _dataset(
        {"HUGE": 451, "MID": 273}, {"Big": 275, "Small": 257}, {"s1": ["HUGE", "MID"]}
    )
    scheduler = dict(
        zip(ALGORITHMS, _schedulers(dataset, max_days=1, blocks_per_day=1), strict=True)
    )[algorithm]

    result = scheduler.schedule()

    assert result.room_assignments == {"MID": "Big"}
    assert result.unscheduled_crns == {"HUGE"}


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_two_sections_competing_for_one_room_never_share_or_overflow(algorithm):
    # Both need the 100-seat room; with one slot only one can be seated.
    dataset = _dataset({"A": 90, "B": 80}, {"Big": 100, "Small": 30})
    scheduler = dict(
        zip(ALGORITHMS, _schedulers(dataset, max_days=1, blocks_per_day=1), strict=True)
    )[algorithm]

    result = scheduler.schedule()

    assert list(result.room_assignments.values()) == ["Big"]
    assert len(result.unscheduled_crns) == 1
    (group,) = result.unscheduled_groups
    assert group.kind == "section"
    assert "room large enough" in group.reason
