"""Events, recurring meetings, participants and attendance (see models)."""

from datetime import date, datetime, time
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
from apps.organizzazione.models import Branca, Squadriglia, Unita
from apps.permessi import policy

from . import avvisi, servizi
from .models import (
    Cerchia,
    Evento,
    Livello,
    Partecipazione,
    RiunioneRicorrente,
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
    inizio: datetime
    fine: datetime
    luogo: str = ""
    descrizione: str = ""
    # A patrol's mission: notes for the parents and the capi, not the ragazzi.
    note_genitori: str = ""
    cerchia: Cerchia = Cerchia.TUTTI


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
    squadriglia_id: int | None
    squadriglia: str | None
    inizio: datetime
    fine: datetime
    luogo: str
    descrizione: str
    note_genitori: str | None  # None: not for this user
    cerchia: Cerchia
    cerchia_nome: str
    riunione: bool
    annullato: bool
    motivo_annullamento: str
    # The user's own and their children's participation (families).
    mie: list[MiaPartecipazione]
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


def _evento_out(user, evento: Evento) -> dict:
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
        "squadriglia_id": evento.squadriglia_id,
        "squadriglia": evento.squadriglia.nome if evento.squadriglia_id else None,
        "inizio": evento.inizio,
        "fine": evento.fine,
        "luogo": evento.luogo,
        "descrizione": evento.descrizione,
        "note_genitori": (
            evento.note_genitori if policy.vede_note_genitori(user, evento) else None
        ),
        "cerchia": evento.cerchia,
        "cerchia_nome": evento.get_cerchia_display(),
        "riunione": evento.riunione_id is not None,
        "annullato": evento.annullato_il is not None,
        "motivo_annullamento": evento.motivo_annullamento,
        "mie": _mie(user, evento),
        "puo_gestire": policy.puo_gestire_evento(user, evento),
        "quota": _quota_evento(evento),
    }


def _quota_evento(evento: Evento) -> dict | None:
    tipo = getattr(evento, "quota", None)
    if tipo is None:
        return None
    return {
        "nome": tipo.nome,
        "rate": tipo.rate_ordinate(),
        "totale": tipo.importo,
        "sconto_famiglia": tipo.sconto_famiglia,
    }


def _evento(request, evento_id: int) -> Evento:
    return get_object_or_404(policy.eventi_visibili(request.auth), pk=evento_id)


@router.get("/eventi", response=list[EventoOut])
def eventi(request, dal: date | None = None, al: date | None = None, unita: int | None = None):
    elenco = policy.eventi_visibili(request.auth).select_related("squadriglia")
    if dal:
        elenco = elenco.filter(fine__date__gte=dal)
    if al:
        elenco = elenco.filter(inizio__date__lte=al)
    risultato = []
    for evento in elenco.order_by("inizio"):
        if unita is not None and unita not in servizi.unita_coinvolte(evento).values_list(
            "pk", flat=True
        ):
            continue
        risultato.append(_evento_out(request.auth, evento))
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
    unita = _dati(request, evento, dati)
    try:
        evento.full_clean()
    except ValidationError as errore:
        raise _errore(errore) from errore
    evento.save()
    if evento.livello == Livello.UNITA and unita:
        evento.unita.set(unita)
    servizi.allinea_partecipanti(evento)
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
    puo_non_invitare: bool


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
        "puo_non_invitare": policy.puo_non_invitare(utente, evento),
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


# --- Recurring meetings -------------------------------------------------------------------


class RiunioneIn(Schema):
    giorno_settimana: int
    ora_inizio: time
    ora_fine: time
    luogo: str = ""
    dal: date
    al: date


class RiunioneOut(RiunioneIn):
    id: int
    riunioni: int


def _riunione_out(r: RiunioneRicorrente) -> dict:
    return {
        "id": r.pk,
        "giorno_settimana": r.giorno_settimana,
        "ora_inizio": r.ora_inizio,
        "ora_fine": r.ora_fine,
        "luogo": r.luogo,
        "dal": r.dal,
        "al": r.al,
        "riunioni": r.eventi.filter(annullato_il__isnull=True).count(),
    }


@router.get("/unita/{unita_id}/riunioni", response=list[RiunioneOut])
def riunioni(request, unita_id: int):
    if not policy.e_capo(request.auth):
        raise HttpError(403, "Le riunioni le vedono i capi.")
    unita = get_object_or_404(Unita, pk=unita_id)
    return [_riunione_out(r) for r in unita.riunioni_ricorrenti.all()]


@router.post("/unita/{unita_id}/riunioni", response={201: RiunioneOut})
def crea_riunioni(request, unita_id: int, dati: RiunioneIn):
    unita = get_object_or_404(Unita, pk=unita_id)
    if not policy.puo_creare_evento(request.auth, Livello.UNITA, unita_ids=[unita.pk]):
        raise HttpError(403, "Le riunioni le stabilisce lo staff dell'unità.")
    riunione = RiunioneRicorrente(unita=unita, creata_da=request.auth, **dati.dict())
    riunione.luogo = riunione.luogo.strip()
    try:
        riunione.full_clean()
        riunione.save()
        servizi.genera_riunioni(riunione, request.auth)
    except ValidationError as errore:
        raise _errore(errore) from errore
    return Status(201, _riunione_out(riunione))


@router.delete("/riunioni/{riunione_id}", response=RiunioneOut)
def togli_riunioni(request, riunione_id: int):
    """Cancels the future dates; past ones (with their attendance) stay."""
    riunione = get_object_or_404(RiunioneRicorrente, pk=riunione_id)
    if not policy.puo_creare_evento(request.auth, Livello.UNITA, unita_ids=[riunione.unita_id]):
        raise HttpError(403, "Le riunioni le stabilisce lo staff dell'unità.")
    for evento in riunione.eventi.filter(inizio__gte=timezone.now(), annullato_il__isnull=True):
        servizi.annulla(evento, "Riunioni ricorrenti tolte")
    riunione.al = min(riunione.al, timezone.localdate())
    riunione.save()
    return _riunione_out(riunione)


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


class AltaSquadrigliaIn(Schema):
    anno: int
    persone: list[int]


class AltaSquadrigliaOut(Schema):
    anno: int
    persone: list[int]
    puo_scegliere: bool


@router.get("/unita/{unita_id}/alta-squadriglia", response=AltaSquadrigliaOut)
def alta_squadriglia(request, unita_id: int, anno: int | None = None):
    from apps.core.anno import AnnoAssociativo

    from .models import MembroAltaSquadriglia

    if not policy.e_capo(request.auth):
        raise HttpError(403, "L'Alta Squadriglia la vedono i capi.")
    reparto = get_object_or_404(Unita, pk=unita_id)
    anno = anno or AnnoAssociativo.corrente().anno_fine
    return {
        "anno": anno,
        "persone": list(
            MembroAltaSquadriglia.objects.filter(reparto=reparto, anno=anno).values_list(
                "persona_id", flat=True
            )
        ),
        "puo_scegliere": policy.puo_scegliere_alta_squadriglia(request.auth, reparto),
    }


@router.put("/unita/{unita_id}/alta-squadriglia", response=AltaSquadrigliaOut)
def scegli_alta_squadriglia(request, unita_id: int, dati: AltaSquadrigliaIn):
    reparto = get_object_or_404(Unita, pk=unita_id)
    if not policy.puo_scegliere_alta_squadriglia(request.auth, reparto):
        raise HttpError(403, "L'Alta Squadriglia la sceglie lo staff del reparto.")
    persone = list(Persona.objects.filter(pk__in=dati.persone))
    try:
        servizi.imposta_alta_squadriglia(reparto, dati.anno, persone)
    except ValidationError as errore:
        raise _errore(errore) from errore
    return alta_squadriglia(request, unita_id, dati.anno)


# --- The event's fee, also in instalments (DEC-77) -----------------------------------------


class QuotaEventoIn(Schema):
    nome: str = ""
    rate: list[RataIO]
    sconto_famiglia: Decimal = Decimal("0")


def _gestore_quote(request, evento: Evento) -> None:
    if policy.e_capo_in_attesa(request.auth) or not policy.puo_gestire_evento(request.auth, evento):
        raise HttpError(403, "La quota la fissano i capi dell'evento.")


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


def _calendario_out(request, calendario) -> dict:
    from django.conf import settings

    from .calendario import VISTE

    base = f"{settings.FRONTEND_URL}/api/v1/calendario/{calendario.token}.ics"
    viste = (
        [{"vista": v, "nome": n, "url": f"{base}?vista={v}"} for v, n in VISTE.items()]
        if policy.e_capo(request.auth)
        else []
    )
    return {"url": base, "viste": viste}


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
