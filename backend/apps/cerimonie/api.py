"""The book of ceremonies and traditions (DEC-437). Off in the settings, none of it exists
(DEC-421). Offline, the PWA keeps only the texts of the entries one reads (`/cerimonie/testi`,
encrypted on the device, DEC-97); attachments and the register are online only. Who reads an entry: `policy.voci_visibili`; who writes it:
`policy.puo_scrivere_voce`."""

import re
from datetime import date

from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from ninja import File, Form, Router, Schema, Status
from ninja.errors import HttpError
from ninja.files import UploadedFile

from apps.anagrafica.models import Persona
from apps.anagrafica.servizi import con_unita, unita_delle_persone
from apps.impostazioni import funzioni
from apps.impostazioni.html import in_testo, pulisci
from apps.organizzazione.models import TipoUnita, Unita
from apps.permessi import policy

from . import condizioni as cond
from .models import LUNGHEZZA_TESTO, AllegatoVoce, PartecipazioneVoce, TipoVoce, VoceLibro
from .stampa import pdf_voce

router = Router(tags=["cerimonie"])

NON_TROVATA = "Voce non trovata."

TIPI_ALLEGATO = {"application/pdf": ".pdf", "image/jpeg": ".jpg", "image/png": ".png"}


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


class Scelta(Schema):
    valore: str
    nome: str


class LibroOut(Schema):
    voci: list[VoceBreve]
    puo_scrivere: bool
    # Where a new entry may go; the group's only for the capigruppo.
    unita: list[UnitaScelta]
    puo_tutto_il_gruppo: bool
    # For the conditions, to who writes: every active unit and the roles one may ask for.
    unita_condizioni: list[UnitaScelta] = []
    incarichi: list[Scelta] = []


class Partecipante(Schema):
    id: int
    nome: str
    cognome: str
    unita: str
    data: date


class AllegatoOut(Schema):
    id: int
    titolo: str
    tipo_file: str


class VoceOut(VoceBreve):
    unita_id: int | None
    testo: str
    allegati: list[AllegatoOut]
    puo_modificare: bool
    # Who was added by hand and the conditions: only for who may change the entry.
    aggiunti: list[int]
    condizioni: list[list[dict]]
    # The register: every capo, and the participants of this entry.
    vede_registro: bool
    partecipanti: list[Partecipante]


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
    condizioni: list = []
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


def _registro(voce: VoceLibro) -> list[dict]:
    partecipazioni = list(voce.partecipazioni.select_related("persona"))
    unita = unita_delle_persone([p.persona for p in partecipazioni])
    return [
        {
            "id": p.persona_id,
            "nome": p.persona.nome,
            "cognome": p.persona.cognome,
            "unita": unita.get(p.persona_id, ""),
            "data": p.data,
        }
        for p in partecipazioni
    ]


def _voce_out(request, voce: VoceLibro) -> dict:
    puo = policy.puo_scrivere_voce(request.auth, voce)
    registro = policy.vede_registro_voce(request.auth, voce)
    return {
        "vede_registro": registro,
        "partecipanti": _registro(voce) if registro else [],
        **_breve(voce),
        "unita_id": voce.unita_id,
        "testo": voce.testo,
        "allegati": [
            {"id": a.pk, "titolo": a.titolo, "tipo_file": a.tipo_file} for a in voce.allegati.all()
        ],
        "puo_modificare": puo,
        "aggiunti": sorted(voce.aggiunti.values_list("pk", flat=True)) if puo else [],
        "condizioni": voce.condizioni if puo else [],
    }


@router.get("/cerimonie", response=LibroOut)
def libro(request):
    _attiva()
    user = request.auth
    voci = policy.voci_visibili(user).select_related("unita")
    scrive = policy.puo_scrivere_voci(user)
    attive = Unita.objects.filter(attiva=True, archiviata_il__isnull=True).exclude(
        tipo=TipoUnita.COMUNITA_CAPI
    )
    return {
        "voci": [_breve(v) for v in voci],
        "puo_scrivere": scrive,
        "unita": [{"id": u.pk, "nome": str(u)} for u in policy.unita_per_voci(user)],
        "puo_tutto_il_gruppo": policy.e_capogruppo(user),
        "unita_condizioni": [{"id": u.pk, "nome": str(u)} for u in attive] if scrive else [],
        "incarichi": (
            [{"valore": r.value, "nome": r.label} for r in cond.INCARICHI] if scrive else []
        ),
    }


class VoceTesto(VoceBreve):
    testo: str


@router.get("/cerimonie/testi", response=list[VoceTesto])
def testi(request):
    """The texts of every entry one reads, for the copy on the device: no register, no
    attachments, no conditions. Not while acting as another user (the copy is one's own)."""
    _attiva()
    return [
        {**_breve(v), "testo": v.testo}
        for v in policy.voci_visibili(request.auth).select_related("unita")
    ]


@router.get("/cerimonie/aggiungibili", response=list[Aggiungibile])
def aggiungibili(request):
    _attiva()
    if not policy.puo_scrivere_voci(request.auth):
        raise HttpError(403, "Le voci le scrivono lo staff delle unità e i capigruppo.")
    return con_unita(policy.aggiungibili_alle_voci(request.auth))


class AnteprimaIn(Schema):
    condizioni: list = []
    aggiunti: list[int] = []
    # The entry being changed: who is in its register reads it too.
    voce_id: int | None = None


@router.post("/cerimonie/anteprima", response=list[Aggiungibile])
def anteprima(request, dati: AnteprimaIn):
    """Who would read an entry today with these conditions: before saving (DEC-437)."""
    _attiva()
    if not policy.puo_scrivere_voci(request.auth):
        raise HttpError(403, "Le voci le scrivono lo staff delle unità e i capigruppo.")
    gruppi = _condizioni(dati.condizioni)
    voce = _leggibile(request, dati.voce_id) if dati.voce_id is not None else None
    return con_unita(policy.lettori_delle_condizioni(gruppi, dati.aggiunti, voce))


def _condizioni(gruppi: list) -> list[list[dict]]:
    try:
        return cond.pulisci(gruppi)
    except cond.CondizioneNonValida as errore:
        raise HttpError(400, str(errore)) from errore


@router.get("/cerimonie/segnabili", response=list[Aggiungibile])
def segnabili(request):
    _attiva()
    if not policy.puo_scrivere_voci(request.auth):
        raise HttpError(403, "Il registro lo segnano lo staff delle unità e i capigruppo.")
    return con_unita(policy.segnabili_nel_registro(request.auth))


class SegnaIn(Schema):
    persone: list[int]
    data: date


@router.post("/cerimonie/{voce_id}/partecipanti", response=VoceOut)
def segna(request, voce_id: int, dati: SegnaIn):
    """Who lived the entry on that day; someone already in the register gets the new day."""
    voce = _scrivibile(request, voce_id)
    if dati.data > date.today():
        raise HttpError(400, "Il giorno non può essere nel futuro.")
    if not dati.persone:
        raise HttpError(400, "Scegli chi l'ha vissuta.")
    possibili = set(policy.segnabili_nel_registro(request.auth).values_list("pk", flat=True))
    if not set(dati.persone) <= possibili:
        raise HttpError(400, "Non puoi segnare una di queste persone.")
    with transaction.atomic():
        for persona_id in set(dati.persone):
            PartecipazioneVoce.objects.update_or_create(
                voce=voce,
                persona_id=persona_id,
                defaults={"data": dati.data, "registrata_da": request.auth},
            )
    return _voce_out(request, voce)


@router.delete("/cerimonie/{voce_id}/partecipanti/{persona_id}", response=VoceOut)
def togli_partecipante(request, voce_id: int, persona_id: int):
    voce = _scrivibile(request, voce_id)
    voce.partecipazioni.filter(persona_id=persona_id).delete()
    return _voce_out(request, voce)


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
    voce.condizioni = _condizioni(dati.condizioni)
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
    voce = _scrivibile(request, voce_id)
    for allegato in voce.allegati.all():
        allegato.file.delete(save=False)
    voce.delete()
    return Status(204, None)


@router.post("/cerimonie/{voce_id}/allegati", response={201: VoceOut})
def carica_allegato(request, voce_id: int, titolo: Form[str], file: File[UploadedFile]):
    from apps.buonacaccia.servizi import _file_con_nome_casuale

    voce = _scrivibile(request, voce_id)
    titolo = " ".join(titolo.split())
    if not titolo:
        raise HttpError(400, "Scrivi cos'è l'allegato.")
    try:
        salvato, tipo_file = _file_con_nome_casuale(
            file, TIPI_ALLEGATO, "Carica un PDF o un'immagine (JPEG o PNG)."
        )
    except ValidationError as errore:
        raise HttpError(400, " ".join(errore.messages)) from errore
    AllegatoVoce.objects.create(voce=voce, titolo=titolo[:120], tipo_file=tipo_file, file=salvato)
    return Status(201, _voce_out(request, voce))


def _allegato(request, allegato_id: int) -> AllegatoVoce:
    _attiva()
    allegato = get_object_or_404(AllegatoVoce, pk=allegato_id)
    # Who does not read the entry does not learn the attachment exists.
    _leggibile(request, allegato.voce_id)
    return allegato


@router.get("/allegati-voce/{allegato_id}")
def scarica_allegato(request, allegato_id: int):
    """Served only here, to who reads the entry; never kept on the device."""
    allegato = _allegato(request, allegato_id)
    estensione = TIPI_ALLEGATO.get(allegato.tipo_file, ".bin")
    risposta = HttpResponse(allegato.file.read(), content_type=allegato.tipo_file)
    risposta["Content-Disposition"] = f'inline; filename="allegato-{allegato.pk}{estensione}"'
    risposta["Cache-Control"] = "private, no-store"
    risposta["X-Content-Type-Options"] = "nosniff"
    return risposta


@router.delete("/allegati-voce/{allegato_id}", response=VoceOut)
def togli_allegato(request, allegato_id: int):
    allegato = _allegato(request, allegato_id)
    voce = _scrivibile(request, allegato.voce_id)
    allegato.file.delete(save=False)
    allegato.delete()
    return _voce_out(request, voce)
