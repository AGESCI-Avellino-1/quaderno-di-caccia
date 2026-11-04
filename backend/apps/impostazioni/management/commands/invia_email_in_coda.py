"""Sends the queued emails a block at a time (DEC-311). With --continua it never stops:
the "posta" service of compose.prod.yml runs it so."""

import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from apps.impostazioni import coda
from apps.notifiche import servizi as notifiche

# How often the queue is looked at; the pause between blocks is in the settings.
OGNI_SECONDI = 15


class Command(BaseCommand):
    help = "Manda le email in coda, un blocco alla volta."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--continua", action="store_true", help="Non si ferma: guarda la coda ogni 15 secondi."
        )

    def handle(self, *args, **options) -> None:
        if not options["continua"]:
            inviate = coda.smaltisci()
            notifiche.smaltisci()
            self.stdout.write(f"Email inviate: {inviate}.")
            return
        while True:
            close_old_connections()
            coda.smaltisci()
            notifiche.smaltisci()
            time.sleep(OGNI_SECONDI)
