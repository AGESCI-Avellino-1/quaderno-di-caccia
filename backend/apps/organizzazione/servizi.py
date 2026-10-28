"""What follows a ragazzo leaving a reparto (DEC-65).

The patrol is the basic body of the reparto: every ragazzo of the reparto is in one,
and whoever leaves the reparto leaves the patrol (confirmed by the maintainer on
2026-10-28).
"""

from datetime import date

from apps.anagrafica.models import AppartenenzaSquadriglia, DerogaSquadriglia, Persona

from .models import RUOLI_DI_SQUADRIGLIA, Incarico, TipoUnita, Unita


def _chiudi(periodo, giorno: date) -> None:
    """End a period on `giorno` (exclusive); one starting that day never took effect."""
    if periodo.data_inizio >= giorno:
        periodo.delete()
    else:
        periodo.data_fine = giorno
        periodo.save(update_fields=["data_fine", "aggiornato_il"])


def esci_dal_reparto(persona: Persona, unita: Unita, giorno: date) -> list[str]:
    """Close patrol membership, CSQ/VCSQ roles and patrol exceptions tied to `unita`.

    Returns what was closed, for the import summary. Exceptions are not listed there:
    they are special-category data and the summary is read by the technical
    administrator too.
    """
    if unita.tipo != TipoUnita.REPARTO:
        return []
    chiusi = []
    for membro in (
        AppartenenzaSquadriglia.objects.attive(giorno)
        .filter(persona=persona, squadriglia__unita=unita)
        .select_related("squadriglia")
    ):
        _chiudi(membro, giorno)
        chiusi.append(f"{persona} — {membro.squadriglia}")
    for incarico in Incarico.objects.attivi(giorno).filter(
        persona=persona, ruolo__in=RUOLI_DI_SQUADRIGLIA, squadriglia__unita=unita
    ):
        _chiudi(incarico, giorno)
        chiusi.append(f"{persona} — {incarico.get_ruolo_display()}")
    for deroga in DerogaSquadriglia.objects.filter(
        persona=persona, reparto=unita, revocata_il__isnull=True
    ):
        deroga.revocata_il = giorno
        deroga.save(update_fields=["revocata_il", "aggiornato_il"])
    return chiusi
