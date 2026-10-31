"""Daily: after two years on the waiting list, ask whether the interest remains, remind
halfway, take out who never answered (DEC-262).

Run once a day from the host's scheduler, e.g.:

    40 7 * * *  cd /srv/qdc && docker compose exec -T web python manage.py promemoria_lista_attesa
"""

from datetime import date

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.attesa.servizi import promemoria


class Command(BaseCommand):
    help = "Lista d'attesa: chiede dopo due anni se l'interesse resta, toglie chi non risponde."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--oggi", type=date.fromisoformat, help="Solo per prove.")

    def handle(self, *args, oggi: date | None = None, **options) -> None:
        fatti = promemoria(oggi or timezone.localdate())
        self.stdout.write(
            f"Domande: {fatti['chiesti']}, promemoria: {fatti['ricordati']}, "
            f"usciti: {fatti['usciti']}."
        )
