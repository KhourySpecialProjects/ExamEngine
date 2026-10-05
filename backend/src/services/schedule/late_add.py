"""Late add: find a block for one exam in a saved schedule, and save it there.

The base schedule comes from the database; enrollments and room blockouts come
from the dataset's uploaded files, parsed unfiltered, because generation drops
enrollment rows for CRNs that are not in the courses file. The placement itself
is `src.domain.services.late_add`. Saving never modifies the base: it writes a
new version (courses row, run, schedule, copied assignments + the late exam,
conflict analysis) in one transaction.
"""

import asyncio
import copy
import datetime
import uuid
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel

from src.core.exceptions import (
    DatasetDeletedError,
    PlacementConflictError,
    StorageError,
    ValidationError,
)
from src.domain.constants import BLOCK_TIMES, DAY_NAMES
from src.domain.services.late_add import (
    BaseExam,
    BaseSchedule,
    BlockEvaluation,
    LateAddSettings,
    LateExam,
    Outcome,
    RoomOption,
    evaluate_placement,
    search_placements,
)
from src.domain.services.late_add_analysis import late_exam_analysis
from src.domain.validation import DatasetFiles
from src.domain.validation.snapshot import ENROLLMENTS, ROOM_BLOCKOUTS
from src.repo.conflict_analyses import ConflictAnalysesRepo
from src.repo.course import CourseRepo
from src.repo.dataset import DatasetRepo
from src.repo.exam_assignment import ExamAssignmentRepo
from src.repo.room import RoomRepo
from src.repo.schedule import ScheduleRepo
from src.repo.time_slot import TimeSlotRepo
from src.schemas.db import Datasets, ExamAssignments, Runs, Schedules, StatusEnum, Users
from src.services.dataset.uploaded_files import load_uploaded_files
from src.services.schedule.summary import resolve_settings
from src.services.storage.interface import IStorage


DATASET_DELETED_MESSAGE = "The dataset's uploaded files are no longer available"

LATE_ADD_ALGORITHM_NAME = "Late add"
# schedules.schedule_name is String(50).
MAX_SCHEDULE_NAME_LENGTH = 50

# Generation's defaults (POST /schedule/generate) for runs that didn't record
# a setting.
_DEFAULT_MAX_DAYS = 7
_DEFAULT_STUDENT_MAX_PER_DAY = 3
_DEFAULT_INSTRUCTOR_MAX_PER_DAY = 3

_DAY_INDEX = {name: index for index, name in enumerate(DAY_NAMES)}
_BLOCK_INDEX = {label: index for index, label in BLOCK_TIMES.items()}


# ----------------------------------------------------------------------
# Response
# ----------------------------------------------------------------------


class LateAddRoom(BaseModel):
    name: str
    capacity: int


class LateAddExam(BaseModel):
    """A base-schedule exam; day/block/room are None when it is unscheduled."""

    crn: str
    course_code: str
    instructor: str | None
    size: int
    day: int | None
    day_name: str | None
    block: int | None
    block_time: str | None
    room: str | None


class LateAddConflictCounts(BaseModel):
    student_double_book: int
    student_over_daily_limit: int
    instructor_double_book: int
    instructor_over_daily_limit: int
    back_to_back_students: int
    back_to_back_instructor: int
    large_course_late: int


class StudentDoubleBook(BaseModel):
    student_id: str
    crns: list[str]


class StudentOverDailyLimit(BaseModel):
    student_id: str
    exams: int


class StudentBackToBack(BaseModel):
    student_id: str
    blocks: list[int]
    block_times: list[str]
    """Labels for `blocks`, same order."""


class LateAddStudentConflicts(BaseModel):
    double_book: list[StudentDoubleBook]
    over_daily_limit: list[StudentOverDailyLimit]
    back_to_back: list[StudentBackToBack]


class LateAddInstructorConflicts(BaseModel):
    double_book_crns: list[str]
    exams_that_day: int
    over_daily_limit: bool
    back_to_back: bool
    day_blocks: list[int]
    day_block_times: list[str]
    """Labels for `day_blocks`, same order."""


class LateAddCandidate(BaseModel):
    day: int
    day_name: str
    block: int
    block_time: str
    room: LateAddRoom
    other_rooms: list[LateAddRoom]
    clear: bool
    conflicts: LateAddConflictCounts
    students: LateAddStudentConflicts
    instructor: LateAddInstructorConflicts
    large_course_late: bool


class LateAddFreeRoom(BaseModel):
    day: int
    day_name: str
    block: int
    block_time: str
    largest_free_room: LateAddRoom | None


class LateAddWindow(BaseModel):
    max_days: int
    blocks_per_day: int
    student_max_per_day: int
    instructor_max_per_day: int


class LateAddSearchResponse(BaseModel):
    schedule_id: str
    crn: str
    course_code: str
    instructor_id: str
    size: int
    outcome: Literal["clear", "least_conflicts", "no_room"]
    settings: LateAddWindow
    candidates: list[LateAddCandidate]
    """Ranked best first; empty for no_room."""
    no_room_blocks: list[LateAddFreeRoom]
    """Every block's largest free room; only for no_room."""
    instructor_exams: list[LateAddExam]
    sibling_sections: list[LateAddExam]
    notes: list[str]


# ----------------------------------------------------------------------
# Service
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class LateAddContext:
    """Everything a late add reads, after every check has passed."""

    schedule: Schedules
    run: Runs
    dataset: Datasets
    assignments: list[ExamAssignments]
    resolved_settings: dict[str, Any]
    """`resolve_settings` of the base run (as stored in a new run's parameters)."""
    base: BaseSchedule
    late: LateExam
    notes: tuple[str, ...]


class LateAddService:
    def __init__(
        self,
        schedule_repo: ScheduleRepo,
        exam_assignment_repo: ExamAssignmentRepo,
        dataset_repo: DatasetRepo,
        room_repo: RoomRepo,
        course_repo: CourseRepo,
        time_slot_repo: TimeSlotRepo,
        conflict_analyses_repo: ConflictAnalysesRepo,
        storage: IStorage,
    ):
        self.schedule_repo = schedule_repo
        self.exam_assignment_repo = exam_assignment_repo
        self.dataset_repo = dataset_repo
        self.room_repo = room_repo
        self.course_repo = course_repo
        self.time_slot_repo = time_slot_repo
        self.conflict_analyses_repo = conflict_analyses_repo
        self.storage = storage

    async def search(
        self,
        schedule_id: UUID,
        user_id: UUID,
        crn: str,
        course_code: str,
        instructor_id: str,
    ) -> LateAddSearchResponse | None:
        """Ranked blocks for the late exam; None if the caller doesn't own it."""
        context = await self.load_context(
            schedule_id, user_id, crn, course_code, instructor_id
        )
        if context is None:
            return None
        result = await asyncio.to_thread(search_placements, context.base, context.late)
        no_room = result.outcome is Outcome.NO_ROOM
        notes = list(context.notes)
        if not result.instructor_exams:
            notes.append(
                f"Instructor ID {context.late.instructor_id} has no exams in this "
                "schedule, so instructor conflicts can't be checked. Make sure it "
                "matches the instructor column of the courses file."
            )
        settings = context.base.settings
        return LateAddSearchResponse(
            schedule_id=str(schedule_id),
            crn=context.late.crn,
            course_code=context.late.course_code,
            instructor_id=context.late.instructor_id,
            size=context.late.size,
            outcome=result.outcome.value,
            settings=LateAddWindow(
                max_days=settings.max_days,
                blocks_per_day=settings.blocks_per_day,
                student_max_per_day=settings.student_max_per_day,
                instructor_max_per_day=settings.instructor_max_per_day,
            ),
            candidates=[_candidate(ev) for ev in result.candidates],
            no_room_blocks=(
                [
                    LateAddFreeRoom(
                        **_slot_fields(ev.day, ev.block),
                        largest_free_room=_room(ev.largest_free_room),
                    )
                    for ev in result.blocks
                ]
                if no_room
                else []
            ),
            instructor_exams=[_exam(exam) for exam in result.instructor_exams],
            sibling_sections=[_exam(exam) for exam in result.sibling_sections],
            notes=notes,
        )

    async def load_context(
        self,
        schedule_id: UUID,
        user_id: UUID,
        crn: str,
        course_code: str,
        instructor_id: str,
    ) -> LateAddContext | None:
        """Check the request and load the base schedule and the late exam.

        Returns None when the schedule doesn't exist or the caller doesn't own
        it (shared viewers included). Raises `DatasetDeletedError` when the
        dataset was deleted, `ValidationError` for a blank field (a "nan"
        instructor ID counts as blank), a CRN already in the schedule, a CRN
        that courses.csv schedules with a nonzero enrollment or a CRN without
        enrollment rows, and `StorageError` when the uploaded files can't be
        read.
        """
        schedule = self.schedule_repo.get_with_run_details(schedule_id, user_id)
        if schedule is None or schedule.run.user_id != user_id:
            return None
        run = schedule.run
        dataset = self.dataset_repo.get_by_id(run.dataset_id)
        if dataset is None or dataset.deleted_at is not None:
            raise DatasetDeletedError(DATASET_DELETED_MESSAGE)

        crn, course_code, instructor_id = (
            crn.strip(),
            course_code.strip(),
            instructor_id.strip(),
        )
        blank = [
            label
            for label, value in (
                ("CRN", crn),
                ("course code", course_code),
                ("instructor ID", instructor_id),
            )
            if not value or (label == "instructor ID" and value.lower() == "nan")
        ]
        if blank:
            raise ValidationError(f"Enter the {' and '.join(blank)}.")

        assignments = self.exam_assignment_repo.get_all_for_schedule(schedule_id)
        _reject_scheduled_crn(crn, assignments)

        files = await load_uploaded_files(
            dataset, self.storage, f"Late add on schedule {schedule_id}"
        )
        _require_readable(files)
        _reject_courses_file_crn(crn, files)
        students = frozenset(r.student_id for r in files.enrollments if r.crn == crn)
        if not students:
            raise ValidationError(f"CRN {crn} has no rows in enrollments.csv.")

        resolved, _ = resolve_settings(run.algorithm_name, run.parameters)
        rooms: dict[str, int] = {
            room.location: room.capacity
            for room in self.room_repo.get_all_for_dataset(dataset.dataset_id)
        }
        students_by_crn: dict[str, set[str]] = defaultdict(set)
        for record in files.enrollments:
            students_by_crn[record.crn].add(record.student_id)

        return LateAddContext(
            schedule=schedule,
            run=run,
            dataset=dataset,
            assignments=assignments,
            resolved_settings=resolved,
            base=BaseSchedule(
                exams=[_base_exam(a) for a in assignments],
                students_by_crn=students_by_crn,
                rooms=rooms,
                blockouts=files.blockouts or {},
                settings=_late_add_settings(resolved),
                combined_groups=_groups(dataset.course_merges),
                common_groups=_groups(dataset.common_exam_groups),
            ),
            late=LateExam(
                crn=crn,
                course_code=course_code,
                instructor_id=instructor_id,
                students=students,
            ),
            notes=tuple(_courses_file_notes(crn, files)),
        )

    async def save(
        self,
        schedule_id: UUID,
        user: Users,
        *,
        crn: str,
        course_code: str,
        instructor_id: str,
        day: int,
        block: int,
        room: str,
        schedule_name: str,
        accept_conflicts: bool,
    ) -> UUID | None:
        """Save the base schedule plus the late exam as a new schedule.

        Returns the new schedule's ID, or None when the caller doesn't own the
        base (as `load_context`). The placement is re-evaluated here, never
        taken from the client. Raises `ValidationError` for a bad name or a
        block outside the window, `PlacementConflictError` when the room can't
        take the exam in that block or the block has hard conflicts that were
        not accepted, and whatever `load_context` raises. Every row is written
        in one transaction: on any error nothing is saved.
        """
        context = await self.load_context(
            schedule_id, user.user_id, crn, course_code, instructor_id
        )
        if context is None:
            return None
        name = self._checked_name(schedule_name, user.user_id)
        try:
            placement = await asyncio.to_thread(
                evaluate_placement, context.base, context.late, day, block
            )
        except ValueError as e:
            raise ValidationError(str(e)) from e
        room = room.strip()
        if not placement.fits_room(room):
            raise PlacementConflictError(_room_problem(context, placement, room))
        if not placement.is_clear and not accept_conflicts:
            raise PlacementConflictError(
                f"{_slot_text(day, block)} has hard conflicts for this exam. "
                "Confirm that you accept them to save it there."
            )

        base_analysis = self.conflict_analyses_repo.get_by_schedule_id(schedule_id)
        new_schedule_id = uuid.uuid4()
        parameters = _version_parameters(
            context, placement, room, user, new_schedule_id
        )
        db = self.schedule_repo.db
        try:
            self._write_version(
                context, placement, room, name, user, new_schedule_id, parameters
            )
            self.conflict_analyses_repo.add_analysis(
                new_schedule_id,
                late_exam_analysis(
                    base_analysis.conflicts if base_analysis is not None else None,
                    context.base,
                    context.late,
                    placement,
                    room,
                ),
            )
            db.commit()
        except Exception:
            db.rollback()
            raise
        return new_schedule_id

    def _checked_name(self, schedule_name: str, user_id: UUID) -> str:
        name = schedule_name.strip()
        if not name:
            raise ValidationError("Enter a schedule name.")
        if len(name) > MAX_SCHEDULE_NAME_LENGTH:
            raise ValidationError(
                f"Schedule names are at most {MAX_SCHEDULE_NAME_LENGTH} characters."
            )
        if self.schedule_repo.name_exists(name, user_id):
            raise ValidationError(f"Schedule name '{name}' already exists")
        return name

    def _write_version(
        self,
        context: LateAddContext,
        placement: BlockEvaluation,
        room: str,
        name: str,
        user: Users,
        new_schedule_id: UUID,
        parameters: dict[str, Any],
    ) -> None:
        """Flush the course, run, schedule and assignment rows (no commit)."""
        dataset_id = context.dataset.dataset_id
        late = context.late
        course = self.course_repo.get_or_add_late_course(
            dataset_id, late.crn, late.course_code, late.instructor_id, late.size
        )
        self.schedule_repo.add_schedule_with_run(
            schedule_name=name,
            dataset_id=dataset_id,
            user_id=user.user_id,
            algorithm_name=LATE_ADD_ALGORITHM_NAME,
            parameters=parameters,
            status=StatusEnum.Completed,
            schedule_id=new_schedule_id,
        )
        time_slot = self.time_slot_repo.get_or_create_slot(
            dataset_id=dataset_id,
            day=DAY_NAMES[placement.day],
            block_index=placement.block,
        )
        room_ids = {
            r.location: r.room_id
            for r in self.room_repo.get_all_for_dataset(dataset_id)
        }
        self.exam_assignment_repo.add_all(
            new_schedule_id,
            [
                {
                    "course_id": a.course_id,
                    "time_slot_id": a.time_slot_id,
                    "room_id": a.room_id,
                }
                for a in context.assignments
            ]
            + [
                {
                    "course_id": course.course_id,
                    "time_slot_id": time_slot.time_slot_id,
                    "room_id": room_ids[room],
                }
            ],
        )


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _slot(assignment: ExamAssignments) -> tuple[int, int] | None:
    slot = assignment.time_slot
    if slot is None:
        return None
    return _DAY_INDEX[slot.day.value], _BLOCK_INDEX[slot.slot_label]


def _base_exam(assignment: ExamAssignments) -> BaseExam:
    course = assignment.course
    slot = _slot(assignment)
    day, block = slot if slot else (None, None)
    return BaseExam(
        crn=str(course.crn).strip(),
        course_code=course.course_subject_code,
        instructor=course.instructor_name,
        size=course.enrollment_count,
        day=day,
        block=block,
        room=assignment.room.location if assignment.room is not None else None,
    )


def _reject_scheduled_crn(crn: str, assignments: list[ExamAssignments]) -> None:
    for assignment in assignments:
        if str(assignment.course.crn).strip() != crn:
            continue
        slot = _slot(assignment)
        if slot is None:
            raise ValidationError(
                f"CRN {crn} is already in this schedule, unscheduled. Late add "
                "only places CRNs that are not in the schedule."
            )
        day, block = slot
        where = f"{DAY_NAMES[day]} {BLOCK_TIMES[block]}"
        if assignment.room is not None:
            where += f" in {assignment.room.location}"
        raise ValidationError(f"CRN {crn} is already in this schedule ({where}).")


def _require_readable(files: DatasetFiles | None) -> None:
    if files is None:
        raise StorageError("Could not download the dataset's uploaded files.")
    # A missing enrollments file is unreadable; a missing blockouts file means
    # none were uploaded.
    unreadable = sorted(files.unreadable & {ENROLLMENTS, ROOM_BLOCKOUTS})
    if unreadable:
        raise StorageError(
            f"Could not read the dataset's uploaded {' and '.join(unreadable)} file."
        )


def _reject_courses_file_crn(crn: str, files: DatasetFiles) -> None:
    """A courses.csv CRN with a nonzero enrollment is a scheduled course."""
    if any(row.crn == crn and row.total_enrollment for row in files.courses or ()):
        raise ValidationError(
            f"CRN {crn} is a scheduled course in courses.csv, not a late add. "
            "Late add only places CRNs that are in enrollments.csv but not "
            "scheduled in courses.csv."
        )


def _courses_file_notes(crn: str, files: DatasetFiles) -> list[str]:
    """Only zero-enrollment courses.csv rows get here (see above)."""
    if not any(row.crn == crn for row in files.courses or ()):
        return []
    return [
        f"CRN {crn} is in courses.csv with zero enrollment, so generation skipped it."
    ]


def _groups(groups: dict[str, list[str]] | None) -> dict[str, tuple[str, ...]]:
    return {
        str(label): tuple(str(crn).strip() for crn in crns)
        for label, crns in (groups or {}).items()
    }


def _late_add_settings(resolved: dict[str, Any]) -> LateAddSettings:
    def setting(key: str, default: int) -> int:
        value = resolved.get(key)
        return int(value) if value is not None else default

    return LateAddSettings(
        max_days=setting("max_days", _DEFAULT_MAX_DAYS),
        blocks_per_day=int(resolved["blocks_per_day"]),
        student_max_per_day=setting(
            "student_max_per_day", _DEFAULT_STUDENT_MAX_PER_DAY
        ),
        instructor_max_per_day=setting(
            "instructor_max_per_day", _DEFAULT_INSTRUCTOR_MAX_PER_DAY
        ),
    )


def _slot_text(day: int, block: int) -> str:
    return f"{DAY_NAMES[day]} {BLOCK_TIMES[block]}"


def _room_problem(
    context: LateAddContext, placement: BlockEvaluation, room: str
) -> str:
    """Why `room` can't take the late exam in the placement's block."""
    base, size = context.base, context.late.size
    slot = (placement.day, placement.block)
    where = _slot_text(*slot)
    capacity = base.rooms.get(room)
    if capacity is None:
        return f"{room} is not one of this dataset's rooms."
    used_by = sorted(e.crn for e in base.exams if e.slot == slot and e.room == room)
    if used_by:
        return f"{room} is already used on {where} (CRN {', '.join(used_by)})."
    if slot in base.blockouts.get(room, ()):
        return f"{room} is blocked out on {where}."
    return f"{room} seats {capacity}, fewer than the exam's {size} students."


def _version_parameters(
    context: LateAddContext,
    placement: BlockEvaluation,
    room: str,
    user: Users,
    new_schedule_id: UUID,
) -> dict[str, Any]:
    """`runs.parameters` of the new version (see docs/DATA.md, "Late add").

    The base run's resolved settings, so legacy bases get an explicit engine
    and blocks per day; settings the base never recorded stay unrecorded.
    """
    base_params = context.run.parameters or {}
    late, day, block = context.late, placement.day, placement.block
    entry = {
        "crn": late.crn,
        "course_code": late.course_code,
        "instructor_id": late.instructor_id,
        "size": late.size,
        "day": day,
        "day_name": DAY_NAMES[day],
        "block": block,
        "block_time": BLOCK_TIMES[block],
        "room": room,
        "outcome": (
            Outcome.CLEAR if placement.is_clear else Outcome.LEAST_CONFLICTS
        ).value,
        "conflicts": placement.counts.as_dict(),
        "added_by": str(user.user_id),
        "added_by_name": user.name,
        "added_at": datetime.datetime.now().isoformat(),
        "schedule_id": str(new_schedule_id),
    }
    return {
        **{k: v for k, v in context.resolved_settings.items() if v is not None},
        "based_on_schedule_id": str(context.schedule.schedule_id),
        "original_schedule_id": str(
            base_params.get("original_schedule_id") or context.schedule.schedule_id
        ),
        "late_additions": [
            *copy.deepcopy(base_params.get("late_additions") or []),
            entry,
        ],
    }


def _slot_fields(day: int, block: int) -> dict[str, Any]:
    return {
        "day": day,
        "day_name": DAY_NAMES[day],
        "block": block,
        "block_time": BLOCK_TIMES[block],
    }


def _room(room: RoomOption | None) -> LateAddRoom | None:
    if room is None:
        return None
    return LateAddRoom(name=room.name, capacity=room.capacity)


def _exam(exam: BaseExam) -> LateAddExam:
    placed = exam.slot is not None
    return LateAddExam(
        crn=exam.crn,
        course_code=exam.course_code,
        instructor=exam.instructor,
        size=exam.size,
        day=exam.day,
        day_name=DAY_NAMES[exam.day] if placed else None,
        block=exam.block,
        block_time=BLOCK_TIMES[exam.block] if placed else None,
        room=exam.room,
    )


def _candidate(ev: BlockEvaluation) -> LateAddCandidate:
    return LateAddCandidate(
        **_slot_fields(ev.day, ev.block),
        # Candidates always have a fitting room.
        room=_room(ev.best_room),
        other_rooms=[_room(room) for room in ev.other_rooms],
        clear=ev.is_clear,
        conflicts=LateAddConflictCounts(**ev.counts.as_dict()),
        students=LateAddStudentConflicts(
            double_book=[
                StudentDoubleBook(student_id=s, crns=list(crns))
                for s, crns in sorted(ev.student_double_book.items())
            ],
            over_daily_limit=[
                StudentOverDailyLimit(student_id=s, exams=n)
                for s, n in sorted(ev.student_over_daily_limit.items())
            ],
            back_to_back=[
                StudentBackToBack(
                    student_id=s,
                    blocks=list(blocks),
                    block_times=_block_times(blocks),
                )
                for s, blocks in sorted(ev.student_back_to_back.items())
            ],
        ),
        instructor=LateAddInstructorConflicts(
            double_book_crns=list(ev.instructor_double_book),
            exams_that_day=ev.instructor_exams_that_day,
            over_daily_limit=ev.instructor_over_daily_limit,
            back_to_back=ev.instructor_back_to_back,
            day_blocks=list(ev.instructor_day_blocks),
            day_block_times=_block_times(ev.instructor_day_blocks),
        ),
        large_course_late=ev.large_course_late,
    )


def _block_times(blocks: Iterable[int]) -> list[str]:
    return [BLOCK_TIMES[block] for block in blocks]
