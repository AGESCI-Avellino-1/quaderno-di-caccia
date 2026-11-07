"""The Download page and the Progetto Educativo di Gruppo (DEC-341…DEC-344). Online only."""

import io
from datetime import date

from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404
from ninja import File, Form, Router, Schema, Status
from ninja.errors import HttpError
from ninja.files import UploadedFile
from ninja.throttling import AnonRateThrottle, AuthRateThrottle
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from apps.core.anno import AnnoAssociativo
from apps.core.file_caricati import MASSIMO_SUL_SERVER, disposizione
from apps.core.stampa import decora_pagina, intestazione
from apps.core.testo_pdf import LARGHEZZA, MARGINE, TITOLO, flowable_del_testo
from apps.organizzazione.models import Gruppo, TipoUnita, Unita
from apps.permessi import policy

from . import servizi
from .models import Documento, Durata, VersionePeg

router = Router(tags=["documenti"])

# A public page: opened now and then, never in bulk.
LIMITI_PUBBLICI = [AnonRateThrottle("120/h"), AuthRateThrottle("240/h")]


class DocumentoOut(Schema):
    id: int
    titolo: str
    descrizione: str
    nome_file: str
    dimensione: int
    durata: Durata
    anno: int | None
    scade_il: date | None
    ultimo_giorno: date | None
    per_coca: bool
    per_genitori: bool
    unita_ids: list[int]
    unita_nomi: list[str]
    unita_ragazzi: bool
    unita_genitori: bool
    aggiornato: bool
    puo_modificare: bool


class UnitaScelta(Schema):
    id: int
    nome: str


class AnnoScelta(Schema):
    anno: int
    etichetta: str


class VersionePegOut(Schema):
    id: int
    nome_file: str
    dimensione: int
    # With the text only when one version is asked for.
    ha_testo: bool
    approvato_il: date
    durata: str
    in_vigore: bool


class PegOut(Schema):
    in_redazione: bool
    versioni: list[VersionePegOut]
    puo_gestire: bool


class DownloadOut(Schema):
    documenti: list[DocumentoOut]
    peg: PegOut | None
    puo_caricare: bool
    unita: list[UnitaScelta]
    anni: list[AnnoScelta]
    massimo: int


def _documento_out(user, documento: Documento) -> dict:
    unita = list(documento.unita.all())
    return {
        "id": documento.pk,
        "titolo": documento.titolo,
        "descrizione": documento.descrizione,
        "nome_file": documento.nome_file,
        "dimensione": documento.dimensione,
        "durata": documento.durata,
        "anno": documento.anno,
        "scade_il": documento.scade_il,
        "ultimo_giorno": documento.ultimo_giorno,
        "per_coca": documento.per_coca,
        "per_genitori": documento.per_genitori,
        "unita_ids": [u.pk for u in unita],
        "unita_nomi": [str(u) for u in unita],
        "unita_ragazzi": documento.unita_ragazzi,
        "unita_genitori": documento.unita_genitori,
        "aggiornato": documento.aggiornato,
        "puo_modificare": policy.puo_modificare_documento(user, documento),
    }


def _versione_out(versione: VersionePeg, vigente_id: int | None) -> dict:
    return {
        "id": versione.pk,
        "nome_file": versione.nome_file,
        "dimensione": versione.dimensione,
        "ha_testo": bool(versione.testo),
        "approvato_il": versione.approvato_il,
        "durata": versione.durata,
        "in_vigore": versione.pk == vigente_id,
    }


def _peg_out(user) -> dict | None:
    if not policy.puo_vedere_storico_peg(user):
        return None
    versioni = list(VersionePeg.objects.all())
    vigente = versioni[0].pk if versioni else None
    gruppo = Gruppo.objects.first()
    return {
        "in_redazione": bool(gruppo and gruppo.peg_in_redazione),
        "versioni": [_versione_out(v, vigente) for v in versioni],
        "puo_gestire": policy.puo_gestire_peg(user),
    }


def _anni_scelta() -> list[dict]:
    corrente = AnnoAssociativo.corrente()
    return [
        {"anno": a.anno_fine, "etichetta": a.etichetta} for a in (corrente, corrente.successivo())
    ]


@router.get("/download", response=DownloadOut)
def pagina_download(request):
    user = request.auth
    carica = policy.puo_caricare_documento(user)
    unita = []
    if carica:
        attive = Unita.objects.filter(archiviata_il__isnull=True).exclude(
            tipo=TipoUnita.COMUNITA_CAPI
        )
        unita = [{"id": u.pk, "nome": str(u)} for u in attive]
    documenti = policy.documenti_visibili(user).prefetch_related("unita")
    return {
        "documenti": [_documento_out(user, d) for d in documenti],
        "peg": _peg_out(user),
        "puo_caricare": carica,
        "unita": unita,
        "anni": _anni_scelta() if carica else [],
        "massimo": MASSIMO_SUL_SERVER,
    }


def _unita_scelte(lista: str) -> list[Unita]:
    """A form field with the ids, comma separated."""
    try:
        ids = [int(x) for x in lista.split(",") if x.strip()]
    except ValueError as errore:
        raise HttpError(400, "Unità non valida.") from errore
    trovate = list(Unita.objects.filter(pk__in=ids).exclude(tipo=TipoUnita.COMUNITA_CAPI))
    if len(trovate) != len(set(ids)):
        raise HttpError(400, "Unità non valida.")
    return trovate


def _azione(funzione, *argomenti):
    try:
        with transaction.atomic():
            return funzione(*argomenti)
    except ValidationError as errore:
        raise HttpError(400, " ".join(errore.messages)) from errore


class DocumentoForm(Schema):
    titolo: str
    descrizione: str
    durata: Durata
    anno: int | None = None
    scade_il: date | None = None
    per_coca: bool = False
    per_genitori: bool = False
    unita: str = ""
    unita_ragazzi: bool = False
    unita_genitori: bool = False
    avvisa: bool = False


def _applica(documento: Documento, dati: DocumentoForm) -> list[Unita]:
    unita = _unita_scelte(dati.unita)
    documento.titolo = dati.titolo.strip()
    documento.descrizione = dati.descrizione.strip()
    documento.durata = dati.durata
    documento.anno = dati.anno
    documento.scade_il = dati.scade_il
    documento.per_coca = dati.per_coca
    documento.per_genitori = dati.per_genitori
    # Ragazzi and parents of the units only with units chosen.
    documento.unita_ragazzi = dati.unita_ragazzi and bool(unita)
    documento.unita_genitori = dati.unita_genitori and bool(unita)
    return unita


@router.post("/documenti", response={201: DocumentoOut})
def carica(request, dati: Form[DocumentoForm], file: File[UploadedFile] = None):
    user = request.auth
    if not policy.puo_caricare_documento(user):
        raise HttpError(403, "I documenti li caricano i capi.")
    documento = Documento(autore=user)
    unita = _applica(documento, dati)
    _azione(servizi.crea_documento, documento, unita, file)
    if dati.avvisa:
        servizi.avvisa_documento(documento)
    return Status(201, _documento_out(user, documento))


def _modificabile(request, documento_id: int) -> Documento:
    documento = policy.documenti_visibili(request.auth).filter(pk=documento_id).first()
    if documento is None:
        raise HttpError(404, "Documento non trovato.")
    if not policy.puo_modificare_documento(request.auth, documento):
        raise HttpError(403, "Il documento lo modificano chi l'ha caricato e i capigruppo.")
    return documento


# POST: Django reads files only from a POST.
@router.post("/documenti/{documento_id}", response=DocumentoOut)
def modifica(
    request, documento_id: int, dati: Form[DocumentoForm], file: File[UploadedFile] = None
):
    documento = _modificabile(request, documento_id)
    unita = _applica(documento, dati)
    _azione(servizi.modifica_documento, documento, unita, file)
    if dati.avvisa:
        servizi.avvisa_documento(documento)
    return _documento_out(request.auth, documento)


@router.delete("/documenti/{documento_id}", response={204: None})
def elimina(request, documento_id: int):
    _azione(servizi.elimina_documento, _modificabile(request, documento_id))
    return Status(204, None)


def _file(file_field, nome: str, tipo: str) -> FileResponse:
    risposta = FileResponse(file_field.open("rb"), content_type=tipo)
    risposta["Content-Disposition"] = disposizione(nome)
    risposta["Cache-Control"] = "private, no-store"
    risposta["X-Content-Type-Options"] = "nosniff"
    return risposta


@router.get("/documenti/{documento_id}/file")
def scarica(request, documento_id: int):
    documento = policy.documenti_visibili(request.auth).filter(pk=documento_id).first()
    if documento is None:
        raise HttpError(404, "Documento non trovato.")
    return _file(documento.file, documento.nome_file, documento.tipo_file)


# --- Progetto Educativo di Gruppo ------------------------------------------------------------


def _pdf_del_testo(versione: VersionePeg) -> bytes:
    uscita = io.BytesIO()
    documento = SimpleDocTemplate(
        uscita,
        pagesize=A4,
        leftMargin=MARGINE,
        rightMargin=MARGINE,
        topMargin=14 * mm,
        bottomMargin=16 * mm,
        title="Progetto Educativo di Gruppo",
    )
    gruppo = Gruppo.objects.first()
    elementi = [
        intestazione(gruppo, LARGHEZZA),
        Spacer(1, 4 * mm),
        Paragraph("Progetto Educativo di Gruppo", TITOLO),
        Spacer(1, 5 * mm),
        *flowable_del_testo(versione.testo),
    ]
    pagina = decora_pagina(gruppo, MARGINE)
    documento.build(elementi, onFirstPage=pagina, onLaterPages=pagina)
    return uscita.getvalue()


def _risposta_versione(versione: VersionePeg):
    if versione.file:
        return _file(versione.file, versione.nome_file, "application/pdf")
    risposta = HttpResponse(_pdf_del_testo(versione), content_type="application/pdf")
    risposta["Content-Disposition"] = disposizione("progetto-educativo-di-gruppo.pdf")
    return risposta


class PegPubblicoOut(Schema):
    gruppo: str
    in_redazione: bool
    approvato_il: date | None
    durata: str
    testo: str
    ha_pdf: bool


@router.get("/peg/pubblico", response=PegPubblicoOut, auth=None, throttle=LIMITI_PUBBLICI)
def peg_pubblico(request):
    """Open to anyone: only the version in force, never the history (DEC-344)."""
    gruppo = Gruppo.objects.first()
    vigente = servizi.peg_in_vigore()
    return {
        "gruppo": gruppo.denominazione if gruppo else "",
        "in_redazione": bool(gruppo and gruppo.peg_in_redazione),
        "approvato_il": vigente.approvato_il if vigente else None,
        "durata": vigente.durata if vigente else "",
        "testo": vigente.testo if vigente else "",
        "ha_pdf": vigente is not None,
    }


@router.get("/peg/pubblico.pdf", auth=None, throttle=LIMITI_PUBBLICI)
def peg_pubblico_pdf(request):
    vigente = servizi.peg_in_vigore()
    if vigente is None:
        raise HttpError(404, "Non trovato.")
    return _risposta_versione(vigente)


def _storico(request) -> None:
    if not policy.puo_vedere_storico_peg(request.auth):
        raise HttpError(404, "Non trovato.")


def _gestione(request) -> None:
    if not policy.puo_gestire_peg(request.auth):
        raise HttpError(403, "Il Progetto Educativo di Gruppo lo caricano i capigruppo.")


@router.get("/peg/versioni/{versione_id}/testo")
def testo_versione(request, versione_id: int) -> dict:
    _storico(request)
    return {"testo": get_object_or_404(VersionePeg, pk=versione_id).testo}


@router.get("/peg/versioni/{versione_id}/file")
def file_versione(request, versione_id: int):
    _storico(request)
    return _risposta_versione(get_object_or_404(VersionePeg, pk=versione_id))


class VersioneForm(Schema):
    approvato_il: date
    durata: str = ""
    testo: str = ""
    avvisa: bool = False


@router.post("/peg/versioni", response={201: VersionePegOut})
def nuova_versione(request, dati: Form[VersioneForm], file: File[UploadedFile] = None):
    _gestione(request)
    versione = VersionePeg(
        approvato_il=dati.approvato_il, durata=dati.durata.strip(), caricata_da=request.auth
    )
    _azione(servizi.nuova_versione_peg, versione, file, dati.testo)
    if dati.avvisa:
        servizi.avvisa_peg()
    return Status(201, _versione_out(versione, versione.pk))


@router.delete("/peg/versioni/{versione_id}", response={204: None})
def elimina_versione(request, versione_id: int):
    _gestione(request)
    _azione(servizi.elimina_versione_peg, get_object_or_404(VersionePeg, pk=versione_id))
    return Status(204, None)


class RedazioneIn(Schema):
    in_redazione: bool


@router.put("/peg/in-redazione", response={204: None})
def in_redazione(request, dati: RedazioneIn):
    _gestione(request)
    gruppo = get_object_or_404(Gruppo.objects.order_by("pk")[:1])
    gruppo.peg_in_redazione = dati.in_redazione
    gruppo.save(update_fields=["peg_in_redazione", "aggiornato_il"])
    return Status(204, None)
