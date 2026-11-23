"""Birthdays (DEC-417): of the active ragazzi/e and capi only, never of the parents. Who sees
whose is decided in `policy.compleanni_visibili` and `policy.compleanni_notificati`."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from django.db.models import QuerySet

from .models import Appartenenza, Persona, RuoloAppartenenza


def soci_attivi() -> QuerySet[Persona]:
    """Who is in a unit or in the Co.Ca. today. Out: the suspended and who left (no open
    membership), who is still on the waiting list (no membership at all) and who has a
    registration from the app still to complete (DEC-125)."""
    from apps.iscrizioni.models import RichiestaIscrizione, StatoIscrizione

    da_completare = RichiestaIscrizione.objects.filter(
        stato__in=(StatoIscrizione.APPROVATA, StatoIscrizione.SOSPESA), persona__isnull=False
    ).values("persona_id")
    attive = Appartenenza.objects.attive().values("persona_id")
    return Persona.objects.filter(pk__in=attive, data_nascita__isnull=False).exclude(
        pk__in=da_completare
    )


def compleanno_nel(nascita: date, anno: int) -> date:
    """Who was born on 29 February has the birthday on the 28th in the other years
    [da verificare]."""
    try:
        return nascita.replace(year=anno)
    except ValueError:
        return date(anno, 2, 28)


@dataclass(frozen=True)
class Compleanno:
    persona: Persona
    giorno: date
    anni: int


def compleanni_tra(persone, dal: date, al: date) -> list[Compleanno]:
    """The birthdays from `dal` to `al`, both included, by day and then by name."""
    elenco = []
    for persona in persone:
        for anno in range(dal.year, al.year + 1):
            giorno = compleanno_nel(persona.data_nascita, anno)
            if dal <= giorno <= al and anno > persona.data_nascita.year:
                elenco.append(Compleanno(persona, giorno, anno - persona.data_nascita.year))
    return sorted(elenco, key=lambda c: (c.giorno, c.persona.cognome, c.persona.nome))


def unita_e_coca(persone_ids) -> tuple[dict[int, str], set[int]]:
    """Each person's units today, as they are always shown (DEC-128), and who is in the
    Co.Ca."""
    attive = (
        Appartenenza.objects.attive()
        .filter(persona_id__in=persone_ids)
        .select_related("unita")
        .order_by("unita__tipo", "unita_id")
    )
    unita: dict[int, list[str]] = defaultdict(list)
    coca: set[int] = set()
    for appartenenza in attive:
        nome = str(appartenenza.unita)
        if nome not in unita[appartenenza.persona_id]:
            unita[appartenenza.persona_id].append(nome)
        if appartenenza.ruolo == RuoloAppartenenza.CAPO:
            coca.add(appartenenza.persona_id)
    return {pk: ", ".join(nomi) for pk, nomi in unita.items()}, coca


def testo_notifica(nomi: list[str]) -> str:
    """First names only: the notification is read on a locked phone (DEC-345, DEC-417)."""
    if len(nomi) == 1:
        return f"Oggi compie gli anni {nomi[0]}"
    if len(nomi) <= 3:
        return f"Oggi compiono gli anni {', '.join(nomi[:-1])} e {nomi[-1]}"
    return f"Oggi compiono gli anni {nomi[0]}, {nomi[1]} e altri {len(nomi) - 2}"
