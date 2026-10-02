"""Derived views of a snapshot shared by the checks.

Each view is computed on first use and reused by later checks of the same run.
Accessors for files raise CheckSkipped when the file is not available, so a
check simply asks for what it needs.
"""

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from functools import cached_property
from typing import Any

from src.domain.constants import BLOCK_TIMES, DAY_NAMES
from src.domain.validation.results import CheckSkipped
from src.domain.validation.snapshot import (
    CourseRecord,
    DatasetFiles,
    EnrollmentRecord,
    RoomRecord,
    RunParameters,
    ScheduleRow,
    ValidationSnapshot,
)


FILES_UNAVAILABLE = "The dataset's uploaded files are no longer available."
NO_BLOCKOUT_FILE = "No room blockout file was uploaded."
NO_ANALYSIS = "This schedule has no stored conflict analysis."

_FILE_NAMES = {
    "courses": "courses",
    "enrollments": "enrollments",
    "rooms": "rooms",
    "room_blockouts": "room blockout",
}

Slot = tuple[int, int]


def unreadable_summary(file_type: str) -> str:
    name = _FILE_NAMES.get(file_type, file_type)
    return f"The uploaded {name} file could not be read."


def slot_label(day: int, block: int) -> str:
    """'Monday 9AM-11AM'; indices outside the calendar are shown as numbers."""
    if 0 <= day < len(DAY_NAMES) and block in BLOCK_TIMES:
        return f"{DAY_NAMES[day]} {BLOCK_TIMES[block]}"
    return f"day {day}, block {block}"


def day_label(day: int) -> str:
    return DAY_NAMES[day] if 0 <= day < len(DAY_NAMES) else f"day {day}"


def unit_label(unit: str) -> str:
    """Human name of an exam unit or time group id."""
    kind, _, name = unit.partition(":")
    if kind == "crn":
        return f"CRN {name}"
    return f"{kind} group '{name}'"


def crn_list(crns: Iterable[str]) -> str:
    return ", ".join(f"CRN {crn}" for crn in sorted(crns))


@dataclass(frozen=True)
class UnscheduledEntry:
    """A well-formed stored `unscheduled_groups` entry."""

    index: int
    kind: str
    label: str
    reason: str
    crns: frozenset[str]


class ValidationContext:
    """A snapshot plus lazily computed indexes over it."""

    def __init__(self, snapshot: ValidationSnapshot):
        self.snapshot = snapshot

    @property
    def params(self) -> RunParameters:
        return self.snapshot.parameters

    # ------------------------------------------------------------------
    # Inputs that may be unavailable
    # ------------------------------------------------------------------

    def files(self) -> DatasetFiles:
        if self.snapshot.files is None:
            raise CheckSkipped(FILES_UNAVAILABLE)
        return self.snapshot.files

    def courses(self) -> tuple[CourseRecord, ...]:
        courses = self.files().courses
        if courses is None:
            raise CheckSkipped(unreadable_summary("courses"))
        return courses

    def enrollments(self) -> tuple[EnrollmentRecord, ...]:
        enrollments = self.files().enrollments
        if enrollments is None:
            raise CheckSkipped(unreadable_summary("enrollments"))
        return enrollments

    def rooms(self) -> tuple[RoomRecord, ...]:
        rooms = self.files().rooms
        if rooms is None:
            raise CheckSkipped(unreadable_summary("rooms"))
        return rooms

    def blockouts(self) -> Mapping[str, frozenset[Slot]]:
        files = self.files()
        if not files.blockouts_uploaded:
            raise CheckSkipped(NO_BLOCKOUT_FILE)
        if files.blockouts is None:
            raise CheckSkipped(unreadable_summary("room_blockouts"))
        return files.blockouts

    def analysis(self) -> Mapping[str, Any]:
        if self.snapshot.analysis is None:
            raise CheckSkipped(NO_ANALYSIS)
        return self.snapshot.analysis

    # ------------------------------------------------------------------
    # Schedule rows
    # ------------------------------------------------------------------

    @cached_property
    def placed_rows(self) -> list[ScheduleRow]:
        return [row for row in self.snapshot.rows if row.placed]

    @cached_property
    def rows_by_crn(self) -> dict[str, list[ScheduleRow]]:
        rows: dict[str, list[ScheduleRow]] = defaultdict(list)
        for row in self.snapshot.rows:
            rows[row.crn].append(row)
        return dict(rows)

    @cached_property
    def placements(self) -> dict[str, set[Slot]]:
        """CRN -> the (day, block) slots its rows are placed in."""
        slots: dict[str, set[Slot]] = defaultdict(set)
        for row in self.placed_rows:
            slots[row.crn].add(row.slot)
        return dict(slots)

    # ------------------------------------------------------------------
    # Combined / common groups and exam units
    # ------------------------------------------------------------------

    @cached_property
    def combined_label_by_crn(self) -> dict[str, str]:
        labels: dict[str, str] = {}
        for label, crns in self.snapshot.combined_groups.items():
            for crn in crns:
                labels.setdefault(crn, label)
        return labels

    @cached_property
    def common_group_crns(self) -> dict[str, frozenset[str]]:
        """Common label -> its CRNs, closed over combined groups.

        A listed CRN that belongs to a combined group brings the whole combined
        group into the common group.
        """
        groups: dict[str, frozenset[str]] = {}
        for label, listed in self.snapshot.common_groups.items():
            crns = set(listed)
            for crn in listed:
                merge = self.combined_label_by_crn.get(crn)
                if merge is not None:
                    crns.update(self.snapshot.combined_groups[merge])
            groups[label] = frozenset(crns)
        return groups

    @cached_property
    def common_label_by_crn(self) -> dict[str, str]:
        labels: dict[str, str] = {}
        for label, crns in self.common_group_crns.items():
            for crn in crns:
                labels.setdefault(crn, label)
        return labels

    def exam_unit(self, crn: str) -> str:
        """Student exam unit: a combined group, or the CRN on its own."""
        merge = self.combined_label_by_crn.get(crn)
        return f"combined:{merge}" if merge is not None else f"crn:{crn}"

    def time_group(self, crn: str) -> str:
        """Instructor time unit: a common group, a combined group, or the CRN."""
        common = self.common_label_by_crn.get(crn)
        if common is not None:
            return f"common:{common}"
        return self.exam_unit(crn)

    @cached_property
    def unscheduled_entries(self) -> tuple[list[UnscheduledEntry], list[str]]:
        """(well-formed stored unscheduled_groups entries, problems with others)."""
        entries: list[UnscheduledEntry] = []
        malformed: list[str] = []
        for index, raw in enumerate(self.snapshot.unscheduled_groups):
            if not isinstance(raw, Mapping):
                malformed.append(f"Unscheduled entry #{index + 1} is not an object")
                continue
            kind, label = raw.get("kind"), raw.get("group")
            reason, crns = raw.get("reason"), raw.get("crns")
            if (
                not isinstance(kind, str)
                or not isinstance(label, str)
                or not isinstance(crns, list)
            ):
                malformed.append(
                    f"Unscheduled entry #{index + 1} lacks kind, group or crns"
                )
                continue
            entries.append(
                UnscheduledEntry(
                    index=index,
                    kind=kind,
                    label=label,
                    reason=reason.strip() if isinstance(reason, str) else "",
                    crns=frozenset(str(crn) for crn in crns),
                )
            )
        return entries, malformed

    @cached_property
    def unscheduled_crns_with_reason(self) -> set[str]:
        return {
            crn
            for entry in self.unscheduled_entries[0]
            if entry.reason
            for crn in entry.crns
        }

    def combined_group_listed_unscheduled(self, label: str) -> bool:
        """Listed itself, or inside a listed common group (reported once there)."""
        members = set(self.snapshot.combined_groups.get(label, ()))
        for entry in self.unscheduled_entries[0]:
            if entry.kind == "combined" and entry.label == label:
                return True
            if entry.kind == "common" and members & entry.crns:
                return True
        return False

    def common_group_listed_unscheduled(self, label: str) -> bool:
        return any(
            entry.kind == "common" and entry.label == label
            for entry in self.unscheduled_entries[0]
        )

    # ------------------------------------------------------------------
    # Files
    # ------------------------------------------------------------------

    @cached_property
    def course_by_crn(self) -> dict[str, CourseRecord]:
        """The courses-file row the app uses for each CRN.

        Rows with zero/blank enrollment are dropped before scheduling and the
        last remaining row of a CRN wins; a CRN with only zero rows maps to its
        last row.
        """
        chosen: dict[str, CourseRecord] = {}
        for course in self.courses():
            current = chosen.get(course.crn)
            if (
                current is None
                or course.total_enrollment
                or not current.total_enrollment
            ):
                chosen[course.crn] = course
        return chosen

    @cached_property
    def zero_enrollment_crns(self) -> set[str]:
        return {
            crn
            for crn, course in self.course_by_crn.items()
            if not course.total_enrollment
        }

    @cached_property
    def students_by_crn(self) -> dict[str, set[str]]:
        students: dict[str, set[str]] = defaultdict(set)
        for enrollment in self.enrollments():
            students[enrollment.crn].add(enrollment.student_id)
        return dict(students)

    def enrollment_of(self, row: ScheduleRow) -> int:
        """Seats a row needs: the courses file's total, else the stored count."""
        files = self.snapshot.files
        if files is not None and files.courses is not None:
            course = self.course_by_crn.get(row.crn)
            if course is not None and course.total_enrollment is not None:
                return course.total_enrollment
        return row.enrollment_count

    @cached_property
    def file_room_capacity(self) -> dict[str, int] | None:
        """Room -> capacity from the rooms file (last row wins), if readable."""
        files = self.snapshot.files
        if files is None or files.rooms is None:
            return None
        return {room.name: room.capacity for room in files.rooms}

    # ------------------------------------------------------------------
    # Who sits / supervises what, when
    # ------------------------------------------------------------------

    @cached_property
    def student_slot_units(self) -> dict[str, dict[Slot, set[str]]]:
        """Student -> slot -> the student exam units they sit there."""
        schedule: dict[str, dict[Slot, set[str]]] = defaultdict(
            lambda: defaultdict(set)
        )
        students_by_crn = self.students_by_crn
        for crn, slots in self.placements.items():
            unit = self.exam_unit(crn)
            for student in students_by_crn.get(crn, ()):
                for slot in slots:
                    schedule[student][slot].add(unit)
        return schedule

    @cached_property
    def instructor_slot_groups(self) -> dict[str, dict[Slot, set[str]]]:
        """Instructor -> slot -> the time groups they have there.

        The instructor of a CRN is the courses file's (stripped) instructor;
        CRNs without one are ignored.
        """
        schedule: dict[str, dict[Slot, set[str]]] = defaultdict(
            lambda: defaultdict(set)
        )
        courses = self.course_by_crn
        for crn, slots in self.placements.items():
            course = courses.get(crn)
            if course is None or not course.instructor:
                continue
            group = self.time_group(crn)
            for slot in slots:
                schedule[course.instructor][slot].add(group)
        return schedule
