"""Totem names and their images (DEC-416)."""

import uuid

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction

from apps.anagrafica.models import Persona
from apps.core.file_caricati import togli_file_dopo

from .models import ModificaTotem, Totem

LUNGHEZZA_MOTIVO = 200


@transaction.atomic
def assegna(persona: Persona, nome: str) -> Totem | None:
    """The totem name; empty takes it away, with its images. Any change turns «Modifica
    totem» off, whoever makes it (DEC-418)."""
    nome = " ".join(nome.split())
    totem = Totem.objects.filter(persona=persona).first()
    if not nome:
        if totem is not None:
            togli_file_dopo(totem.immagine)
            togli_file_dopo(totem.immagine_in_attesa)
            totem.delete()
            attiva_modifica(persona, False)
        return None
    if len(nome) > Totem._meta.get_field("nome").max_length:
        raise ValidationError("Il nome di totem va scritto in breve: al massimo 80 caratteri.")
    if totem is None:
        totem = Totem(persona=persona)
    elif totem.nome == nome:
        return totem
    totem.nome = nome
    totem.save()
    attiva_modifica(persona, False)
    return totem


def attiva_modifica(persona: Persona, attiva: bool) -> None:
    """The «Modifica totem» switch (DEC-418)."""
    if attiva:
        ModificaTotem.objects.get_or_create(persona=persona)
    else:
        # One by one, so the audit log records who turned it off.
        for modifica in ModificaTotem.objects.filter(persona=persona):
            modifica.delete()


def _salva(campo, jpeg: bytes) -> None:
    """A new file under a random name; the one it replaces goes once saved."""
    togli_file_dopo(campo)
    campo.save(f"{uuid.uuid4().hex}.jpg", ContentFile(jpeg), save=False)


@transaction.atomic
def carica_immagine(totem: Totem, file, da_approvare: bool) -> Totem:
    """A ragazzo's image waits for a capo, replacing one still waiting; a capo's is shown
    at once and drops the one waiting."""
    from apps.buonacaccia.servizi import prepara_foto

    jpeg = prepara_foto(file)
    if da_approvare:
        _salva(totem.immagine_in_attesa, jpeg)
    else:
        _salva(totem.immagine, jpeg)
        togli_file_dopo(totem.immagine_in_attesa)
        totem.immagine_in_attesa = ""
    totem.avviso_immagine = ""
    totem.save()
    return totem


def _motivo(motivo: str) -> str:
    motivo = " ".join(motivo.split())
    if not motivo:
        raise ValidationError("Scrivi il motivo: lo legge chi ha il totem.")
    if len(motivo) > LUNGHEZZA_MOTIVO:
        raise ValidationError("Il motivo va scritto in breve: al massimo 200 caratteri.")
    return motivo


@transaction.atomic
def approva(totem: Totem) -> Totem:
    if not totem.immagine_in_attesa:
        raise ValidationError("Non c'è un'immagine da approvare.")
    togli_file_dopo(totem.immagine)
    totem.immagine = totem.immagine_in_attesa.name
    totem.immagine_in_attesa = ""
    totem.avviso_immagine = ""
    totem.save()
    return totem


@transaction.atomic
def rifiuta(totem: Totem, motivo: str) -> Totem:
    motivo = _motivo(motivo)
    if not totem.immagine_in_attesa:
        raise ValidationError("Non c'è un'immagine da approvare.")
    togli_file_dopo(totem.immagine_in_attesa)
    totem.immagine_in_attesa = ""
    totem.avviso_immagine = f"Immagine non approvata da un capo: {motivo}"
    totem.save()
    return totem


@transaction.atomic
def togli(totem: Totem, motivo: str) -> Totem:
    """An image that is not appropriate: any capo takes it away, with the reason."""
    motivo = _motivo(motivo)
    if not totem.immagine:
        raise ValidationError("Il totem non ha un'immagine.")
    togli_file_dopo(totem.immagine)
    totem.immagine = ""
    totem.avviso_immagine = f"Immagine tolta da un capo: {motivo}"
    totem.save()
    return totem
