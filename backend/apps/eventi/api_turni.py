"""Turns of the patrols and of the sestiglie, and the sestiglie themselves (DEC-312)."""

from datetime import date, datetime

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router, Schema
from ninja.errors import HttpError
from ninja.responses import Status

from apps.anagrafica.models import Appartenenza, Persona, RuoloAppartenenza
from apps.organizzazione.models import Squadriglia, Unita
from apps.permessi import policy

from . import turni
from .api import EventoOut, _evento_out
from .models import (
    MembroSestiglia,
    Rotazione,
    Sestiglia,
    TipoEvento,
    TurniUnita,
    TurnoCambiato,
)

router = Router(tags=["turni"])


def _unita(request, unita_id: int) -> Unita:
    unita = get_object_or_404(Unita, pk=unita_id)
    if not turni.unita_con_turni(unita):
        raise HttpError(400, "I turni sono di un reparto, di un branco o di un cerchio.")
    if not policy.puo_gestire_turni(request.auth, unita):
        raise HttpError(403, "I turni li stabilisce lo staff dell'unità.")
    return unita


# --- Turns -----------------------------------------------------------------------------------


class TurniIn(Schema):
    nomi: list[str]
    rotazione: Rotazione = Rotazione.SETTIMANALE
    dal: date
    con_collegata: bool = False


class AssegnazioneOut(Schema):
    turno: str
    gruppo: str


class ProssimaOut(Schema):
    id: int
    inizio: datetime
    turni: list[AssegnazioneOut]


class TurniOut(Schema):
    nomi: list[str]
    rotazione: Rotazione
    dal: date | None
    con_collegata: bool
    collegata: str | None
    gruppi: list[str]
    prossime: list[ProssimaOut]


def _turni_out(unita: Unita) -> dict:
    conf = TurniUnita.objects.filter(unita=unita).first()
    collegata = str(unita.collegata_a) if unita.collegata_a_id else None
    if conf is None:
        return {
            "nomi": [],
            "rotazione": Rotazione.SETTIMANALE,
            "dal": None,
            "con_collegata": False,
            "collegata": collegata,
            "gruppi": [],
            "prossime": [],
        }
    inizi = list(turni._riunioni(conf).values_list("inizio", flat=True))
    prossime = turni._riunioni(conf).filter(inizio__gte=timezone.now())[:6]
    return {
        "nomi": conf.nomi,
        "rotazione": conf.rotazione,
        "dal": conf.dal,
        "con_collegata": conf.con_collegata,
        "collegata": collegata,
        "gruppi": [str(g) for g in turni.gruppi(conf)],
        "prossime": [
            {
                "id": e.pk,
                "inizio": e.inizio,
                "turni": [
                    {"turno": a["turno"], "gruppo": str(a["gruppo"])}
                    for a in turni.assegnazioni(e, conf, inizi)
                ],
            }
            for e in prossime
        ],
    }


@router.get("/unita/{unita_id}/turni", response=TurniOut)
def turni_unita(request, unita_id: int):
    return _turni_out(_unita(request, unita_id))


@router.put("/unita/{unita_id}/turni", response=TurniOut)
def imposta_turni(request, unita_id: int, dati: TurniIn):
    unita = _unita(request, unita_id)
    nomi = list(dict.fromkeys(n.strip()[:80] for n in dati.nomi if n.strip()))
    if not nomi:
        TurniUnita.objects.filter(unita=unita).delete()
        return _turni_out(unita)
    TurniUnita.objects.update_or_create(
        unita=unita,
        defaults={
            "nomi": nomi,
            "rotazione": dati.rotazione,
            "dal": dati.dal,
            "con_collegata": dati.con_collegata and unita.collegata_a_id is not None,
        },
    )
    return _turni_out(unita)


class CambioTurno(Schema):
    turno: str
    # None for both: back to the rotation.
    squadriglia_id: int | None = None
    sestiglia_id: int | None = None


@router.put("/riunioni/{evento_id}/turni", response=EventoOut)
def cambia_turno(request, evento_id: int, dati: CambioTurno):
    """One turn of one meeting to another group; the rotation goes on as planned."""
    evento = get_object_or_404(
        policy.eventi_visibili(request.auth), pk=evento_id, tipo=TipoEvento.RIUNIONE
    )
    conf = turni.configurazione(evento)
    if conf is None or dati.turno not in conf.nomi:
        raise HttpError(400, "Questa riunione non ha questo turno.")
    if not policy.puo_gestire_turni(request.auth, conf.unita):
        raise HttpError(403, "I turni li stabilisce lo staff dell'unità.")
    gruppi = {turni.chiave(g): g for g in turni.gruppi(conf)}
    with transaction.atomic():
        TurnoCambiato.objects.filter(evento=evento, turno=dati.turno).delete()
        if dati.squadriglia_id or dati.sestiglia_id:
            chiave = (
                ("sq", dati.squadriglia_id) if dati.squadriglia_id else ("se", dati.sestiglia_id)
            )
            gruppo = gruppi.get(chiave)
            if gruppo is None:
                raise HttpError(400, "Scegli una squadriglia o una sestiglia dell'unità.")
            TurnoCambiato.objects.create(
                evento=evento,
                turno=dati.turno,
                squadriglia=gruppo if isinstance(gruppo, Squadriglia) else None,
                sestiglia=gruppo if isinstance(gruppo, Sestiglia) else None,
            )
    return _evento_out(request.auth, evento)


# --- Sestiglie -------------------------------------------------------------------------------


class Bambino(Schema):
    id: int
    nome: str
    cognome: str


class MembroOut(Schema):
    id: int
    persona: Bambino


class SestigliaOut(Schema):
    id: int
    nome: str
    membri: list[MembroOut]


class SestiglieOut(Schema):
    sestiglie: list[SestigliaOut]
    senza_sestiglia: list[Bambino]


def _sestiglie_out(unita: Unita) -> dict:
    oggi = timezone.localdate()
    attivi = _attivi(sestiglia__unita=unita, data_inizio__lte=oggi)
    attivi = attivi.select_related("persona").order_by("persona__cognome", "persona__nome")
    per_sestiglia: dict[int, list] = {}
    con_sestiglia = set()
    for m in attivi:
        per_sestiglia.setdefault(m.sestiglia_id, []).append(m)
        con_sestiglia.add(m.persona_id)
    bambini = Persona.objects.filter(
        pk__in=Appartenenza.objects.attive()
        .filter(unita=unita, ruolo=RuoloAppartenenza.RAGAZZO)
        .values("persona_id")
    ).order_by("cognome", "nome")
    return {
        "sestiglie": [
            {"id": s.pk, "nome": s.nome, "membri": per_sestiglia.get(s.pk, [])}
            for s in Sestiglia.objects.filter(unita=unita, attiva=True)
        ],
        "senza_sestiglia": [b for b in bambini if b.pk not in con_sestiglia],
    }


def _branco(request, unita_id: int) -> Unita:
    unita = _unita(request, unita_id)
    if unita.tipo not in turni.LC:
        raise HttpError(400, "Le sestiglie sono di un branco o di un cerchio.")
    return unita


@router.get("/unita/{unita_id}/sestiglie", response=SestiglieOut)
def sestiglie(request, unita_id: int):
    return _sestiglie_out(_branco(request, unita_id))


class NomeIn(Schema):
    nome: str


@router.post("/unita/{unita_id}/sestiglie", response={201: SestiglieOut})
def crea_sestiglia(request, unita_id: int, dati: NomeIn):
    unita = _branco(request, unita_id)
    nome = dati.nome.strip()[:80]
    if not nome:
        raise HttpError(400, "Scrivi il nome della sestiglia.")
    if Sestiglia.objects.filter(unita=unita, attiva=True, nome__iexact=nome).exists():
        raise HttpError(400, "C'è già una sestiglia con questo nome.")
    Sestiglia.objects.create(unita=unita, nome=nome)
    return Status(201, _sestiglie_out(unita))


def _chiudi_membro(membro: MembroSestiglia, giorno: date) -> None:
    if membro.data_inizio >= giorno:
        membro.delete()
    else:
        membro.data_fine = giorno
        membro.save(update_fields=["data_fine", "aggiornato_il"])


def _attivi(**filtri):
    oggi = timezone.localdate()
    return MembroSestiglia.objects.filter(**filtri).exclude(data_fine__lte=oggi)


@router.delete("/sestiglie/{sestiglia_id}", response=SestiglieOut)
def chiudi_sestiglia(request, sestiglia_id: int):
    sestiglia = get_object_or_404(Sestiglia, pk=sestiglia_id, attiva=True)
    unita = _branco(request, sestiglia.unita_id)
    oggi = timezone.localdate()
    with transaction.atomic():
        for membro in _attivi(sestiglia=sestiglia):
            _chiudi_membro(membro, oggi)
        sestiglia.attiva = False
        sestiglia.save(update_fields=["attiva", "aggiornato_il"])
    return _sestiglie_out(unita)


class MembroIn(Schema):
    persona_id: int


@router.post("/sestiglie/{sestiglia_id}/membri", response=SestiglieOut)
def metti_in_sestiglia(request, sestiglia_id: int, dati: MembroIn):
    """One sestiglia at a time: moving a child closes the other one."""
    sestiglia = get_object_or_404(Sestiglia, pk=sestiglia_id, attiva=True)
    unita = _branco(request, sestiglia.unita_id)
    if (
        not Appartenenza.objects.attive()
        .filter(persona_id=dati.persona_id, unita=unita, ruolo=RuoloAppartenenza.RAGAZZO)
        .exists()
    ):
        raise HttpError(400, "Si mettono in sestiglia solo i bambini dell'unità.")
    oggi = timezone.localdate()
    with transaction.atomic():
        for membro in _attivi(persona_id=dati.persona_id, sestiglia__unita=unita):
            _chiudi_membro(membro, oggi)
        MembroSestiglia.objects.create(
            sestiglia=sestiglia, persona_id=dati.persona_id, data_inizio=oggi
        )
    return _sestiglie_out(unita)


@router.delete("/sestiglie/membri/{membro_id}", response=SestiglieOut)
def togli_da_sestiglia(request, membro_id: int):
    membro = get_object_or_404(MembroSestiglia, pk=membro_id)
    unita = _branco(request, membro.sestiglia.unita_id)
    _chiudi_membro(membro, timezone.localdate())
    return _sestiglie_out(unita)
