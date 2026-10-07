"""Day and block indices of saved exams, and the week a schedule draws."""

from collections.abc import Iterable

from src.domain.constants import BLOCK_TIMES, DAY_NAMES
from src.schemas.db import ExamAssignments, Runs
from src.services.schedule.summary import resolve_settings


_DAY_INDEX = {name: index for index, name in enumerate(DAY_NAMES)}
_BLOCK_INDEX = {label: index for index, label in BLOCK_TIMES.items()}


def slot_indices(assignment: ExamAssignments) -> tuple[int, int] | None:
    """(day index, Monday = 0; block index); None when the exam is unscheduled."""
    slot = assignment.time_slot
    if slot is None:
        return None
    return _DAY_INDEX[slot.day.value], _BLOCK_INDEX[slot.slot_label]


def calendar_window(
    run: Runs, assignments: Iterable[ExamAssignments]
) -> tuple[list[str], list[str]]:
    """(day names, block times) of the schedule's week, for drawing it.

    The run's days and blocks per day, extended to the last day and block an
    exam uses (a late add may sit outside the run's window).
    """
    settings, _ = resolve_settings(run.algorithm_name, run.parameters)
    slots = [slot for a in assignments if (slot := slot_indices(a)) is not None]
    day_count = max([settings.get("max_days") or 0, *(day + 1 for day, _ in slots)])
    block_count = max([settings["blocks_per_day"], *(block + 1 for _, block in slots)])
    return (
        DAY_NAMES[: min(day_count, len(DAY_NAMES))],
        [BLOCK_TIMES[b] for b in range(min(block_count, len(BLOCK_TIMES)))],
    )
