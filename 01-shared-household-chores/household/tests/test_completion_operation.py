"""Tests for the atomic chore completion operation."""

from datetime import date, datetime, timezone as datetime_timezone
from unittest.mock import patch

from django.db import IntegrityError
from django.test import TestCase

from household.completion import CompletionResult, CompletionStatus, complete_chore
from household.models import Chore, Completion, Member


class CompletionOperationTests(TestCase):
    def setUp(self):
        self.member = Member.objects.create(name="Alex", display_order=1)
        self.other_member = Member.objects.create(name="Sam", display_order=2)
        self.chore = Chore.objects.create(
            name="Sweep kitchen",
            frequency_days=7,
            points=15,
            next_due_date=date(2026, 9, 6),
            is_active=True,
            completion_version=0,
        )
        self.now = datetime(2026, 9, 6, 12, 0, tzinfo=datetime_timezone.utc)

    def test_complete_chore_success(self):
        result = complete_chore(
            member_id=self.member.pk,
            chore_id=self.chore.pk,
            expected_version=0,
            completed_at=self.now,
        )

        self.assertEqual(result.status, CompletionStatus.SUCCESS)
        self.assertIsNotNone(result.completion)
        self.assertEqual(result.completion.member, self.member)
        self.assertEqual(result.completion.chore, self.chore)
        self.assertEqual(result.completion.awarded_points, 15)
        self.assertEqual(result.completion.chore_name_snapshot, "Sweep kitchen")
        self.assertEqual(result.completion.completed_version, 0)
        self.assertEqual(result.completion.completed_at, self.now)

        # Chore state updated
        self.chore.refresh_from_db()
        self.assertEqual(self.chore.completion_version, 1)
        self.assertEqual(self.chore.next_due_date, date(2026, 9, 13))

    def test_complete_chore_accepts_model_instances(self):
        result = complete_chore(
            member_id=self.member,
            chore_id=self.chore,
            expected_version=0,
            completed_at=self.now,
        )
        self.assertEqual(result.status, CompletionStatus.SUCCESS)

    def test_complete_chore_requires_timezone_aware_datetime(self):
        naive_now = datetime(2026, 9, 6, 12, 0)
        with self.assertRaises(ValueError):
            complete_chore(
                member_id=self.member.pk,
                chore_id=self.chore.pk,
                expected_version=0,
                completed_at=naive_now,
            )

    def test_complete_chore_member_not_found(self):
        result = complete_chore(
            member_id=9999,
            chore_id=self.chore.pk,
            expected_version=0,
            completed_at=self.now,
        )
        self.assertEqual(result.status, CompletionStatus.NOT_FOUND)
        self.assertEqual(Completion.objects.count(), 0)

    def test_complete_chore_chore_not_found(self):
        result = complete_chore(
            member_id=self.member.pk,
            chore_id=9999,
            expected_version=0,
            completed_at=self.now,
        )
        self.assertEqual(result.status, CompletionStatus.NOT_FOUND)
        self.assertEqual(Completion.objects.count(), 0)

    def test_complete_chore_inactive_chore_rejected(self):
        self.chore.is_active = False
        self.chore.save()

        result = complete_chore(
            member_id=self.member.pk,
            chore_id=self.chore.pk,
            expected_version=0,
            completed_at=self.now,
        )
        self.assertEqual(result.status, CompletionStatus.INACTIVE_CHORE)
        self.assertEqual(Completion.objects.count(), 0)
        self.chore.refresh_from_db()
        self.assertEqual(self.chore.completion_version, 0)

    def test_complete_chore_ineligible_future_chore_rejected(self):
        # Chore is due in future: 2026-09-10
        self.chore.next_due_date = date(2026, 9, 10)
        self.chore.save()

        result = complete_chore(
            member_id=self.member.pk,
            chore_id=self.chore.pk,
            expected_version=0,
            completed_at=self.now,  # 2026-09-06
        )
        self.assertEqual(result.status, CompletionStatus.INELIGIBLE)
        self.assertEqual(Completion.objects.count(), 0)
        self.chore.refresh_from_db()
        self.assertEqual(self.chore.completion_version, 0)
        self.assertEqual(self.chore.next_due_date, date(2026, 9, 10))

    def test_complete_chore_stale_expected_version_rejected(self):
        # Chore is at version 0, but request supplies expected_version=1
        result = complete_chore(
            member_id=self.member.pk,
            chore_id=self.chore.pk,
            expected_version=1,
            completed_at=self.now,
        )
        self.assertEqual(result.status, CompletionStatus.STALE_VERSION)
        self.assertEqual(Completion.objects.count(), 0)
        self.chore.refresh_from_db()
        self.assertEqual(self.chore.completion_version, 0)

    def test_complete_chore_repeated_submission_returns_stale(self):
        # First submission succeeds
        first_result = complete_chore(
            member_id=self.member.pk,
            chore_id=self.chore.pk,
            expected_version=0,
            completed_at=self.now,
        )
        self.assertEqual(first_result.status, CompletionStatus.SUCCESS)

        # Repeated submission with old expected_version=0
        second_result = complete_chore(
            member_id=self.other_member.pk,
            chore_id=self.chore.pk,
            expected_version=0,
            completed_at=self.now,
        )
        self.assertEqual(second_result.status, CompletionStatus.STALE_VERSION)
        self.assertEqual(Completion.objects.count(), 1)
        self.chore.refresh_from_db()
        self.assertEqual(self.chore.completion_version, 1)

    def test_complete_chore_atomic_rollback_on_failure(self):
        # Simulate an IntegrityError or unexpected database error during completion creation
        with patch.object(Completion.objects, "create", side_effect=IntegrityError("Simulated DB failure")):
            result = complete_chore(
                member_id=self.member.pk,
                chore_id=self.chore.pk,
                expected_version=0,
                completed_at=self.now,
            )

        self.assertEqual(result.status, CompletionStatus.STALE_VERSION)
        self.assertEqual(Completion.objects.count(), 0)
        self.chore.refresh_from_db()
        self.assertEqual(self.chore.completion_version, 0)
        self.assertEqual(self.chore.next_due_date, date(2026, 9, 6))
