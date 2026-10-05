"""One student's or instructor's exams in a saved schedule.

Instructors come from the saved assignments (the course row's instructor ID).
Students need the enrollments, which are never stored in the database, so they
come from the dataset's uploaded files. Access is the schedule-view check
(owner or shared with the user), like the Validator.
"""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from src.core.exceptions import DatasetDeletedError, StorageError, ValidationError
from src.domain.constants import BLOCK_TIMES, DAY_NAMES
from src.domain.services.late_add import instructor_key
from src.domain.validation.snapshot import ENROLLMENTS
from src.repo.dataset import DatasetRepo
from src.repo.exam_assignment import ExamAssignmentRepo
from src.repo.schedule import ScheduleRepo
from src.schemas.db import ExamAssignments
from src.services.dataset.uploaded_files import load_uploaded_files
from src.services.schedule.summary import resolve_settings
from src.services.storage.interface import IStorage


PersonKind = Literal["student", "instructor"]

_DAY_INDEX = {name: index for index, name in enumerate(DAY_NAMES)}
_BLOCK_INDEX = {label: index for index, label in BLOCK_TIMES.items()}


class PersonExam(BaseModel):
    crn: str
    course_code: str
    day: int | None
    """Day index, Monday = 0; None when the exam is unscheduled."""
    day_name: str | None
    block: int | None
    """Block index, 0 = the first block of the day; None when unscheduled."""
    block_time: str | None
    room: str | None
    """None when the exam has no room (unscheduled or unroomed)."""


class PersonExamsResponse(BaseModel):
    kind: PersonKind
    person_id: str
    exams: list[PersonExam]
    """Scheduled exams by day and block (then CRN), then unscheduled ones."""
    days: list[str]
    """The schedule's exam days, Monday first, for drawing its week."""
    block_times: list[str]
    """The schedule's blocks per day, earliest first."""


class PersonExamsService:
    """Looks up one person's exams in a schedule the user may view."""

    def __init__(
        self,
        schedule_repo: ScheduleRepo,
        exam_assignment_repo: ExamAssignmentRepo,
        dataset_repo: DatasetRepo,
        storage: IStorage,
    ):
        self.schedule_repo = schedule_repo
        self.exam_assignment_repo = exam_assignment_repo
        self.dataset_repo = dataset_repo
        self.storage = storage

    async def get(
        self, schedule_id: UUID, user_id: UUID, kind: PersonKind, person_id: str
    ) -> PersonExamsResponse | None:
        """The person's exams, or None if the schedule isn't viewable.

        An ID with no exams in the schedule gets an empty list. Raises
        `ValidationError` for a blank ID, and for students `DatasetDeletedError`
        when the dataset was deleted and `StorageError` when its enrollments
        file can't be read.
        """
        person_id = person_id.strip()
        if not person_id:
            raise ValidationError("Enter a student or instructor ID.")
        schedule = self.schedule_repo.get_with_run_details(schedule_id, user_id)
        if schedule is None:
            return None
        run = schedule.run
        assignments = self.exam_assignment_repo.get_all_for_schedule(schedule_id)

        if kind == "instructor":
            mine = [
                a
                for a in assignments
                if instructor_key(a.course.instructor_name) == person_id
            ]
        else:
            crns = await self._student_crns(run.dataset_id, schedule_id, person_id)
            mine = [a for a in assignments if str(a.course.crn).strip() in crns]

        settings, _ = resolve_settings(run.algorithm_name, run.parameters)
        slots = [slot for a in assignments if (slot := _slot(a)) is not None]
        day_count = max([settings.get("max_days") or 0, *(day + 1 for day, _ in slots)])
        block_count = max(
            [settings["blocks_per_day"], *(block + 1 for _, block in slots)]
        )
        exams = sorted((_exam(a) for a in mine), key=_exam_order)
        return PersonExamsResponse(
            kind=kind,
            person_id=person_id,
            exams=exams,
            days=DAY_NAMES[: min(day_count, len(DAY_NAMES))],
            block_times=[
                BLOCK_TIMES[b] for b in range(min(block_count, len(BLOCK_TIMES)))
            ],
        )

    async def _student_crns(
        self, dataset_id: UUID, schedule_id: UUID, student_id: str
    ) -> set[str]:
        dataset = self.dataset_repo.get_by_id(dataset_id)
        if dataset is None or dataset.deleted_at is not None:
            raise DatasetDeletedError(
                "The dataset's uploaded files are no longer available, so its "
                "students' exams can't be looked up."
            )
        files = await load_uploaded_files(
            dataset, self.storage, f"Person exams on schedule {schedule_id}"
        )
        if (
            files is None
            or files.enrollments is None
            or ENROLLMENTS in files.unreadable
        ):
            raise StorageError(
                "Could not read the dataset's uploaded enrollments file."
            )
        return {
            record.crn.strip()
            for record in files.enrollments
            if record.student_id.strip() == student_id
        }


def _slot(assignment: ExamAssignments) -> tuple[int, int] | None:
    slot = assignment.time_slot
    if slot is None:
        return None
    return _DAY_INDEX[slot.day.value], _BLOCK_INDEX[slot.slot_label]


def _exam(assignment: ExamAssignments) -> PersonExam:
    course, room = assignment.course, assignment.room
    slot = _slot(assignment)
    day, block = slot if slot else (None, None)
    return PersonExam(
        crn=str(course.crn),
        course_code=course.course_subject_code,
        day=day,
        day_name=DAY_NAMES[day] if day is not None else None,
        block=block,
        block_time=BLOCK_TIMES[block] if block is not None else None,
        room=room.location if room is not None else None,
    )


def _exam_order(exam: PersonExam) -> tuple[bool, int, int, str]:
    return (exam.day is None, exam.day or 0, exam.block or 0, exam.crn)
