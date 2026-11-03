"""Maintenance from the command line (DEC-268), for scripts/aggiorna.sh (DEC-292).

python manage.py manutenzione              # prints "attiva" or "non attiva"
python manage.py manutenzione attiva [--messaggio "…"]
python manage.py manutenzione disattiva
"""

from django.core.management.base import BaseCommand

from apps.impostazioni.models import Impostazioni


class Command(BaseCommand):
    help = "Mostra, attiva o disattiva la manutenzione dell'app."

    def add_arguments(self, parser):
        parser.add_argument("azione", nargs="?", choices=["attiva", "disattiva"])
        parser.add_argument(
            "--messaggio", default=None, help="L'avviso per chi apre l'app (di base quello solito)."
        )

    def handle(self, *args, azione=None, messaggio=None, **options):
        imp = Impostazioni.carica()
        if azione is None:
            self.stdout.write("attiva" if imp.manutenzione else "non attiva")
            return
        imp.manutenzione = azione == "attiva"
        campi = ["manutenzione", "aggiornato_il"]
        if messaggio is not None:
            imp.messaggio_manutenzione = messaggio.strip()
            campi.append("messaggio_manutenzione")
        imp.save(update_fields=campi)
        self.stdout.write(
            "Manutenzione attiva." if imp.manutenzione else "Manutenzione disattivata."
        )
