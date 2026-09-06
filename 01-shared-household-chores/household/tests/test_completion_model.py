from datetime import date, datetime, timezone as datetime_timezone

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase, override_settings
from django.utils import timezone

from household.models import Chore, Completion, Member


@override_settings(USE_TZ=True, TIME_ZONE="Europe/Berlin")
class CompletionModelTests(TestCase):
    def setUp(self):
        self.member = Member.objects.create(name="Alex", display_order=1)
        self.chore = Chore.objects.create(
            name="Dishes",
            frequency_days=7,
            points=10,
            next_due_date=date(2026, 9, 6),
        )

    def make_completion(self, **overrides):
        values = {
            "member": self.member,
            "chore": self.chore,
            "awarded_points": 10,
            "chore_name_snapshot": "Dishes",
            "completed_version": 0,
        }
        values.update(overrides)
        return Completion(**values)

    def test_valid_completion_stores_all_required_values(self):
        completed_at = datetime(2026, 9, 6, 12, 30, tzinfo=datetime_timezone.utc)
        completion = self.make_completion(completed_at=completed_at)

        completion.full_clean()
        completion.save()
        completion.refresh_from_db()

        self.assertEqual(completion.member, self.member)
        self.assertEqual(completion.chore, self.chore)
        self.assertEqual(completion.completed_at, completed_at)
        self.assertEqual(completion.awarded_points, 10)
        self.assertEqual(completion.chore_name_snapshot, "Dishes")
        self.assertEqual(completion.completed_version, 0)

    def test_default_timestamp_is_current_and_reads_back_timezone_aware(self):
        before = timezone.now()
        completion = self.make_completion()
        after = timezone.now()

        self.assertLessEqual(before, completion.completed_at)
        self.assertLessEqual(completion.completed_at, after)

        completion.save()
        completion.refresh_from_db()
        self.assertTrue(timezone.is_aware(completion.completed_at))

    def test_model_validation_rejects_naive_timestamp(self):
        for completed_at in (
            datetime(2026, 9, 6, 12, 30),
            "2026-09-06T12:30:00",
        ):
            with self.subTest(completed_at=completed_at):
                completion = self.make_completion(completed_at=completed_at)

                with self.assertRaises(ValidationError) as raised:
                    completion.full_clean()

                self.assertIn("completed_at", raised.exception.message_dict)

    def test_required_fields_reject_missing_values(self):
        for field_name in (
            "member",
            "chore",
            "completed_at",
            "awarded_points",
            "chore_name_snapshot",
            "completed_version",
        ):
            with self.subTest(field_name=field_name):
                completion = self.make_completion(**{field_name: None})
                with self.assertRaises(ValidationError) as raised:
                    completion.full_clean()
                self.assertIn(field_name, raised.exception.message_dict)

    def test_awarded_points_accepts_integer_boundaries(self):
        for points in (1, 100):
            with self.subTest(points=points):
                self.make_completion(awarded_points=points).full_clean()

    def test_awarded_points_rejects_invalid_model_values(self):
        for points in (None, "", True, False, 0, -1, 1.5, 101):
            with self.subTest(points=points):
                with self.assertRaises(ValidationError) as raised:
                    self.make_completion(awarded_points=points).full_clean()
                self.assertIn("awarded_points", raised.exception.message_dict)

    def test_database_rejects_awarded_points_outside_range(self):
        for points in (0, -1, 101):
            with self.subTest(points=points):
                with self.assertRaises(IntegrityError):
                    with transaction.atomic():
                        Completion.objects.create(
                            member=self.member,
                            chore=self.chore,
                            awarded_points=points,
                            chore_name_snapshot="Dishes",
                            completed_version=0,
                        )

    def test_chore_name_snapshot_validation(self):
        self.make_completion(chore_name_snapshot="x" * 100).full_clean()

        for snapshot in ("", " \t\n ", "x" * 101):
            with self.subTest(snapshot=snapshot):
                with self.assertRaises(ValidationError) as raised:
                    self.make_completion(chore_name_snapshot=snapshot).full_clean()
                self.assertIn("chore_name_snapshot", raised.exception.message_dict)

    def test_database_rejects_empty_chore_name_snapshot(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Completion.objects.create(
                    member=self.member,
                    chore=self.chore,
                    awarded_points=10,
                    chore_name_snapshot="",
                    completed_version=0,
                )

    def test_completed_version_accepts_nonnegative_integers(self):
        for completed_version in (0, 1):
            with self.subTest(completed_version=completed_version):
                self.make_completion(completed_version=completed_version).full_clean()

    def test_completed_version_rejects_invalid_model_values(self):
        for completed_version in (None, "", True, False, -1, 1.5):
            with self.subTest(completed_version=completed_version):
                with self.assertRaises(ValidationError) as raised:
                    self.make_completion(completed_version=completed_version).full_clean()
                self.assertIn("completed_version", raised.exception.message_dict)

    def test_database_rejects_negative_completed_version(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Completion.objects.create(
                    member=self.member,
                    chore=self.chore,
                    awarded_points=10,
                    chore_name_snapshot="Dishes",
                    completed_version=-1,
                )

    def test_duplicate_chore_occurrence_is_rejected(self):
        self.make_completion(completed_version=2).save()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.make_completion(completed_version=2).save()

    def test_same_completed_version_is_allowed_for_different_chores(self):
        other_chore = Chore.objects.create(
            name="Bins",
            frequency_days=7,
            points=5,
            next_due_date=date(2026, 9, 6),
        )

        self.make_completion(completed_version=3).save()
        self.make_completion(chore=other_chore, completed_version=3).save()

        self.assertEqual(Completion.objects.count(), 2)

    def test_deleting_referenced_member_is_protected(self):
        completion = self.make_completion()
        completion.save()

        with self.assertRaises(ProtectedError):
            self.member.delete()

        completion.refresh_from_db()
        self.assertEqual(completion.member, self.member)
        self.assertEqual(Completion.objects.count(), 1)

    def test_deleting_referenced_chore_is_protected(self):
        completion = self.make_completion()
        completion.save()

        with self.assertRaises(ProtectedError):
            self.chore.delete()

        completion.refresh_from_db()
        self.assertEqual(completion.chore, self.chore)
        self.assertEqual(Completion.objects.count(), 1)

    def test_inactive_chore_retains_completion_and_snapshots(self):
        completed_at = datetime(2026, 9, 6, 12, 30, tzinfo=datetime_timezone.utc)
        completion = self.make_completion(
            completed_at=completed_at,
            awarded_points=10,
            chore_name_snapshot="Dishes",
            completed_version=4,
        )
        completion.save()

        self.chore.is_active = False
        self.chore.save()
        completion.refresh_from_db()

        self.assertFalse(completion.chore.is_active)
        self.assertEqual(completion.completed_at, completed_at)
        self.assertEqual(completion.awarded_points, 10)
        self.assertEqual(completion.chore_name_snapshot, "Dishes")
        self.assertEqual(completion.completed_version, 4)

    def test_later_chore_edits_do_not_change_completion_snapshot(self):
        completed_at = datetime(2026, 9, 6, 12, 30, tzinfo=datetime_timezone.utc)
        completion = self.make_completion(
            completed_at=completed_at,
            awarded_points=10,
            chore_name_snapshot="Dishes",
            completed_version=5,
        )
        completion.save()
        original_member_id = completion.member_id
        original_chore_id = completion.chore_id

        self.chore.name = "Kitchen cleanup"
        self.chore.points = 75
        self.chore.save()
        completion.refresh_from_db()

        self.assertEqual(completion.completed_at, completed_at)
        self.assertEqual(completion.awarded_points, 10)
        self.assertEqual(completion.chore_name_snapshot, "Dishes")
        self.assertEqual(completion.completed_version, 5)
        self.assertEqual(completion.member_id, original_member_id)
        self.assertEqual(completion.chore_id, original_chore_id)

    def test_default_ordering_is_newest_first_with_primary_key_tiebreaker(self):
        older = self.make_completion(
            completed_at=datetime(2026, 9, 5, 12, tzinfo=datetime_timezone.utc),
            completed_version=0,
        )
        older.save()
        shared_time = datetime(2026, 9, 6, 12, tzinfo=datetime_timezone.utc)
        first_at_shared_time = self.make_completion(
            completed_at=shared_time,
            completed_version=1,
        )
        first_at_shared_time.save()
        second_at_shared_time = self.make_completion(
            completed_at=shared_time,
            completed_version=2,
        )
        second_at_shared_time.save()

        self.assertEqual(
            list(Completion.objects.all()),
            [second_at_shared_time, first_at_shared_time, older],
        )
