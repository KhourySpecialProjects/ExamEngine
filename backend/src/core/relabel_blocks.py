"""Relabel saved exam blocks from the legacy block times to the current ones.

Saved data from before the block times were corrected carries the legacy
labels and clock times (`LEGACY_EXAM_BLOCKS`). Block indices never changed, so
each legacy block becomes the current block with the same index:

- `time_slots`: label, start and end time (every schedule's exams point here,
  so the schedule view, summaries and the CSV export follow).
- `conflict_analyses.conflicts`, `runs.parameters` (late additions) and the
  room blockout counts in `datasets.file_paths`: label strings.

Idempotent: legacy and current start times and labels never overlap, so a
second run finds nothing to change.
"""

import logging
from collections.abc import Callable
from typing import Any

from sqlalchemy import Connection, String, or_, select, update
from sqlalchemy.orm import InstrumentedAttribute

from src.domain.constants import EXAM_BLOCKS, LEGACY_EXAM_BLOCKS
from src.schemas.db import ConflictAnalyses, Datasets, Runs, TimeSlots


logger = logging.getLogger("examengine.relabel_blocks")

CURRENT_LABEL = {
    legacy.label: current.label
    for legacy, current in zip(LEGACY_EXAM_BLOCKS, EXAM_BLOCKS, strict=True)
}
# JSON keys whose values are block labels (a string or a list of strings).
_LABEL_KEYS = frozenset({"block_time", "block_times", "day_block_times"})
# Rows whose JSON text holds a legacy label somewhere.
_LEGACY_PATTERNS = [f'%"{label}"%' for label in CURRENT_LABEL]


def relabel_block_times(connection: Connection) -> None:
    """Rewrite every saved legacy block label and time; logs what changed."""
    slots = _relabel_time_slots(connection)
    analyses = _relabel_json(
        connection,
        ConflictAnalyses.analysis_id,
        ConflictAnalyses.conflicts,
        _relabel_values,
    )
    runs = _relabel_json(connection, Runs.run_id, Runs.parameters, _relabel_values)
    datasets = _relabel_json(
        connection, Datasets.dataset_id, Datasets.file_paths, _relabel_blockout_slots
    )
    if slots or analyses or runs or datasets:
        logger.info(
            "Relabeled legacy exam block times: %d time slots, %d conflict "
            "analyses, %d runs, %d datasets",
            slots,
            analyses,
            runs,
            datasets,
        )


def _relabel_time_slots(connection: Connection) -> int:
    changed = 0
    for legacy, current in zip(LEGACY_EXAM_BLOCKS, EXAM_BLOCKS, strict=True):
        result = connection.execute(
            update(TimeSlots)
            .where(
                TimeSlots.start_time == legacy.start,
                TimeSlots.end_time == legacy.end,
            )
            .values(
                slot_label=current.label, start_time=current.start, end_time=current.end
            )
        )
        changed += result.rowcount
    return changed


def _relabel_json(
    connection: Connection,
    key: InstrumentedAttribute[Any],
    column: InstrumentedAttribute[Any],
    relabel: Callable[[Any], Any],
) -> int:
    has_legacy = or_(*(column.cast(String).like(p) for p in _LEGACY_PATTERNS))
    rows = connection.execute(select(key, column).where(has_legacy)).all()
    changed = 0
    for row_key, value in rows:
        relabeled = relabel(value)
        if relabeled != value:
            connection.execute(
                update(key.class_).where(key == row_key).values({column: relabeled})
            )
            changed += 1
    return changed


def _relabel_values(value: Any) -> Any:
    """Copy of `value` with the legacy labels under `_LABEL_KEYS` replaced."""
    if isinstance(value, dict):
        return {
            k: _current_labels(v) if k in _LABEL_KEYS else _relabel_values(v)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_relabel_values(item) for item in value]
    return value


def _current_labels(value: Any) -> Any:
    if isinstance(value, str):
        return CURRENT_LABEL.get(value, value)
    if isinstance(value, list):
        return [_current_labels(item) for item in value]
    return value


def _relabel_blockout_slots(file_paths: Any) -> Any:
    """Copy of a dataset's `file_paths` with the blockout count keys relabeled.

    `metadata.blockout_slots` of the room_blockouts entry is
    `{day name: {block label: count}}`.
    """
    if not isinstance(file_paths, list):
        return file_paths
    relabeled = []
    for entry in file_paths:
        slots = (
            (entry.get("metadata") or {}).get("blockout_slots")
            if isinstance(entry, dict)
            else None
        )
        if isinstance(slots, dict):
            entry = {
                **entry,
                "metadata": {
                    **entry["metadata"],
                    "blockout_slots": {
                        day: _relabel_keys(counts) for day, counts in slots.items()
                    },
                },
            }
        relabeled.append(entry)
    return relabeled


def _relabel_keys(counts: Any) -> Any:
    if not isinstance(counts, dict):
        return counts
    result: dict[str, Any] = {}
    for label, count in counts.items():
        current = CURRENT_LABEL.get(label, label)
        result[current] = result.get(current, 0) + count
    return result
