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
from django.core.mail import send_mail
from django.core.management.base import BaseCommand

from apps.anagrafica.models import Appartenenza, Persona, RuoloAppartenenza, VisibilitaGenitori
from apps.anagrafica.preferenze import accetta, nota_a_piede
from apps.core.anno import compie_anni

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


def _testi(persona: Persona, giorno: date, oggi: date) -> tuple[str, str, str]:
    """Subject, text for the member, text for the parents."""
    quando = "oggi" if giorno <= oggi else f"il {giorno.strftime('%d/%m/%Y')}"
    link = f"{settings.FRONTEND_URL}/persone/{persona.pk}"
    oggetto = (
        "Compi 18 anni: cosa vedono i tuoi genitori"
        if giorno <= oggi
        else ("Tra un mese compi 18 anni")
    )
    al_ragazzo = (
        f"Ciao {persona.nome},\n\n"
        f"{quando} compi 18 anni. Da quel giorno decidi tu cosa possono vedere i tuoi "
        f"genitori nel Quaderno di Caccia: contatti, farmaci e allergie, la tua scheda.\n"
        f"Finché non scegli, continuano a vedere tutto.\n\n"
        f"Scegli qui (serve il tuo account; se non l'hai, chiedilo ai tuoi capi):\n{link}\n"
    )
    ai_genitori = (
        f"Gentile genitore,\n\n"
        f"{quando} {persona.nome} compie 18 anni. Da quel giorno sarà {persona.nome} a "
        f"decidere cosa resta visibile a voi nel Quaderno di Caccia. Finché non sceglie, "
        f"continuate a vedere tutto come ora.\n"
    )
    return oggetto, al_ragazzo, ai_genitori


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
            oggetto, al_ragazzo, ai_genitori = _testi(persona, giorno, oggi)
            if accetta(persona, "maggiore_eta") and (email := _email(persona)):
                send_mail(oggetto, al_ragazzo + nota_a_piede(), None, [email])
            # One email per parent: separated parents do not see each other's address.
            genitori = [g for g in _genitori(persona) if accetta(g, "maggiore_eta")]
            for destinatario in sorted({_email(g) for g in genitori} - {""}):
                send_mail(
                    f"{persona.nome} compie 18 anni",
                    ai_genitori + nota_a_piede(),
                    None,
                    [destinatario],
                )
            scelta.save()
            inviati += 1
        self.stdout.write(f"Avvisi inviati per {inviati} persone.")
