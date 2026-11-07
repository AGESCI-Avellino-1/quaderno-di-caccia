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
from apps.notifiche.servizi import notifica
from apps.permessi.policy import genitori_vedono

from .models import CERCHIE_CONVOCATE, Evento, StatoPartecipazione, TipoEvento

TITOLI_PUSH = {
    "evento_nuovo": "Nuovo evento",
    "evento_modificato": "Evento cambiato",
    "evento_annullato": "Evento annullato",
    "riunione_spostata": "Riunione spostata",
    "riunione_annullata": "Riunione annullata",
}


def famiglia(persone, vedono: str = "scheda") -> list[Persona]:
    """The adult member themself, the parents with parental responsibility of a minor
    (of an adult while they still see `vedono`, what the email is about, DEC-26)."""
    chi: list[Persona] = []
    for persona in persone:
        if not persona.e_minorenne():
            chi.append(persona)
        if persona.e_minorenne() or genitori_vedono(persona, vedono):
            chi += [
                t.tutore
                for t in persona.tutori.select_related("tutore__utente").filter(
                    responsabilita_genitoriale=True
                )
            ]
    return chi


def indirizzi_famiglia(persone, categoria: str, vedono: str = "scheda") -> list[str]:
    """The family's addresses; not who chose not to receive this kind of email."""
    indirizzi: list[str] = []
    for chi in famiglia(persone, vedono):
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
        giorno = f"{inizio:%d/%m/%Y}"
        # Only the day may be known, on BuonaCaccia (DEC-391).
        if evento.senza_ora_inizio and evento.senza_ora_fine:
            return giorno
        if evento.senza_ora_fine:
            return f"{giorno}, dalle {inizio:%H:%M}"
        if evento.senza_ora_inizio:
            return f"{giorno}, fino alle {fine:%H:%M}"
        return f"{giorno}, dalle {inizio:%H:%M} alle {fine:%H:%M}"
    dal = f"{inizio:%d/%m/%Y}" if evento.senza_ora_inizio else f"{inizio:%d/%m/%Y %H:%M}"
    al = f"{fine:%d/%m/%Y}" if evento.senza_ora_fine else f"{fine:%d/%m/%Y %H:%M}"
    return f"dal {dal} al {al}"


def _invia(evento: Evento, modello: str, valori: dict[str, str]) -> int:
    partecipanti = Persona.objects.filter(
        partecipazioni__evento=evento, partecipazioni__stato=StatoPartecipazione.INVITATO
    )
    diretti = evento.cerchia in CERCHIE_CONVOCATE
    indirizzi = (
        indirizzi_diretti(partecipanti, "eventi")
        if diretti
        else indirizzi_famiglia(partecipanti, "eventi")
    )
    percorso = f"/{'riunioni' if _riunione(evento) else 'eventi'}/{evento.pk}"
    inviate = invia(
        modello,
        {"Evento": evento.titolo, "Link": f"{settings.FRONTEND_URL}{percorso}", **valori},
        indirizzi,
    )
    notifica(
        "eventi",
        list(partecipanti) if diretti else famiglia(partecipanti),
        f"{TITOLI_PUSH[modello]}: {evento.titolo}",
        percorso,
    )
    return inviate


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
