from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from household.models import Member


PREDEFINED_MEMBERS = (("Alex", 1), ("Sam", 2), ("Jamie", 3))


class Command(BaseCommand):
    help = "Create the predefined household members without changing existing data."

    @transaction.atomic
    def handle(self, *args, **options):
        existing_members = list(Member.objects.all())
        by_name = {member.name: member for member in existing_members}
        by_order = {member.display_order: member for member in existing_members}

        missing = []
        conflicts = []
        for name, display_order in PREDEFINED_MEMBERS:
            named_member = by_name.get(name)
            ordered_member = by_order.get(display_order)

            if (
                named_member is not None
                and named_member.display_order == display_order
            ):
                continue

            if named_member is not None:
                conflicts.append(
                    f"name {name!r} already has display order "
                    f"{named_member.display_order} (required: {display_order})"
                )
            if ordered_member is not None:
                conflicts.append(
                    f"display order {display_order} already belongs to "
                    f"{ordered_member.name!r} (required: {name!r})"
                )
            if named_member is None and ordered_member is None:
                missing.append((name, display_order))

        if conflicts:
            raise CommandError(
                "Cannot set up predefined members because existing data conflicts: "
                + "; ".join(conflicts)
                + ". No member data was changed."
            )

        for name, display_order in missing:
            Member.objects.create(name=name, display_order=display_order)

        if missing:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created {len(missing)} predefined member(s): "
                    + ", ".join(name for name, _ in missing)
                    + "."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("Predefined members already exist; no changes made.")
            )
