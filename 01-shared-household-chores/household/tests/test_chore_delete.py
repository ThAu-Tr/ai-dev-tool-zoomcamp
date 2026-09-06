"""Tests for chore deletion with history preservation."""

from datetime import date, timezone as datetime_timezone, datetime

from django.contrib.messages import get_messages
from django.test import Client, TestCase
from django.urls import reverse

from household.models import Chore, Completion, Member


class ChoreDeleteTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.csrf_client = Client(enforce_csrf_checks=True)
        self.member = Member.objects.create(name="Alex", display_order=1)
        self.chore = Chore.objects.create(
            name="Vacuum rugs",
            frequency_days=7,
            points=10,
            next_due_date=date(2026, 9, 15),
            is_active=True,
            completion_version=2,
        )

    def test_chore_delete_get_renders_confirmation_page_with_chore_name(self):
        url = reverse("household:chore_delete", args=[self.chore.pk])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "household/chore_confirm_delete.html")
        self.assertTemplateUsed(response, "household/base.html")
        self.assertContains(response, "Vacuum rugs")
        self.assertContains(response, reverse("household:home"))
        self.assertContains(response, "Delete chore")
        self.assertContains(response, "Cancel")

    def test_chore_delete_get_makes_no_database_modifications(self):
        url = reverse("household:chore_delete", args=[self.chore.pk])
        self.client.get(url)

        self.chore.refresh_from_db()
        self.assertTrue(self.chore.is_active)

    def test_chore_delete_get_returns_404_for_inactive_chore(self):
        self.chore.is_active = False
        self.chore.save()

        url = reverse("household:chore_delete", args=[self.chore.pk])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_chore_delete_get_returns_404_for_nonexistent_chore(self):
        url = reverse("household:chore_delete", args=[9999])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_chore_delete_post_requires_csrf_protection(self):
        url = reverse("household:chore_delete", args=[self.chore.pk])
        response = self.csrf_client.post(url)

        self.assertEqual(response.status_code, 403)
        self.chore.refresh_from_db()
        self.assertTrue(self.chore.is_active)

    def test_chore_delete_post_marks_chore_inactive_and_redirects(self):
        url = reverse("household:chore_delete", args=[self.chore.pk])
        response = self.client.post(url)

        self.assertRedirects(response, reverse("household:home"))
        self.chore.refresh_from_db()
        self.assertFalse(self.chore.is_active)

        # Verify flash message
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].message, 'Chore "Vacuum rugs" deleted.')

    def test_deleted_chore_does_not_appear_on_household_home(self):
        url = reverse("household:chore_delete", args=[self.chore.pk])
        response = self.client.post(url, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(self.chore, [display.chore for display in response.context["active_chores"]])
        self.assertNotContains(response, f"<h3>{self.chore.name}</h3>")

    def test_chore_delete_preserves_all_completion_records(self):
        completion1 = Completion.objects.create(
            member=self.member,
            chore=self.chore,
            completed_at=datetime(2026, 9, 1, 10, 0, tzinfo=datetime_timezone.utc),
            awarded_points=10,
            chore_name_snapshot="Vacuum rugs",
            completed_version=0,
        )
        completion2 = Completion.objects.create(
            member=self.member,
            chore=self.chore,
            completed_at=datetime(2026, 9, 8, 10, 0, tzinfo=datetime_timezone.utc),
            awarded_points=10,
            chore_name_snapshot="Vacuum rugs",
            completed_version=1,
        )

        url = reverse("household:chore_delete", args=[self.chore.pk])
        self.client.post(url)

        # Check completions still exist and are untouched
        self.assertEqual(Completion.objects.filter(chore=self.chore).count(), 2)
        completion1.refresh_from_db()
        completion2.refresh_from_db()
        self.assertEqual(completion1.awarded_points, 10)
        self.assertEqual(completion2.awarded_points, 10)
        self.assertEqual(completion1.chore_name_snapshot, "Vacuum rugs")

    def test_chore_delete_repeated_post_returns_404(self):
        url = reverse("household:chore_delete", args=[self.chore.pk])
        # First deletion
        self.client.post(url)

        # Second deletion attempt
        response = self.client.post(url)
        self.assertEqual(response.status_code, 404)

    def test_name_can_be_reused_after_chore_is_deleted(self):
        url = reverse("household:chore_delete", args=[self.chore.pk])
        self.client.post(url)

        # Re-creating a chore with the same name should succeed
        create_url = reverse("household:chore_create")
        response = self.client.post(
            create_url,
            {
                "name": "Vacuum rugs",
                "frequency_days": 14,
                "points": 15,
                "next_due_date": "2026-09-20",
            },
        )
        self.assertRedirects(response, reverse("household:home"))
        self.assertTrue(
            Chore.objects.filter(name="Vacuum rugs", is_active=True).exists()
        )
        self.assertTrue(
            Chore.objects.filter(name="Vacuum rugs", is_active=False).exists()
        )

    def test_delete_link_present_on_chore_edit_page(self):
        edit_url = reverse("household:chore_edit", args=[self.chore.pk])
        response = self.client.get(edit_url)

        self.assertEqual(response.status_code, 200)
        delete_url = reverse("household:chore_delete", args=[self.chore.pk])
        self.assertContains(response, delete_url)
        self.assertContains(response, "Delete chore")

    def test_delete_link_present_on_home_page(self):
        home_response = self.client.get(reverse("household:home"))
        self.assertEqual(home_response.status_code, 200)
        delete_url = reverse("household:chore_delete", args=[self.chore.pk])
        self.assertContains(home_response, delete_url)
