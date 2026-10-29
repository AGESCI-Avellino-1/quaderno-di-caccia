"""Domain services for people. Views, API and imports call these, never the ORM ad hoc."""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from .models import (
    CAMPI_BUONASTRADA,
    STATI_APERTI,
    CorrezioneAnagrafica,
    Persona,
    StatoCorrezione,
)


def fratelli(persona: Persona) -> QuerySet[Persona]:
    """Members who share at least one guardian with `persona` (DEC-33).

    Guardians are identified by their Persona record, which imports deduplicate by
    codice fiscale, so 'same guardian' means 'same codice fiscale'.
    """
    tutori = persona.tutori.values_list("tutore_id", flat=True)
    return Persona.objects.filter(tutori__tutore_id__in=tutori).exclude(pk=persona.pk).distinct()


# --- Corrections to BuonaStrada data (DEC-31) ---------------------------------------


def come_testo(valore) -> str:
    """How a field value is stored in a correction (dates in ISO format, None empty)."""
    return "" if valore is None else str(valore)


def da_testo(campo: str, testo: str):
    """The field value back from its stored text."""
    field = Persona._meta.get_field(campo)
    if testo == "":
        return None if field.null else ""
    return field.to_python(testo)


def _valida(persona: Persona, campo: str) -> None:
    """Field validation (format, choices, uniqueness of the codice fiscale) only: the
    rest of the record comes from BuonaStrada and is not the user's to fix here."""
    altri = [f.name for f in Persona._meta.fields if f.name != campo]
    persona.full_clean(exclude=altri)


@transaction.atomic
def correggi_campo(persona: Persona, campo: str, valore, richiesta_da=None):
    """Apply a correction to a BuonaStrada-owned field and track it (DEC-31).

    `valore` may be text from the API: it is converted to the field type and validated
    (ValidationError). A second correction of the same field updates the open one and
    needs forwarding again; going back to BuonaStrada's value withdraws it. Returns the
    open correction, or None when nothing is left to forward.
    """
    if campo not in CAMPI_BUONASTRADA:
        raise ValidationError(f"Il campo {campo} non è gestito da BuonaStrada.")
    if isinstance(valore, str):
        valore = da_testo(campo, valore.strip())
    persona = Persona.objects.select_for_update().get(pk=persona.pk)
    attuale = getattr(persona, campo)
    if come_testo(attuale) == come_testo(valore):
        raise ValidationError("Il valore è uguale a quello attuale.")
    setattr(persona, campo, valore)
    _valida(persona, campo)
    valore = getattr(persona, campo)  # normalised by full_clean

    aperta = CorrezioneAnagrafica.objects.filter(
        persona=persona, campo=campo, stato__in=STATI_APERTI
    ).first()
    if aperta is not None and aperta.valore_precedente == come_testo(valore):
        aperta.delete()  # back to what BuonaStrada has: nothing to forward
        correzione = None
    elif aperta is not None:
        aperta.valore_corretto = come_testo(valore)
        aperta.richiesta_da = richiesta_da
        aperta.stato = StatoCorrezione.IN_ATTESA
        aperta.inoltrata_il = aperta.inoltrata_da = aperta.segnalata_il = None
        aperta.save()
        correzione = aperta
    else:
        correzione = CorrezioneAnagrafica.objects.create(
            persona=persona,
            campo=campo,
            valore_precedente=come_testo(attuale),
            valore_corretto=come_testo(valore),
            richiesta_da=richiesta_da,
        )
    persona.save(update_fields=[campo, "aggiornato_il"])
    return correzione


def inoltra_correzione(correzione: CorrezioneAnagrafica, utente) -> None:
    """A capogruppo sent it to the regional office (DEC-31)."""
    if correzione.stato != StatoCorrezione.IN_ATTESA:
        raise ValidationError("Questa correzione non è da inoltrare.")
    correzione.stato = StatoCorrezione.INOLTRATA
    correzione.inoltrata_il = timezone.now()
    correzione.inoltrata_da = utente
    correzione.save()


@transaction.atomic
def scarta_correzione(correzione: CorrezioneAnagrafica, utente, motivo: str) -> None:
    """A capogruppo discards it: the previous value comes back (maintainer, 2026-10-29)."""
    if not correzione.aperta:
        raise ValidationError("Questa correzione è già chiusa.")
    correzione.stato = StatoCorrezione.SCARTATA
    correzione.motivo_scarto = motivo.strip()
    correzione.chiusa_il = timezone.now()
    correzione.chiusa_da = utente
    correzione.full_clean()
    correzione.save()
    persona = correzione.persona
    setattr(persona, correzione.campo, da_testo(correzione.campo, correzione.valore_precedente))
    persona.save(update_fields=[correzione.campo, "aggiornato_il"])


def recepisci_correzione(correzione: CorrezioneAnagrafica) -> None:
    """The import found the corrected value in BuonaStrada (DEC-31)."""
    correzione.stato = StatoCorrezione.RECEPITA
    correzione.chiusa_il = timezone.now()
    correzione.save()
