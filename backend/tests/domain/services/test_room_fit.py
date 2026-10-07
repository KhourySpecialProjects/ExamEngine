"""The large-only room rule's seating check against brute force (EXENG-164)."""

import random
from itertools import permutations

import pytest

from src.domain.models import Room
from src.domain.services.room_fit import (
    NO_CUTOFF,
    RoomPools,
    large_only_cutoff,
    large_only_problem,
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
