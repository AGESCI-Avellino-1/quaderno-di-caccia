"""Emails of the notice board: on publishing, when the author asks, one message per
address; a kind of email the reader may refuse (DEC-157, DEC-219)."""

from django.conf import settings
from django.utils import timezone

from apps.anagrafica.models import Appartenenza, Persona, RuoloAppartenenza
from apps.anagrafica.preferenze import accetta
from apps.impostazioni.email import invia as invia_email
from apps.permessi.policy import genitori_vedono

from .models import Avviso, Destinatari


def _email(persona: Persona) -> str:
    return persona.email or (persona.utente.email if persona.utente_id else "")


def lettori(avviso: Avviso) -> list[Persona]:
    """Who the notice is for, as people (not accounts: parents get emails before they
    have one)."""
    attive = Appartenenza.objects.attive().select_related("persona__utente")
    if avviso.destinatari == Destinatari.CAPI:
        return [a.persona for a in attive.filter(ruolo=RuoloAppartenenza.CAPO)]
    ragazzi_app = attive.filter(ruolo=RuoloAppartenenza.RAGAZZO)
    if avviso.unita_id is not None:
        ragazzi_app = ragazzi_app.filter(unita_id=avviso.unita_id)
    ragazzi = list({a.persona_id: a.persona for a in ragazzi_app}.values())
    chi: list[Persona] = []
    if avviso.destinatari in (Destinatari.FAMIGLIE, Destinatari.RAGAZZI):
        chi += ragazzi
    if avviso.destinatari in (Destinatari.FAMIGLIE, Destinatari.GENITORI):
        for ragazzo in ragazzi:
            if not genitori_vedono(ragazzo, "scheda"):
                continue
            chi += [
                t.tutore
                for t in ragazzo.tutori.select_related("tutore__utente").filter(
                    responsabilita_genitoriale=True
                )
            ]
    return chi


def invia(avviso: Avviso) -> int:
    indirizzi: list[str] = []
    for persona in lettori(avviso):
        email = _email(persona)
        if email and email not in indirizzi and accetta(persona, "avvisi"):
            indirizzi.append(email)
    inviati = invia_email(
        "avviso_bacheca",
        {
            "Titolo": avviso.titolo,
            "Testo": avviso.testo,
            "Link": f"{settings.FRONTEND_URL}/bacheca",
        },
        indirizzi,
    )
    avviso.email_inviata_il = timezone.now()
    avviso.save(update_fields=["email_inviata_il"])
    return inviati
