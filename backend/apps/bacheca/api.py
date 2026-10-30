"""The notice board (see models). Who reads and who writes: apps.permessi.policy.
Online only."""

from datetime import date, datetime

from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from ninja import File, Form, Router, Schema, Status
from ninja.errors import HttpError
from ninja.files import UploadedFile

from apps.organizzazione.models import TipoUnita, Unita
from apps.permessi import policy

from . import servizi
from .models import AllegatoAvviso, Avviso, Destinatari

router = Router(tags=["bacheca"])

TIPI_ALLEGATO = {"application/pdf": ".pdf", "image/jpeg": ".jpg", "image/png": ".png"}


class AllegatoOut(Schema):
    id: int
    titolo: str
    tipo_file: str


class AvvisoOut(Schema):
    id: int
    titolo: str
    testo: str
    unita_id: int | None
    # "Tutto il gruppo" when for the whole group.
    dove: str
    destinatari: Destinatari
    destinatari_nome: str
    scade_il: date
    pubblicato_il: datetime
    autore: str
    email_inviata: bool
    scaduto: bool
    puo_modificare: bool
    allegati: list[AllegatoOut]


class DoveOut(Schema):
    unita_id: int | None
    nome: str
    # To whom the user may address a notice there.
    destinatari: list[Destinatari]


class BachecaOut(Schema):
    avvisi: list[AvvisoOut]
    # Where the user may publish; empty: nowhere.
    pubblica_in: list[DoveOut]
    # The capi may also see the expired notices.
    vede_archivio: bool


def _autore(avviso: Avviso) -> str:
    persona = getattr(avviso.autore, "persona", None) if avviso.autore_id else None
    return f"{persona.nome} {persona.cognome}" if persona else ""


def _out(user, avviso: Avviso) -> dict:
    return {
        "id": avviso.pk,
        "titolo": avviso.titolo,
        "testo": avviso.testo,
        "unita_id": avviso.unita_id,
        "dove": str(avviso.unita) if avviso.unita_id else "Tutto il gruppo",
        "destinatari": avviso.destinatari,
        "destinatari_nome": avviso.get_destinatari_display(),
        "scade_il": avviso.scade_il,
        "pubblicato_il": avviso.creato_il,
        "autore": _autore(avviso),
        "email_inviata": avviso.email_inviata_il is not None,
        "scaduto": avviso.scade_il < date.today(),
        "puo_modificare": policy.puo_modificare_avviso(user, avviso),
        "allegati": [
            {"id": a.pk, "titolo": a.titolo, "tipo_file": a.tipo_file}
            for a in avviso.allegati.all()
        ],
    }


def _pubblica_in(user) -> list[dict]:
    dove = []
    luoghi = [(None, "Tutto il gruppo")] + [
        (u, str(u))
        for u in Unita.objects.exclude(tipo=TipoUnita.COMUNITA_CAPI).order_by("tipo", "nome")
    ]
    for unita, nome in luoghi:
        destinatari = [d for d in Destinatari if policy.puo_pubblicare_avviso(user, unita, d)]
        if destinatari:
            dove.append(
                {"unita_id": unita.pk if unita else None, "nome": nome, "destinatari": destinatari}
            )
    return dove


@router.get("/avvisi", response=BachecaOut)
def bacheca(request, scaduti: bool = False):
    user = request.auth
    avvisi = (
        policy.avvisi_visibili(user, scaduti=scaduti)
        .select_related("unita", "autore__persona")
        .prefetch_related("allegati")
    )
    return {
        "avvisi": [_out(user, a) for a in avvisi],
        "pubblica_in": _pubblica_in(user),
        "vede_archivio": policy.e_capo(user),
    }


class AvvisoIn(Schema):
    titolo: str
    testo: str
    unita_id: int | None = None
    destinatari: Destinatari
    scade_il: date
    # Only when publishing.
    invia_email: bool = False


def _unita(unita_id: int | None) -> Unita | None:
    if unita_id is None:
        return None
    return get_object_or_404(Unita, pk=unita_id)


def _salva(avviso: Avviso) -> None:
    try:
        avviso.full_clean()
    except ValidationError as errore:
        raise HttpError(400, " ".join(errore.messages)) from errore
    avviso.save()


@router.post("/avvisi", response={201: AvvisoOut})
def pubblica(request, dati: AvvisoIn):
    user = request.auth
    unita = _unita(dati.unita_id)
    if not policy.puo_pubblicare_avviso(user, unita, dati.destinatari):
        raise HttpError(
            403,
            "Gli avvisi li pubblicano lo staff per la sua unità e i capigruppo; "
            "quelli per la Comunità capi ogni capo.",
        )
    if dati.scade_il < date.today():
        raise HttpError(400, "Scegli fino a quando mostrarlo: oggi o un giorno dopo.")
    avviso = Avviso(
        titolo=dati.titolo.strip(),
        testo=dati.testo.strip(),
        unita=unita,
        destinatari=dati.destinatari,
        scade_il=dati.scade_il,
        autore=user,
    )
    _salva(avviso)
    if dati.invia_email:
        servizi.invia(avviso)
    return Status(201, _out(user, avviso))


def _avviso(request, avviso_id: int) -> Avviso:
    avviso = (
        policy.avvisi_visibili(request.auth, scaduti=True)
        .select_related("unita", "autore__persona")
        .filter(pk=avviso_id)
        .first()
    )
    if avviso is None:
        raise HttpError(404, "Avviso non trovato.")
    return avviso


def _modificabile(request, avviso_id: int) -> Avviso:
    avviso = _avviso(request, avviso_id)
    if not policy.puo_modificare_avviso(request.auth, avviso):
        raise HttpError(403, "L'avviso lo modificano chi l'ha pubblicato e i capigruppo.")
    return avviso


@router.put("/avvisi/{avviso_id}", response=AvvisoOut)
def modifica(request, avviso_id: int, dati: AvvisoIn):
    """No new email: who wants one publishes a new notice."""
    avviso = _modificabile(request, avviso_id)
    unita = _unita(dati.unita_id)
    cambia = (unita, dati.destinatari) != (avviso.unita, avviso.destinatari)
    if cambia and not policy.puo_pubblicare_avviso(request.auth, unita, dati.destinatari):
        raise HttpError(403, "Non puoi pubblicare avvisi per questa unità o per questi lettori.")
    avviso.titolo = dati.titolo.strip()
    avviso.testo = dati.testo.strip()
    avviso.unita = unita
    avviso.destinatari = dati.destinatari
    avviso.scade_il = dati.scade_il
    _salva(avviso)
    return _out(request.auth, avviso)


@router.delete("/avvisi/{avviso_id}", response={204: None})
def togli(request, avviso_id: int):
    avviso = _modificabile(request, avviso_id)
    for allegato in avviso.allegati.all():
        allegato.file.delete(save=False)
    avviso.delete()
    return Status(204, None)


@router.post("/avvisi/{avviso_id}/allegati", response={201: AvvisoOut})
def carica_allegato(request, avviso_id: int, titolo: Form[str], file: File[UploadedFile]):
    from apps.buonacaccia.servizi import _file_con_nome_casuale

    avviso = _modificabile(request, avviso_id)
    if not titolo.strip():
        raise HttpError(400, "Scrivi cos'è l'allegato.")
    try:
        salvato, tipo_file = _file_con_nome_casuale(
            file, TIPI_ALLEGATO, "Carica un PDF o un'immagine (JPEG o PNG)."
        )
    except ValidationError as errore:
        raise HttpError(400, " ".join(errore.messages)) from errore
    AllegatoAvviso.objects.create(
        avviso=avviso, titolo=titolo.strip()[:120], tipo_file=tipo_file, file=salvato
    )
    return Status(201, _out(request.auth, avviso))


def _allegato(request, allegato_id: int) -> AllegatoAvviso:
    allegato = get_object_or_404(AllegatoAvviso, pk=allegato_id)
    _avviso(request, allegato.avviso_id)
    return allegato


@router.get("/allegati-avviso/{allegato_id}")
def scarica_allegato(request, allegato_id: int):
    """Served only here, to who reads the notice."""
    allegato = _allegato(request, allegato_id)
    estensione = TIPI_ALLEGATO.get(allegato.tipo_file, ".bin")
    risposta = HttpResponse(allegato.file.read(), content_type=allegato.tipo_file)
    risposta["Content-Disposition"] = f'inline; filename="allegato-{allegato.pk}{estensione}"'
    risposta["Cache-Control"] = "private, no-store"
    risposta["X-Content-Type-Options"] = "nosniff"
    return risposta


@router.delete("/allegati-avviso/{allegato_id}", response=AvvisoOut)
def togli_allegato(request, allegato_id: int):
    allegato = _allegato(request, allegato_id)
    avviso = _modificabile(request, allegato.avviso_id)
    allegato.file.delete(save=False)
    allegato.delete()
    return _out(request.auth, avviso)
