"""Run the catalog against a snapshot, one check at a time."""

from collections.abc import Iterator
from dataclasses import dataclass

from src.domain.validation.catalog import CHECKS, Check
from src.domain.validation.context import ValidationContext
from src.domain.validation.results import CheckResult, CheckSkipped, skipped
from src.domain.validation.snapshot import ValidationSnapshot


@dataclass(frozen=True)
class CheckStarted:
    check: Check


@dataclass(frozen=True)
class CheckFinished:
    check: Check
    result: CheckResult


def run_check(check: Check, ctx: ValidationContext) -> CheckResult:
    """Run one check; a crash becomes a `fail` result carrying the exception."""
    try:
        return check.run(ctx)
    except CheckSkipped as skip:
        return skipped(skip.summary)
    except Exception as exc:
        return CheckResult(
            status="fail",
            summary=f"Check crashed: {type(exc).__name__}",
            count=0,
            error=exc,
        )


def run_checks(
    snapshot: ValidationSnapshot, checks: tuple[Check, ...] = CHECKS
) -> Iterator[CheckStarted | CheckFinished]:
    """Yield a start event before each check runs and its result after."""
    ctx = ValidationContext(snapshot)
    for check in checks:
        yield CheckStarted(check)
        yield CheckFinished(check, run_check(check, ctx))
