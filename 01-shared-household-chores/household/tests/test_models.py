from datetime import date, datetime, timezone as datetime_timezone
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings

from household.models import Chore, Member, household_local_date


class MemberModelTests(TestCase):
    def test_name_and_display_order_are_required_and_individually_unique(self):
        first = Member(name="Alex", display_order=1)
        first.full_clean()
        first.save()

        invalid_members = (
            Member(name="", display_order=2),
            Member(name="Sam", display_order=0),
            Member(name="Alex", display_order=2),
            Member(name="Sam", display_order=1),
        )
        for member in invalid_members:
            with self.subTest(member=member):
                with self.assertRaises(ValidationError):
                    member.full_clean()

    def test_database_rejects_nonpositive_display_order(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Member.objects.create(name="Alex", display_order=0)


class ChoreModelTests(TestCase):
    def make_chore(self, **overrides):
        values = {
            "name": "Dishes",
            "frequency_days": 7,
            "points": 10,
            "next_due_date": date(2026, 3, 10),
        }
        values.update(overrides)
        return Chore(**values)

    def test_save_normalizes_whitespace_before_persisting(self):
        chore = self.make_chore(name="  Clean   Kitchen\t\n ")

        chore.save()

        chore.refresh_from_db()
        self.assertEqual(chore.name, "Clean Kitchen")

    def test_normalized_name_length_boundaries(self):
        accepted = self.make_chore(name=f"  {'x' * 100}  ")
        accepted.full_clean()
        self.assertEqual(len(accepted.name), 100)

        for name in (" \t\n ", "x" * 101):
            with self.subTest(name=name):
                chore = self.make_chore(name=name)
                with self.assertRaises(ValidationError) as raised:
                    chore.full_clean()
                self.assertIn("name", raised.exception.message_dict)

    def test_active_name_is_unique_ignoring_case_after_normalization(self):
        self.make_chore(name="Dishes").save()

        duplicate = self.make_chore(name=" dishes ")
        with self.assertRaises(ValidationError):
            duplicate.save()

    def test_database_rejects_case_insensitive_active_duplicate(self):
        self.make_chore(name="Dishes").save()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Chore.objects.bulk_create([self.make_chore(name="DISHES")])

    def test_inactive_name_can_be_reused_by_active_chore(self):
        self.make_chore(name="Dishes", is_active=False).save()

        active = self.make_chore(name=" dishes ")
        active.save()

        self.assertEqual(active.name, "dishes")

    def test_reactivating_conflicting_chore_is_rejected(self):
        self.make_chore(name="Dishes").save()
        inactive = self.make_chore(name="DISHES", is_active=False)
        inactive.save()

        inactive.is_active = True
        with self.assertRaises(ValidationError):
            inactive.save()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Chore.objects.filter(pk=inactive.pk).update(is_active=True)

    def test_frequency_and_points_accept_boundaries(self):
        for frequency_days in (1, 365):
            for points in (1, 100):
                with self.subTest(frequency_days=frequency_days, points=points):
                    self.make_chore(
                        frequency_days=frequency_days,
                        points=points,
                    ).full_clean()

    def test_frequency_and_points_reject_invalid_values(self):
        invalid_values = (None, "", True, False, 0, -1, 1.5, 366)
        for field_name in ("frequency_days", "points"):
            for value in invalid_values:
                if field_name == "points" and value == 366:
                    value = 101
                with self.subTest(field_name=field_name, value=value):
                    chore = self.make_chore(**{field_name: value})
                    with self.assertRaises(ValidationError) as raised:
                        chore.full_clean()
                    self.assertIn(field_name, raised.exception.message_dict)

    def test_database_enforces_numeric_ranges(self):
        invalid_fields = {
            "frequency_days": (0, 366),
            "points": (0, 101),
            "completion_version": (-1,),
        }
        for field_name, values in invalid_fields.items():
            for value in values:
                with self.subTest(field_name=field_name, value=value):
                    with self.assertRaises(IntegrityError):
                        with transaction.atomic():
                            Chore.objects.bulk_create(
                                [self.make_chore(**{field_name: value})]
                            )

    def test_defaults_are_active_with_version_zero(self):
        chore = self.make_chore()

        self.assertTrue(chore.is_active)
        self.assertEqual(chore.completion_version, 0)

    def test_completion_version_requires_nonnegative_integer(self):
        for value in (0, 1):
            self.make_chore(completion_version=value).full_clean()

        for value in (None, True, -1, 1.5):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    self.make_chore(completion_version=value).full_clean()

    def test_explicit_due_dates_are_preserved(self):
        for supplied_date in (
            date(2020, 1, 1),
            date(2026, 3, 10),
            date(2030, 12, 31),
        ):
            with self.subTest(supplied_date=supplied_date):
                chore = self.make_chore(next_due_date=supplied_date)
                chore.save()
                chore.refresh_from_db()
                self.assertEqual(chore.next_due_date, supplied_date)
                chore.delete()

    @override_settings(TIME_ZONE="Europe/Berlin", USE_TZ=True)
    @patch("household.models.timezone.now")
    def test_default_due_date_uses_europe_berlin_local_date(self, mocked_now):
        mocked_now.return_value = datetime(
            2026, 3, 28, 23, 30, tzinfo=datetime_timezone.utc
        )

        self.assertEqual(household_local_date(), date(2026, 3, 29))
        self.assertEqual(
            Chore(name="Bins", frequency_days=7, points=5).next_due_date,
            date(2026, 3, 29),
        )
