"""The book and the Alta Squadriglia (DEC-439, DEC-440): an entry of the Alta Squadriglia belongs
to one of them, by name; its entry ceremony, who lived it by entering, the antechamber, which
does not read its entries until it enters, and the copies into a new one."""

import uuid
from datetime import date

from django.core.files.base import ContentFile
from django.db.models import Min

from apps.organizzazione.models import Unita

from .models import AllegatoVoce, VoceLibro


def reparti_dell_alta(unita_ids) -> set[int]:
    """The reparti and those linked to them: two linked reparti share one Alta Squadriglia."""
    ids = set(unita_ids)
    collegate = Unita.objects.filter(pk__in=ids, collegata_a__isnull=False).values_list(
        "collegata_a_id", flat=True
    )
    return ids | set(collegate)


def reparti_della_voce(voce: VoceLibro) -> set[int]:
    """The reparti of the Alta Squadriglia of an entry: their staffs write it."""
    if voce.alta_id is None:
        return set()
    return set(voce.alta.reparti())


def cerimonia_ingresso(reparto: Unita) -> int | None:
    """The entry ceremony of the Alta Squadriglia open for this reparto, while the book is on."""
    from apps.eventi.models import AltaSquadriglia
    from apps.impostazioni import funzioni

    if not funzioni.attiva(funzioni.CERIMONIE):
        return None
    return (
        VoceLibro.objects.filter(
            cerimonia_ingresso_alta=True, alta__in=AltaSquadriglia.objects.aperte_di(reparto)
        )
        .values_list("pk", flat=True)
        .first()
    )


def entrati_nell_alta(voce: VoceLibro) -> dict[int, date]:
    """For an entry ceremony: who ever entered its Alta Squadriglia, with the first day."""
    from apps.eventi.models import MembroAltaSquadriglia

    if not voce.cerimonia_ingresso_alta or voce.alta_id is None:
        return {}
    return dict(
        MembroAltaSquadriglia.objects.filter(alta_id=voce.alta_id, data_inizio__isnull=False)
        .values("persona_id")
        .annotate(primo=Min("data_inizio"))
        .values_list("persona_id", "primo")
    )


def ingressi_vissuti(persona_ids) -> dict[int, set[int]]:
    """The entry ceremonies each person lived by entering their Alta Squadriglia."""
    from apps.eventi.models import MembroAltaSquadriglia

    voci: dict[int, set[int]] = {}
    for voce, alta in VoceLibro.objects.filter(
        cerimonia_ingresso_alta=True, alta__isnull=False
    ).values_list("pk", "alta_id"):
        voci.setdefault(alta, set()).add(voce)
    vissuti: dict[int, set[int]] = {}
    if not voci:
        return vissuti
    for persona, alta in MembroAltaSquadriglia.objects.filter(
        persona_id__in=persona_ids, data_inizio__isnull=False, alta_id__in=list(voci)
    ).values_list("persona_id", "alta_id"):
        vissuti.setdefault(persona, set()).update(voci[alta])
    return vissuti


def voci_dell_anticamera(persona) -> set[int]:
    """The Alta Squadriglia's entries the person does not read: in its antechamber, not yet in
    (DEC-439), whatever the conditions or the choice by hand say."""
    from apps.eventi.models import MembroAltaSquadriglia

    alte = MembroAltaSquadriglia.objects.in_anticamera().filter(persona=persona).values("alta_id")
    return set(VoceLibro.objects.filter(alta__in=alte).values_list("pk", flat=True))


def _condizioni_per(condizioni: list, vecchia: int, nuova: int) -> list:
    """A condition on the old Alta Squadriglia asks for the new one in the copy."""
    return [
        [
            (
                {**c, "alta": nuova}
                if c.get("tipo") == "alta_squadriglia" and c.get("alta") == vecchia
                else c
            )
            for c in gruppo
        ]
        for gruppo in condizioni
    ]


def copia_voci(vecchia, nuova, ids: list[int]) -> list[VoceLibro]:
    """Entries of the old Alta Squadriglia copied into the new one (DEC-440): text, conditions and
    attachments, never the register nor who was added by hand; the old ones stay as they are."""
    copie = []
    for voce in VoceLibro.objects.filter(alta=vecchia, pk__in=ids):
        copia = VoceLibro.objects.create(
            titolo=voce.titolo,
            tipo=voce.tipo,
            ambito=voce.ambito,
            alta=nuova,
            testo=voce.testo,
            condizioni=_condizioni_per(voce.condizioni, vecchia.pk, nuova.pk),
            cerimonia_ingresso_alta=voce.cerimonia_ingresso_alta,
        )
        for allegato in voce.allegati.all():
            with allegato.file.open("rb") as aperto:
                contenuto = aperto.read()
            estensione = allegato.file.name.rsplit(".", 1)[-1]
            nuovo = AllegatoVoce(voce=copia, titolo=allegato.titolo, tipo_file=allegato.tipo_file)
            nuovo.file.save(f"{uuid.uuid4().hex}.{estensione}", ContentFile(contenuto), save=False)
            nuovo.save()
        copie.append(copia)
    return copie
