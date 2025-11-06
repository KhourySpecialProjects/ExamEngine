from src.repo.schedule import ScheduleRepo


class ScheduleService:
    """Business logic for exam schedule generation."""

    def __init__(self, schedule_repo: ScheduleRepo):
        self.schedule_repo = schedule_repo
