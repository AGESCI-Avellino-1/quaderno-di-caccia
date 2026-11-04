"""Documents past their last day go, from the server too (DEC-342). Daily, from cron."""

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.documenti import servizi


class Command(BaseCommand):
    help = "Cancella i documenti scaduti."

    def handle(self, *args, **options) -> None:
        cancellati = servizi.cancella_scaduti(timezone.localdate())
        self.stdout.write(f"Documenti cancellati: {cancellati}.")
