"""What follows a ragazzo leaving a reparto (DEC-65), and the end of a unit.

The patrol is the basic body of the reparto: every ragazzo of the reparto is in one,
and whoever leaves the reparto leaves the patrol (DEC-133).

A closed unit is deleted only when nothing refers to it (created by mistake, DEC-273);
with only archived people in its history it is archived instead, and comes back when
one of them returns (DEC-275).
"""

from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction

from apps.anagrafica.models import (
    Appartenenza,
    AppartenenzaSquadriglia,
    DerogaSquadriglia,
    Persona,
)
from apps.anagrafica.preferenze import accetta
from apps.impostazioni.email import invia
from apps.notifiche.servizi import notifica
from apps.permessi import policy

from .models import RUOLI_DI_SQUADRIGLIA, Incarico, RuoloIncarico, Squadriglia, TipoUnita, Unita


def _chiudi(periodo, giorno: date) -> None:
    """End a period on `giorno` (exclusive); one starting that day never took effect."""
    if periodo.data_inizio >= giorno:
        periodo.delete()
    else:
        periodo.data_fine = giorno
        periodo.save(update_fields=["data_fine", "aggiornato_il"])


def esci_dal_reparto(persona: Persona, unita: Unita, giorno: date) -> list[str]:
    """Close patrol membership, patrol roles and patrol exceptions tied to `unita`,
    and the Consiglio degli Anziani of a branco or cerchio.

    Returns what was closed, for the import summary. Exceptions are not listed there:
    they are special-category data and the summary is read by the technical
    administrator too.
    """
    chiusi = []
    # Leaving a branco or cerchio ends the Consiglio degli Anziani (DEC-182).
    for incarico in Incarico.objects.attivi(giorno).filter(
        persona=persona, ruolo=RuoloIncarico.CONSIGLIO_ANZIANI, unita=unita
    ):
        _chiudi(incarico, giorno)
        chiusi.append(f"{persona} — {incarico.get_ruolo_display()}")
    # And the sestiglia (DEC-312).
    from apps.eventi.models import MembroSestiglia

    for membro in (
        MembroSestiglia.objects.filter(persona=persona, sestiglia__unita=unita)
        .filter(models.Q(data_fine__isnull=True) | models.Q(data_fine__gt=giorno))
        .select_related("sestiglia")
    ):
        _chiudi(membro, giorno)
        chiusi.append(f"{persona} — {membro.sestiglia}")
    if unita.tipo != TipoUnita.REPARTO:
        return chiusi
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


# --- The end of a unit (DEC-273, DEC-275) ------------------------------------------------


def _persone_non_archiviate(unita: Unita) -> models.QuerySet:
    return Appartenenza.objects.filter(unita=unita, persona__archiviazioni__isnull=True)


def unita_da_archiviare() -> models.QuerySet:
    """Closed units with someone in their history, all of them archived (DEC-275)."""
    return (
        Unita.objects.filter(attiva=False, archiviata_il__isnull=True, appartenenze__isnull=False)
        .exclude(appartenenze__persona__archiviazioni__isnull=True)
        .distinct()
    )


def archivia_unita(unita: Unita, oggi: date | None = None) -> None:
    if unita.attiva:
        raise ValidationError("Prima chiudi l'unità.")
    if _persone_non_archiviate(unita).exists():
        raise ValidationError(
            "Nello storico dell'unità c'è ancora qualcuno che non è stato archiviato."
        )
    if not unita.appartenenze.exists():
        raise ValidationError("Nell'unità non c'è mai stato nessuno: si può eliminare.")
    unita.archiviata_il = oggi or date.today()
    unita.save(update_fields=["archiviata_il", "aggiornato_il"])


def ripristina_unita(unita: Unita) -> bool:
    """Back among the closed units (DEC-275). True if it was archived."""
    if unita.archiviata_il is None:
        return False
    unita.archiviata_il = None
    unita.save(update_fields=["archiviata_il", "aggiornato_il"])
    return True


def ripristina_unita_di(persona: Persona) -> list[Unita]:
    """Someone archived comes back: the archived units of their history come back too,
    still closed (DEC-275)."""
    unita = Unita.objects.filter(appartenenze__persona=persona, archiviata_il__isnull=False)
    return [u for u in unita.distinct() if ripristina_unita(u)]


def _collegati(unita: Unita) -> list[str]:
    """What still refers to the unit, by name; what is only unlinked (SET_NULL) does not
    count."""
    collegati = []
    for relazione in Unita._meta.get_fields(include_hidden=True):
        if not (relazione.auto_created and not relazione.concrete):
            continue  # not a reverse relation
        if getattr(relazione, "on_delete", None) is models.SET_NULL:
            continue
        modello = relazione.related_model
        if modello._meta.auto_created:
            continue  # a many-to-many table: its model is counted by the other relation
        if modello._default_manager.filter(**{relazione.field.name: unita}).exists():
            collegati.append(str(modello._meta.verbose_name_plural))
    return sorted(set(collegati))


def cancella_unita(unita: Unita) -> None:
    """Only a closed unit nobody was ever in and nothing refers to: created by mistake
    (DEC-273)."""
    if unita.attiva:
        raise ValidationError("Prima chiudi l'unità.")
    if unita.appartenenze.exists():
        raise ValidationError(
            "Nell'unità c'è stato qualcuno: non si può eliminare. Quando tutte le persone "
            "del suo storico saranno archiviate, potrai archiviarla."
        )
    collegati = _collegati(unita)
    if collegati:
        raise ValidationError(
            f"All'unità sono ancora collegati: {', '.join(collegati)}. Non si può eliminare."
        )
    from apps.fascicolo.models import ServizioPassato

    with transaction.atomic():
        # A year rebuilt by hand keeps the unit by name (DEC-207).
        for servizio in ServizioPassato.objects.filter(unita=unita):
            servizio.unita_testo = str(unita)
            servizio.save(update_fields=["unita_testo", "aggiornato_il"])
        unita.delete()


# --- Linked units (DEC-36, DEC-279) ---------------------------------------------------------


def nome_provvisorio(unita: Unita) -> str:
    """ "Nuova Squadriglia" with the first number free among the active patrols (DEC-409)."""
    presi = set(unita.squadriglie.filter(attiva=True).values_list("nome", flat=True))
    n = 1
    while f"Nuova Squadriglia {n}" in presi:
        n += 1
    return f"Nuova Squadriglia {n}"


def avvisa_animale_scelto(squadriglia: Squadriglia) -> None:
    """Its CSQ chose the animal of a new patrol (DEC-409): an optional email and a
    notification to the reparto staff, who may correct it for a month."""
    staff = policy.staff_del_reparto(squadriglia.unita)
    percorso = f"/unita/{squadriglia.unita_id}"
    notifica("riepiloghi", staff, "Una squadriglia ha scelto il suo animale", percorso)
    invia(
        "animale_squadriglia",
        {
            "Squadriglia": squadriglia.nome,
            "Unità": str(squadriglia.unita),
            "Fino al": squadriglia.correggibile_fino().strftime("%d/%m/%Y"),
            "Link": f"{settings.FRONTEND_URL}{percorso}",
        },
        [p.utente.email for p in staff if p.utente_id and accetta(p, "riepiloghi")],
    )


def collega(unita: Unita, altra: Unita | None, nota: str = "") -> None:
    """Link two units both ways, or unlink them (`altra` None).

    Units are linked in pairs: changing a link means removing the old one first, on
    purpose, so neither side loses a link without anyone noticing. Only active units are
    linked. The note is the same on both sides. `unita` must be saved.
    """
    nota = nota.strip()
    attuale = unita.collegata_a
    if unita.cassa_comune_dal and (altra is None or altra.pk != getattr(attuale, "pk", None)):
        raise ValidationError(
            "Queste unità hanno la cassa in comune: dividi prima le casse, poi cambia il "
            "collegamento."
        )
    with transaction.atomic():
        if altra is None:
            if attuale is not None and attuale.collegata_a_id == unita.pk:
                attuale.collegata_a, attuale.nota_collegamento = None, ""
                attuale.save(update_fields=["collegata_a", "nota_collegamento", "aggiornato_il"])
            unita.collegata_a, unita.nota_collegamento = None, ""
        else:
            if altra.pk == unita.pk:
                raise ValidationError("Un'unità non può essere collegata a sé stessa.")
            if attuale is not None and attuale.pk != altra.pk:
                raise ValidationError(
                    f"{unita} è già collegata a {attuale}: togli prima quel collegamento "
                    "(«Collegata a»: Nessuna), poi scegli la nuova unità."
                )
            if altra.collegata_a_id not in (None, unita.pk):
                raise ValidationError(
                    f"{altra} è già collegata a {altra.collegata_a}: togli prima quel "
                    "collegamento dalla sua pagina."
                )
            if attuale is None and (not altra.attiva or altra.archiviata_il):
                raise ValidationError("Si collegano solo unità attive.")
            altra.collegata_a, altra.nota_collegamento = unita, nota
            altra.save(update_fields=["collegata_a", "nota_collegamento", "aggiornato_il"])
            unita.collegata_a, unita.nota_collegamento = altra, nota
        unita.save(update_fields=["collegata_a", "nota_collegamento", "aggiornato_il"])
