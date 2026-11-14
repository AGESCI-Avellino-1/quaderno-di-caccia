"""Draft reorganisation of the patrols (DEC-410): online only, never cached."""

from datetime import date, datetime

from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router, Schema, Status
from ninja.errors import HttpError

from apps.anagrafica.models import Persona
from apps.permessi import policy

from . import riorganizzazione as rio
from .animali import AnimaleBreve, breve
from .models import (
    AnimaleSquadriglia,
    BozzaSquadriglie,
    SquadrigliaInBozza,
    StatoBozza,
    Unita,
    reparti_insieme,
)

router = Router(tags=["riorganizzazione"])


class Ragazzo(Schema):
    id: int
    nome: str
    cognome: str


class RagazzoSenza(Ragazzo):
    reparto_id: int | None
    # Shown apart: goes to R/S (DEC-411).
    passa_in_rs: bool = False


class PostoOut(Schema):
    id: int
    nome: str
    # A patrol that does not exist yet.
    nuova: bool
    unita_id: int
    unita_nome: str
    animale: AnimaleBreve | None = None
    sesso: str
    capo_id: int | None
    vice_id: int | None
    membri: list[Ragazzo]


class RepartoBozza(Schema):
    id: int
    nome: str
    composizione: str


class BozzaOut(Schema):
    id: int
    data_inizio: date
    stato: StatoBozza
    visibile_ai_capi_squadriglia: bool
    # From its first day on.
    si_applica: bool
    annullabile: bool
    applicata_il: datetime | None
    applicata_da: str
    reparti: list[RepartoBozza]
    squadriglie: list[PostoOut]
    senza_squadriglia: list[RagazzoSenza]
    # Changes in reality since the draft: for who prepares it.
    differenze: list[str]
    puo_gestire: bool


class BozzeUnita(Schema):
    aperta: BozzaOut | None
    # The last one applied, while it may still be undone.
    applicata: BozzaOut | None


def _persona(p: Persona) -> dict:
    return {"id": p.pk, "nome": p.nome, "cognome": p.cognome}


def _bozza_out(user, bozza: BozzaSquadriglie) -> dict:
    gestisce = policy.puo_gestire_squadriglie(user, bozza.unita)
    reparti = rio.reparti(bozza)
    oggi = rio.ragazzi(reparti)
    membri = list(
        bozza.membri.select_related("persona").order_by("persona__cognome", "persona__nome")
    )
    posti = list(bozza.squadriglie.select_related("squadriglia", "animale", "unita").order_by("pk"))
    senza_animale = 0
    squadriglie = []
    for posto in posti:
        nome = posto.nome
        if not posto.squadriglia_id and not posto.animale_id:
            senza_animale += 1
            nome = f"Nuova squadriglia {senza_animale} (senza animale)"
        squadriglie.append(
            {
                "id": posto.pk,
                "nome": nome,
                "nuova": not posto.squadriglia_id,
                "unita_id": posto.unita_id,
                "unita_nome": str(posto.unita),
                "animale": breve(posto.animale),
                "sesso": posto.sesso,
                "capo_id": posto.capo_id,
                "vice_id": posto.vice_id,
                "membri": [_persona(m.persona) for m in membri if m.squadriglia_id == posto.pk],
            }
        )
    applicata_da = bozza.applicata_da
    return {
        "id": bozza.pk,
        "data_inizio": bozza.data_inizio,
        "stato": bozza.stato,
        "visibile_ai_capi_squadriglia": bozza.visibile_ai_capi_squadriglia,
        "si_applica": bozza.data_inizio <= timezone.localdate(),
        "annullabile": gestisce and rio.annullabile(bozza),
        "applicata_il": bozza.applicata_il,
        "applicata_da": str(policy.persona_di(applicata_da) or "") if applicata_da else "",
        "reparti": [{"id": r.pk, "nome": str(r), "composizione": r.composizione} for r in reparti],
        "squadriglie": squadriglie,
        "senza_squadriglia": [
            {
                **_persona(m.persona),
                "reparto_id": getattr(oggi.get(m.persona_id), "pk", None),
                "passa_in_rs": m.passa_in_rs,
            }
            for m in membri
            if m.squadriglia_id is None
        ],
        "differenze": (
            rio.differenze(bozza) if gestisce and bozza.stato == StatoBozza.APERTA else []
        ),
        "puo_gestire": gestisce,
    }


def _errore(errore: ValidationError) -> HttpError:
    return HttpError(400, " ".join(errore.messages))


def _reparto(request, unita_id: int) -> Unita:
    unita = get_object_or_404(Unita, pk=unita_id)
    if not reparti_insieme(unita):
        raise HttpError(400, "Le squadriglie sono di un reparto.")
    if not policy.puo_gestire_squadriglie(request.auth, unita):
        raise HttpError(403, "Le squadriglie le prepara lo staff del reparto.")
    return unita


def _bozza(request, bozza_id: int) -> BozzaSquadriglie:
    bozza = get_object_or_404(BozzaSquadriglie.objects.select_related("unita"), pk=bozza_id)
    if not policy.puo_gestire_squadriglie(request.auth, bozza.unita):
        raise HttpError(403, "Le squadriglie le prepara lo staff del reparto.")
    return bozza


def _posto(bozza: BozzaSquadriglie, posto_id: int) -> SquadrigliaInBozza:
    return get_object_or_404(SquadrigliaInBozza, pk=posto_id, bozza=bozza)


def _ragazzo(persona_id: int | None) -> Persona | None:
    return get_object_or_404(Persona, pk=persona_id) if persona_id is not None else None


@router.get("/unita/{unita_id}/bozza-squadriglie", response=BozzeUnita)
def bozze_unita(request, unita_id: int):
    unita = _reparto(request, unita_id)
    aperta = rio.aperta(unita)
    applicata = rio.ultima_applicata(unita)
    return {
        "aperta": _bozza_out(request.auth, aperta) if aperta else None,
        "applicata": (
            _bozza_out(request.auth, applicata)
            if applicata and rio.annullabile(applicata)
            else None
        ),
    }


class NuovaBozza(Schema):
    data_inizio: date


@router.post("/unita/{unita_id}/bozza-squadriglie", response={201: BozzaOut})
def crea_bozza(request, unita_id: int, dati: NuovaBozza):
    unita = _reparto(request, unita_id)
    try:
        bozza = rio.crea(unita, dati.data_inizio)
    except ValidationError as errore:
        raise _errore(errore) from errore
    return Status(201, _bozza_out(request.auth, bozza))


@router.get("/bozze-squadriglie/{bozza_id}", response=BozzaOut)
def leggi_bozza(request, bozza_id: int):
    """The staff, and the future CSQ and VCSQ when the staff shows it to them."""
    bozza = get_object_or_404(BozzaSquadriglie.objects.select_related("unita"), pk=bozza_id)
    if not policy.puo_leggere_bozza_squadriglie(request.auth, bozza):
        raise HttpError(404, "Bozza non trovata.")
    return _bozza_out(request.auth, bozza)


class ImpostaBozza(Schema):
    data_inizio: date
    visibile_ai_capi_squadriglia: bool = False


@router.put("/bozze-squadriglie/{bozza_id}", response=BozzaOut)
def imposta_bozza(request, bozza_id: int, dati: ImpostaBozza):
    bozza = _bozza(request, bozza_id)
    try:
        rio.imposta(bozza, dati.data_inizio, dati.visibile_ai_capi_squadriglia)
    except ValidationError as errore:
        raise _errore(errore) from errore
    return _bozza_out(request.auth, bozza)


@router.delete("/bozze-squadriglie/{bozza_id}", response={204: None})
def scarta_bozza(request, bozza_id: int):
    bozza = _bozza(request, bozza_id)
    if bozza.stato != StatoBozza.APERTA:
        raise HttpError(400, "Una bozza applicata non si scarta: puoi annullarne l'applicazione.")
    bozza.delete()
    return Status(204, None)


class NuovaSquadrigliaIn(Schema):
    unita_id: int
    # None: its CSQ chooses it (DEC-409).
    animale_id: int | None = None
    sesso: str


@router.post("/bozze-squadriglie/{bozza_id}/squadriglie", response={201: BozzaOut})
def aggiungi_squadriglia(request, bozza_id: int, dati: NuovaSquadrigliaIn):
    bozza = _bozza(request, bozza_id)
    unita = get_object_or_404(Unita, pk=dati.unita_id)
    animale = (
        get_object_or_404(AnimaleSquadriglia, pk=dati.animale_id)
        if dati.animale_id is not None
        else None
    )
    if dati.sesso not in ("M", "F"):
        raise HttpError(400, "Scegli maschile o femminile.")
    try:
        rio.nuova_squadriglia(bozza, unita, animale, dati.sesso)
    except ValidationError as errore:
        raise _errore(errore) from errore
    return Status(201, _bozza_out(request.auth, bozza))


@router.delete("/bozze-squadriglie/{bozza_id}/squadriglie/{posto_id}", response=BozzaOut)
def togli_squadriglia(request, bozza_id: int, posto_id: int):
    bozza = _bozza(request, bozza_id)
    try:
        rio.togli_squadriglia(_posto(bozza, posto_id))
    except ValidationError as errore:
        raise _errore(errore) from errore
    return _bozza_out(request.auth, bozza)


class GuideIn(Schema):
    capo_id: int | None = None
    vice_id: int | None = None


@router.put("/bozze-squadriglie/{bozza_id}/squadriglie/{posto_id}/guide", response=BozzaOut)
def imposta_guide(request, bozza_id: int, posto_id: int, dati: GuideIn):
    bozza = _bozza(request, bozza_id)
    try:
        rio.guide(_posto(bozza, posto_id), _ragazzo(dati.capo_id), _ragazzo(dati.vice_id))
    except ValidationError as errore:
        raise _errore(errore) from errore
    return _bozza_out(request.auth, bozza)


class PostoIn(Schema):
    # None: no patrol.
    squadriglia_id: int | None = None


@router.put("/bozze-squadriglie/{bozza_id}/membri/{persona_id}", response=BozzaOut)
def sposta(request, bozza_id: int, persona_id: int, dati: PostoIn):
    bozza = _bozza(request, bozza_id)
    posto = _posto(bozza, dati.squadriglia_id) if dati.squadriglia_id is not None else None
    try:
        rio.sposta(bozza, get_object_or_404(Persona, pk=persona_id), posto)
    except ValidationError as errore:
        raise _errore(errore) from errore
    return _bozza_out(request.auth, bozza)


class PassaInRS(Schema):
    passa: bool


@router.put("/bozze-squadriglie/{bozza_id}/membri/{persona_id}/rs", response=BozzaOut)
def segna_rs(request, bozza_id: int, persona_id: int, dati: PassaInRS):
    bozza = _bozza(request, bozza_id)
    try:
        rio.segna_rs(bozza, get_object_or_404(Persona, pk=persona_id), dati.passa)
    except ValidationError as errore:
        raise _errore(errore) from errore
    return _bozza_out(request.auth, bozza)


@router.get("/bozze-squadriglie/{bozza_id}/bozza.pdf")
def bozza_pdf(request, bozza_id: int):
    """The open draft on the letterhead, for the Co.Ca. (DEC-411); never stored."""
    bozza = get_object_or_404(BozzaSquadriglie.objects.select_related("unita"), pk=bozza_id)
    if not policy.puo_scaricare_bozza_squadriglie(request.auth, bozza):
        raise HttpError(404, "Bozza non trovata.")
    risposta = HttpResponse(rio.pdf(bozza), content_type="application/pdf")
    risposta["Content-Disposition"] = 'attachment; filename="bozza-squadriglie.pdf"'
    risposta["Cache-Control"] = "no-store"
    return risposta


@router.post("/bozze-squadriglie/{bozza_id}/applica", response=BozzaOut)
def applica(request, bozza_id: int):
    bozza = _bozza(request, bozza_id)
    try:
        bozza = rio.applica(bozza, request.auth)
    except ValidationError as errore:
        raise _errore(errore) from errore
    return _bozza_out(request.auth, bozza)


@router.post("/bozze-squadriglie/{bozza_id}/annulla", response=BozzaOut)
def annulla(request, bozza_id: int):
    bozza = _bozza(request, bozza_id)
    try:
        bozza = rio.annulla(bozza)
    except ValidationError as errore:
        raise _errore(errore) from errore
    return _bozza_out(request.auth, bozza)
