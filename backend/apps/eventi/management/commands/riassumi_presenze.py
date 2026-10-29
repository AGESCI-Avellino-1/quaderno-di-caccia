"""Attendance older than two associative years becomes yearly totals (DEC-78). Daily
(cron): it only acts once a year has gone past the limit."""

from django.core.management.base import BaseCommand

from apps.eventi.servizi import riassumi_presenze


class Command(BaseCommand):
    help = "Riassume in totali per anno le presenze più vecchie di due anni associativi."

    def handle(self, *args, **options) -> None:
        self.stdout.write(f"Presenze riassunte: {riassumi_presenze()}")
