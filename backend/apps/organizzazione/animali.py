"""The patrol animals (DEC-350...DEC-354): the catalog the list starts from, and the image of
an animal: a symbol shipped with the app, or a file a capo uploaded."""

import io
import json
import re
import secrets
from pathlib import Path

import py_svg_hush
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from ninja import Schema
from PIL import Image, UnidentifiedImageError

from .models import AnimaleSquadriglia

CATALOGO = Path(__file__).resolve().parent.parent.parent / "data/cataloghi/animali_squadriglia.json"
MASSIMO_SVG = 1024**2
MASSIMO_IMMAGINE = 5 * 1024**2
LATO_MASSIMO = 600

_catalogo = json.loads(CATALOGO.read_text(encoding="utf-8"))
# Name of a colour and how to draw it. The catalog gives the names only: the codes are ours.
COLORI: dict[str, str] = _catalogo["colori"]

# What the sanitizer lets through and is of no use in a drawing: a link it made relative, a
# javascript: left in an animation with its target removed, a url() out of the file.
_ESTERNI = re.compile(
    rb"""javascript:|(?:\bhref\s*=\s*["'](?!\#))|(?:url\(\s*["']?(?!\#))""", re.IGNORECASE
)


class ColoreOut(Schema):
    nome: str
    codice: str
    significato: str


class AnimaleBreve(Schema):
    """What a patrol's name shows next to it."""

    nome: str
    # Where the image is, "" if the animal has none.
    immagine: str
    # The symbols of the catalog take the theme's colour; an uploaded file stays as it is.
    simbolo: str
    colori: list[ColoreOut]


def colori_di(animale: AnimaleSquadriglia) -> list[dict]:
    return [
        {"nome": nome, "codice": COLORI.get(nome, "#ffffff"), "significato": significato}
        for nome, significato in (
            (animale.colore_1, animale.significato_1),
            (animale.colore_2, animale.significato_2),
        )
        if nome
    ]


def percorso_immagine(animale: AnimaleSquadriglia) -> str:
    if animale.simbolo:
        return f"/animali/{animale.simbolo}.svg"
    if animale.immagine:
        return f"/api/v1/animali/immagini/{Path(animale.immagine.name).name}"
    return ""


def breve(animale: AnimaleSquadriglia | None) -> dict | None:
    if animale is None:
        return None
    return {
        "nome": animale.nome,
        "immagine": percorso_immagine(animale),
        "simbolo": animale.simbolo,
        "colori": colori_di(animale),
    }


def carica_catalogo() -> None:
    """The animals of the catalog missing from the list: the data migration does it at
    installation; for test data, after a flush."""
    for voce in _catalogo["animali"]:
        AnimaleSquadriglia.objects.get_or_create(nome=voce["nome"], defaults=voce)


def pulisci_svg(contenuto: bytes) -> bytes:
    """Only the drawing is left, or a refusal (DEC-354). The sanitizer removes scripts and
    handlers; what it leaves behind that points elsewhere refuses the file, the second check
    against whatever it may miss. Then the file is only ever served as an image, with a policy
    against scripts (`api_animali`)."""
    try:
        pulito = py_svg_hush.filter_svg(contenuto)
    except ValueError as errore:
        raise ValidationError("Il file non è un SVG valido.") from errore
    if b"<svg" not in pulito or _ESTERNI.search(pulito):
        raise ValidationError(
            "L'SVG contiene collegamenti esterni: caricane uno con il solo disegno."
        )
    return pulito


def _ricodifica(file) -> bytes:
    """PNG or JPEG rewritten by Pillow as a PNG: nothing but the pixels is left."""
    try:
        immagine = Image.open(file)
        if immagine.format not in ("PNG", "JPEG"):
            raise UnidentifiedImageError
        immagine.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as errore:
        raise ValidationError("Carica un'immagine SVG, PNG o JPEG.") from errore
    immagine = immagine.convert("RGBA")
    immagine.thumbnail((LATO_MASSIMO, LATO_MASSIMO))
    uscita = io.BytesIO()
    immagine.save(uscita, "PNG", optimize=True)
    return uscita.getvalue()


def salva_immagine(animale: AnimaleSquadriglia, file) -> None:
    """The uploaded file replaces the animal's image, the catalog's symbol too. Under a random
    name, so a device never keeps the old one."""
    if (file.name or "").lower().endswith(".svg"):
        if file.size > MASSIMO_SVG:
            raise ValidationError("L'SVG è troppo grande: il massimo è 1 MB.")
        contenuto, estensione = pulisci_svg(file.read()), "svg"
    else:
        if file.size > MASSIMO_IMMAGINE:
            raise ValidationError("L'immagine è troppo grande: il massimo è 5 MB.")
        contenuto, estensione = _ricodifica(file), "png"
    with transaction.atomic():
        vecchia = animale.immagine.name
        animale.simbolo = ""
        animale.immagine.save(
            f"{secrets.token_hex(16)}.{estensione}", ContentFile(contenuto), save=True
        )
        if vecchia:
            storage = animale.immagine.storage
            transaction.on_commit(lambda: storage.delete(vecchia))
