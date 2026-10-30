"""Progressione Personale (see models). Who may do what: apps.permessi.policy."""

from datetime import date

from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from ninja import Router, Schema
from ninja.errors import HttpError
from ninja.responses import Status

from apps.anagrafica.models import Appartenenza, Persona, RuoloAppartenenza
from apps.core.date_parziali import PrecisioneData
from apps.organizzazione.models import Branca, Unita
from apps.permessi import policy

from . import servizi
from .models import (
    ConsegnaDistintivo,
    Fase,
    Impegno,
    MetaEG,
    PeriodoBranca,
    Promessa,
    SedeVerifica,
    Stato,
    Tappa,
)

router = Router(tags=["progressione"])


def _esegui(funzione, *args, **kwargs):
    try:
        return funzione(*args, **kwargs)
    except ValidationError as errore:
        raise HttpError(400, " ".join(errore.messages)) from errore


class DataIn(Schema):
    data: date | None = None
    precisione: PrecisioneData = PrecisioneData.GIORNO


def _quando(dati: DataIn):
    valore = dati.data
    if valore is not None and dati.precisione == PrecisioneData.MESE:
        valore = valore.replace(day=1)
    elif valore is not None and dati.precisione == PrecisioneData.ANNO:
        valore = valore.replace(month=1, day=1)
    return _esegui(servizi.data_parziale, valore, dati.precisione)


# --- Reading ------------------------------------------------------------------------------


class DataOut(Schema):
    data: date | None
    precisione: PrecisioneData


def _d(valore, precisione) -> dict | None:
    return None if valore is None else {"data": valore, "precisione": precisione}


class TappaOut(Schema):
    id: int
    fase: Fase
    fase_nome: str
    inizio: DataOut
    collocamento: bool
    motivazione: str
    completata: DataOut | None
    in_corso: bool
    distintivo: DataOut | None
    nota_rettifica: str


class RevisioneOut(Schema):
    testo: str
    criterio_verifica: str
    termine: date | None
    sostituita_il: str


class PercorsoOut(Schema):
    id: int
    testo: str
    termine: date | None
    stato: Stato
    stato_nome: str
    proposto_dal_ragazzo: bool
    concordato_il: date | None
    avviato_il: date | None
    verifica_proposta: bool
    verificato_il: date | None
    sede: str
    sede_nome: str
    interrotto_il: date | None
    motivo_interruzione: str
    revisioni: list[RevisioneOut]


class MetaOut(PercorsoOut):
    riservata: bool


class ImpegnoOut(PercorsoOut):
    criterio_verifica: str
    mete: list[int]


class PeriodoOut(Schema):
    id: int
    branca: str
    branca_nome: str
    inizio: DataOut
    fine: date | None
    attivo: bool
    promessa: DataOut | None
    tappe: list[TappaOut]


class SchedaOut(Schema):
    persona_id: int
    persona: str
    periodi: list[PeriodoOut]
    mete: list[MetaOut]
    impegni: list[ImpegnoOut]
    # What the user may do (the API checks again on every command).
    puo_gestire: bool
    puo_proporre: bool
    puo_proporre_verifica: bool
    sedi: list[dict]


def _tappa_out(t: Tappa) -> dict:
    distintivo = getattr(t, "distintivo", None)
    return {
        "id": t.pk,
        "fase": t.fase,
        "fase_nome": t.get_fase_display(),
        "inizio": _d(t.data_inizio, t.precisione_inizio),
        "collocamento": t.collocamento,
        "motivazione": t.motivazione,
        "completata": _d(t.completata_il, t.precisione_completata),
        "in_corso": t.data_fine is None and t.periodo.data_fine is None,
        "distintivo": _d(distintivo.data, distintivo.precisione) if distintivo else None,
        "nota_rettifica": t.nota_rettifica,
    }


def _percorso_out(o) -> dict:
    return {
        "id": o.pk,
        "testo": o.testo,
        "termine": o.termine,
        "stato": o.stato,
        "stato_nome": o.get_stato_display(),
        "proposto_dal_ragazzo": o.proposto_dal_ragazzo,
        "concordato_il": o.concordato_il,
        "avviato_il": o.avviato_il,
        "verifica_proposta": o.verifica_proposta_il is not None,
        "verificato_il": o.verificato_il,
        "sede": o.sede,
        "sede_nome": o.sede_descrizione or (o.get_sede_display() if o.sede else ""),
        "interrotto_il": o.interrotto_il,
        "motivo_interruzione": o.motivo_interruzione,
        "revisioni": [
            {
                "testo": r.testo,
                "criterio_verifica": r.criterio_verifica,
                "termine": r.termine,
                "sostituita_il": r.sostituita_il.isoformat(),
            }
            for r in o.revisioni.all()
        ],
    }


def _scheda(user, persona: Persona) -> dict:
    periodi = list(
        PeriodoBranca.objects.filter(persona=persona).prefetch_related("tappe__distintivo")
    )
    mete = MetaEG.objects.filter(periodo__persona=persona).prefetch_related("revisioni")
    if not policy.vede_mete_riservate(user, persona):
        mete = mete.filter(riservata=False)
    visibili = {m.pk for m in mete}
    impegni = Impegno.objects.filter(periodo__persona=persona).prefetch_related("revisioni", "mete")
    return {
        "persona_id": persona.pk,
        "persona": f"{persona.nome} {persona.cognome}",
        "periodi": [
            {
                "id": p.pk,
                "branca": p.branca,
                "branca_nome": p.get_branca_display(),
                "inizio": _d(p.data_inizio, p.precisione_inizio),
                "fine": p.data_fine,
                "attivo": p.data_fine is None,
                "promessa": (
                    _d(p.promessa.data, p.promessa.precisione) if hasattr(p, "promessa") else None
                ),
                "tappe": [_tappa_out(t) for t in p.tappe.all()],
            }
            for p in periodi
        ],
        "mete": [{**_percorso_out(m), "riservata": m.riservata} for m in mete],
        "impegni": [
            {
                **_percorso_out(i),
                "criterio_verifica": i.criterio_verifica,
                # A private meta the user may not see is not even named.
                "mete": [m.pk for m in i.mete.all() if m.pk in visibili],
            }
            for i in impegni
        ],
        "puo_gestire": policy.puo_gestire_progressione(user, persona),
        "puo_proporre": policy.puo_proporre_percorsi(user, persona),
        "puo_proporre_verifica": policy.puo_proporre_verifica(user, persona),
        "sedi": [{"valore": v, "etichetta": e} for v, e in SedeVerifica.choices],
    }


def _persona(request, persona_id: int) -> Persona:
    persona = get_object_or_404(Persona, pk=persona_id)
    if not policy.puo_vedere_progressione(request.auth, persona):
        raise HttpError(404, "Persona non trovata.")
    return persona


@router.get("/persone/{persona_id}/progressione", response=SchedaOut)
def scheda(request, persona_id: int):
    """The personal file of the PP: every year in the group (DEC-72)."""
    return _scheda(request.auth, _persona(request, persona_id))


def _gestore(request, persona: Persona) -> None:
    if not policy.puo_gestire_progressione(request.auth, persona):
        raise HttpError(403, "La progressione la registra lo staff dell'unità.")


# --- Sentiero, Promessa, tappe, badges ----------------------------------------------------


@router.post("/persone/{persona_id}/progressione/sentiero", response={201: SchedaOut})
def apri_sentiero(request, persona_id: int, dati: DataIn):
    persona = _persona(request, persona_id)
    _gestore(request, persona)
    with transaction.atomic():
        _esegui(servizi.apri_sentiero, persona, _quando(dati), request.auth)
    return Status(201, _scheda(request.auth, persona))


def _periodo(request, periodo_id: int) -> PeriodoBranca:
    periodo = get_object_or_404(PeriodoBranca.objects.select_related("persona"), pk=periodo_id)
    _persona(request, periodo.persona_id)
    _gestore(request, periodo.persona)
    return periodo


@router.post("/progressione/periodi/{periodo_id}/promessa", response=SchedaOut)
def promessa(request, periodo_id: int, dati: DataIn):
    periodo = _periodo(request, periodo_id)
    _esegui(servizi.registra_promessa, periodo, _quando(dati), request.auth)
    return _scheda(request.auth, periodo.persona)


class RettificaIn(DataIn):
    motivo: str


@router.put("/progressione/periodi/{periodo_id}/promessa", response=SchedaOut)
def rettifica_promessa(request, periodo_id: int, dati: RettificaIn):
    periodo = _periodo(request, periodo_id)
    promessa = get_object_or_404(Promessa, periodo=periodo)
    _esegui(servizi.rettifica_data, promessa, "data", _quando(dati), dati.motivo)
    return _scheda(request.auth, periodo.persona)


def _tappa(request, tappa_id: int) -> Tappa:
    tappa = get_object_or_404(Tappa.objects.select_related("periodo__persona"), pk=tappa_id)
    _periodo(request, tappa.periodo_id)
    return tappa


@router.post("/progressione/tappe/{tappa_id}/riconosci", response=SchedaOut)
def riconosci(request, tappa_id: int, dati: DataIn):
    """Recognised in the Consiglio della Legge: the next tappa starts."""
    tappa = _tappa(request, tappa_id)
    _esegui(servizi.riconosci_tappa, tappa, _quando(dati), request.auth)
    return _scheda(request.auth, tappa.periodo.persona)


class CollocamentoIn(DataIn):
    fase: Fase
    motivazione: str


@router.post("/progressione/tappe/{tappa_id}/colloca", response=SchedaOut)
def colloca(request, tappa_id: int, dati: CollocamentoIn):
    tappa = _tappa(request, tappa_id)
    _esegui(servizi.colloca, tappa, dati.fase, _quando(dati), dati.motivazione, request.auth)
    return _scheda(request.auth, tappa.periodo.persona)


@router.post("/progressione/tappe/{tappa_id}/distintivo", response=SchedaOut)
def distintivo(request, tappa_id: int, dati: DataIn):
    tappa = _tappa(request, tappa_id)
    _esegui(servizi.consegna_distintivo, tappa, _quando(dati), request.auth)
    return _scheda(request.auth, tappa.periodo.persona)


class RettificaTappaIn(RettificaIn):
    campo: str  # "inizio", "completata" or "distintivo"


@router.put("/progressione/tappe/{tappa_id}", response=SchedaOut)
def rettifica_tappa(request, tappa_id: int, dati: RettificaTappaIn):
    """A traced correction of a date (spec §18.4), with its reason."""
    tappa = _tappa(request, tappa_id)
    quando = _quando(dati)
    if dati.campo == "inizio":
        _esegui(servizi.rettifica_data, tappa, "data_inizio", quando, dati.motivo)
    elif dati.campo == "completata" and tappa.completata_il is not None:
        _esegui(servizi.rettifica_data, tappa, "completata_il", quando, dati.motivo)
    elif dati.campo == "distintivo":
        consegna = get_object_or_404(ConsegnaDistintivo, tappa=tappa)
        _esegui(servizi.rettifica_data, consegna, "data", quando, dati.motivo)
    else:
        raise HttpError(400, "Non c'è questa data da correggere.")
    return _scheda(request.auth, tappa.periodo.persona)


# --- Impegni and mete ----------------------------------------------------------------------


class PercorsoIn(Schema):
    testo: str
    termine: date | None = None


class MetaIn(PercorsoIn):
    riservata: bool = False


class ImpegnoIn(PercorsoIn):
    criterio_verifica: str = ""
    mete: list[int] = []


def _sentiero_attivo(request, persona_id: int) -> tuple[Persona, PeriodoBranca]:
    persona = _persona(request, persona_id)
    if not policy.puo_proporre_percorsi(request.auth, persona):
        raise HttpError(403, "Mete e impegni li scrivono il ragazzo e lo staff.")
    periodo = servizi.periodo_attivo(persona)
    if periodo is None:
        raise HttpError(400, "Il sentiero non è ancora aperto: lo apre lo staff.")
    return persona, periodo


def _dal_ragazzo(request, persona: Persona) -> bool:
    return not policy.puo_gestire_progressione(request.auth, persona)


@router.post("/persone/{persona_id}/progressione/mete", response={201: SchedaOut})
def nuova_meta(request, persona_id: int, dati: MetaIn):
    persona, periodo = _sentiero_attivo(request, persona_id)
    _esegui(
        servizi.nuovo,
        MetaEG,
        periodo,
        request.auth,
        testo=dati.testo,
        termine=dati.termine,
        dal_ragazzo=_dal_ragazzo(request, persona),
        riservata=dati.riservata,
    )
    return Status(201, _scheda(request.auth, persona))


@router.post("/persone/{persona_id}/progressione/impegni", response={201: SchedaOut})
def nuovo_impegno(request, persona_id: int, dati: ImpegnoIn):
    """Also offline (DEC-95): the queue replays it once (Idempotency-Key)."""
    persona, periodo = _sentiero_attivo(request, persona_id)
    with transaction.atomic():
        impegno = _esegui(
            servizi.nuovo,
            Impegno,
            periodo,
            request.auth,
            testo=dati.testo,
            termine=dati.termine,
            dal_ragazzo=_dal_ragazzo(request, persona),
            criterio_verifica=dati.criterio_verifica.strip(),
        )
        mete = list(MetaEG.objects.filter(pk__in=dati.mete))
        _esegui(servizi.collega_mete, impegno, mete)
    return Status(201, _scheda(request.auth, persona))


MODELLI = {"mete": MetaEG, "impegni": Impegno}


def _oggetto(request, tipo: str, oggetto_id: int):
    modello = MODELLI.get(tipo)
    if modello is None:
        raise HttpError(404, "Non trovato.")
    oggetto = get_object_or_404(modello.objects.select_related("periodo__persona"), pk=oggetto_id)
    persona = _persona(request, oggetto.periodo.persona_id)
    if (
        isinstance(oggetto, MetaEG)
        and oggetto.riservata
        and not policy.vede_mete_riservate(request.auth, persona)
    ):
        raise HttpError(404, "Non trovato.")
    return oggetto, persona


class RiformulaIn(Schema):
    testo: str
    termine: date | None = None
    criterio_verifica: str | None = None
    riservata: bool | None = None
    mete: list[int] | None = None


@router.put("/progressione/{tipo}/{oggetto_id}", response=SchedaOut)
def riformula(request, tipo: str, oggetto_id: int, dati: RiformulaIn):
    """A new wording (the old one is kept). The ragazzo only on their drafts."""
    oggetto, persona = _oggetto(request, tipo, oggetto_id)
    gestisce = policy.puo_gestire_progressione(request.auth, persona)
    proprio = policy.puo_proporre_percorsi(request.auth, persona)
    if not (gestisce or (proprio and oggetto.stato == Stato.BOZZA)):
        raise HttpError(403, "Dopo l'accordo con lo staff lo riformula lo staff.")
    with transaction.atomic():
        _esegui(
            servizi.riformula,
            oggetto,
            request.auth,
            testo=dati.testo,
            termine=dati.termine,
            criterio=dati.criterio_verifica,
        )
        if isinstance(oggetto, MetaEG) and dati.riservata is not None:
            oggetto.riservata = dati.riservata
            oggetto.save(update_fields=["riservata", "aggiornato_il"])
        if isinstance(oggetto, Impegno) and dati.mete is not None:
            _esegui(servizi.collega_mete, oggetto, list(MetaEG.objects.filter(pk__in=dati.mete)))
    return _scheda(request.auth, persona)


class AzioneIn(Schema):
    il: date | None = None
    sede: str = ""
    sede_descrizione: str = ""
    motivo: str = ""


# Who may take each step: proposing a verification is open to the ragazzo and their CSQ
# (DEC-13, DEC-61); the rest is the staff's.
DELLO_STAFF = {"concorda", "avvia", "prosegui", "convalida", "interrompi"}


@router.post("/progressione/{tipo}/{oggetto_id}/{azione}", response=SchedaOut)
def azione(request, tipo: str, oggetto_id: int, azione: str, dati: AzioneIn):
    """Also offline (DEC-95): a step already applied is answered as done (DEC-96)."""
    oggetto, persona = _oggetto(request, tipo, oggetto_id)
    if azione in DELLO_STAFF:
        _gestore(request, persona)
    elif azione == "proponi_verifica":
        if not policy.puo_proporre_verifica(request.auth, persona):
            raise HttpError(
                403, "La verifica la propongono il ragazzo, il capo squadriglia o lo staff."
            )
    else:
        raise HttpError(404, "Operazione sconosciuta.")
    _esegui(
        servizi.esegui,
        oggetto,
        azione,
        request.auth,
        il=dati.il,
        sede=dati.sede,
        sede_descrizione=dati.sede_descrizione,
        motivo=dati.motivo,
    )
    return _scheda(request.auth, persona)


# --- The reparto at a glance (DEC-72: a unit view, no ranking, DEC-71) ---------------------


class RagazzoSentiero(Schema):
    persona_id: int
    persona: str
    sentiero_aperto: bool
    tappa: str | None
    tappa_dal: DataOut | None
    distintivo: bool
    promessa: bool
    impegni_in_corso: int
    impegni_da_verificare: int
    bozze: int
    mete_aperte: int


class SentieroUnita(Schema):
    unita: str
    ragazzi: list[RagazzoSentiero]
    puo_gestire: bool


@router.get("/unita/{unita_id}/progressione", response=SentieroUnita)
def sentiero_unita(request, unita_id: int):
    """Who has something to read again or to validate; sorted by name, never by
    "level" (spec §12.2). Cached on the capi's phones for meetings without network
    (DEC-95)."""
    unita = get_object_or_404(Unita, pk=unita_id)
    if not policy.e_capo_censito(request.auth):
        raise HttpError(403, "La vista dell'unità è dei capi.")
    if unita.branca != Branca.EG:
        raise HttpError(400, "Per ora la progressione è quella del reparto.")
    persone = Persona.objects.filter(
        pk__in=Appartenenza.objects.attive()
        .filter(unita=unita, ruolo=RuoloAppartenenza.RAGAZZO)
        .values("persona_id")
    ).order_by("cognome", "nome")
    righe = []
    for persona in persone:
        periodo = servizi.periodo_attivo(persona)
        tappa = periodo.tappa_attuale() if periodo else None
        impegni = Impegno.objects.filter(periodo=periodo) if periodo else Impegno.objects.none()
        righe.append(
            {
                "persona_id": persona.pk,
                "persona": f"{persona.cognome} {persona.nome}",
                "sentiero_aperto": periodo is not None,
                "tappa": tappa.get_fase_display() if tappa else None,
                "tappa_dal": _d(tappa.data_inizio, tappa.precisione_inizio) if tappa else None,
                "distintivo": bool(tappa and hasattr(tappa, "distintivo")),
                "promessa": bool(periodo and hasattr(periodo, "promessa")),
                "impegni_in_corso": impegni.filter(stato=Stato.IN_CORSO).count(),
                "impegni_da_verificare": impegni.filter(stato=Stato.DA_VERIFICARE).count(),
                "bozze": impegni.filter(stato=Stato.BOZZA).count()
                + (
                    MetaEG.objects.filter(periodo=periodo, stato=Stato.BOZZA).count()
                    if periodo
                    else 0
                ),
                "mete_aperte": (
                    MetaEG.objects.filter(
                        periodo=periodo,
                        stato__in=[Stato.CONCORDATO, Stato.IN_CORSO, Stato.DA_VERIFICARE],
                    ).count()
                    if periodo
                    else 0
                ),
            }
        )
    return {
        "unita": str(unita),
        "ragazzi": righe,
        "puo_gestire": policy.e_staff(request.auth, unita),
    }
