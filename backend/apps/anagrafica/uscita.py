"""The exit from the group recorded in the app (DEC-420).

Who left the group goes out of the app without waiting for BuonaStrada: from the chosen day
the periods in the units, the patrol (and with it a CSQ equiparazione, DEC-419), the sestiglia,
the roles and the patrol exceptions end; the unpaid fees chosen are cancelled. Everything done
is kept in `UscitaDalGruppo.chiusure`, so that an undo puts it back. The exit goes to the
capigruppo as a correction to forward; the import closes it, or reports it as a difference
while BuonaStrada still has the person active.
"""

from datetime import date

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.core.chiusura import controlla_anno_aperto

from .models import (
    CAMPO_USCITA,
    Appartenenza,
    AppartenenzaSquadriglia,
    CorrezioneAnagrafica,
    DerogaSquadriglia,
    Persona,
    StatoCorrezione,
    UscitaDalGruppo,
)

MOTIVO_QUOTA = "Ha lasciato il gruppo"


def _modelli() -> dict:
    from apps.eventi.models import MembroSestiglia
    from apps.organizzazione.models import Incarico

    return {
        "appartenenza": Appartenenza,
        "squadriglia": AppartenenzaSquadriglia,
        "sestiglia": MembroSestiglia,
        "incarico": Incarico,
    }


def attiva(persona: Persona) -> UscitaDalGruppo | None:
    """The exit in force: recorded, not undone, and the person not back in a unit since
    (BuonaStrada brought them back after the office had recorded the exit)."""
    uscita = persona.uscite.filter(annullata_il__isnull=True).order_by("-data").first()
    if uscita is None:
        return None
    if Appartenenza.objects.attive().filter(persona=persona, data_inizio__gte=uscita.data).exists():
        return None
    return uscita


def quote_annullabili(persona: Persona) -> list:
    """Fees with nothing paid and no payment reported and waiting to be checked: only those
    may be cancelled (a fee with payments needs them cancelled first)."""
    from apps.quote.models import Quota, StatoSegnalazione

    return [
        quota
        for quota in Quota.objects.filter(persona=persona, annullata_il__isnull=True)
        .select_related("tipo")
        .order_by("periodo", "pk")
        if not quota.pagato
        and not quota.segnalazioni.filter(stato=StatoSegnalazione.IN_VERIFICA).exists()
    ]


def _aperti(modello, persona: Persona, giorno: date) -> QuerySet:
    """Periods still running on `giorno`, or starting later."""
    return modello.objects.filter(persona=persona).filter(
        Q(data_fine__isnull=True) | Q(data_fine__gt=giorno)
    )


def _campi(oggetto) -> dict:
    campi = {
        f.attname: getattr(oggetto, f.attname)
        for f in oggetto._meta.concrete_fields
        if f.attname not in ("creato_il", "aggiornato_il")
    }
    return {k: v.isoformat() if isinstance(v, date) else v for k, v in campi.items()}


def _chiudi(c: dict, chiave: str, periodo, giorno: date) -> None:
    """End a period on `giorno`; one starting that day or later is removed, kept here to
    be put back."""
    if periodo.data_inizio >= giorno:
        c["eliminati"].append({"modello": chiave, "campi": _campi(periodo)})
        periodo.delete()
        return
    fine = periodo.data_fine.isoformat() if periodo.data_fine else None
    c["chiusi"].append({"modello": chiave, "pk": periodo.pk, "data_fine": fine})
    periodo.data_fine = giorno
    periodo.save(update_fields=["data_fine", "aggiornato_il"])


def puo_essere_registrata(persona: Persona) -> bool:
    """In a unit today, or from a day to come, and not already out."""
    oggi = timezone.localdate()
    return attiva(persona) is None and _aperti(Appartenenza, persona, oggi).exists()


@transaction.atomic
def registra(persona: Persona, giorno: date, utente, quote_ids: list[int]) -> UscitaDalGruppo:
    persona = Persona.objects.select_for_update().get(pk=persona.pk)
    if giorno > timezone.localdate():
        raise ValidationError("Il giorno dell'uscita non può essere nel futuro.")
    if attiva(persona) is not None:
        raise ValidationError(f"L'uscita di {persona} è già registrata.")
    if not _aperti(Appartenenza, persona, giorno).exists():
        raise ValidationError(f"{persona} non è in nessuna unità da quel giorno.")
    controlla_anno_aperto(giorno)
    annullabili = {q.pk: q for q in quote_annullabili(persona)}
    if any(pk not in annullabili for pk in quote_ids):
        raise ValidationError("Una delle quote scelte non si può annullare: ha dei pagamenti.")
    c: dict = {"chiusi": [], "eliminati": [], "deroghe": [], "quote": []}
    for chiave, modello in _modelli().items():
        for periodo in _aperti(modello, persona, giorno):
            _chiudi(c, chiave, periodo, giorno)
    for deroga in DerogaSquadriglia.objects.filter(persona=persona, revocata_il__isnull=True):
        c["deroghe"].append(deroga.pk)
        deroga.revocata_il = max(giorno, deroga.data_decisione)
        deroga.save(update_fields=["revocata_il", "aggiornato_il"])
    from apps.quote.servizi import annulla_quota

    for pk in quote_ids:
        annulla_quota(annullabili[pk], utente, MOTIVO_QUOTA)
        c["quote"].append(pk)
    correzione = CorrezioneAnagrafica.objects.filter(
        persona=persona, campo=CAMPO_USCITA, stato__in=(StatoCorrezione.IN_ATTESA,)
    ).first() or CorrezioneAnagrafica(persona=persona, campo=CAMPO_USCITA)
    correzione.valore_precedente = "Nel gruppo"
    correzione.valore_corretto = f"Uscito/a dal gruppo il {giorno:%d/%m/%Y}"
    correzione.richiesta_da = utente
    correzione.stato = StatoCorrezione.IN_ATTESA
    correzione.segnalata_il = None
    correzione.full_clean()
    correzione.save()
    return UscitaDalGruppo.objects.create(
        persona=persona, data=giorno, registrata_da=utente, correzione=correzione, chiusure=c
    )


@transaction.atomic
def annulla(uscita: UscitaDalGruppo, utente, *, dalla_correzione: bool = False) -> None:
    """Back as before: periods, patrol, roles, exceptions and the fees cancelled. From the
    correction (discarded by a capogruppo, or BuonaStrada chosen at the import) it is that
    correction which closes; otherwise one still to forward goes away."""
    uscita = UscitaDalGruppo.objects.select_for_update().get(pk=uscita.pk)
    if uscita.annullata_il is not None:
        raise ValidationError("L'uscita è già stata annullata.")
    persona = uscita.persona
    if (
        Appartenenza.objects.filter(persona=persona, data_inizio__gte=uscita.data)
        .filter(Q(data_fine__isnull=True) | Q(data_fine__gt=timezone.localdate()))
        .exists()
    ):
        raise ValidationError(
            f"{persona} è di nuovo in un'unità dopo l'uscita: correggi a mano le unità."
        )
    c = uscita.chiusure or {}
    from apps.quote.models import Quota

    quote = list(Quota.objects.filter(pk__in=c.get("quote", [])))
    controlla_anno_aperto(uscita.data, *(q.periodo for q in quote))
    modelli = _modelli()
    for chiuso in c.get("chiusi", []):
        periodo = modelli[chiuso["modello"]].objects.filter(pk=chiuso["pk"]).first()
        if periodo is not None:
            periodo.data_fine = (
                date.fromisoformat(chiuso["data_fine"]) if chiuso["data_fine"] else None
            )
            periodo.save(update_fields=["data_fine", "aggiornato_il"])
    for eliminato in c.get("eliminati", []):
        campi = {
            k: date.fromisoformat(v) if k.startswith("data_") and v else v
            for k, v in eliminato["campi"].items()
        }
        modello = modelli[eliminato["modello"]]
        if not modello.objects.filter(pk=campi.get("id")).exists():
            modello.objects.create(**campi)
    for deroga in DerogaSquadriglia.objects.filter(pk__in=c.get("deroghe", [])):
        deroga.revocata_il = None
        deroga.save(update_fields=["revocata_il", "aggiornato_il"])
    for quota in quote:
        quota.annullata_il = None
        quota.annullata_da = None
        quota.motivo_annullamento = ""
        quota.save()
    correzione = uscita.correzione
    if not dalla_correzione and correzione is not None:
        if correzione.stato == StatoCorrezione.IN_ATTESA:
            uscita.correzione = None
            uscita.save(update_fields=["correzione", "aggiornato_il"])
            correzione.delete()  # never forwarded: nothing to tell the office
        elif correzione.aperta:
            correzione.stato = StatoCorrezione.SCARTATA
            correzione.motivo_scarto = "Uscita annullata nell'app."
            correzione.chiusa_il = timezone.now()
            correzione.chiusa_da = utente
            correzione.save()
    uscita.annullata_il = timezone.now()
    uscita.annullata_da = utente
    uscita.save(update_fields=["annullata_il", "annullata_da", "aggiornato_il"])
