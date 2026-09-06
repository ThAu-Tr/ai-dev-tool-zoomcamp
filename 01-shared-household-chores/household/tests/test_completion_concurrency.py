"""Concurrency tests for atomic chore completion with SQLite."""

import threading
from datetime import date, datetime, timezone as datetime_timezone
from unittest.mock import patch

from django.db import connection, OperationalError
from household.completion import (
    CompletionResult,
    CompletionStatus,
    complete_chore,
)
from household.models import Chore, Completion, Member
from django.test import TransactionTestCase


class SQLiteContentionAndConcurrencyTests(TransactionTestCase):
    def setUp(self):
        # Create or fetch members
        self.member1, _ = Member.objects.get_or_create(name="Alex", defaults={"display_order": 1})
        self.member2, _ = Member.objects.get_or_create(name="Sam", defaults={"display_order": 2})
        self.chore = Chore.objects.create(
            name="Scrub bathtub",
            frequency_days=7,
            points=20,
            next_due_date=date(2026, 9, 6),
            is_active=True,
            completion_version=0,
        )
        self.now = datetime(2026, 9, 6, 14, 0, tzinfo=datetime_timezone.utc)

    def test_competing_completions_for_same_chore_occurrence(self):
        """Simultaneous completion attempts for the same version award points exactly once."""
        results = []
        barrier = threading.Barrier(2)

        def worker(member_id):
            connection.close()
            try:
                barrier.wait(timeout=5)
                res = complete_chore(
                    member_id=member_id,
                    chore_id=self.chore.pk,
                    expected_version=0,
                    completed_at=self.now,
                )
                results.append(res)
            finally:
                connection.close()

        t1 = threading.Thread(target=worker, args=(self.member1.pk,))
        t2 = threading.Thread(target=worker, args=(self.member2.pk,))

        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

        self.assertEqual(len(results), 2)
        statuses = [r.status for r in results]

        # Exactly one thread succeeds
        self.assertEqual(statuses.count(CompletionStatus.SUCCESS), 1)

        # The competing thread receives STALE_VERSION or LOCKED
        self.assertIn(
            statuses[0] if statuses[1] == CompletionStatus.SUCCESS else statuses[1],
            [CompletionStatus.STALE_VERSION, CompletionStatus.LOCKED],
        )

        # Verify database state has no partial or duplicate data
        self.chore.refresh_from_db()
        self.assertEqual(self.chore.completion_version, 1)
        self.assertEqual(self.chore.next_due_date, date(2026, 9, 13))

        completions = list(Completion.objects.filter(chore=self.chore))
        self.assertEqual(len(completions), 1)
        self.assertEqual(completions[0].awarded_points, 20)
        self.assertEqual(completions[0].completed_version, 0)
        self.assertEqual(completions[0].chore_name_snapshot, "Scrub bathtub")

    def test_lock_contention_retries_and_returns_locked_if_exhausted(self):
        """If SQLite remains locked across retries, complete_chore returns LOCKED."""
        with patch("django.db.transaction.atomic") as mock_atomic:
            mock_atomic.side_effect = OperationalError("database is locked")
            result = complete_chore(
                member_id=self.member1.pk,
                chore_id=self.chore.pk,
                expected_version=0,
                completed_at=self.now,
            )

        self.assertEqual(result.status, CompletionStatus.LOCKED)
        self.assertIn("busy", result.message.lower())

    def test_unrelated_operational_error_is_not_swallowed(self):
        """Unrelated OperationalErrors (e.g. disk corruption, syntax) are raised."""
        with patch("django.db.transaction.atomic") as mock_atomic:
            mock_atomic.side_effect = OperationalError("unrecognized token / disk error")
            with self.assertRaises(OperationalError):
                complete_chore(
                    member_id=self.member1.pk,
                    chore_id=self.chore.pk,
                    expected_version=0,
                    completed_at=self.now,
                )
