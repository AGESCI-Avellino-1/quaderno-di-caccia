"""Issue the fees whose period has started (daily, cron). Idempotent."""

from django.core.management.base import BaseCommand

from apps.quote.servizi import emetti_tutte


class Command(BaseCommand):
    help = "Emette le quote dell'anno associativo il cui periodo è iniziato."

    def handle(self, *args, **options) -> None:
        self.stdout.write(f"Quote emesse: {emetti_tutte()}")
