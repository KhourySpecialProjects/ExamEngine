"""Independent schedule validation.

Re-checks a stored schedule against the dataset's original uploaded files. The
check logic is written from scratch and deliberately shares no code with the
scheduler, conflict detection or schedule analysis it verifies.
"""

from .catalog import CHECKS, Check
from .parsing import parse_dataset_files
from .results import STATUSES, CheckResult, CheckStatus
from .runner import CheckFinished, CheckStarted, run_check, run_checks
from .snapshot import (
    CourseRecord,
    DatasetFiles,
    EnrollmentRecord,
    RoomRecord,
    RunParameters,
    ScheduleRow,
    ValidationSnapshot,
)


__all__ = [
    "CHECKS",
    "STATUSES",
    "Check",
    "CheckFinished",
    "CheckResult",
    "CheckStarted",
    "CheckStatus",
    "CourseRecord",
    "DatasetFiles",
    "EnrollmentRecord",
    "RoomRecord",
    "RunParameters",
    "ScheduleRow",
    "ValidationSnapshot",
    "parse_dataset_files",
    "run_check",
    "run_checks",
]
