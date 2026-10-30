"""Emails of the notice board: on publishing, when the author asks, one message per
address; a kind of email the reader may refuse (DEC-157, DEC-219)."""

from django.conf import settings
from django.core.mail import EmailMessage, mailers
from django.utils import timezone

from apps.anagrafica.models import Appartenenza, Persona, RuoloAppartenenza
from apps.anagrafica.preferenze import accetta, nota_a_piede
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
    corpo = (
        f"Ciao,\n\n{avviso.titolo}\n\n{avviso.testo}\n\n"
        f"Nella bacheca dell'app:\n{settings.FRONTEND_URL}/bacheca" + nota_a_piede()
    )
    messaggi = [EmailMessage(subject=avviso.titolo, body=corpo, to=[a]) for a in indirizzi]
    if messaggi:
        mailers.default.send_messages(messaggi)
    avviso.email_inviata_il = timezone.now()
    avviso.save(update_fields=["email_inviata_il"])
    return len(messaggi)
