"""Reminders to the capigruppo (DEC-209, DEC-44): the year just ended still open, from
1 November, every Monday; people to archive, on the 1st of the month. Only a count and
the link: no names.

    50 7 * * *  cd /srv/qdc && docker compose exec -T web python manage.py promemoria_fine_anno
"""

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.anagrafica.preferenze import accetta, nota_a_piede
from apps.archivio import servizi
from apps.core.anno import AnnoAssociativo
from apps.organizzazione.models import Incarico, RuoloIncarico


class Command(BaseCommand):
    help = "Ricorda ai capigruppo di chiudere l'anno associativo e di archiviare chi è uscito."

    def handle(self, *args, **options) -> None:
        oggi = timezone.localdate()
        righe = []
        anno = servizi.anno_da_chiudere(oggi)
        if anno and (oggi.weekday() == 0 or (oggi.month, oggi.day) == (11, 1)):
            righe.append(
                f"l'anno associativo {AnnoAssociativo(anno).etichetta} è finito ma è ancora "
                "aperto: chiudilo quando rendiconto e verifiche sono fatti."
            )
        if oggi.day == 1:
            numero = servizi.da_archiviare(oggi).count()
            if numero:
                righe.append(
                    f"{numero} persone sono uscite dal gruppo da più di due anni e sono da "
                    "archiviare sul Drive del gruppo."
                )
        if not righe:
            return
        destinatari = sorted(
            {
                i.persona.utente.email
                for i in Incarico.objects.attivi()
                .filter(ruolo=RuoloIncarico.CAPOGRUPPO, persona__utente__isnull=False)
                .select_related("persona__utente")
                if accetta(i.persona, "riepiloghi")
            }
        )
        if not destinatari:
            return
        send_mail(
            subject="Fine anno e archivio nel Quaderno di Caccia",
            message="Ciao,\n\n"
            + "\n\n".join(f"- {r}" for r in righe)
            + f"\n\nTrovi tutto qui:\n{settings.FRONTEND_URL}/gruppo\n"
            + nota_a_piede(),
            from_email=None,
            recipient_list=destinatari,
        )
        self.stdout.write(f"Avvisati {len(destinatari)} capigruppo.")
