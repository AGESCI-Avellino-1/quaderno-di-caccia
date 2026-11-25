"""Emails about events (DEC-79): a new event, a change of dates or place, a
cancellation. To the families of the participants (to the adult member, and to their
parents while they still see their activities, DEC-26). One message per address, so
nobody sees the others'. Meetings: one moved or cancelled, and a new one or a new series when
who creates it chooses so (DEC-431).
"""

from django.conf import settings
from django.utils import timezone

from apps.anagrafica.models import Persona
from apps.anagrafica.preferenze import accetta
from apps.impostazioni.email import invia
from apps.notifiche.servizi import notifica
from apps.permessi.policy import genitori_vedono

from .models import CERCHIE_CONVOCATE, Cerchia, Evento, StatoPartecipazione, TipoEvento

TITOLI_PUSH = {
    "evento_nuovo": "Nuovo evento",
    "evento_modificato": "Evento cambiato",
    "evento_annullato": "Evento annullato",
    "riunione_nuova": "Nuova riunione",
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


def _invitati_e_genitori(partecipanti) -> list[Persona]:
    """The people themselves, a minor only with their own account, and the parents of the
    minors (DEC-431): never the parents of an adult."""
    chi: dict[int, Persona] = {}
    for persona in partecipanti.select_related("utente"):
        if not persona.e_minorenne():
            chi[persona.pk] = persona
            continue
        if persona.utente_id:
            chi[persona.pk] = persona
        for t in persona.tutori.select_related("tutore__utente").filter(
            responsabilita_genitoriale=True
        ):
            chi[t.tutore_id] = t.tutore
    return list(chi.values())


def _invia_a(chi: list[Persona], modello: str, titolo: str, valori: dict, percorso: str) -> int:
    indirizzi = []
    for p in chi:
        if not accetta(p, "eventi"):
            continue
        # A minor's email in the registry may be a parent's: only their account's.
        if p.e_minorenne():
            email = p.utente.email if p.utente else ""
        else:
            email = p.email or (p.utente.email if p.utente else "")
        if email and email not in indirizzi:
            indirizzi.append(email)
    inviate = invia(
        modello,
        {"Evento": titolo, "Link": f"{settings.FRONTEND_URL}{percorso}", **valori},
        indirizzi,
    )
    notifica("eventi", chi, f"{TITOLI_PUSH[modello]}: {titolo}", percorso)
    return inviate


GIORNI = ("lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica")


def riunioni_nuove(eventi: list[Evento], persone: list[Persona] | None = None) -> int:
    """One email for the meeting or for the whole series just created (DEC-431); with
    `persone` only to them, chosen later (DEC-430)."""
    eventi = [e for e in eventi if _da_annunciare(e)]
    if not eventi:
        return 0
    primo, ultimo = eventi[0], eventi[-1]
    if len(eventi) > 1:
        inizio, fine = timezone.localtime(primo.inizio), timezone.localtime(primo.fine)
        quando = (
            f"ogni {GIORNI[inizio.weekday()]}, dalle {inizio:%H:%M} alle {fine:%H:%M}, "
            f"dal {inizio:%d/%m/%Y} al {timezone.localtime(ultimo.inizio):%d/%m/%Y}"
        )
        percorso = "/riunioni"
    else:
        quando = _quando(primo)
        percorso = f"/riunioni/{primo.pk}"
    dove = primo.dove()
    partecipanti = Persona.objects.filter(
        partecipazioni__evento__in=eventi, partecipazioni__stato=StatoPartecipazione.INVITATO
    ).distinct()
    if persone is not None:
        partecipanti = partecipanti.filter(pk__in=[p.pk for p in persone])
    return _invia_a(
        _invitati_e_genitori(partecipanti),
        "riunione_nuova",
        primo.titolo,
        {"Quando": quando + (f", {dove}" if dove else "")},
        percorso,
    )


def _invia(
    evento: Evento, modello: str, valori: dict[str, str], percorso: str | None = None
) -> int:
    partecipanti = Persona.objects.filter(
        partecipazioni__evento=evento, partecipazioni__stato=StatoPartecipazione.INVITATO
    )
    percorso = percorso or f"/{'riunioni' if _riunione(evento) else 'eventi'}/{evento.pk}"
    if evento.cerchia == Cerchia.SCELTI:
        chi = _invitati_e_genitori(partecipanti)
        return _invia_a(chi, modello, evento.titolo, valori, percorso)
    # A staff meeting is for the capi themselves, never their families (DEC-401).
    diretti = evento.cerchia in CERCHIE_CONVOCATE or evento.cerchia == Cerchia.STAFF
    indirizzi = (
        indirizzi_diretti(partecipanti, "eventi")
        if diretti
        else indirizzi_famiglia(partecipanti, "eventi")
    )
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


def eliminata(evento: Evento) -> int:
    """A meeting deleted, when who deletes it chooses to tell (DEC-413): the email of a
    cancelled one, its link to the meetings, as the meeting's page is gone. Sent before
    deleting, while its invitees can still be read."""
    if not _da_annunciare(evento):
        return 0
    motivo = evento.motivo_annullamento or "è stata tolta dal calendario."
    return _invia(
        evento, "riunione_annullata", {"Quando": _quando(evento), "Motivo": motivo}, "/riunioni"
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
    dove = evento.dove()
    quando = _quando(evento) + (f", {dove}" if dove else "")
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
