"""«La mia tribù» and the totem names (DEC-416). Online only: nothing is kept on the
devices. Who sees what is decided in `policy`."""

from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from ninja import File, Router, Schema
from ninja.errors import HttpError
from ninja.files import UploadedFile

from apps.anagrafica.models import Persona
from apps.impostazioni.models import Impostazioni
from apps.permessi import policy

from . import servizi, testi
from .models import Totem
from .stampa import pdf_cerimonia

router = Router(tags=["tribu"])

NON_TROVATO = "Nome di totem non trovato."


def _o_errore(funzione, *argomenti):
    try:
        return funzione(*argomenti)
    except ValidationError as errore:
        raise HttpError(400, " ".join(errore.messages)) from errore


class Proprietario(Schema):
    id: int
    nome: str
    cognome: str


class TotemOut(Schema):
    id: int
    nome: str
    # Whose it is, only for who may know (DEC-416).
    persona: Proprietario | None = None
    immagine: bool
    # For the owner and the capi: an image waiting for a capo.
    in_attesa: bool = False
    # Changes when an image changes: the PWA asks for it again.
    versione: str


class TribuOut(Schema):
    descrizione: str
    # The capi, when the group wrote one.
    cerimonia: bool
    mio: TotemOut | None
    totem: list[TotemOut]
    # The capi: images uploaded by ragazzi, waiting for one of them.
    da_approvare: list[TotemOut]


def _totem_out(user, totem: Totem, *, attesa: bool = False) -> dict:
    persona = totem.persona
    return {
        "id": totem.pk,
        "nome": totem.nome,
        "persona": persona if policy.vede_di_chi_e_totem(user, persona) else None,
        "immagine": bool(totem.immagine),
        "in_attesa": attesa and bool(totem.immagine_in_attesa),
        "versione": f"{totem.aggiornato_il:%Y%m%d%H%M%S%f}",
    }


@router.get("/tribu", response=TribuOut)
def tribu(request):
    utente = request.auth
    if not policy.vede_tribu(utente):
        raise HttpError(404, "Pagina non trovata.")
    capo = policy.puo_moderare_immagini_totem(utente)
    propria = policy.persona_di(utente)
    tutti = list(
        Totem.objects.filter(persona__in=policy.nella_tribu())
        .select_related("persona")
        .order_by("nome", "pk")
    )
    mio = next((t for t in tutti if propria is not None and t.persona_id == propria.pk), None)
    imp = Impostazioni.carica()
    return {
        "descrizione": testi.descrizione(imp),
        "cerimonia": policy.vede_cerimonia_totem(utente) and bool(imp.cerimonia_totem),
        "mio": _totem_out(utente, mio, attesa=True) if mio else None,
        "totem": [_totem_out(utente, t, attesa=capo) for t in tutti if t is not mio],
        "da_approvare": (
            [_totem_out(utente, t, attesa=True) for t in tutti if t.immagine_in_attesa]
            if capo
            else []
        ),
    }


@router.get("/tribu/{totem_id}/immagine")
def immagine(request, totem_id: int, in_attesa: bool = False):
    """The image; the one waiting only for its owner and the capi."""
    totem = get_object_or_404(Totem, pk=totem_id)
    utente = request.auth
    if not policy.vede_tribu(utente) or not policy.puo_avere_totem(totem.persona):
        raise HttpError(404, NON_TROVATO)
    if in_attesa:
        propria = policy.persona_di(utente)
        if not (
            policy.puo_moderare_immagini_totem(utente)
            or (propria is not None and propria.pk == totem.persona_id)
        ):
            raise HttpError(404, NON_TROVATO)
    file = totem.immagine_in_attesa if in_attesa else totem.immagine
    if not file:
        raise HttpError(404, "Nessuna immagine.")
    with file.open("rb") as aperto:
        risposta = HttpResponse(aperto.read(), content_type="image/jpeg")
    risposta["Cache-Control"] = "private, no-store"
    return risposta


def _da_moderare(request, totem_id: int) -> Totem:
    totem = get_object_or_404(Totem, pk=totem_id)
    if not policy.puo_moderare_immagini_totem(request.auth):
        raise HttpError(403, "Le immagini dei totem le approvano i capi.")
    return totem


class MotivoIn(Schema):
    motivo: str


@router.post("/tribu/{totem_id}/immagine/approva", response=TotemOut)
def approva(request, totem_id: int):
    totem = _o_errore(servizi.approva, _da_moderare(request, totem_id))
    return _totem_out(request.auth, totem, attesa=True)


@router.post("/tribu/{totem_id}/immagine/rifiuta", response=TotemOut)
def rifiuta(request, totem_id: int, dati: MotivoIn):
    totem = _o_errore(servizi.rifiuta, _da_moderare(request, totem_id), dati.motivo)
    return _totem_out(request.auth, totem, attesa=True)


@router.post("/tribu/{totem_id}/immagine/togli", response=TotemOut)
def togli(request, totem_id: int, dati: MotivoIn):
    totem = _o_errore(servizi.togli, _da_moderare(request, totem_id), dati.motivo)
    return _totem_out(request.auth, totem, attesa=True)


class CerimoniaOut(Schema):
    html: str


def _cerimonia(request) -> str:
    html = Impostazioni.carica().cerimonia_totem
    if not policy.vede_cerimonia_totem(request.auth) or not html:
        raise HttpError(404, "Cerimonia non trovata.")
    return html


@router.get("/tribu/cerimonia", response=CerimoniaOut)
def cerimonia(request):
    return {"html": _cerimonia(request)}


@router.get("/tribu/cerimonia.pdf")
def cerimonia_pdf(request):
    risposta = HttpResponse(pdf_cerimonia(_cerimonia(request)), content_type="application/pdf")
    risposta["Content-Disposition"] = 'attachment; filename="cerimonia-del-totem.pdf"'
    risposta["Cache-Control"] = "private, no-store"
    return risposta


# --- On the person's page ------------------------------------------------------------


class TotemPersonaOut(Schema):
    id: int | None
    nome: str
    immagine: bool
    in_attesa: bool
    # Why a capo refused or took away the image.
    avviso: str
    versione: str
    puo_assegnare: bool
    puo_caricare: bool
    # A new image waits for a capo.
    da_approvare: bool
    puo_moderare: bool


def _persona_totem(request, persona_id: int) -> Persona:
    persona = get_object_or_404(Persona, pk=persona_id)
    if not policy.vede_totem_persona(request.auth, persona):
        raise HttpError(404, NON_TROVATO)
    return persona


def _totem_persona(request, persona: Persona) -> dict:
    utente = request.auth
    totem = Totem.objects.filter(persona=persona).first()
    return {
        "id": totem.pk if totem else None,
        "nome": totem.nome if totem else "",
        "immagine": bool(totem and totem.immagine),
        "in_attesa": bool(totem and totem.immagine_in_attesa),
        "avviso": totem.avviso_immagine if totem else "",
        "versione": f"{totem.aggiornato_il:%Y%m%d%H%M%S%f}" if totem else "",
        "puo_assegnare": policy.puo_assegnare_totem(utente, persona),
        "puo_caricare": policy.puo_caricare_immagine_totem(utente, persona),
        "da_approvare": policy.immagine_totem_da_approvare(utente),
        "puo_moderare": policy.puo_moderare_immagini_totem(utente),
    }


@router.get("/persone/{persona_id}/totem", response=TotemPersonaOut)
def totem_persona(request, persona_id: int):
    return _totem_persona(request, _persona_totem(request, persona_id))


class NomeIn(Schema):
    # Empty: the totem name is taken away.
    nome: str = ""


@router.put("/persone/{persona_id}/totem", response=TotemPersonaOut)
def assegna(request, persona_id: int, dati: NomeIn):
    persona = _persona_totem(request, persona_id)
    if not policy.puo_assegnare_totem(request.auth, persona):
        raise HttpError(403, "Il nome di totem lo assegnano lo staff dell'unità e i capigruppo.")
    _o_errore(servizi.assegna, persona, dati.nome)
    return _totem_persona(request, persona)


@router.post("/persone/{persona_id}/totem/immagine", response=TotemPersonaOut)
def carica_immagine(request, persona_id: int, file: File[UploadedFile]):
    persona = _persona_totem(request, persona_id)
    if not policy.puo_caricare_immagine_totem(request.auth, persona):
        raise HttpError(403, "L'immagine la carica chi ha il totem, o chi lo assegna.")
    totem = Totem.objects.get(persona=persona)
    _o_errore(
        servizi.carica_immagine,
        totem,
        file,
        policy.immagine_totem_da_approvare(request.auth),
    )
    return _totem_persona(request, persona)
