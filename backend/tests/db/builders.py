"""Minimal rows for integration tests. Each builder flushes and returns the row."""

import datetime
import uuid
from typing import Any

from sqlalchemy.orm import Session

from src.repo.time_slot import TimeSlotRepo
from src.schemas.db import (
    ConflictAnalyses,
    Courses,
    Datasets,
    DayEnum,
    ExamAssignments,
    Rooms,
    Runs,
    Schedules,
    ScheduleShares,
    StatusEnum,
    TimeSlots,
    Users,
)


def make_user(db: Session, name: str = "Test User") -> Users:
    user = Users(
        name=name,
        email=f"{uuid.uuid4().hex}@example.test",
        password_hash="not-a-real-hash",  # noqa: S106 (no login in these tests)
        role="user",
        status="approved",
    )
    db.add(user)
    db.flush()
    return user


def make_dataset(db: Session, owner: Users) -> Datasets:
    dataset = Datasets(
        dataset_name="Test dataset", user_id=owner.user_id, file_paths=[]
    )
    db.add(dataset)
    db.flush()
    return dataset


def make_schedule(
    db: Session,
    owner: Users,
    name: str = "Test schedule",
    *,
    dataset: Datasets | None = None,
    parameters: dict[str, Any] | None = None,
    algorithm_name: str = "dsatur",
) -> Schedules:
    """A completed run by ``owner`` and its schedule (no exams).

    Uses a new dataset unless one is given.
    """
    dataset = dataset or make_dataset(db, owner)
    run = Runs(
        dataset_id=dataset.dataset_id,
        user_id=owner.user_id,
        algorithm_name=algorithm_name,
        parameters=parameters if parameters is not None else {},
        status=StatusEnum.Completed,
    )
    db.add(run)
    db.flush()
    schedule = Schedules(schedule_name=name, run_id=run.run_id)
    db.add(schedule)
    db.flush()
    return schedule


def add_exam(
    db: Session,
    schedule: Schedules,
    crn: str,
    size: int,
    *,
    slot: tuple[str, int] | None = None,
    block: tuple[str, int] | None = None,
    room: tuple[str, int] | None = None,
    instructor: str | None = None,
) -> ExamAssignments:
    """Add a course to the schedule's dataset and its exam to the schedule.

    ``slot`` is (day name, start hour); ``block`` is (day name, block index)
    with the app's real block labels (use one or the other); ``room`` is
    (location, capacity). No slot = unscheduled; a slot without a room =
    unroomed.
    """
    dataset_id = schedule.run.dataset_id
    course = Courses(
        crn=crn,
        course_subject_code=f"TEST {crn}",
        instructor_name=instructor,
        enrollment_count=size,
        dataset_id=dataset_id,
    )
    db.add(course)
    time_slot = None
    if block is not None:
        time_slot = TimeSlotRepo(db).get_or_create_slot(dataset_id, *block)
    if slot is not None:
        day, hour = slot
        time_slot = TimeSlots(
            slot_label=f"{hour}:00-{hour + 2}:00",
            day=DayEnum(day),
            start_time=datetime.time(hour),
            end_time=datetime.time(hour + 2),
            dataset_id=dataset_id,
        )
        db.add(time_slot)
    room_row = None
    if room is not None:
        location, capacity = room
        room_row = Rooms(location=location, capacity=capacity, dataset_id=dataset_id)
        db.add(room_row)
    db.flush()
    assignment = ExamAssignments(
        course_id=course.course_id,
        time_slot_id=time_slot.time_slot_id if time_slot else None,
        room_id=room_row.room_id if room_row else None,
        schedule_id=schedule.schedule_id,
    )
    db.add(assignment)
    db.flush()
    return assignment


def save_analysis(
    db: Session, schedule: Schedules, conflicts: dict[str, Any]
) -> ConflictAnalyses:
    analysis = ConflictAnalyses(schedule_id=schedule.schedule_id, conflicts=conflicts)
    db.add(analysis)
    db.flush()
    return analysis


def share_schedule(
    db: Session, schedule: Schedules, owner: Users, recipient: Users
) -> ScheduleShares:
    share = ScheduleShares(
        schedule_id=schedule.schedule_id,
        shared_with_user_id=recipient.user_id,
        shared_by_user_id=owner.user_id,
        permission="view",
    )
    db.add(share)
    db.flush()
    return share
