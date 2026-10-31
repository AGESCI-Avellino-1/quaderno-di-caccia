"""Fees, payments, receipts (see models). Every endpoint asks the policy."""

from datetime import date, datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from ninja import Router, Schema
from ninja.errors import HttpError
from ninja.responses import Status

from apps.anagrafica.models import Appartenenza, Persona
from apps.core.anno import AnnoAssociativo
from apps.core.chiusura import anno_chiuso
from apps.organizzazione.models import Gruppo, Unita
from apps.permessi import policy

from . import modi_pagamento, servizi
from .models import (
    Agevolazione,
    CategoriaQuota,
    Destinatari,
    LegameConiugale,
    MetodoPagamento,
    Pagamento,
    Quota,
    TipoQuota,
)
from .ricevute import pdf

router = Router(tags=["quote"])


def _valida(oggetto) -> None:
    try:
        oggetto.full_clean()
    except ValidationError as errore:
        raise HttpError(400, " ".join(errore.messages)) from errore


def _anno(anno: int | None) -> int:
    return anno or AnnoAssociativo.corrente().anno_fine


# --- Fee types (only the group) ---------------------------------------------------------


class TipoQuotaIn(Schema):
    nome: str
    categoria: CategoriaQuota
    anno: int
    importo: Decimal
    sconto_famiglia: Decimal = Decimal("0")
    destinatari: Destinatari
    unita: list[int] = []
    scadenza: date | None = None
    mesi: list[int] = []
    giorno_scadenza: int | None = None


class TipoQuotaOut(TipoQuotaIn):
    id: int
    categoria_nome: str
    destinatari_nome: str
    anno_etichetta: str
    emesse: int


def _tipo_out(tipo: TipoQuota) -> dict:
    return {
        "id": tipo.pk,
        "nome": tipo.nome,
        "categoria": tipo.categoria,
        "categoria_nome": tipo.get_categoria_display(),
        "anno": tipo.anno,
        "anno_etichetta": tipo.anno_associativo.etichetta,
        "importo": tipo.importo,
        "sconto_famiglia": tipo.sconto_famiglia,
        "destinatari": tipo.destinatari,
        "destinatari_nome": tipo.get_destinatari_display(),
        "unita": [u.pk for u in tipo.unita.all()],
        "scadenza": tipo.scadenza,
        "mesi": tipo.mesi,
        "giorno_scadenza": tipo.giorno_scadenza,
        "emesse": tipo.quote.valide().count(),
    }


def _gestore(request) -> None:
    if not policy.puo_gestire_quote(request.auth):
        raise HttpError(403, "Le quote le gestiscono i capigruppo e il tesoriere di gruppo.")


def _salva_tipo(tipo: TipoQuota, dati: TipoQuotaIn) -> TipoQuota:
    if (
        tipo.pk
        and tipo.quote.exists()
        and (tipo.categoria, tipo.anno) != (dati.categoria, dati.anno)
    ):
        raise HttpError(400, "Categoria e anno non si cambiano dopo l'emissione.")
    for campo in ("nome", "categoria", "anno", "importo", "sconto_famiglia", "destinatari"):
        setattr(tipo, campo, getattr(dati, campo))
    tipo.nome = tipo.nome.strip()
    mensile = dati.categoria == CategoriaQuota.MENSILE
    tipo.scadenza = None if mensile else dati.scadenza
    tipo.mesi = sorted(set(dati.mesi)) if mensile else []
    tipo.giorno_scadenza = dati.giorno_scadenza if mensile else None
    unita = list(Unita.objects.filter(pk__in=dati.unita))
    if dati.destinatari == Destinatari.UNITA and not unita:
        raise HttpError(400, "Scegli almeno un'unità.")
    _valida(tipo)
    with transaction.atomic():
        tipo.save()
        tipo.unita.set(unita if dati.destinatari == Destinatari.UNITA else [])
    return tipo


@router.get("/quote/tipi", response=list[TipoQuotaOut])
def tipi_quota(request, anno: int | None = None):
    if not policy.puo_vedere_situazione_quote(request.auth):
        raise HttpError(403, "Non puoi vedere le quote.")
    # An event's fee is set on the event (DEC-77), a BuonaCaccia one at registration.
    tipi = (
        TipoQuota.objects.filter(anno=_anno(anno))
        .exclude(categoria__in=[CategoriaQuota.EVENTO, CategoriaQuota.BUONACACCIA])
        .prefetch_related("unita")
    )
    return [_tipo_out(t) for t in tipi]


@router.post("/quote/tipi", response={201: TipoQuotaOut})
def crea_tipo_quota(request, dati: TipoQuotaIn):
    _gestore(request)
    return Status(201, _tipo_out(_salva_tipo(TipoQuota(), dati)))


@router.put("/quote/tipi/{tipo_id}", response=TipoQuotaOut)
def modifica_tipo_quota(request, tipo_id: int, dati: TipoQuotaIn):
    """Fees already issued keep their amount and discount."""
    _gestore(request)
    return _tipo_out(_salva_tipo(get_object_or_404(TipoQuota, pk=tipo_id), dati))


class Emissione(Schema):
    emesse: int


@router.post("/quote/tipi/{tipo_id}/emetti", response=Emissione)
def emetti_tipo(request, tipo_id: int):
    """Issue now what the daily job would issue: periods already started."""
    _gestore(request)
    return {"emesse": len(servizi.emetti(get_object_or_404(TipoQuota, pk=tipo_id)))}


# --- Fees of a member ----------------------------------------------------------------------


class AgevolazioneOut(Schema):
    importo: Decimal
    decisa_il: date
    nota: str = ""  # only for the Co.Ca.


class QuotaOut(Schema):
    id: int
    persona_id: int
    persona: str
    descrizione: str
    categoria: CategoriaQuota
    periodo: date
    scadenza: date
    importo: Decimal
    sconto: Decimal
    agevolazione: AgevolazioneOut | None
    dovuto: Decimal
    pagato: Decimal
    residuo: Decimal
    annullata: bool
    motivo_annullamento: str = ""
    # Unpaid from an earlier year, shown with the year asked (DEC-216).
    arretrata: bool = False


def _quota_out(user, quota: Quota) -> dict:
    agevolazione = getattr(quota, "agevolazione", None)
    coca = policy.puo_vedere_agevolazioni(user)
    vede = policy.puo_vedere_agevolazione_di(user, quota.persona)
    return {
        "id": quota.pk,
        "persona_id": quota.persona_id,
        "persona": f"{quota.persona.nome} {quota.persona.cognome}",
        "descrizione": quota.descrizione,
        "categoria": quota.tipo.categoria,
        "periodo": quota.periodo,
        "scadenza": quota.scadenza,
        "importo": quota.importo,
        "sconto": quota.sconto,
        "agevolazione": (
            {
                "importo": agevolazione.importo,
                "decisa_il": agevolazione.decisa_il,
                "nota": agevolazione.nota if coca else "",
            }
            if agevolazione and vede
            else None
        ),
        # Without seeing the agevolazione, the treasurer sees what is left to pay.
        "dovuto": quota.dovuto,
        "pagato": quota.pagato,
        "residuo": quota.residuo,
        "annullata": quota.annullata_il is not None,
        "motivo_annullamento": quota.motivo_annullamento,
        "arretrata": getattr(quota, "arretrata", False),
    }


def _quote(persone, anno: int) -> list[Quota]:
    """The fees of the year, then those of earlier years still unpaid: they carry over
    as arrears into the following years (DEC-216)."""
    base = Quota.objects.filter(persona__in=persone).select_related(
        "tipo", "persona", "agevolazione"
    )
    ordine = ("persona__cognome", "persona__nome", "periodo", "tipo__nome")
    arretrate = [
        q
        for q in base.filter(tipo__anno__lt=anno, annullata_il__isnull=True).order_by(*ordine)
        if q.residuo > 0
    ]
    for q in arretrate:
        q.arretrata = True
    return list(base.filter(tipo__anno=anno).order_by(*ordine)) + arretrate


def _persona_quote(request, persona_id: int) -> Persona:
    persona = get_object_or_404(Persona, pk=persona_id)
    if not policy.puo_vedere_quote(request.auth, persona):
        raise HttpError(404, "Persona non trovata.")
    return persona


class QuotePersonaOut(Schema):
    quote: list[QuotaOut]
    famiglia: list[QuotaOut]  # open fees of the family, for one payment over several
    puo_registrare: bool
    puo_gestire: bool
    puo_agevolare: bool


@router.get("/persone/{persona_id}/quote", response=QuotePersonaOut)
def quote_persona(request, persona_id: int, anno: int | None = None):
    persona = _persona_quote(request, persona_id)
    utente = request.auth
    anno = _anno(anno)
    puo_registrare = policy.puo_registrare_pagamenti(utente, persona)
    famiglia = []
    if puo_registrare:
        altri = Persona.objects.filter(pk__in=servizi.famiglia(persona)).exclude(pk=persona.pk)
        famiglia = [
            _quota_out(utente, q)
            for q in _quote(altri, anno)
            if not q.annullata_il and q.residuo > 0 and policy.puo_vedere_quote(utente, q.persona)
        ]
    return {
        "quote": [_quota_out(utente, q) for q in _quote([persona], anno)],
        "famiglia": famiglia,
        "puo_registrare": puo_registrare,
        "puo_gestire": policy.puo_gestire_quote(utente),
        "puo_agevolare": policy.puo_registrare_agevolazioni(utente),
    }


class Motivo(Schema):
    motivo: str


@router.post("/quote/{quota_id}/annulla", response=QuotaOut)
def annulla_quota(request, quota_id: int, dati: Motivo):
    _gestore(request)
    quota = get_object_or_404(Quota, pk=quota_id)
    try:
        servizi.annulla_quota(quota, request.auth, dati.motivo)
    except ValidationError as errore:
        raise HttpError(400, " ".join(errore.messages)) from errore
    return _quota_out(request.auth, quota)


class AgevolazioneIn(Schema):
    importo: Decimal
    decisa_il: date
    nota: str = ""


def _solo_pendenze(quota: Quota) -> None:
    """In a closed year an agevolazione is still decided on a fee left unpaid, never on
    one already settled (DEC-216)."""
    if anno_chiuso(quota.periodo) and quota.residuo <= 0:
        raise HttpError(
            400, "L'anno di questa quota è chiuso e la quota è pagata: non si cambia più."
        )


@router.put("/quote/{quota_id}/agevolazione", response=QuotaOut)
def agevola(request, quota_id: int, dati: AgevolazioneIn):
    """DEC-82: decided by the Co.Ca., recorded here."""
    if not policy.puo_registrare_agevolazioni(request.auth):
        raise HttpError(403, "Le agevolazioni le registrano i capigruppo e il tesoriere di gruppo.")
    quota = get_object_or_404(Quota.objects.select_related("tipo", "persona"), pk=quota_id)
    if quota.annullata_il:
        raise HttpError(400, "La quota è annullata.")
    _solo_pendenze(quota)
    agevolazione = getattr(quota, "agevolazione", None) or Agevolazione(quota=quota)
    agevolazione.importo = dati.importo
    agevolazione.decisa_il = dati.decisa_il
    agevolazione.nota = dati.nota.strip()
    agevolazione.registrata_da = request.auth
    _valida(agevolazione)
    if quota.importo - quota.sconto - dati.importo < quota.pagato:
        raise HttpError(400, "La famiglia ha già pagato più di quanto resterebbe dovuto.")
    agevolazione.save()
    quota.agevolazione = agevolazione
    return _quota_out(request.auth, quota)


@router.delete("/quote/{quota_id}/agevolazione", response=QuotaOut)
def togli_agevolazione(request, quota_id: int):
    if not policy.puo_registrare_agevolazioni(request.auth):
        raise HttpError(403, "Le agevolazioni le registrano i capigruppo e il tesoriere di gruppo.")
    quota = get_object_or_404(Quota.objects.select_related("tipo", "persona"), pk=quota_id)
    _solo_pendenze(quota)
    Agevolazione.objects.filter(quota=quota).delete()
    return _quota_out(request.auth, Quota.objects.get(pk=quota.pk))


# --- Situation of a unit (DEC-92: the Co.Ca. and the unit's treasurer) -----------------


class RigaSituazione(Schema):
    persona_id: int
    persona: str
    dovuto: Decimal
    pagato: Decimal
    residuo: Decimal
    scadute: int  # open fees past their due date


@router.get("/quote/situazione", response=list[RigaSituazione])
def situazione(request, unita: int, anno: int | None = None):
    unita_obj = get_object_or_404(Unita, pk=unita)
    if not policy.puo_vedere_situazione_quote(request.auth, unita_obj):
        raise HttpError(403, "Non puoi vedere le quote di questa unità.")
    anno = _anno(anno)
    anno_obj = AnnoAssociativo(anno)
    persone = Persona.objects.filter(
        pk__in=Appartenenza.objects.filter(unita=unita_obj, data_inizio__lte=anno_obj.fine)
        .exclude(data_fine__lte=anno_obj.inizio)
        .values("persona_id")
    ).order_by("cognome", "nome")
    oggi = date.today()
    righe = []
    quote = {}
    for quota in _quote(persone, anno):
        if not quota.annullata_il:
            quote.setdefault(quota.persona_id, []).append(quota)
    for persona in persone:
        sue = quote.get(persona.pk, [])
        righe.append(
            {
                "persona_id": persona.pk,
                "persona": f"{persona.cognome} {persona.nome}",
                "dovuto": sum((q.dovuto for q in sue), Decimal("0")),
                "pagato": sum((q.pagato for q in sue), Decimal("0")),
                "residuo": sum((q.residuo for q in sue), Decimal("0")),
                "scadute": sum(1 for q in sue if q.residuo > 0 and q.scadenza < oggi),
            }
        )
    return righe


# --- Payments and receipts (DEC-83, DEC-84) -----------------------------------------------


class RigaIn(Schema):
    quota_id: int
    importo: Decimal


class PagamentoIn(Schema):
    data: date
    metodo: MetodoPagamento
    versato_da: str
    note: str = ""
    righe: list[RigaIn]
    # The cash box the money goes to; default: the unit's cash box for cash, else the
    # bank account.
    cassa_id: int | None = None


class RigaOut(Schema):
    quota_id: int
    persona: str
    descrizione: str
    importo: Decimal


class PagamentoOut(Schema):
    id: int
    numero: str
    data: date
    importo: Decimal
    metodo: MetodoPagamento
    metodo_nome: str
    versato_da: str
    note: str
    righe: list[RigaOut]
    registrato_da: str | None
    ricevuta_inviata_il: datetime | None
    annullato: bool
    motivo_annullamento: str = ""
    puo_annullare: bool = False


def _pagamento_out(pagamento: Pagamento, user=None) -> dict:
    registrato = pagamento.registrato_da
    persona = getattr(registrato, "persona", None) if registrato else None
    return {
        "id": pagamento.pk,
        "numero": pagamento.numero,
        "data": pagamento.data,
        "importo": pagamento.importo,
        "metodo": pagamento.metodo,
        "metodo_nome": pagamento.get_metodo_display(),
        "versato_da": pagamento.versato_da,
        "note": pagamento.note,
        "righe": [
            {
                "quota_id": r.quota_id,
                "persona": f"{r.quota.persona.nome} {r.quota.persona.cognome}",
                "descrizione": r.quota.descrizione,
                "importo": r.importo,
            }
            for r in pagamento.righe.select_related("quota__tipo", "quota__persona")
        ],
        "registrato_da": f"{persona.nome} {persona.cognome}" if persona else None,
        "ricevuta_inviata_il": pagamento.ricevuta_inviata_il,
        "annullato": pagamento.annullato_il is not None,
        "motivo_annullamento": pagamento.motivo_annullamento,
        "puo_annullare": (
            user is not None
            and pagamento.annullato_il is None
            and policy.puo_annullare_pagamento(user, pagamento)
        ),
    }


@router.post("/pagamenti", response={201: PagamentoOut})
def registra_pagamento(request, dati: PagamentoIn):
    """Recorded also offline (queued with an Idempotency-Key, DEC-96): the receipt
    number is given here, when the record reaches the server."""
    utente = request.auth
    quote = {
        q.pk: q
        for q in Quota.objects.select_related("tipo", "persona", "agevolazione").filter(
            pk__in=[r.quota_id for r in dati.righe]
        )
    }
    if len(quote) != len({r.quota_id for r in dati.righe}):
        raise HttpError(404, "Quota non trovata.")
    for quota in quote.values():
        if not policy.puo_registrare_pagamenti(utente, quota.persona):
            raise HttpError(403, f"Non puoi registrare pagamenti per {quota.persona.nome}.")
    cassa = None
    if dati.cassa_id is not None:
        from apps.cassa.models import Cassa

        cassa = get_object_or_404(Cassa, pk=dati.cassa_id)
        if not policy.puo_registrare_in_cassa(utente, cassa):
            raise HttpError(403, "Non puoi registrare incassi in quella cassa.")
    try:
        pagamento = servizi.registra_pagamento(
            data=dati.data,
            metodo=dati.metodo,
            versato_da=dati.versato_da,
            note=dati.note,
            righe=[servizi.Riga(quote[r.quota_id], r.importo) for r in dati.righe],
            utente=utente,
            cassa=cassa,
        )
    except ValidationError as errore:
        raise HttpError(400, " ".join(errore.messages)) from errore
    transaction.on_commit(lambda: servizi.invia_ricevuta(pagamento))
    return Status(201, _pagamento_out(pagamento, utente))


def _pagamento_visibile(request, pagamento_id: int) -> Pagamento:
    pagamento = get_object_or_404(Pagamento, pk=pagamento_id)
    persone = servizi.persone_del_pagamento(pagamento)
    if not all(policy.puo_vedere_quote(request.auth, p) for p in persone):
        raise HttpError(404, "Pagamento non trovato.")
    return pagamento


@router.get("/persone/{persona_id}/pagamenti", response=list[PagamentoOut])
def pagamenti_persona(request, persona_id: int, anno: int | None = None):
    persona = _persona_quote(request, persona_id)
    pagamenti = Pagamento.objects.filter(
        righe__quota__persona=persona, anno_ricevuta=_anno(anno)
    ).distinct()
    return [_pagamento_out(p, request.auth) for p in pagamenti]


@router.get("/pagamenti/{pagamento_id}/ricevuta.pdf")
def ricevuta(request, pagamento_id: int):
    pagamento = _pagamento_visibile(request, pagamento_id)
    risposta = HttpResponse(pdf(pagamento), content_type="application/pdf")
    nome = f"ricevuta-{pagamento.numero.replace('/', '-')}.pdf"
    risposta["Content-Disposition"] = f'attachment; filename="{nome}"'
    return risposta


@router.post("/pagamenti/{pagamento_id}/invia", response=PagamentoOut)
def reinvia_ricevuta(request, pagamento_id: int):
    pagamento = _pagamento_visibile(request, pagamento_id)
    persone = servizi.persone_del_pagamento(pagamento)
    if not all(policy.puo_registrare_pagamenti(request.auth, p) for p in persone):
        raise HttpError(403, "Non puoi inviare questa ricevuta.")
    if not servizi.invia_ricevuta(pagamento):
        raise HttpError(400, "Nessun indirizzo email a cui inviarla.")
    return _pagamento_out(pagamento, request.auth)


@router.post("/pagamenti/{pagamento_id}/annulla", response=PagamentoOut)
def annulla_pagamento(request, pagamento_id: int, dati: Motivo):
    pagamento = get_object_or_404(Pagamento, pk=pagamento_id)
    if not policy.puo_annullare_pagamento(request.auth, pagamento):
        raise HttpError(
            403,
            "I pagamenti li annullano i capigruppo e il tesoriere di gruppo; chi li ha "
            "registrati, finché la cassa non è stata verificata.",
        )
    try:
        servizi.annulla_pagamento(pagamento, request.auth, dati.motivo)
    except ValidationError as errore:
        raise HttpError(400, " ".join(errore.messages)) from errore
    return _pagamento_out(pagamento, request.auth)


# --- The family's page (DEC-16, DEC-92) ----------------------------------------------------


class BonificoOut(Schema):
    iban: str
    intestatario: str
    banca: str = ""
    bic: str = ""


class PaypalQuotaOut(Schema):
    quota_id: int
    maggiorazione: Decimal
    totale: Decimal
    link: str


class PaypalOut(Schema):
    # With the amount in it (paypal.me): for everything due.
    link: str
    # The rule in words, what to add to the whole amount due, and the total.
    regola: str
    maggiorazione: Decimal
    totale: Decimal
    per_quota: list[PaypalQuotaOut] = []


class ModiPagamentoOut(Schema):
    """How to pay, only the ways the group enabled (DEC-253)."""

    contanti: bool = False
    carte: bool = False
    bonifico: BonificoOut | None = None
    paypal: PaypalOut | None = None


class MieQuoteOut(Schema):
    quote: list[QuotaOut]
    pagamenti: list[PagamentoOut] = []
    modi_pagamento: ModiPagamentoOut = ModiPagamentoOut()


@router.get("/mie-quote", response=MieQuoteOut)
def mie_quote(request, anno: int | None = None):
    """The user's own fees and those of their children (of an adult child while still
    linked, DEC-26), with the payments and the group's payment link (DEC-83)."""
    utente = request.auth
    persone = [p for p in policy.tutelati(utente) if policy.puo_vedere_quote(utente, p)]
    propria = policy.persona_di(utente)
    if propria is not None:
        persone.insert(0, propria)
    anno = _anno(anno)
    pagamenti = Pagamento.objects.filter(
        righe__quota__persona__in=persone, anno_ricevuta=anno
    ).distinct()
    quote = [q for q in _quote(persone, anno) if not q.annullata_il]
    return {
        "quote": [_quota_out(utente, q) for q in quote],
        "pagamenti": [_pagamento_out(p, request.auth) for p in pagamenti],
        "modi_pagamento": modi_pagamento.per_la_famiglia(Gruppo.objects.first(), quote),
    }


# --- Spouses for the family discount (DEC-81) ----------------------------------------------


class ConiugiIn(Schema):
    persona_id: int
    coniuge_id: int


class ConiugiOut(Schema):
    id: int
    persona: str
    coniuge: str


def _coniugi_out(legame: LegameConiugale) -> dict:
    return {
        "id": legame.pk,
        "persona": f"{legame.persona.nome} {legame.persona.cognome}",
        "coniuge": f"{legame.coniuge.nome} {legame.coniuge.cognome}",
    }


@router.get("/quote/coniugi", response=list[ConiugiOut])
def coniugi(request):
    _gestore(request)
    return [_coniugi_out(c) for c in LegameConiugale.objects.select_related("persona", "coniuge")]


@router.post("/quote/coniugi", response={201: ConiugiOut})
def aggiungi_coniugi(request, dati: ConiugiIn):
    _gestore(request)
    if dati.persona_id == dati.coniuge_id:
        raise HttpError(400, "Scegli due persone diverse.")
    a, b = sorted((dati.persona_id, dati.coniuge_id))
    persona, coniuge = get_object_or_404(Persona, pk=a), get_object_or_404(Persona, pk=b)
    legame, _ = LegameConiugale.objects.get_or_create(persona=persona, coniuge=coniuge)
    return Status(201, _coniugi_out(legame))


@router.delete("/quote/coniugi/{legame_id}", response={204: None})
def togli_coniugi(request, legame_id: int):
    _gestore(request)
    get_object_or_404(LegameConiugale, pk=legame_id).delete()
    return Status(204, None)


# --- Settings ------------------------------------------------------------------------------


class FasciaPaypal(Schema):
    fino_a: Decimal | None = None
    quota: Decimal


class ImpostazioniQuote(Schema):
    """The payment section of the settings (DEC-253)."""

    contanti_attivo: bool = True
    carte_attivo: bool = False
    bonifico_attivo: bool = False
    iban: str = ""
    intestatario_conto: str = ""
    banca: str = ""
    bic: str = ""
    paypal_attivo: bool = False
    link_pagamento: str = ""
    paypal_maggiorazione: str = "NESSUNA"
    paypal_valore: Decimal | None = None
    paypal_fasce: list[FasciaPaypal] = []


CAMPI_PAGAMENTO = list(ImpostazioniQuote.model_fields)


def _impostazioni_out(gruppo: Gruppo | None) -> dict:
    if gruppo is None:
        return {}
    return {c: getattr(gruppo, c) for c in CAMPI_PAGAMENTO}


@router.get("/quote/impostazioni", response=ImpostazioniQuote)
def impostazioni(request):
    _gestore(request)
    return _impostazioni_out(Gruppo.objects.first())


@router.put("/quote/impostazioni", response=ImpostazioniQuote)
def salva_impostazioni(request, dati: ImpostazioniQuote):
    _gestore(request)
    gruppo = Gruppo.objects.first()
    if gruppo is None:
        raise HttpError(400, "Importa prima i dati del gruppo da BuonaStrada.")
    for campo in CAMPI_PAGAMENTO:
        setattr(gruppo, campo, getattr(dati, campo))
    gruppo.iban = modi_pagamento.normalizza_iban(dati.iban)
    gruppo.intestatario_conto = dati.intestatario_conto.strip()
    gruppo.banca = dati.banca.strip()
    gruppo.bic = "".join(dati.bic.split()).upper()
    gruppo.link_pagamento = dati.link_pagamento.strip()
    gruppo.paypal_fasce = [
        {"fino_a": None if f.fino_a is None else str(f.fino_a), "quota": str(f.quota)}
        for f in dati.paypal_fasce
    ]
    errori = modi_pagamento.problemi(gruppo)
    if errori:
        raise HttpError(400, " ".join(errori))
    _valida(gruppo)
    gruppo.save(update_fields=[*CAMPI_PAGAMENTO, "aggiornato_il"])
    return _impostazioni_out(gruppo)
