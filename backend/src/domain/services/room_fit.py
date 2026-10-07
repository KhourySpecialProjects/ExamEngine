"""Which rooms may seat which exams.

A room seats one exam (a room unit: a lone section or a whole combined group)
at a time, never over capacity. A dataset may mark one room large-only
(rooms.csv ``LargeOnly``): it must seat more than every other room, and it
takes exactly the exams that no other room can, i.e. those larger than the
**cutoff** (the largest other room's capacity). Every other exam must use an
ordinary room.

The two kinds of room therefore form separate pools: exams above the cutoff
compete only for the large-only room, the rest only for ordinary rooms. Within
a pool, a room that fits an exam also fits every smaller one, so seating stays
a simple largest-first matching (``seats_fit``).

Without a large-only room the cutoff is infinite and every room is ordinary.
"""

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from src.domain.models import Room


NO_CUTOFF = math.inf


def large_only_problem(rooms: Iterable[Room]) -> str | None:
    """Why the rooms' large-only marks are invalid, or None if they are valid.

    At most one room may be large-only, and it must seat strictly more than
    every other room. ``rooms`` should hold one entry per room name.
    """
    rooms = list(rooms)
    marked = [room for room in rooms if room.large_only]
    if len(marked) > 1:
        names = ", ".join(room.name for room in marked)
        return f"Only one room may be marked LargeOnly; found {len(marked)}: {names}"
    if not marked:
        return None
    large = marked[0]
    bigger = [
        room
        for room in rooms
        if not room.large_only and room.capacity >= large.capacity
    ]
    if bigger:
        other = max(bigger, key=lambda room: room.capacity)
        return (
            f"LargeOnly room {large.name} ({large.capacity:g} seats) must seat more "
            f"than every other room, but {other.name} seats {other.capacity:g}"
        )
    return None


def large_only_cutoff(rooms: Iterable[Room]) -> float:
    """Exams larger than this use only the large-only room, and only they do.

    The largest ordinary room's capacity (0 if every room is large-only), or
    ``NO_CUTOFF`` when no room is large-only.
    """
    rooms = list(rooms)
    if not any(room.large_only for room in rooms):
        return NO_CUTOFF
    return max((room.capacity for room in rooms if not room.large_only), default=0)


def room_allows(room: Room, size: int, cutoff: float) -> bool:
    """True if ``room`` may seat an exam of ``size`` students."""
    return size <= room.capacity and room.large_only == (size > cutoff)


def seats_fit(sizes_desc: Sequence[int], capacities_desc: Sequence[int]) -> bool:
    """True if every exam can have its own room at least its size.

    Both lists are sorted largest first. Rooms that fit an exam also fit every
    smaller exam, so a seating exists iff the k-th largest exam fits the k-th
    largest room for every k.
    """
    return len(sizes_desc) <= len(capacities_desc) and all(
        size <= capacity
        for size, capacity in zip(sizes_desc, capacities_desc, strict=False)
    )


def _largest_addable(placed_desc: Sequence[int], caps_desc: Sequence[int]) -> float:
    """Largest exam that can join ``placed_desc`` in rooms ``caps_desc`` (−1: none).

    Fitting is monotone in size and only changes at room capacities, so the
    answer is the largest capacity that still fits (binary search).
    """
    candidates = sorted(set(caps_desc))
    best: float = -1
    lo, hi = 0, len(candidates) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if seats_fit(sorted([*placed_desc, candidates[mid]], reverse=True), caps_desc):
            best = candidates[mid]
            lo = mid + 1
        else:
            hi = mid - 1
    return best


@dataclass(frozen=True)
class RoomPools:
    """Capacities of the rooms open at one time, split by the large-only rule.

    ``ordinary`` and ``large_only`` are sorted largest first.
    """

    ordinary: tuple[int, ...]
    large_only: tuple[int, ...]
    cutoff: float

    @classmethod
    def of(cls, rooms: Iterable[Room], cutoff: float) -> "RoomPools":
        ordinary: list[int] = []
        large_only: list[int] = []
        for room in rooms:
            (large_only if room.large_only else ordinary).append(room.capacity)
        return cls(
            ordinary=tuple(sorted(ordinary, reverse=True)),
            large_only=tuple(sorted(large_only, reverse=True)),
            cutoff=cutoff,
        )

    def _split(self, sizes_desc: Sequence[int]) -> int:
        """Number of leading exams above the cutoff."""
        return next(
            (i for i, size in enumerate(sizes_desc) if size <= self.cutoff),
            len(sizes_desc),
        )

    def fits(self, sizes_desc: Sequence[int]) -> bool:
        """True if every exam can have its own allowed room (largest first)."""
        k = self._split(sizes_desc)
        return seats_fit(sizes_desc[:k], self.large_only) and seats_fit(
            sizes_desc[k:], self.ordinary
        )

    def largest_addable(self, placed_desc: Sequence[int]) -> tuple[float, float]:
        """Largest single exam each pool can still take (−1: none).

        Returns (ordinary pool, large-only pool) given the exams already placed
        (largest first). An exam of size s fits iff s <= the first value when
        s <= cutoff, else s <= the second.
        """
        k = self._split(placed_desc)
        return (
            _largest_addable(placed_desc[k:], self.ordinary),
            _largest_addable(placed_desc[:k], self.large_only),
        )

    def single_fits(self, size: int, largest: tuple[float, float]) -> bool:
        """True if one more exam of ``size`` fits, given ``largest_addable``."""
        return size <= (largest[1] if size > self.cutoff else largest[0])
