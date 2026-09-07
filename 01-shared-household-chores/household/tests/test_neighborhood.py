"""Focused coverage for the public neighborhood garden page."""

from datetime import date, datetime, timezone as datetime_timezone
from unittest.mock import patch

from django.test import TestCase
from django.urls import resolve, reverse

from household.garden import GARDEN_STAGES
from household.models import Chore, Completion, Member


class NeighborhoodViewTests(TestCase):
    def setUp(self):
        self.alex = Member.objects.create(name="Alex", display_order=2)
        self.sam = Member.objects.create(name="Sam", display_order=1)
        self.jo = Member.objects.create(name="Jo", display_order=3)
        self.chore = Chore.objects.create(
            name="Kitchen cleanup",
            frequency_days=7,
            points=25,
            next_due_date=date(2026, 9, 6),
        )

    def url(self):
        return reverse("household:neighborhood")

    def completion(self, *, member, points, completed_at, version=0, chore=None):
        return Completion.objects.create(
            member=member,
            chore=chore or self.chore,
            awarded_points=points,
            completed_at=completed_at,
            chore_name_snapshot="Kitchen cleanup",
            completed_version=version,
        )

    def award_total(self, *, member, total, completed_at):
        """Create valid completion records that sum to a stage threshold."""

        for index, points in enumerate(range(total, 0, -100)):
            award = min(points, 100)
            chore = self.chore if index == 0 else Chore.objects.create(
                name=f"Threshold chore {total}-{index}",
                frequency_days=7,
                points=award,
                next_due_date=date(2026, 9, 6),
            )
            self.completion(member=member, points=award, completed_at=completed_at, chore=chore)

    def test_route_heading_shared_layout_order_and_member_links(self):
        response = self.client.get(self.url())
        content = response.content.decode()

        self.assertEqual(resolve(self.url()).view_name, "household:neighborhood")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "household/neighborhood.html")
        self.assertContains(response, "<h1>Neighborhood gardens</h1>", html=True)
        self.assertEqual(response.content.count(b'<figure class="garden-visual">'), 3)
        self.assertEqual([score.member for score in response.context["member_scores"]], [self.sam, self.alex, self.jo])
        self.assertLess(content.index("Sam's garden"), content.index("Alex's garden"))
        self.assertLess(content.index("Alex's garden"), content.index("Jo's garden"))

        for member in (self.sam, self.alex, self.jo):
            detail_url = reverse("household:member_detail", args=[member.pk])
            self.assertContains(
                response,
                f'<a class="neighborhood-garden__link" href="{detail_url}">{member.name}</a>',
            )
            self.assertContains(self.client.get(detail_url), f"<h1>{member.name}</h1>", html=True)

    def test_zero_completion_member_has_empty_soil_on_both_pages(self):
        neighborhood = self.client.get(self.url())
        detail = self.client.get(reverse("household:member_detail", args=[self.sam.pk]))

        for response in (neighborhood, detail):
            self.assertContains(response, "Sam's garden \u2014 Empty soil")

    def test_threshold_crossing_uses_same_stage_on_member_and_neighborhood_pages(self):
        at = datetime(2026, 9, 12, 12, 0, tzinfo=datetime_timezone.utc)
        self.completion(member=self.alex, points=24, completed_at=at)

        with patch("household.scores.timezone.now", return_value=at):
            before_detail = self.client.get(reverse("household:member_detail", args=[self.alex.pk]))
            before_neighborhood = self.client.get(self.url())
        self.assertContains(before_detail, "Alex's garden \u2014 Empty soil")
        self.assertContains(before_neighborhood, "Alex's garden \u2014 Empty soil")

        threshold_chore = Chore.objects.create(
            name="Bathroom cleanup",
            frequency_days=7,
            points=1,
            next_due_date=date(2026, 9, 6),
        )
        self.completion(
            member=self.alex,
            points=1,
            completed_at=at,
            chore=threshold_chore,
        )

        with patch("household.scores.timezone.now", return_value=at):
            after_detail = self.client.get(reverse("household:member_detail", args=[self.alex.pk]))
            after_neighborhood = self.client.get(self.url())
        self.assertContains(after_detail, "Alex's garden \u2014 Seed")
        self.assertContains(after_neighborhood, "Alex's garden \u2014 Seed")

    def test_inactive_chore_history_and_month_boundaries_do_not_reset_lifetime_garden(self):
        august = datetime(2026, 8, 31, 12, 0, tzinfo=datetime_timezone.utc)
        self.completion(member=self.alex, points=75, completed_at=august)
        self.chore.is_active = False
        self.chore.save(update_fields=["is_active"])

        october = datetime(2026, 10, 1, 12, 0, tzinfo=datetime_timezone.utc)
        with patch("household.scores.timezone.now", return_value=october):
            neighborhood = self.client.get(self.url())
            detail = self.client.get(reverse("household:member_detail", args=[self.alex.pk]))

        for response in (neighborhood, detail):
            self.assertContains(response, "Alex's garden \u2014 Sprout")
        self.assertContains(detail, "0 points")
        self.assertContains(detail, "75 XP")

    def test_all_configured_stage_labels_render_consistently(self):
        at = datetime(2026, 9, 12, 12, 0, tzinfo=datetime_timezone.utc)
        for stage in GARDEN_STAGES:
            with self.subTest(stage=stage.identifier):
                Completion.objects.all().delete()
                if stage.threshold:
                    self.award_total(member=self.alex, total=stage.threshold, completed_at=at)
                with patch("household.scores.timezone.now", return_value=at):
                    neighborhood = self.client.get(self.url())
                    detail = self.client.get(reverse("household:member_detail", args=[self.alex.pk]))
                expected = f"Alex's garden \u2014 {stage.label}"
                self.assertContains(neighborhood, expected)
                self.assertContains(detail, expected)

    def test_shared_navigation_keeps_both_destinations_linked_and_marks_current_page(self):
        household = self.client.get(reverse("household:home"))
        member = self.client.get(reverse("household:member_detail", args=[self.alex.pk]))
        neighborhood = self.client.get(self.url())

        household_url = reverse("household:home")
        neighborhood_url = self.url()
        for response in (household, member, neighborhood):
            self.assertContains(response, f'<a href="{household_url}"')
            self.assertContains(response, f'<a href="{neighborhood_url}"')
        self.assertContains(household, f'<a href="{household_url}" aria-current="page">Household</a>')
        self.assertContains(member, f'<a href="{household_url}" aria-current="page">Household</a>')
        self.assertContains(neighborhood, f'<a href="{neighborhood_url}" aria-current="page">Neighborhood</a>')
