"""
Regression tests for schedule summary counts.

The generate endpoint builds its summary from the in-memory ScheduleResult,
while the retrieve endpoint rebuilds it from persisted assignment rows. Both
must report the SAME num_classes / unplaced_exams for the same schedule.

An exam is "unplaced" when it could not be seated: its CRN is in
ScheduleResult.unscheduled_crns and gets neither slot nor room. The schedulers
never leave a placed exam without a room.

These previously diverged: generate and retrieve counted unplaced exams
differently. See _summarize_placement and _calculate_summary_stats.
"""

from types import SimpleNamespace

from src.domain.services.scheduler import ScheduleResult, UnscheduledGroup
from src.services.schedule.service import ScheduleService


def _make_result() -> ScheduleResult:
    """Placed P1/P2/P3, unscheduled group mg1 -> M1/M2."""
    return ScheduleResult(
        assignments={"P1": (0, 0), "P2": (0, 1), "P3": (1, 0)},
        room_assignments={"P1": "Room A", "P2": "Room B", "P3": "Room A"},
        conflicts=[],
        colors={},
        unscheduled_groups=[
            UnscheduledGroup(
                kind="combined", label="mg1", reason="too big", crns=["M1", "M2"]
            )
        ],
        unscheduled_crns={"M1", "M2"},
    )


def _persisted_rows_from(result):
    """Mirror _save_exam_assignments: the rows retrieve would later count."""
    day = SimpleNamespace(value="Monday")
    slot = SimpleNamespace(day=day, slot_label="9AM-11AM")
    room = SimpleNamespace(location="Room A")
    course = SimpleNamespace(enrollment_count=10)
    rows = []
    for crn in result.assignments:
        rows.append(
            SimpleNamespace(
                time_slot=slot,
                room=room if crn in result.room_assignments else None,
                course=course,
            )
        )
    for _crn in result.unscheduled_crns:
        rows.append(SimpleNamespace(time_slot=None, room=None, course=course))
    return rows


class TestSummarizePlacement:
    def test_counts_unscheduled_crns_as_unplaced(self):
        num_classes, unplaced = ScheduleService._summarize_placement(_make_result())

        # 3 placed (P1, P2, P3) + 2 unscheduled-group CRNs (M1, M2)
        assert num_classes == 5
        assert unplaced == 2

    def test_no_unscheduled_crns_means_nothing_unplaced(self):
        result = _make_result()
        result.unscheduled_groups = []
        result.unscheduled_crns = set()

        num_classes, unplaced = ScheduleService._summarize_placement(result)

        assert num_classes == 3
        assert unplaced == 0

    def test_generate_and_retrieve_counts_agree(self):
        """The core invariant: generate (result-based) == retrieve (row-based)."""
        result = _make_result()

        gen_classes, gen_unplaced = ScheduleService._summarize_placement(result)

        rows = _persisted_rows_from(result)
        retrieve_summary = ScheduleService._calculate_summary_stats(
            ScheduleService.__new__(ScheduleService), rows, {"total": 0}
        )

        assert gen_classes == retrieve_summary["num_classes"]
        assert gen_unplaced == retrieve_summary["unplaced_exams"]
