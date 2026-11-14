"""The invitees of the events and meetings to come follow who is in the units (DEC-414).

Whatever changes who is in a unit, a patrol, a role or the Alta Squadriglia (the import from
BuonaStrada, passages, joining, leaving, the draft of the patrols) ends here through the
signals below: once per transaction, after it commits, for the units touched and for the
group's and branch's events. Who arrives is invited to what is still to come; who left is no
longer invited to it, unless they have a mark of attendance or a fee there; who was left out
by hand with a reason stays out. The past stays as it is. Events on BuonaCaccia have their
participants one by one and are never touched.
"""

import threading

from django.db import transaction
from django.db.models import Q
from django.db.models.signals import post_delete, post_save
from django.utils import timezone

from .models import Evento, Livello, StatoPartecipazione

_in_attesa = threading.local()


def riallinea(unita_ids: set[int] | None = None) -> tuple[int, int]:
    """The events to come of these units (all of them with None), and the group's and
    branch's; returns how many invitations were added and removed."""
    from apps.quote.models import Quota

    from . import servizi

    eventi = Evento.objects.filter(fine__gte=timezone.now(), annullato_il__isnull=True).exclude(
        livello=Livello.ESTERNO
    )
    if unita_ids is not None:
        eventi = eventi.filter(
            Q(livello__in=(Livello.GRUPPO, Livello.BRANCA))
            | Q(unita__in=unita_ids)
            | Q(squadriglia__unita__in=unita_ids)
        ).distinct()
    aggiunti = tolti = 0
    for evento in eventi:
        prima = evento.partecipazioni.count()
        servizi.allinea_partecipanti(evento)
        aggiunti += evento.partecipazioni.count() - prima
        tolti += (
            evento.partecipazioni.exclude(persona__in=servizi.previsti(evento))
            .exclude(persona__in=evento.presenze.values("persona_id"))
            .exclude(persona__in=Quota.objects.filter(tipo__evento=evento).values("persona_id"))
            .filter(stato__in=(StatoPartecipazione.INVITATO, StatoPartecipazione.NON_PARTECIPA))
            .delete()[0]
        )
    return aggiunti, tolti


def _esegui() -> None:
    unita_ids = getattr(_in_attesa, "unita", None) or set()
    _in_attesa.unita = None
    if unita_ids:
        riallinea(unita_ids)


def programma(*unita_ids: int | None) -> None:
    """After the commit: the first call does the work for the whole transaction, the others
    find nothing left to do. A rolled back transaction leaves only extra units."""
    attese = getattr(_in_attesa, "unita", None)
    if attese is None:
        attese = _in_attesa.unita = set()
    attese.update(u for u in unita_ids if u)
    transaction.on_commit(_esegui)


def _da_appartenenza(sender, instance, **kwargs) -> None:
    programma(instance.unita_id)


def _reparto_di(squadriglia_id: int | None) -> int | None:
    """By query: in a cascade the patrol object may be gone already."""
    from apps.organizzazione.models import Squadriglia

    if squadriglia_id is None:
        return None
    return Squadriglia.objects.filter(pk=squadriglia_id).values_list("unita_id", flat=True).first()


def _da_squadriglia(sender, instance, **kwargs) -> None:
    programma(_reparto_di(instance.squadriglia_id))


def _da_incarico(sender, instance, **kwargs) -> None:
    programma(instance.unita_id, _reparto_di(instance.squadriglia_id))


def _da_alta_squadriglia(sender, instance, **kwargs) -> None:
    programma(instance.reparto_id)


def _da_passaggio(sender, instance, **kwargs) -> None:
    programma(instance.unita_origine_id, instance.unita_destinazione_id)


def _da_persona_del_passaggio(sender, instance, **kwargs) -> None:
    from apps.progressione.models import Passaggio

    passaggio = (
        Passaggio.objects.filter(pk=instance.passaggio_id)
        .values_list("unita_origine_id", "unita_destinazione_id")
        .first()
    )
    if passaggio:
        programma(*passaggio)


def collega() -> None:
    from apps.anagrafica.models import Appartenenza, AppartenenzaSquadriglia
    from apps.organizzazione.models import Incarico
    from apps.progressione.models import Passaggio, PassaggioPersona

    from .models import MembroAltaSquadriglia

    for modello, ricevitore in (
        (Appartenenza, _da_appartenenza),
        (AppartenenzaSquadriglia, _da_squadriglia),
        (Incarico, _da_incarico),
        (MembroAltaSquadriglia, _da_alta_squadriglia),
        # A passage prepared, moved or cancelled (DEC-414).
        (Passaggio, _da_passaggio),
        (PassaggioPersona, _da_persona_del_passaggio),
    ):
        for segnale in (post_save, post_delete):
            segnale.connect(ricevitore, sender=modello, dispatch_uid=f"dec414-{modello.__name__}")
