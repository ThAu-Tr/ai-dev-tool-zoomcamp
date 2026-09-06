"""Shared contribution queries and score calculations for household members."""

from dataclasses import dataclass
from datetime import datetime

from django.db.models import Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from household.garden import GardenStage, calculate_garden_stage
from household.models import Member


@dataclass(frozen=True)
class MemberScore:
    member: Member
    monthly_points: int
    lifetime_xp: int
    garden_stage: GardenStage


def _get_local_month_bounds(at: datetime | None = None) -> tuple[str, datetime, datetime]:
    """Return the month label, month start, and next month start in Europe/Berlin."""
    if at is None:
        at = timezone.now()

    if timezone.is_naive(at):
        raise ValueError("Reference datetime must be timezone-aware.")

    tz = timezone.get_current_timezone()
    local_dt = timezone.localtime(at, tz)

    month_label = local_dt.strftime("%B %Y")
    month_start = local_dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    if local_dt.month == 12:
        next_month_start = local_dt.replace(
            year=local_dt.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0
        )
    else:
        next_month_start = local_dt.replace(
            month=local_dt.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0
        )

    return month_label, month_start, next_month_start


def get_household_scores(at: datetime | None = None) -> tuple[str, list[MemberScore]]:
    """Return the month label and scores for all household members in display order."""
    month_label, month_start, next_month_start = _get_local_month_bounds(at)

    members = (
        Member.objects.annotate(
            annotated_monthly_points=Coalesce(
                Sum(
                    "completions__awarded_points",
                    filter=Q(
                        completions__completed_at__gte=month_start,
                        completions__completed_at__lt=next_month_start,
                    ),
                ),
                Value(0),
            ),
            annotated_lifetime_xp=Coalesce(
                Sum("completions__awarded_points"),
                Value(0),
            ),
        )
        .order_by("display_order", "pk")
    )

    scores = []
    for member in members:
        monthly_points = member.annotated_monthly_points
        lifetime_xp = member.annotated_lifetime_xp
        scores.append(
            MemberScore(
                member=member,
                monthly_points=monthly_points,
                lifetime_xp=lifetime_xp,
                garden_stage=calculate_garden_stage(lifetime_xp),
            )
        )

    return month_label, scores


def get_member_scores(member: Member, at: datetime | None = None) -> MemberScore:
    """Return the score details for an individual member."""
    _, month_start, next_month_start = _get_local_month_bounds(at)

    aggregated = Member.objects.filter(pk=member.pk).aggregate(
        monthly_points=Coalesce(
            Sum(
                "completions__awarded_points",
                filter=Q(
                    completions__completed_at__gte=month_start,
                    completions__completed_at__lt=next_month_start,
                ),
            ),
            Value(0),
        ),
        lifetime_xp=Coalesce(
            Sum("completions__awarded_points"),
            Value(0),
        ),
    )

    monthly_points = aggregated["monthly_points"]
    lifetime_xp = aggregated["lifetime_xp"]

    return MemberScore(
        member=member,
        monthly_points=monthly_points,
        lifetime_xp=lifetime_xp,
        garden_stage=calculate_garden_stage(lifetime_xp),
    )
