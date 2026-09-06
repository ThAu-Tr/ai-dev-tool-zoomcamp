"""Pure household due-date and recurrence calculations."""

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from zoneinfo import ZoneInfo

from django.utils import timezone


HOUSEHOLD_TIME_ZONE = ZoneInfo("Europe/Berlin")


class DueStatus(str, Enum):
    """The relationship between a scheduled date and today's local date."""

    NOT_YET_DUE = "not_yet_due"
    DUE = "due"
    OVERDUE = "overdue"


@dataclass(frozen=True)
class DueEvaluation:
    due_date: date
    local_date: date
    status: DueStatus
    eligible: bool


def _require_date(value: object, *, name: str) -> date:
    """Require a date value while deliberately excluding datetime subclasses."""

    if not isinstance(value, date) or isinstance(value, datetime):
        raise TypeError(f"{name} must be a date, not a datetime or another type.")
    return value


def _require_aware_datetime(value: object, *, name: str) -> datetime:
    """Require a timezone-aware datetime without reinterpreting naive values."""

    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime.")
    if timezone.is_naive(value):
        raise ValueError(f"{name} must be timezone-aware.")
    return value


def household_local_date(at: datetime | None = None) -> date:
    """Return the calendar date for an aware instant in Europe/Berlin."""

    instant = timezone.now() if at is None else _require_aware_datetime(at, name="at")
    return _require_aware_datetime(instant, name="at").astimezone(
        HOUSEHOLD_TIME_ZONE
    ).date()


def evaluate_due(due_date: date, *, at: datetime | None = None) -> DueEvaluation:
    """Classify a stored due date without modifying any persisted state."""

    checked_due_date = _require_date(due_date, name="due_date")
    local_date = household_local_date(at)
    if local_date < checked_due_date:
        return DueEvaluation(
            due_date=checked_due_date,
            local_date=local_date,
            status=DueStatus.NOT_YET_DUE,
            eligible=False,
        )
    if local_date == checked_due_date:
        return DueEvaluation(
            due_date=checked_due_date,
            local_date=local_date,
            status=DueStatus.DUE,
            eligible=True,
        )
    return DueEvaluation(
        due_date=checked_due_date,
        local_date=local_date,
        status=DueStatus.OVERDUE,
        eligible=True,
    )


def calculate_next_due_date(
    previous_due_date: date,
    frequency_days: int,
    *,
    completed_at: datetime,
) -> date:
    """Advance an anchored daily recurrence beyond the local completion date."""

    checked_previous_due_date = _require_date(
        previous_due_date, name="previous_due_date"
    )
    if type(frequency_days) is not int:
        raise TypeError("frequency_days must be an integer.")
    if not 1 <= frequency_days <= 365:
        raise ValueError("frequency_days must be between 1 and 365.")

    completed_local_date = household_local_date(
        _require_aware_datetime(completed_at, name="completed_at")
    )
    if completed_local_date < checked_previous_due_date:
        raise ValueError("completed_at cannot be before previous_due_date.")

    elapsed_days = (completed_local_date - checked_previous_due_date).days
    intervals = elapsed_days // frequency_days + 1
    return checked_previous_due_date.fromordinal(
        checked_previous_due_date.toordinal() + intervals * frequency_days
    )
