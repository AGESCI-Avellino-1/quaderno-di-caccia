"""Check that the Drive of the archive is set up right (DEC-196), without writing on it.

python manage.py controlla_drive
"""

from django.core.management.base import BaseCommand, CommandError

from apps.archivio import drive


class Command(BaseCommand):
    help = "Controlla l'impostazione del Drive dell'archivio, senza scriverci nulla."

    def handle(self, *args, **options):
        esiti = drive.controlla()
        for ok, messaggio in esiti:
            self.stdout.write(f"{'OK  ' if ok else 'NO  '}{messaggio}")
        if not all(ok for ok, _ in esiti):
            raise CommandError(
                "Il Drive non è ancora impostato bene: correggi il punto segnato NO."
            )
        self.stdout.write(self.style.SUCCESS("Il Drive dell'archivio è pronto."))
