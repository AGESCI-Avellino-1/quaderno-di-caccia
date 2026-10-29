"""Domain services for people. Views, API and imports call these, never the ORM ad hoc."""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from .models import (
    CAMPI_BUONASTRADA,
    STATI_APERTI,
    ContatoreCodiceProvvisorio,
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


# --- Provisional codice socio (maintainer, 2026-10-29) ---------------------------------
# A member who joins from the app has no codice socio until the group enters them in
# BuonaStrada: they get 9 followed by a zero-padded progressive, 10 digits in all.
# Real codes have about 7 digits, so the two never clash; the import replaces the
# provisional code with the real one (found by codice fiscale): BuonaStrada wins.


def codice_fiscale_valido(codice: str) -> bool:
    """Format only (16 characters, letters and digits in their places): BuonaStrada
    checks it for real when the member is entered."""
    import re

    return bool(
        re.fullmatch(
            r"[A-Z]{6}[0-9LMNPQRSTUV]{2}[A-Z][0-9LMNPQRSTUV]{2}[A-Z][0-9LMNPQRSTUV]{3}[A-Z]",
            codice or "",
        )
    )


def e_codice_provvisorio(codice: str | None) -> bool:
    return bool(codice) and len(codice) == 10 and codice.startswith("9") and codice.isdigit()


@transaction.atomic
def nuovo_codice_provvisorio() -> str:
    contatore, _ = ContatoreCodiceProvvisorio.objects.select_for_update().get_or_create(pk=1)
    contatore.ultimo += 1
    contatore.save(update_fields=["ultimo"])
    return f"9{contatore.ultimo:09d}"


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


def supera_correzione(correzione: CorrezioneAnagrafica) -> None:
    """At import time BuonaStrada's value was chosen over the app's (maintainer,
    2026-10-29): the correction closes, whoever made it sees it on the person page."""
    correzione.stato = StatoCorrezione.SUPERATA
    correzione.chiusa_il = timezone.now()
    correzione.save()


def recepisci_correzione(correzione: CorrezioneAnagrafica) -> None:
    """The import found the corrected value in BuonaStrada (DEC-31)."""
    correzione.stato = StatoCorrezione.RECEPITA
    correzione.chiusa_il = timezone.now()
    correzione.save()


# --- Phones within the patrol (DEC-13, maintainer 2026-10-29) ------------------------


def genitori_con_telefono(persona: Persona) -> QuerySet[Persona]:
    """Parents and legal guardians with parental responsibility and a mobile number:
    the only numbers a child may share in the patrol (maintainer, 2026-10-29)."""
    return Persona.objects.filter(
        tutele__minore=persona, tutele__responsabilita_genitoriale=True
    ).exclude(cellulare="")


def telefono_di_famiglia(persona: Persona) -> Persona | None:
    """The parent whose mobile is shared by all their children without one."""
    return (
        genitori_con_telefono(persona)
        .filter(telefono_per_i_figli=True)
        .order_by("cognome", "nome")
        .first()
    )


def telefono_in_squadriglia(persona: Persona) -> tuple[str, Persona | None]:
    """The number the patrol uses for `persona` and, if it is a parent's, whose.

    BuonaStrada counts when it has the child's mobile (minors need not have one, and
    below R/S it cannot be entered); otherwise the parent chosen for this child, then
    the parent chosen for the whole family; otherwise no number (maintainer,
    2026-10-29). Hiding is not applied here: the CSQ sees the number anyway.
    """
    if persona.cellulare:
        return persona.cellulare, None
    genitore = persona.telefono_squadriglia_da
    if genitore is None or not genitore.cellulare:
        genitore = telefono_di_famiglia(persona)
    if genitore is not None:
        return genitore.cellulare, genitore
    return "", None


@transaction.atomic
def imposta_telefono_squadriglia(
    persona: Persona, genitore: Persona | None, nascosto: bool, per_tutti_i_figli: bool = False
) -> None:
    """`per_tutti_i_figli`: the parent's mobile becomes the family number, for every
    child of theirs without a phone (the other guardians stop being it)."""
    genitori = genitori_con_telefono(persona)
    if genitore is not None and not genitori.filter(pk=genitore.pk).exists():
        raise ValidationError("Si può scegliere solo il cellulare di un genitore o tutore.")
    if per_tutti_i_figli and genitore is not None:
        figli = Persona.objects.filter(tutori__tutore=genitore)
        Persona.objects.filter(tutele__minore__in=figli).exclude(pk=genitore.pk).update(
            telefono_per_i_figli=False
        )
        Persona.objects.filter(pk=genitore.pk).update(telefono_per_i_figli=True)
        genitore = None  # the family number applies
    persona.telefono_squadriglia_da = genitore
    persona.telefono_squadriglia_nascosto = nascosto
    persona.save(
        update_fields=["telefono_squadriglia_da", "telefono_squadriglia_nascosto", "aggiornato_il"]
    )
