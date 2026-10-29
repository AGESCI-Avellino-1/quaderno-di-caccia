"""Cash book (see models). Every endpoint asks the policy."""

from datetime import date, datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from ninja import Router, Schema
from ninja.errors import HttpError
from ninja.responses import Status

from apps.anagrafica.models import Persona
from apps.core.anno import AnnoAssociativo
from apps.organizzazione.models import Unita
from apps.permessi import policy

from . import servizi
from .catalogo import catalogo
from .models import Cassa, Movimento, SpesaAnticipata, TipoCassa, TipoMovimento, VerificaCassa

router = Router(tags=["cassa"])


def _errore(errore: ValidationError) -> HttpError:
    return HttpError(400, " ".join(errore.messages))


def _anno(anno: int | None) -> AnnoAssociativo:
    return AnnoAssociativo(anno) if anno else AnnoAssociativo.corrente()


def _nome_utente(utente) -> str | None:
    persona = getattr(utente, "persona", None) if utente else None
    return f"{persona.nome} {persona.cognome}" if persona else None


def _visibili(user):
    """Movements the user may see: all for the Co.Ca., their units' for an R/S
    treasurer (DEC-92 style: the money of others is the Co.Ca.'s business)."""
    unita = policy.unita_cassa_visibili(user)
    movimenti = Movimento.objects.all()
    return movimenti if unita is None else movimenti.filter(unita_id__in=unita)


def _guardia(request) -> None:
    if not policy.puo_vedere_cassa(request.auth):
        raise HttpError(403, "La prima nota la vedono la Co.Ca. e i tesorieri.")


# --- Categories --------------------------------------------------------------------------------


class VoceOut(Schema):
    id: str
    lato: str
    riga: str
    titolo_riga: str
    nome: str


@router.get("/voci-modello-d", response=list[VoceOut])
def voci(request):
    _guardia(request)
    return [v.__dict__ for v in catalogo().voci]


# --- Cash boxes ------------------------------------------------------------------------------


class CassaIn(Schema):
    nome: str
    tipo: TipoCassa
    unita_id: int | None = None
    saldo_iniziale: Decimal
    data_saldo_iniziale: date
    attiva: bool = True


class CassaOut(Schema):
    id: int
    nome: str
    tipo: TipoCassa
    unita_id: int | None
    saldo_iniziale: Decimal
    data_saldo_iniziale: date
    attiva: bool
    saldo: Decimal | None  # hidden from an R/S treasurer on the shared bank account
    puo_registrare: bool
    senza_giustificativo: int


def _cassa_out(user, cassa: Cassa) -> dict:
    tutto = policy.unita_cassa_visibili(user) is None
    return {
        "id": cassa.pk,
        "nome": cassa.nome,
        "tipo": cassa.tipo,
        "unita_id": cassa.unita_id,
        "saldo_iniziale": cassa.saldo_iniziale,
        "data_saldo_iniziale": cassa.data_saldo_iniziale,
        "attiva": cassa.attiva,
        "saldo": cassa.saldo() if tutto or cassa.unita_id else None,
        "puo_registrare": policy.puo_registrare_in_cassa(user, cassa),
        "senza_giustificativo": sum(
            1
            for m in _visibili(user).filter(cassa=cassa, tipo=TipoMovimento.USCITA)
            if m.senza_giustificativo and not hasattr(m, "storno")
        ),
    }


def _casse_visibili(user):
    unita = policy.unita_cassa_visibili(user)
    casse = Cassa.objects.all()
    if unita is None:
        return casse
    return casse.filter(unita_id__in=unita) | casse.filter(tipo=TipoCassa.BANCA)


@router.get("/casse", response=list[CassaOut])
def casse(request):
    _guardia(request)
    return [_cassa_out(request.auth, c) for c in _casse_visibili(request.auth)]


def _salva_cassa(request, cassa: Cassa, dati: CassaIn) -> dict:
    if not policy.puo_gestire_casse(request.auth):
        raise HttpError(403, "Le casse le configurano i capigruppo e il tesoriere di gruppo.")
    if (
        cassa.pk
        and cassa.movimenti.exists()
        and (
            cassa.saldo_iniziale != dati.saldo_iniziale
            or cassa.data_saldo_iniziale != dati.data_saldo_iniziale
        )
    ):
        raise HttpError(400, "Il saldo iniziale non si cambia dopo i primi movimenti.")
    cassa.nome = dati.nome.strip()
    cassa.tipo = dati.tipo
    cassa.unita = get_object_or_404(Unita, pk=dati.unita_id) if dati.unita_id else None
    cassa.saldo_iniziale = dati.saldo_iniziale
    cassa.data_saldo_iniziale = dati.data_saldo_iniziale
    cassa.attiva = dati.attiva
    try:
        cassa.full_clean()
    except ValidationError as errore:
        raise _errore(errore) from errore
    cassa.save()
    return _cassa_out(request.auth, cassa)


@router.post("/casse", response={201: CassaOut})
def crea_cassa(request, dati: CassaIn):
    return Status(201, _salva_cassa(request, Cassa(), dati))


@router.put("/casse/{cassa_id}", response=CassaOut)
def modifica_cassa(request, cassa_id: int, dati: CassaIn):
    return _salva_cassa(request, get_object_or_404(Cassa, pk=cassa_id), dati)


# --- Movements ---------------------------------------------------------------------------------


class MovimentoIn(Schema):
    cassa_id: int
    tipo: TipoMovimento
    data: date
    importo: Decimal
    descrizione: str
    voce_id: str = ""
    unita_id: int | None = None
    cassa_destinazione_id: int | None = None
    evento_id: int | None = None
    # Base64 (optionally a data: URL), so the record can wait in the offline queue.
    giustificativo: str = ""


class MovimentoOut(Schema):
    id: int
    cassa_id: int
    cassa: str
    tipo: TipoMovimento
    tipo_nome: str
    data: date
    importo: Decimal
    effetto: Decimal
    descrizione: str
    voce_riga: str
    voce_nome: str
    unita_id: int | None
    cassa_destinazione: str | None
    ha_giustificativo: bool
    senza_giustificativo: bool
    storno_di: int | None
    stornato: bool
    motivo_storno: str
    da_quote: bool
    evento_id: int | None
    evento: str | None
    registrato_da: str | None
    creato_il: datetime


def _movimento_out(m: Movimento) -> dict:
    return {
        "id": m.pk,
        "cassa_id": m.cassa_id,
        "cassa": m.cassa.nome,
        "tipo": m.tipo,
        "tipo_nome": m.get_tipo_display(),
        "data": m.data,
        "importo": m.importo,
        "effetto": m.effetto,
        "descrizione": m.descrizione,
        "voce_riga": m.voce_riga,
        "voce_nome": m.voce_nome,
        "unita_id": m.unita_id,
        "cassa_destinazione": m.cassa_destinazione.nome if m.cassa_destinazione else None,
        "ha_giustificativo": bool(m.giustificativo),
        "senza_giustificativo": m.senza_giustificativo and not hasattr(m, "storno"),
        "storno_di": m.storno_di_id,
        "stornato": hasattr(m, "storno"),
        "motivo_storno": m.motivo_storno,
        "da_quote": m.pagamento_id is not None,
        "evento_id": m.evento_id,
        "evento": m.evento.titolo if m.evento_id else None,
        "registrato_da": _nome_utente(m.registrato_da),
        "creato_il": m.creato_il,
    }


@router.get("/movimenti", response=list[MovimentoOut])
def movimenti(request, cassa: int | None = None, anno: int | None = None, unita: int | None = None):
    _guardia(request)
    periodo = _anno(anno)
    elenco = _visibili(request.auth).filter(data__gte=periodo.inizio, data__lte=periodo.fine)
    if cassa is not None:
        elenco = elenco.filter(cassa_id=cassa) | elenco.filter(cassa_destinazione_id=cassa)
    if unita is not None:
        elenco = elenco.filter(unita_id=unita)
    elenco = elenco.select_related(
        "cassa", "cassa_destinazione", "registrato_da__persona", "evento"
    )
    return [_movimento_out(m) for m in elenco.order_by("-data", "-pk")]


@router.post("/movimenti", response={201: MovimentoOut})
def registra_movimento(request, dati: MovimentoIn):
    """Also offline (queued with an Idempotency-Key, DEC-96)."""
    utente = request.auth
    cassa = get_object_or_404(Cassa, pk=dati.cassa_id)
    unita_id = cassa.unita_id if cassa.tipo == TipoCassa.CONTANTI else dati.unita_id
    if not policy.puo_registrare_in_cassa(utente, cassa) or not (
        policy.puo_registrare_movimenti(utente, unita_id)
    ):
        raise HttpError(403, "Non puoi registrare movimenti su questa cassa per questa unità.")
    evento = None
    if dati.evento_id is not None:
        evento = get_object_or_404(policy.eventi_visibili(utente), pk=dati.evento_id)
    destinazione = None
    if dati.cassa_destinazione_id:
        destinazione = get_object_or_404(Cassa, pk=dati.cassa_destinazione_id)
        if not policy.puo_registrare_in_cassa(utente, destinazione):
            raise HttpError(403, "Non puoi versare in quella cassa.")
    try:
        movimento = servizi.registra(
            cassa=cassa,
            tipo=dati.tipo,
            data=dati.data,
            importo=dati.importo,
            descrizione=dati.descrizione,
            voce_id=dati.voce_id,
            unita=Unita.objects.filter(pk=unita_id).first() if unita_id else None,
            cassa_destinazione=destinazione,
            giustificativo=servizi.giustificativo_da_testo(dati.giustificativo),
            evento=evento,
            utente=utente,
        )
    except ValidationError as errore:
        raise _errore(errore) from errore
    return Status(201, _movimento_out(movimento))


def _movimento(request, movimento_id: int) -> Movimento:
    _guardia(request)
    return get_object_or_404(_visibili(request.auth), pk=movimento_id)


class Motivo(Schema):
    motivo: str


@router.post("/movimenti/{movimento_id}/storno", response=MovimentoOut)
def storna(request, movimento_id: int, dati: Motivo):
    movimento = _movimento(request, movimento_id)
    if not policy.puo_registrare_movimenti(request.auth, movimento.unita_id):
        raise HttpError(403, "Non puoi stornare questo movimento.")
    if movimento.pagamento_id and not movimento.pagamento.annullato_il:
        raise HttpError(400, "È l'incasso di un pagamento di quote: annulla il pagamento.")
    try:
        return _movimento_out(servizi.storna(movimento, request.auth, dati.motivo))
    except ValidationError as errore:
        raise _errore(errore) from errore


class Giustificativo(Schema):
    giustificativo: str


@router.post("/movimenti/{movimento_id}/giustificativo", response=MovimentoOut)
def aggiungi_giustificativo(request, movimento_id: int, dati: Giustificativo):
    """The photo may come later; once there, it stays (it is part of the record)."""
    movimento = _movimento(request, movimento_id)
    if not policy.puo_registrare_movimenti(request.auth, movimento.unita_id):
        raise HttpError(403, "Non puoi modificare questo movimento.")
    if movimento.giustificativo:
        raise HttpError(400, "Il movimento ha già il suo giustificativo.")
    try:
        movimento.giustificativo = servizi.giustificativo_da_testo(dati.giustificativo)
    except ValidationError as errore:
        raise _errore(errore) from errore
    movimento.save(update_fields=["giustificativo", "aggiornato_il"])
    return _movimento_out(movimento)


def _file(campo):
    if not campo:
        raise HttpError(404, "Nessun giustificativo.")
    return FileResponse(campo.open("rb"), filename=campo.name.rsplit("/", 1)[-1])


@router.get("/movimenti/{movimento_id}/giustificativo")
def giustificativo(request, movimento_id: int):
    return _file(_movimento(request, movimento_id).giustificativo)


# --- Cash checks (DEC-11) ----------------------------------------------------------------------


class VerificaIn(Schema):
    data: date
    saldo_contato: Decimal
    motivo: str = ""


class VerificaOut(Schema):
    id: int
    data: date
    saldo_contato: Decimal
    saldo_app: Decimal
    differenza: Decimal
    motivo: str
    registrata_da: str | None


def _verifica_out(v: VerificaCassa) -> dict:
    return {
        "id": v.pk,
        "data": v.data,
        "saldo_contato": v.saldo_contato,
        "saldo_app": v.saldo_app,
        "differenza": v.differenza,
        "motivo": v.motivo,
        "registrata_da": _nome_utente(v.registrata_da),
    }


def _cassa_verificabile(request, cassa_id: int) -> Cassa:
    cassa = get_object_or_404(Cassa, pk=cassa_id)
    if cassa.unita_id is None and not policy.puo_gestire_casse(request.auth):
        raise HttpError(403, "Il conto del gruppo lo verificano capigruppo e tesoriere di gruppo.")
    if not policy.puo_registrare_in_cassa(request.auth, cassa):
        raise HttpError(403, "La verifica la fanno il tesoriere o il capo unità.")
    return cassa


@router.get("/casse/{cassa_id}/verifiche", response=list[VerificaOut])
def verifiche(request, cassa_id: int):
    _guardia(request)
    cassa = get_object_or_404(_casse_visibili(request.auth), pk=cassa_id)
    return [_verifica_out(v) for v in cassa.verifiche.select_related("registrata_da__persona")]


@router.post("/casse/{cassa_id}/verifiche", response={201: VerificaOut})
def verifica(request, cassa_id: int, dati: VerificaIn):
    cassa = _cassa_verificabile(request, cassa_id)
    try:
        esito = servizi.verifica(
            cassa,
            data=dati.data,
            saldo_contato=dati.saldo_contato,
            motivo=dati.motivo,
            utente=request.auth,
        )
    except ValidationError as errore:
        raise _errore(errore) from errore
    return Status(201, _verifica_out(esito))


# --- Expenses paid by a capo (DEC-86) ----------------------------------------------------------


class SpesaIn(Schema):
    capo_id: int | None = None  # default: the user
    data: date
    importo: Decimal
    descrizione: str
    unita_id: int | None = None
    giustificativo: str = ""


class SpesaOut(Schema):
    id: int
    capo_id: int
    capo: str
    data: date
    importo: Decimal
    descrizione: str
    unita_id: int | None
    ha_giustificativo: bool
    stato: str  # da_rimborsare, rimborsata, respinta
    rimborsata_il: date | None
    motivo_rifiuto: str
    puo_rimborsare: bool


def _spesa_out(user, s: SpesaAnticipata) -> dict:
    stato = "rimborsata" if s.rimborso_id else "respinta" if s.respinta_il else "da_rimborsare"
    return {
        "id": s.pk,
        "capo_id": s.capo_id,
        "capo": f"{s.capo.nome} {s.capo.cognome}",
        "data": s.data,
        "importo": s.importo,
        "descrizione": s.descrizione,
        "unita_id": s.unita_id,
        "ha_giustificativo": bool(s.giustificativo),
        "stato": stato,
        "rimborsata_il": s.rimborso.data if s.rimborso_id else None,
        "motivo_rifiuto": s.motivo_rifiuto,
        "puo_rimborsare": stato == "da_rimborsare"
        and policy.puo_registrare_movimenti(user, s.unita_id),
    }


def _spese_visibili(user):
    spese = SpesaAnticipata.objects.select_related("capo", "rimborso")
    if policy.unita_cassa_visibili(user) is None and policy.e_capo_censito(user):
        return spese  # the Co.Ca.
    propria = policy.persona_di(user)
    return spese.filter(capo=propria) if propria else spese.none()


@router.get("/spese-anticipate", response=list[SpesaOut])
def spese_anticipate(request):
    return [_spesa_out(request.auth, s) for s in _spese_visibili(request.auth)]


@router.post("/spese-anticipate", response={201: SpesaOut})
def registra_spesa(request, dati: SpesaIn):
    utente = request.auth
    capo = (
        get_object_or_404(Persona, pk=dati.capo_id) if dati.capo_id else policy.persona_di(utente)
    )
    if capo is None or not policy.puo_registrare_spesa_anticipata(utente, capo):
        raise HttpError(403, "Le spese anticipate le registra il capo che le ha pagate.")
    if dati.data > date.today():
        raise HttpError(400, "La data non può essere nel futuro.")
    if dati.importo <= 0:
        raise HttpError(400, "L'importo deve essere positivo.")
    try:
        file = servizi.giustificativo_da_testo(dati.giustificativo)
    except ValidationError as errore:
        raise _errore(errore) from errore
    spesa = SpesaAnticipata(
        capo=capo,
        data=dati.data,
        importo=dati.importo,
        descrizione=dati.descrizione.strip(),
        unita=Unita.objects.filter(pk=dati.unita_id).first() if dati.unita_id else None,
        registrata_da=utente,
    )
    if file is not None:
        spesa.giustificativo = file
    spesa.save()
    return Status(201, _spesa_out(utente, spesa))


class RimborsoIn(Schema):
    cassa_id: int
    data: date | None = None


def _spesa(request, spesa_id: int) -> SpesaAnticipata:
    return get_object_or_404(_spese_visibili(request.auth), pk=spesa_id)


@router.post("/spese-anticipate/{spesa_id}/rimborsa", response=SpesaOut)
def rimborsa(request, spesa_id: int, dati: RimborsoIn):
    spesa = _spesa(request, spesa_id)
    cassa = get_object_or_404(Cassa, pk=dati.cassa_id)
    utente = request.auth
    if not policy.puo_registrare_movimenti(utente, spesa.unita_id) or not (
        policy.puo_registrare_in_cassa(utente, cassa)
    ):
        raise HttpError(403, "I rimborsi li registrano i tesorieri e il capo unità.")
    try:
        with transaction.atomic():
            servizi.rimborsa(spesa, cassa, utente, dati.data)
    except ValidationError as errore:
        raise _errore(errore) from errore
    return _spesa_out(utente, spesa)


@router.post("/spese-anticipate/{spesa_id}/respingi", response=SpesaOut)
def respingi(request, spesa_id: int, dati: Motivo):
    spesa = _spesa(request, spesa_id)
    if not policy.puo_registrare_movimenti(request.auth, spesa.unita_id):
        raise HttpError(403, "Le spese le valutano i tesorieri e il capo unità.")
    try:
        servizi.respingi(spesa, dati.motivo)
    except ValidationError as errore:
        raise _errore(errore) from errore
    return _spesa_out(request.auth, spesa)


@router.get("/spese-anticipate/{spesa_id}/giustificativo")
def giustificativo_spesa(request, spesa_id: int):
    return _file(_spesa(request, spesa_id).giustificativo)


# --- Totals for the national report (DEC-87) -----------------------------------------------


class RigaModelloD(Schema):
    lato: str
    riga: str
    titolo: str
    totale: Decimal


class ModelloDOut(Schema):
    anno_bilancio: str
    anno_etichetta: str
    righe: list[RigaModelloD]
    entrate: Decimal
    uscite: Decimal
    rettifiche: Decimal
    saldi: list[CassaOut]


@router.get("/modello-d", response=ModelloDOut)
def modello_d(request, anno: int | None = None):
    """The totals to copy by hand into the national report (DEC-06, DEC-87)."""
    if policy.unita_cassa_visibili(request.auth) is not None:
        raise HttpError(403, "Il rendiconto lo vede la Co.Ca.")
    periodo = _anno(anno)
    return {
        **servizi.modello_d(periodo),
        "anno_etichetta": periodo.etichetta,
        "saldi": [_cassa_out(request.auth, c) for c in Cassa.objects.all()],
    }
