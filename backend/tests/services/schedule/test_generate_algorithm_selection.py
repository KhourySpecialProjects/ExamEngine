"""ScheduleService.generate_schedule picks the engine from `algorithm`."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.core.exceptions import ValidationError
from src.services.schedule import service as service_module
from src.services.schedule.service import ScheduleService


def _service() -> ScheduleService:
    svc = ScheduleService.__new__(ScheduleService)
    svc.schedule_repo = MagicMock()
    svc.schedule_repo.name_exists.return_value = False
    svc.schedule_repo.create_schedule_with_run.return_value = (
        SimpleNamespace(schedule_id=uuid4()),
        SimpleNamespace(run_id=uuid4()),
    )
    svc.run_repo = MagicMock()
    svc.dataset_service = MagicMock()
    svc.dataset_service.get_dataset_files = AsyncMock(return_value={})
    svc.dataset_service.drop_zero_enrollment = AsyncMock(
        return_value={"courses": None, "enrollments": None, "rooms": None}
    )
    svc.dataset_service.get_merges.return_value = {}
    svc.dataset_service.get_common_exams.return_value = {}
    svc._ensure_courses = MagicMock(return_value={})
    svc._ensure_rooms = MagicMock(return_value={})
    svc._save_exam_assignments = AsyncMock()
    svc._save_conflicts = AsyncMock()
    svc.get_schedule_with_details = AsyncMock(return_value={})
    return svc


def _generate(svc: ScheduleService, **kwargs):
    with (
        patch.object(service_module, "DatasetFactory"),
        patch.object(service_module, "ScheduleAnalyzer"),
        patch.object(service_module, "Scheduler") as dsatur,
        patch.object(service_module, "AnnealingScheduler") as annealing,
    ):
        asyncio.run(svc.generate_schedule(uuid4(), uuid4(), "name", **kwargs))
    return dsatur, annealing


def _run_record(svc: ScheduleService) -> dict:
    return svc.schedule_repo.create_schedule_with_run.call_args.kwargs


def test_default_request_runs_dsatur():
    svc = _service()
    dsatur, annealing = _generate(svc)

    dsatur.assert_called_once()
    annealing.assert_not_called()
    record = _run_record(svc)
    assert record["algorithm_name"] == "DSATUR"
    assert record["parameters"]["algorithm"] == "dsatur"
    assert record["parameters"]["time_budget_seconds"] == 15


def test_annealing_request_runs_annealing_with_budget():
    svc = _service()
    dsatur, annealing = _generate(svc, algorithm="annealing", time_budget_seconds=30)

    dsatur.assert_not_called()
    annealing.assert_called_once()
    assert annealing.call_args.kwargs["time_budget_seconds"] == 30
    annealing.return_value.schedule.assert_called_once()
    record = _run_record(svc)
    assert record["algorithm_name"] == "Annealing"
    assert record["parameters"]["algorithm"] == "annealing"
    assert record["parameters"]["time_budget_seconds"] == 30


def test_avoid_back_to_back_off_zeroes_annealing_b2b_weights():
    svc = _service()
    _, annealing = _generate(svc, algorithm="annealing", avoid_back_to_back=False)

    kwargs = annealing.call_args.kwargs
    assert kwargs["weight_b2b_student"] == 0
    assert kwargs["weight_b2b_instructor"] == 0


def test_avoid_back_to_back_on_keeps_annealing_default_weights():
    svc = _service()
    _, annealing = _generate(svc, algorithm="annealing", avoid_back_to_back=True)

    kwargs = annealing.call_args.kwargs
    assert "weight_b2b_student" not in kwargs
    assert "weight_b2b_instructor" not in kwargs


def test_unknown_algorithm_is_rejected_before_any_run_is_created():
    svc = _service()

    with pytest.raises(ValidationError):
        _generate(svc, algorithm="bogus")
    svc.schedule_repo.create_schedule_with_run.assert_not_called()
