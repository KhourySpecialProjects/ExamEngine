"""Check outcomes and the helpers checks use to build them."""

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Literal


CheckStatus = Literal["pass", "warn", "fail", "skipped"]
STATUSES: tuple[CheckStatus, ...] = ("pass", "warn", "fail", "skipped")

MAX_EXAMPLES = 20


@dataclass(frozen=True)
class CheckResult:
    """Outcome of one check.

    `count` is the number of offending items (0 for pass); `examples` holds at
    most MAX_EXAMPLES short strings. `error` is the exception of a crashed check;
    it is never sent to clients.
    """

    status: CheckStatus
    summary: str
    count: int = 0
    examples: tuple[str, ...] = ()
    error: BaseException | None = field(default=None, compare=False)


class CheckSkipped(Exception):  # noqa: N818 - control flow, not an error
    """Raised inside a check when it does not apply; becomes a `skipped` result."""

    def __init__(self, summary: str):
        super().__init__(summary)
        self.summary = summary


def passed(summary: str) -> CheckResult:
    return CheckResult(status="pass", summary=summary)


def skipped(summary: str) -> CheckResult:
    return CheckResult(status="skipped", summary=summary)


def problems(
    status: CheckStatus,
    summary: str,
    examples: Iterable[str],
    count: int | None = None,
) -> CheckResult:
    """A warn/fail result; `count` defaults to the number of examples given."""
    items = list(examples)
    return CheckResult(
        status=status,
        summary=summary,
        count=len(items) if count is None else count,
        examples=tuple(items[:MAX_EXAMPLES]),
    )


def plural(count: int, noun: str, plural_noun: str | None = None) -> str:
    """'1 exam', '3 exams'."""
    word = noun if count == 1 else (plural_noun or f"{noun}s")
    return f"{count} {word}"
