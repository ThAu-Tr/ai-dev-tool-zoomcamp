"""Core storage for the shared household."""

import re
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

from household.scheduling import household_local_date as _scheduling_household_local_date


def household_local_date():
    """Compatibility import path retained for the initial migration."""

    return _scheduling_household_local_date()


def normalize_chore_name(name: str) -> str:
    """Strip surrounding whitespace and collapse internal whitespace."""

    return re.sub(r"\s+", " ", name.strip())


class Member(models.Model):
    name = models.CharField(max_length=100, unique=True)
    display_order = models.PositiveIntegerField(
        unique=True,
        validators=[MinValueValidator(1)],
    )

    class Meta:
        ordering = ("display_order",)
        constraints = [
            models.CheckConstraint(
                condition=models.Q(display_order__gte=1),
                name="member_display_order_positive",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class Chore(models.Model):
    name = models.CharField(max_length=100)
    frequency_days = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(365)]
    )
    points = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(100)]
    )
    next_due_date = models.DateField(default=household_local_date)
    is_active = models.BooleanField(default=True)
    completion_version = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("name"),
                condition=models.Q(is_active=True),
                name="unique_active_chore_name_ci",
            ),
            models.CheckConstraint(
                condition=models.Q(frequency_days__gte=1)
                & models.Q(frequency_days__lte=365),
                name="chore_frequency_days_range",
            ),
            models.CheckConstraint(
                condition=models.Q(points__gte=1) & models.Q(points__lte=100),
                name="chore_points_range",
            ),
            models.CheckConstraint(
                condition=models.Q(completion_version__gte=0),
                name="chore_completion_version_nonnegative",
            ),
        ]

    def clean_fields(self, exclude=None):
        if isinstance(self.name, str):
            self.name = normalize_chore_name(self.name)

        errors = {}
        for field_name in ("frequency_days", "points", "completion_version"):
            value = getattr(self, field_name)
            if value is not None and type(value) is not int:
                errors[field_name] = "Enter a whole number."

        if errors:
            raise ValidationError(errors)

        super().clean_fields(exclude=exclude)

    def save(self, *args, **kwargs):
        original_name = self.name
        self.full_clean()

        update_fields = kwargs.get("update_fields")
        if (
            update_fields is not None
            and self.name != original_name
            and "name" not in update_fields
        ):
            kwargs["update_fields"] = {*update_fields, "name"}

        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class Completion(models.Model):
    member = models.ForeignKey(
        Member,
        on_delete=models.PROTECT,
        related_name="completions",
    )
    chore = models.ForeignKey(
        Chore,
        on_delete=models.PROTECT,
        related_name="completions",
    )
    completed_at = models.DateTimeField(default=timezone.now)
    awarded_points = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(100)]
    )
    chore_name_snapshot = models.CharField(max_length=100)
    completed_version = models.PositiveIntegerField()

    class Meta:
        ordering = ("-completed_at", "-pk")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(awarded_points__gte=1)
                & models.Q(awarded_points__lte=100),
                name="completion_awarded_points_range",
            ),
            models.CheckConstraint(
                condition=~models.Q(chore_name_snapshot=""),
                name="completion_chore_name_snapshot_nonempty",
            ),
            models.CheckConstraint(
                condition=models.Q(completed_version__gte=0),
                name="completion_version_nonnegative",
            ),
            models.UniqueConstraint(
                fields=("chore", "completed_version"),
                name="unique_chore_completed_version",
            ),
        ]

    def clean_fields(self, exclude=None):
        excluded_fields = set(exclude or ())
        errors = {}

        for field_name in ("awarded_points", "completed_version"):
            if field_name in excluded_fields:
                continue
            value = getattr(self, field_name)
            if value is not None and type(value) is not int:
                errors[field_name] = "Enter a whole number."

        if "completed_at" not in excluded_fields:
            completed_at = self.completed_at
            if completed_at is not None:
                try:
                    parsed_completed_at = self._meta.get_field(
                        "completed_at"
                    ).to_python(completed_at)
                except ValidationError:
                    pass
                else:
                    if timezone.is_naive(parsed_completed_at):
                        errors["completed_at"] = "Enter a timezone-aware timestamp."

        if "chore_name_snapshot" not in excluded_fields:
            snapshot = self.chore_name_snapshot
            if isinstance(snapshot, str) and not snapshot.strip():
                errors["chore_name_snapshot"] = "This field cannot be blank."

        if errors:
            raise ValidationError(errors)

        super().clean_fields(exclude=exclude)
