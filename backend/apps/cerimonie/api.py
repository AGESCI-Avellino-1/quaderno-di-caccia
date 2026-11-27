"""The book of ceremonies and traditions (DEC-437), online only for now. Off in the settings,
none of it exists (DEC-421). Who reads an entry: `policy.voci_visibili`; who writes it:
`policy.puo_scrivere_voce`."""

import re

from django.db import transaction
from django.http import HttpResponse
from ninja import Router, Schema, Status
from ninja.errors import HttpError

from apps.anagrafica.models import Persona
from apps.anagrafica.servizi import con_unita
from apps.impostazioni import funzioni
from apps.impostazioni.html import in_testo, pulisci
from apps.organizzazione.models import Unita
from apps.permessi import policy

from .models import LUNGHEZZA_TESTO, TipoVoce, VoceLibro
from .stampa import pdf_voce

router = Router(tags=["cerimonie"])

NON_TROVATA = "Voce non trovata."


def _attiva() -> None:
    funzioni.richiedi(funzioni.CERIMONIE)


def _leggibile(request, voce_id: int) -> VoceLibro:
    _attiva()
    voce = policy.voci_visibili(request.auth).filter(pk=voce_id).select_related("unita").first()
    if voce is None:
        raise HttpError(404, NON_TROVATA)
    return voce


def _scrivibile(request, voce_id: int) -> VoceLibro:
    voce = _leggibile(request, voce_id)
    if not policy.puo_scrivere_voce(request.auth, voce):
        raise HttpError(403, "Questa voce la cambiano lo staff della sua unità e i capigruppo.")
    return voce


class UnitaScelta(Schema):
    id: int
    nome: str


class VoceBreve(Schema):
    id: int
    titolo: str
    tipo: str
    # «Tutto il gruppo» or the unit.
    unita: str
    cerimonia_del_totem: bool


class LibroOut(Schema):
    voci: list[VoceBreve]
    puo_scrivere: bool
    # Where a new entry may go; the group's only for the capigruppo.
    unita: list[UnitaScelta]
    puo_tutto_il_gruppo: bool


class VoceOut(VoceBreve):
    unita_id: int | None
    testo: str
    puo_modificare: bool
    # Who was added by hand: only for who may change the entry.
    aggiunti: list[int]


class Aggiungibile(Schema):
    id: int
    nome: str
    cognome: str
    unita: str


class VoceIn(Schema):
    titolo: str
    tipo: str = TipoVoce.CERIMONIA
    unita_id: int | None = None
    testo: str = ""
    aggiunti: list[int] = []
    # «La mia tribù» links to it: one entry of the whole group, set by the capigruppo.
    cerimonia_del_totem: bool = False


def _nome_unita(voce: VoceLibro) -> str:
    return str(voce.unita) if voce.unita_id else "Tutto il gruppo"


def _breve(voce: VoceLibro) -> dict:
    return {
        "id": voce.pk,
        "titolo": voce.titolo,
        "tipo": voce.tipo,
        "unita": _nome_unita(voce),
        "cerimonia_del_totem": voce.cerimonia_del_totem,
    }


def _voce_out(request, voce: VoceLibro) -> dict:
    puo = policy.puo_scrivere_voce(request.auth, voce)
    return {
        **_breve(voce),
        "unita_id": voce.unita_id,
        "testo": voce.testo,
        "puo_modificare": puo,
        "aggiunti": sorted(voce.aggiunti.values_list("pk", flat=True)) if puo else [],
    }


@router.get("/cerimonie", response=LibroOut)
def libro(request):
    _attiva()
    user = request.auth
    voci = policy.voci_visibili(user).select_related("unita")
    return {
        "voci": [_breve(v) for v in voci],
        "puo_scrivere": policy.puo_scrivere_voci(user),
        "unita": [{"id": u.pk, "nome": str(u)} for u in policy.unita_per_voci(user)],
        "puo_tutto_il_gruppo": policy.e_capogruppo(user),
    }


@router.get("/cerimonie/aggiungibili", response=list[Aggiungibile])
def aggiungibili(request):
    _attiva()
    if not policy.puo_scrivere_voci(request.auth):
        raise HttpError(403, "Le voci le scrivono lo staff delle unità e i capigruppo.")
    return con_unita(policy.aggiungibili_alle_voci(request.auth))


@router.get("/cerimonie/{voce_id}", response=VoceOut)
def voce(request, voce_id: int):
    return _voce_out(request, _leggibile(request, voce_id))


@router.get("/cerimonie/{voce_id}/pdf")
def voce_pdf(request, voce_id: int):
    voce = _leggibile(request, voce_id)
    risposta = HttpResponse(pdf_voce(voce.titolo, voce.testo), content_type="application/pdf")
    nome = re.sub(r"[^a-z0-9]+", "-", voce.titolo.lower()).strip("-") or "voce"
    risposta["Content-Disposition"] = f'attachment; filename="{nome}.pdf"'
    risposta["Cache-Control"] = "private, no-store"
    return risposta


def _unita_scelta(request, unita_id: int | None) -> Unita | None:
    if unita_id is None:
        if not policy.e_capogruppo(request.auth):
            raise HttpError(403, "Le voci di tutto il gruppo le scrivono i capigruppo.")
        return None
    unita = policy.unita_per_voci(request.auth).filter(pk=unita_id).first()
    if unita is None:
        raise HttpError(403, "Puoi scrivere le voci solo delle unità in cui sei in servizio.")
    return unita


def _aggiunti(request, ids: list[int], gia: set[int]) -> list[Persona]:
    """`gia`: already added, also by someone who may add more people (or who since left)."""
    possibili = set(policy.aggiungibili_alle_voci(request.auth).values_list("pk", flat=True))
    if not set(ids) <= possibili | gia:
        raise HttpError(400, "Non puoi aggiungere una di queste persone.")
    return list(Persona.objects.filter(pk__in=ids))


def _applica(request, voce: VoceLibro, dati: VoceIn, gia: set[int]) -> VoceLibro:
    titolo = " ".join(dati.titolo.split())
    if not titolo:
        raise HttpError(400, "Scrivi il titolo.")
    if len(titolo) > 200:
        raise HttpError(400, "Il titolo va scritto in breve: al massimo 200 caratteri.")
    if dati.tipo not in TipoVoce.values:
        raise HttpError(400, "Scegli se è una cerimonia o una tradizione.")
    testo = pulisci(dati.testo, immagini=False)
    # An editor left with empty paragraphs only: no text.
    if not in_testo(testo).strip():
        testo = ""
    if len(testo) > LUNGHEZZA_TESTO:
        raise HttpError(400, "Il testo è troppo lungo.")
    aggiunti = _aggiunti(request, dati.aggiunti, gia)
    voce.titolo, voce.tipo, voce.testo = titolo, dati.tipo, testo
    voce.unita = _unita_scelta(request, dati.unita_id)
    if dati.cerimonia_del_totem != voce.cerimonia_del_totem:
        if not policy.e_capogruppo(request.auth):
            raise HttpError(403, "La cerimonia del totem la sceglie un capogruppo.")
        if dati.cerimonia_del_totem and voce.unita_id is not None:
            raise HttpError(400, "La cerimonia del totem è una voce di tutto il gruppo.")
    elif voce.cerimonia_del_totem and voce.unita_id is not None:
        raise HttpError(400, "La cerimonia del totem è una voce di tutto il gruppo.")
    voce.cerimonia_del_totem = dati.cerimonia_del_totem
    with transaction.atomic():
        if voce.cerimonia_del_totem:
            # Only one: the one chosen now takes the place of the one before.
            VoceLibro.objects.filter(cerimonia_del_totem=True).exclude(pk=voce.pk).update(
                cerimonia_del_totem=False
            )
        voce.save()
        voce.aggiunti.set(aggiunti)
    return voce


@router.post("/cerimonie", response={201: VoceOut})
def crea(request, dati: VoceIn):
    _attiva()
    if not policy.puo_scrivere_voci(request.auth):
        raise HttpError(403, "Le voci le scrivono lo staff delle unità e i capigruppo.")
    voce = _applica(request, VoceLibro(), dati, set())
    return Status(201, _voce_out(request, voce))


@router.put("/cerimonie/{voce_id}", response=VoceOut)
def modifica(request, voce_id: int, dati: VoceIn):
    voce = _scrivibile(request, voce_id)
    gia = set(voce.aggiunti.values_list("pk", flat=True))
    return _voce_out(request, _applica(request, voce, dati, gia))


@router.delete("/cerimonie/{voce_id}", response={204: None})
def elimina(request, voce_id: int):
    _scrivibile(request, voce_id).delete()
    return Status(204, None)
