"""The documents of the medical form and the signed form (DEC-290): uploaded in the app,
verified by a capo who saves them on the group's Drive (when linked) or on their
computer; at the confirmation the file is deleted from the server. Only the dates and
who did it stay, and for the signed form the date of the signature."""

import uuid
from datetime import date

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.iscrizioni.models import DIMENSIONE_MASSIMA, tipo_file

from .models import AllegatoSanitario, InformazioniSanitarie, SalvatoSu, TipoAllegatoSanitario

ESTENSIONI = {"application/pdf": ".pdf", "image/jpeg": ".jpg", "image/png": ".png"}


def carica(persona, tipo: str, file, utente) -> AllegatoSanitario:
    """PDF, JPEG or PNG up to 10 MB, checked on its first bytes; random file name."""
    if tipo not in TipoAllegatoSanitario.values:
        raise ValidationError("Scegli quale documento stai caricando.")
    if file.size > DIMENSIONE_MASSIMA:
        raise ValidationError("Il file è troppo grande: al massimo 10 MB.")
    contenuto = tipo_file(file.read(8))
    file.seek(0)
    if contenuto is None:
        raise ValidationError("Carica un PDF o una foto (JPEG o PNG).")
    nome_originale = (file.name or "documento")[-200:]
    file.name = f"{uuid.uuid4().hex}{ESTENSIONI[contenuto]}"
    return AllegatoSanitario.objects.create(
        persona=persona,
        tipo=tipo,
        file=file,
        nome_file=nome_originale,
        tipo_contenuto=contenuto,
        caricato_da=utente,
    )


def togli(allegato: AllegatoSanitario) -> None:
    if allegato.verificato_il is not None:
        raise ValidationError("Un documento già verificato non si toglie.")
    allegato.file.delete(save=False)
    allegato.delete()


def nome_sul_drive(allegato: AllegatoSanitario) -> str:
    p = allegato.persona
    estensione = ESTENSIONI.get(allegato.tipo_contenuto, "")
    return (
        f"{p.cognome} {p.nome} - {allegato.get_tipo_display()} - "
        f"{timezone.localdate():%Y-%m-%d}{estensione}"
    )


@transaction.atomic
def conferma(
    allegato: AllegatoSanitario, utente, salvato_su: str, firmata_il: date | None = None
) -> AllegatoSanitario:
    """The capo saved the document: the server forgets the file. For the signed form the
    date of the signature goes on the medical form (DEC-52)."""
    if allegato.verificato_il is not None:
        raise ValidationError("Questo documento è già stato verificato.")
    if allegato.tipo == TipoAllegatoSanitario.SCHEDA_FIRMATA:
        if firmata_il is None:
            raise ValidationError("Indica la data in cui la scheda è stata firmata.")
        if firmata_il > timezone.localdate():
            raise ValidationError("La data della firma non può essere nel futuro.")
        info = InformazioniSanitarie.objects.filter(persona=allegato.persona).first()
        if info is None:
            raise ValidationError("La scheda non è ancora compilata nell'app.")
        info.firmata_il = firmata_il
        info.firma_registrata_da = utente
        info.save(update_fields=["firmata_il", "firma_registrata_da", "aggiornato_il"])
    allegato.file.delete(save=False)
    allegato.file = ""
    allegato.verificato_il = timezone.now()
    allegato.verificato_da = utente
    allegato.salvato_su = salvato_su
    allegato.save()
    return allegato


def salva_sul_drive(allegato: AllegatoSanitario, utente, firmata_il: date | None = None):
    """Upload to the group's Drive, checked by Google's checksum, then confirm."""
    from apps.archivio import drive

    if allegato.verificato_il is not None:
        raise ValidationError("Questo documento è già stato verificato.")
    if allegato.tipo == TipoAllegatoSanitario.SCHEDA_FIRMATA and firmata_il is None:
        raise ValidationError("Indica la data in cui la scheda è stata firmata.")
    with allegato.file.open("rb") as f:
        contenuto = f.read()
    try:
        drive.carica(nome_sul_drive(allegato), contenuto, allegato.tipo_contenuto)
    except drive.ErroreDrive as errore:
        raise ValidationError(str(errore)) from errore
    return conferma(allegato, utente, SalvatoSu.DRIVE, firmata_il)
