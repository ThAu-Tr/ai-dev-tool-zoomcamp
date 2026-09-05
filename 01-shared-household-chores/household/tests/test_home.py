from django.test import SimpleTestCase
from django.urls import reverse


class HomeTests(SimpleTestCase):
    def test_home_displays_placeholder_without_login(self):
        response = self.client.get(reverse("household:home"))

        self.assertContains(response, "<h1>Shared Household Chores</h1>", html=True)
        self.assertTemplateUsed(response, "household/home.html")
