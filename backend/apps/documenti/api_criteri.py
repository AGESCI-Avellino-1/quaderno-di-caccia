"""The admission criteria of the year (DEC-355...DEC-357). The capigruppo write them; everybody
reads them, also without an account, from the waiting list."""

from datetime import date

from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from ninja import Router, Schema, Status
from ninja.errors import HttpError
from ninja.throttling import AnonRateThrottle, AuthRateThrottle

from apps.core.anno import AnnoAssociativo
from apps.core.file_caricati import disposizione
from apps.impostazioni.html import pulisci
from apps.organizzazione.models import TipoUnita, Unita
from apps.permessi import policy

from . import criteri
from .models import MassimoUnita, VersioneCriteri

router = Router(tags=["documenti"])


class _AnonimiCriteri(AnonRateThrottle):
    """Ninja keeps one count per address for every AnonRateThrottle, whatever its rate. These
    are read each time the waiting list opens: on the shared count, parents on one network
    would use up the 20 sign-ups an hour of the list itself."""

    scope = "criteri_anon"


class _UtentiCriteri(AuthRateThrottle):
    scope = "criteri_utente"


LIMITI_PUBBLICI = [_AnonimiCriteri("120/h"), _UtentiCriteri("240/h")]


class VersioneOut(Schema):
    id: int
    anno: int
    anno_nome: str
    valida_dal: date
    valida_fino_al: date
    in_vigore: bool
    verbale_numero: str
    verbale_data: date


def _versione_out(versione: VersioneCriteri, vigente_id: int | None) -> dict:
    return {
        "id": versione.pk,
        "anno": versione.anno,
        "anno_nome": AnnoAssociativo(versione.anno).etichetta,
        "valida_dal": versione.valida_dal,
        "valida_fino_al": criteri.valida_fino_al(versione),
        "in_vigore": versione.pk == vigente_id,
        "verbale_numero": versione.verbale_numero,
        "verbale_data": versione.verbale_data,
    }


class CriteriPubblici(Schema):
    # The last year's, only an outline while the new one is missing (DEC-357).
    traccia: bool
    anno_nome: str
    anno_corrente_nome: str
    versioni: list[VersioneOut]


def _pdf(versione: VersioneCriteri) -> HttpResponse:
    risposta = HttpResponse(criteri.pdf(versione), content_type="application/pdf")
    etichetta = AnnoAssociativo(versione.anno).etichetta.replace("/", "-")
    risposta["Content-Disposition"] = disposizione(
        f"criteri-di-ammissione-{etichetta}-dal-{versione.valida_dal:%Y-%m-%d}.pdf"
    )
    return risposta


@router.get(
    "/criteri-ammissione/pubblici", response=CriteriPubblici, auth=None, throttle=LIMITI_PUBBLICI
)
def criteri_pubblici(request):
    """Open to anyone: the versions of the year already begun, never one still to come."""
    visti = criteri.pubblicati()
    vigente = criteri.in_vigore()
    return {
        "traccia": visti.traccia,
        "anno_nome": AnnoAssociativo(visti.anno).etichetta if visti.anno else "",
        "anno_corrente_nome": AnnoAssociativo.corrente().etichetta,
        "versioni": [_versione_out(v, vigente.pk if vigente else None) for v in visti.versioni],
    }


@router.get("/criteri-ammissione/pubblici/{versione_id}.pdf", auth=None, throttle=LIMITI_PUBBLICI)
def criteri_pubblici_pdf(request, versione_id: int):
    for versione in criteri.pubblicati().versioni:
        if versione.pk == versione_id:
            return _pdf(versione)
    raise HttpError(404, "Non trovato.")


# --- For the capigruppo --------------------------------------------------------------------


class UnitaDaLimitare(Schema):
    id: int
    nome: str


class MassimoIO(Schema):
    unita_id: int
    massimo: int


class AnnoScelta(Schema):
    valore: int
    nome: str


class GestioneCriteri(Schema):
    versioni: list[VersioneOut]
    anni: list[AnnoScelta]
    unita: list[UnitaDaLimitare]
    # Where a new version starts from: the latest one's, or the template.
    testo: str
    massimi: list[MassimoIO]
    verbale_numero: str
    verbale_data: date | None


class NuovaVersione(Schema):
    anno: int
    valida_dal: date
    verbale_numero: str
    verbale_data: date
    testo: str
    massimi: list[MassimoIO] = []


def _gestione(request) -> None:
    if not policy.puo_gestire_criteri(request.auth):
        raise HttpError(403, "I criteri di ammissione li compilano i capigruppo.")


def _unita_da_limitare():
    return Unita.objects.filter(attiva=True).exclude(tipo=TipoUnita.COMUNITA_CAPI)


@router.get("/criteri-ammissione", response=GestioneCriteri)
def gestione_criteri(request):
    _gestione(request)
    versioni = list(VersioneCriteri.objects.order_by("-anno", "-valida_dal"))
    vigente = criteri.in_vigore()
    corrente = AnnoAssociativo.corrente()
    ultima = versioni[0] if versioni else None
    return {
        "versioni": [_versione_out(v, vigente.pk if vigente else None) for v in versioni],
        "anni": [
            {"valore": a.anno_fine, "nome": a.etichetta} for a in (corrente, corrente.successivo())
        ],
        "unita": [
            {"id": u.pk, "nome": str(u)} for u in _unita_da_limitare().order_by("tipo", "nome")
        ],
        "testo": ultima.testo if ultima else criteri.MODELLO,
        "massimi": (
            [{"unita_id": m.unita_id, "massimo": m.massimo} for m in ultima.massimi.all()]
            if ultima
            else []
        ),
        "verbale_numero": ultima.verbale_numero if ultima else "",
        "verbale_data": ultima.verbale_data if ultima else None,
    }


@router.post("/criteri-ammissione", response={201: VersioneOut})
@transaction.atomic
def nuova_versione(request, dati: NuovaVersione):
    _gestione(request)
    corrente = AnnoAssociativo.corrente()
    if dati.anno not in (corrente.anno_fine, corrente.successivo().anno_fine):
        raise HttpError(400, "Scegli l'anno in corso o il successivo.")
    testo = pulisci(dati.testo or "", immagini=False)
    versione = VersioneCriteri(
        anno=dati.anno,
        valida_dal=dati.valida_dal,
        verbale_numero=dati.verbale_numero.strip(),
        verbale_data=dati.verbale_data,
        testo=testo,
        caricata_da=request.auth,
    )
    try:
        versione.full_clean()
    except ValidationError as errore:
        raise HttpError(400, " ".join(errore.messages)) from errore
    versione.save()
    unita = {u.pk: u for u in _unita_da_limitare()}
    for voce in dati.massimi:
        if voce.unita_id not in unita:
            raise HttpError(400, "Una delle unità non è attiva.")
        if voce.massimo < 1:
            raise HttpError(400, f"Il massimo di {unita[voce.unita_id]} deve essere almeno 1.")
    MassimoUnita.objects.bulk_create(
        MassimoUnita(versione=versione, unita=unita[voce.unita_id], massimo=voce.massimo)
        for voce in {v.unita_id: v for v in dati.massimi}.values()
    )
    vigente = criteri.in_vigore()
    return Status(201, _versione_out(versione, vigente.pk if vigente else None))


@router.get("/criteri-ammissione/{versione_id}.pdf")
def pdf_versione(request, versione_id: int):
    """Also a version still to come or of a past year: for who writes them."""
    _gestione(request)
    return _pdf(get_object_or_404(VersioneCriteri, pk=versione_id))


@router.delete("/criteri-ammissione/{versione_id}", response={204: None})
def elimina_versione(request, versione_id: int):
    """One loaded by mistake: the previous version counts again; the audit log keeps it."""
    _gestione(request)
    get_object_or_404(VersioneCriteri, pk=versione_id).delete()
    return Status(204, None)
