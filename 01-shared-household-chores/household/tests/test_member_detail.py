"""Regression coverage for the public, read-only member detail page."""

from datetime import date, datetime, timezone as datetime_timezone
from unittest.mock import patch

from django.test import TestCase
from django.urls import resolve, reverse

from household.models import Chore, Completion, Member


class MemberDetailViewTests(TestCase):
    def setUp(self):
        self.member = Member.objects.create(name="Alex", display_order=1)
        self.other_member = Member.objects.create(name="Sam", display_order=2)
        self.chore = Chore.objects.create(
            name="Kitchen cleanup",
            frequency_days=7,
            points=10,
            next_due_date=date(2026, 9, 6),
        )

    def detail_url(self, member=None):
        return reverse("household:member_detail", args=[(member or self.member).pk])

    def completion(self, *, member=None, chore=None, completed_at, points, snapshot, version):
        return Completion.objects.create(
            member=member or self.member,
            chore=chore or self.chore,
            completed_at=completed_at,
            awarded_points=points,
            chore_name_snapshot=snapshot,
            completed_version=version,
        )

    def test_route_resolves_and_anonymous_get_renders_shared_layout_and_navigation(self):
        url = self.detail_url()

        self.assertEqual(resolve(url).view_name, "household:member_detail")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "household/member_detail.html")
        self.assertTemplateUsed(response, "household/base.html")
        self.assertContains(response, '<link rel="stylesheet" href="/static/household/site.css">')
        self.assertContains(response, '<h1>Alex</h1>', html=True)
        self.assertEqual(response.content.count(b"<h1"), 1)
        self.assertContains(
            response,
            f'<a href="{reverse("household:home")}" class="back-link">',
        )
        self.assertContains(response, "Back to household")

    def test_unknown_member_returns_404(self):
        response = self.client.get(reverse("household:member_detail", args=[9999]))

        self.assertEqual(response.status_code, 404)

    def test_zero_completion_summary_uses_shared_score_labels(self):
        response = self.client.get(self.detail_url())

        self.assertContains(response, "Monthly points")
        self.assertContains(response, "0 points")
        self.assertContains(response, "Lifetime XP")
        self.assertContains(response, "0 XP")
        self.assertContains(response, "Garden stage")
        self.assertContains(response, "Empty soil")

    def test_member_page_renders_one_reusable_personal_garden(self):
        response = self.client.get(self.detail_url())

        self.assertContains(response, "<h2 id=\"garden-heading\">Alex's garden</h2>", html=True)
        self.assertEqual(response.content.count(b'<figure class="garden-visual">'), 1)
        self.assertContains(response, "Alex's garden \u2014 Empty soil")

    def test_summary_uses_berlin_month_points_lifetime_xp_and_garden_stage(self):
        september = datetime(2026, 9, 12, 12, 0, tzinfo=datetime_timezone.utc)
        august = datetime(2026, 8, 31, 12, 0, tzinfo=datetime_timezone.utc)
        self.completion(
            completed_at=september,
            points=25,
            snapshot="September snapshot",
            version=0,
        )
        self.completion(
            completed_at=august,
            points=50,
            snapshot="August snapshot",
            version=1,
        )

        with patch("household.scores.timezone.now", return_value=september):
            response = self.client.get(self.detail_url())

        self.assertContains(response, "25 points")
        self.assertContains(response, "75 XP")
        self.assertContains(response, "Sprout")

    def test_history_is_member_owned_newest_first_and_breaks_timestamp_ties_by_pk(self):
        oldest = self.completion(
            completed_at=datetime(2026, 9, 1, 10, 0, tzinfo=datetime_timezone.utc),
            points=10,
            snapshot="Oldest snapshot",
            version=0,
        )
        tied_at = datetime(2026, 9, 2, 10, 0, tzinfo=datetime_timezone.utc)
        tie_first = self.completion(
            completed_at=tied_at,
            points=11,
            snapshot="First tie snapshot",
            version=1,
        )
        tie_second = self.completion(
            completed_at=tied_at,
            points=12,
            snapshot="Second tie snapshot",
            version=2,
        )
        newest = self.completion(
            completed_at=datetime(2026, 9, 3, 10, 0, tzinfo=datetime_timezone.utc),
            points=13,
            snapshot="Newest snapshot",
            version=3,
        )
        other_chore = Chore.objects.create(
            name="Other chore",
            frequency_days=3,
            points=5,
            next_due_date=date(2026, 9, 6),
        )
        self.completion(
            member=self.other_member,
            chore=other_chore,
            completed_at=datetime(2026, 9, 4, 10, 0, tzinfo=datetime_timezone.utc),
            points=5,
            snapshot="Other member snapshot",
            version=0,
        )

        response = self.client.get(self.detail_url())
        content = response.content.decode()

        self.assertContains(response, '<h2 id="history-heading">Completion history</h2>', html=True)
        self.assertContains(response, '<table class="history-table">')
        for header in ("Chore", "Date", "Points"):
            self.assertContains(response, header)
        self.assertNotContains(response, "Other member snapshot")
        self.assertEqual(
            list(response.context["completions"]),
            [newest, tie_second, tie_first, oldest],
        )
        self.assertLess(content.index("Newest snapshot"), content.index("Second tie snapshot"))
        self.assertLess(content.index("Second tie snapshot"), content.index("First tie snapshot"))
        self.assertLess(content.index("First tie snapshot"), content.index("Oldest snapshot"))

    def test_history_renders_stored_snapshot_award_and_europe_berlin_date(self):
        # 23:30 UTC on New Year's Eve is 00:30 on 1 January in Berlin.
        completion = self.completion(
            completed_at=datetime(2026, 12, 31, 23, 30, tzinfo=datetime_timezone.utc),
            points=37,
            snapshot="Original chore title",
            version=0,
        )
        self.chore.name = "Renamed chore"
        self.chore.save()

        response = self.client.get(self.detail_url())

        self.assertContains(response, completion.chore_name_snapshot)
        self.assertContains(response, "37 pts")
        self.assertContains(response, "2027-01-01")
        self.assertNotContains(response, "Renamed chore")

    def test_inactive_chore_completion_remains_visible_and_contributes_to_totals(self):
        self.completion(
            completed_at=datetime(2026, 9, 6, 12, 0, tzinfo=datetime_timezone.utc),
            points=30,
            snapshot="Deleted chore snapshot",
            version=0,
        )
        self.chore.is_active = False
        self.chore.save(update_fields=["is_active"])

        with patch(
            "household.scores.timezone.now",
            return_value=datetime(2026, 9, 15, 12, 0, tzinfo=datetime_timezone.utc),
        ):
            response = self.client.get(self.detail_url())

        self.assertContains(response, "Deleted chore snapshot")
        self.assertContains(response, "30 pts")
        self.assertContains(response, "30 points")
        self.assertContains(response, "30 XP")

    def test_empty_history_has_clear_message_without_table(self):
        response = self.client.get(self.detail_url())

        self.assertContains(response, "No completions recorded yet.")
        self.assertNotContains(response, '<table class="history-table">')

    def test_home_links_every_member_card_to_its_detail_page(self):
        response = self.client.get(reverse("household:home"))

        for member in (self.member, self.other_member):
            url = self.detail_url(member)
            self.assertContains(
                response,
                f'<a href="{url}" class="member-detail-link">{member.name}</a>',
            )

    def test_detail_page_is_read_only_and_post_does_not_modify_data(self):
        completion_count = Completion.objects.count()
        member_count = Member.objects.count()
        response = self.client.post(self.detail_url(), {"name": "Changed"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Completion.objects.count(), completion_count)
        self.assertEqual(Member.objects.count(), member_count)
        self.member.refresh_from_db()
        self.assertEqual(self.member.name, "Alex")
        self.assertNotContains(response, "<form")
        self.assertNotContains(response, "Complete")
        self.assertNotContains(response, "Edit")
