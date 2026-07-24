"""
Regression tests for schedule summary counts.

The generate endpoint builds its summary from the in-memory ScheduleResult,
while the retrieve endpoint rebuilds it from persisted assignment rows. Both
must report the SAME num_classes / unplaced_exams for the same schedule.

An exam is "unplaced" when it lacks a usable slot+room. Two disjoint cases:
  - unroomed: has a slot but every room was blocked/full (ScheduleResult.unassigned)
  - unscheduled merge: a merge group that could not be scheduled at all
    (ScheduleResult.unscheduled_merges); its CRNs get neither slot nor room.

These previously diverged: generate counted only `unassigned`, while retrieve
also counted the null-slot unscheduled-merge rows. See _summarize_placement and
_calculate_summary_stats.
"""

from types import SimpleNamespace

from src.domain.services.scheduler import ScheduleResult
from src.services.schedule.service import ScheduleService


def _make_result() -> tuple[ScheduleResult, dict[str, list[str]], dict[str, object]]:
    """Placed P1/P2, unroomed UR (slot, no room), unscheduled merge mg1 -> M1/M2."""
    result = ScheduleResult(
        assignments={"P1": (0, 0), "P2": (0, 1), "UR": (1, 0)},
        room_assignments={"P1": "Room A", "P2": "Room B"},  # UR has no room
        conflicts=[],
        colors={},
        unassigned={"UR"},
        unscheduled_merges={"mg1"},
    )
    merges = {"mg1": ["M1", "M2"]}
    courses = {crn: object() for crn in ("P1", "P2", "UR", "M1", "M2")}
    return result, merges, courses


def _persisted_rows_from(result, merges, courses):
    """Mirror _save_exam_assignments: the rows retrieve would later count."""
    day = SimpleNamespace(value="Monday")
    slot = SimpleNamespace(day=day, slot_label="9AM-11AM")
    room = SimpleNamespace(location="Room A")
    course = SimpleNamespace(enrollment_count=10)
    rows = []
    for crn in result.assignments:
        has_room = crn in result.room_assignments and crn not in result.unassigned
        rows.append(
            SimpleNamespace(
                time_slot=slot,
                room=room if has_room else None,
                course=course,
            )
        )
    for merge_id in result.unscheduled_merges:
        for crn in merges.get(merge_id, []):
            if crn in courses:
                rows.append(SimpleNamespace(time_slot=None, room=None, course=course))
    return rows


class TestSummarizePlacement:
    def test_counts_unscheduled_merges_and_unroomed_as_unplaced(self):
        result, merges, courses = _make_result()

        num_classes, unplaced = ScheduleService._summarize_placement(
            result, merges, courses
        )

        # 3 with slots (P1, P2, UR) + 2 unscheduled-merge CRNs (M1, M2)
        assert num_classes == 5
        # unroomed UR + unscheduled-merge M1, M2
        assert unplaced == 3

    def test_no_merges_counts_only_assignments(self):
        result, _, courses = _make_result()
        result.unscheduled_merges = set()

        num_classes, unplaced = ScheduleService._summarize_placement(
            result, {}, courses
        )

        assert num_classes == 3  # P1, P2, UR
        assert unplaced == 1  # UR only

    def test_none_merges_does_not_crash(self):
        result, _, courses = _make_result()
        # Defensive: helper must tolerate merges being None (the crash root cause).
        num_classes, unplaced = ScheduleService._summarize_placement(
            result, None, courses
        )
        # With no merge mapping, unscheduled-merge CRNs are unknown -> excluded.
        assert num_classes == 3
        assert unplaced == 1

    def test_generate_and_retrieve_counts_agree(self):
        """The core invariant: generate (result-based) == retrieve (row-based)."""
        result, merges, courses = _make_result()

        gen_classes, gen_unplaced = ScheduleService._summarize_placement(
            result, merges, courses
        )

        rows = _persisted_rows_from(result, merges, courses)
        retrieve_summary = ScheduleService._calculate_summary_stats(
            ScheduleService.__new__(ScheduleService), rows, {"total": 0}
        )

        assert gen_classes == retrieve_summary["num_classes"]
        assert gen_unplaced == retrieve_summary["unplaced_exams"]
