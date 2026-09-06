from io import StringIO

from django.core.management import CommandError, call_command
from django.test import TestCase

from household.models import Member


class SetupMembersCommandTests(TestCase):
    def test_fresh_setup_creates_exact_predefined_members(self):
        call_command("setup_members", stdout=StringIO())

        self.assertEqual(
            list(Member.objects.values_list("name", "display_order")),
            [("Alex", 1), ("Sam", 2), ("Jamie", 3)],
        )

    def test_repeated_setup_creates_nothing_and_changes_nothing(self):
        call_command("setup_members", stdout=StringIO())
        before = list(Member.objects.values_list("id", "name", "display_order"))

        output = StringIO()
        call_command("setup_members", stdout=output)

        self.assertEqual(
            list(Member.objects.values_list("id", "name", "display_order")),
            before,
        )
        self.assertIn("no changes made", output.getvalue())

    def test_conflict_errors_without_partial_changes(self):
        existing = Member.objects.create(name="Existing", display_order=2)
        before = list(Member.objects.values_list("id", "name", "display_order"))

        with self.assertRaisesMessage(CommandError, "existing data conflicts"):
            call_command("setup_members", stdout=StringIO(), stderr=StringIO())

        existing.refresh_from_db()
        self.assertEqual((existing.name, existing.display_order), ("Existing", 2))
        self.assertEqual(
            list(Member.objects.values_list("id", "name", "display_order")),
            before,
        )

    def test_name_at_wrong_order_conflicts_without_overwrite(self):
        alex = Member.objects.create(name="Alex", display_order=4)

        with self.assertRaisesMessage(CommandError, "required: 1"):
            call_command("setup_members", stdout=StringIO(), stderr=StringIO())

        alex.refresh_from_db()
        self.assertEqual((alex.name, alex.display_order), ("Alex", 4))
        self.assertEqual(Member.objects.count(), 1)
