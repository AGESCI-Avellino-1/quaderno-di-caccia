"""Daily summary to the capigruppo of corrections to forward (DEC-31).

Run once a day from the host's scheduler, e.g.:

    15 7 * * *  cd /srv/qdc && docker compose exec -T web python manage.py segnala_correzioni

Each correction is mentioned in one email only. The email carries only a count and the
link: no names or values (they are personal data of minors).
"""

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.anagrafica.models import CorrezioneAnagrafica, StatoCorrezione
from apps.anagrafica.preferenze import accetta
from apps.impostazioni.email import invia
from apps.notifiche.servizi import notifica
from apps.organizzazione.models import Incarico, RuoloIncarico
from apps.permessi import policy


def _capigruppo() -> list:
    """Only who may forward them (DEC-385)."""
    incarichi = (
        Incarico.objects.attivi()
        .filter(ruolo=RuoloIncarico.CAPOGRUPPO)
        .select_related("persona__utente")
    )
    return policy.chi_puo((i.persona for i in incarichi), policy.puo_gestire_correzioni)


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
        capigruppo = _capigruppo()
        destinatari = sorted({p.utente.email for p in capigruppo if accetta(p, "riepiloghi")})
        if not destinatari:
            self.stderr.write("Nessun capogruppo da avvisare: nessuna email inviata.")
            return
        da_inoltrare = CorrezioneAnagrafica.objects.filter(stato=StatoCorrezione.IN_ATTESA).count()
        notifica(
            "riepiloghi",
            capigruppo,
            "Correzioni da inoltrare",
            "/correzioni",
        )
        # One message per capogruppo: nobody sees the others' addresses.
        invia(
            "correzioni_da_inoltrare",
            {
                "Nuove": str(numero),
                "Da inoltrare": str(da_inoltrare),
                "Link": f"{settings.FRONTEND_URL}/correzioni",
            },
            destinatari,
        )
        nuove.update(segnalata_il=timezone.now())
        self.stdout.write(f"Avvisati {len(destinatari)} capigruppo.")
