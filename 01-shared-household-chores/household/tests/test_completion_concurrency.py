"""Concurrency tests for atomic chore completion with SQLite."""

import os
import tempfile
import threading
from datetime import date, datetime, timezone as datetime_timezone
from unittest.mock import call, patch

from django.db import OperationalError, connection, connections
from django.db.models import Sum
from django.test import TransactionTestCase

from household.completion import (
    INITIAL_BACKOFF_SECONDS,
    MAX_LOCK_RETRIES,
    CompletionStatus,
    complete_chore,
)
from household.models import Chore, Completion, Member


class SQLiteContentionAndConcurrencyTests(TransactionTestCase):
    """Exercise completion against a temporary, file-backed SQLite database."""

    def setUp(self):
        super().setUp()
        descriptor, database_name = tempfile.mkstemp(suffix="-completion-contention.sqlite3")
        os.close(descriptor)
        self._database_name = database_name
        self._original_database_name = connection.settings_dict["NAME"]

        # The application always uses the default alias. Point it at a fresh SQLite
        # file for this test so each worker opens its own connection to the same DB.
        connection.close()
        connection.settings_dict["NAME"] = self._database_name
        connection.connect()
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(Member)
            schema_editor.create_model(Chore)
            schema_editor.create_model(Completion)

        self.member1 = Member.objects.create(name="Alex", display_order=1)
        self.member2 = Member.objects.create(name="Sam", display_order=2)
        self.chore = Chore.objects.create(
            name="Scrub bathtub",
            frequency_days=7,
            points=20,
            next_due_date=date(2026, 9, 6),
            is_active=True,
            completion_version=0,
        )
        self.now = datetime(2026, 9, 6, 14, 0, tzinfo=datetime_timezone.utc)

    def tearDown(self):
        connection.close()
        connection.settings_dict["NAME"] = self._original_database_name
        connection.connect()
        os.unlink(self._database_name)
        super().tearDown()

    def test_competing_completions_use_separate_connections_and_award_once(self):
        """Two simultaneous callers share one SQLite file but not a connection."""
        barrier = threading.Barrier(2)
        results = []
        worker_connection_ids = []
        worker_errors = []
        result_lock = threading.Lock()

        def worker(member_id):
            worker_connection = connections["default"]
            worker_connection.close()
            try:
                # Force each thread to establish a distinct SQLite connection before
                # both calls race for the same optimistic-lock version.
                with worker_connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                with result_lock:
                    worker_connection_ids.append(id(worker_connection.connection))

                barrier.wait(timeout=5)
                result = complete_chore(
                    member_id=member_id,
                    chore_id=self.chore.pk,
                    expected_version=0,
                    completed_at=self.now,
                )
                with result_lock:
                    results.append(result)
            except BaseException as error:  # surfaced in the test thread below
                with result_lock:
                    worker_errors.append(error)
            finally:
                worker_connection.close()

        workers = [
            threading.Thread(target=worker, args=(self.member1.pk,)),
            threading.Thread(target=worker, args=(self.member2.pk,)),
        ]
        for worker_thread in workers:
            worker_thread.start()
        for worker_thread in workers:
            worker_thread.join(timeout=10)

        self.assertTrue(all(not worker_thread.is_alive() for worker_thread in workers))
        self.assertEqual(worker_errors, [])
        self.assertEqual(len(set(worker_connection_ids)), 2)
        self.assertEqual(len(results), 2)
        self.assertEqual(
            [result.status for result in results].count(CompletionStatus.SUCCESS), 1
        )
        self.assertEqual(
            [result.status for result in results if result.status != CompletionStatus.SUCCESS][0],
            CompletionStatus.STALE_VERSION,
        )

        # A losing request leaves no partial advancement or duplicate award.
        self.chore.refresh_from_db()
        self.assertEqual(self.chore.completion_version, 1)
        self.assertEqual(self.chore.next_due_date, date(2026, 9, 13))
        completions = Completion.objects.filter(chore=self.chore)
        self.assertEqual(completions.count(), 1)
        self.assertEqual(completions.aggregate(total=Sum("awarded_points"))["total"], 20)
        completion = completions.get()
        self.assertEqual(completion.completed_version, 0)
        self.assertEqual(completion.chore_name_snapshot, "Scrub bathtub")

    def test_locked_retries_have_bounded_count_and_exponential_backoff(self):
        """Persistent SQLite locks make exactly the configured number of attempts."""
        with (
            patch(
                "household.completion.transaction.atomic",
                side_effect=OperationalError("database is locked"),
            ) as atomic,
            patch("household.completion.time.sleep") as sleep,
        ):
            result = complete_chore(
                member_id=self.member1.pk,
                chore_id=self.chore.pk,
                expected_version=0,
                completed_at=self.now,
            )

        self.assertEqual(result.status, CompletionStatus.LOCKED)
        self.assertEqual(atomic.call_count, MAX_LOCK_RETRIES)
        self.assertEqual(
            sleep.call_args_list,
            [
                call(INITIAL_BACKOFF_SECONDS),
                call(INITIAL_BACKOFF_SECONDS * 2),
            ],
        )
        self.chore.refresh_from_db()
        self.assertEqual(self.chore.completion_version, 0)
        self.assertEqual(self.chore.next_due_date, date(2026, 9, 6))
        self.assertEqual(Completion.objects.count(), 0)

    def test_unrelated_operational_error_is_not_swallowed_or_retried(self):
        """Only SQLite busy/locked errors are recoverable contention outcomes."""
        with (
            patch(
                "household.completion.transaction.atomic",
                side_effect=OperationalError("unrecognized token / disk error"),
            ) as atomic,
            patch("household.completion.time.sleep") as sleep,
        ):
            with self.assertRaisesRegex(OperationalError, "unrecognized token"):
                complete_chore(
                    member_id=self.member1.pk,
                    chore_id=self.chore.pk,
                    expected_version=0,
                    completed_at=self.now,
                )

        self.assertEqual(atomic.call_count, 1)
        sleep.assert_not_called()

    def test_a_new_request_can_safely_succeed_after_locked_result(self):
        """An exhausted lock response commits nothing and a later retry is safe."""
        with (
            patch(
                "household.completion.transaction.atomic",
                side_effect=OperationalError("database is busy"),
            ),
            patch("household.completion.time.sleep"),
        ):
            locked_result = complete_chore(
                member_id=self.member1.pk,
                chore_id=self.chore.pk,
                expected_version=0,
                completed_at=self.now,
            )

        self.assertEqual(locked_result.status, CompletionStatus.LOCKED)
        retry_result = complete_chore(
            member_id=self.member1.pk,
            chore_id=self.chore.pk,
            expected_version=0,
            completed_at=self.now,
        )
        self.assertEqual(retry_result.status, CompletionStatus.SUCCESS)
        self.chore.refresh_from_db()
        self.assertEqual(self.chore.completion_version, 1)
        self.assertEqual(Completion.objects.filter(chore=self.chore).count(), 1)
