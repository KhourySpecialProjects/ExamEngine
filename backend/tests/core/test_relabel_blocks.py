"""Startup relabel of saved data from the legacy exam block times."""

from sqlalchemy.orm import Session

from src.core.relabel_blocks import relabel_block_times
from src.domain.constants import EXAM_BLOCKS, LEGACY_EXAM_BLOCKS
from src.schemas.db import DayEnum, TimeSlots
from tests.db.builders import make_schedule, make_user, save_analysis


def _slot(db: Session, dataset_id, block) -> TimeSlots:
    slot = TimeSlots(
        slot_label=block.label,
        day=DayEnum.Monday,
        start_time=block.start,
        end_time=block.end,
        dataset_id=dataset_id,
    )
    db.add(slot)
    db.flush()
    return slot


def _state(db: Session, slots, schedule, analysis):
    db.expire_all()
    return (
        [(s.slot_label, s.start_time, s.end_time) for s in slots],
        analysis.conflicts,
        schedule.run.parameters,
        schedule.run.dataset.file_paths,
    )


def test_legacy_blocks_become_the_current_block_with_the_same_index(db_session):
    owner = make_user(db_session)
    schedule = make_schedule(
        db_session,
        owner,
        parameters={
            "max_days": 5,
            "late_additions": [
                {
                    "crn": "900",
                    "block": 4,
                    "block_time": "7PM-9PM",
                    "conflicts": {
                        "students": [
                            {
                                "blocks": [3, 4],
                                "block_times": ["4:30PM-6:30PM", "7PM-9PM"],
                            }
                        ],
                        "instructor": {
                            "day_blocks": [4],
                            "day_block_times": ["7PM-9PM"],
                        },
                    },
                }
            ],
        },
    )
    dataset = schedule.run.dataset
    dataset.file_paths = [
        {"type": "courses", "storage_key": "k/courses.csv", "metadata": {}},
        {
            "type": "room_blockouts",
            "storage_key": "k/room_blockouts.csv",
            "metadata": {
                "total_blockout_entries": 3,
                "blockout_slots": {"Monday": {"9AM-11AM": 2, "2PM-4PM": 1}},
            },
        },
    ]
    legacy = [_slot(db_session, dataset.dataset_id, b) for b in LEGACY_EXAM_BLOCKS]
    current = _slot(db_session, dataset.dataset_id, EXAM_BLOCKS[0])
    analysis = save_analysis(
        db_session,
        schedule,
        {
            "hard_conflicts": {
                "student_double_book": [
                    {
                        "entity_id": "s1",
                        "day": "Monday",
                        "block": 0,
                        "block_time": "9AM-11AM",
                    }
                ]
            },
            "soft_conflicts": {
                "back_to_back_students": [
                    {
                        "day": "Monday",
                        "blocks": [0, 1],
                        "block_times": ["9AM-11AM", "11:30AM-1:30PM"],
                    }
                ],
                "large_courses_not_early": [
                    {"crn": "100", "block": 2, "block_time": "2PM-4PM"}
                ],
            },
            "statistics": {"total_conflicts": 2},
        },
    )

    relabel_block_times(db_session.connection())
    after = _state(db_session, [*legacy, current], schedule, analysis)

    slots, conflicts, parameters, file_paths = after
    assert slots == [(b.label, b.start, b.end) for b in (*EXAM_BLOCKS, EXAM_BLOCKS[0])]
    assert conflicts == {
        "hard_conflicts": {
            "student_double_book": [
                {
                    "entity_id": "s1",
                    "day": "Monday",
                    "block": 0,
                    "block_time": "8AM-10AM",
                }
            ]
        },
        "soft_conflicts": {
            "back_to_back_students": [
                {
                    "day": "Monday",
                    "blocks": [0, 1],
                    "block_times": ["8AM-10AM", "10:30AM-12:30PM"],
                }
            ],
            "large_courses_not_early": [
                {"crn": "100", "block": 2, "block_time": "1PM-3PM"}
            ],
        },
        "statistics": {"total_conflicts": 2},
    }
    late = parameters["late_additions"][0]
    assert parameters["max_days"] == 5
    assert late["block_time"] == "6PM-8PM"
    assert late["conflicts"] == {
        "students": [{"blocks": [3, 4], "block_times": ["3:30PM-5:30PM", "6PM-8PM"]}],
        "instructor": {"day_blocks": [4], "day_block_times": ["6PM-8PM"]},
    }
    assert file_paths[0] == {
        "type": "courses",
        "storage_key": "k/courses.csv",
        "metadata": {},
    }
    assert file_paths[1]["metadata"] == {
        "total_blockout_entries": 3,
        "blockout_slots": {"Monday": {"8AM-10AM": 2, "1PM-3PM": 1}},
    }

    # A second startup finds nothing left to change.
    relabel_block_times(db_session.connection())
    assert _state(db_session, [*legacy, current], schedule, analysis) == after
