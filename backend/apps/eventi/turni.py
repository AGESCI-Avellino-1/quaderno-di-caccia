"""Turns of the patrols and of the sestiglie (DEC-312).

The staff chooses the turns (cleaning, prayer…) of a reparto or of a branco/cerchio, also
with the unit linked to it; they go round its patrols or sestiglie. Weekly, one step at
every meeting of the unit held (a week without meetings, or a cancelled meeting, does not
count); monthly, one step at the first meeting of each month. At step p turn j goes to
group (j + p) mod the number of groups. The staff may give one turn of one meeting to
another group (`TurnoCambiato`): the rotation goes on as planned afterwards.
"""

from bisect import bisect_left
from datetime import date

from django.db.models import Q
from django.utils import timezone

from apps.anagrafica.models import AppartenenzaSquadriglia
from apps.organizzazione.models import Squadriglia, TipoUnita, Unita

from .models import (
    Cerchia,
    Evento,
    Livello,
    MembroSestiglia,
    Rotazione,
    Sestiglia,
    TipoEvento,
    TurniUnita,
    TurnoCambiato,
)

LC = {TipoUnita.BRANCO, TipoUnita.CERCHIO, TipoUnita.BRANCO_CERCHIO}


def unita_con_turni(unita: Unita) -> bool:
    return unita.tipo == TipoUnita.REPARTO or unita.tipo in LC


def unita_dei_turni(conf: TurniUnita) -> list[Unita]:
    unita = [conf.unita]
    if conf.con_collegata and conf.unita.collegata_a_id:
        unita.append(conf.unita.collegata_a)
    return unita


def gruppi(conf: TurniUnita) -> list[Squadriglia | Sestiglia]:
    """The patrols or sestiglie the turns go round, in a fixed order."""
    unita = unita_dei_turni(conf)
    if conf.unita.tipo == TipoUnita.REPARTO:
        return list(
            Squadriglia.objects.filter(unita__in=unita, attiva=True).order_by("unita_id", "nome")
        )
    return list(Sestiglia.objects.filter(unita__in=unita, attiva=True).order_by("unita_id", "nome"))


def _riunioni(conf: TurniUnita):
    """The meetings of the whole unit, held, from the start of the turns."""
    return (
        Evento.objects.filter(
            tipo=TipoEvento.RIUNIONE,
            livello=Livello.UNITA,
            cerchia=Cerchia.TUTTI,
            unita=conf.unita,
            annullato_il__isnull=True,
            inizio__date__gte=conf.dal,
        )
        .distinct()
        .order_by("inizio")
    )


def _passo(conf: TurniUnita, evento: Evento, inizi: list) -> int:
    if conf.rotazione == Rotazione.SETTIMANALE:
        return bisect_left(inizi, evento.inizio)
    mesi = sorted({(timezone.localtime(i).year, timezone.localtime(i).month) for i in inizi})
    inizio = timezone.localtime(evento.inizio)
    return bisect_left(mesi, (inizio.year, inizio.month))


def _in_cache(cache: dict | None, chiave, calcola):
    """`cache`: one per request, so a list of meetings asks the database once."""
    if cache is None:
        return calcola()
    if chiave not in cache:
        cache[chiave] = calcola()
    return cache[chiave]


def configurazione(evento: Evento, cache: dict | None = None) -> TurniUnita | None:
    """The turns this meeting carries, if any: a meeting of the whole unit, held."""
    if (
        evento.tipo != TipoEvento.RIUNIONE
        or evento.livello != Livello.UNITA
        or evento.cerchia != Cerchia.TUTTI
        or evento.annullato_il
    ):
        return None
    for unita in evento.unita.all():
        conf = _in_cache(
            cache,
            ("conf", unita.pk),
            lambda u=unita: TurniUnita.objects.filter(
                Q(unita=u) | Q(unita_id=u.collegata_a_id, con_collegata=True)
            )
            .select_related("unita__collegata_a")
            .first(),
        )
        if conf and conf.nomi and timezone.localdate(evento.inizio) >= conf.dal:
            return conf
    return None


def assegnazioni(
    evento: Evento, conf: TurniUnita | None = None, inizi=None, cache: dict | None = None
) -> list[dict]:
    """Each turn of the meeting and the group that has it."""
    conf = conf or configurazione(evento, cache)
    if conf is None:
        return []
    elenco = _in_cache(cache, ("gruppi", conf.pk), lambda: gruppi(conf))
    if not elenco:
        return []
    if inizi is None:
        inizi = _in_cache(
            cache,
            ("inizi", conf.pk),
            lambda: list(_riunioni(conf).values_list("inizio", flat=True)),
        )
    passo = _passo(conf, evento, inizi)
    cambiati = {
        c.turno: c.squadriglia or c.sestiglia
        for c in TurnoCambiato.objects.filter(evento=evento).select_related(
            "squadriglia", "sestiglia"
        )
    }
    risultato = []
    for j, nome in enumerate(conf.nomi):
        gruppo = cambiati.get(nome) or elenco[(j + passo) % len(elenco)]
        risultato.append({"turno": nome, "gruppo": gruppo, "cambiato": nome in cambiati})
    return risultato


def gruppi_di(persone_ids: list[int], giorno: date) -> set[tuple[str, int]]:
    """The patrols and sestiglie of these people on `giorno`: ("sq", id), ("se", id)."""
    squadriglie = (
        AppartenenzaSquadriglia.objects.attive(giorno)
        .filter(persona_id__in=persone_ids)
        .values_list("squadriglia_id", flat=True)
    )
    sestiglie = (
        MembroSestiglia.objects.filter(persona_id__in=persone_ids, data_inizio__lte=giorno)
        .filter(Q(data_fine__isnull=True) | Q(data_fine__gt=giorno))
        .values_list("sestiglia_id", flat=True)
    )
    return {("sq", i) for i in squadriglie} | {("se", i) for i in sestiglie}


def chiave(gruppo) -> tuple[str, int]:
    return ("sq" if isinstance(gruppo, Squadriglia) else "se", gruppo.pk)


def nome_gruppo(gruppo) -> str:
    return str(gruppo)
