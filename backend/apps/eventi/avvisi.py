"""Emails about events (DEC-79): a new event, a change of dates or place, a
cancellation. To the families of the participants (to the adult member, and to their
parents while they still see their activities, DEC-26). One message per address, so
nobody sees the others'. Weekly meetings are not announced one by one.
"""

from django.conf import settings
from django.core.mail import EmailMessage, mailers
from django.utils import timezone

from apps.anagrafica.models import Persona
from apps.anagrafica.preferenze import accetta, nota_a_piede
from apps.permessi.policy import genitori_vedono

from .models import Evento, StatoPartecipazione


def indirizzi_famiglia(persone, categoria: str) -> list[str]:
    """The adult member themself, the parents with parental responsibility of a minor
    (of an adult while they still see their activities); not who chose not to receive
    this kind of email."""
    indirizzi: list[str] = []
    for persona in persone:
        destinatari = [] if persona.e_minorenne() else [persona]
        if persona.e_minorenne() or genitori_vedono(persona, "scheda"):
            destinatari += [
                t.tutore
                for t in persona.tutori.select_related("tutore__utente").filter(
                    responsabilita_genitoriale=True
                )
            ]
        for chi in destinatari:
            if not accetta(chi, categoria):
                continue
            email = chi.email or (chi.utente.email if chi.utente else "")
            if email and email not in indirizzi:
                indirizzi.append(email)
    return indirizzi


def _quando(evento: Evento) -> str:
    inizio = timezone.localtime(evento.inizio)
    fine = timezone.localtime(evento.fine)
    if inizio.date() == fine.date():
        return f"{inizio:%d/%m/%Y}, dalle {inizio:%H:%M} alle {fine:%H:%M}"
    return f"dal {inizio:%d/%m/%Y %H:%M} al {fine:%d/%m/%Y %H:%M}"


def _invia(evento: Evento, oggetto: str, testo: str) -> int:
    partecipanti = Persona.objects.filter(
        partecipazioni__evento=evento, partecipazioni__stato=StatoPartecipazione.INVITATO
    )
    indirizzi = indirizzi_famiglia(partecipanti, "eventi")
    corpo = (
        f"Ciao,\n\n{testo}\n\nI dettagli nell'app:\n{settings.FRONTEND_URL}/eventi/{evento.pk}"
        + nota_a_piede()
    )
    messaggi = [EmailMessage(subject=oggetto, body=corpo, to=[a]) for a in indirizzi]
    if messaggi:
        mailers.default.send_messages(messaggi)
    return len(messaggi)


def _da_annunciare(evento: Evento) -> bool:
    return evento.riunione_id is None and evento.fine >= timezone.now()


def nuovo(evento: Evento) -> int:
    if not _da_annunciare(evento):
        return 0
    righe = [f"nuovo evento: {evento.titolo}", _quando(evento)]
    if evento.luogo:
        righe.append(f"Luogo: {evento.luogo}")
    tipo = getattr(evento, "quota", None)
    if tipo is not None:
        righe.append(f"Quota: {tipo.importo} €")
    return _invia(evento, evento.titolo, "\n".join(righe))


def modificato(evento: Evento) -> int:
    if not _da_annunciare(evento):
        return 0
    testo = f"è cambiato l'evento {evento.titolo}: ora è {_quando(evento)}"
    if evento.luogo:
        testo += f", a {evento.luogo}"
    return _invia(evento, f"Cambiato: {evento.titolo}", testo + ".")


def annullato(evento: Evento) -> int:
    if evento.riunione_id is not None or evento.fine < timezone.now():
        return 0
    return _invia(
        evento,
        f"Annullato: {evento.titolo}",
        f"l'evento {evento.titolo} ({_quando(evento)}) è annullato: {evento.motivo_annullamento}",
    )
