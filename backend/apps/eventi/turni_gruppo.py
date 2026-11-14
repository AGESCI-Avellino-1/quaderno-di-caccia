"""Turns of the group that go round the units (DEC-406).

Set and changed by the capigruppo and the capi of the Co.Ca.: the units in their order,
the first day and the period (week, month, quarter). Period p goes to unit p mod the
number of units; one period may be given by hand to another unit (`PeriodoCambiato`), and
the rotation goes on as planned afterwards. Everyone in the units sees the turn on the
meetings of the unit that has it, in the app only (not in the iCal feed).
"""

from datetime import date, timedelta

from django.utils import timezone

from apps.organizzazione.models import Unita

from .models import Cerchia, Evento, Livello, PeriodoTurno, TipoEvento, TurnoGruppo

MESI = {PeriodoTurno.MESE: 1, PeriodoTurno.TRIMESTRE: 3}


def _mese(giorno: date, piu: int) -> date:
    """The first day of the month `piu` months after `giorno`'s."""
    n = giorno.year * 12 + giorno.month - 1 + piu
    return date(n // 12, n % 12 + 1, 1)


def indice(turno: TurnoGruppo, giorno: date) -> int | None:
    """Which period `giorno` falls in, from 0; None before the start."""
    if giorno < turno.dal:
        return None
    if turno.periodo == PeriodoTurno.SETTIMANA:
        return (giorno - turno.dal).days // 7
    mesi = (giorno.year - turno.dal.year) * 12 + giorno.month - turno.dal.month
    return mesi // MESI[turno.periodo]


def limiti(turno: TurnoGruppo, i: int) -> tuple[date, date]:
    """First and last day of period `i`; the first period starts on `dal`."""
    if turno.periodo == PeriodoTurno.SETTIMANA:
        inizio = turno.dal + timedelta(weeks=i)
        return inizio, inizio + timedelta(days=6)
    passo = MESI[turno.periodo]
    inizio = turno.dal if i == 0 else _mese(turno.dal, i * passo)
    return inizio, _mese(turno.dal, (i + 1) * passo) - timedelta(days=1)


def unita_del_turno(turno: TurnoGruppo) -> list[Unita]:
    """The units in their order; a unit deleted since is left out."""
    per_id = {u.pk: u for u in Unita.objects.filter(pk__in=turno.unita)}
    return [per_id[i] for i in turno.unita if i in per_id]


def assegnata(turno: TurnoGruppo, i: int, elenco: list[Unita], cambi: dict) -> Unita | None:
    if i in cambi:
        return cambi[i]
    return elenco[i % len(elenco)] if elenco else None


def _cambi(turno: TurnoGruppo) -> dict[int, Unita]:
    return {c.indice: c.unita for c in turno.cambi.select_related("unita")}


def turni_della_riunione(evento: Evento, cache: dict | None = None) -> list[dict]:
    """The group turns this meeting carries: those whose period falls on its day and
    belongs to one of its units. Only a meeting of the whole unit, held."""
    if (
        evento.tipo != TipoEvento.RIUNIONE
        or evento.livello != Livello.UNITA
        or evento.cerchia != Cerchia.TUTTI
        or evento.annullato_il
    ):
        return []
    cache = {} if cache is None else cache
    if "turni_gruppo" not in cache:
        cache["turni_gruppo"] = [
            (t, unita_del_turno(t), _cambi(t)) for t in TurnoGruppo.objects.all()
        ]
    giorno = timezone.localdate(evento.inizio)
    sue = {u.pk for u in evento.unita.all()}
    risultato = []
    for turno, elenco, cambi in cache["turni_gruppo"]:
        i = indice(turno, giorno)
        if i is None:
            continue
        unita = assegnata(turno, i, elenco, cambi)
        if unita is not None and unita.pk in sue:
            risultato.append({"turno": turno.nome, "unita": str(unita)})
    return risultato


def prossimi(turno: TurnoGruppo, quanti: int = 6, oggi: date | None = None) -> list[dict]:
    """The current period and the next ones, with their unit."""
    oggi = oggi or timezone.localdate()
    elenco = unita_del_turno(turno)
    cambi = _cambi(turno)
    primo = indice(turno, oggi) or 0
    risultato = []
    for i in range(primo, primo + quanti):
        dal, al = limiti(turno, i)
        unita = assegnata(turno, i, elenco, cambi)
        risultato.append(
            {
                "indice": i,
                "dal": dal,
                "al": al,
                "unita_id": unita.pk if unita else None,
                "unita": str(unita) if unita else "",
                "cambiato": i in cambi,
            }
        )
    return risultato
