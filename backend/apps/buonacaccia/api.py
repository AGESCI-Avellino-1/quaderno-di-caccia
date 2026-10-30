"""Events on BuonaCaccia (see models). Who may do what: apps.permessi.policy."""

import io
from datetime import date, datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import File, Router, Schema
from ninja.errors import HttpError
from ninja.files import UploadedFile
from ninja.responses import Status

from apps.anagrafica.models import Persona
from apps.core.anno import AnnoAssociativo
from apps.eventi import avvisi as avvisi_eventi
from apps.eventi.models import Evento, Livello, Partecipazione, StatoPartecipazione, TipoEvento
from apps.permessi import policy
from apps.permessi.models import Azione, Categoria, registra_accessi

from . import avvisi, servizi
from .models import (
    EsitoLiberatoria,
    EventoBuonaCaccia,
    IscrizioneBuonaCaccia,
    ModelloScheda,
    ModoLiberatoria,
    StatoIscrizione,
    TipoCampoFormazione,
    TipoDomanda,
)

router = Router(tags=["buonacaccia"])

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _esegui(funzione, *args, **kwargs):
    try:
        return funzione(*args, **kwargs)
    except ValidationError as errore:
        raise HttpError(400, " ".join(errore.messages)) from errore


def _nome(persona: Persona) -> str:
    return f"{persona.nome} {persona.cognome}"


# --- Event forms (DEC-161) -------------------------------------------------------------------


class DomandaIO(Schema):
    id: str = ""
    tipo: TipoDomanda
    testo: str
    opzioni: list[str] = []
    obbligatoria: bool = False


class VersioneOut(Schema):
    id: int
    modello_id: int
    nome: str
    numero: int
    domande: list[DomandaIO]
    chiede_foto: bool


class SchedaOut(Schema):
    id: int
    nome: str
    ultima: VersioneOut
    versioni: int
    usata: int  # events using one of its versions


class SchedaIn(Schema):
    nome: str
    domande: list[DomandaIO]


def _versione_out(versione) -> dict:
    return {
        "id": versione.pk,
        "modello_id": versione.modello_id,
        "nome": versione.modello.nome,
        "numero": versione.numero,
        "domande": versione.domande,
        "chiede_foto": versione.chiede_foto,
    }


def _scheda_out(modello: ModelloScheda) -> dict:
    return {
        "id": modello.pk,
        "nome": modello.nome,
        "ultima": _versione_out(modello.ultima()),
        "versioni": modello.versioni.count(),
        "usata": EventoBuonaCaccia.objects.filter(scheda__modello=modello).count(),
    }


def _gestore_schede(request) -> None:
    if not policy.puo_gestire_schede_buonacaccia(request.auth):
        raise HttpError(403, "Le schede degli eventi le preparano i capi.")


@router.get("/buonacaccia/schede", response=list[SchedaOut])
def schede(request):
    _gestore_schede(request)
    return [_scheda_out(m) for m in ModelloScheda.objects.filter(versioni__isnull=False).distinct()]


@router.post("/buonacaccia/schede", response={201: SchedaOut})
def crea_scheda(request, dati: SchedaIn):
    _gestore_schede(request)
    modello = ModelloScheda(nome=dati.nome)
    with transaction.atomic():
        _esegui(servizi.salva_scheda, modello, [d.dict() for d in dati.domande], request.auth)
    return Status(201, _scheda_out(modello))


@router.put("/buonacaccia/schede/{scheda_id}", response=SchedaOut)
def nuova_versione(request, scheda_id: int, dati: SchedaIn):
    """A change saves a new version: the events that used the old one keep it."""
    _gestore_schede(request)
    modello = get_object_or_404(ModelloScheda, pk=scheda_id)
    modello.nome = dati.nome
    with transaction.atomic():
        _esegui(servizi.salva_scheda, modello, [d.dict() for d in dati.domande], request.auth)
    return _scheda_out(modello)


# --- Events ----------------------------------------------------------------------------------


class EventoBCIn(Schema):
    titolo: str
    tipo: TipoEvento = TipoEvento.CAMPO
    inizio: datetime
    fine: datetime
    luogo: str = ""
    descrizione: str = ""
    formazione_capi: bool = False
    piccole_orme: bool = False
    tipo_campo: TipoCampoFormazione | None = None
    specifica: str = ""


class EventoTrovato(Schema):
    id: int
    titolo: str
    inizio: datetime
    fine: datetime
    luogo: str
    formazione_capi: bool
    piccole_orme: bool


def _eventi_trovati(elenco) -> list[dict]:
    return [
        {
            "id": e.pk,
            "titolo": e.titolo,
            "inizio": e.inizio,
            "fine": e.fine,
            "luogo": e.luogo,
            "formazione_capi": getattr(getattr(e, "buonacaccia", None), "formazione_capi", False),
            "piccole_orme": getattr(getattr(e, "buonacaccia", None), "piccole_orme", False),
        }
        for e in elenco
    ]


@router.get("/buonacaccia/eventi", response=list[EventoTrovato])
def cerca_eventi(request, cerca: str = ""):
    """Before creating one: the event may already be there (DEC-158)."""
    if not policy.puo_creare_evento_buonacaccia(request.auth):
        raise HttpError(403, "Non puoi registrare eventi su BuonaCaccia.")
    return _eventi_trovati(servizi.cerca_eventi(cerca)[:30])


def _compila(evento: Evento, dettagli: EventoBuonaCaccia, dati: EventoBCIn) -> None:
    evento.titolo = dati.titolo.strip()
    evento.tipo = dati.tipo
    evento.inizio = dati.inizio
    evento.fine = dati.fine
    evento.luogo = dati.luogo.strip()
    evento.descrizione = dati.descrizione.strip()
    dettagli.formazione_capi = dati.formazione_capi
    dettagli.piccole_orme = dati.piccole_orme and not dati.formazione_capi
    dettagli.tipo_campo = (dati.tipo_campo or "") if dati.formazione_capi else ""
    dettagli.specifica = dati.specifica.strip() if dettagli.tipo_campo else ""


@router.post("/buonacaccia/eventi", response={201: EventoTrovato})
def crea_evento(request, dati: EventoBCIn):
    if not policy.puo_creare_evento_buonacaccia(request.auth):
        raise HttpError(403, "Non puoi registrare eventi su BuonaCaccia.")
    evento, dettagli = Evento(), EventoBuonaCaccia()
    _compila(evento, dettagli, dati)
    _esegui(servizi.salva_evento, evento, dettagli, request.auth)
    return Status(201, _eventi_trovati([evento])[0])


def _evento(request, evento_id: int) -> Evento:
    """An external event the user may see, or one they could join."""
    evento = get_object_or_404(Evento, pk=evento_id, livello=Livello.ESTERNO)
    if policy.eventi_visibili(request.auth).filter(pk=evento.pk).exists():
        return evento
    if policy.puo_creare_evento_buonacaccia(request.auth):
        return evento
    raise HttpError(404, "Evento non trovato.")


def _gestore_evento(request, evento: Evento) -> None:
    if not policy.puo_gestire_evento_buonacaccia(request.auth, evento):
        raise HttpError(403, "L'evento lo gestisce chi ha iscritto i partecipanti.")


@router.put("/buonacaccia/eventi/{evento_id}", response=EventoTrovato)
def modifica_evento(request, evento_id: int, dati: EventoBCIn):
    evento = _evento(request, evento_id)
    _gestore_evento(request, evento)
    dettagli = servizi.dettagli(evento)
    prima = (evento.inizio, evento.fine, evento.luogo)
    _compila(evento, dettagli, dati)
    _esegui(servizi.salva_evento, evento, dettagli, request.auth)
    if (evento.inizio, evento.fine, evento.luogo) != prima:
        transaction.on_commit(lambda: avvisi_eventi.modificato(evento))
    return _eventi_trovati([evento])[0]


# --- One event with its registrations ------------------------------------------------------


class QuotaIscrizione(Schema):
    id: int
    importo: Decimal
    scadenza: date
    dovuto: Decimal
    pagato: Decimal
    residuo: Decimal
    annullata: bool


class IscrizioneOut(Schema):
    id: int
    evento_id: int
    evento: str
    inizio: datetime
    persona_id: int
    persona: str
    stato: StatoIscrizione
    stato_nome: str
    attiva: bool
    iscritto_il: date
    scadenza: date
    limite_cancellazione: date
    cancellata_il: date | None
    link_gestione: str | None  # None: not for this user (DEC-159)
    modo_liberatoria: ModoLiberatoria
    scadenza_liberatoria: date
    scadenza_liberatoria_fissata: bool
    liberatoria_da_firmare: bool
    liberatoria_firmata: bool
    liberatoria_ricevuta_il: date | None
    liberatoria_caricata_il: date | None
    esito_liberatoria: str
    motivo_rigetto: str
    risposte: dict
    risposte_il: datetime | None
    risposte_mancanti: list[str]
    foto: bool
    presentazione: str | None  # None: capi only
    # Piccole Orme: what does not fit (lived before, not in Responsabilità, too short).
    avvisi: list[str]
    scheda_inviata_il: date | None
    pagata_il: date | None
    quota: QuotaIscrizione | None
    puo_gestire: bool
    puo_rispondere: bool  # the family: release form, answers
    puo_scrivere_scheda: bool  # answers and photo: the family or who manages it
    puo_togliere_quota: bool


def _quota_out(quota) -> dict | None:
    if quota is None:
        return None
    return {
        "id": quota.pk,
        "importo": quota.importo,
        "scadenza": quota.scadenza,
        "dovuto": quota.dovuto,
        "pagato": quota.pagato,
        "residuo": quota.residuo,
        "annullata": quota.annullata_il is not None,
    }


def _iscrizione_out(user, i: IscrizioneBuonaCaccia) -> dict:
    persona = i.partecipazione.persona
    evento = i.partecipazione.evento
    gestisce = policy.puo_gestire_iscrizione_buonacaccia(user, persona)
    return {
        "id": i.pk,
        "evento_id": evento.pk,
        "evento": evento.titolo,
        "inizio": evento.inizio,
        "persona_id": persona.pk,
        "persona": _nome(persona),
        "stato": i.stato,
        "stato_nome": i.get_stato_display(),
        "attiva": i.attiva,
        "iscritto_il": i.iscritto_il,
        "scadenza": i.scadenza,
        "limite_cancellazione": i.limite_cancellazione,
        "cancellata_il": i.cancellata_il,
        "link_gestione": i.link_gestione if gestisce else None,
        "modo_liberatoria": i.modo_liberatoria,
        "scadenza_liberatoria": i.scadenza_della_liberatoria,
        "scadenza_liberatoria_fissata": i.scadenza_liberatoria is not None,
        "liberatoria_da_firmare": bool(i.liberatoria_da_firmare),
        "liberatoria_firmata": bool(i.liberatoria_firmata),
        "liberatoria_ricevuta_il": i.liberatoria_ricevuta_il,
        "liberatoria_caricata_il": i.liberatoria_caricata_il,
        "esito_liberatoria": i.esito_liberatoria,
        "motivo_rigetto": i.motivo_rigetto,
        "risposte": i.risposte,
        "risposte_il": i.risposte_il,
        "risposte_mancanti": servizi.risposte_mancanti(i),
        "foto": bool(i.foto),
        "presentazione": (i.presentazione if policy.vede_presentazione_buonacaccia(user) else None),
        "scheda_inviata_il": i.scheda_inviata_il,
        "pagata_il": i.pagata_il,
        "quota": _quota_out(i.quota),
        "puo_gestire": gestisce,
        "puo_rispondere": policy.puo_rispondere_scheda(user, persona),
        "puo_scrivere_scheda": policy.puo_scrivere_scheda(user, persona),
        "puo_togliere_quota": gestisce and servizi.puo_togliere_quota(i),
        "avvisi": servizi.avvisi_piccole_orme(i) if gestisce else [],
    }


class AdultoOut(Schema):
    persona_id: int
    persona: str
    partecipa: bool
    quota_versata: Decimal | None
    puo_modificare: bool


class DettaglioBC(Schema):
    id: int
    titolo: str
    tipo: TipoEvento
    inizio: datetime
    fine: datetime
    luogo: str
    descrizione: str
    annullato: bool
    formazione_capi: bool
    piccole_orme: bool
    tipo_campo: str
    tipo_campo_nome: str
    specifica: str
    scheda: VersioneOut | None
    iscrizioni: list[IscrizioneOut]
    adulti: list[AdultoOut]
    puo_gestire: bool
    puo_iscrivere: bool
    puo_partecipare: bool  # an adult may add themself


def _iscrizioni_visibili(user, evento: Evento):
    elenco = IscrizioneBuonaCaccia.objects.filter(partecipazione__evento=evento).select_related(
        "partecipazione__persona", "partecipazione__evento", "quota__tipo"
    )
    return [
        i
        for i in elenco.order_by("partecipazione__persona__cognome")
        if policy.puo_vedere_iscrizione_buonacaccia(user, i.partecipazione.persona)
    ]


def _dettaglio(request, evento: Evento) -> dict:
    user = request.auth
    dettagli = servizi.dettagli(evento)
    con_iscrizione = IscrizioneBuonaCaccia.objects.filter(partecipazione__evento=evento).values(
        "partecipazione_id"
    )
    adulti = []
    for p in (
        evento.partecipazioni.exclude(pk__in=con_iscrizione)
        .select_related("persona")
        .order_by("persona__cognome")
    ):
        propria = policy.persona_di(user)
        if not (policy.e_capo(user) or (propria is not None and propria.pk == p.persona_id)):
            continue
        quota = getattr(p, "quota_formazione", None)
        adulti.append(
            {
                "persona_id": p.persona_id,
                "persona": _nome(p.persona),
                "partecipa": p.stato == StatoPartecipazione.INVITATO,
                "quota_versata": quota.importo if quota else None,
                "puo_modificare": policy.puo_segnare_partecipazione_esterna(user, p.persona),
            }
        )
    propria = policy.persona_di(user)
    return {
        "id": evento.pk,
        "titolo": evento.titolo,
        "tipo": evento.tipo,
        "inizio": evento.inizio,
        "fine": evento.fine,
        "luogo": evento.luogo,
        "descrizione": evento.descrizione,
        "annullato": evento.annullato_il is not None,
        "formazione_capi": dettagli.formazione_capi,
        "piccole_orme": dettagli.piccole_orme,
        "tipo_campo": dettagli.tipo_campo,
        "tipo_campo_nome": dettagli.tipo_campo_testo if dettagli.tipo_campo else "",
        "specifica": dettagli.specifica,
        "scheda": _versione_out(dettagli.scheda) if dettagli.scheda else None,
        "iscrizioni": [_iscrizione_out(user, i) for i in _iscrizioni_visibili(user, evento)],
        "adulti": adulti,
        "puo_gestire": policy.puo_gestire_evento_buonacaccia(user, evento),
        "puo_iscrivere": policy.e_capo(user) and not policy.e_capo_in_attesa(user),
        "puo_partecipare": (
            propria is not None and policy.puo_segnare_partecipazione_esterna(user, propria)
        ),
    }


@router.get("/buonacaccia/eventi/{evento_id}", response=DettaglioBC)
def dettaglio(request, evento_id: int):
    return _dettaglio(request, _evento(request, evento_id))


class SchedaEventoIn(Schema):
    versione_id: int | None


@router.put("/buonacaccia/eventi/{evento_id}/scheda", response=DettaglioBC)
def scheda_evento(request, evento_id: int, dati: SchedaEventoIn):
    """The form of the event: a saved version, the same for every participant."""
    from .models import VersioneScheda

    evento = _evento(request, evento_id)
    _gestore_evento(request, evento)
    dettagli = servizi.dettagli(evento)
    dettagli.scheda = (
        get_object_or_404(VersioneScheda, pk=dati.versione_id) if dati.versione_id else None
    )
    dettagli.save()
    return _dettaglio(request, evento)


# --- Registrations of minors (DEC-158, DEC-159) --------------------------------------------


class IscrizioneIn(Schema):
    persona_id: int
    iscritto_il: date
    stato: StatoIscrizione = StatoIscrizione.AMMESSO
    link_gestione: str = ""
    modo_liberatoria: ModoLiberatoria = ModoLiberatoria.APP
    scadenza_liberatoria: date | None = None
    importo: Decimal | None = None
    scadenza_quota: date | None = None


@router.post("/buonacaccia/eventi/{evento_id}/iscrizioni", response={201: IscrizioneOut})
def iscrivi(request, evento_id: int, dati: IscrizioneIn):
    evento = _evento(request, evento_id)
    persona = get_object_or_404(Persona, pk=dati.persona_id)
    if not policy.puo_gestire_iscrizione_buonacaccia(request.auth, persona):
        raise HttpError(403, "L'iscrizione la registra lo staff dell'unità del ragazzo.")
    with transaction.atomic():
        iscrizione = _esegui(
            servizi.iscrivi,
            evento,
            persona,
            request.auth,
            **dati.dict(exclude={"persona_id"}),
        )
    transaction.on_commit(lambda: avvisi.iscritto(iscrizione))
    return Status(201, _iscrizione_out(request.auth, iscrizione))


def _iscrizione(request, iscrizione_id: int) -> IscrizioneBuonaCaccia:
    iscrizione = get_object_or_404(
        IscrizioneBuonaCaccia.objects.select_related(
            "partecipazione__persona", "partecipazione__evento", "quota__tipo"
        ),
        pk=iscrizione_id,
    )
    if not policy.puo_vedere_iscrizione_buonacaccia(
        request.auth, iscrizione.partecipazione.persona
    ):
        raise HttpError(404, "Iscrizione non trovata.")
    return iscrizione


def _da_gestire(request, iscrizione_id: int) -> IscrizioneBuonaCaccia:
    iscrizione = _iscrizione(request, iscrizione_id)
    if not policy.puo_gestire_iscrizione_buonacaccia(
        request.auth, iscrizione.partecipazione.persona
    ):
        raise HttpError(403, "L'iscrizione la gestisce lo staff dell'unità del ragazzo.")
    return iscrizione


@router.get("/buonacaccia/iscrizioni", response=list[IscrizioneOut])
def da_seguire(request, tutte: bool = False):
    """The registrations the user manages, open ones first by nearest deadline."""
    if not policy.e_capo(request.auth):
        raise HttpError(403, "Le iscrizioni su BuonaCaccia le seguono i capi.")
    elenco = IscrizioneBuonaCaccia.objects.select_related(
        "partecipazione__persona", "partecipazione__evento", "quota__tipo"
    )
    if not tutte:
        elenco = elenco.filter(
            stato__in=[StatoIscrizione.AMMESSO, StatoIscrizione.IN_ATTESA],
            partecipazione__evento__fine__gte=timezone.now(),
        )
    risultato = [
        _iscrizione_out(request.auth, i)
        for i in elenco
        if policy.puo_gestire_iscrizione_buonacaccia(request.auth, i.partecipazione.persona)
    ]
    return sorted(risultato, key=lambda r: (not r["attiva"], r["scadenza"]))


class AggiornaIn(Schema):
    iscritto_il: date | None = None
    stato: StatoIscrizione | None = None
    link_gestione: str | None = None
    modo_liberatoria: ModoLiberatoria | None = None
    scadenza_liberatoria: date | None = None
    # True: back to the default (2 days before the registration's deadline).
    scadenza_liberatoria_predefinita: bool = False


@router.put("/buonacaccia/iscrizioni/{iscrizione_id}", response=IscrizioneOut)
def aggiorna(request, iscrizione_id: int, dati: AggiornaIn):
    iscrizione = _da_gestire(request, iscrizione_id)
    campi = dati.dict(exclude={"scadenza_liberatoria_predefinita"})
    _esegui(servizi.aggiorna, iscrizione, **campi)
    if dati.scadenza_liberatoria_predefinita:
        iscrizione.scadenza_liberatoria = None
        iscrizione.save(update_fields=["scadenza_liberatoria", "aggiornato_il"])
    return _iscrizione_out(request.auth, iscrizione)


class ChiudiIn(Schema):
    stato: StatoIscrizione
    il: date


@router.post("/buonacaccia/iscrizioni/{iscrizione_id}/chiudi", response=IscrizioneOut)
def chiudi(request, iscrizione_id: int, dati: ChiudiIn):
    """Cancelled on BuonaCaccia, or not admitted."""
    iscrizione = _da_gestire(request, iscrizione_id)
    _esegui(servizi.chiudi, iscrizione, dati.stato, dati.il, request.auth)
    return _iscrizione_out(request.auth, iscrizione)


class QuotaIn(Schema):
    importo: Decimal
    scadenza: date


@router.put("/buonacaccia/iscrizioni/{iscrizione_id}/quota", response=IscrizioneOut)
def quota(request, iscrizione_id: int, dati: QuotaIn):
    iscrizione = _da_gestire(request, iscrizione_id)
    _esegui(servizi.imposta_quota, iscrizione, dati.importo, dati.scadenza, request.auth)
    return _iscrizione_out(request.auth, iscrizione)


@router.post("/buonacaccia/iscrizioni/{iscrizione_id}/togli-quota", response=IscrizioneOut)
def togli_quota(request, iscrizione_id: int):
    iscrizione = _da_gestire(request, iscrizione_id)
    _esegui(servizi.togli_quota, iscrizione, request.auth)
    iscrizione.quota.refresh_from_db()
    return _iscrizione_out(request.auth, iscrizione)


class PassiIn(Schema):
    """Only the fields sent change; null clears a tick."""

    liberatoria_ricevuta_il: date | None = None
    liberatoria_caricata_il: date | None = None
    scheda_inviata_il: date | None = None
    pagata_il: date | None = None


@router.put("/buonacaccia/iscrizioni/{iscrizione_id}/passi", response=IscrizioneOut)
def passi(request, iscrizione_id: int, dati: PassiIn):
    iscrizione = _da_gestire(request, iscrizione_id)
    _esegui(servizi.segna_passi, iscrizione, **dati.dict(exclude_unset=True))
    return _iscrizione_out(request.auth, iscrizione)


class EsitoIn(Schema):
    esito: EsitoLiberatoria
    motivo: str = ""


@router.post("/buonacaccia/iscrizioni/{iscrizione_id}/esito-liberatoria", response=IscrizioneOut)
def esito(request, iscrizione_id: int, dati: EsitoIn):
    iscrizione = _da_gestire(request, iscrizione_id)
    _esegui(servizi.esito_liberatoria, iscrizione, dati.esito, dati.motivo)
    if dati.esito == EsitoLiberatoria.RIGETTATA:
        transaction.on_commit(lambda: avvisi.liberatoria_rigettata(iscrizione))
    return _iscrizione_out(request.auth, iscrizione)


# --- Release form files (DEC-160) ----------------------------------------------------------


@router.post("/buonacaccia/iscrizioni/{iscrizione_id}/liberatoria", response=IscrizioneOut)
def carica_da_firmare(request, iscrizione_id: int, file: File[UploadedFile]):
    """The staff uploads the PDF BuonaCaccia sent; the family is told."""
    iscrizione = _da_gestire(request, iscrizione_id)
    _esegui(servizi.carica_da_firmare, iscrizione, file)
    transaction.on_commit(lambda: avvisi.liberatoria_da_firmare(iscrizione))
    return _iscrizione_out(request.auth, iscrizione)


@router.post("/buonacaccia/iscrizioni/{iscrizione_id}/liberatoria-firmata", response=IscrizioneOut)
def carica_firmata(request, iscrizione_id: int, file: File[UploadedFile]):
    iscrizione = _iscrizione(request, iscrizione_id)
    persona = iscrizione.partecipazione.persona
    if not (
        policy.puo_rispondere_scheda(request.auth, persona)
        or policy.puo_gestire_iscrizione_buonacaccia(request.auth, persona)
    ):
        raise HttpError(403, "La liberatoria firmata la carica la famiglia.")
    _esegui(servizi.carica_firmata, iscrizione, file)
    return _iscrizione_out(request.auth, iscrizione)


def _scarica(request, iscrizione: IscrizioneBuonaCaccia, campo: str, nome: str, tipo: str):
    persona = iscrizione.partecipazione.persona
    famiglia = policy.puo_rispondere_scheda(request.auth, persona)
    if not (famiglia or policy.puo_gestire_iscrizione_buonacaccia(request.auth, persona)):
        raise HttpError(403, "La liberatoria la vedono la famiglia e chi gestisce l'iscrizione.")
    file = getattr(iscrizione, campo)
    if not file:
        raise HttpError(404, "Nessun file.")
    if not famiglia:
        registra_accessi(request, [persona], Categoria.MODULI, Azione.LETTURA)
    return FileResponse(file.open("rb"), content_type=tipo, filename=nome)


@router.get("/buonacaccia/iscrizioni/{iscrizione_id}/liberatoria")
def scarica_da_firmare(request, iscrizione_id: int):
    iscrizione = _iscrizione(request, iscrizione_id)
    return _scarica(
        request, iscrizione, "liberatoria_da_firmare", "liberatoria.pdf", "application/pdf"
    )


@router.get("/buonacaccia/iscrizioni/{iscrizione_id}/liberatoria-firmata")
def scarica_firmata(request, iscrizione_id: int):
    iscrizione = _iscrizione(request, iscrizione_id)
    estensione = {"application/pdf": "pdf", "image/jpeg": "jpg", "image/png": "png"}.get(
        iscrizione.tipo_firmata, "pdf"
    )
    return _scarica(
        request,
        iscrizione,
        "liberatoria_firmata",
        f"liberatoria-firmata.{estensione}",
        iscrizione.tipo_firmata or "application/pdf",
    )


# --- Answers, photo, presentation (DEC-161, DEC-162) --------------------------------------


class RisposteIn(Schema):
    risposte: dict


def _famiglia(request, iscrizione: IscrizioneBuonaCaccia) -> None:
    if not policy.puo_scrivere_scheda(request.auth, iscrizione.partecipazione.persona):
        raise HttpError(
            403, "Alla scheda rispondono il ragazzo, i genitori o chi gestisce l'iscrizione."
        )


@router.put("/buonacaccia/iscrizioni/{iscrizione_id}/risposte", response=IscrizioneOut)
def risposte(request, iscrizione_id: int, dati: RisposteIn):
    iscrizione = _iscrizione(request, iscrizione_id)
    _famiglia(request, iscrizione)
    _esegui(servizi.rispondi, iscrizione, dati.risposte, request.auth)
    return _iscrizione_out(request.auth, iscrizione)


@router.post("/buonacaccia/iscrizioni/{iscrizione_id}/foto", response=IscrizioneOut)
def carica_foto(request, iscrizione_id: int, file: File[UploadedFile]):
    iscrizione = _iscrizione(request, iscrizione_id)
    _famiglia(request, iscrizione)
    _esegui(servizi.carica_foto, iscrizione, file, request.auth)
    return _iscrizione_out(request.auth, iscrizione)


@router.post("/buonacaccia/iscrizioni/{iscrizione_id}/foto-profilo", response=IscrizioneOut)
def usa_foto_profilo(request, iscrizione_id: int):
    """The profile photo, if there is one, instead of a new one (DEC-162)."""
    iscrizione = _iscrizione(request, iscrizione_id)
    _famiglia(request, iscrizione)
    attuale = iscrizione.partecipazione.persona.foto_profilo.first()
    if attuale is None:
        raise HttpError(400, "Non c'è ancora una foto profilo.")
    attuale.file.open("rb")
    try:
        _esegui(servizi.carica_foto, iscrizione, attuale.file, request.auth)
    finally:
        attuale.file.close()
    return _iscrizione_out(request.auth, iscrizione)


@router.get("/buonacaccia/iscrizioni/{iscrizione_id}/foto")
def scarica_foto(request, iscrizione_id: int):
    """The JPEG ready for BuonaCaccia."""
    iscrizione = _iscrizione(request, iscrizione_id)
    if not iscrizione.foto:
        raise HttpError(404, "Nessuna foto.")
    persona = iscrizione.partecipazione.persona
    nome = f"foto-{persona.cognome}-{persona.nome}.jpg".replace(" ", "-").lower()
    return FileResponse(iscrizione.foto.open("rb"), content_type="image/jpeg", filename=nome)


class TestoIn(Schema):
    testo: str


@router.put("/buonacaccia/iscrizioni/{iscrizione_id}/presentazione", response=IscrizioneOut)
def presentazione(request, iscrizione_id: int, dati: TestoIn):
    iscrizione = _da_gestire(request, iscrizione_id)
    iscrizione.presentazione = dati.testo.strip()
    iscrizione.save(update_fields=["presentazione", "aggiornato_il"])
    return _iscrizione_out(request.auth, iscrizione)


class RigaRiepilogo(Schema):
    domanda: str
    tipo: TipoDomanda
    risposta: str


class RiepilogoOut(Schema):
    persona: str
    righe: list[RigaRiepilogo]
    presentazione: str
    foto: bool


@router.get("/buonacaccia/iscrizioni/{iscrizione_id}/riepilogo", response=RiepilogoOut)
def riepilogo(request, iscrizione_id: int):
    """Answers and presentation to copy on BuonaCaccia in one go (DEC-161)."""
    iscrizione = _da_gestire(request, iscrizione_id)
    return {
        "persona": _nome(iscrizione.partecipazione.persona),
        "righe": servizi.riepilogo(iscrizione),
        "presentazione": iscrizione.presentazione,
        "foto": bool(iscrizione.foto),
    }


# --- Adults and capi training (DEC-164) ---------------------------------------------------


class PartecipazioneIn(Schema):
    persona_id: int
    partecipa: bool = True
    quota_versata: Decimal | None = None


@router.put("/buonacaccia/eventi/{evento_id}/partecipanti", response=DettaglioBC)
def partecipante(request, evento_id: int, dati: PartecipazioneIn):
    """An adult records their own participation (or the staff for them), and for a
    capi training camp the fee they paid."""
    evento = _evento(request, evento_id)
    persona = get_object_or_404(Persona, pk=dati.persona_id)
    if not policy.puo_segnare_partecipazione_esterna(request.auth, persona):
        raise HttpError(403, "Non puoi segnare la partecipazione di questa persona.")
    with transaction.atomic():
        if dati.partecipa:
            _esegui(servizi.segna_partecipazione, evento, persona, request.auth, dati.quota_versata)
        else:
            Partecipazione.objects.filter(
                evento=evento, persona=persona, iscrizione_buonacaccia__isnull=True
            ).delete()
    return _dettaglio(request, evento)


class FormazioneOut(Schema):
    persona_id: int
    persona: str
    evento_id: int
    evento: str
    dal: date
    al: date
    luogo: str
    tipo_campo: str
    quota_versata: Decimal | None


def _anno(anno: int | None) -> int:
    return anno or AnnoAssociativo.corrente().anno_fine


@router.get("/buonacaccia/formazione", response=list[FormazioneOut])
def formazione(request, anno: int | None = None):
    if not policy.puo_vedere_formazione_capi(request.auth):
        raise HttpError(403, "L'elenco per la Zona lo vedono i capigruppo.")
    return servizi.formazione_capi(_anno(anno))


@router.get("/buonacaccia/formazione.xlsx")
def formazione_xlsx(request, anno: int | None = None):
    from openpyxl import Workbook
    from openpyxl.styles import Font

    if not policy.puo_vedere_formazione_capi(request.auth):
        raise HttpError(403, "L'elenco per la Zona lo vedono i capigruppo.")
    anno = _anno(anno)
    libro = Workbook()
    foglio = libro.active
    foglio.title = "Formazione capi"
    foglio.append(["Capo", "Evento", "Dal", "Al", "Località", "Tipo di campo", "Quota versata"])
    for cella in foglio[1]:
        cella.font = Font(bold=True)
    for r in servizi.formazione_capi(anno):
        foglio.append(
            [
                r["persona"],
                r["evento"],
                r["dal"],
                r["al"],
                r["luogo"],
                r["tipo_campo"],
                r["quota_versata"],
            ]
        )
    for colonna in foglio.columns:
        larghezza = max(len(str(c.value or "")) for c in colonna)
        foglio.column_dimensions[colonna[0].column_letter].width = min(larghezza + 2, 50)
    uscita = io.BytesIO()
    libro.save(uscita)
    risposta = HttpResponse(uscita.getvalue(), content_type=XLSX)
    nome = f"formazione-capi-{AnnoAssociativo(anno).etichetta.replace('/', '-')}.xlsx"
    risposta["Content-Disposition"] = f'attachment; filename="{nome}"'
    return risposta
