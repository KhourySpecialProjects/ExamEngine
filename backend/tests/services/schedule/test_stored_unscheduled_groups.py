"""Unscheduled combined/common groups read back from a saved schedule."""

from types import SimpleNamespace

from src.services.schedule.service import ScheduleService


GROUP = {
    "kind": "combined",
    "group": "Oversize Combined 01",
    "reason": "Combined enrollment 419 exceeds the largest room capacity 400",
    "crns": ["20016", "20022"],
}


def test_saved_groups_are_returned():
    analysis = SimpleNamespace(
        conflicts={"hard_conflicts": {}, "unscheduled_groups": [GROUP]}
    )

    assert ScheduleService._stored_unscheduled_groups(analysis) == [GROUP]


def test_schedule_saved_before_groups_were_stored_has_none():
    analysis = SimpleNamespace(conflicts={"hard_conflicts": {}, "soft_conflicts": {}})

    assert ScheduleService._stored_unscheduled_groups(analysis) == []


def test_schedule_without_analysis_has_none():
    assert ScheduleService._stored_unscheduled_groups(None) == []
