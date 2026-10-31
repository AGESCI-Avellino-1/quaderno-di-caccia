"""Alerts for members turning 18 (DEC-26, DEC-119).

At 18 the R/S decides what the parents keep seeing. One month before and on the day,
the member and the parents get an email with the link to the choices. Run once a day
from the host's scheduler, e.g.:

    20 7 * * *  cd /srv/qdc && docker compose exec -T web python manage.py avvisa_maggiore_eta

Each alert is sent once. Members without an account are also shown to the capi on the
unit page (organizzazione.api), so that someone invites them.
"""

from datetime import date, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.anagrafica.models import Appartenenza, Persona, RuoloAppartenenza, VisibilitaGenitori
from apps.anagrafica.preferenze import accetta
from apps.core.anno import compie_anni
from apps.impostazioni.email import invia

ANTICIPO = timedelta(days=30)


def _email(persona: Persona) -> str:
    utente = persona.utente
    return (utente.email if utente else "") or persona.email


def _genitori(persona: Persona) -> list[Persona]:
    return list(
        Persona.objects.filter(
            tutele__minore=persona, tutele__responsabilita_genitoriale=True
        ).exclude(email="", utente__isnull=True)
    )


class Command(BaseCommand):
    help = "Avvisa chi compie 18 anni (e i genitori) che può scegliere cosa vedono i genitori."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--oggi", type=date.fromisoformat, help="Solo per prove.")

    def handle(self, *args, oggi: date | None = None, **options) -> None:
        oggi = oggi or date.today()
        ragazzi = (
            Persona.objects.filter(
                pk__in=Appartenenza.objects.attive(oggi)
                .filter(ruolo=RuoloAppartenenza.RAGAZZO)
                .values("persona_id"),
                data_nascita__isnull=False,
                tutori__responsabilita_genitoriale=True,
            )
            .select_related("utente")
            .distinct()
        )
        inviati = 0
        for persona in ragazzi:
            giorno = compie_anni(persona.data_nascita, 18)
            if not oggi - ANTICIPO < giorno <= oggi + ANTICIPO:
                continue  # also skips those already adult when this was installed
            scelta, _ = VisibilitaGenitori.objects.get_or_create(persona=persona)
            if giorno <= oggi:
                if scelta.avviso_compleanno:
                    continue
                scelta.avviso_compleanno = oggi
            else:
                if scelta.avviso_mese_prima:
                    continue
                scelta.avviso_mese_prima = oggi
            quando = "oggi" if giorno <= oggi else f"il {giorno.strftime('%d/%m/%Y')}"
            valori = {
                "Nome": persona.nome,
                "Quando": quando,
                "Link": f"{settings.FRONTEND_URL}/email",
            }
            if accetta(persona, "maggiore_eta") and (email := _email(persona)):
                modello = "maggiore_eta" if giorno <= oggi else "maggiore_eta_mese_prima"
                invia(modello, valori, [email])
            # One email per parent: separated parents do not see each other's address.
            genitori = [g for g in _genitori(persona) if accetta(g, "maggiore_eta")]
            invia("maggiore_eta_genitori", valori, {_email(g) for g in genitori} - {""})
            scelta.save()
            inviati += 1
        self.stdout.write(f"Avvisi inviati per {inviati} persone.")
