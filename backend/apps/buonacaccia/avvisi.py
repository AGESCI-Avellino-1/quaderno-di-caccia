"""Emails about BuonaCaccia registrations. They carry deadlines the family and the staff
must meet for a registration already made, so they are always sent, like the
registration from the app (not an optional kind of DEC-157, DEC-168).

- to the family: the registration as soon as the staff records it, the release form to
  sign, reminders before its deadline (DEC-160);
- to the whole staff of the member's unit (the capigruppo when it has none): reminders
  before the 9-day deadline and the last day to cancel without losing the fee (DEC-158).

Reminders go 2 days before and on the day (DEC-168), each once.
"""

from collections import defaultdict
from datetime import date, timedelta

from django.conf import settings
from django.db.models import Q

from apps.anagrafica.models import Appartenenza, Persona
from apps.impostazioni.email import invia
from apps.organizzazione.models import Incarico, RuoloIncarico

from . import servizi
from .models import ATTIVE, IscrizioneBuonaCaccia, ModoLiberatoria

PREAVVISO = 2


def _email(persona: Persona) -> str:
    return persona.email or (persona.utente.email if persona.utente_id else "")


def indirizzi_famiglia(persona: Persona) -> list[str]:
    """The parents with parental responsibility, and the member when they have an
    account of their own (they answer the event form, DEC-161)."""
    chi = [
        t.tutore
        for t in persona.tutori.select_related("tutore__utente").filter(
            responsabilita_genitoriale=True
        )
    ]
    if persona.utente_id:
        chi.append(persona)
    indirizzi: list[str] = []
    for p in chi:
        email = _email(p)
        if email and email not in indirizzi:
            indirizzi.append(email)
    return indirizzi


def indirizzi_staff(persona: Persona) -> list[str]:
    """The staff of the member's unit; the capigruppo when the unit has none."""
    unita = Appartenenza.objects.attive().filter(persona=persona).values("unita_id")
    incarichi = Incarico.objects.attivi().filter(
        ruolo__in={RuoloIncarico.STAFF, RuoloIncarico.CAPO_UNITA}, unita_id__in=unita
    )
    if not incarichi.exists():
        incarichi = Incarico.objects.attivi().filter(ruolo=RuoloIncarico.CAPOGRUPPO)
    indirizzi: list[str] = []
    for incarico in incarichi.select_related("persona__utente"):
        email = _email(incarico.persona)
        if email and email not in indirizzi:
            indirizzi.append(email)
    return indirizzi


def _link(iscrizione: IscrizioneBuonaCaccia) -> str:
    return f"{settings.FRONTEND_URL}/eventi/{iscrizione.partecipazione.evento_id}"


def _invia(indirizzi: list[str], modello: str, valori: dict[str, str]) -> int:
    return invia(modello, valori, indirizzi)


def _cosa_serve(iscrizione: IscrizioneBuonaCaccia) -> list[str]:
    """What the family still has to do."""
    righe = []
    if servizi.liberatoria_mancante(iscrizione):
        if iscrizione.modo_liberatoria == ModoLiberatoria.APP:
            righe.append(
                "la liberatoria firmata dai genitori, da caricare nell'app entro il "
                f"{iscrizione.scadenza_della_liberatoria:%d/%m/%Y}"
            )
        else:
            righe.append(
                "la liberatoria firmata dai genitori, da consegnare allo staff entro il "
                f"{iscrizione.scadenza_della_liberatoria:%d/%m/%Y}"
            )
    if servizi.dettagli(iscrizione.partecipazione.evento).scheda and (
        servizi.risposte_mancanti(iscrizione) or not iscrizione.risposte_il
    ):
        righe.append("le risposte alla scheda dell'evento, nell'app")
    return righe


def iscritto(iscrizione: IscrizioneBuonaCaccia) -> int:
    persona = iscrizione.partecipazione.persona
    evento = iscrizione.partecipazione.evento
    righe = []
    serve = _cosa_serve(iscrizione)
    if serve:
        righe.append("Ci serve:\n" + "\n".join(f"- {r}" for r in serve))
    if iscrizione.quota_id:
        righe.append("Trovi nell'app anche la quota da versare al gruppo.")
    return _invia(
        indirizzi_famiglia(persona),
        "buonacaccia_iscrizione",
        {
            "Nome": persona.nome,
            "Evento": evento.titolo,
            "Data": f"{evento.inizio:%d/%m/%Y}",
            "Stato": iscrizione.get_stato_display().lower(),
            "Cosa serve": "\n\n".join(righe),
            "Link": _link(iscrizione),
        },
    )


def liberatoria_da_firmare(iscrizione: IscrizioneBuonaCaccia) -> int:
    persona = iscrizione.partecipazione.persona
    evento = iscrizione.partecipazione.evento
    return _invia(
        indirizzi_famiglia(persona),
        "liberatoria_da_firmare",
        {
            "Nome": persona.nome,
            "Evento": evento.titolo,
            "Scadenza": f"{iscrizione.scadenza_della_liberatoria:%d/%m/%Y}",
            "Link": _link(iscrizione),
        },
    )


def liberatoria_rigettata(iscrizione: IscrizioneBuonaCaccia) -> int:
    persona = iscrizione.partecipazione.persona
    evento = iscrizione.partecipazione.evento
    return _invia(
        indirizzi_famiglia(persona),
        "liberatoria_rigettata",
        {
            "Nome": persona.nome,
            "Evento": evento.titolo,
            "Motivo": iscrizione.motivo_rigetto,
            "Link": _link(iscrizione),
        },
    )


# --- Daily reminders ----------------------------------------------------------------------


def _passo(scadenza: date, oggi: date) -> str | None:
    """Which reminder is due: "2" in the two days before, "0" on the day."""
    if oggi == scadenza:
        return "0"
    if scadenza - timedelta(days=PREAVVISO) <= oggi < scadenza:
        return str(PREAVVISO)
    return None


def _manca_allo_staff(iscrizione: IscrizioneBuonaCaccia) -> list[str]:
    manca = []
    if not iscrizione.liberatoria_caricata_il or iscrizione.esito_liberatoria == "RIGETTATA":
        manca.append("caricare la liberatoria")
    if servizi.dettagli(iscrizione.partecipazione.evento).scheda and not (
        iscrizione.scheda_inviata_il
    ):
        manca.append("compilare la scheda")
    if not iscrizione.pagata_il:
        manca.append("pagare la quota")
    return manca


def promemoria(oggi: date) -> int:
    """One email per address, listing every registration with a deadline near."""
    allo_staff: dict[str, list[str]] = defaultdict(list)
    alla_famiglia: dict[str, list[str]] = defaultdict(list)
    inviati: list[tuple[IscrizioneBuonaCaccia, list[str]]] = []
    iscrizioni = IscrizioneBuonaCaccia.objects.filter(
        Q(stato__in=ATTIVE),
        partecipazione__evento__annullato_il__isnull=True,
        partecipazione__evento__inizio__date__gte=oggi,
    ).select_related("partecipazione__persona__utente", "partecipazione__evento")
    for iscrizione in iscrizioni:
        persona = iscrizione.partecipazione.persona
        evento = iscrizione.partecipazione.evento
        chi = f"{persona.cognome} {persona.nome}, {evento.titolo}"
        chiavi = []
        passo = _passo(iscrizione.scadenza, oggi)
        manca = _manca_allo_staff(iscrizione)
        if passo and manca and f"staff-scadenza-{passo}" not in iscrizione.promemoria:
            chiavi.append(f"staff-scadenza-{passo}")
            for indirizzo in indirizzi_staff(persona):
                allo_staff[indirizzo].append(
                    f"- {chi}: entro il {iscrizione.scadenza:%d/%m/%Y} su BuonaCaccia "
                    f"resta da {', '.join(manca)}"
                )
        passo = _passo(iscrizione.limite_cancellazione, oggi)
        if passo and f"staff-cancella-{passo}" not in iscrizione.promemoria:
            chiavi.append(f"staff-cancella-{passo}")
            for indirizzo in indirizzi_staff(persona):
                allo_staff[indirizzo].append(
                    f"- {chi}: il {iscrizione.limite_cancellazione:%d/%m/%Y} è l'ultimo "
                    "giorno per cancellare l'iscrizione senza perdere la quota"
                )
        passo = _passo(iscrizione.scadenza_della_liberatoria, oggi)
        serve = _cosa_serve(iscrizione)
        if (
            passo
            and servizi.liberatoria_mancante(iscrizione)
            and f"famiglia-{passo}" not in iscrizione.promemoria
        ):
            chiavi.append(f"famiglia-{passo}")
            for indirizzo in indirizzi_famiglia(persona):
                alla_famiglia[indirizzo].append(
                    f"Per {persona.nome} ({evento.titolo}, {_link(iscrizione)}) ci serve:\n"
                    + "\n".join(f"- {r}" for r in serve)
                )
        if chiavi:
            inviati.append((iscrizione, chiavi))
    quanti = 0
    for indirizzo, righe in allo_staff.items():
        quanti += _invia(
            [indirizzo],
            "buonacaccia_scadenze",
            {"Elenco": "\n".join(righe), "Link": f"{settings.FRONTEND_URL}/buonacaccia"},
        )
    for indirizzo, blocchi in alla_famiglia.items():
        quanti += _invia([indirizzo], "promemoria_liberatoria", {"Elenco": "\n\n".join(blocchi)})
    for iscrizione, chiavi in inviati:
        iscrizione.promemoria = {**iscrizione.promemoria, **{c: oggi.isoformat() for c in chiavi}}
        iscrizione.save(update_fields=["promemoria", "aggiornato_il"])
    return quanti
