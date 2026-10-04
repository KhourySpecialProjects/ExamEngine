"""Minimal rows for integration tests. Each builder flushes and returns the row."""

import uuid

from sqlalchemy.orm import Session

from src.schemas.db import (
    Datasets,
    Runs,
    Schedules,
    ScheduleShares,
    StatusEnum,
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


def make_schedule(db: Session, owner: Users, name: str = "Test schedule") -> Schedules:
    """A completed run by ``owner`` on a new dataset, and its schedule (no exams)."""
    dataset = make_dataset(db, owner)
    run = Runs(
        dataset_id=dataset.dataset_id,
        user_id=owner.user_id,
        algorithm_name="dsatur",
        parameters={},
        status=StatusEnum.Completed,
    )
    db.add(run)
    db.flush()
    schedule = Schedules(schedule_name=name, run_id=run.run_id)
    db.add(schedule)
    db.flush()
    return schedule


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
