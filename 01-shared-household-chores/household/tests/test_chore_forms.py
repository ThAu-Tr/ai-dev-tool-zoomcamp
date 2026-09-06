"""Tests for chore creation and editing forms and views."""

from datetime import date, datetime, timezone as datetime_timezone
from unittest.mock import patch

from django.contrib.messages import get_messages
from django.test import Client, TestCase
from django.urls import reverse

from household.forms import ChoreForm
from household.models import Chore, Completion, Member


class ChoreFormViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.csrf_client = Client(enforce_csrf_checks=True)

    def test_chore_create_get_renders_form_with_layout_and_fields(self):
        response = self.client.get(reverse("household:chore_create"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "household/chore_form.html")
        self.assertTemplateUsed(response, "household/base.html")
        self.assertContains(response, '<label for="id_name">Chore name</label>')
        self.assertContains(response, '<label for="id_frequency_days">Frequency in days</label>')
        self.assertContains(response, '<label for="id_points">Points</label>')
        self.assertContains(response, '<label for="id_next_due_date">Next due date</label>')
        self.assertContains(response, '<input type="text" name="name"')
        self.assertContains(response, '<input type="number" name="frequency_days"')
        self.assertContains(response, '<input type="number" name="points"')
        self.assertContains(response, '<input type="date" name="next_due_date"')
        self.assertContains(response, reverse("household:home"))
        self.assertContains(response, "Cancel")

    def test_chore_create_prepopulates_next_due_date_with_berlin_local_date(self):
        # 2026-09-06 23:30 UTC is 2026-09-07 01:30 in Europe/Berlin (UTC+2 DST)
        mock_now = datetime(2026, 9, 6, 23, 30, tzinfo=datetime_timezone.utc)
        with patch("household.scheduling.timezone.now", return_value=mock_now):
            response = self.client.get(reverse("household:chore_create"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="2026-09-07"')

    def test_chore_edit_get_renders_form_prepopulated_with_active_chore_data(self):
        chore = Chore.objects.create(
            name="Dust bookshelves",
            frequency_days=14,
            points=5,
            next_due_date=date(2026, 9, 20),
            is_active=True,
        )

        response = self.client.get(reverse("household:chore_edit", args=[chore.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "household/chore_form.html")
        self.assertTemplateUsed(response, "household/base.html")
        self.assertContains(response, 'value="Dust bookshelves"')
        self.assertContains(response, 'value="14"')
        self.assertContains(response, 'value="5"')
        self.assertContains(response, 'value="2026-09-20"')
        self.assertContains(response, "Cancel")

    def test_chore_edit_missing_chore_returns_404(self):
        response_get = self.client.get(reverse("household:chore_edit", args=[9999]))
        self.assertEqual(response_get.status_code, 404)

        response_post = self.client.post(
            reverse("household:chore_edit", args=[9999]),
            {"name": "Ghost chore", "frequency_days": 1, "points": 1, "next_due_date": "2026-09-06"},
        )
        self.assertEqual(response_post.status_code, 404)

    def test_chore_edit_inactive_chore_returns_404(self):
        chore = Chore.objects.create(
            name="Archived chore",
            frequency_days=7,
            points=3,
            next_due_date=date(2026, 9, 10),
            is_active=False,
        )

        response_get = self.client.get(reverse("household:chore_edit", args=[chore.pk]))
        self.assertEqual(response_get.status_code, 404)

        response_post = self.client.post(
            reverse("household:chore_edit", args=[chore.pk]),
            {"name": "Archived chore", "frequency_days": 7, "points": 3, "next_due_date": "2026-09-10"},
        )
        self.assertEqual(response_post.status_code, 404)

    def test_pure_get_requests_produce_no_side_effects(self):
        chore = Chore.objects.create(
            name="Stable chore",
            frequency_days=7,
            points=2,
            next_due_date=date(2026, 9, 10),
        )
        initial_chores_count = Chore.objects.count()

        self.client.get(reverse("household:chore_create"))
        self.client.get(reverse("household:chore_edit", args=[chore.pk]))

        self.assertEqual(Chore.objects.count(), initial_chores_count)
        chore.refresh_from_db()
        self.assertEqual(chore.name, "Stable chore")

    def test_csrf_protection_enforced_on_create_and_edit(self):
        response_create = self.csrf_client.post(
            reverse("household:chore_create"),
            {"name": "No CSRF", "frequency_days": 1, "points": 1, "next_due_date": "2026-09-06"},
        )
        self.assertEqual(response_create.status_code, 403)

        chore = Chore.objects.create(
            name="Existing chore",
            frequency_days=7,
            points=2,
            next_due_date=date(2026, 9, 10),
        )
        response_edit = self.csrf_client.post(
            reverse("household:chore_edit", args=[chore.pk]),
            {"name": "Hacked name", "frequency_days": 7, "points": 2, "next_due_date": "2026-09-10"},
        )
        self.assertEqual(response_edit.status_code, 403)
        chore.refresh_from_db()
        self.assertEqual(chore.name, "Existing chore")

    def test_invalid_post_redisplays_form_with_errors_and_preserved_values(self):
        response = self.client.post(
            reverse("household:chore_create"),
            {
                "name": "   ",
                "frequency_days": 500,
                "points": 0,
                "next_due_date": "invalid-date",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "household/chore_form.html")
        self.assertEqual(Chore.objects.count(), 0)
        # Form shows inline errors
        form = response.context["form"]
        self.assertTrue(form.errors.get("name"))
        self.assertTrue(form.errors.get("frequency_days"))
        self.assertTrue(form.errors.get("points"))
        self.assertTrue(form.errors.get("next_due_date"))
        # Preserves user input values
        self.assertContains(response, 'value="500"')
        self.assertContains(response, 'value="0"')
        self.assertContains(response, 'value="invalid-date"')

    def test_name_validation_and_normalization(self):
        # Empty and whitespace-only rejected
        for bad_name in ["", "   ", "\t\n  "]:
            form = ChoreForm(data={"name": bad_name, "frequency_days": 1, "points": 1, "next_due_date": "2026-09-06"})
            self.assertFalse(form.is_valid())
            self.assertIn("name", form.errors)

        # Leading/trailing spaces stripped, internal whitespace collapsed
        form = ChoreForm(
            data={"name": "  Clean   the   kitchen  ", "frequency_days": 1, "points": 1, "next_due_date": "2026-09-06"}
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["name"], "Clean the kitchen")

        # Name exactly 100 characters after normalization is accepted
        exact_100 = "a" * 100
        form_100 = ChoreForm(
            data={"name": f"   {exact_100}   ", "frequency_days": 1, "points": 1, "next_due_date": "2026-09-06"}
        )
        self.assertTrue(form_100.is_valid(), form_100.errors)
        self.assertEqual(form_100.cleaned_data["name"], exact_100)

        # Name exceeding 100 characters after normalization is rejected
        too_long = "a" * 101
        form_too_long = ChoreForm(
            data={"name": too_long, "frequency_days": 1, "points": 1, "next_due_date": "2026-09-06"}
        )
        self.assertFalse(form_too_long.is_valid())
        self.assertIn("name", form_too_long.errors)

        # Raw string > 100 characters that normalizes to <= 100 characters is accepted
        long_with_spaces = "a " * 50  # 100 chars: 50 'a's and 50 spaces -> collapses to "a a a ... a" (99 chars)
        form_normalized_fits = ChoreForm(
            data={"name": f"   {long_with_spaces}   ", "frequency_days": 1, "points": 1, "next_due_date": "2026-09-06"}
        )
        self.assertTrue(form_normalized_fits.is_valid(), form_normalized_fits.errors)

    def test_duplicate_active_name_case_insensitive_rejected_inactive_allowed(self):
        Chore.objects.create(
            name="Vacuum rugs",
            frequency_days=7,
            points=2,
            next_due_date=date(2026, 9, 10),
            is_active=True,
        )
        Chore.objects.create(
            name="Water plants",
            frequency_days=3,
            points=1,
            next_due_date=date(2026, 9, 10),
            is_active=False,
        )

        # Duplicate case variation of active chore is rejected on create
        form_dup_create = ChoreForm(
            data={"name": "vAcUuM RUGS", "frequency_days": 1, "points": 1, "next_due_date": "2026-09-06"}
        )
        self.assertFalse(form_dup_create.is_valid())
        self.assertIn("name", form_dup_create.errors)

        # Inactive chore name can be reused on create
        form_reuse_inactive = ChoreForm(
            data={"name": "WATER PLANTS", "frequency_days": 1, "points": 1, "next_due_date": "2026-09-06"}
        )
        self.assertTrue(form_reuse_inactive.is_valid(), form_reuse_inactive.errors)

        # On edit, conflict with another active chore is rejected
        other_chore = Chore.objects.create(
            name="Mop floor",
            frequency_days=7,
            points=2,
            next_due_date=date(2026, 9, 10),
            is_active=True,
        )
        form_dup_edit = ChoreForm(
            data={"name": "vacuum rugs", "frequency_days": 7, "points": 2, "next_due_date": "2026-09-10"},
            instance=other_chore,
        )
        self.assertFalse(form_dup_edit.is_valid())
        self.assertIn("name", form_dup_edit.errors)

        # On edit, chore can keep its own name (including case variation)
        form_self_name = ChoreForm(
            data={"name": "VACUUM RUGS", "frequency_days": 7, "points": 2, "next_due_date": "2026-09-10"},
            instance=Chore.objects.get(name="Vacuum rugs"),
        )
        self.assertTrue(form_self_name.is_valid(), form_self_name.errors)

        # On edit, reusing an inactive chore name is accepted
        form_edit_reuse_inactive = ChoreForm(
            data={"name": "water plants", "frequency_days": 7, "points": 2, "next_due_date": "2026-09-10"},
            instance=other_chore,
        )
        self.assertTrue(form_edit_reuse_inactive.is_valid(), form_edit_reuse_inactive.errors)

    def test_frequency_validation(self):
        valid_data = {"name": "Test chore", "points": 5, "next_due_date": "2026-09-06"}

        # Boundaries 1 and 365 accepted
        for valid_freq in [1, 365, 30]:
            form = ChoreForm(data={**valid_data, "frequency_days": valid_freq})
            self.assertTrue(form.is_valid(), f"Failed for frequency {valid_freq}")

        # Blank, non-integer, zero, negative, > 365 rejected
        for bad_freq in ["", "abc", 0, -1, 366, 1.5]:
            form = ChoreForm(data={**valid_data, "frequency_days": bad_freq})
            self.assertFalse(form.is_valid(), f"Expected failure for frequency {bad_freq}")
            self.assertIn("frequency_days", form.errors)

    def test_points_validation(self):
        valid_data = {"name": "Test chore", "frequency_days": 7, "next_due_date": "2026-09-06"}

        # Boundaries 1 and 100 accepted
        for valid_point in [1, 100, 50]:
            form = ChoreForm(data={**valid_data, "points": valid_point})
            self.assertTrue(form.is_valid(), f"Failed for points {valid_point}")

        # Blank, non-integer, zero, negative, > 100 rejected
        for bad_point in ["", "xyz", 0, -5, 101, 2.5]:
            form = ChoreForm(data={**valid_data, "points": bad_point})
            self.assertFalse(form.is_valid(), f"Expected failure for points {bad_point}")
            self.assertIn("points", form.errors)

    def test_next_due_date_validation_and_date_ranges(self):
        valid_data = {"name": "Test chore", "frequency_days": 7, "points": 10}

        # Past dates, today, and future dates are all accepted
        for valid_date in ["2020-01-01", "2026-09-06", "2030-12-31"]:
            form = ChoreForm(data={**valid_data, "next_due_date": valid_date})
            self.assertTrue(form.is_valid(), f"Failed for date {valid_date}")

        # Blank and invalid date formats rejected
        for bad_date in ["", "not-a-date", "2026-13-45", "06/09/2026"]:
            form = ChoreForm(data={**valid_data, "next_due_date": bad_date})
            self.assertFalse(form.is_valid(), f"Expected failure for date {bad_date}")
            self.assertIn("next_due_date", form.errors)

    def test_edit_leaves_next_due_date_unchanged_when_not_directly_edited(self):
        original_due = date(2026, 9, 25)
        chore = Chore.objects.create(
            name="Clean windows",
            frequency_days=7,
            points=5,
            next_due_date=original_due,
        )

        # 1. Frequency change leaves due date unchanged
        response_freq = self.client.post(
            reverse("household:chore_edit", args=[chore.pk]),
            {
                "name": chore.name,
                "frequency_days": 14,
                "points": chore.points,
                "next_due_date": "2026-09-25",
            },
        )
        self.assertRedirects(response_freq, reverse("household:home"))
        chore.refresh_from_db()
        self.assertEqual(chore.frequency_days, 14)
        self.assertEqual(chore.next_due_date, original_due)

        # 2. Name-only change leaves due date unchanged
        response_name = self.client.post(
            reverse("household:chore_edit", args=[chore.pk]),
            {
                "name": "Wash windows",
                "frequency_days": 14,
                "points": chore.points,
                "next_due_date": "2026-09-25",
            },
        )
        self.assertRedirects(response_name, reverse("household:home"))
        chore.refresh_from_db()
        self.assertEqual(chore.name, "Wash windows")
        self.assertEqual(chore.next_due_date, original_due)

        # 3. Points-only change leaves due date unchanged
        response_pts = self.client.post(
            reverse("household:chore_edit", args=[chore.pk]),
            {
                "name": chore.name,
                "frequency_days": 14,
                "points": 8,
                "next_due_date": "2026-09-25",
            },
        )
        self.assertRedirects(response_pts, reverse("household:home"))
        chore.refresh_from_db()
        self.assertEqual(chore.points, 8)
        self.assertEqual(chore.next_due_date, original_due)

    def test_edit_direct_next_due_date_update_persists_new_date(self):
        chore = Chore.objects.create(
            name="Scrub bathroom",
            frequency_days=7,
            points=5,
            next_due_date=date(2026, 9, 10),
        )

        response = self.client.post(
            reverse("household:chore_edit", args=[chore.pk]),
            {
                "name": chore.name,
                "frequency_days": chore.frequency_days,
                "points": chore.points,
                "next_due_date": "2026-10-01",
            },
        )
        self.assertRedirects(response, reverse("household:home"))
        chore.refresh_from_db()
        self.assertEqual(chore.next_due_date, date(2026, 10, 1))

    def test_edit_preserves_completion_version_and_completion_records(self):
        member = Member.objects.create(name="Alex", display_order=1)
        chore = Chore.objects.create(
            name="Take out recycling",
            frequency_days=7,
            points=3,
            next_due_date=date(2026, 9, 10),
            completion_version=2,
        )
        completion_time = datetime(2026, 9, 3, 14, 0, tzinfo=datetime_timezone.utc)
        completion = Completion.objects.create(
            member=member,
            chore=chore,
            completed_at=completion_time,
            awarded_points=3,
            chore_name_snapshot="Take out recycling",
            completed_version=1,
        )

        response = self.client.post(
            reverse("household:chore_edit", args=[chore.pk]),
            {
                "name": "Recycling and composting",
                "frequency_days": 14,
                "points": 10,
                "next_due_date": "2026-09-17",
            },
        )
        self.assertRedirects(response, reverse("household:home"))

        chore.refresh_from_db()
        self.assertEqual(chore.completion_version, 2)

        completion.refresh_from_db()
        self.assertEqual(completion.awarded_points, 3)
        self.assertEqual(completion.chore_name_snapshot, "Take out recycling")
        self.assertEqual(completion.completed_version, 1)
        self.assertEqual(completion.completed_at, completion_time)
        self.assertEqual(completion.member, member)
        self.assertEqual(completion.chore, chore)

    def test_successful_creation_saves_active_chore_queues_message_and_redirects(self):
        post_data = {
            "name": "   Wipe down counters   ",
            "frequency_days": 2,
            "points": 4,
            "next_due_date": "2026-09-08",
        }

        response = self.client.post(reverse("household:chore_create"), post_data)

        self.assertRedirects(response, reverse("household:home"))
        chore = Chore.objects.get(name="Wipe down counters")
        self.assertTrue(chore.is_active)
        self.assertEqual(chore.completion_version, 0)
        self.assertEqual(chore.frequency_days, 2)
        self.assertEqual(chore.points, 4)
        self.assertEqual(chore.next_due_date, date(2026, 9, 8))

        # Flash success message queued
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'Chore "Wipe down counters" created.')

    def test_successful_edit_updates_chore_queues_message_and_redirects(self):
        chore = Chore.objects.create(
            name="Mop kitchen floor",
            frequency_days=7,
            points=5,
            next_due_date=date(2026, 9, 10),
            is_active=True,
            completion_version=3,
        )

        response = self.client.post(
            reverse("household:chore_edit", args=[chore.pk]),
            {
                "name": "Deep mop kitchen",
                "frequency_days": 10,
                "points": 8,
                "next_due_date": "2026-09-15",
            },
        )

        self.assertRedirects(response, reverse("household:home"))
        chore.refresh_from_db()
        self.assertEqual(chore.name, "Deep mop kitchen")
        self.assertEqual(chore.frequency_days, 10)
        self.assertEqual(chore.points, 8)
        self.assertEqual(chore.next_due_date, date(2026, 9, 15))
        self.assertEqual(chore.completion_version, 3)
        self.assertTrue(chore.is_active)

        # Flash success message queued
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'Chore "Deep mop kitchen" updated.')
