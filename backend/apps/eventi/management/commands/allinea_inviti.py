"""The invitees of every event and meeting to come follow who is in the units today
(DEC-414). Once after the update that brought the rule, then daily (cron) as a safety net:
the changes in the units already realign them by themselves."""

from django.core.management.base import BaseCommand

from apps.eventi.allineamento import riallinea


class Command(BaseCommand):
    help = "Allinea gli invitati di riunioni ed eventi futuri a chi è oggi nelle unità."

    def handle(self, *args, **options) -> None:
        aggiunti, tolti = riallinea()
        self.stdout.write(f"Inviti aggiunti: {aggiunti}, tolti: {tolti}")
