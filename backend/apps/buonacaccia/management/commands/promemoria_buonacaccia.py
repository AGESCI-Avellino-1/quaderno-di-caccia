"""Daily (cron): reminders of the BuonaCaccia deadlines to the staff and the families
(DEC-158, DEC-160)."""

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.buonacaccia.avvisi import promemoria


class Command(BaseCommand):
    help = "Manda i promemoria delle scadenze delle iscrizioni su BuonaCaccia."

    def handle(self, *args, **options) -> None:
        inviati = promemoria(timezone.localdate())
        self.stdout.write(f"Promemoria inviati: {inviati}")
