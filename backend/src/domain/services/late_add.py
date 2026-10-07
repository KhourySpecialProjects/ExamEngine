"""Late add: place one exam into a saved schedule without moving anything.

Pure domain code (no DB, no S3). Every block in the base run's window is
evaluated for the late exam against the fixed base schedule: free rooms,
student and instructor hard conflicts, back-to-backs and the large-course-late
rule. `search_placements` ranks the blocks; `evaluate_placement` evaluates one
block and is what the save step re-runs before storing the late exam.

Counting (the Validator's rule, EXENG-81): each person's existing exams count
once per distinct (unit, block) on a day. For students the unit is the exam
unit: a combined group, else the CRN. For instructors it is the time group: a
common group (a combined group listed partly in one joins it whole), else a
combined group, else the CRN. So the CRNs of one combined exam, and the rooms of
one common exam, count once, while two separate exams in one block count twice.
The late exam is always one more exam for its students and instructor, also
in a block where they already sit an exam.

Rooms follow the large-only rule (`room_fit`): when rooms.csv marks a room
LargeOnly, a late exam larger than every other room (the cutoff) may only use
that room, and any other late exam may never use it.

Deliberately independent of the schedulers and of the Validator: it must not
re-seat existing exams, and the Validator must stay a separate re-check of
what late add stores.
"""

import math
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence, Set
from dataclasses import dataclass, field
from enum import StrEnum
from functools import cached_property

from src.domain.constants import EARLY_WEEK_CUTOFF, LARGE_COURSE_THRESHOLD


Slot = tuple[int, int]


class Outcome(StrEnum):
    CLEAR = "clear"
    LEAST_CONFLICTS = "least_conflicts"
    NO_ROOM = "no_room"


@dataclass(frozen=True)
class BaseExam:
    """One CRN of the base schedule. Unscheduled/unroomed rows occupy nothing."""

    crn: str
    course_code: str
    instructor: str | None
    size: int
    day: int | None = None
    block: int | None = None
    room: str | None = None

    @property
    def slot(self) -> Slot | None:
        if self.day is None or self.block is None:
            return None
        return (self.day, self.block)


@dataclass(frozen=True)
class LateExam:
    crn: str
    course_code: str
    instructor_id: str
    students: frozenset[str]

    @property
    def size(self) -> int:
        return len(self.students)


@dataclass(frozen=True)
class LateAddSettings:
    """The base run's resolved settings that late add uses."""

    max_days: int
    blocks_per_day: int
    student_max_per_day: int
    instructor_max_per_day: int


@dataclass(frozen=True)
class BaseSchedule:
    exams: Sequence[BaseExam]
    students_by_crn: Mapping[str, Set[str]]
    """Unfiltered enrollments: every CRN in enrollments.csv."""
    rooms: Mapping[str, int]
    """Room name → capacity."""
    blockouts: Mapping[str, Set[Slot]]
    """Room name → blocked (day, block) slots."""
    settings: LateAddSettings
    combined_groups: Mapping[str, Sequence[str]] = field(default_factory=dict)
    """Dataset combined groups (`course_merges`): label → CRNs."""
    common_groups: Mapping[str, Sequence[str]] = field(default_factory=dict)
    """Dataset common exam groups: label → CRNs as listed."""
    large_only_room: str | None = None
    """The room rooms.csv marks LargeOnly, if any."""

    @cached_property
    def large_only_cutoff(self) -> float:
        """Exams over this size use only the large-only room, and only they do.

        The largest other room's capacity; infinite without a large-only room.
        """
        if self.large_only_room not in self.rooms:
            return math.inf
        return max(
            (cap for name, cap in self.rooms.items() if name != self.large_only_room),
            default=0,
        )

    def room_allowed(self, room: str, size: int) -> bool:
        """True if the large-only rule lets `room` seat `size` (capacity aside)."""
        return (room == self.large_only_room) == (size > self.large_only_cutoff)

    def group_units(self) -> tuple[dict[str, str], dict[str, str]]:
        """(CRN → exam unit, CRN → time group) for every grouped CRN.

        A CRN missing from a map is its own unit and time group. The first
        group listing a CRN wins; a listed CRN of a combined group brings the
        whole combined group into its common group.
        """
        combined_label: dict[str, str] = {}
        for label, crns in self.combined_groups.items():
            for crn in crns:
                combined_label.setdefault(crn, label)
        exam_unit = {crn: f"combined:{label}" for crn, label in combined_label.items()}
        time_group = dict(exam_unit)
        common_label: dict[str, str] = {}
        for label, listed in self.common_groups.items():
            crns = set(listed)
            for crn in listed:
                merge = combined_label.get(crn)
                if merge is not None:
                    crns.update(self.combined_groups[merge])
            for crn in crns:
                common_label.setdefault(crn, label)
        for crn, label in common_label.items():
            time_group[crn] = f"common:{label}"
        return exam_unit, time_group


@dataclass(frozen=True)
class RoomOption:
    name: str
    capacity: int


@dataclass(frozen=True)
class ConflictCounts:
    """Counts for one block; keys match `late_additions[].conflicts`."""

    student_double_book: int
    student_over_daily_limit: int
    instructor_double_book: int
    instructor_over_daily_limit: int
    back_to_back_students: int
    back_to_back_instructor: int
    large_course_late: int

    @property
    def hard(self) -> int:
        return (
            self.student_double_book
            + self.student_over_daily_limit
            + self.instructor_double_book
            + self.instructor_over_daily_limit
        )

    def as_dict(self) -> dict[str, int]:
        return {
            "student_double_book": self.student_double_book,
            "student_over_daily_limit": self.student_over_daily_limit,
            "instructor_double_book": self.instructor_double_book,
            "instructor_over_daily_limit": self.instructor_over_daily_limit,
            "back_to_back_students": self.back_to_back_students,
            "back_to_back_instructor": self.back_to_back_instructor,
            "large_course_late": self.large_course_late,
        }


@dataclass(frozen=True)
class BlockEvaluation:
    """The late exam placed in one block of the base schedule.

    People maps are keyed by student ID. "Day blocks" are the sorted distinct
    blocks that person has an exam in on this day, including the late exam's.
    """

    day: int
    block: int
    best_room: RoomOption | None
    """Smallest free, unblocked, allowed room that seats the late exam."""
    other_rooms: tuple[RoomOption, ...]
    """The other fitting free allowed rooms, smallest first."""
    largest_free_room: RoomOption | None
    """Largest free, unblocked room the large-only rule allows, fitting or not
    (for No room)."""
    student_double_book: Mapping[str, tuple[str, ...]]
    """Student → base CRNs they sit in this block."""
    student_over_daily_limit: Mapping[str, int]
    """Student → exams that day including the late one, when over the limit."""
    student_back_to_back: Mapping[str, tuple[int, ...]]
    """Student → day blocks, when an exam is in an adjacent block."""
    student_day_blocks: Mapping[str, tuple[int, ...]]
    """Day blocks of every late student with another exam that day."""
    instructor_double_book: tuple[str, ...]
    """Base CRNs of the instructor in this block."""
    instructor_exams_that_day: int
    """Instructor's exams that day including the late one."""
    instructor_over_daily_limit: bool
    instructor_back_to_back: bool
    instructor_day_blocks: tuple[int, ...]
    """Empty when the instructor has no other exam that day."""
    large_course_late: bool

    @property
    def fitting_rooms(self) -> tuple[RoomOption, ...]:
        if self.best_room is None:
            return ()
        return (self.best_room, *self.other_rooms)

    def fits_room(self, room: str) -> bool:
        return any(option.name == room for option in self.fitting_rooms)

    @property
    def counts(self) -> ConflictCounts:
        return ConflictCounts(
            student_double_book=len(self.student_double_book),
            student_over_daily_limit=len(self.student_over_daily_limit),
            instructor_double_book=int(bool(self.instructor_double_book)),
            instructor_over_daily_limit=int(self.instructor_over_daily_limit),
            back_to_back_students=len(self.student_back_to_back),
            back_to_back_instructor=int(self.instructor_back_to_back),
            large_course_late=int(self.large_course_late),
        )

    @property
    def is_clear(self) -> bool:
        """No student or instructor hard conflict and a fitting free room."""
        return self.best_room is not None and self.counts.hard == 0

    @property
    def rank_key(self) -> tuple[int, ...]:
        c = self.counts
        return (
            c.student_double_book,
            c.student_over_daily_limit,
            c.instructor_double_book,
            c.instructor_over_daily_limit,
            c.back_to_back_students,
            c.back_to_back_instructor,
            c.large_course_late,
            self.day,
            self.block,
        )


@dataclass(frozen=True)
class PlacementSearch:
    outcome: Outcome
    candidates: tuple[BlockEvaluation, ...]
    """Ranked: the clear blocks (Clear), every block with a fitting free room
    (Least conflicts), or none (No room)."""
    blocks: tuple[BlockEvaluation, ...]
    """Every block in the window, in day/block order."""
    instructor_exams: tuple[BaseExam, ...]
    """Base exams whose instructor matches the late exam's instructor ID."""
    sibling_sections: tuple[BaseExam, ...]
    """Base exams with the late exam's course code (information only)."""


def instructor_key(value: str | None) -> str | None:
    """Trimmed instructor value; blank and "nan" (EXENG-79) never match."""
    if value is None:
        return None
    key = value.strip()
    if not key or key.lower() == "nan":
        return None
    return key


def in_window(settings: LateAddSettings, day: int, block: int) -> bool:
    return 0 <= day < settings.max_days and 0 <= block < settings.blocks_per_day


def search_placements(base: BaseSchedule, late: LateExam) -> PlacementSearch:
    """Evaluate every block of the base run's window and rank them."""
    index = _Index.build(base, late)
    settings = base.settings
    blocks = tuple(
        index.evaluate(day, block)
        for day in range(settings.max_days)
        for block in range(settings.blocks_per_day)
    )
    clear = [ev for ev in blocks if ev.is_clear]
    if clear:
        outcome, candidates = Outcome.CLEAR, clear
    else:
        candidates = [ev for ev in blocks if ev.best_room is not None]
        outcome = Outcome.LEAST_CONFLICTS if candidates else Outcome.NO_ROOM
    return PlacementSearch(
        outcome=outcome,
        candidates=tuple(sorted(candidates, key=lambda ev: ev.rank_key)),
        blocks=blocks,
        instructor_exams=_sorted_exams(index.instructor_exams),
        sibling_sections=_sorted_exams(
            exam
            for exam in base.exams
            if exam.course_code.strip() == late.course_code.strip()
        ),
    )


def evaluate_placement(
    base: BaseSchedule, late: LateExam, day: int, block: int
) -> BlockEvaluation:
    """Evaluate one block; raises ValueError outside the base run's window."""
    if not in_window(base.settings, day, block):
        raise ValueError(
            f"Day {day}, block {block} is outside the schedule's window "
            f"({base.settings.max_days} days × {base.settings.blocks_per_day} blocks)"
        )
    return _Index.build(base, late).evaluate(day, block)


def _sorted_exams(exams: Iterable[BaseExam]) -> tuple[BaseExam, ...]:
    return tuple(
        sorted(
            exams,
            key=lambda e: (e.slot is None, e.slot or (0, 0), e.crn),
        )
    )


@dataclass
class _Index:
    """Base schedule views restricted to the late exam's people."""

    base: BaseSchedule
    late: LateExam
    # slot → rooms used by placed base exams
    occupied: dict[Slot, set[str]] = field(default_factory=lambda: defaultdict(set))
    # student → slot → base CRNs they sit there (late students only)
    student_slots: dict[str, dict[Slot, list[str]]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(list))
    )
    # student → slot → the exam units (combined group, else CRN) they sit there
    student_units: dict[str, dict[Slot, set[str]]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(set))
    )
    # slot → base CRNs of the late exam's instructor
    instructor_slots: dict[Slot, list[str]] = field(
        default_factory=lambda: defaultdict(list)
    )
    # slot → the instructor's time groups there (common, combined group or CRN)
    instructor_groups: dict[Slot, set[str]] = field(
        default_factory=lambda: defaultdict(set)
    )
    instructor_exams: list[BaseExam] = field(default_factory=list)

    @classmethod
    def build(cls, base: BaseSchedule, late: LateExam) -> "_Index":
        index = cls(base=base, late=late)
        exam_unit, time_group = base.group_units()
        instructor = instructor_key(late.instructor_id)
        for exam in base.exams:
            matched = instructor is not None and instructor_key(exam.instructor) == (
                instructor
            )
            if matched:
                index.instructor_exams.append(exam)
            slot = exam.slot
            if slot is None:
                continue
            if exam.room:
                index.occupied[slot].add(exam.room)
            if matched:
                index.instructor_slots[slot].append(exam.crn)
                index.instructor_groups[slot].add(
                    time_group.get(exam.crn, f"crn:{exam.crn}")
                )
            enrolled = base.students_by_crn.get(exam.crn, ())
            unit = exam_unit.get(exam.crn, f"crn:{exam.crn}")
            for student in late.students.intersection(enrolled):
                index.student_slots[student][slot].append(exam.crn)
                index.student_units[student][slot].add(unit)
        return index

    def evaluate(self, day: int, block: int) -> BlockEvaluation:
        slot = (day, block)
        settings = self.base.settings
        size = self.late.size

        free = sorted(
            (
                RoomOption(name, capacity)
                for name, capacity in self.base.rooms.items()
                if name not in self.occupied.get(slot, ())
                and slot not in self.base.blockouts.get(name, ())
                and self.base.room_allowed(name, size)
            ),
            key=lambda room: (room.capacity, room.name),
        )
        fitting = [room for room in free if room.capacity >= size]

        double_book: dict[str, tuple[str, ...]] = {}
        over_limit: dict[str, int] = {}
        back_to_back: dict[str, tuple[int, ...]] = {}
        day_blocks: dict[str, tuple[int, ...]] = {}
        for student, slots in self.student_slots.items():
            if slot in slots:
                double_book[student] = tuple(sorted(slots[slot]))
            blocks = {b for d, b in slots if d == day}
            if not blocks:
                continue
            day_blocks[student] = tuple(sorted(blocks | {block}))
            sittings = sum(
                len(units)
                for (d, _), units in self.student_units[student].items()
                if d == day
            )
            if sittings + 1 > settings.student_max_per_day:
                over_limit[student] = sittings + 1
            if block - 1 in blocks or block + 1 in blocks:
                back_to_back[student] = day_blocks[student]

        instructor_blocks = {b for d, b in self.instructor_slots if d == day}
        instructor_exams_that_day = (
            sum(
                len(groups)
                for (d, _), groups in self.instructor_groups.items()
                if d == day
            )
            + 1
        )

        return BlockEvaluation(
            day=day,
            block=block,
            best_room=fitting[0] if fitting else None,
            other_rooms=tuple(fitting[1:]),
            largest_free_room=max(
                free, key=lambda room: (room.capacity, room.name), default=None
            ),
            student_double_book=double_book,
            student_over_daily_limit=over_limit,
            student_back_to_back=back_to_back,
            student_day_blocks=day_blocks,
            instructor_double_book=tuple(sorted(self.instructor_slots.get(slot, ()))),
            instructor_exams_that_day=instructor_exams_that_day,
            instructor_over_daily_limit=(
                instructor_exams_that_day > settings.instructor_max_per_day
            ),
            instructor_back_to_back=(
                block - 1 in instructor_blocks or block + 1 in instructor_blocks
            ),
            instructor_day_blocks=(
                tuple(sorted(instructor_blocks | {block})) if instructor_blocks else ()
            ),
            large_course_late=(
                size >= LARGE_COURSE_THRESHOLD and day >= EARLY_WEEK_CUTOFF
            ),
        )
