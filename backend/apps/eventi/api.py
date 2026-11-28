"""Events, recurring meetings, participants and attendance (see models)."""

from datetime import date, datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router, Schema
from ninja.errors import HttpError
from ninja.responses import Status
from ninja.throttling import AnonRateThrottle

from apps.anagrafica.models import Persona
from apps.core.dataora import DataOra
from apps.organizzazione.animali import AnimaleBreve, breve
from apps.organizzazione.models import Branca, Squadriglia, Unita
from apps.permessi import policy

from . import avvisi, servizi, turni_gruppo
from .models import (
    Cerchia,
    Evento,
    Livello,
    Partecipazione,
    StatoPartecipazione,
    StatoPresenza,
    TipoEvento,
)

router = Router(tags=["eventi"])


def _errore(errore: ValidationError) -> HttpError:
    return HttpError(400, " ".join(errore.messages))


# --- Events ----------------------------------------------------------------------------------


class EventoIn(Schema):
    titolo: str
    tipo: TipoEvento
    livello: Livello
    branca: Branca | None = None
    unita: list[int] = []
    squadriglia_id: int | None = None
    inizio: DataOra
    fine: DataOra
    luogo: str = ""
    descrizione: str = ""
    # A patrol's mission: notes for the parents and the capi, not the ragazzi.
    note_genitori: str = ""
    cerchia: Cerchia = Cerchia.TUTTI
    # An Alta Squadriglia's: its antechamber invited too (DEC-439). None: as it is.
    anticamera: bool | None = None


class MiaPartecipazione(Schema):
    persona_id: int
    persona: str
    stato: StatoPartecipazione
    motivo: str
    puo_segnalare: bool


class RataIO(Schema):
    descrizione: str = ""
    importo: Decimal
    scadenza: date


class QuotaEvento(Schema):
    """The event's fee as everyone sees it (DEC-77): the instalments and the total."""

    nome: str
    rate: list[RataIO]
    totale: Decimal
    sconto_famiglia: Decimal
    # What the capi pay (DEC-428); None = nothing.
    importo_capi: Decimal | None = None


class LocalitaOut(Schema):
    id: int
    nome: str
    denominazione: str
    indirizzo: str
    civico: str
    indirizzo_completo: str
    mappa: str


class TurnoGruppoRiunione(Schema):
    turno: str
    unita: str


class TurnoOut(Schema):
    turno: str
    gruppo: str
    # The user's or their children's patrol or sestiglia.
    mio: bool
    cambiato: bool
    squadriglia_id: int | None
    sestiglia_id: int | None


class GruppoTurni(Schema):
    nome: str
    squadriglia_id: int | None
    sestiglia_id: int | None


class EventoOut(Schema):
    id: int
    titolo: str
    tipo: TipoEvento
    tipo_nome: str
    livello: Livello
    livello_nome: str
    branca: str
    unita: list[int]
    unita_nomi: list[str]
    # The type of an event on BuonaCaccia, in place of the units it has not (DEC-398).
    tipologia_bc: str = ""
    squadriglia_id: int | None
    squadriglia: str | None
    # Its image, next to the name (DEC-353).
    animale: AnimaleBreve | None = None
    inizio: datetime
    fine: datetime
    senza_ora_inizio: bool = False
    senza_ora_fine: bool = False
    luogo: str
    descrizione: str
    note_genitori: str | None  # None: not for this user
    cerchia: Cerchia
    cerchia_nome: str
    # An Alta Squadriglia's: its antechamber invited too (DEC-439).
    anticamera: bool = False
    riunione: bool
    # A meeting (DEC-310): its series, place, uniform and the staff's notes (HTML).
    serie_id: int | None = None
    localita: LocalitaOut | None = None
    uniforme: bool | None = None
    informazioni: str = ""
    # In person, online or mixed, and the link (DEC-402).
    modalita: str = "PRESENZA"
    link: str = ""
    puo_essere_online: bool = False
    # Whether the meeting has an agenda, read online from its own endpoint (DEC-365).
    con_ordine_del_giorno: bool = False
    # The turns of the meeting (DEC-312): all for the capi, one's own for the others.
    turni: list[TurnoOut] = []
    # The groups a turn may be given to, for who manages the turns.
    gruppi_turni: list[GruppoTurni] = []
    # The group's turns that fall on this meeting's unit (DEC-406): seen by all who see it.
    turni_gruppo: list[TurnoGruppoRiunione] = []
    annullato: bool
    motivo_annullamento: str
    # The user's own and their children's participation (families).
    mie: list[MiaPartecipazione]
    # The user's own, apart from what they only see (DEC-432).
    mio: bool = True
    puo_gestire: bool
    quota: QuotaEvento | None


def _mie(user, evento: Evento) -> list[dict]:
    persone = {p.pk for p in policy.tutelati(user)}
    propria = policy.persona_di(user)
    if propria is not None:
        persone.add(propria.pk)
    return [
        {
            "persona_id": p.persona_id,
            "persona": f"{p.persona.nome} {p.persona.cognome}",
            "stato": p.stato,
            "motivo": p.motivo,
            "puo_segnalare": policy.puo_segnalare_assenza(user, p.persona, evento),
        }
        for p in evento.partecipazioni.select_related("persona").filter(persona_id__in=persone)
    ]


def _evento_out(user, evento: Evento, cache: dict | None = None) -> dict:
    from apps.verbali.servizi import ha_ordine_del_giorno

    unita = list(servizi.unita_coinvolte(evento))
    return {
        "id": evento.pk,
        "titolo": evento.titolo,
        "tipo": evento.tipo,
        "tipo_nome": evento.get_tipo_display(),
        "livello": evento.livello,
        "livello_nome": evento.get_livello_display(),
        "branca": evento.branca,
        "unita": [u.pk for u in unita],
        "unita_nomi": [str(u) for u in unita],
        "tipologia_bc": (
            str(evento.buonacaccia.tipologia)
            if evento.livello == Livello.ESTERNO and hasattr(evento, "buonacaccia")
            else ""
        ),
        "squadriglia_id": evento.squadriglia_id,
        "squadriglia": evento.squadriglia.nome if evento.squadriglia_id else None,
        "animale": breve(evento.squadriglia.animale) if evento.squadriglia_id else None,
        "inizio": evento.inizio,
        "fine": evento.fine,
        "senza_ora_inizio": evento.senza_ora_inizio,
        "senza_ora_fine": evento.senza_ora_fine,
        "luogo": evento.luogo,
        "descrizione": evento.descrizione,
        "note_genitori": (
            evento.note_genitori if policy.vede_note_genitori(user, evento) else None
        ),
        "cerchia": evento.cerchia,
        "cerchia_nome": evento.get_cerchia_display(),
        "anticamera": evento.anticamera,
        "riunione": evento.riunione_id is not None,
        "serie_id": evento.riunione_id,
        "localita": evento.localita,
        "uniforme": evento.con_uniforme(),
        "informazioni": evento.informazioni,
        "modalita": evento.modalita,
        "link": evento.link,
        "puo_essere_online": (
            evento.tipo == TipoEvento.RIUNIONE and servizi.puo_essere_online(evento.cerchia, unita)
        ),
        "con_ordine_del_giorno": ha_ordine_del_giorno(evento),
        "turni": _turni_out(user, evento, cache),
        "gruppi_turni": _gruppi_turni(user, evento, cache),
        "turni_gruppo": turni_gruppo.turni_della_riunione(evento, cache),
        "annullato": evento.annullato_il is not None,
        "motivo_annullamento": evento.motivo_annullamento,
        "mie": _mie(user, evento),
        "mio": evento.pk
        in (cache["miei"] if cache and "miei" in cache else servizi.miei(user, [evento])),
        "puo_gestire": policy.puo_gestire_evento(user, evento),
        "quota": _quota_evento(evento),
    }


def _turni_out(user, evento: Evento, cache: dict | None = None) -> list[dict]:
    from apps.organizzazione.models import Squadriglia

    from . import turni

    if evento.tipo != TipoEvento.RIUNIONE:
        return []
    cache = {} if cache is None else cache
    assegnati = turni.assegnazioni(evento, cache=cache)
    if not assegnati:
        return []

    def persone():
        ids = [p.pk for p in policy.tutelati(user) if policy.genitori_vedono(p, "scheda")]
        propria = policy.persona_di(user)
        return [*ids, propria.pk] if propria is not None else ids

    giorno = timezone.localdate(evento.inizio)
    ids = turni._in_cache(cache, "persone", persone)
    miei = turni._in_cache(cache, ("miei", giorno), lambda: turni.gruppi_di(ids, giorno))
    tutti = turni._in_cache(cache, "capo", lambda: policy.e_capo(user))
    risultato = []
    for a in assegnati:
        gruppo = a["gruppo"]
        mio = turni.chiave(gruppo) in miei
        if not (tutti or mio):
            continue
        squadriglia = isinstance(gruppo, Squadriglia)
        risultato.append(
            {
                "turno": a["turno"],
                "gruppo": turni.nome_gruppo(gruppo),
                "mio": mio,
                "cambiato": a["cambiato"],
                "squadriglia_id": gruppo.pk if squadriglia else None,
                "sestiglia_id": None if squadriglia else gruppo.pk,
            }
        )
    return risultato


def _gruppi_turni(user, evento: Evento, cache: dict | None = None) -> list[dict]:
    from apps.organizzazione.models import Squadriglia

    from . import turni

    if evento.tipo != TipoEvento.RIUNIONE:
        return []
    cache = {} if cache is None else cache
    conf = turni.configurazione(evento, cache)
    if conf is None or not turni._in_cache(
        cache, ("gestisce", conf.pk), lambda: policy.puo_gestire_turni(user, conf.unita)
    ):
        return []
    return [
        {
            "nome": str(g),
            "squadriglia_id": g.pk if isinstance(g, Squadriglia) else None,
            "sestiglia_id": None if isinstance(g, Squadriglia) else g.pk,
        }
        for g in turni._in_cache(cache, ("gruppi", conf.pk), lambda: turni.gruppi(conf))
    ]


def _quota_evento(evento: Evento) -> dict | None:
    tipo = getattr(evento, "quota", None)
    if tipo is None:
        return None
    return {
        "nome": tipo.nome,
        "rate": tipo.rate_ordinate(),
        "totale": tipo.importo,
        "sconto_famiglia": tipo.sconto_famiglia,
        "importo_capi": tipo.importo_capi,
    }


def _evento(request, evento_id: int) -> Evento:
    return get_object_or_404(policy.eventi_visibili(request.auth), pk=evento_id)


@router.get("/eventi", response=list[EventoOut])
def eventi(
    request,
    dal: date | None = None,
    al: date | None = None,
    unita: int | None = None,
    riunioni: bool = False,
):
    """The events; with `riunioni` the meetings instead, which are not events for who uses
    the app (DEC-310)."""
    elenco = policy.eventi_visibili(request.auth).select_related(
        "squadriglia__animale", "localita", "riunione", "buonacaccia__tipologia"
    )
    if riunioni:
        elenco = elenco.filter(tipo=TipoEvento.RIUNIONE)
    else:
        elenco = elenco.exclude(tipo=TipoEvento.RIUNIONE)
    if dal:
        elenco = elenco.filter(fine__date__gte=dal)
    if al:
        elenco = elenco.filter(inizio__date__lte=al)
    risultato = []
    elenco = list(elenco.order_by("inizio").prefetch_related("unita"))
    cache: dict = {"miei": servizi.miei(request.auth, elenco)}
    for evento in elenco:
        if unita is not None and unita not in servizi.unita_coinvolte(evento).values_list(
            "pk", flat=True
        ):
            continue
        risultato.append(_evento_out(request.auth, evento, cache))
    return risultato


def _dati(request, evento: Evento, dati: EventoIn) -> list[Unita]:
    unita = list(Unita.objects.filter(pk__in=dati.unita))
    squadriglia = (
        get_object_or_404(Squadriglia, pk=dati.squadriglia_id) if dati.squadriglia_id else None
    )
    if not policy.puo_creare_evento(
        request.auth,
        dati.livello,
        unita_ids=[u.pk for u in unita],
        branca=dati.branca or "",
        squadriglia=squadriglia,
        tipo=dati.tipo,
        cerchia=dati.cerchia,
    ):
        raise HttpError(403, "Non puoi creare questo evento.")
    if TipoEvento.RIUNIONE in (dati.tipo, evento.tipo):
        raise HttpError(400, "Le riunioni si creano e si cambiano dalla pagina Riunioni.")
    evento.titolo = dati.titolo.strip()
    evento.tipo = dati.tipo
    evento.livello = dati.livello
    evento.branca = dati.branca or "" if dati.livello == Livello.BRANCA else ""
    evento.squadriglia = squadriglia if dati.livello == Livello.SQUADRIGLIA else None
    evento.inizio = dati.inizio
    evento.fine = dati.fine
    evento.luogo = dati.luogo.strip()
    evento.descrizione = dati.descrizione.strip()
    evento.note_genitori = dati.note_genitori.strip() if dati.tipo == TipoEvento.MISSIONE else ""
    evento.cerchia = dati.cerchia if dati.livello == Livello.UNITA else Cerchia.TUTTI
    if dati.anticamera is not None:
        evento.anticamera = dati.anticamera
    evento.anticamera = evento.anticamera and evento.cerchia == Cerchia.ALTA_SQUADRIGLIA
    return unita


@router.post("/eventi", response={201: EventoOut})
def crea_evento(request, dati: EventoIn):
    evento = Evento()
    unita = _dati(request, evento, dati)
    try:
        servizi.crea(evento, unita, request.auth)
    except ValidationError as errore:
        raise _errore(errore) from errore
    transaction.on_commit(lambda: avvisi.nuovo(evento))
    return Status(201, _evento_out(request.auth, evento))


@router.put("/eventi/{evento_id}", response=EventoOut)
def modifica_evento(request, evento_id: int, dati: EventoIn):
    evento = _evento(request, evento_id)
    if not policy.puo_gestire_evento(request.auth, evento):
        raise HttpError(403, "Non puoi modificare questo evento.")
    if (dati.livello, dati.branca or "", dati.squadriglia_id, dati.cerchia) != (
        evento.livello,
        evento.branca,
        evento.squadriglia_id,
        evento.cerchia,
    ):
        raise HttpError(400, "Il livello dell'evento non si cambia: creane uno nuovo.")
    prima = (evento.inizio, evento.fine, evento.luogo)
    anticamera = evento.anticamera
    unita = _dati(request, evento, dati)
    try:
        evento.full_clean()
    except ValidationError as errore:
        raise _errore(errore) from errore
    evento.save()
    if evento.livello == Livello.UNITA and unita:
        evento.unita.set(unita)
    servizi.allinea_partecipanti(evento)
    if anticamera != evento.anticamera:
        from .allineamento import programma

        # The antechamber left out: its invitations go (DEC-414, DEC-439).
        programma(*evento.unita.values_list("pk", flat=True))
    if (evento.inizio, evento.fine, evento.luogo) != prima:
        transaction.on_commit(lambda: avvisi.modificato(evento))
    return _evento_out(request.auth, evento)


class Motivo(Schema):
    motivo: str


@router.post("/eventi/{evento_id}/annulla", response=EventoOut)
def annulla_evento(request, evento_id: int, dati: Motivo):
    evento = _evento(request, evento_id)
    if not policy.puo_gestire_evento(request.auth, evento):
        raise HttpError(403, "Non puoi annullare questo evento.")
    try:
        servizi.annulla(evento, dati.motivo)
    except ValidationError as errore:
        raise _errore(errore) from errore
    transaction.on_commit(lambda: avvisi.annullato(evento))
    return _evento_out(request.auth, evento)


# --- Participants and attendance ------------------------------------------------------------


class PartecipanteOut(Schema):
    persona_id: int
    cognome: str
    nome: str
    stato: StatoPartecipazione
    motivo: str
    presenza: StatoPresenza | None


class DettaglioOut(EventoOut):
    partecipanti: list[PartecipanteOut]
    puo_presenze: bool
    # The participants' medical forms (DEC-195).
    puo_stampare_schede: bool = False
    puo_non_invitare: bool
    # Of people chosen one by one, who is invited (DEC-430).
    puo_scegliere: bool = False
    # A meeting deleted for good, and what goes with it (DEC-413).
    puo_eliminare: bool = False
    si_perde: list[str] = []


def _dettaglio(utente, evento: Evento) -> dict:
    servizi.allinea_partecipanti(evento)
    partecipanti = []
    if policy.puo_vedere_partecipanti(utente, evento):
        presenze = dict(evento.presenze.values_list("persona_id", "stato"))
        partecipanti = [
            {
                "persona_id": p.persona_id,
                "cognome": p.persona.cognome,
                "nome": p.persona.nome,
                "stato": p.stato,
                "motivo": p.motivo,
                "presenza": presenze.get(p.persona_id),
            }
            for p in evento.partecipazioni.select_related("persona").order_by(
                "persona__cognome", "persona__nome"
            )
        ]
    return {
        **_evento_out(utente, evento),
        "partecipanti": partecipanti,
        "puo_presenze": policy.puo_segnare_presenze(utente, evento),
        "puo_stampare_schede": policy.puo_stampare_schede_evento(utente, evento),
        "puo_non_invitare": policy.puo_non_invitare(utente, evento),
        "puo_scegliere": evento.cerchia == Cerchia.SCELTI
        and policy.puo_gestire_evento(utente, evento),
        **(
            {"puo_eliminare": True, "si_perde": servizi.cosa_si_perde(evento)}
            if policy.puo_eliminare_riunione(utente, evento)
            else {}
        ),
    }


def _partecipazione(evento: Evento, persona_id: int) -> Partecipazione:
    return get_object_or_404(Partecipazione, evento=evento, persona_id=persona_id)


class Partecipa(Schema):
    partecipa: bool


@router.post("/eventi/{evento_id}/partecipanti/{persona_id}/partecipa", response=EventoOut)
def partecipa(request, evento_id: int, persona_id: int, dati: Partecipa):
    """The family says whether the member takes part."""
    evento = _evento(request, evento_id)
    persona = get_object_or_404(Persona, pk=persona_id)
    if not policy.puo_segnalare_assenza(request.auth, persona, evento):
        raise HttpError(403, "Non puoi cambiare la partecipazione di questa persona.")
    try:
        servizi.non_partecipa(_partecipazione(evento, persona_id), request.auth, not dati.partecipa)
    except ValidationError as errore:
        raise _errore(errore) from errore
    return _evento_out(request.auth, evento)


@router.post("/eventi/{evento_id}/partecipanti/{persona_id}/non-invitare", response=DettaglioOut)
def non_invitare(request, evento_id: int, persona_id: int, dati: Motivo):
    evento = _evento(request, evento_id)
    if not policy.puo_non_invitare(request.auth, evento):
        raise HttpError(403, "Lo decide lo staff dell'evento (la Co.Ca. per gli eventi di gruppo).")
    try:
        servizi.non_invitare(_partecipazione(evento, persona_id), request.auth, dati.motivo)
    except ValidationError as errore:
        raise _errore(errore) from errore
    return _dettaglio(request.auth, evento)


@router.post("/eventi/{evento_id}/partecipanti/{persona_id}/reinvita", response=DettaglioOut)
def reinvita(request, evento_id: int, persona_id: int):
    evento = _evento(request, evento_id)
    if not policy.puo_non_invitare(request.auth, evento):
        raise HttpError(403, "Lo decide lo staff dell'evento (la Co.Ca. per gli eventi di gruppo).")
    servizi.reinvita(_partecipazione(evento, persona_id), request.auth)
    return _dettaglio(request.auth, evento)


class Segno(Schema):
    persona_id: int
    stato: StatoPresenza


class PresenzeIn(Schema):
    segni: list[Segno]


class PresenzeOut(Schema):
    segnate: int


@router.put("/eventi/{evento_id}/presenze", response=PresenzeOut)
def presenze(request, evento_id: int, dati: PresenzeIn):
    """Also offline (queued, DEC-95, DEC-96): one record per member, the last wins."""
    evento = _evento(request, evento_id)
    if not policy.puo_segnare_presenze(request.auth, evento):
        raise HttpError(403, "Le presenze le segnano i capi.")
    try:
        segnate = servizi.segna_presenze(
            evento, {s.persona_id: s.stato for s in dati.segni}, request.auth
        )
    except ValidationError as errore:
        raise _errore(errore) from errore
    return {"segnate": segnate}


@router.get("/eventi/{evento_id}", response=DettaglioOut)
def dettaglio_evento(request, evento_id: int):
    return _dettaglio(request.auth, _evento(request, evento_id))


@router.get("/eventi/{evento_id}/foglio-presenze.pdf")
def foglio_presenze(request, evento_id: int):
    """A list to fill in by hand when the phone is not at hand, to copy later (DEC-78)."""
    from .stampa import foglio

    evento = _evento(request, evento_id)
    if not policy.puo_segnare_presenze(request.auth, evento):
        raise HttpError(403, "Le presenze le segnano i capi.")
    servizi.allinea_partecipanti(evento)
    risposta = HttpResponse(foglio(evento), content_type="application/pdf")
    risposta["Content-Disposition"] = f'attachment; filename="presenze-{evento.pk}.pdf"'
    return risposta


# --- Patrol delegate and Alta Squadriglia ------------------------------------------------


class DelegaIn(Schema):
    persona_id: int


class DelegaOut(Schema):
    persona_id: int | None
    persona: str | None
    puo_delegare: bool


def _delega_out(user, squadriglia) -> dict:
    attuale = servizi.delegato(squadriglia)
    return {
        "persona_id": attuale.persona_id if attuale else None,
        "persona": f"{attuale.persona.nome} {attuale.persona.cognome}" if attuale else None,
        "puo_delegare": policy.puo_delegare(user, squadriglia),
    }


@router.get("/squadriglie/{squadriglia_id}/delega", response=DelegaOut)
def delega(request, squadriglia_id: int):
    squadriglia = get_object_or_404(Squadriglia, pk=squadriglia_id)
    if not (
        policy.puo_delegare(request.auth, squadriglia)
        or policy.squadriglie_di(request.auth).filter(pk=squadriglia.pk).exists()
    ):
        raise HttpError(404, "Squadriglia non trovata.")
    return _delega_out(request.auth, squadriglia)


@router.put("/squadriglie/{squadriglia_id}/delega", response=DelegaOut)
def delega_a(request, squadriglia_id: int, dati: DelegaIn):
    """The member who may create the patrol's meetings besides the CSQ."""
    squadriglia = get_object_or_404(Squadriglia, pk=squadriglia_id)
    if not policy.puo_delegare(request.auth, squadriglia):
        raise HttpError(403, "La delega la dà il capo squadriglia.")
    try:
        servizi.delega(squadriglia, get_object_or_404(Persona, pk=dati.persona_id), request.auth)
    except ValidationError as errore:
        raise _errore(errore) from errore
    return _delega_out(request.auth, squadriglia)


@router.delete("/squadriglie/{squadriglia_id}/delega", response=DelegaOut)
def revoca_delega(request, squadriglia_id: int):
    squadriglia = get_object_or_404(Squadriglia, pk=squadriglia_id)
    if not policy.puo_delegare(request.auth, squadriglia):
        raise HttpError(403, "La delega la revoca il capo squadriglia.")
    servizi.revoca(squadriglia)
    return _delega_out(request.auth, squadriglia)


class MembroAltaOut(Schema):
    id: int
    persona_id: int
    nome: str
    cognome: str
    unita: str
    # None: in the antechamber since `in_anticamera_dal`.
    dal: date | None
    in_anticamera_dal: date | None
    al: date | None


class AltaSquadrigliaOut(Schema):
    """The Alta Squadriglia of a reparto, shared with the linked one (DEC-439)."""

    entrati: list[MembroAltaOut]
    anticamera: list[MembroAltaOut]
    # Who was in and is out: the history, last first.
    usciti: list[MembroAltaOut]
    # The reparto's ragazzi/e not in nor in the antechamber.
    candidati: list[MembroAltaOut]
    puo_scegliere: bool
    # The entry ceremony in the book, if written and the book is on.
    cerimonia: int | None


class PersoneAltaIn(Schema):
    persone: list[int]
    # For the entry: that day (today if none).
    data: date | None = None


def _reparto_alta(request, unita_id: int, scrivere: bool = False) -> Unita:
    if not policy.e_capo(request.auth):
        raise HttpError(403, "L'Alta Squadriglia la vedono i capi.")
    reparto = get_object_or_404(Unita, pk=unita_id)
    if scrivere and not policy.puo_scegliere_alta_squadriglia(request.auth, reparto):
        raise HttpError(403, "L'Alta Squadriglia la sceglie lo staff del reparto.")
    return reparto


def _membro_out(membro, unita: dict) -> dict:
    return {
        **_candidato_out(membro.persona, unita),
        "id": membro.pk,
        "dal": membro.data_inizio,
        "in_anticamera_dal": membro.in_anticamera_dal,
        "al": membro.data_fine,
    }


def _candidato_out(persona: Persona, unita: dict) -> dict:
    return {
        "id": 0,
        "persona_id": persona.pk,
        "nome": persona.nome,
        "cognome": persona.cognome,
        "unita": unita.get(persona.pk, ""),
        "dal": None,
        "in_anticamera_dal": None,
        "al": None,
    }


@router.get("/unita/{unita_id}/alta-squadriglia", response=AltaSquadrigliaOut)
def alta_squadriglia(request, unita_id: int):
    from apps.anagrafica.servizi import unita_delle_persone
    from apps.cerimonie.servizi import cerimonia_ingresso

    from .models import MembroAltaSquadriglia

    reparto = _reparto_alta(request, unita_id)
    membri = list(MembroAltaSquadriglia.objects.dell_alta(reparto).select_related("persona"))
    aperti = [m for m in membri if m.data_fine is None]
    dentro = {m.persona_id for m in aperti}
    candidati = list(
        servizi.ragazzi_per_alta(reparto).exclude(pk__in=dentro).order_by("cognome", "nome")
    )
    unita = unita_delle_persone([m.persona for m in membri] + candidati)
    per_nome = lambda m: (m.persona.cognome, m.persona.nome)  # noqa: E731
    return {
        "entrati": [_membro_out(m, unita) for m in sorted(aperti, key=per_nome) if m.data_inizio],
        "anticamera": [
            _membro_out(m, unita) for m in sorted(aperti, key=per_nome) if not m.data_inizio
        ],
        "usciti": [
            _membro_out(m, unita)
            for m in sorted(
                (m for m in membri if m.data_fine), key=lambda m: m.data_fine, reverse=True
            )
        ],
        "candidati": [_candidato_out(p, unita) for p in candidati],
        "puo_scegliere": policy.puo_scegliere_alta_squadriglia(request.auth, reparto),
        "cerimonia": cerimonia_ingresso(reparto),
    }


def _persone_alta(dati: PersoneAltaIn) -> list[Persona]:
    persone = list(Persona.objects.filter(pk__in=dati.persone))
    if not persone:
        raise HttpError(400, "Scegli almeno un ragazzo o una ragazza.")
    return persone


@router.post("/unita/{unita_id}/alta-squadriglia/anticamera", response=AltaSquadrigliaOut)
def metti_in_anticamera(request, unita_id: int, dati: PersoneAltaIn):
    reparto = _reparto_alta(request, unita_id, scrivere=True)
    try:
        servizi.metti_in_anticamera(reparto, _persone_alta(dati))
    except ValidationError as errore:
        raise _errore(errore) from errore
    return alta_squadriglia(request, unita_id)


@router.post("/unita/{unita_id}/alta-squadriglia/ingresso", response=AltaSquadrigliaOut)
def fai_entrare(request, unita_id: int, dati: PersoneAltaIn):
    """In from a day, from the antechamber or directly (DEC-439)."""
    reparto = _reparto_alta(request, unita_id, scrivere=True)
    try:
        servizi.fai_entrare(reparto, _persone_alta(dati), dati.data or date.today())
    except ValidationError as errore:
        raise _errore(errore) from errore
    return alta_squadriglia(request, unita_id)


def _membro_alta(request, unita_id: int, membro_id: int):
    from .models import MembroAltaSquadriglia

    reparto = _reparto_alta(request, unita_id, scrivere=True)
    return get_object_or_404(
        MembroAltaSquadriglia.objects.dell_alta(reparto), pk=membro_id, data_fine__isnull=True
    )


@router.post(
    "/unita/{unita_id}/alta-squadriglia/{membro_id}/anticamera", response=AltaSquadrigliaOut
)
def rimetti_in_anticamera(request, unita_id: int, membro_id: int):
    servizi.rimetti_in_anticamera(_membro_alta(request, unita_id, membro_id))
    return alta_squadriglia(request, unita_id)


@router.delete("/unita/{unita_id}/alta-squadriglia/{membro_id}", response=AltaSquadrigliaOut)
def togli_dall_alta(request, unita_id: int, membro_id: int):
    servizi.togli_dall_alta(_membro_alta(request, unita_id, membro_id))
    return alta_squadriglia(request, unita_id)


# --- The event's fee, also in instalments (DEC-77) -----------------------------------------


class QuotaEventoIn(Schema):
    nome: str = ""
    rate: list[RataIO]
    sconto_famiglia: Decimal = Decimal("0")
    # What the capi pay (DEC-428); None or 0 = nothing.
    importo_capi: Decimal | None = None


def _gestore_quote(request, evento: Evento) -> None:
    if policy.e_capo_in_attesa(request.auth) or not policy.puo_gestire_evento(request.auth, evento):
        raise HttpError(403, "La quota la fissano i capi dell'evento.")
    if evento.tipo == TipoEvento.RIUNIONE:
        raise HttpError(400, "Le riunioni non hanno quote né budget.")


@router.put("/eventi/{evento_id}/quota", response=EventoOut)
def fissa_quota(request, evento_id: int, dati: QuotaEventoIn):
    """Fees already issued keep their amount; a new instalment is issued to everyone,
    an instalment taken away withdraws the unpaid fees."""
    from django.db import transaction

    from apps.core.anno import AnnoAssociativo
    from apps.quote import servizi as quote
    from apps.quote.models import CategoriaQuota, Destinatari, Quota, TipoQuota

    evento = _evento(request, evento_id)
    _gestore_quote(request, evento)
    tipo = getattr(evento, "quota", None) or TipoQuota(
        evento=evento,
        categoria=CategoriaQuota.EVENTO,
        destinatari=Destinatari.TUTTI,
        anno=AnnoAssociativo.da_data(timezone.localdate(evento.inizio)).anno_fine,
    )
    tipo.nome = dati.nome.strip() or f"Quota {evento.titolo}"[:120]
    tipo.rate = [
        {
            "descrizione": r.descrizione.strip(),
            "importo": str(r.importo),
            "scadenza": r.scadenza.isoformat(),
        }
        for r in dati.rate
    ]
    tipo.importo = sum((r.importo for r in dati.rate), Decimal("0"))
    tipo.sconto_famiglia = dati.sconto_famiglia
    importo_capi_prima = tipo.importo_capi
    tipo.importo_capi = dati.importo_capi or None
    try:
        tipo.full_clean()
    except ValidationError as errore:
        raise _errore(errore) from errore
    with transaction.atomic():
        tipo.save()
        scadenze = {r.scadenza for r in dati.rate}
        for tolta in Quota.objects.valide().filter(tipo=tipo).exclude(periodo__in=scadenze):
            if not tolta.pagato:
                quote.annulla_quota(tolta, request.auth, "Rata tolta dall'evento")
        quote.emetti_evento(tipo)
        quote.allinea_quote_capi(tipo, request.auth, importo_capi_prima)
        quote.allinea_quote_evento(evento)
    evento.refresh_from_db()
    return _evento_out(request.auth, evento)


class QuotaPersona(Schema):
    quota_id: int
    descrizione: str
    scadenza: date
    importo: Decimal
    dovuto: Decimal
    pagato: Decimal
    residuo: Decimal
    annullata: bool


class SituazioneQuote(Schema):
    persona_id: int
    persona: str
    quote: list[QuotaPersona]


@router.get("/eventi/{evento_id}/quote", response=list[SituazioneQuote])
def quote_evento(request, evento_id: int):
    """Who paid what: the event's managers and the Co.Ca. (DEC-92)."""
    from apps.quote.models import Quota

    evento = _evento(request, evento_id)
    if not (policy.puo_gestire_evento(request.auth, evento) or policy.e_capo_censito(request.auth)):
        raise HttpError(403, "Le quote dell'evento le vedono i capi.")
    tipo = getattr(evento, "quota", None)
    if tipo is None:
        return []
    righe: dict[int, dict] = {}
    for q in Quota.objects.filter(tipo=tipo).select_related("persona", "tipo", "agevolazione"):
        riga = righe.setdefault(
            q.persona_id,
            {
                "persona_id": q.persona_id,
                "persona": f"{q.persona.cognome} {q.persona.nome}",
                "quote": [],
            },
        )
        riga["quote"].append(
            {
                "quota_id": q.pk,
                "descrizione": q.descrizione,
                "scadenza": q.scadenza,
                "importo": q.importo,
                "dovuto": q.dovuto,
                "pagato": q.pagato,
                "residuo": q.residuo,
                "annullata": q.annullata_il is not None,
            }
        )
    return sorted(righe.values(), key=lambda r: r["persona"])


class ImportoIn(Schema):
    importo: Decimal


@router.put("/eventi/{evento_id}/quote/{quota_id}", response=QuotaPersona)
def importo_persona(request, evento_id: int, quota_id: int, dati: ImportoIn):
    """DEC-77: one person's amount, down to zero."""
    from apps.quote import servizi as quote
    from apps.quote.models import Quota

    evento = _evento(request, evento_id)
    _gestore_quote(request, evento)
    q = get_object_or_404(Quota, pk=quota_id, tipo__evento=evento)
    try:
        quote.imposta_importo(q, dati.importo)
    except ValidationError as errore:
        raise _errore(errore) from errore
    return {
        "quota_id": q.pk,
        "descrizione": q.descrizione,
        "scadenza": q.scadenza,
        "importo": q.importo,
        "dovuto": q.dovuto,
        "pagato": q.pagato,
        "residuo": q.residuo,
        "annullata": q.annullata_il is not None,
    }


# --- Personal calendar (DEC-79) ---------------------------------------------------------


class VistaCalendario(Schema):
    vista: str
    nome: str
    url: str


class CalendarioOut(Schema):
    url: str
    # A capo's three views (DEC-143); empty for everyone else.
    viste: list[VistaCalendario]
    # Whether the page shows the birthdays: ragazzi/e and capi (DEC-417).
    compleanni: bool


def _calendario_out(request, calendario) -> dict:
    from django.conf import settings

    from .calendario import VISTE

    base = f"{settings.FRONTEND_URL}/api/v1/calendario/{calendario.token}.ics"
    viste = (
        [{"vista": v, "nome": n, "url": f"{base}?vista={v}"} for v, n in VISTE.items()]
        if policy.e_capo(request.auth)
        else []
    )
    return {"url": base, "viste": viste, "compleanni": policy.riceve_compleanni(request.auth)}


@router.get("/calendario", response=CalendarioOut)
def mio_calendario(request):
    """The secret address to add to Google Calendar or the iPhone Calendar."""
    from .models import CalendarioPersonale

    calendario, _ = CalendarioPersonale.objects.get_or_create(utente=request.auth)
    return _calendario_out(request, calendario)


@router.post("/calendario/rigenera", response=CalendarioOut)
def rigenera_calendario(request):
    """A new address: the old one stops working (e.g. it was shared by mistake)."""
    from .models import CalendarioPersonale

    calendario, _ = CalendarioPersonale.objects.get_or_create(utente=request.auth)
    calendario.rigenera()
    return _calendario_out(request, calendario)


class EventoCalendario(Schema):
    id: int
    titolo: str
    tipo_nome: str
    inizio: datetime
    fine: datetime
    senza_ora_inizio: bool
    senza_ora_fine: bool
    luogo: str
    annullato: bool
    # The user's own, apart from what they only see (DEC-432).
    mio: bool


def _vista(vista: str) -> str:
    from .calendario import VISTE

    if vista not in VISTE:
        raise HttpError(400, "Vista del calendario sconosciuta.")
    return vista


@router.get("/calendario/eventi", response=list[EventoCalendario])
def eventi_del_mio_calendario(
    request, vista: str = "unita", dal: date | None = None, al: date | None = None
):
    """The calendar page (DEC-286): the same events as the personal feed, by view for a
    capo (DEC-143), as a month or as a list of the next ones."""
    from .calendario import eventi_del_calendario

    elenco = eventi_del_calendario(request.auth, _vista(vista))
    if dal:
        elenco = elenco.filter(fine__date__gte=dal)
    if al:
        elenco = elenco.filter(inizio__date__lte=al)
    elenco = list(elenco)
    miei = servizi.miei(request.auth, elenco)
    return [
        {
            "id": e.pk,
            "titolo": e.titolo,
            "tipo_nome": e.get_tipo_display(),
            "inizio": e.inizio,
            "fine": e.fine,
            "senza_ora_inizio": e.senza_ora_inizio,
            "senza_ora_fine": e.senza_ora_fine,
            "luogo": e.luogo or ("Online" if e.modalita == "ONLINE" else ""),
            "annullato": e.annullato_il is not None,
            "mio": e.pk in miei,
        }
        for e in elenco
    ]


class CompleannoOut(Schema):
    persona_id: int
    nome: str
    cognome: str
    giorno: date
    anni: int
    unita: str
    # In the Co.Ca.: shown apart to the capi.
    coca: bool
    # Whether the name may link to the personal file (DEC-314).
    scheda: bool


GIORNI_COMPLEANNI = 30
# A month's grid is six weeks at most.
MASSIMO_GIORNI_COMPLEANNI = 42


@router.get("/calendario/compleanni", response=list[CompleannoOut])
def compleanni_del_calendario(request, dal: date | None = None, al: date | None = None):
    """The next birthdays (DEC-417): from today for 30 days by default, or a month's grid.
    Not in the iCal feed."""
    from datetime import timedelta

    from apps.anagrafica.compleanni import compleanni_tra, unita_e_coca

    dal = dal or timezone.localdate()
    al = al or dal + timedelta(days=GIORNI_COMPLEANNI - 1)
    if al < dal or (al - dal).days >= MASSIMO_GIORNI_COMPLEANNI:
        raise HttpError(400, "Scegli al massimo sei settimane di compleanni.")
    elenco = compleanni_tra(policy.compleanni_visibili(request.auth), dal, al)
    unita, coca = unita_e_coca({c.persona.pk for c in elenco})
    capo = policy.e_capo(request.auth)
    return [
        {
            "persona_id": c.persona.pk,
            "nome": c.persona.nome,
            "cognome": c.persona.cognome,
            "giorno": c.giorno,
            "anni": c.anni,
            "unita": unita.get(c.persona.pk, ""),
            "coca": capo and c.persona.pk in coca,
            "scheda": policy.scheda_apribile(request, c.persona.pk),
        }
        for c in elenco
    ]


def _file_ics(eventi, nome: str) -> HttpResponse:
    from .calendario import ics

    risposta = HttpResponse(ics(eventi), content_type="text/calendar; charset=utf-8")
    risposta["Content-Disposition"] = f'attachment; filename="{nome}"'
    risposta["Cache-Control"] = "no-store"
    return risposta


@router.get("/calendario.ics")
def scarica_mio_calendario(request, vista: str = "unita"):
    """The calendar as a file, once, for who does not subscribe (DEC-286)."""
    from .calendario import eventi_del_calendario

    return _file_ics(eventi_del_calendario(request.auth, _vista(vista)), "calendario.ics")


@router.get("/eventi/{evento_id}/evento.ics")
def scarica_evento(request, evento_id: int):
    """One event as a file, to add it to the phone's calendar (DEC-286)."""
    return _file_ics([_evento(request, evento_id)], f"evento-{evento_id}.ics")


# Calendar apps check every few hours; guessing a 43-character token is hopeless.
LIMITI_CALENDARIO = [AnonRateThrottle("120/h")]


@router.get("/calendario/{token}.ics", auth=None, throttle=LIMITI_CALENDARIO)
def feed_calendario(request, token: str, vista: str = "unita"):
    from .calendario import eventi_del_calendario, ics
    from .models import CalendarioPersonale

    calendario = CalendarioPersonale.objects.filter(token=token).select_related("utente").first()
    if calendario is None or not calendario.utente.is_active:
        raise HttpError(404, "Calendario non trovato.")
    risposta = HttpResponse(
        ics(eventi_del_calendario(calendario.utente, vista)),
        content_type="text/calendar; charset=utf-8",
    )
    risposta["Cache-Control"] = "private, max-age=900"
    return risposta


# --- Budget and accounts (DEC-90, DEC-91) ---------------------------------------------------


class BudgetIn(Schema):
    quota: Decimal | None = None
    contributo: Decimal | None = None
    totale: Decimal | None = None
    quota_staff: Decimal = Decimal("0")


class BudgetOut(Schema):
    partecipanti: int
    staff: int
    quota_staff: Decimal
    quota: Decimal | None
    contributo: Decimal
    totale: Decimal
    calcolato: str


class RendicontoOut(Schema):
    budget: BudgetOut | None
    entrate: Decimal
    uscite: Decimal
    saldo: Decimal
    quote_dovute: Decimal
    quote_incassate: Decimal
    agevolazioni: Decimal
    puo_gestire: bool


def _rendiconto(request, evento: Evento) -> dict:
    return {
        "budget": servizi.budget(evento),
        **servizi.rendiconto(evento),
        "puo_gestire": policy.puo_gestire_evento(request.auth, evento),
    }


@router.get("/eventi/{evento_id}/rendiconto", response=RendicontoOut)
def rendiconto(request, evento_id: int):
    """The event's capi and the Co.Ca. (the money of the group is the Co.Ca.'s)."""
    evento = _evento(request, evento_id)
    if not (policy.puo_gestire_evento(request.auth, evento) or policy.e_capo_censito(request.auth)):
        raise HttpError(403, "Budget e rendiconto li vedono i capi.")
    return _rendiconto(request, evento)


@router.put("/eventi/{evento_id}/budget", response=RendicontoOut)
def fissa_budget(request, evento_id: int, dati: BudgetIn):
    evento = _evento(request, evento_id)
    _gestore_quote(request, evento)
    try:
        servizi.fissa_budget(evento, dati.quota, dati.contributo, dati.totale, dati.quota_staff)
    except ValidationError as errore:
        raise _errore(errore) from errore
    return _rendiconto(request, evento)
