"""End-to-end public household journey coverage."""

from datetime import date, datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import resolve, reverse

from household.models import Chore, Completion, Member


BERLIN = ZoneInfo("Europe/Berlin")
FROZEN_NOW = datetime(2026, 9, 6, 10, 30, tzinfo=BERLIN)


@override_settings(TIME_ZONE="Europe/Berlin", USE_TZ=True)
class HouseholdJourneyTests(TestCase):
    """Exercise the public workflow while preserving contribution history."""

    def setUp(self):
        call_command("setup_members", verbosity=0)
        self.alex = Member.objects.get(name="Alex")

    def assert_scores_and_seed_garden(self, *, chore_name):
        """Assert one completed 25-point chore is rendered consistently everywhere."""

        household_url = reverse("household:home")
        member_url = reverse("household:member_detail", args=[self.alex.pk])
        neighborhood_url = reverse("household:neighborhood")

        self.assertEqual(resolve(household_url).view_name, "household:home")
        self.assertEqual(resolve(member_url).view_name, "household:member_detail")
        self.assertEqual(resolve(neighborhood_url).view_name, "household:neighborhood")

        household = self.client.get(household_url)
        member = self.client.get(member_url)
        neighborhood = self.client.get(neighborhood_url)

        self.assertEqual(household.status_code, 200)
        self.assertContains(household, "Household scores — September 2026")
        household_score = next(
            score
            for score in household.context["member_scores"]
            if score.member == self.alex
        )
        self.assertEqual(household_score.monthly_points, 25)
        self.assertEqual(household_score.lifetime_xp, 25)
        self.assertEqual(household_score.garden_stage.label, "Seed")
        self.assertContains(household, "25 points")
        self.assertContains(household, "25 XP")
        self.assertContains(household, "Seed")

        self.assertEqual(member.status_code, 200)
        self.assertContains(member, "25 points")
        self.assertContains(member, "25 XP")
        self.assertContains(member, "Alex's garden — Seed")
        self.assertContains(member, chore_name)
        self.assertContains(member, "25 pts")

        self.assertEqual(neighborhood.status_code, 200)
        self.assertContains(neighborhood, "Alex's garden — Seed")

        return household, member, neighborhood

    @patch("django.utils.timezone.now", return_value=FROZEN_NOW)
    def test_predefined_member_keeps_contribution_after_create_complete_edit_and_delete(self, _now):
        call_command("setup_members", verbosity=0)
        self.assertEqual(
            list(Member.objects.values_list("name", "display_order")),
            [("Alex", 1), ("Sam", 2), ("Jamie", 3)],
        )

        create_url = reverse("household:chore_create")
        self.assertEqual(resolve(create_url).view_name, "household:chore_create")
        creation = self.client.post(
            create_url,
            {
                "name": "Polish kitchen table",
                "frequency_days": 7,
                "points": 25,
                "next_due_date": "2026-09-06",
            },
        )
        home_url = reverse("household:home")
        self.assertRedirects(creation, home_url)

        chore = Chore.objects.get(name="Polish kitchen table")
        self.assertEqual(chore.next_due_date, date(2026, 9, 6))
        self.assertEqual(chore.completion_version, 0)
        household_after_create = self.client.get(home_url)
        self.assertContains(household_after_create, "Polish kitchen table")
        self.assertContains(household_after_create, "Due")
        self.assertContains(household_after_create, "2026-09-06")
        self.assertContains(
            household_after_create,
            reverse("household:chore_complete", args=[chore.pk]),
        )
        self.assertContains(
            household_after_create,
            f'<option value="{self.alex.pk}">Alex</option>',
        )

        complete_url = reverse("household:chore_complete", args=[chore.pk])
        self.assertEqual(resolve(complete_url).view_name, "household:chore_complete")
        completion_response = self.client.post(
            complete_url,
            {"member": self.alex.pk, "completion_version": 0},
        )
        self.assertRedirects(completion_response, home_url)

        chore.refresh_from_db()
        completion = Completion.objects.get(chore=chore)
        self.assertEqual(chore.completion_version, 1)
        self.assertEqual(chore.next_due_date, date(2026, 9, 13))
        self.assertEqual(completion.member, self.alex)
        self.assertEqual(completion.completed_at, FROZEN_NOW)
        self.assertEqual(completion.awarded_points, 25)
        self.assertEqual(completion.chore_name_snapshot, "Polish kitchen table")
        self.assertEqual(completion.completed_version, 0)
        self.assert_scores_and_seed_garden(chore_name="Polish kitchen table")

        edit_url = reverse("household:chore_edit", args=[chore.pk])
        self.assertEqual(resolve(edit_url).view_name, "household:chore_edit")
        edit_response = self.client.post(
            edit_url,
            {
                "name": "Polish dining table",
                "frequency_days": 14,
                "points": 40,
                "next_due_date": "2026-09-13",
            },
        )
        self.assertRedirects(edit_response, home_url)

        chore.refresh_from_db()
        completion.refresh_from_db()
        self.assertEqual(chore.name, "Polish dining table")
        self.assertEqual(chore.frequency_days, 14)
        self.assertEqual(chore.points, 40)
        self.assertEqual(chore.next_due_date, date(2026, 9, 13))
        self.assertEqual(chore.completion_version, 1)
        self.assertEqual(completion.awarded_points, 25)
        self.assertEqual(completion.chore_name_snapshot, "Polish kitchen table")
        self.assertEqual(completion.completed_version, 0)
        self.assertEqual(completion.completed_at, FROZEN_NOW)
        self.assert_scores_and_seed_garden(chore_name="Polish kitchen table")

        delete_url = reverse("household:chore_delete", args=[chore.pk])
        self.assertEqual(resolve(delete_url).view_name, "household:chore_delete")
        delete_response = self.client.post(delete_url)
        self.assertRedirects(delete_response, home_url)

        chore.refresh_from_db()
        completion.refresh_from_db()
        self.assertFalse(chore.is_active)
        self.assertEqual(Completion.objects.filter(chore=chore).count(), 1)
        self.assertEqual(completion.awarded_points, 25)
        self.assertEqual(completion.chore_name_snapshot, "Polish kitchen table")
        household, member, _neighborhood = self.assert_scores_and_seed_garden(
            chore_name="Polish kitchen table"
        )
        self.assertNotContains(household, "Polish dining table")
        self.assertNotContains(household, "Polish kitchen table")
        self.assertContains(member, "Polish kitchen table")

