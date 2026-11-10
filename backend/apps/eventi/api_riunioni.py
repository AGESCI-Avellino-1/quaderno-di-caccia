"""Meetings and the group's places (DEC-310). A meeting is stored as an `Evento` of type
RIUNIONE (attendance, calendar and the offline copy are those of the events), but it has
its own page: series or single, the uniform, the staff's notes, never a fee."""

from datetime import date, datetime, time

from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router, Schema
from ninja.errors import HttpError
from ninja.responses import Status
from ninja.throttling import AuthRateThrottle

from apps.impostazioni.html import in_testo, pulisci
from apps.organizzazione.models import Squadriglia, Unita
from apps.permessi import policy

from . import avvisi, indirizzi, servizi
from .api import EventoOut, LocalitaOut, _errore, _evento_out
from .models import (
    CERCHIE_CONVOCATE,
    Cerchia,
    Evento,
    Livello,
    Localita,
    Modalita,
    RiunioneRicorrente,
    TipoEvento,
)

router = Router(tags=["riunioni"])


# --- Places ---------------------------------------------------------------------------------


class LocalitaIn(Schema):
    nome: str
    denominazione: str = ""
    indirizzo: str = ""
    civico: str = ""
    mappa: str = ""


def _puo_usare_localita(user) -> bool:
    """Who creates meetings: the capi, a CSQ, a member a CSQ delegated."""
    return (
        policy.e_capo(user)
        or policy.squadriglie_guidate(user).exists()
        or bool(policy.squadriglie_delegate(user))
    )


class _LimiteIndirizzi(AuthRateThrottle):
    # Its own count: ninja shares one among all the throttles of the same scope.
    scope = "indirizzi"


class PropostaIndirizzo(Schema):
    nome: str
    indirizzo: str
    civico: str


@router.get(
    "/localita/cerca", response=list[PropostaIndirizzo], throttle=[_LimiteIndirizzi("60/m")]
)
def cerca_indirizzi(request, testo: str = ""):
    """Proposals while a place is written (DEC-360): only a help, never an error."""
    if not _puo_usare_localita(request.auth):
        raise HttpError(403, "Gli indirizzi li cerca chi crea le riunioni.")
    return indirizzi.cerca(testo)


@router.get("/localita", response=list[LocalitaOut])
def elenco_localita(request):
    if not _puo_usare_localita(request.auth):
        raise HttpError(403, "Le località le vede chi crea le riunioni.")
    return Localita.objects.filter(attiva=True)


def _nuova_localita(user, dati: LocalitaIn) -> Localita:
    nome = dati.nome.strip()
    if not nome:
        raise HttpError(400, "Scrivi il nome della località.")
    esistente = Localita.objects.filter(attiva=True, nome__iexact=nome).first()
    if esistente:
        return esistente
    localita = Localita(
        nome=nome,
        denominazione=dati.denominazione.strip(),
        indirizzo=dati.indirizzo.strip(),
        civico=dati.civico.strip(),
        mappa=dati.mappa.strip(),
        creata_da=user,
    )
    try:
        localita.full_clean()
    except ValidationError as errore:
        raise _errore(errore) from errore
    localita.save()
    return localita


@router.post("/localita", response={201: LocalitaOut})
def crea_localita(request, dati: LocalitaIn):
    """A new place enters the group's list at once; the capigruppo fix it (DEC-310)."""
    if not _puo_usare_localita(request.auth):
        raise HttpError(403, "Le località le aggiunge chi crea le riunioni.")
    return Status(201, _nuova_localita(request.auth, dati))


def _localita_del_gruppo(request, localita_id: int) -> Localita:
    if not policy.e_capogruppo(request.auth):
        raise HttpError(403, "Le località del gruppo le sistemano i capigruppo.")
    return get_object_or_404(Localita, pk=localita_id, attiva=True)


@router.put("/localita/{localita_id}", response=LocalitaOut)
def modifica_localita(request, localita_id: int, dati: LocalitaIn):
    localita = _localita_del_gruppo(request, localita_id)
    localita.nome = dati.nome.strip()
    localita.denominazione = dati.denominazione.strip()
    localita.indirizzo = dati.indirizzo.strip()
    localita.civico = dati.civico.strip()
    localita.mappa = dati.mappa.strip()
    try:
        localita.full_clean()
    except ValidationError as errore:
        raise _errore(errore) from errore
    localita.save()
    # The meetings to come show the new name.
    localita.eventi.filter(inizio__gte=timezone.now()).update(luogo=localita.nome_visibile)
    return localita


@router.delete("/localita/{localita_id}", response={204: None})
def togli_localita(request, localita_id: int):
    """Out of the list; meetings and events that used it keep its name."""
    localita = _localita_del_gruppo(request, localita_id)
    localita.attiva = False
    localita.save(update_fields=["attiva", "aggiornato_il"])
    return Status(204, None)


# --- Meetings ---------------------------------------------------------------------------------


class RiunioneIn(Schema):
    """A series (with `giorno_settimana`, `dal`, `al`) or a single meeting (`giorno`)."""

    titolo: str = ""
    cerchia: Cerchia = Cerchia.TUTTI
    unita: list[int] = []  # the first is the unit's; a second one meets with it
    # A meeting of the parents of the whole group, with no unit (DEC-325); the assembly always.
    di_gruppo: bool = False
    squadriglia_id: int | None = None
    ora_inizio: time
    ora_fine: time
    giorno: date | None = None
    giorno_settimana: int | None = None
    dal: date | None = None
    al: date | None = None
    localita_id: int | None = None
    nuova_localita: LocalitaIn | None = None
    uniforme: bool = True
    # In person, online or mixed, with the link (DEC-402).
    modalita: Modalita = Modalita.PRESENZA
    link: str = ""
    # Of a single meeting of the Co.Ca. or of the parents (DEC-362); in a series, written later
    # on each meeting.
    ordine_del_giorno: str = ""


class SerieOut(Schema):
    id: int
    titolo: str
    cerchia: Cerchia
    cerchia_nome: str
    unita: list[str]
    squadriglia: str | None
    giorno_settimana: int
    ora_inizio: time
    ora_fine: time
    dal: date
    al: date
    localita: LocalitaOut | None
    luogo: str
    uniforme: bool
    modalita: Modalita
    link: str
    puo_essere_online: bool
    riunioni: int
    puo_gestire: bool


def _serie_out(user, serie: RiunioneRicorrente) -> dict:
    return {
        "id": serie.pk,
        "titolo": servizi.titolo_riunione(serie),
        "cerchia": serie.cerchia,
        "cerchia_nome": serie.get_cerchia_display(),
        "unita": [str(u) for u in servizi.unita_della_serie(serie)],
        "squadriglia": serie.squadriglia.nome if serie.squadriglia_id else None,
        "giorno_settimana": serie.giorno_settimana,
        "ora_inizio": serie.ora_inizio,
        "ora_fine": serie.ora_fine,
        "dal": serie.dal,
        "al": serie.al,
        "localita": serie.localita,
        "luogo": serie.localita.nome_visibile if serie.localita_id else serie.luogo,
        "uniforme": serie.uniforme,
        "modalita": serie.modalita,
        "link": serie.link,
        "puo_essere_online": servizi.puo_essere_online(
            serie.cerchia, servizi.unita_della_serie(serie)
        ),
        "riunioni": serie.eventi.filter(annullato_il__isnull=True).count(),
        "puo_gestire": _puo_gestire_serie(user, serie),
    }


def _puo_creare(user, unita: list[Unita], squadriglia, cerchia: str, livello=None) -> bool:
    return policy.puo_creare_evento(
        user,
        livello or (Livello.SQUADRIGLIA if squadriglia else Livello.UNITA),
        unita_ids=[u.pk for u in unita],
        squadriglia=squadriglia,
        tipo=TipoEvento.RIUNIONE,
        cerchia=cerchia,
    )


def _puo_gestire_serie(user, serie: RiunioneRicorrente) -> bool:
    return _puo_creare(user, servizi.unita_della_serie(serie), serie.squadriglia, serie.cerchia)


def _localita(request, dati: RiunioneIn) -> Localita | None:
    if dati.modalita == Modalita.ONLINE:
        return None  # online there is only the link (DEC-402)
    if dati.nuova_localita and dati.nuova_localita.nome.strip():
        return _nuova_localita(request.auth, dati.nuova_localita)
    if dati.localita_id:
        return get_object_or_404(Localita, pk=dati.localita_id, attiva=True)
    return None


def _unita_e_squadriglia(dati: RiunioneIn) -> tuple[list[Unita], Squadriglia | None]:
    if dati.squadriglia_id:
        squadriglia = get_object_or_404(Squadriglia, pk=dati.squadriglia_id)
        return [squadriglia.unita], squadriglia
    per_id = Unita.objects.in_bulk(dati.unita)
    unita = [per_id[i] for i in dict.fromkeys(dati.unita) if i in per_id]
    if not unita:
        raise HttpError(400, "Scegli l'unità.")
    if dati.cerchia in (Cerchia.GENITORI, Cerchia.STAFF):
        # The parents of one or more units (DEC-325); the staffs of units chosen freely,
        # linked or not (DEC-401).
        return unita, None
    if len(unita) > 1:
        # Two units meet together only when linked (DEC-279).
        principale = unita[0]
        if len(unita) > 2 or principale.collegata_a_id != unita[1].pk:
            raise HttpError(400, "Una riunione si fa insieme solo con l'unità collegata.")
    return unita, None


def _con_ordine_del_giorno(evento: Evento, dati: RiunioneIn) -> Evento:
    from apps.verbali.servizi import scrivi_ordine_del_giorno

    if in_testo(dati.ordine_del_giorno).strip():
        scrivi_ordine_del_giorno(evento, dati.ordine_del_giorno)
    return evento


@router.post("/riunioni", response={201: list[EventoOut]})
def crea_riunioni(request, dati: RiunioneIn):
    if dati.cerchia in CERCHIE_CONVOCATE:
        return _crea_riunione_convocata(request, dati)
    if dati.di_gruppo:
        raise HttpError(400, "Solo una riunione dei genitori è di tutto il gruppo.")
    unita, squadriglia = _unita_e_squadriglia(dati)
    cerchia = Cerchia.TUTTI if squadriglia else dati.cerchia
    if not _puo_creare(request.auth, unita, squadriglia, cerchia):
        raise HttpError(403, "Non puoi creare questa riunione.")
    try:
        servizi.controlla_cerchia(cerchia, unita)
        servizi.controlla_modalita(dati.modalita, cerchia, unita)
    except ValidationError as errore:
        raise _errore(errore) from errore
    link = _link(dati)
    with transaction.atomic():
        localita = _localita(request, dati)
        if dati.giorno is not None:
            zona = timezone.get_current_timezone()
            evento = Evento(
                titolo=dati.titolo.strip() or _titolo_singola(unita, squadriglia, cerchia),
                tipo=TipoEvento.RIUNIONE,
                livello=Livello.SQUADRIGLIA if squadriglia else Livello.UNITA,
                squadriglia=squadriglia,
                cerchia=cerchia,
                inizio=datetime.combine(dati.giorno, dati.ora_inizio, zona),
                fine=datetime.combine(dati.giorno, dati.ora_fine, zona),
                luogo=localita.nome_visibile if localita else "",
                localita=localita,
                uniforme=dati.uniforme,
                modalita=dati.modalita,
                link=link,
            )
            try:
                if evento.fine <= evento.inizio:
                    raise ValidationError("L'ora di fine deve seguire quella di inizio.")
                creati = [servizi.crea(evento, [] if squadriglia else unita, request.auth)]
                _con_ordine_del_giorno(creati[0], dati)
            except ValidationError as errore:
                raise _errore(errore) from errore
        else:
            if dati.giorno_settimana is None or not dati.dal or not dati.al:
                raise HttpError(400, "Scegli il giorno della settimana e le date.")
            serie = RiunioneRicorrente(
                unita=unita[0],
                squadriglia=squadriglia,
                cerchia=cerchia,
                titolo=dati.titolo.strip(),
                giorno_settimana=dati.giorno_settimana,
                ora_inizio=dati.ora_inizio,
                ora_fine=dati.ora_fine,
                dal=dati.dal,
                al=dati.al,
                localita=localita,
                uniforme=dati.uniforme,
                modalita=dati.modalita,
                link=link,
                creata_da=request.auth,
            )
            try:
                serie.full_clean()
                serie.save()
                serie.unita_insieme.set(unita[1:])
                creati = servizi.genera_riunioni(serie, request.auth)
            except ValidationError as errore:
                raise _errore(errore) from errore
    return Status(201, [_evento_out(request.auth, e) for e in creati])


def _crea_riunione_convocata(request, dati: RiunioneIn):
    """The parents' meetings and the assembly, one at a time: each has its own convocation
    (DEC-325, DEC-326, DEC-327). Nobody is told until who manages it sends the convocation,
    once the attachments are there."""
    if dati.giorno is None:
        raise HttpError(400, "Questa riunione è una sola: scegli il giorno.")
    assemblea = dati.cerchia == Cerchia.SOCI
    di_gruppo = dati.di_gruppo or assemblea
    unita, _ = ([], None) if di_gruppo else _unita_e_squadriglia(dati)
    livello = Livello.GRUPPO if di_gruppo else Livello.UNITA
    if not _puo_creare(request.auth, unita, None, dati.cerchia, livello):
        raise HttpError(403, "Non puoi creare questa riunione.")
    try:
        servizi.controlla_modalita(dati.modalita, dati.cerchia, unita)
    except ValidationError as errore:
        raise _errore(errore) from errore
    titolo = "Assemblea dei soci" if assemblea else servizi.titolo_riunione_genitori(unita)
    zona = timezone.get_current_timezone()
    with transaction.atomic():
        localita = _localita(request, dati)
        evento = Evento(
            titolo=dati.titolo.strip() or titolo,
            tipo=TipoEvento.RIUNIONE,
            livello=livello,
            cerchia=dati.cerchia,
            inizio=datetime.combine(dati.giorno, dati.ora_inizio, zona),
            fine=datetime.combine(dati.giorno, dati.ora_fine, zona),
            luogo=localita.nome_visibile if localita else "",
            localita=localita,
            uniforme=False,
            modalita=dati.modalita,
            link=_link(dati),
        )
        try:
            if evento.fine <= evento.inizio:
                raise ValidationError("L'ora di fine deve seguire quella di inizio.")
            creata = _con_ordine_del_giorno(servizi.crea(evento, unita, request.auth), dati)
        except ValidationError as errore:
            raise _errore(errore) from errore
    return Status(201, [_evento_out(request.auth, creata)])


def _titolo_singola(unita: list[Unita], squadriglia, cerchia: str) -> str:
    serie = RiunioneRicorrente(unita=unita[0], squadriglia=squadriglia, cerchia=cerchia)
    return servizi.titolo_riunione(serie, unita)


def _link(dati) -> str:
    return dati.link.strip() if dati.modalita != Modalita.PRESENZA else ""


@router.get("/riunioni/serie", response=list[SerieOut])
def elenco_serie(request, unita: int | None = None):
    """The series, for who manages meetings: the capi, a CSQ for their patrol."""
    serie = RiunioneRicorrente.objects.select_related("unita", "squadriglia", "localita")
    if unita is not None:
        serie = serie.filter(unita_id=unita)
    serie = serie.filter(al__gte=timezone.localdate()).order_by("giorno_settimana", "ora_inizio")
    if policy.e_capo(request.auth):
        return [_serie_out(request.auth, s) for s in serie]
    return [_serie_out(request.auth, s) for s in serie if _puo_gestire_serie(request.auth, s)]


class SerieIn(Schema):
    uniforme: bool
    localita_id: int | None = None
    nuova_localita: LocalitaIn | None = None
    # None: as it is (an app not yet updated does not send them).
    modalita: Modalita | None = None
    link: str | None = None


def _serie(request, serie_id: int) -> RiunioneRicorrente:
    serie = get_object_or_404(RiunioneRicorrente, pk=serie_id)
    if not _puo_gestire_serie(request.auth, serie):
        raise HttpError(403, "Le riunioni le stabilisce lo staff dell'unità.")
    return serie


@router.put("/riunioni/serie/{serie_id}", response=SerieOut)
def modifica_serie(request, serie_id: int, dati: SerieIn):
    serie = _serie(request, serie_id)
    modalita = dati.modalita or serie.modalita
    link = serie.link if dati.link is None else dati.link
    try:
        servizi.controlla_modalita(modalita, serie.cerchia, servizi.unita_della_serie(serie))
        with transaction.atomic():
            localita = _localita(
                request,
                RiunioneIn(
                    ora_inizio=time(0),
                    ora_fine=time(0),
                    localita_id=dati.localita_id,
                    nuova_localita=dati.nuova_localita,
                    modalita=modalita,
                ),
            )
            servizi.cambia_serie(
                serie, uniforme=dati.uniforme, localita=localita, modalita=modalita, link=link
            )
    except ValidationError as errore:
        raise _errore(errore) from errore
    return _serie_out(request.auth, serie)


@router.delete("/riunioni/serie/{serie_id}", response=SerieOut)
def togli_serie(request, serie_id: int):
    """Cancels the meetings to come; past ones (with their attendance) stay. No email:
    the whole series goes, not one meeting."""
    serie = _serie(request, serie_id)
    for evento in serie.eventi.filter(inizio__gte=timezone.now(), annullato_il__isnull=True):
        servizi.annulla(evento, "Riunioni tolte")
    serie.al = max(min(serie.al, timezone.localdate()), serie.dal)
    serie.save()
    return _serie_out(request.auth, serie)


class ModificaRiunione(Schema):
    inizio: datetime
    fine: datetime
    localita_id: int | None = None
    nuova_localita: LocalitaIn | None = None
    luogo: str = ""
    # None: as its series.
    uniforme: bool | None = None
    informazioni: str = ""
    # None: as it is (an app not yet updated does not send them).
    modalita: Modalita | None = None
    link: str | None = None


@router.put("/riunioni/{evento_id}", response=EventoOut)
def modifica_riunione(request, evento_id: int, dati: ModificaRiunione):
    """One meeting: moved, another place, the uniform, the notes. Moving it (date, time,
    place) tells the invited (DEC-310); the notes and the uniform do not."""
    evento = get_object_or_404(
        policy.eventi_visibili(request.auth), pk=evento_id, tipo=TipoEvento.RIUNIONE
    )
    if not policy.puo_gestire_evento(request.auth, evento):
        raise HttpError(403, "Non puoi cambiare questa riunione.")
    prima = (evento.inizio, evento.fine, evento.luogo, evento.modalita, evento.link)
    modalita = dati.modalita or evento.modalita
    if modalita != evento.modalita:
        try:
            servizi.controlla_modalita(
                modalita, evento.cerchia, list(servizi.unita_coinvolte(evento))
            )
        except ValidationError as errore:
            raise _errore(errore) from errore
    with transaction.atomic():
        localita = _localita(
            request,
            RiunioneIn(
                ora_inizio=time(0),
                ora_fine=time(0),
                localita_id=dati.localita_id,
                nuova_localita=dati.nuova_localita,
                modalita=modalita,
            ),
        )
        evento.modalita = modalita
        if dati.link is not None:
            evento.link = dati.link.strip()
        if modalita == Modalita.PRESENZA:
            evento.link = ""
        evento.inizio, evento.fine = dati.inizio, dati.fine
        evento.localita = localita
        evento.luogo = localita.nome_visibile if localita else dati.luogo.strip()
        if modalita == Modalita.ONLINE:
            evento.luogo = ""
        if dati.uniforme is None and evento.riunione_id is None:
            raise HttpError(400, "Scegli se la riunione è con l'uniforme.")
        evento.uniforme = dati.uniforme
        evento.informazioni = pulisci(dati.informazioni) if dati.informazioni.strip() else ""
        try:
            evento.full_clean()
        except ValidationError as errore:
            raise _errore(errore) from errore
        evento.save()
        servizi.allinea_partecipanti(evento)
    if (evento.inizio, evento.fine, evento.luogo, evento.modalita, evento.link) != prima:
        transaction.on_commit(lambda: avvisi.modificato(evento))
    return _evento_out(request.auth, evento)
