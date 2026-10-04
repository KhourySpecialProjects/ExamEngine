"""
Schedule summary counts, built from the saved assignment rows.

Generate and GET /schedule/{id} both return this summary. An exam is
"unplaced" when its row has no slot or no room; it still counts as a class.
"""

from types import SimpleNamespace

from src.services.schedule.service import ScheduleService


def _rows(placed: int, unplaced: int) -> list[SimpleNamespace]:
    day = SimpleNamespace(value="Monday")
    slot = SimpleNamespace(day=day, slot_label="9AM-11AM")
    room = SimpleNamespace(location="Room A")
    course = SimpleNamespace(enrollment_count=10)
    return [
        SimpleNamespace(time_slot=slot, room=room, course=course) for _ in range(placed)
    ] + [
        SimpleNamespace(time_slot=None, room=None, course=course)
        for _ in range(unplaced)
    ]


def _summary(rows) -> dict:
    return ScheduleService._calculate_summary_stats(
        ScheduleService.__new__(ScheduleService), rows, {"total": 0}
    )


class TestCalculateSummaryStats:
    def test_unplaced_rows_count_as_classes_and_as_unplaced(self):
        summary = _summary(_rows(placed=3, unplaced=2))

        assert summary["num_classes"] == 5
        assert summary["unplaced_exams"] == 2

    def test_no_unplaced_rows_means_nothing_unplaced(self):
        summary = _summary(_rows(placed=3, unplaced=0))

        assert summary["num_classes"] == 3
        assert summary["unplaced_exams"] == 0
