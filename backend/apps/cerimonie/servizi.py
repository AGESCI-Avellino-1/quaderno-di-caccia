"""The book and the Alta Squadriglia (DEC-439): its entry ceremony, who lived it by entering,
and the antechamber, which does not read the Alta Squadriglia's entries until it enters."""

from datetime import date

from django.db.models import Min

from apps.organizzazione.models import Unita

from .models import AmbitoVoce, VoceLibro


def reparti_dell_alta(unita_ids) -> set[int]:
    """The reparti and those linked to them: two linked reparti share one Alta Squadriglia."""
    ids = set(unita_ids)
    collegate = Unita.objects.filter(pk__in=ids, collegata_a__isnull=False).values_list(
        "collegata_a_id", flat=True
    )
    return ids | set(collegate)


def reparti_della_voce(voce: VoceLibro) -> set[int]:
    if voce.ambito != AmbitoVoce.ALTA_SQUADRIGLIA:
        return set()
    return reparti_dell_alta(voce.unita.values_list("pk", flat=True))


def cerimonia_ingresso(reparto: Unita) -> int | None:
    """The entry ceremony of this reparto's Alta Squadriglia, while the book is on."""
    from apps.impostazioni import funzioni

    if not funzioni.attiva(funzioni.CERIMONIE):
        return None
    return (
        VoceLibro.objects.filter(
            cerimonia_ingresso_alta=True, unita__in=reparti_dell_alta([reparto.pk])
        )
        .values_list("pk", flat=True)
        .first()
    )


def entrati_nell_alta(voce: VoceLibro) -> dict[int, date]:
    """For an entry ceremony: who ever entered its Alta Squadriglia, with the first day."""
    from apps.eventi.models import MembroAltaSquadriglia

    if not voce.cerimonia_ingresso_alta:
        return {}
    return dict(
        MembroAltaSquadriglia.objects.filter(
            reparto_id__in=reparti_della_voce(voce), data_inizio__isnull=False
        )
        .values("persona_id")
        .annotate(primo=Min("data_inizio"))
        .values_list("persona_id", "primo")
    )


def ingressi_vissuti(persona_ids) -> dict[int, set[int]]:
    """The entry ceremonies each person lived by entering their Alta Squadriglia."""
    from apps.eventi.models import MembroAltaSquadriglia

    voci = {
        v.pk: reparti_dell_alta(v.unita.values_list("pk", flat=True))
        for v in VoceLibro.objects.filter(cerimonia_ingresso_alta=True)
    }
    vissuti: dict[int, set[int]] = {}
    if not voci:
        return vissuti
    for persona, reparto in MembroAltaSquadriglia.objects.filter(
        persona_id__in=persona_ids, data_inizio__isnull=False
    ).values_list("persona_id", "reparto_id"):
        for voce, reparti in voci.items():
            if reparto in reparti:
                vissuti.setdefault(persona, set()).add(voce)
    return vissuti


def voci_dell_anticamera(persona) -> set[int]:
    """The Alta Squadriglia's entries the person does not read: in its antechamber, not yet in
    (DEC-439), whatever the conditions or the choice by hand say."""
    from apps.eventi.models import MembroAltaSquadriglia

    anticamera = set(
        MembroAltaSquadriglia.objects.in_anticamera()
        .filter(persona=persona)
        .values_list("reparto_id", flat=True)
    )
    if not anticamera:
        return set()
    return {
        v.pk
        for v in VoceLibro.objects.filter(ambito=AmbitoVoce.ALTA_SQUADRIGLIA)
        if reparti_della_voce(v) & anticamera
    }
