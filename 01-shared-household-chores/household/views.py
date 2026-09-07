from dataclasses import dataclass

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from household.completion import CompletionStatus, complete_chore
from household.forms import ChoreForm
from household.models import Chore, Member
from household.scheduling import DueStatus, evaluate_due
from household.scores import get_household_scores, get_member_scores


@dataclass(frozen=True)
class ChoreDisplay:
    """Presentation data prepared by the household view."""

    chore: Chore
    status_label: str
    status_sort_order: int
    eligible: bool


STATUS_LABELS = {
    DueStatus.OVERDUE: ("Overdue", 0),
    DueStatus.DUE: ("Due", 1),
    DueStatus.NOT_YET_DUE: ("Not yet due", 2),
}

MAX_BIGINT = 2**63 - 1
MAX_POSITIVE_INTEGER = 2**31 - 1


def _parse_nonnegative_ascii_integer(value: str, *, maximum: int) -> int | None:
    """Return an integer only for non-negative ASCII decimal input."""

    if not value or not value.isascii() or not value.isdecimal():
        return None
    parsed = int(value)
    return parsed if parsed <= maximum else None


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
                eligible=evaluation.eligible,
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
    month_label, member_scores = get_household_scores()
    return render(
        request,
        "household/home.html",
        {
            "month_label": month_label,
            "member_scores": member_scores,
            "members": [score.member for score in member_scores],
            "active_chores": _active_chore_displays(),
        },
    )


def chore_create(request):
    if request.method == "POST":
        form = ChoreForm(request.POST)
        if form.is_valid():
            chore = form.save()
            messages.success(request, f'Chore "{chore.name}" created.')
            return redirect("household:home")
    else:
        form = ChoreForm()

    return render(
        request,
        "household/chore_form.html",
        {
            "form": form,
            "is_edit": False,
        },
    )


def chore_edit(request, pk):
    chore = get_object_or_404(Chore, pk=pk, is_active=True)
    if request.method == "POST":
        form = ChoreForm(request.POST, instance=chore)
        if form.is_valid():
            chore = form.save()
            messages.success(request, f'Chore "{chore.name}" updated.')
            return redirect("household:home")
    else:
        form = ChoreForm(instance=chore)

    return render(
        request,
        "household/chore_form.html",
        {
            "form": form,
            "chore": chore,
            "is_edit": True,
        },
    )


def chore_delete(request, pk):
    chore = get_object_or_404(Chore, pk=pk, is_active=True)
    if request.method == "POST":
        chore.is_active = False
        chore.save(update_fields=["is_active"])
        messages.success(request, f'Chore "{chore.name}" deleted.')
        return redirect("household:home")

    return render(
        request,
        "household/chore_confirm_delete.html",
        {
            "chore": chore,
        },
    )


def chore_complete(request, pk):
    if request.method != "POST":
        return redirect("household:home")

    member_raw = request.POST.get("member", "").strip()
    version_raw = request.POST.get("completion_version", "").strip()

    member_id = _parse_nonnegative_ascii_integer(member_raw, maximum=MAX_BIGINT)
    if member_id is None:
        messages.error(request, "Please select a household member.")
        return redirect("household:home")

    expected_version = _parse_nonnegative_ascii_integer(
        version_raw,
        maximum=MAX_POSITIVE_INTEGER,
    )
    if expected_version is None:
        messages.error(request, "Invalid submission.")
        return redirect("household:home")

    result = complete_chore(
        member_id=member_id,
        chore_id=pk,
        expected_version=expected_version,
    )

    if result.status == CompletionStatus.SUCCESS:
        messages.success(request, result.message)
    elif result.status in (CompletionStatus.STALE_VERSION, CompletionStatus.INELIGIBLE):
        messages.warning(request, result.message)
    else:
        messages.error(request, result.message)

    return redirect("household:home")


def member_detail(request, pk):
    member = get_object_or_404(Member, pk=pk)
    score = get_member_scores(member)
    completions = member.completions.order_by("-completed_at", "-pk")
    return render(
        request,
        "household/member_detail.html",
        {
            "member": member,
            "score": score,
            "completions": completions,
        },
    )


def neighborhood(request):
    """Render every predefined member's lifetime-XP-derived garden."""

    _, member_scores = get_household_scores()
    return render(
        request,
        "household/neighborhood.html",
        {
            "member_scores": member_scores,
        },
    )
