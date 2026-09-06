import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from django.db import IntegrityError, OperationalError, transaction
from django.utils import timezone

from household.models import Chore, Completion, Member
from household.scheduling import calculate_next_due_date, evaluate_due

MAX_LOCK_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 0.05


class CompletionStatus(str, Enum):
    SUCCESS = "success"
    STALE_VERSION = "stale_version"
    INELIGIBLE = "ineligible"
    INACTIVE_CHORE = "inactive_chore"
    NOT_FOUND = "not_found"
    LOCKED = "locked"


@dataclass(frozen=True)
class CompletionResult:
    status: CompletionStatus
    message: str
    completion: Completion | None = None
    chore: Chore | None = None


def complete_chore(
    *,
    member_id: int | Member,
    chore_id: int | Chore,
    expected_version: int,
    completed_at: datetime | None = None,
) -> CompletionResult:
    """Record a completion and advance the chore in a single atomic transaction.

    Validates member existence, chore existence and active state, completion
    eligibility under household scheduling rules, and the expected completion
    version.

    Outcomes for UI callers:
    - SUCCESS: Chore advanced and Completion record created. Redirect with success message.
    - STALE_VERSION: Occurrence already completed or version modified. Redirect or display
      informative message that chore was already completed.
    - INELIGIBLE: Chore is not yet due under Europe/Berlin local time.
    - INACTIVE_CHORE: Chore has been deleted/deactivated.
    - NOT_FOUND: Member or chore ID does not exist.
    - LOCKED: SQLite database is busy/locked after bounded retries. Recoverable; inform user
      to retry.
    """
    if completed_at is None:
        completed_at = timezone.now()

    if timezone.is_naive(completed_at):
        raise ValueError("completed_at must be timezone-aware.")

    resolved_member_id = member_id.pk if isinstance(member_id, Member) else member_id
    resolved_chore_id = chore_id.pk if isinstance(chore_id, Chore) else chore_id

    for attempt in range(MAX_LOCK_RETRIES):
        try:
            try:
                member = Member.objects.get(pk=resolved_member_id)
            except Member.DoesNotExist:
                return CompletionResult(
                    status=CompletionStatus.NOT_FOUND,
                    message="Selected household member was not found.",
                )

            try:
                chore = Chore.objects.get(pk=resolved_chore_id)
            except Chore.DoesNotExist:
                return CompletionResult(
                    status=CompletionStatus.NOT_FOUND,
                    message="Chore was not found.",
                )

            if not chore.is_active:
                return CompletionResult(
                    status=CompletionStatus.INACTIVE_CHORE,
                    message="Chore is no longer active.",
                    chore=chore,
                )

            if chore.completion_version != expected_version:
                return CompletionResult(
                    status=CompletionStatus.STALE_VERSION,
                    message="This chore occurrence has already been completed or modified.",
                    chore=chore,
                )

            evaluation = evaluate_due(chore.next_due_date, at=completed_at)
            if not evaluation.eligible:
                return CompletionResult(
                    status=CompletionStatus.INELIGIBLE,
                    message="Chore is not yet due.",
                    chore=chore,
                )

            next_due_date = calculate_next_due_date(
                chore.next_due_date,
                chore.frequency_days,
                completed_at=completed_at,
            )

            with transaction.atomic():
                # Conditional version update ensures optimistic locking
                updated_rows = Chore.objects.filter(
                    pk=chore.pk,
                    completion_version=expected_version,
                    is_active=True,
                ).update(
                    completion_version=expected_version + 1,
                    next_due_date=next_due_date,
                )

                if updated_rows != 1:
                    chore.refresh_from_db()
                    return CompletionResult(
                        status=CompletionStatus.STALE_VERSION,
                        message="This chore occurrence has already been completed or modified.",
                        chore=chore,
                    )

                completion = Completion.objects.create(
                    member=member,
                    chore=chore,
                    completed_at=completed_at,
                    awarded_points=chore.points,
                    chore_name_snapshot=chore.name,
                    completed_version=expected_version,
                )

                chore.refresh_from_db()
                return CompletionResult(
                    status=CompletionStatus.SUCCESS,
                    message=f'Completed "{chore.name}" for {member.name}.',
                    completion=completion,
                    chore=chore,
                )
        except IntegrityError:
            try:
                chore = Chore.objects.get(pk=resolved_chore_id)
            except Chore.DoesNotExist:
                chore = None
            return CompletionResult(
                status=CompletionStatus.STALE_VERSION,
                message="This chore occurrence has already been completed.",
                chore=chore,
            )
        except OperationalError as e:
            err_msg = str(e).lower()
            if "database is locked" in err_msg or "locked" in err_msg or "busy" in err_msg:
                if attempt < MAX_LOCK_RETRIES - 1:
                    time.sleep(INITIAL_BACKOFF_SECONDS * (2**attempt))
                    continue
                try:
                    chore = Chore.objects.get(pk=resolved_chore_id)
                except Exception:
                    chore = None
                return CompletionResult(
                    status=CompletionStatus.LOCKED,
                    message="The database is busy. Please try again in a moment.",
                    chore=chore,
                )
            raise

    return CompletionResult(
        status=CompletionStatus.LOCKED,
        message="The database is busy. Please try again in a moment.",
        chore=None,
    )
