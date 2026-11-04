"""Emails about events (DEC-79): a new event, a change of dates or place, a
cancellation. To the families of the participants (to the adult member, and to their
parents while they still see their activities, DEC-26). One message per address, so
nobody sees the others'. Meetings are not announced (DEC-310): only a single meeting
moved or cancelled.
"""

from django.conf import settings
from django.utils import timezone

from apps.anagrafica.models import Persona
from apps.anagrafica.preferenze import accetta
from apps.impostazioni.email import invia
from apps.permessi.policy import genitori_vedono

from .models import CERCHIE_CONVOCATE, Evento, StatoPartecipazione, TipoEvento


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


def indirizzi_diretti(persone, categoria: str | None = None) -> list[str]:
    """The people themselves: at a meeting of the parents they are the ones invited, not
    the families of who is invited (DEC-325). No category: an email that always goes."""
    indirizzi = []
    for chi in persone.select_related("utente"):
        if categoria and not accetta(chi, categoria):
            continue
        email = chi.email or (chi.utente.email if chi.utente else "")
        if email and email not in indirizzi:
            indirizzi.append(email)
    return indirizzi


def quando(evento: Evento) -> str:
    return _quando(evento)


def _quando(evento: Evento) -> str:
    inizio = timezone.localtime(evento.inizio)
    fine = timezone.localtime(evento.fine)
    if inizio.date() == fine.date():
        return f"{inizio:%d/%m/%Y}, dalle {inizio:%H:%M} alle {fine:%H:%M}"
    return f"dal {inizio:%d/%m/%Y %H:%M} al {fine:%d/%m/%Y %H:%M}"


def _invia(evento: Evento, modello: str, valori: dict[str, str]) -> int:
    partecipanti = Persona.objects.filter(
        partecipazioni__evento=evento, partecipazioni__stato=StatoPartecipazione.INVITATO
    )
    indirizzi = (
        indirizzi_diretti(partecipanti, "eventi")
        if evento.cerchia in CERCHIE_CONVOCATE
        else indirizzi_famiglia(partecipanti, "eventi")
    )
    return invia(
        modello,
        {
            "Evento": evento.titolo,
            "Link": f"{settings.FRONTEND_URL}/{'riunioni' if _riunione(evento) else 'eventi'}"
            f"/{evento.pk}",
            **valori,
        },
        indirizzi,
    )


def _da_annunciare(evento: Evento) -> bool:
    return evento.fine >= timezone.now()


def _riunione(evento: Evento) -> bool:
    return evento.tipo == TipoEvento.RIUNIONE


def nuovo(evento: Evento) -> int:
    if not _da_annunciare(evento) or _riunione(evento):
        return 0
    dettagli = []
    if evento.luogo:
        dettagli.append(f"Luogo: {evento.luogo}")
    tipo = getattr(evento, "quota", None)
    if tipo is not None:
        dettagli.append(f"Quota: {tipo.importo} €")
    return _invia(
        evento, "evento_nuovo", {"Quando": _quando(evento), "Dettagli": "\n".join(dettagli)}
    )


def modificato(evento: Evento) -> int:
    if not _da_annunciare(evento):
        return 0
    quando = _quando(evento) + (f", a {evento.luogo}" if evento.luogo else "")
    modello = "riunione_spostata" if _riunione(evento) else "evento_modificato"
    return _invia(evento, modello, {"Quando": quando})


def annullato(evento: Evento) -> int:
    if not _da_annunciare(evento):
        return 0
    return _invia(
        evento,
        "riunione_annullata" if _riunione(evento) else "evento_annullato",
        {"Quando": _quando(evento), "Motivo": evento.motivo_annullamento},
    )
