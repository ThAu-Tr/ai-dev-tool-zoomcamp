"""Tests for member selection and completion controls view."""

from datetime import date, datetime, timezone as datetime_timezone
from unittest.mock import patch

from django.contrib.messages import get_messages
from django.test import Client, TestCase
from django.urls import reverse

from household.models import Chore, Completion, Member


class ChoreCompleteViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.csrf_client = Client(enforce_csrf_checks=True)

        self.alex = Member.objects.create(name="Alex", display_order=1)
        self.sam = Member.objects.create(name="Sam", display_order=2)
        self.jamie = Member.objects.create(name="Jamie", display_order=3)

        # Due chore
        self.due_chore = Chore.objects.create(
            name="Wash dishes",
            frequency_days=1,
            points=5,
            next_due_date=date(2026, 9, 6),
            is_active=True,
            completion_version=0,
        )

        # Future chore (not yet due)
        self.future_chore = Chore.objects.create(
            name="Clean windows",
            frequency_days=30,
            points=25,
            next_due_date=date(2026, 9, 20),
            is_active=True,
            completion_version=0,
        )

    def test_home_page_renders_completion_form_for_eligible_chore(self):
        # Local date 2026-09-06
        mock_now = datetime(2026, 9, 6, 12, 0, tzinfo=datetime_timezone.utc)
        with patch("household.scheduling.timezone.now", return_value=mock_now):
            response = self.client.get(reverse("household:home"))

        self.assertEqual(response.status_code, 200)

        # Check form for due chore
        form_action = reverse("household:chore_complete", args=[self.due_chore.pk])
        self.assertContains(response, f'action="{form_action}"')
        self.assertContains(response, 'name="completion_version" value="0"')
        self.assertContains(response, f'<label for="id_member_{self.due_chore.pk}">Completed by</label>')
        self.assertContains(response, f'<select name="member" id="id_member_{self.due_chore.pk}"')
        self.assertContains(response, f'<option value="{self.alex.pk}">Alex</option>')
        self.assertContains(response, f'<option value="{self.sam.pk}">Sam</option>')
        self.assertContains(response, f'<option value="{self.jamie.pk}">Jamie</option>')
        self.assertContains(response, '<button type="submit" class="btn btn--primary">Complete</button>')

    def test_home_page_shows_not_due_notice_for_ineligible_chore(self):
        mock_now = datetime(2026, 9, 6, 12, 0, tzinfo=datetime_timezone.utc)
        with patch("household.scheduling.timezone.now", return_value=mock_now):
            response = self.client.get(reverse("household:home"))

        self.assertEqual(response.status_code, 200)
        future_action = reverse("household:chore_complete", args=[self.future_chore.pk])
        self.assertNotContains(response, f'action="{future_action}"')
        self.assertContains(response, "Not eligible for completion until 2026-09-20.")

    def test_chore_complete_get_redirects_to_home(self):
        url = reverse("household:chore_complete", args=[self.due_chore.pk])
        response = self.client.get(url)
        self.assertRedirects(response, reverse("household:home"))

    def test_chore_complete_post_enforces_csrf(self):
        url = reverse("household:chore_complete", args=[self.due_chore.pk])
        response = self.csrf_client.post(
            url,
            {"member": self.alex.pk, "completion_version": 0},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Completion.objects.count(), 0)

    def test_chore_complete_missing_member_redirects_with_error(self):
        url = reverse("household:chore_complete", args=[self.due_chore.pk])
        response = self.client.post(
            url,
            {"member": "", "completion_version": 0},
            follow=True,
        )
        self.assertRedirects(response, reverse("household:home"))
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].message, "Please select a household member.")
        self.assertEqual(Completion.objects.count(), 0)

    def test_chore_complete_invalid_version_redirects_with_error(self):
        url = reverse("household:chore_complete", args=[self.due_chore.pk])
        response = self.client.post(
            url,
            {"member": self.alex.pk, "completion_version": "invalid"},
            follow=True,
        )
        self.assertRedirects(response, reverse("household:home"))
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].message, "Invalid submission.")
        self.assertEqual(Completion.objects.count(), 0)

    def test_chore_complete_rejects_invalid_member_values_without_mutation(self):
        url = reverse("household:chore_complete", args=[self.due_chore.pk])
        invalid_values = ("", "   ", "invalid", "²", "-1", "1.5")

        for member in invalid_values:
            with self.subTest(member=member):
                response = self.client.post(
                    url,
                    {"member": member, "completion_version": 0},
                    follow=True,
                )

                self.assertRedirects(response, reverse("household:home"))
                messages = list(get_messages(response.wsgi_request))
                self.assertEqual(len(messages), 1)
                self.assertEqual(messages[0].message, "Please select a household member.")
                self.assertEqual(Completion.objects.count(), 0)
                self.assertEqual(self.due_chore.completion_version, 0)

    def test_chore_complete_rejects_invalid_version_values_without_mutation(self):
        url = reverse("household:chore_complete", args=[self.due_chore.pk])
        invalid_values = ("", "   ", "invalid", "²", "-1", "1.5")

        for version in invalid_values:
            with self.subTest(version=version):
                response = self.client.post(
                    url,
                    {"member": self.alex.pk, "completion_version": version},
                    follow=True,
                )

                self.assertRedirects(response, reverse("household:home"))
                messages = list(get_messages(response.wsgi_request))
                self.assertEqual(len(messages), 1)
                self.assertEqual(messages[0].message, "Invalid submission.")
                self.assertEqual(Completion.objects.count(), 0)
                self.assertEqual(self.due_chore.completion_version, 0)

    def test_chore_complete_success_flow(self):
        mock_now = datetime(2026, 9, 6, 12, 0, tzinfo=datetime_timezone.utc)
        url = reverse("household:chore_complete", args=[self.due_chore.pk])

        with patch("household.completion.timezone.now", return_value=mock_now):
            response = self.client.post(
                url,
                {"member": self.alex.pk, "completion_version": 0},
                follow=True,
            )

        self.assertRedirects(response, reverse("household:home"))
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].message, 'Completed "Wash dishes" for Alex.')

        self.due_chore.refresh_from_db()
        self.assertEqual(self.due_chore.completion_version, 1)
        self.assertEqual(self.due_chore.next_due_date, date(2026, 9, 7))

        completions = Completion.objects.filter(chore=self.due_chore)
        self.assertEqual(completions.count(), 1)
        completion = completions.first()
        self.assertEqual(completion.member, self.alex)
        self.assertEqual(completion.awarded_points, 5)
        self.assertEqual(completion.chore_name_snapshot, "Wash dishes")

    def test_chore_complete_stale_resubmission_warns_and_prevents_duplicates(self):
        url = reverse("household:chore_complete", args=[self.due_chore.pk])
        # First successful completion (consume redirect and messages)
        first_resp = self.client.post(
            url,
            {"member": self.alex.pk, "completion_version": 0},
            follow=True,
        )
        self.assertEqual(Completion.objects.count(), 1)

        # Second submission with the same old version 0
        response = self.client.post(
            url,
            {"member": self.sam.pk, "completion_version": 0},
            follow=True,
        )

        self.assertRedirects(response, reverse("household:home"))
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn("already been completed", messages[0].message)

        # No duplicate completion created
        self.assertEqual(Completion.objects.count(), 1)

    def test_chore_complete_ineligible_chore_rejected(self):
        url = reverse("household:chore_complete", args=[self.future_chore.pk])
        response = self.client.post(
            url,
            {"member": self.alex.pk, "completion_version": 0},
            follow=True,
        )

        self.assertRedirects(response, reverse("household:home"))
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].message, "Chore is not yet due.")
        self.assertEqual(Completion.objects.count(), 0)

    def test_chore_complete_inactive_chore_rejected(self):
        self.due_chore.is_active = False
        self.due_chore.save()

        url = reverse("household:chore_complete", args=[self.due_chore.pk])
        response = self.client.post(
            url,
            {"member": self.alex.pk, "completion_version": 0},
            follow=True,
        )

        self.assertRedirects(response, reverse("household:home"))
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].message, "Chore is no longer active.")
        self.assertEqual(Completion.objects.count(), 0)
