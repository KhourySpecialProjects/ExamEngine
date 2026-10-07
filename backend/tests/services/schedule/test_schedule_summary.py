"""The schedule summary: every number the schedule and compare pages show."""

import datetime
from types import SimpleNamespace

from src.services.schedule.summary import (
    build_schedule_summary,
    count_conflicts,
    resolve_settings,
)


def _exam(
    crn: str,
    size: int,
    day: str | None = None,
    hour: int = 9,
    room: str | None = None,
    capacity: int = 0,
) -> SimpleNamespace:
    """An assignment row: no day = unscheduled; a day but no room = unroomed."""
    slot = (
        SimpleNamespace(
            day=SimpleNamespace(value=day),
            slot_label=f"{hour}:00",
            start_time=datetime.time(hour),
        )
        if day
        else None
    )
    return SimpleNamespace(
        course=SimpleNamespace(
            crn=crn, course_subject_code=f"TEST {crn}", enrollment_count=size
        ),
        time_slot=slot,
        room=SimpleNamespace(location=room, capacity=capacity) if room else None,
    )


def _summary(
    exams, *, groups=(), merges=None, common=None, file_paths=(), parameters=None
) -> dict:
    return build_schedule_summary(
        assignments=exams,
        breakdown=[],
        unscheduled_groups=list(groups),
        run=SimpleNamespace(algorithm_name="DSATUR", parameters=parameters or {}),
        dataset=SimpleNamespace(
            file_paths=list(file_paths),
            course_merges=merges,
            common_exam_groups=common,
        ),
    )


class TestExams:
    def test_unroomed_exams_hold_a_slot_but_are_not_placed(self):
        summary = _summary(
            [
                _exam("1", 10, "Monday", 9, "A", 20),
                _exam("2", 10, "Monday", 14),
                _exam("3", 10),
            ]
        )

        assert summary["exams"]["placed"] == 1
        assert summary["exams"]["unroomed"] == 1
        assert summary["exams"]["unscheduled"] == 1
        assert summary["calendar"]["slots_used"] == 2
        assert summary["calendar"]["days"] == [
            {"day": "Monday", "exams": 1, "seats": 10}
        ]

    def test_unscheduled_crns_outside_reported_groups_are_listed(self):
        summary = _summary(
            [_exam("1", 10), _exam("2", 5)],
            groups=[{"kind": "combined", "crns": ["1"], "reason": "no room"}],
        )

        assert summary["unscheduled"]["other_crns"] == ["2"]
        assert summary["unscheduled"]["students"] == 15

    def test_fill_is_capped_per_exam_and_rounded_half_up(self):
        summary = _summary(
            [
                _exam("1", 50, "Monday", 9, "A", 40),
                _exam("2", 40, "Monday", 9, "B", 40),
                _exam("3", 20, "Monday", 9, "C", 40),
            ]
        )

        assert summary["rooms"]["average_fill"] == 83.3
        assert summary["rooms"]["used"] == 3

    def test_fill_buckets_include_their_lower_bound(self):
        sizes = [49, 50, 74, 75, 89, 90, 100]
        summary = _summary([_exam(str(s), s, "Monday", 9, f"R{s}", 100) for s in sizes])

        assert summary["rooms"]["fill_buckets"] == {
            "under_50": 1,
            "from_50_to_75": 2,
            "from_75_to_90": 2,
            "from_90_to_100": 2,
        }

    def test_rooms_without_capacity_have_no_fill_and_are_never_over(self):
        summary = _summary([_exam("1", 50, "Monday", 9, "A", 0)])

        assert summary["rooms"]["average_fill"] == 0
        assert summary["exams"]["over_capacity"] == 0

    def test_over_capacity_lists_the_largest_overflow_first(self):
        summary = _summary(
            [
                _exam("1", 45, "Monday", 9, "A", 40),
                _exam("2", 60, "Monday", 9, "B", 40),
            ]
        )

        assert [e["crn"] for e in summary["over_capacity"]] == ["2", "1"]
        assert summary["over_capacity"][0]["capacity"] == 40

    def test_calendar_orders_days_by_week_and_blocks_by_start_time(self):
        summary = _summary(
            [
                _exam("1", 10, "Wednesday", 14, "A", 20),
                _exam("2", 10, "Monday", 16, "A", 20),
                _exam("3", 10, "Monday", 9, "B", 20),
                _exam("4", 10, "Monday", 9, "C", 20),
            ]
        )
        calendar = summary["calendar"]

        assert [d["day"] for d in calendar["days"]] == ["Monday", "Wednesday"]
        assert calendar["blocks"] == [
            {"label": "9:00", "exams": 2},
            {"label": "14:00", "exams": 1},
            {"label": "16:00", "exams": 1},
        ]
        assert calendar["matrix"] == [[2, 0, 1], [0, 1, 0]]
        assert calendar["days_used"] == 2


class TestDatasetContext:
    def test_a_combined_exam_listed_in_a_common_group_is_common_as_a_whole(self):
        summary = _summary(
            [_exam("101", 10), _exam("102", 20), _exam("103", 5)],
            merges={"C1": ["101", "102"]},
            common={"G1": [" 101", "103"]},
        )

        assert summary["groups"]["combined"] == {
            "groups": 1,
            "sections": 2,
            "students": 30,
        }
        assert summary["groups"]["common"] == {
            "groups": 1,
            "sections": 3,
            "students": 35,
        }

    def test_students_and_blockouts_come_from_upload_metadata(self):
        summary = _summary(
            [],
            file_paths=[
                {"type": "enrollments", "metadata": {"unique_students": 12}},
                {
                    "type": "room_blockouts",
                    "metadata": {
                        "unique_rooms_blocked": 3,
                        "total_blockout_entries": 7,
                    },
                },
            ],
        )

        assert summary["unique_students"] == 12
        assert summary["blockouts"] == {"rooms": 3, "slots": 7}

    def test_without_metadata_students_are_unknown_and_blockouts_zero(self):
        summary = _summary([])

        assert summary["unique_students"] is None
        assert summary["blockouts"] == {"rooms": 0, "slots": 0}
        assert summary["large_only_room"] is None

    def test_large_only_room_counts_what_this_schedule_placed_there(self):
        hall = {"name": "Hall", "capacity": 300, "cutoff": 100}
        summary = _summary(
            [
                # A combined exam (two sections) and a lone section in Hall
                _exam("1", 70, "Monday", 9, "Hall", 300),
                _exam("2", 60, "Monday", 9, "Hall", 300),
                _exam("3", 150, "Tuesday", 9, "Hall", 300),
                _exam("4", 40, "Monday", 9, "R1", 50),
                _exam("5", 120),
            ],
            file_paths=[
                {"type": "rooms", "metadata": {"large_only_room": hall}},
            ],
        )

        assert summary["large_only_room"] == {
            **hall,
            "exams": 2,
            "sections": 3,
            "students": 280,
        }


def _double_book(student, day, block_time, crn, other) -> dict:
    return {
        "conflict_type": "student_double_book",
        "entity_id": student,
        "day": day,
        "block": 0,
        "block_time": block_time,
        "crn": crn,
        "conflicting_crn": other,
    }


class TestConflicts:
    def test_a_three_way_double_book_is_one_occurrence(self):
        counts = count_conflicts(
            [
                _double_book("s1", "Monday", "9AM-11AM", "1", "2"),
                _double_book("s1", "Monday", "9AM-11AM", "1", "3"),
                _double_book("s1", "Monday", "9AM-11AM", "2", "3"),
                _double_book("s1", "Tuesday", "9AM-11AM", "4", "5"),
                _double_book("s2", "Monday", "9AM-11AM", "1", "2"),
            ]
        )

        assert counts["student_double_book"] == {"people": 2, "instances": 3}

    def test_daily_limit_records_merge_by_day(self):
        record = {"conflict_type": "student_gt_max_per_day", "student_id": "s1"}
        counts = count_conflicts(
            [
                {**record, "day": "Monday", "block_time": "9AM-11AM", "crn": "1"},
                {**record, "day": "Monday", "block_time": "2PM-4PM", "crn": "2"},
                {**record, "day": "Tuesday", "block_time": "9AM-11AM", "crn": "3"},
            ]
        )

        assert counts["student_over_daily_limit"] == {"people": 1, "instances": 2}

    def test_back_to_back_counts_each_pair_of_blocks(self):
        record = {"conflict_type": "back_to_back_instructor", "entity_id": "Dr X"}
        counts = count_conflicts(
            [
                {**record, "day": "Monday", "block_times": ["9AM", "11:30AM"]},
                {**record, "day": "Monday", "block_times": ["11:30AM", "2PM"]},
            ]
        )

        assert counts["instructor_back_to_back"] == {"people": 1, "instances": 2}
        assert counts["student_back_to_back"] == {"people": 0, "instances": 0}

    def test_records_without_a_person_each_count_once(self):
        counts = count_conflicts(
            [
                _double_book(None, "Monday", "9AM-11AM", "1", "2"),
                _double_book("", "Monday", "9AM-11AM", "1", "2"),
            ]
        )

        assert counts["student_double_book"] == {"people": 2, "instances": 2}

    def test_large_courses_late_counts_distinct_exams(self):
        record = {"conflict_type": "large_course_not_early", "day": "Friday"}
        counts = count_conflicts(
            [{**record, "crn": "1"}, {**record, "crn": "1"}, {**record, "crn": "2"}]
        )

        assert counts["large_courses_late"] == {"people": 2, "instances": 3}


class TestSettings:
    def test_runs_before_settings_were_recorded(self):
        settings, assumed = resolve_settings("DSATUR", None)

        assert settings["algorithm"] == "dsatur"
        assert settings["blocks_per_day"] == 5
        assert assumed == ["blocks_per_day"]
        assert settings["max_days"] is None
        assert settings["avoid_back_to_back"] is None

    def test_recorded_settings_are_used_as_stored(self):
        params = {
            "algorithm": "annealing",
            "blocks_per_day": 4,
            "max_days": 6,
            "student_max_per_day": 2,
            "instructor_max_per_day": 3,
            "avoid_back_to_back": False,
            "prioritize_large_courses": True,
            "time_budget_seconds": 30,
        }

        settings, assumed = resolve_settings("Annealing", params)

        assert settings == params
        assert assumed == []

    def test_each_engine_lists_the_recorded_settings_it_ignores(self):
        # Classic runs record the time budget's default and avoid back-to-back
        # but use neither; Optimized ignores prioritize-large.
        classic = _summary([], parameters={"time_budget_seconds": 15})
        optimized = _summary(
            [], parameters={"algorithm": "annealing", "prioritize_large_courses": True}
        )

        assert classic["settings_unused"] == [
            "time_budget_seconds",
            "avoid_back_to_back",
        ]
        assert optimized["settings_unused"] == ["prioritize_large_courses"]
