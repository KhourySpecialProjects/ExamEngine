"""Immutable inputs of a schedule validation run.

A snapshot holds everything the checks read: the schedule as stored in the
database and the dataset's original uploaded files, parsed. It is built in full
before any check runs, so checks never touch the database or storage.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from src.domain.constants import BLOCKS_PER_DAY


# Defaults used by schedule generation when a run parameter is missing
# (ScheduleService.generate_schedule and the /schedule/generate route).
DEFAULT_MAX_DAYS = 7
DEFAULT_STUDENT_MAX_PER_DAY = 3
DEFAULT_INSTRUCTOR_MAX_PER_DAY = 3

COURSES = "courses"
ENROLLMENTS = "enrollments"
ROOMS = "rooms"
ROOM_BLOCKOUTS = "room_blockouts"


@dataclass(frozen=True)
class ScheduleRow:
    """One stored exam assignment with the course and room data stored with it.

    `day_index`/`block_index` are None when the exam has no time slot; `room` is
    None when it has no room. `course_code` is the stored course subject code.
    """

    crn: str
    day_index: int | None
    block_index: int | None
    room: str | None
    room_capacity: int | None
    enrollment_count: int
    instructor: str | None
    course_code: str | None = None

    @property
    def placed(self) -> bool:
        return self.day_index is not None and self.block_index is not None

    @property
    def slot(self) -> tuple[int, int]:
        """(day_index, block_index) of a placed row."""
        if self.day_index is None or self.block_index is None:
            raise ValueError(f"CRN {self.crn} has no time slot")
        return self.day_index, self.block_index


@dataclass(frozen=True)
class RunParameters:
    """Generation parameters the schedule was built with."""

    max_days: int = DEFAULT_MAX_DAYS
    blocks_per_day: int = BLOCKS_PER_DAY
    student_max_per_day: int = DEFAULT_STUDENT_MAX_PER_DAY
    instructor_max_per_day: int = DEFAULT_INSTRUCTOR_MAX_PER_DAY

    @classmethod
    def from_stored(cls, parameters: Mapping[str, Any] | None) -> "RunParameters":
        """Read a run's stored `parameters`, defaulting missing keys."""
        stored = parameters or {}
        defaults = cls()
        return cls(
            max_days=int(stored.get("max_days", defaults.max_days)),
            blocks_per_day=int(stored.get("blocks_per_day", defaults.blocks_per_day)),
            student_max_per_day=int(
                stored.get("student_max_per_day", defaults.student_max_per_day)
            ),
            instructor_max_per_day=int(
                stored.get("instructor_max_per_day", defaults.instructor_max_per_day)
            ),
        )


def late_additions_from_stored(parameters: Mapping[str, Any] | None) -> tuple[Any, ...]:
    """The raw `late_additions` entries of a run's stored `parameters`.

    Late-add versions record each exam added after generation here; generated
    schedules have none. Entries are kept as stored (claims the checks re-verify).
    """
    entries = (parameters or {}).get("late_additions")
    return tuple(entries) if isinstance(entries, list) else ()


@dataclass(frozen=True)
class CourseRecord:
    """One row of the courses file. `total_enrollment` is None when blank."""

    crn: str
    total_enrollment: int | None
    instructor: str | None


@dataclass(frozen=True)
class EnrollmentRecord:
    """One row of the enrollments file."""

    student_id: str
    crn: str


@dataclass(frozen=True)
class RoomRecord:
    """One row of the rooms file (``large_only``: the LargeOnly column says yes)."""

    name: str
    capacity: int
    large_only: bool = False


@dataclass(frozen=True)
class DatasetFiles:
    """The dataset's uploaded files, parsed.

    A file that could not be read is None and its type is in `unreadable`.
    `blockouts` is None when no blockout file was uploaded
    (`blockouts_uploaded` False) or it could not be read.
    """

    courses: tuple[CourseRecord, ...] | None
    enrollments: tuple[EnrollmentRecord, ...] | None
    rooms: tuple[RoomRecord, ...] | None
    blockouts: Mapping[str, frozenset[tuple[int, int]]] | None
    blockouts_uploaded: bool
    unreadable: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class ValidationSnapshot:
    """Everything one validation run reads.

    `analysis` is the stored `conflict_analyses.conflicts` JSON, or None when the
    schedule has no stored analysis. `files` is None when the dataset's uploaded
    files are no longer available. `late_additions` holds the run's stored
    late-add records (raw JSON entries); empty for generated schedules.
    """

    rows: tuple[ScheduleRow, ...]
    parameters: RunParameters
    analysis: Mapping[str, Any] | None
    combined_groups: Mapping[str, tuple[str, ...]]
    common_groups: Mapping[str, tuple[str, ...]]
    files: DatasetFiles | None
    late_additions: tuple[Any, ...] = ()

    @property
    def unscheduled_groups(self) -> list[Any]:
        """Stored unscheduled combined/common groups (raw JSON entries)."""
        if not self.analysis:
            return []
        entries = self.analysis.get("unscheduled_groups") or []
        return list(entries) if isinstance(entries, list) else []
