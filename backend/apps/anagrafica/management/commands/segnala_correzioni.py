"""Daily summary to the capigruppo of corrections to forward (DEC-31).

Run once a day from the host's scheduler, e.g.:

    15 7 * * *  cd /srv/qdc && docker compose exec -T web python manage.py segnala_correzioni

Each correction is mentioned in one email only. The email carries only a count and the
link: no names or values (they are personal data of minors).
"""

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.anagrafica.models import CorrezioneAnagrafica, StatoCorrezione
from apps.anagrafica.preferenze import accetta, nota_a_piede
from apps.organizzazione.models import Incarico, RuoloIncarico


class Command(BaseCommand):
    help = "Avvisa i capigruppo delle correzioni nuove da inoltrare alla segreteria."

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        nuove = CorrezioneAnagrafica.objects.select_for_update().filter(
            stato=StatoCorrezione.IN_ATTESA, segnalata_il__isnull=True
        )
        numero = nuove.count()
        if not numero:
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
            self.stderr.write("Nessun capogruppo da avvisare: nessuna email inviata.")
            return
        da_inoltrare = CorrezioneAnagrafica.objects.filter(stato=StatoCorrezione.IN_ATTESA).count()
        send_mail(
            subject="Correzioni da inoltrare alla segreteria",
            message=(
                f"Ciao,\n\n"
                f"nel Quaderno di Caccia ci sono {numero} nuove correzioni ai dati di "
                f"BuonaStrada ({da_inoltrare} in tutto da inoltrare alla segreteria).\n\n"
                f"Le trovi qui:\n{settings.FRONTEND_URL}/correzioni\n\n"
                f"Dopo averle inoltrate, segnalale come inoltrate nell'app." + nota_a_piede()
            ),
            from_email=None,
            recipient_list=destinatari,
        )
        nuove.update(segnalata_il=timezone.now())
        self.stdout.write(f"Avvisati {len(destinatari)} capigruppo.")
