"""Daily (cron): reminders of the minutes still to write, and the housekeeping that goes
with them (DEC-328, DEC-330, DEC-331)."""

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.verbali import servizi


class Command(BaseCommand):
    help = "Manda i promemoria dei verbali da scrivere e toglie i nomi conservati e scaduti."

    def handle(self, *args, **options) -> None:
        oggi = timezone.localdate()
        inviati = servizi.promemoria(oggi)
        tolti = servizi.togli_nomi_scaduti(oggi)
        interrotti = servizi.pulisci_caricamenti_interrotti(oggi)
        self.stdout.write(
            f"Promemoria inviati: {inviati}; nomi tolti: {tolti}; "
            f"caricamenti interrotti tolti: {interrotti}"
        )
