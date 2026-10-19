from django.core.management.base import BaseCommand
from django.utils import timezone

from crm.models import ContactImportReceipt, ContactImportState


class Command(BaseCommand):
    help = "Remove expired contact-import receipts and preview states; keep active previews protected."

    def handle(self, *args, **options):
        removed, _ = ContactImportReceipt.objects.filter(expires_at__lte=timezone.now()).delete()
        self.stdout.write(f"Removed {removed} expired contact-import receipt(s).")
        states, _ = ContactImportState.objects.filter(expires_at__lte=timezone.now()).delete()
        self.stdout.write(f"Removed {states} expired contact-import preview state(s).")
