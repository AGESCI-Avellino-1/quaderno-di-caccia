"""Domain services for people. Views, API and imports call these, never the ORM ad hoc."""

from django.db import transaction
from django.db.models import QuerySet

from .models import CAMPI_BUONASTRADA, CorrezioneAnagrafica, Persona, StatoCorrezione


def fratelli(persona: Persona) -> QuerySet[Persona]:
    """Members who share at least one guardian with `persona` (DEC-33).

    Guardians are identified by their Persona record, which imports deduplicate by
    codice fiscale, so 'same guardian' means 'same codice fiscale'.
    """
    tutori = persona.tutori.values_list("tutore_id", flat=True)
    return Persona.objects.filter(tutori__tutore_id__in=tutori).exclude(pk=persona.pk).distinct()


@transaction.atomic
def correggi_campo(persona: Persona, campo: str, valore, richiesta_da=None) -> CorrezioneAnagrafica:
    """Apply a correction to a BuonaStrada-owned field and track it (DEC-31)."""
    if campo not in CAMPI_BUONASTRADA:
        raise ValueError(f"Il campo {campo} non è gestito da BuonaStrada.")
    precedente = getattr(persona, campo)
    correzione, _ = CorrezioneAnagrafica.objects.update_or_create(
        persona=persona,
        campo=campo,
        stato=StatoCorrezione.IN_ATTESA,
        defaults={
            "valore_precedente": "" if precedente is None else str(precedente),
            "valore_corretto": "" if valore is None else str(valore),
            "richiesta_da": richiesta_da,
        },
    )
    setattr(persona, campo, valore)
    persona.save(update_fields=[campo, "aggiornato_il"])
    return correzione
