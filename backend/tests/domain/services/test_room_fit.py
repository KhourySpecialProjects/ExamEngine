"""Room-fit rules: the large-only seating check against brute force (EXENG-164)
and promotion into larger free rooms (EXENG-182)."""

import random
from itertools import permutations

import pytest

from src.domain.models import Room
from src.domain.services.room_fit import (
    NO_CUTOFF,
    PROMOTION_FACTOR,
    RoomPools,
    large_only_cutoff,
    large_only_problem,
    promote_to_larger_rooms,
    room_allows,
)


def _brute_force_fits(sizes: list[int], rooms: list[Room], cutoff: float) -> bool:
    return any(
        all(
            room_allows(room, size, cutoff)
            for size, room in zip(sizes, chosen, strict=True)
        )
        for chosen in permutations(rooms, len(sizes))
    )


def _random_rooms(rng: random.Random) -> list[Room]:
    rooms = [
        Room(name=f"R{i}", capacity=rng.choice([20, 40, 60, 90]))
        for i in range(rng.randint(1, 5))
    ]
    if rng.random() < 0.7:
        rooms.append(
            Room(name="Hall", capacity=rng.choice([100, 150]), large_only=True)
        )
    return rooms


@pytest.mark.parametrize("seed", range(200))
def test_pools_fit_exactly_when_an_allowed_seating_exists(seed):
    rng = random.Random(seed)  # noqa: S311 - reproducible test data
    rooms = _random_rooms(rng)
    cutoff = large_only_cutoff(rooms)
    sizes = sorted(
        (rng.randint(5, 160) for _ in range(rng.randint(1, 4))), reverse=True
    )
    pools = RoomPools.of(rooms, cutoff)

    assert pools.fits(sizes) == _brute_force_fits(sizes, rooms, cutoff)

    if not pools.fits(sizes):
        return  # the engines only ever add exams to a slot whose exams fit
    # The cached single-exam answer agrees with the full check for any newcomer.
    largest = pools.largest_addable(sizes)
    for size in range(1, 170):
        merged = sorted([*sizes, size], reverse=True)
        assert pools.single_fits(size, largest) == pools.fits(merged), size


def test_without_a_large_only_room_every_room_is_open():
    rooms = [Room(name="A", capacity=50), Room(name="B", capacity=500)]

    assert large_only_cutoff(rooms) == NO_CUTOFF
    assert room_allows(rooms[1], 10, NO_CUTOFF)
    assert large_only_problem(rooms) is None


@pytest.mark.parametrize(
    ("rooms", "problem"),
    [
        (
            [
                Room(name="A", capacity=500, large_only=True),
                Room(name="B", capacity=400, large_only=True),
            ],
            "Only one room may be marked LargeOnly",
        ),
        (
            [Room(name="A", capacity=300, large_only=True), Room("B", 300)],
            "must seat more than every other room",
        ),
    ],
)
def test_large_only_marks_must_name_one_strictly_largest_room(rooms, problem):
    assert problem in (large_only_problem(rooms) or "")


def _promote(
    seated: dict[str, tuple[int, str]],
    rooms: dict[str, int],
    large_only: str | None = None,
) -> dict[str, str]:
    """Promote exams (unit → (size, room)) among ``rooms`` (name → capacity)."""
    room_list = [
        Room(name=name, capacity=cap, large_only=name == large_only)
        for name, cap in rooms.items()
    ]
    return promote_to_larger_rooms(
        {unit: room for unit, (_, room) in seated.items()},
        {unit: size for unit, (size, _) in seated.items()},
        room_list,
        large_only_cutoff(room_list),
    )


def test_promotion_reuses_the_room_a_promoted_exam_leaves():
    # X (48 of 50) takes the free 90; Y (27 of 30) then takes X's old 50.
    assert _promote({"X": (48, "A"), "Y": (27, "B")}, {"A": 50, "B": 30, "C": 90}) == {
        "X": "C",
        "Y": "A",
    }


def test_fullest_exam_gets_a_contested_room_first():
    # Both may use C; X is fuller (40/40 against 45/50), so Y keeps B.
    assert _promote({"X": (40, "A"), "Y": (45, "B")}, {"A": 40, "B": 50, "C": 80}) == {
        "X": "C",
        "Y": "B",
    }


def test_promotion_takes_the_largest_room_within_twice_the_exam():
    rooms = {"A": 50, "B": 60, "C": 100, "D": 101}

    assert _promote({"X": (50, "A")}, rooms) == {"X": "C"}


def test_promotion_never_uses_the_large_only_room():
    # Hall would seat X within twice its size, but X is below the cutoff (150).
    seated = {"X": (100, "R"), "Y": (140, "Big")}
    rooms = {"R": 100, "Big": 150, "Hall": 200}

    assert _promote(seated, rooms, large_only="Hall") == {"X": "R", "Y": "Big"}


@pytest.mark.parametrize("seed", range(200))
def test_promotion_only_moves_up_within_the_rules_until_nothing_can_move(seed):
    rng = random.Random(seed)  # noqa: S311 - reproducible test data
    rooms = _random_rooms(rng) + [
        Room(name=f"S{i}", capacity=rng.randint(10, 95)) for i in range(4)
    ]
    cutoff = large_only_cutoff(rooms)
    free = list(rooms)
    plan: dict[str, str] = {}
    sizes: dict[str, int] = {}
    for unit in range(rng.randint(1, 6)):
        size = rng.randint(5, 160)
        allowed = [room for room in free if room_allows(room, size, cutoff)]
        if allowed:
            room = rng.choice(allowed)
            free.remove(room)
            plan[f"u{unit}"], sizes[f"u{unit}"] = room.name, size
    by_name = {room.name: room for room in rooms}

    promoted = promote_to_larger_rooms(plan, sizes, rooms, cutoff)

    assert promoted.keys() == plan.keys()
    assert len(set(promoted.values())) == len(promoted)
    for unit, name in promoted.items():
        old, new, size = by_name[plan[unit]], by_name[name], sizes[unit]
        assert room_allows(new, size, cutoff)
        assert new == old or old.capacity < new.capacity <= PROMOTION_FACTOR * size
    # Done: no exam has a larger allowed free room within twice its size.
    still_free = [room for room in rooms if room.name not in promoted.values()]
    for unit, name in promoted.items():
        size, current = sizes[unit], by_name[name].capacity
        assert not any(
            current < room.capacity <= PROMOTION_FACTOR * size
            and room_allows(room, size, cutoff)
            for room in still_free
        ), unit
