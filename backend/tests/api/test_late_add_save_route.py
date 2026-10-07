"""POST /api/schedule/{id}/late-add against the Postgres test database (EXENG-124)."""

import asyncio
import copy
import datetime
from unittest.mock import patch

import pytest
from sqlalchemy import func, select

from src.domain.validation import CheckFinished, run_checks
from src.repo.conflict_analyses import ConflictAnalysesRepo
from src.repo.dataset import DatasetRepo
from src.repo.exam_assignment import ExamAssignmentRepo
from src.repo.schedule import ScheduleRepo
from src.repo.time_slot import TimeSlotRepo
from src.schemas.db import (
    ConflictAnalyses,
    Courses,
    ExamAssignments,
    Rooms,
    Runs,
    Schedules,
    TimeSlots,
)
from src.services.schedule_validation import ScheduleValidationService
from tests.api.test_late_add_search_route import _app, _post
from tests.db.builders import (
    make_dataset,
    make_schedule,
    make_user,
    save_analysis,
    share_schedule,
)


SETTINGS = {
    "student_max_per_day": 3,
    "instructor_max_per_day": 2,
    "avoid_back_to_back": True,
    "max_days": 1,
    "blocks_per_day": 4,
    "prioritize_large_courses": False,
    "algorithm": "dsatur",
    "time_budget_seconds": 15,
    "promote_rooms": False,
}

# (crn, course code, enrollment, instructor, block, room); block None =
# unscheduled. One day (Monday), four blocks.
BASE_EXAMS = [
    ("101", "SUBJ 1001", 2, "I-1", 0, "Hall A"),
    ("105", "SUBJ 1005", 2, "I-3", 0, "Room C"),
    ("109", "SUBJ 1009", 1, "I-3", 0, "Hall D"),
    ("102", "SUBJ 1002", 2, "I-2", 1, "Hall A"),
    ("103", "SUBJ 1003", 1, "I-2", 2, "Room C"),
    ("111", "SUBJ 1011", 1, "I-2", 2, "Hall A"),
    ("108", "SUBJ 1008", 1, "I-2", 3, "Hall D"),
    ("110", "SUBJ 1010", 1, "I-7", None, None),
]
ROOMS = {"Hall A": 50, "Room B": 5, "Room C": 10, "Hall D": 50}

FILES = {
    "k/courses.csv": b"CRN,CourseID,num_students,Instructor Name\n"
    + b"".join(
        f"{crn},{code},{size},{instructor}\n".encode()
        for crn, code, size, instructor, *_ in BASE_EXAMS
    )
    + b"950,SUBJ 9500,0,I-9\n",
    "k/enrollments.csv": b"Student_PIDM,CRN\n"
    b"S1,101\nS2,101\nS2,102\nS3,102\nS4,103\nS2,105\nS7,105\nS13,108\nS12,109\n"
    b"S15,111\nS14,110\nS1,900\nS5,900\nS3,950\nS5,950\nS5,960\n"
    + b"".join(f"B{n},990\n".encode() for n in range(60)),
    "k/rooms.csv": b"room_name,capacity\n"
    + b"".join(f"{name},{cap}\n".encode() for name, cap in ROOMS.items()),
    "k/room_blockouts.csv": b"Room,Day,Block\nRoom B,0,2\n",
}


def _hard(entity, block, crn, course, other=None, other_course=None):
    return {
        "entity_id": entity,
        "day": "Monday",
        "block": block,
        "block_time": ["8AM-10AM", "10:30AM-12:30PM", "1PM-3PM", "3:30PM-5:30PM"][
            block
        ],
        "crn": crn,
        "course": course,
        "conflicting_crn": other,
        "conflicting_course": other_course,
    }


def _b2b(key, person, blocks):
    times = ["8AM-10AM", "10:30AM-12:30PM", "1PM-3PM", "3:30PM-5:30PM"]
    return {
        key: person,
        "day": "Monday",
        "blocks": blocks,
        "block_times": [times[b] for b in blocks],
    }


# What DSATUR (Classic) stores for the base: S2 sits 101 and 105 at 8AM, I-3
# has 105 and 109 at 8AM, I-2 has 103 and 111 at 1PM and four exams (limit 2),
# one entry per exam placed while I-2 was at the limit; S2 and I-2 have
# back-to-back exams.
BASE_ANALYSIS = {
    "hard_conflicts": {
        "student_double_book": [
            _hard("S2", 0, "105", "SUBJ 1005", "101", "SUBJ 1001"),
        ],
        "instructor_double_book": [
            _hard("I-3", 0, "109", "SUBJ 1009", "105", "SUBJ 1005"),
            _hard("I-2", 2, "111", "SUBJ 1011", "103", "SUBJ 1003"),
        ],
        "student_gt_max_per_day": [],
        "instructor_gt_max_per_day": [
            _hard("I-2", 3, "108", "SUBJ 1008"),
            _hard("I-2", 2, "111", "SUBJ 1011"),
        ],
    },
    "soft_conflicts": {
        "back_to_back_students": [_b2b("student_id", "S2", [0, 1])],
        "back_to_back_instructors": [_b2b("instructor_name", "I-2", [1, 2, 3])],
        "large_courses_not_early": [],
    },
    "statistics": {
        "num_classes": 7,
        "num_students": 8,
        "num_rooms": 3,
        "slots_used": 4,
        "unplaced_exams": 0,
        "total_hard_conflicts": 5,
        "total_soft_conflicts": 2,
        "student_double_book_count": 1,
        "instructor_double_book_count": 2,
        "student_gt_max_per_day_count": 0,
        "instructor_gt_max_per_day_count": 2,
        "back_to_back_students_count": 1,
        "back_to_back_instructors_count": 1,
        "large_courses_not_early_count": 0,
    },
    "unscheduled_groups": [
        {"kind": "section", "group": "110", "reason": "No free block", "crns": ["110"]}
    ],
}

# What Annealing (Optimized) stores for the same base: people in order of
# their first CRN, and one per-day entry for each exam past the limit in
# block order.
OPTIMIZED_ANALYSIS = copy.deepcopy(BASE_ANALYSIS)
OPTIMIZED_ANALYSIS["hard_conflicts"].update(
    instructor_double_book=[
        _hard("I-2", 2, "111", "SUBJ 1011", "103", "SUBJ 1003"),
        _hard("I-3", 0, "109", "SUBJ 1009", "105", "SUBJ 1005"),
    ],
    instructor_gt_max_per_day=[
        _hard("I-2", 2, "111", "SUBJ 1011"),
        _hard("I-2", 3, "108", "SUBJ 1008"),
    ],
)

# (algorithm_name, runs.parameters, stored analysis) as generation stores them.
BASES = {
    "classic": ("DSATUR", SETTINGS, BASE_ANALYSIS),
    "optimized": (
        "Annealing",
        {**SETTINGS, "algorithm": "annealing"},
        OPTIMIZED_ANALYSIS,
    ),
}

# Late A: S1 (8AM) and I-1 (8AM) get back-to-back exams at 10:30AM; clear.
LATE_A = {
    "crn": "900",
    "course_code": "LATE 9000",
    "instructor_id": "I-1",
    "day": 0,
    "block": 1,
    "room": "Room B",
    "schedule_name": "Version 2",
    "accept_conflicts": False,
}
# Late B: a courses.csv CRN with zero enrollment; S3, S5 and I-1 all have an
# exam at 10:30AM once A is there, and I-1 is over the daily limit anywhere.
LATE_B = {
    "crn": "950",
    "course_code": "SUBJ 9500",
    "instructor_id": "I-1",
    "day": 0,
    "block": 1,
    "room": "Room C",
    "schedule_name": "Version 3",
    "accept_conflicts": True,
}

_RANK = {"pass": 0, "skipped": 1, "warn": 2, "fail": 3}


def _generated_base(
    db,
    owner,
    *,
    parameters=None,
    algorithm_name="DSATUR",
    analysis=BASE_ANALYSIS,
    room_capacities=ROOMS,
):
    """A schedule stored the way generation stores one, committed."""
    dataset = make_dataset(db, owner)
    dataset.file_paths = [
        {"type": file_type, "storage_key": f"k/{file_type}.csv", "metadata": {}}
        for file_type in ("courses", "enrollments", "rooms", "room_blockouts")
    ]
    sched = make_schedule(
        db,
        owner,
        "Base",
        dataset=dataset,
        parameters=dict(SETTINGS) if parameters is None else parameters,
        algorithm_name=algorithm_name,
    )
    rooms = {
        name: Rooms(location=name, capacity=cap, dataset_id=dataset.dataset_id)
        for name, cap in room_capacities.items()
    }
    db.add_all(rooms.values())
    slots = TimeSlotRepo(db)
    for crn, code, size, instructor, block, room in BASE_EXAMS:
        course = Courses(
            crn=crn,
            course_subject_code=code,
            instructor_name=instructor,
            enrollment_count=size,
            dataset_id=dataset.dataset_id,
        )
        db.add(course)
        db.flush()
        slot = (
            slots.get_or_create_slot(dataset.dataset_id, "Monday", block)
            if block is not None
            else None
        )
        db.add(
            ExamAssignments(
                course_id=course.course_id,
                time_slot_id=slot.time_slot_id if slot else None,
                room_id=rooms[room].room_id if room else None,
                schedule_id=sched.schedule_id,
            )
        )
    db.flush()
    save_analysis(db, sched, copy.deepcopy(analysis))
    # Committed (released savepoint), so a rollback in the code under test
    # only undoes the late add.
    db.commit()
    return sched


def _call(db, user, schedule_id, path, body, files=FILES):
    with patch("src.api.deps.storage") as storage:
        storage.download_file.side_effect = files.get
        return _post(_app(db, user), f"/api/schedule/{schedule_id}/{path}", body)


def _save(db, user, schedule_id, body, files=FILES):
    return _call(db, user, schedule_id, "late-add", body, files)


def _search(db, user, schedule_id, crn, course_code, instructor_id):
    status, body = _call(
        db,
        user,
        schedule_id,
        "late-add/search",
        {"crn": crn, "course_code": course_code, "instructor_id": instructor_id},
    )
    assert status == 200, body
    return body


def _candidate(search, day, block):
    return next(
        c for c in search["candidates"] if (c["day"], c["block"]) == (day, block)
    )


def _counts(db) -> dict[str, int]:
    return {
        model.__tablename__: db.execute(
            select(func.count()).select_from(model)
        ).scalar_one()
        for model in (
            Courses,
            Runs,
            Schedules,
            ExamAssignments,
            ConflictAnalyses,
            TimeSlots,
        )
    }


def _rows(db, schedule_id) -> list[tuple[str, str, str]]:
    return sorted(
        (str(course_id), str(slot_id), str(room_id))
        for course_id, slot_id, room_id in db.execute(
            select(
                ExamAssignments.course_id,
                ExamAssignments.time_slot_id,
                ExamAssignments.room_id,
            ).where(ExamAssignments.schedule_id == schedule_id)
        )
    )


def _analysis(db, schedule_id) -> dict:
    return db.execute(
        select(ConflictAnalyses.conflicts).where(
            ConflictAnalyses.schedule_id == schedule_id
        )
    ).scalar_one()


def _stored_state(db, schedule_id) -> tuple:
    run = db.execute(
        select(Runs.algorithm_name, Runs.parameters, Runs.status)
        .join(Schedules, Schedules.run_id == Runs.run_id)
        .where(Schedules.schedule_id == schedule_id)
    ).one()
    return _rows(db, schedule_id), copy.deepcopy(_analysis(db, schedule_id)), run


def _validate(db, owner, schedule_id) -> dict[str, str]:
    service = ScheduleValidationService(
        ScheduleRepo(db),
        ExamAssignmentRepo(db),
        ConflictAnalysesRepo(db),
        DatasetRepo(db),
    )
    with patch("src.services.schedule_validation.storage") as storage:
        storage.download_file.side_effect = FILES.get
        snapshot = asyncio.run(service.build_snapshot(schedule_id, owner.user_id))
    return {
        event.check.id: event.result.status
        for event in run_checks(snapshot)
        if isinstance(event, CheckFinished)
    }


@pytest.mark.parametrize("shape", sorted(BASES))
def test_v1_to_v2_to_v3_chain_keeps_every_version_valid(db_session, shape):
    algorithm_name, parameters, base_analysis = BASES[shape]
    owner = make_user(db_session, "Owner")
    v1 = _generated_base(
        db_session,
        owner,
        parameters=dict(parameters),
        algorithm_name=algorithm_name,
        analysis=base_analysis,
    )
    v1_before = _stored_state(db_session, v1.schedule_id)
    v1_checks = _validate(db_session, owner, v1.schedule_id)

    status, v2 = _save(db_session, owner, v1.schedule_id, LATE_A)

    assert status == 200, v2
    assert (v2["schedule_name"], v2["algorithm"], v2["status"]) == (
        "Version 2",
        "Late add",
        "Completed",
    )
    entry_a = v2["lineage"]["late_additions"][0]
    added_at = entry_a.pop("added_at")
    assert datetime.datetime.fromisoformat(added_at).tzinfo is None
    assert entry_a == {
        "crn": "900",
        "course_code": "LATE 9000",
        "instructor_id": "I-1",
        "size": 2,
        "day": 0,
        "day_name": "Monday",
        "block": 1,
        "block_time": "10:30AM-12:30PM",
        "room": "Room B",
        "outcome": "clear",
        "conflicts": {
            "student_double_book": 0,
            "student_over_daily_limit": 0,
            "instructor_double_book": 0,
            "instructor_over_daily_limit": 0,
            "back_to_back_students": 1,
            "back_to_back_instructor": 1,
            "large_course_late": 0,
        },
        "added_by": str(owner.user_id),
        "added_by_name": "Owner",
        "schedule_id": v2["schedule_id"],
    }
    assert v2["parameters"] == {
        **parameters,
        "based_on_schedule_id": str(v1.schedule_id),
        "original_schedule_id": str(v1.schedule_id),
        "late_additions": [{**entry_a, "added_at": added_at}],
    }
    assert v2["lineage"]["based_on"]["id"] == str(v1.schedule_id)
    # Every base row (the unscheduled one too) plus the late exam.
    v2_rows = _rows(db_session, v2["schedule_id"])
    assert len(v2_rows) == len(BASE_EXAMS) + 1
    assert set(v1_before[0]) < set(v2_rows)
    late_row = db_session.execute(
        select(Courses).where(Courses.crn == "900")
    ).scalar_one()
    assert (
        late_row.course_subject_code,
        late_row.instructor_name,
        late_row.enrollment_count,
        late_row.dataset_id,
        late_row.department,
        late_row.examination_term,
    ) == ("LATE 9000", "I-1", 2, v1.run.dataset_id, None, None)
    v2_analysis = _analysis(db_session, v2["schedule_id"])
    assert v2_analysis["soft_conflicts"]["back_to_back_students"] == [
        _b2b("student_id", "S2", [0, 1]),
        _b2b("student_id", "S1", [0, 1]),
    ]
    assert v2_analysis["hard_conflicts"] == base_analysis["hard_conflicts"]

    # On v2, A's student S5 and instructor I-1 are busy at 10:30AM.
    search_b = _search(db_session, owner, v2["schedule_id"], "950", "SUBJ 9500", "I-1")
    assert search_b["outcome"] == "least_conflicts"
    at_1130 = _candidate(search_b, 0, 1)
    assert at_1130["students"]["double_book"] == [
        {"student_id": "S3", "crns": ["102"]},
        {"student_id": "S5", "crns": ["900"]},
    ]
    assert at_1130["instructor"]["double_book_crns"] == ["900"]

    status, v3 = _save(db_session, owner, v2["schedule_id"], LATE_B)

    assert status == 200, v3
    lineage = v3["lineage"]
    assert (lineage["based_on"]["id"], lineage["original"]["id"]) == (
        v2["schedule_id"],
        str(v1.schedule_id),
    )
    first, entry_b = lineage["late_additions"]
    assert first == {**entry_a, "added_at": added_at}
    assert entry_b["schedule_id"] == v3["schedule_id"]
    assert (entry_b["outcome"], entry_b["size"]) == ("least_conflicts", 2)
    assert entry_b["conflicts"] == {
        "student_double_book": 2,
        "student_over_daily_limit": 0,
        "instructor_double_book": 1,
        "instructor_over_daily_limit": 1,
        "back_to_back_students": 0,
        "back_to_back_instructor": 1,
        "large_course_late": 0,
    }
    hard = _analysis(db_session, v3["schedule_id"])["hard_conflicts"]
    base_hard = base_analysis["hard_conflicts"]
    assert hard["student_double_book"] == [
        *base_hard["student_double_book"],
        _hard("S3", 1, "950", "SUBJ 9500", "102", "SUBJ 1002"),
        _hard("S5", 1, "950", "SUBJ 9500", "900", "LATE 9000"),
    ]
    assert hard["instructor_double_book"] == [
        *base_hard["instructor_double_book"],
        _hard("I-1", 1, "950", "SUBJ 9500", "900", "LATE 9000"),
    ]
    assert hard["instructor_gt_max_per_day"] == [
        *base_hard["instructor_gt_max_per_day"],
        _hard("I-1", 1, "950", "SUBJ 9500"),
    ]
    assert hard["student_gt_max_per_day"] == []

    # v3 has both late exams: a third one finds A's and B's people busy.
    search_c = _search(db_session, owner, v3["schedule_id"], "960", "LATE 9600", "I-1")
    at_1130 = _candidate(search_c, 0, 1)
    assert at_1130["students"]["double_book"] == [
        {"student_id": "S5", "crns": ["900", "950"]}
    ]
    assert at_1130["instructor"]["double_book_crns"] == ["900", "950"]

    # The base is never modified.
    assert _stored_state(db_session, v1.schedule_id) == v1_before

    # The Validator finds no check worse on a late-add version than on v1,
    # which generation stored consistently (warnings are the real conflicts).
    assert v1_checks["coverage.late_additions"] == "skipped"
    assert "fail" not in v1_checks.values(), v1_checks
    for version in (v2, v3):
        checks = _validate(db_session, owner, version["schedule_id"])
        worse = {
            check: (v1_checks[check], status)
            for check, status in checks.items()
            if _RANK[status] > _RANK[v1_checks[check]]
        }
        assert worse == {}, version["schedule_name"]
        assert "fail" not in checks.values(), checks
        assert checks["coverage.late_additions"] == "pass"
        assert checks["coverage.crn_in_courses_file"] == "pass"
        assert checks["data.stored_statistics"] == "pass"
        assert (
            _analysis(db_session, version["schedule_id"])["unscheduled_groups"]
            == base_analysis["unscheduled_groups"]
        )


def test_unchanged_late_course_row_is_reused_and_a_changed_one_is_not(db_session):
    owner = make_user(db_session, "Owner")
    v1 = _generated_base(db_session, owner)

    first = _save(db_session, owner, v1.schedule_id, LATE_A)
    branch = _save(db_session, owner, v1.schedule_id, {**LATE_A, "schedule_name": "B"})
    changed = _save(
        db_session,
        owner,
        v1.schedule_id,
        {**LATE_A, "course_code": "LATE 9001", "schedule_name": "C"},
    )

    assert [status for status, _ in (first, branch, changed)] == [200, 200, 200]
    rows = db_session.execute(
        select(Courses.course_subject_code).where(Courses.crn == "900")
    ).scalars()
    assert sorted(rows) == ["LATE 9000", "LATE 9001"]


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"room": "Hall A"}, "Hall A is already used on Monday 10:30AM-12:30PM"),
        ({"block": 2, "room": "Room B"}, "Room B is blocked out on Monday 1PM-3PM"),
        ({"room": "Hall Z"}, "Hall Z is not one of this dataset's rooms"),
        (
            {"crn": "990", "course_code": "BIG 9900", "room": "Room C"},
            "Room C seats 10, fewer than the exam's 60 students",
        ),
        # No room in any block seats 60 (outcome No room).
        (
            {"crn": "990", "course_code": "BIG 9900", "room": "Hall D"},
            "Hall D seats 50, fewer than the exam's 60 students",
        ),
        (
            {"block": 0, "room": "Room B"},
            "Monday 8AM-10AM has hard conflicts for this exam",
        ),
    ],
)
def test_placement_that_does_not_hold_is_409_and_nothing_is_written(
    db_session, change, message
):
    owner = make_user(db_session, "Owner")
    v1 = _generated_base(db_session, owner)
    before = _counts(db_session)

    status, body = _save(db_session, owner, v1.schedule_id, {**LATE_A, **change})

    assert status == 409, body
    assert body["detail"].startswith(message)
    assert _counts(db_session) == before


# Hall A is marked LargeOnly and seats 100; the cutoff is Hall D's 50.
LARGE_ONLY_ROOMS = {**ROOMS, "Hall A": 100}
LARGE_ONLY_FILES = {
    **FILES,
    "k/rooms.csv": b"room_name,capacity,LargeOnly\n"
    b"Hall A,100,yes\nRoom B,5,\nRoom C,10,no\nHall D,50,\n",
}


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (
            {"block": 3, "room": "Hall A"},
            "Hall A is reserved for exams over 50 students; this exam has 2.",
        ),
        (
            {"crn": "990", "course_code": "BIG 9900", "room": "Hall D"},
            "Exams over 50 students must use Hall A; this exam has 60.",
        ),
    ],
)
def test_room_that_breaks_the_large_only_rule_is_409_with_the_reason(
    db_session, change, message
):
    owner = make_user(db_session, "Owner")
    v1 = _generated_base(db_session, owner, room_capacities=LARGE_ONLY_ROOMS)
    before = _counts(db_session)

    status, body = _save(
        db_session, owner, v1.schedule_id, {**LATE_A, **change}, LARGE_ONLY_FILES
    )

    assert status == 409, body
    assert body["detail"] == message
    assert _counts(db_session) == before


def test_exam_over_the_cutoff_is_saved_in_the_large_only_room(db_session):
    owner = make_user(db_session, "Owner")
    v1 = _generated_base(db_session, owner, room_capacities=LARGE_ONLY_ROOMS)
    big = {**LATE_A, "crn": "990", "course_code": "BIG 9900", "block": 3}

    status, body = _save(
        db_session, owner, v1.schedule_id, {**big, "room": "Hall A"}, LARGE_ONLY_FILES
    )

    assert status == 200, body


def test_hard_conflicts_are_saved_once_accepted(db_session):
    owner = make_user(db_session, "Owner")
    v1 = _generated_base(db_session, owner)
    # 8AM: S1 sits 101 and I-1 teaches it.
    body = {**LATE_A, "block": 0, "accept_conflicts": True}

    status, saved = _save(db_session, owner, v1.schedule_id, body)

    assert status == 200, saved
    entry = saved["lineage"]["late_additions"][0]
    assert entry["outcome"] == "least_conflicts"
    assert entry["conflicts"]["student_double_book"] == 1
    assert entry["conflicts"]["instructor_double_book"] == 1
    hard = _analysis(db_session, saved["schedule_id"])["hard_conflicts"]
    assert hard["student_double_book"][-1] == _hard(
        "S1", 0, "900", "LATE 9000", "101", "SUBJ 1001"
    )
    assert hard["instructor_double_book"][-1] == _hard(
        "I-1", 0, "900", "LATE 9000", "101", "SUBJ 1001"
    )


def test_instructor_double_booked_in_base_goes_over_the_limit_and_v2_validates(
    db_session,
):
    owner = make_user(db_session, "Owner")
    v1 = _generated_base(db_session, owner)
    # I-3 already sits two separate exams (105, 109) at 8AM: a third exam that
    # day is over the limit of 2 in every block.
    search = _search(db_session, owner, v1.schedule_id, "900", "LATE 9000", "I-3")
    assert search["outcome"] == "least_conflicts"
    assert _candidate(search, 0, 1)["instructor"]["exams_that_day"] == 3
    body = {**LATE_A, "instructor_id": "I-3", "accept_conflicts": True}

    status, v2 = _save(db_session, owner, v1.schedule_id, body)

    assert status == 200, v2
    entry = v2["lineage"]["late_additions"][0]
    assert entry["outcome"] == "least_conflicts"
    assert entry["conflicts"]["instructor_over_daily_limit"] == 1
    assert _analysis(db_session, v2["schedule_id"])["hard_conflicts"][
        "instructor_gt_max_per_day"
    ][-1] == _hard("I-3", 1, "900", "LATE 9000")
    checks = _validate(db_session, owner, v2["schedule_id"])
    assert checks["conflicts.instructor_over_max_per_day"] == "warn"
    assert "fail" not in checks.values(), checks


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"schedule_name": "   "}, "Enter a schedule name."),
        ({"instructor_id": " NaN "}, "Enter the instructor ID."),
        ({"schedule_name": "x" * 51}, "Schedule names are at most 50 characters."),
        ({"schedule_name": " Base "}, "Schedule name 'Base' already exists"),
        ({"day": 1}, "Day 1, block 1 is outside the schedule's window"),
        ({"block": 4}, "Day 0, block 4 is outside the schedule's window"),
        ({"block": -1}, "Day 0, block -1 is outside the schedule's window"),
    ],
)
def test_bad_name_or_block_is_400_and_nothing_is_written(db_session, change, message):
    owner = make_user(db_session, "Owner")
    v1 = _generated_base(db_session, owner)
    before = _counts(db_session)

    status, body = _save(db_session, owner, v1.schedule_id, {**LATE_A, **change})

    assert status == 400, body
    assert body["detail"].startswith(message)
    assert _counts(db_session) == before


def test_name_taken_by_another_user_is_fine_and_fifty_characters_is_allowed(
    db_session,
):
    owner = make_user(db_session, "Owner")
    other = make_user(db_session, "Other")
    make_schedule(db_session, other, "x" * 50)
    v1 = _generated_base(db_session, owner)

    status, body = _save(
        db_session, owner, v1.schedule_id, {**LATE_A, "schedule_name": "x" * 50}
    )

    assert status == 200, body
    assert body["schedule_name"] == "x" * 50


def test_only_the_owner_may_save_and_a_deleted_dataset_is_409(db_session):
    owner = make_user(db_session, "Owner")
    viewer = make_user(db_session, "Viewer")
    stranger = make_user(db_session, "Stranger")
    v1 = _generated_base(db_session, owner)
    share_schedule(db_session, v1, owner, viewer)
    before = _counts(db_session)

    for user in (viewer, stranger):
        status, body = _save(db_session, user, v1.schedule_id, LATE_A)
        assert (status, body) == (
            404,
            {"detail": f"Schedule {v1.schedule_id} not found"},
        )

    v1.run.dataset.deleted_at = datetime.datetime.now()
    db_session.flush()
    status, _ = _save(db_session, owner, v1.schedule_id, LATE_A)
    assert status == 409
    assert _counts(db_session) == before


def test_failure_after_some_writes_leaves_nothing_behind(db_session):
    owner = make_user(db_session, "Owner")
    v1 = _generated_base(db_session, owner)
    before = _counts(db_session)

    with patch.object(
        ConflictAnalysesRepo, "add_analysis", side_effect=RuntimeError("disk full")
    ):
        status, body = _save(db_session, owner, v1.schedule_id, LATE_A)

    assert status == 500
    assert "disk full" in body["detail"]
    assert _counts(db_session) == before
    # Nothing half-saved blocks a retry under the same name.
    status, body = _save(db_session, owner, v1.schedule_id, LATE_A)
    assert status == 200, body


def test_legacy_base_keeps_its_engine_and_records_settings_explicitly(db_session):
    owner = make_user(db_session, "Owner")
    legacy = {"student_max_per_day": 3, "instructor_max_per_day": 2, "max_days": 1}
    v1 = _generated_base(db_session, owner, parameters=legacy, algorithm_name="DSATUR")

    status, v2 = _save(db_session, owner, v1.schedule_id, LATE_A)

    assert status == 200, v2
    params = v2["parameters"]
    assert (params["algorithm"], params["blocks_per_day"]) == ("dsatur", 5)
    # Settings the base never recorded stay unrecorded (not null).
    assert "time_budget_seconds" not in params
    assert v2["summary"]["settings"]["algorithm"] == "dsatur"
    assert v2["summary"]["settings_assumed"] == []
