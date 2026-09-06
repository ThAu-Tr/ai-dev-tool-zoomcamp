"""Tests for member contribution queries and household scores display."""

from datetime import date, datetime, timezone as datetime_timezone
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.test import Client, TestCase
from django.urls import reverse

from household.models import Chore, Completion, Member
from household.scores import (
    _get_local_month_bounds,
    get_household_scores,
    get_member_scores,
)


class ScoreCalculationTests(TestCase):
    def setUp(self):
        self.alex = Member.objects.create(name="Alex", display_order=1)
        self.sam = Member.objects.create(name="Sam", display_order=2)
        self.jamie = Member.objects.create(name="Jamie", display_order=3)

        self.dish_chore = Chore.objects.create(
            name="Dishes",
            frequency_days=1,
            points=10,
            next_due_date=date(2026, 9, 6),
            is_active=True,
        )
        self.trash_chore = Chore.objects.create(
            name="Trash",
            frequency_days=7,
            points=20,
            next_due_date=date(2026, 9, 6),
            is_active=True,
        )

    def test_month_bounds_and_year_rollover(self):
        # December in Europe/Berlin
        dec_time = datetime(2026, 12, 15, 12, 0, tzinfo=ZoneInfo("Europe/Berlin"))
        label, start, next_start = _get_local_month_bounds(dec_time)
        self.assertEqual(label, "December 2026")
        self.assertEqual(start, datetime(2026, 12, 1, 0, 0, tzinfo=ZoneInfo("Europe/Berlin")))
        self.assertEqual(next_start, datetime(2027, 1, 1, 0, 0, tzinfo=ZoneInfo("Europe/Berlin")))

        # Month boundary across UTC / Europe/Berlin
        # 2026-09-30 23:00 UTC is 2026-10-01 01:00 CEST (UTC+2)
        sep_utc = datetime(2026, 9, 30, 23, 0, tzinfo=datetime_timezone.utc)
        label_oct, start_oct, next_start_oct = _get_local_month_bounds(sep_utc)
        self.assertEqual(label_oct, "October 2026")
        self.assertEqual(start_oct, datetime(2026, 10, 1, 0, 0, tzinfo=ZoneInfo("Europe/Berlin")))
        self.assertEqual(next_start_oct, datetime(2026, 11, 1, 0, 0, tzinfo=ZoneInfo("Europe/Berlin")))

    def test_month_bounds_rejects_naive_datetime(self):
        with self.assertRaises(ValueError):
            _get_local_month_bounds(datetime(2026, 9, 1, 12, 0))

    def test_members_with_zero_completions(self):
        eval_time = datetime(2026, 9, 15, 12, 0, tzinfo=ZoneInfo("Europe/Berlin"))
        label, scores = get_household_scores(eval_time)
        self.assertEqual(label, "September 2026")
        self.assertEqual(len(scores), 3)

        for score in scores:
            self.assertEqual(score.monthly_points, 0)
            self.assertEqual(score.lifetime_xp, 0)
            self.assertEqual(score.garden_stage.label, "Empty soil")

    def test_monthly_points_and_lifetime_xp_calculations(self):
        # 1. Past month completion (August 2026) for Alex (10 points)
        august_dt = datetime(2026, 8, 20, 10, 0, tzinfo=ZoneInfo("Europe/Berlin"))
        Completion.objects.create(
            member=self.alex,
            chore=self.dish_chore,
            completed_at=august_dt,
            awarded_points=10,
            chore_name_snapshot="Dishes",
            completed_version=0,
        )

        # 2. Current month completion (September 2026) for Alex (20 points)
        sep_dt1 = datetime(2026, 9, 5, 10, 0, tzinfo=ZoneInfo("Europe/Berlin"))
        Completion.objects.create(
            member=self.alex,
            chore=self.trash_chore,
            completed_at=sep_dt1,
            awarded_points=20,
            chore_name_snapshot="Trash",
            completed_version=0,
        )

        # 3. Current month completion for inactive chore for Alex (50 points)
        self.trash_chore.is_active = False
        self.trash_chore.save()
        sep_dt2 = datetime(2026, 9, 10, 14, 0, tzinfo=ZoneInfo("Europe/Berlin"))
        Completion.objects.create(
            member=self.alex,
            chore=self.trash_chore,
            completed_at=sep_dt2,
            awarded_points=50,
            chore_name_snapshot="Trash (old)",
            completed_version=1,
        )

        # Evaluate at mid September 2026
        eval_time = datetime(2026, 9, 15, 12, 0, tzinfo=ZoneInfo("Europe/Berlin"))
        alex_score = get_member_scores(self.alex, eval_time)

        # Alex monthly points in September: 20 + 50 = 70 (August completion excluded)
        self.assertEqual(alex_score.monthly_points, 70)
        # Alex lifetime XP: 10 + 20 + 50 = 80 (includes August and inactive chore)
        self.assertEqual(alex_score.lifetime_xp, 80)
        # 80 XP -> Sprout (threshold 75)
        self.assertEqual(alex_score.garden_stage.label, "Sprout")

        # Sam and Jamie have 0
        sam_score = get_member_scores(self.sam, eval_time)
        self.assertEqual(sam_score.monthly_points, 0)
        self.assertEqual(sam_score.lifetime_xp, 0)

        # Test get_household_scores ordering
        label, scores = get_household_scores(eval_time)
        self.assertEqual(label, "September 2026")
        self.assertEqual([s.member.name for s in scores], ["Alex", "Sam", "Jamie"])
        self.assertEqual(scores[0].monthly_points, 70)
        self.assertEqual(scores[0].lifetime_xp, 80)


class HouseholdScoreViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.alex = Member.objects.create(name="Alex", display_order=1)
        self.sam = Member.objects.create(name="Sam", display_order=2)

        self.chore = Chore.objects.create(
            name="Vacuum",
            frequency_days=3,
            points=15,
            next_due_date=date(2026, 9, 6),
            is_active=True,
            completion_version=0,
        )

    def test_home_page_displays_scores_and_month_label(self):
        mock_now = datetime(2026, 9, 6, 12, 0, tzinfo=datetime_timezone.utc)
        with patch("household.scores.timezone.now", return_value=mock_now):
            response = self.client.get(reverse("household:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Household scores — September 2026")
        self.assertContains(response, "Alex")
        self.assertContains(response, "0 points")
        self.assertContains(response, "0 XP")
        self.assertContains(response, "Empty soil")

    def test_completing_chore_updates_scores_on_redirect(self):
        mock_now = datetime(2026, 9, 6, 12, 0, tzinfo=datetime_timezone.utc)
        complete_url = reverse("household:chore_complete", args=[self.chore.pk])

        with patch("household.scores.timezone.now", return_value=mock_now), \
             patch("household.completion.timezone.now", return_value=mock_now):
            response = self.client.post(
                complete_url,
                {"member": self.alex.pk, "completion_version": 0},
                follow=True,
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Household scores — September 2026")
        # Alex earned 15 points
        self.assertContains(response, "15 points")
        self.assertContains(response, "15 XP")
