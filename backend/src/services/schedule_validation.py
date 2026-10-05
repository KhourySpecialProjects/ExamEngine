"""Load a schedule for validation and stream the run as NDJSON.

The snapshot is built completely (database rows and the dataset's uploaded
files) before streaming starts, so the stream never uses the database session.
The stream carries check results only, never file contents.
"""

import json
import logging
import time
from collections.abc import Iterator, Mapping
from typing import Any
from uuid import UUID

from src.domain.constants import BLOCK_TIMES, DAY_NAMES
from src.domain.validation import (
    STATUSES,
    CheckFinished,
    CheckResult,
    DatasetFiles,
    RunParameters,
    ScheduleRow,
    ValidationSnapshot,
    run_checks,
)
from src.domain.validation.catalog import Check
from src.domain.validation.snapshot import late_additions_from_stored
from src.repo.conflict_analyses import ConflictAnalysesRepo
from src.repo.dataset import DatasetRepo
from src.repo.exam_assignment import ExamAssignmentRepo
from src.repo.schedule import ScheduleRepo
from src.schemas.db import Datasets, ExamAssignments
from src.services.dataset.uploaded_files import load_uploaded_files, stored_groups
from src.services.storage import storage


logger = logging.getLogger("examengine.validation")

_DAY_INDEX = {name: index for index, name in enumerate(DAY_NAMES)}
_BLOCK_INDEX = {label: index for index, label in BLOCK_TIMES.items()}
_LOGGED_EXAMPLES = 5


class ScheduleValidationService:
    """Builds validation snapshots for schedules the user may view."""

    def __init__(
        self,
        schedule_repo: ScheduleRepo,
        exam_assignment_repo: ExamAssignmentRepo,
        conflict_analyses_repo: ConflictAnalysesRepo,
        dataset_repo: DatasetRepo,
    ):
        self.schedule_repo = schedule_repo
        self.exam_assignment_repo = exam_assignment_repo
        self.conflict_analyses_repo = conflict_analyses_repo
        self.dataset_repo = dataset_repo

    async def build_snapshot(
        self, schedule_id: UUID, user_id: UUID
    ) -> ValidationSnapshot | None:
        """Snapshot of a schedule, or None if it doesn't exist or isn't viewable.

        The dataset is loaded by id, regardless of its owner, only after the
        schedule-view check (owner or shared with the user) has passed.
        """
        schedule = self.schedule_repo.get_with_run_details(schedule_id, user_id)
        if schedule is None:
            return None
        run = schedule.run

        assignments = self.exam_assignment_repo.get_all_for_schedule(schedule_id)
        analysis = self.conflict_analyses_repo.get_by_schedule_id(schedule_id)
        dataset = self.dataset_repo.get_by_id(run.dataset_id)

        return ValidationSnapshot(
            rows=tuple(_schedule_row(assignment) for assignment in assignments),
            parameters=RunParameters.from_stored(run.parameters),
            late_additions=late_additions_from_stored(run.parameters),
            # A detached plain-JSON copy of the stored analysis.
            analysis=(
                json.loads(json.dumps(analysis.conflicts))
                if analysis is not None
                else None
            ),
            combined_groups=stored_groups(dataset.course_merges if dataset else None),
            common_groups=stored_groups(
                dataset.common_exam_groups if dataset else None
            ),
            files=await _load_files(dataset, schedule_id),
        )


def _schedule_row(assignment: ExamAssignments) -> ScheduleRow:
    slot, room, course = assignment.time_slot, assignment.room, assignment.course
    return ScheduleRow(
        crn=str(course.crn),
        day_index=_DAY_INDEX[slot.day.value] if slot is not None else None,
        block_index=_BLOCK_INDEX[slot.slot_label] if slot is not None else None,
        room=room.location if room is not None else None,
        room_capacity=room.capacity if room is not None else None,
        enrollment_count=course.enrollment_count,
        instructor=course.instructor_name,
        course_code=course.course_subject_code,
    )


async def _load_files(
    dataset: Datasets | None, schedule_id: UUID
) -> DatasetFiles | None:
    """Download and parse the dataset's uploaded files.

    None when the dataset is deleted or any needed file cannot be downloaded.
    """
    return await load_uploaded_files(
        dataset, storage, f"Validation of schedule {schedule_id}"
    )


# ----------------------------------------------------------------------
# NDJSON stream
# ----------------------------------------------------------------------


def _line(event: Mapping[str, Any]) -> bytes:
    return (json.dumps(event) + "\n").encode()


def _log_result(
    check: Check, result: CheckResult, schedule_id: UUID, user_id: UUID
) -> None:
    if result.error is not None:
        logger.error(
            "Validation check crashed: schedule=%s user=%s check=%s",
            schedule_id,
            user_id,
            check.id,
            exc_info=result.error,
        )
    elif result.status == "fail":
        logger.warning(
            "Validation check failed: schedule=%s user=%s check=%s count=%d "
            "examples=%s",
            schedule_id,
            user_id,
            check.id,
            result.count,
            list(result.examples[:_LOGGED_EXAMPLES]),
        )


def validation_stream(
    snapshot: ValidationSnapshot, schedule_id: UUID, user_id: UUID
) -> Iterator[bytes]:
    """NDJSON lines: start/result per check in catalog order, then done.

    A synchronous generator: the web framework iterates it in a worker thread,
    so the CPU-bound checks never block the event loop. An unexpected error
    ends the stream with an `error` event.
    """
    started = time.perf_counter()
    counts = dict.fromkeys(STATUSES, 0)
    try:
        for event in run_checks(snapshot):
            if not isinstance(event, CheckFinished):
                yield _line({"type": "start", "check_id": event.check.id})
                continue
            result = event.result
            counts[result.status] += 1
            _log_result(event.check, result, schedule_id, user_id)
            yield _line(
                {
                    "type": "result",
                    "check_id": event.check.id,
                    "status": result.status,
                    "summary": result.summary,
                    "count": result.count,
                    "examples": list(result.examples),
                }
            )
    except Exception:
        logger.exception(
            "Validation of schedule %s for user %s stopped", schedule_id, user_id
        )
        yield _line(
            {"type": "error", "message": "Validation stopped by an internal error."}
        )
        return

    duration_ms = round((time.perf_counter() - started) * 1000)
    logger.info(
        "Validated schedule %s for user %s in %d ms: %d pass, %d warn, %d fail, "
        "%d skipped",
        schedule_id,
        user_id,
        duration_ms,
        counts["pass"],
        counts["warn"],
        counts["fail"],
        counts["skipped"],
    )
    yield _line({"type": "done", "counts": counts, "duration_ms": duration_ms})
