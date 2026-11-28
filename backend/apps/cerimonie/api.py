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
from apps.organizzazione.models import Squadriglia, TipoUnita, Unita
from apps.permessi import policy

from . import condizioni as cond
from .models import (
    AMBITI_DI_UNA_UNITA,
    LUNGHEZZA_TESTO,
    AllegatoVoce,
    AmbitoVoce,
    PartecipazioneVoce,
    TipoVoce,
    VoceLibro,
)
from .servizi import entrati_nell_alta, reparti_dell_alta, reparti_della_voce
from .stampa import pdf_voce

router = Router(tags=["cerimonie"])

NON_TROVATA = "Voce non trovata."

TIPI_ALLEGATO = {"application/pdf": ".pdf", "image/jpeg": ".jpg", "image/png": ".png"}


def _attiva() -> None:
    funzioni.richiedi(funzioni.CERIMONIE)


def _leggibile(request, voce_id: int) -> VoceLibro:
    _attiva()
    voce = _con_ambito(policy.voci_visibili(request.auth)).filter(pk=voce_id).first()
    if voce is None:
        raise HttpError(404, NON_TROVATA)
    return voce


def _scrivibile(request, voce_id: int) -> VoceLibro:
    voce = _leggibile(request, voce_id)
    if not policy.puo_scrivere_voce(request.auth, voce):
        raise HttpError(403, "Questa voce la cambiano lo staff della sua unità e i capigruppo.")
    return voce


def _con_ambito(voci):
    return voci.prefetch_related("unita__collegata_a", "squadriglie")


# Where the Consiglio degli Anziani sits (DEC-438).
TIPI_LC = (TipoUnita.BRANCO, TipoUnita.CERCHIO, TipoUnita.BRANCO_CERCHIO)


class UnitaScelta(Schema):
    id: int
    nome: str
    tipo: str = ""
    # The unit linked to it (DEC-279): two linked reparti share one Alta Squadriglia (DEC-439).
    collegata_id: int | None = None
    collegata: str = ""


class SquadrigliaScelta(Schema):
    id: int
    nome: str
    unita_id: int


class VoceBreve(Schema):
    id: int
    titolo: str
    tipo: str
    ambito: str
    # Whose it is, in words: «Tutto il gruppo», the units, the patrols… (DEC-438).
    unita: str
    cerimonia_del_totem: bool
    # The entry ceremony of its Alta Squadriglia (DEC-439).
    cerimonia_ingresso_alta: bool = False


class Scelta(Schema):
    valore: str
    nome: str


class LibroOut(Schema):
    voci: list[VoceBreve]
    puo_scrivere: bool
    # Where a new entry may go; the group's and the Co.Ca.'s only for the capigruppo.
    unita: list[UnitaScelta]
    squadriglie: list[SquadrigliaScelta] = []
    puo_tutto_il_gruppo: bool
    # For the conditions, to who writes: every active unit and patrol, and the roles one may
    # ask for.
    unita_condizioni: list[UnitaScelta] = []
    squadriglie_condizioni: list[SquadrigliaScelta] = []
    incarichi: list[Scelta] = []


class Partecipante(Schema):
    id: int
    nome: str
    cognome: str
    unita: str
    # None: in the register by themselves, «nella tribù» (DEC-438).
    data: date | None
    tribu: bool = False
    # In the register by themselves: the tribe, who entered the Alta Squadriglia (DEC-439).
    # Not taken off here.
    automatica: bool = False


class AllegatoOut(Schema):
    id: int
    titolo: str
    tipo_file: str


class VoceOut(VoceBreve):
    unita_ids: list[int]
    squadriglie_ids: list[int]
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
    ambito: str = AmbitoVoce.GRUPPO
    unita_ids: list[int] = []
    squadriglie_ids: list[int] = []
    testo: str = ""
    aggiunti: list[int] = []
    condizioni: list = []
    # «La mia tribù» links to it: one entry of the whole group, set by the capigruppo.
    cerimonia_del_totem: bool = False
    # The entry ceremony of the Alta Squadriglia, one per Alta Squadriglia (DEC-439).
    cerimonia_ingresso_alta: bool = False


def _elenco(nomi: list[str]) -> str:
    return nomi[0] if len(nomi) == 1 else ", ".join(nomi[:-1]) + " e " + nomi[-1]


def nome_ambito(voce: VoceLibro) -> str:
    """Whose an entry is, in words (DEC-438): «Tutto il gruppo», «Comunità capi», the units,
    «Alta Squadriglia · Reparto …» (with the linked one, as they share it, DEC-439)…"""
    if voce.ambito in (AmbitoVoce.GRUPPO, AmbitoVoce.COCA):
        return voce.get_ambito_display()
    if voce.ambito == AmbitoVoce.SQUADRIGLIE:
        return _elenco(sorted(str(s) for s in voce.squadriglie.all())) if voce.pk else ""
    unita = sorted(voce.unita.all(), key=str) if voce.pk else []
    if voce.ambito == AmbitoVoce.ALTA_SQUADRIGLIA:
        unita += [u.collegata_a for u in unita if u.collegata_a and u.collegata_a not in unita]
    nomi = _elenco([str(u) for u in unita]) if unita else ""
    if voce.ambito == AmbitoVoce.UNITA:
        return nomi
    return f"{voce.get_ambito_display()} · {nomi}"


def _breve(voce: VoceLibro) -> dict:
    return {
        "id": voce.pk,
        "titolo": voce.titolo,
        "tipo": voce.tipo,
        "ambito": voce.ambito,
        "unita": nome_ambito(voce),
        "cerimonia_del_totem": voce.cerimonia_del_totem,
        "cerimonia_ingresso_alta": voce.cerimonia_ingresso_alta,
    }


def _registro(voce: VoceLibro) -> list[dict]:
    """Who is marked, with their day; after them who is there by themselves: for the totem
    ceremony the tribe not marked (DEC-438), with no day; for the entry ceremony of the Alta
    Squadriglia who entered, with the day of entry (DEC-439)."""
    partecipazioni = list(voce.partecipazioni.select_related("persona"))
    righe = [(p.persona, p.data, False) for p in partecipazioni]
    segnati = {p.persona_id for p in partecipazioni}
    if voce.cerimonia_del_totem:
        tribu = policy.tribu_della_cerimonia().exclude(pk__in=segnati).order_by("cognome", "nome")
        righe += [(persona, None, True) for persona in tribu]
    entrati = {k: v for k, v in entrati_nell_alta(voce).items() if k not in segnati}
    if entrati:
        persone = Persona.objects.in_bulk(list(entrati))
        righe += sorted(
            ((persone[i], giorno, True) for i, giorno in entrati.items()),
            key=lambda r: r[1],
            reverse=True,
        )
    unita = unita_delle_persone([persona for persona, _, _ in righe])
    return [
        {
            "id": persona.pk,
            "nome": persona.nome,
            "cognome": persona.cognome,
            "unita": unita.get(persona.pk, ""),
            "data": giorno,
            "tribu": giorno is None,
            "automatica": automatica,
        }
        for persona, giorno, automatica in righe
    ]


def _voce_out(request, voce: VoceLibro) -> dict:
    puo = policy.puo_scrivere_voce(request.auth, voce)
    registro = policy.vede_registro_voce(request.auth, voce)
    return {
        "vede_registro": registro,
        "partecipanti": _registro(voce) if registro else [],
        **_breve(voce),
        "unita_ids": sorted(u.pk for u in voce.unita.all()),
        "squadriglie_ids": sorted(s.pk for s in voce.squadriglie.all()),
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
    voci = _con_ambito(policy.voci_visibili(user))
    scrive = policy.puo_scrivere_voci(user)
    attive = (
        Unita.objects.filter(attiva=True, archiviata_il__isnull=True)
        .exclude(tipo=TipoUnita.COMUNITA_CAPI)
        .select_related("collegata_a")
    )
    sq = Squadriglia.objects.filter(attiva=True).order_by("unita_id", "nome")
    return {
        "voci": [_breve(v) for v in voci],
        "puo_scrivere": scrive,
        "unita": [
            _unita_scelta_out(u) for u in policy.unita_per_voci(user).select_related("collegata_a")
        ],
        "squadriglie": [_squadriglia_out(q) for q in policy.squadriglie_per_voci(user)],
        "puo_tutto_il_gruppo": policy.e_capogruppo(user),
        "unita_condizioni": [_unita_scelta_out(u) for u in attive] if scrive else [],
        "squadriglie_condizioni": [_squadriglia_out(q) for q in sq] if scrive else [],
        "incarichi": (
            [{"valore": r.value, "nome": r.label} for r in cond.INCARICHI] if scrive else []
        ),
    }


def _unita_scelta_out(u: Unita) -> dict:
    collegata = u.collegata_a
    return {
        "id": u.pk,
        "nome": str(u),
        "tipo": u.tipo,
        "collegata_id": collegata.pk if collegata else None,
        "collegata": str(collegata) if collegata else "",
    }


def _squadriglia_out(q: Squadriglia) -> dict:
    return {"id": q.pk, "nome": str(q), "unita_id": q.unita_id}


class VoceTesto(VoceBreve):
    testo: str


@router.get("/cerimonie/testi", response=list[VoceTesto])
def testi(request):
    """The texts of every entry one reads, for the copy on the device: no register, no
    attachments, no conditions. Not while acting as another user (the copy is one's own)."""
    _attiva()
    return [
        {**_breve(v), "testo": v.testo} for v in _con_ambito(policy.voci_visibili(request.auth))
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
    # Whose it is: an Alta Squadriglia's is not read by its antechamber (DEC-439).
    ambito: str = AmbitoVoce.GRUPPO
    unita_ids: list[int] = []


@router.post("/cerimonie/anteprima", response=list[Aggiungibile])
def anteprima(request, dati: AnteprimaIn):
    """Who would read an entry today with these conditions: before saving (DEC-437)."""
    _attiva()
    if not policy.puo_scrivere_voci(request.auth):
        raise HttpError(403, "Le voci le scrivono lo staff delle unità e i capigruppo.")
    gruppi = _condizioni(dati.condizioni)
    voce = _leggibile(request, dati.voce_id) if dati.voce_id is not None else None
    reparti = (
        reparti_dell_alta(dati.unita_ids) if dati.ambito == AmbitoVoce.ALTA_SQUADRIGLIA else set()
    )
    return con_unita(policy.lettori_delle_condizioni(gruppi, dati.aggiunti, voce, reparti))


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
        if voce.cerimonia_ingresso_alta:
            _entrano(voce, dati.persone, dati.data)
    return _voce_out(request, voce)


def _entrano(voce: VoceLibro, persone: list[int], giorno: date) -> None:
    """Marked in the entry ceremony: the ragazzi/e of its reparti enter the Alta Squadriglia
    that day (DEC-439); the others (a capo, who has since moved on) stay only in the register."""
    from apps.eventi import servizi as eventi

    reparto = voce.unita.first()
    if reparto is None:
        return
    possibili = eventi.ragazzi_per_alta(reparto).filter(pk__in=persone)
    try:
        eventi.fai_entrare(reparto, list(possibili), giorno)
    except ValidationError as errore:
        raise HttpError(400, " ".join(errore.messages)) from errore


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


def _ambito(request, voce: VoceLibro, dati: VoceIn) -> tuple[list[Unita], list[Squadriglia]]:
    """The units and patrols of the entry, checked (DEC-438). The staff adds only the units
    (or patrols of the reparti) it serves; those already there stay a choice."""
    user = request.auth
    if dati.ambito not in AmbitoVoce.values:
        raise HttpError(400, "Scegli di chi è la voce.")
    if dati.ambito in (AmbitoVoce.GRUPPO, AmbitoVoce.COCA):
        if not policy.e_capogruppo(user):
            raise HttpError(
                403, "Le voci di tutto il gruppo e della Comunità capi le scrivono i capigruppo."
            )
        return [], []
    if dati.ambito == AmbitoVoce.SQUADRIGLIE:
        gia = set(voce.squadriglie.values_list("pk", flat=True)) if voce.pk else set()
        ammesse = set(policy.squadriglie_per_voci(user).values_list("pk", flat=True))
        if policy.e_capogruppo(user):
            ammesse = set(Squadriglia.objects.filter(attiva=True).values_list("pk", flat=True))
        scelte = set(dati.squadriglie_ids)
        if not scelte:
            raise HttpError(400, "Scegli almeno una squadriglia.")
        if not scelte <= ammesse | gia:
            raise HttpError(
                403, "Puoi scegliere solo le squadriglie dei reparti in cui sei in servizio."
            )
        return [], list(Squadriglia.objects.filter(pk__in=scelte))
    gia = set(voce.unita.values_list("pk", flat=True)) if voce.pk else set()
    ammesse = set(policy.unita_per_voci(user).values_list("pk", flat=True))
    scelte = set(dati.unita_ids)
    if not scelte:
        raise HttpError(400, "Scegli l'unità della voce.")
    if not scelte <= ammesse | gia:
        raise HttpError(403, "Puoi scegliere solo le unità in cui sei in servizio.")
    unita = list(Unita.objects.filter(pk__in=scelte))
    if dati.ambito in AMBITI_DI_UNA_UNITA:
        tipi = TIPI_LC if dati.ambito == AmbitoVoce.CONSIGLIO_ANZIANI else (TipoUnita.REPARTO,)
        if len(unita) != 1 or unita[0].tipo not in tipi:
            if dati.ambito == AmbitoVoce.CONSIGLIO_ANZIANI:
                raise HttpError(400, "Il Consiglio degli Anziani è di un branco o di un cerchio.")
            raise HttpError(400, f"{AmbitoVoce(dati.ambito).label} è di un reparto.")
    elif any(u.tipo == TipoUnita.COMUNITA_CAPI for u in unita):
        raise HttpError(400, "Per la Comunità capi scegli «Comunità capi».")
    return unita, []


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
    unita, squadriglie = _ambito(request, voce, dati)
    voce.ambito = dati.ambito
    di_tutti = dati.ambito == AmbitoVoce.GRUPPO
    if dati.cerimonia_del_totem != voce.cerimonia_del_totem:
        if not policy.e_capogruppo(request.auth):
            raise HttpError(403, "La cerimonia del totem la sceglie un capogruppo.")
        if dati.cerimonia_del_totem and not di_tutti:
            raise HttpError(400, "La cerimonia del totem è una voce di tutto il gruppo.")
    elif voce.cerimonia_del_totem and not di_tutti:
        raise HttpError(400, "La cerimonia del totem è una voce di tutto il gruppo.")
    voce.cerimonia_del_totem = dati.cerimonia_del_totem
    if dati.cerimonia_ingresso_alta and dati.ambito != AmbitoVoce.ALTA_SQUADRIGLIA:
        raise HttpError(400, "La cerimonia d'ingresso è una voce dell'Alta Squadriglia.")
    voce.cerimonia_ingresso_alta = dati.cerimonia_ingresso_alta
    with transaction.atomic():
        if voce.cerimonia_del_totem:
            # Only one: the one chosen now takes the place of the one before.
            VoceLibro.objects.filter(cerimonia_del_totem=True).exclude(pk=voce.pk).update(
                cerimonia_del_totem=False
            )
        voce.save()
        voce.aggiunti.set(aggiunti)
        voce.unita.set(unita)
        voce.squadriglie.set(squadriglie)
        if voce.cerimonia_ingresso_alta:
            # One per Alta Squadriglia: the one chosen now takes the place of the one before.
            for altra in VoceLibro.objects.filter(cerimonia_ingresso_alta=True).exclude(pk=voce.pk):
                if reparti_della_voce(altra) & reparti_della_voce(voce):
                    altra.cerimonia_ingresso_alta = False
                    altra.save(update_fields=["cerimonia_ingresso_alta", "aggiornato_il"])
        # Who would no longer write it keeps one of their own units (the error undoes it all).
        if not policy.puo_scrivere_voce(request.auth, voce):
            raise HttpError(403, "Tieni almeno una delle unità in cui sei in servizio.")
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
