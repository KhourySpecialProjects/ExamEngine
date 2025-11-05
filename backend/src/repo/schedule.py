from sqlalchemy.orm import Session

from src.schemas.db import Schedules

from .base import BaseRepo


class ScheduleRepo(BaseRepo[Schedules]):
    """Repository for schedule data access operations."""

    def __init__(self, db: Session):
        super().__init__(Schedules, db)

    # TODO
