from datetime import date, datetime, timedelta, timezone as datetime_timezone
from zoneinfo import ZoneInfo

from django.test import TestCase

from household.models import Chore, Completion, Member, household_local_date as model_local_date
from household.scheduling import (
    HOUSEHOLD_TIME_ZONE,
    DueEvaluation,
    DueStatus,
    calculate_next_due_date,
    evaluate_due,
    household_local_date,
)


class HouseholdLocalDateTests(TestCase):
    def test_household_timezone_is_the_shared_berlin_zone(self):
        self.assertEqual(HOUSEHOLD_TIME_ZONE, ZoneInfo("Europe/Berlin"))

    def test_converts_utc_and_other_timezone_instants_to_berlin_date(self):
        self.assertEqual(
            household_local_date(datetime(2026, 1, 1, 23, 30, tzinfo=datetime_timezone.utc)),
            date(2026, 1, 2),
        )
        new_york = ZoneInfo("America/New_York")
        self.assertEqual(
            household_local_date(datetime(2026, 7, 1, 20, 30, tzinfo=new_york)),
            date(2026, 7, 2),
        )

    def test_handles_standard_and_daylight_saving_date_boundaries(self):
        # Standard time: midnight Berlin is 23:00 UTC on the preceding day.
        self.assertEqual(
            household_local_date(datetime(2026, 1, 10, 22, 59, tzinfo=datetime_timezone.utc)),
            date(2026, 1, 10),
        )
        self.assertEqual(
            household_local_date(datetime(2026, 1, 10, 23, 0, tzinfo=datetime_timezone.utc)),
            date(2026, 1, 11),
        )
        # Daylight saving time: midnight Berlin is 22:00 UTC on the preceding day.
        self.assertEqual(
            household_local_date(datetime(2026, 7, 10, 21, 59, tzinfo=datetime_timezone.utc)),
            date(2026, 7, 10),
        )
        self.assertEqual(
            household_local_date(datetime(2026, 7, 10, 22, 0, tzinfo=datetime_timezone.utc)),
            date(2026, 7, 11),
        )

    def test_rejects_naive_and_non_datetime_instants(self):
        for value in (datetime(2026, 1, 1), "2026-01-01", None, date(2026, 1, 1)):
            with self.subTest(value=value):
                if value is None:
                    # None is reserved for the omitted-now behavior, so pass it through
                    # the functions which require a supplied instant instead.
                    with self.assertRaises(TypeError):
                        calculate_next_due_date(date(2026, 1, 1), 1, completed_at=value)
                elif isinstance(value, datetime) and value.tzinfo is None:
                    with self.assertRaises(ValueError):
                        household_local_date(value)
                else:
                    with self.assertRaises(TypeError):
                        household_local_date(value)

    def test_model_migration_callable_delegates_to_shared_implementation(self):
        instant = datetime(2026, 3, 28, 23, 30, tzinfo=datetime_timezone.utc)
        # The migration callable has no explicit-instant argument, but it remains the
        # exact compatibility entry point used by Chore.next_due_date defaults.
        self.assertEqual(model_local_date.__module__, "household.models")
        self.assertEqual(household_local_date(instant), date(2026, 3, 29))


class DueEvaluationTests(TestCase):
    due_date = date(2026, 3, 10)

    def test_due_status_boundaries_and_eligibility(self):
        cases = (
            (datetime(2026, 3, 8, 23, 0, tzinfo=datetime_timezone.utc), DueStatus.NOT_YET_DUE, False),
            (datetime(2026, 3, 9, 23, 0, tzinfo=datetime_timezone.utc), DueStatus.DUE, True),
            (datetime(2026, 3, 10, 23, 0, tzinfo=datetime_timezone.utc), DueStatus.OVERDUE, True),
        )
        for instant, status, eligible in cases:
            with self.subTest(instant=instant):
                evaluation = evaluate_due(self.due_date, at=instant)
                self.assertIsInstance(evaluation, DueEvaluation)
                self.assertEqual(evaluation.due_date, self.due_date)
                self.assertEqual(evaluation.status, status)
                self.assertEqual(evaluation.eligible, eligible)
                self.assertEqual(evaluation.local_date, household_local_date(instant))

    def test_due_evaluation_is_immutable_and_enum_values_are_serialized_strings(self):
        evaluation = evaluate_due(
            self.due_date, at=datetime(2026, 3, 9, 23, tzinfo=datetime_timezone.utc)
        )
        self.assertEqual(
            [(status.name, status.value) for status in DueStatus],
            [
                ("NOT_YET_DUE", "not_yet_due"),
                ("DUE", "due"),
                ("OVERDUE", "overdue"),
            ],
        )
        with self.assertRaises(AttributeError):
            evaluation.eligible = False

    def test_rejects_invalid_due_dates_and_instants(self):
        for invalid_due_date in (datetime(2026, 3, 10, tzinfo=datetime_timezone.utc), "2026-03-10", None, 1):
            with self.subTest(invalid_due_date=invalid_due_date):
                with self.assertRaises(TypeError):
                    evaluate_due(invalid_due_date, at=datetime(2026, 3, 9, tzinfo=datetime_timezone.utc))
        with self.assertRaises(ValueError):
            evaluate_due(self.due_date, at=datetime(2026, 3, 10))
        with self.assertRaises(TypeError):
            evaluate_due(self.due_date, at="2026-03-10T00:00:00+00:00")


class RecurrenceTests(TestCase):
    @staticmethod
    def berlin_noon(day):
        return datetime.combine(day, datetime.min.time(), tzinfo=HOUSEHOLD_TIME_ZONE) + timedelta(hours=12)

    def test_uses_prior_due_date_as_anchor_for_on_time_and_overdue_completion(self):
        self.assertEqual(
            calculate_next_due_date(date(2026, 12, 31), 7, completed_at=self.berlin_noon(date(2026, 12, 31))),
            date(2027, 1, 7),
        )
        self.assertEqual(
            calculate_next_due_date(date(2026, 1, 1), 7, completed_at=self.berlin_noon(date(2026, 1, 20))),
            date(2026, 1, 22),
        )
        self.assertEqual(
            calculate_next_due_date(date(2026, 3, 1), 14, completed_at=self.berlin_noon(date(2026, 3, 20))),
            date(2026, 3, 29),
        )

    def test_uses_elapsed_calendar_days_across_months_and_leap_days(self):
        cases = (
            (date(2026, 1, 31), 1, date(2026, 1, 31), date(2026, 2, 1)),
            (date(2024, 2, 28), 1, date(2024, 2, 28), date(2024, 2, 29)),
            (date(2024, 2, 29), 365, date(2024, 2, 29), date(2025, 2, 28)),
        )
        for previous, frequency, completed, expected in cases:
            with self.subTest(previous=previous, frequency=frequency):
                self.assertEqual(
                    calculate_next_due_date(previous, frequency, completed_at=self.berlin_noon(completed)),
                    expected,
                )

    def test_rejects_early_completion_without_mutating_records(self):
        member = Member.objects.create(name="Alex", display_order=1)
        chore = Chore.objects.create(
            name="Bins", frequency_days=7, points=5, next_due_date=date(2026, 3, 10)
        )
        with self.assertRaises(ValueError):
            calculate_next_due_date(
                chore.next_due_date,
                chore.frequency_days,
                completed_at=self.berlin_noon(date(2026, 3, 9)),
            )
        chore.refresh_from_db()
        self.assertEqual(chore.next_due_date, date(2026, 3, 10))
        self.assertEqual(chore.completion_version, 0)
        self.assertEqual(Completion.objects.count(), 0)
        self.assertEqual(member.completions.count(), 0)

    def test_calculations_do_not_write_models(self):
        member = Member.objects.create(name="Alex", display_order=1)
        chore = Chore.objects.create(
            name="Dishes", frequency_days=7, points=5, next_due_date=date(2026, 3, 10)
        )
        instant = self.berlin_noon(date(2026, 3, 12))
        household_local_date(instant)
        evaluation = evaluate_due(chore.next_due_date, at=instant)
        self.assertEqual(evaluation.status, DueStatus.OVERDUE)
        self.assertEqual(
            calculate_next_due_date(chore.next_due_date, chore.frequency_days, completed_at=instant),
            date(2026, 3, 17),
        )
        chore.refresh_from_db()
        self.assertEqual(chore.next_due_date, date(2026, 3, 10))
        self.assertEqual(chore.completion_version, 0)
        self.assertEqual(Completion.objects.count(), 0)
        self.assertEqual(member.completions.count(), 0)

    def test_rejects_invalid_dates_frequency_and_completion_instants(self):
        completed_at = self.berlin_noon(date(2026, 3, 10))
        for invalid_date in (datetime(2026, 3, 10, tzinfo=datetime_timezone.utc), "2026-03-10", None, 1):
            with self.subTest(invalid_date=invalid_date):
                with self.assertRaises(TypeError):
                    calculate_next_due_date(invalid_date, 7, completed_at=completed_at)
        for invalid_frequency in (True, False, 1.0, "7", None):
            with self.subTest(invalid_frequency=invalid_frequency):
                with self.assertRaises(TypeError):
                    calculate_next_due_date(date(2026, 3, 10), invalid_frequency, completed_at=completed_at)
        for invalid_frequency in (0, -1, 366):
            with self.subTest(invalid_frequency=invalid_frequency):
                with self.assertRaises(ValueError):
                    calculate_next_due_date(date(2026, 3, 10), invalid_frequency, completed_at=completed_at)
        with self.assertRaises(ValueError):
            calculate_next_due_date(date(2026, 3, 10), 7, completed_at=datetime(2026, 3, 10))
        with self.assertRaises(TypeError):
            calculate_next_due_date(date(2026, 3, 10), 7, completed_at="2026-03-10T00:00:00+00:00")
