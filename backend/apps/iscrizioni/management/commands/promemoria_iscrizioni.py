"""Daily emails about registrations from the app (DEC-125).

- to who approves: new requests waiting (one email each, count and link only);
- to the family: a reminder some days before the deadline to complete;
- at the deadline, if still incomplete: the registration is suspended (the family no
  longer sees that member until it completes) and told so.

Run once a day from the host's scheduler, e.g.:

    25 7 * * *  cd /srv/qdc && docker compose exec -T web python manage.py promemoria_iscrizioni
"""

from datetime import date, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.anagrafica.preferenze import accetta
from apps.impostazioni.email import invia
from apps.iscrizioni.models import RichiestaIscrizione, StatoIscrizione
from apps.iscrizioni.servizi import mancanti
from apps.organizzazione.models import Incarico, RuoloIncarico, TipoUnita

# How many days before the deadline the family is reminded (DEC-125).
PREAVVISO = timedelta(days=7)


def _approvatori(unita) -> set[str]:
    ruoli = {RuoloIncarico.CAPOGRUPPO}
    filtro = Incarico.objects.attivi().filter(persona__utente__isnull=False)
    capigruppo = filtro.filter(ruolo__in=ruoli)
    staff = (
        filtro.filter(unita=unita, ruolo__in={RuoloIncarico.STAFF, RuoloIncarico.CAPO_UNITA})
        if unita.tipo != TipoUnita.COMUNITA_CAPI
        else filtro.none()
    )
    return {
        i.persona.utente.email
        for i in (capigruppo | staff).select_related("persona__utente")
        if accetta(i.persona, "riepiloghi")
    }


class Command(BaseCommand):
    help = "Avvisi giornalieri sulle iscrizioni dall'app."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--oggi", type=date.fromisoformat, help="Solo per prove.")

    def handle(self, *args, oggi: date | None = None, **options) -> None:
        oggi = oggi or timezone.localdate()
        link = settings.FRONTEND_URL

        nuove = RichiestaIscrizione.objects.filter(
            stato=StatoIscrizione.IN_ATTESA, segnalata_il__isnull=True
        ).select_related("unita")
        for richiesta in nuove:
            invia(
                "nuova_richiesta_iscrizione",
                {"Unità": str(richiesta.unita), "Link": f"{link}/iscrizioni"},
                _approvatori(richiesta.unita),
            )
            richiesta.segnalata_il = timezone.now()
            richiesta.save(update_fields=["segnalata_il", "aggiornato_il"])

        da_completare = RichiestaIscrizione.objects.filter(
            stato=StatoIscrizione.APPROVATA, scadenza_completamento__isnull=False
        ).select_related("utente", "unita", "persona")
        for richiesta in da_completare:
            email = richiesta.utente.email if richiesta.utente else ""
            scadenza = richiesta.scadenza_completamento
            valori = {
                "Nome": richiesta.nome,
                "Scadenza": scadenza.strftime("%d/%m/%Y"),
                "Link": f"{link}/mia-iscrizione",
            }
            if scadenza <= oggi and mancanti(richiesta):
                richiesta.stato = StatoIscrizione.SOSPESA
                richiesta.sospesa_il = oggi
                richiesta.save(update_fields=["stato", "sospesa_il", "aggiornato_il"])
                invia("iscrizione_sospesa", valori, [email])
            elif scadenza - PREAVVISO <= oggi < scadenza and not richiesta.promemoria_il:
                richiesta.promemoria_il = oggi
                richiesta.save(update_fields=["promemoria_il", "aggiornato_il"])
                invia("iscrizione_da_completare", valori, [email])
