"""The list of the patrol animals (DEC-350...DEC-354). Who reads and changes it asks the policy;
the image shows to whoever already sees the patrol's name, so reading it needs only an account."""

from pathlib import Path

from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import FileResponse
from ninja import File, Router, Schema, Status, UploadedFile
from ninja.errors import HttpError

from apps.permessi import policy

from . import animali
from .models import AnimaleSquadriglia, Squadriglia, TipoAnimale

router = Router(tags=["organizzazione"])

TIPI_IMMAGINE = {".svg": "image/svg+xml", ".png": "image/png"}
# Nothing in a file runs or loads, even if opened by itself in a tab (DEC-354).
POLITICA_IMMAGINE = "default-src 'none'; style-src 'unsafe-inline'; sandbox"


class AnimaleIn(Schema):
    nome: str
    plurale: str
    tipo: TipoAnimale = TipoAnimale.GENERALE
    colore_1: str = ""
    significato_1: str = ""
    colore_2: str = ""
    significato_2: str = ""
    richiamo: str = ""
    attivo: bool = True


class AnimaleOut(Schema):
    id: int
    nome: str
    plurale: str
    tipo: str
    tipo_nome: str
    colori: list[animali.ColoreOut]
    # As written, for the form.
    colore_1: str
    significato_1: str
    colore_2: str
    significato_2: str
    richiamo: str
    immagine: str
    simbolo: str
    attivo: bool
    # Chosen by a patrol, even a closed one: it is not deleted (DEC-352).
    usato: bool

    @staticmethod
    def resolve_tipo_nome(obj: AnimaleSquadriglia) -> str:
        return obj.get_tipo_display()

    @staticmethod
    def resolve_colori(obj: AnimaleSquadriglia) -> list[dict]:
        return animali.colori_di(obj)

    @staticmethod
    def resolve_immagine(obj: AnimaleSquadriglia) -> str:
        return animali.percorso_immagine(obj)

    @staticmethod
    def resolve_usato(obj: AnimaleSquadriglia) -> bool:
        return obj.squadriglie.exists()


class ElencoAnimali(Schema):
    animali: list[AnimaleOut]
    # The colours to choose from, for the form.
    colori: list[str]
    puo_modificare: bool


def _da_modificare(request, animale_id: int | None = None) -> AnimaleSquadriglia:
    if not policy.puo_modificare_animali(request.auth):
        raise HttpError(403, "Gli animali di squadriglia li modificano gli staff dei reparti.")
    if animale_id is None:
        return AnimaleSquadriglia()
    animale = AnimaleSquadriglia.objects.filter(pk=animale_id).first()
    if animale is None:
        raise HttpError(404, "Animale non trovato.")
    return animale


@transaction.atomic
def _applica(animale: AnimaleSquadriglia, dati: AnimaleIn) -> AnimaleSquadriglia:
    for campo, valore in dati.dict().items():
        setattr(animale, campo, valore.strip() if isinstance(valore, str) else valore)
    try:
        animale.full_clean()
    except ValidationError as errore:
        raise HttpError(400, " ".join(errore.messages)) from errore
    animale.save()
    # A change holds everywhere and the patrols' names follow the plural (DEC-352).
    for squadriglia in animale.squadriglie.select_related("unita"):
        if squadriglia.nome == animale.plurale:
            continue
        squadriglia.nome = animale.plurale
        try:
            squadriglia.full_clean()
        except ValidationError as errore:
            raise HttpError(
                400, f"In {squadriglia.unita} c'è già una squadriglia {animale.plurale}."
            ) from errore
        squadriglia.save(update_fields=["nome", "aggiornato_il"])
    return animale


@router.get("/animali", response=ElencoAnimali)
def elenco_animali(request):
    if not policy.puo_vedere_animali(request.auth):
        raise HttpError(403, "Riservato ai reparti.")
    puo = policy.puo_modificare_animali(request.auth)
    return {
        "animali": list(
            AnimaleSquadriglia.objects.all()
            if puo
            else AnimaleSquadriglia.objects.filter(attivo=True)
        ),
        "colori": sorted(animali.COLORI),
        "puo_modificare": puo,
    }


@router.get("/animali/in-uso", response=list[str])
def animali_in_uso(request):
    """The images to keep on the device, not the whole list (DEC-353): those of the patrols."""
    usati = (
        AnimaleSquadriglia.objects.filter(squadriglie__attiva=True, squadriglie__unita__attiva=True)
        .distinct()
        .order_by("pk")
    )
    return [p for p in (animali.percorso_immagine(a) for a in usati) if p]


@router.get("/animali/immagini/{nome}")
def immagine_animale(request, nome: str):
    """Under a random name, no personal data: stays in the device's cache as it is. The name is
    looked for in the database, never joined to a path."""
    animale = AnimaleSquadriglia.objects.filter(immagine=f"animali/{Path(nome).name}").first()
    if animale is None:
        raise HttpError(404, "Immagine non trovata.")
    tipo = TIPI_IMMAGINE.get(Path(nome).suffix.lower())
    if tipo is None:
        raise HttpError(404, "Immagine non trovata.")
    risposta = FileResponse(animale.immagine.open("rb"), content_type=tipo)
    risposta["Content-Disposition"] = "inline"
    risposta["Content-Security-Policy"] = POLITICA_IMMAGINE
    risposta["X-Content-Type-Options"] = "nosniff"
    risposta["Cache-Control"] = "private, max-age=31536000, immutable"
    return risposta


@router.post("/animali", response={201: AnimaleOut})
def crea_animale(request, dati: AnimaleIn):
    return Status(201, _applica(_da_modificare(request), dati))


@router.put("/animali/{animale_id}", response=AnimaleOut)
def modifica_animale(request, animale_id: int, dati: AnimaleIn):
    return _applica(_da_modificare(request, animale_id), dati)


@router.post("/animali/{animale_id}/immagine", response=AnimaleOut)
def carica_immagine(request, animale_id: int, file: File[UploadedFile]):
    animale = _da_modificare(request, animale_id)
    try:
        animali.salva_immagine(animale, file)
    except ValidationError as errore:
        raise HttpError(400, " ".join(errore.messages)) from errore
    return animale


@router.delete("/animali/{animale_id}", response={204: None})
def elimina_animale(request, animale_id: int):
    animale = _da_modificare(request, animale_id)
    if Squadriglia.objects.filter(animale=animale).exists():
        raise HttpError(400, "Una squadriglia ha scelto questo animale: puoi solo disattivarlo.")
    immagine, storage = animale.immagine.name, animale.immagine.storage
    with transaction.atomic():
        animale.delete()
        if immagine:
            transaction.on_commit(lambda: storage.delete(immagine))
    return Status(204, None)
