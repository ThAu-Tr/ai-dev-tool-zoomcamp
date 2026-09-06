from dataclasses import dataclass

from django.shortcuts import render

from household.models import Chore, Member
from household.scheduling import DueStatus, evaluate_due


@dataclass(frozen=True)
class ChoreDisplay:
    """Presentation data prepared by the household view."""

    chore: Chore
    status_label: str
    status_sort_order: int


STATUS_LABELS = {
    DueStatus.OVERDUE: ("Overdue", 0),
    DueStatus.DUE: ("Due", 1),
    DueStatus.NOT_YET_DUE: ("Not yet due", 2),
}


def _active_chore_displays() -> list[ChoreDisplay]:
    """Return active chores with due statuses and deterministic display order."""

    displays = []
    for chore in Chore.objects.filter(is_active=True):
        evaluation = evaluate_due(chore.next_due_date)
        status_label, status_sort_order = STATUS_LABELS[evaluation.status]
        displays.append(
            ChoreDisplay(
                chore=chore,
                status_label=status_label,
                status_sort_order=status_sort_order,
            )
        )

    return sorted(
        displays,
        key=lambda display: (
            display.status_sort_order,
            display.chore.next_due_date,
            display.chore.name.casefold(),
            display.chore.pk,
        ),
    )


def home(request):
    return render(
        request,
        "household/home.html",
        {
            "members": Member.objects.order_by("display_order", "pk"),
            "active_chores": _active_chore_displays(),
        },
    )
