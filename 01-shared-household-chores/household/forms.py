"""Forms for creating and editing household chores."""

from datetime import date

from django import forms

from household.models import Chore, normalize_chore_name
from household.scheduling import household_local_date


class NormalizedChoreNameField(forms.CharField):
    """CharField that normalizes whitespace before length and presence checks."""

    def to_python(self, value):
        val = super().to_python(value)
        if val:
            return normalize_chore_name(val)
        return ""


class ChoreForm(forms.ModelForm):
    name = NormalizedChoreNameField(
        label="Chore name",
        max_length=100,
        required=True,
        widget=forms.TextInput(
            attrs={
                "id": "id_name",
                "placeholder": "e.g. Wash dishes",
            }
        ),
    )
    frequency_days = forms.IntegerField(
        label="Frequency in days",
        min_value=1,
        max_value=365,
        required=True,
        widget=forms.NumberInput(
            attrs={
                "id": "id_frequency_days",
                "min": 1,
                "max": 365,
            }
        ),
    )
    points = forms.IntegerField(
        label="Points",
        min_value=1,
        max_value=100,
        required=True,
        widget=forms.NumberInput(
            attrs={
                "id": "id_points",
                "min": 1,
                "max": 100,
            }
        ),
    )
    next_due_date = forms.DateField(
        label="Next due date",
        required=True,
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(
            format="%Y-%m-%d",
            attrs={
                "type": "date",
                "id": "id_next_due_date",
            },
        ),
    )

    class Meta:
        model = Chore
        fields = ["name", "frequency_days", "points", "next_due_date"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound and (not self.instance or not self.instance.pk):
            if not self.initial.get("next_due_date"):
                self.initial["next_due_date"] = household_local_date().strftime("%Y-%m-%d")

    def clean_name(self):
        name = self.cleaned_data.get("name")
        if not name:
            return name

        conflicts = Chore.objects.filter(is_active=True, name__iexact=name)
        if self.instance and self.instance.pk:
            conflicts = conflicts.exclude(pk=self.instance.pk)

        if conflicts.exists():
            raise forms.ValidationError("An active chore with this name already exists.")

        return name

    def save(self, commit=True):
        chore = super().save(commit=False)
        if not chore.pk:
            chore.is_active = True
            chore.completion_version = 0
        if commit:
            chore.save()
        return chore
