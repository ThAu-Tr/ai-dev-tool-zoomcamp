from datetime import date, datetime, timezone as datetime_timezone
from unittest.mock import patch

from django.contrib import messages
from django.contrib.messages import constants as message_constants
from django.contrib.messages.storage.cookie import CookieStorage
from django.test import RequestFactory, TestCase
from django.urls import reverse

from household.models import Chore, Member
from household.views import home


class HomeTests(TestCase):
    def create_chore(self, name, due_date, *, active=True, frequency=1, points=1):
        return Chore.objects.create(
            name=name,
            frequency_days=frequency,
            points=points,
            next_due_date=due_date,
            is_active=active,
        )

    def get_at(self, instant):
        with patch("household.scheduling.timezone.now", return_value=instant):
            return self.client.get(reverse("household:home"))

    def test_anonymous_home_uses_shared_base_layout_and_static_css(self):
        response = self.client.get(reverse("household:home"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "household/home.html")
        self.assertTemplateUsed(response, "household/base.html")
        self.assertContains(response, '<link rel="stylesheet" href="/static/household/site.css">')
        self.assertContains(response, '<a href="/">Household</a>', html=True)
        self.assertContains(response, '<h1>Shared Household Chores</h1>', html=True)
        self.assertEqual(response.content.count(b"<h1"), 1)

    def test_members_are_displayed_in_display_order(self):
        Member.objects.create(name="Jamie", display_order=3)
        Member.objects.create(name="Alex", display_order=1)
        Member.objects.create(name="Sam", display_order=2)

        response = self.client.get(reverse("household:home"))

        content = response.content.decode()
        self.assertLess(content.index(">Alex<"), content.index(">Sam<"))
        self.assertLess(content.index(">Sam<"), content.index(">Jamie<"))

    def test_member_empty_state(self):
        response = self.client.get(reverse("household:home"))

        self.assertContains(response, "No household members available.")
        self.assertNotContains(response, 'class="member-list"')

    def test_active_chores_show_all_due_labels_and_required_details(self):
        today = date(2026, 9, 6)
        self.create_chore("Overdue chore", date(2026, 9, 5), frequency=1, points=1)
        self.create_chore("Due chore", today, frequency=2, points=2)
        self.create_chore("Future chore", date(2026, 9, 7), frequency=7, points=10)
        self.create_chore("Hidden inactive", today, active=False)

        response = self.get_at(datetime(2026, 9, 6, 10, tzinfo=datetime_timezone.utc))

        self.assertContains(response, "Overdue")
        self.assertContains(response, "Due")
        self.assertContains(response, "Not yet due")
        self.assertContains(response, "1 day")
        self.assertContains(response, "2 days")
        self.assertContains(response, "1 point")
        self.assertContains(response, "10 points")
        self.assertContains(response, "2026-09-05")
        self.assertNotContains(response, "Hidden inactive")
        self.assertNotContains(response, 'value="Hidden inactive"')

    def test_active_chores_follow_status_due_date_name_and_pk_ordering(self):
        first = self.create_chore("alpha", date(2026, 9, 4))
        second = self.create_chore("Bravo", date(2026, 9, 4))
        future = self.create_chore("Future", date(2026, 9, 7))
        due = self.create_chore("Due", date(2026, 9, 6))
        later_overdue = self.create_chore("Earlier name", date(2026, 9, 5))

        response = self.get_at(datetime(2026, 9, 6, 10, tzinfo=datetime_timezone.utc))

        self.assertEqual(
            [item.chore for item in response.context["active_chores"]],
            [first, second, later_overdue, due, future],
        )

    def test_active_chore_empty_state_has_no_chore_list_or_controls(self):
        self.create_chore("Inactive", date(2026, 9, 6), active=False)

        response = self.client.get(reverse("household:home"))

        self.assertContains(response, "No active chores yet.")
        self.assertNotContains(response, 'class="chore-list"')
        self.assertNotContains(response, "Complete")
        self.assertNotContains(response, "Add chore")

    def test_messages_render_before_page_content_with_correct_roles(self):
        request = RequestFactory().get(reverse("household:home"))
        request._messages = CookieStorage(request)
        messages.add_message(request, message_constants.INFO, "A helpful update")
        messages.add_message(request, message_constants.ERROR, "A problem occurred")

        response = self.client.get(reverse("household:home"))
        self.assertNotContains(response, 'class="messages"')

        response = home(request)
        content = response.content.decode()
        self.assertIn('role="status">A helpful update', content)
        self.assertIn('role="alert">A problem occurred', content)
        self.assertLess(content.index("A helpful update"), content.index("<h1>"))
