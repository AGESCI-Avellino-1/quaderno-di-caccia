"""Progressione Personale (see models). Who may do what: apps.permessi.policy."""

from datetime import date, datetime

from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import File, Form, Router, Schema, UploadedFile
from ninja.errors import HttpError
from ninja.responses import Status

from apps.anagrafica.models import Appartenenza, Persona, RuoloAppartenenza
from apps.buonacaccia.models import IscrizioneBuonaCaccia
from apps.core.date_parziali import PrecisioneData
from apps.organizzazione.models import Branca, TipoUnita, Unita
from apps.permessi import policy

from . import servizi
from .models import (
    AllegatoPP,
    ConsegnaDistintivo,
    Fase,
    FirmaCarta,
    Impegno,
    Impresa,
    LivelloImpresa,
    Obiettivo,
    Passaggio,
    PassaggioPersona,
    PercorsoCompetenza,
    PeriodoBranca,
    PostoAzione,
    Promessa,
    PuntoStrada,
    SedeVerifica,
    Stagione,
    Stato,
    StatoCompetenza,
    StatoPassaggio,
    StatoStagione,
    Tappa,
    TipoCompetenza,
    TipoConclusione,
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


class AllegatoOut(Schema):
    id: int
    titolo: str
    tipo_file: str
    caricato_il: datetime


def _allegati(voce) -> list[dict]:
    return [
        {"id": a.pk, "titolo": a.titolo, "tipo_file": a.tipo_file, "caricato_il": a.creato_il}
        for a in voce.allegati.all()
    ]


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
    allegati: list[AllegatoOut] = []


class MetaOut(PercorsoOut):
    riservata: bool


class ImpegnoOut(PercorsoOut):
    criterio_verifica: str
    mete: list[int]
    stagione_id: int | None = None
    stagione: str = ""


class PassaggioRiassunto(Schema):
    data: date
    da: str
    a: str
    data_cerimonia: date | None
    sintesi: str


class ConclusioneOut(Schema):
    tipo: TipoConclusione
    tipo_nome: str
    data: DataOut
    nota: str


class PuntoStradaOut(Schema):
    id: int
    periodo_id: int
    data: date
    sintesi: str
    servizio: str
    # None: the user may not read what was faced in confidence (DEC-180).
    riservato: str | None
    # The rover's or scolta's own reading (DEC-188); None as for `riservato`.
    voce: str | None
    obiettivi: list[int]


class StagioneBreve(Schema):
    id: int
    nome: str
    stato: StatoStagione


class PiccoleOrmeOut(Schema):
    evento: str
    inizio: date
    fine: date
    stato: str


class PeriodoOut(Schema):
    id: int
    branca: str
    branca_nome: str
    inizio: DataOut
    fine: date | None
    motivo_fine: str
    attivo: bool
    # How the period began: the passage, with the summary for the new capi (spec §7).
    passaggio: PassaggioRiassunto | None
    promessa: DataOut | None
    tappe: list[TappaOut]
    # R/S only (DEC-67).
    firma_carta: DataOut | None = None
    conclusione: ConclusioneOut | None = None


class CompetenzaOut(Schema):
    id: int
    tipo: TipoCompetenza
    tipo_nome: str
    codice: str
    nome: str
    stato: StatoCompetenza
    stato_nome: str
    carta: str
    maestro: str
    confronto: str
    collegati: list[int]
    avviato_il: date | None
    verifica_proposta: bool
    riconosciuto: DataOut | None
    storico: bool
    distintivo: DataOut | None
    interrotto_il: date | None
    motivo_interruzione: str
    allegati: list[AllegatoOut] = []


class PostoOut(Schema):
    id: int
    impresa_id: int
    impresa: str
    impresa_livello: str
    persona_id: int
    persona: str
    ruolo: str
    impegno_id: int | None
    verificato_il: date | None
    sede_nome: str


class SchedaOut(Schema):
    persona_id: int
    persona: str
    periodi: list[PeriodoOut]
    mete: list[MetaOut]
    impegni: list[ImpegnoOut]
    competenze: list[CompetenzaOut]
    posti_azione: list[PostoOut]
    punti_strada: list[PuntoStradaOut]
    puo_scrivere_voce: bool
    # L/C (DEC-66, DEC-185): GIUNGLA or BOSCO for the names; the seasons of the unit a
    # preda or volo may refer to; the Piccole Orme lived (DEC-184).
    ambiente: str | None
    stagioni: list[StagioneBreve]
    piccole_orme: list[PiccoleOrmeOut]
    # What the user may do (the API checks again on every command).
    puo_gestire: bool
    puo_proporre: bool
    puo_proporre_verifica: bool
    sedi: list[dict]
    tipi_conclusione: list[dict]


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
        "allegati": _allegati(o),
    }


def _competenza_out(c: PercorsoCompetenza) -> dict:
    return {
        "id": c.pk,
        "tipo": c.tipo,
        "tipo_nome": c.get_tipo_display(),
        "codice": c.codice,
        "nome": c.nome,
        "stato": c.stato,
        "stato_nome": c.get_stato_display(),
        "carta": c.carta,
        "maestro": c.maestro,
        "confronto": c.confronto,
        "collegati": [a.pk for a in c.collegati.all()],
        "avviato_il": c.avviato_il,
        "verifica_proposta": c.verifica_proposta_il is not None,
        "riconosciuto": _d(c.riconosciuto_il, c.precisione_riconosciuto),
        "storico": c.storico,
        "distintivo": _d(c.distintivo_il, c.precisione_distintivo),
        "interrotto_il": c.interrotto_il,
        "motivo_interruzione": c.motivo_interruzione,
        "allegati": _allegati(c) if c.periodo_id else [],
    }


def _posto_out(p: PostoAzione) -> dict:
    return {
        "id": p.pk,
        "impresa_id": p.impresa_id,
        "impresa": p.impresa.titolo,
        "impresa_livello": p.impresa.get_livello_display(),
        "persona_id": p.persona_id,
        "persona": f"{p.persona.cognome} {p.persona.nome}",
        "ruolo": p.ruolo,
        "impegno_id": p.impegno_id,
        "verificato_il": p.verificato_il,
        "sede_nome": p.sede_descrizione or (p.get_sede_display() if p.sede else ""),
    }


def _passaggio_di(periodo: PeriodoBranca) -> dict | None:
    riga = (
        PassaggioPersona.objects.filter(periodo_destinazione=periodo)
        .select_related("passaggio__unita_origine", "passaggio__unita_destinazione")
        .first()
    )
    if riga is None:
        return None
    passaggio = riga.passaggio
    return {
        "data": passaggio.data,
        "da": str(passaggio.unita_origine),
        "a": str(passaggio.unita_destinazione),
        "data_cerimonia": passaggio.data_cerimonia,
        "sintesi": riga.sintesi,
    }


def _unita_lc(persona: Persona):
    return Unita.objects.filter(
        pk__in=Appartenenza.objects.attive()
        .filter(persona=persona, ruolo=RuoloAppartenenza.RAGAZZO)
        .values("unita_id"),
        tipo__in=[TipoUnita.BRANCO, TipoUnita.CERCHIO, TipoUnita.BRANCO_CERCHIO],
    )


def ambiente(persona: Persona) -> str | None:
    """The unit's setting, giungla (branco) or bosco (cerchio), whatever its composition
    and never by the child's sex (DEC-185, DEC-225). None: generic names (setting not
    known yet, or not in L/C)."""
    unita = _unita_lc(persona).first()
    if unita is None:
        return None
    if unita.ambiente in ("GIUNGLA", "BOSCO"):
        return unita.ambiente
    if unita.tipo == TipoUnita.BRANCO:
        return "GIUNGLA"
    if unita.tipo == TipoUnita.CERCHIO:
        return "BOSCO"
    return None


def _scheda(user, persona: Persona) -> dict:
    periodi = list(
        PeriodoBranca.objects.filter(persona=persona).prefetch_related("tappe__distintivo")
    )
    mete = Obiettivo.objects.filter(periodo__persona=persona).prefetch_related(
        "revisioni", "allegati"
    )
    if not policy.vede_mete_riservate(user, persona):
        mete = mete.filter(riservata=False)
    visibili = {m.pk for m in mete}
    vede_riservato = policy.vede_riservato_punto_strada(user, persona)
    impegni = (
        Impegno.objects.filter(periodo__persona=persona)
        .select_related("stagione")
        .prefetch_related("revisioni", "mete", "allegati")
    )
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
                "motivo_fine": p.motivo_fine,
                "attivo": p.data_fine is None,
                "passaggio": _passaggio_di(p),
                "promessa": (
                    _d(p.promessa.data, p.promessa.precisione) if hasattr(p, "promessa") else None
                ),
                "tappe": [_tappa_out(t) for t in p.tappe.all()],
                "firma_carta": (
                    _d(p.firma_carta.data, p.firma_carta.precisione)
                    if hasattr(p, "firma_carta")
                    else None
                ),
                "conclusione": (
                    {
                        "tipo": p.conclusione.tipo,
                        "tipo_nome": p.conclusione.get_tipo_display(),
                        "data": _d(p.conclusione.data, p.conclusione.precisione),
                        "nota": p.conclusione.nota,
                    }
                    if hasattr(p, "conclusione")
                    else None
                ),
            }
            for p in periodi
        ],
        "mete": [{**_percorso_out(m), "riservata": m.riservata} for m in mete],
        "impegni": [
            {
                **_percorso_out(i),
                "criterio_verifica": i.criterio_verifica,
                "stagione_id": i.stagione_id,
                "stagione": i.stagione.nome if i.stagione_id else "",
                # A private meta the user may not see is not even named.
                "mete": [m.pk for m in i.mete.all() if m.pk in visibili],
            }
            for i in impegni
        ],
        "competenze": [
            _competenza_out(c)
            for c in PercorsoCompetenza.objects.filter(periodo__persona=persona).prefetch_related(
                "collegati"
            )
        ],
        "posti_azione": [
            _posto_out(p)
            for p in PostoAzione.objects.filter(persona=persona).select_related(
                "impresa", "persona"
            )
        ],
        "puo_scrivere_voce": policy.puo_scrivere_voce_punto_strada(user, persona),
        "punti_strada": [
            {
                "id": ps.pk,
                "periodo_id": ps.periodo_id,
                "data": ps.data,
                "sintesi": ps.sintesi,
                "servizio": ps.servizio,
                "riservato": ps.riservato if vede_riservato else None,
                "voce": ps.voce if vede_riservato else None,
                "obiettivi": [o.pk for o in ps.obiettivi.all() if o.pk in visibili],
            }
            for ps in PuntoStrada.objects.filter(periodo__persona=persona).prefetch_related(
                "obiettivi"
            )
        ],
        "puo_gestire": policy.puo_gestire_progressione(user, persona),
        "puo_proporre": policy.puo_proporre_percorsi(user, persona),
        "puo_proporre_verifica": policy.puo_proporre_verifica(user, persona),
        "sedi": [{"valore": v, "etichetta": e} for v, e in SedeVerifica.choices],
        "tipi_conclusione": [{"valore": v, "etichetta": e} for v, e in TipoConclusione.choices],
        "ambiente": ambiente(persona),
        "stagioni": [
            {"id": s.pk, "nome": s.nome, "stato": s.stato}
            for s in Stagione.objects.filter(
                unita__in=_unita_lc(persona),
                stato__in=[StatoStagione.PREVISTA, StatoStagione.APERTA],
            )
        ],
        "piccole_orme": [
            {
                "evento": i.partecipazione.evento.titolo,
                "inizio": timezone.localdate(i.partecipazione.evento.inizio),
                "fine": timezone.localdate(i.partecipazione.evento.fine),
                "stato": i.get_stato_display(),
            }
            for i in IscrizioneBuonaCaccia.objects.filter(
                partecipazione__persona=persona,
                partecipazione__evento__buonacaccia__piccole_orme=True,
            ).select_related("partecipazione__evento")
        ],
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


class RiconoscimentoIn(DataIn):
    # L/C: history of who was already there, without the conquests recorded (V05).
    storico: bool = False


@router.post("/progressione/tappe/{tappa_id}/riconosci", response=SchedaOut)
def riconosci(request, tappa_id: int, dati: RiconoscimentoIn):
    """Recognised in the Consiglio della Legge (L/C: by the staff, after a conquest):
    the next tappa or momento starts."""
    tappa = _tappa(request, tappa_id)
    _esegui(servizi.riconosci_tappa, tappa, _quando(dati), request.auth, storico=dati.storico)
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


# --- R/S: Carta di clan, passi, Punto della Strada, conclusione (DEC-67, DEC-179…DEC-181) ---


@router.post("/progressione/periodi/{periodo_id}/carta", response=SchedaOut)
def firma_carta(request, periodo_id: int, dati: DataIn):
    """The Carta di clan, signed: the passi di competenza begin (V12)."""
    periodo = _periodo(request, periodo_id)
    _esegui(servizi.firma_carta, periodo, _quando(dati), request.auth)
    return _scheda(request.auth, periodo.persona)


@router.put("/progressione/periodi/{periodo_id}/carta", response=SchedaOut)
def rettifica_carta(request, periodo_id: int, dati: RettificaIn):
    periodo = _periodo(request, periodo_id)
    firma = get_object_or_404(FirmaCarta, periodo=periodo)
    _esegui(servizi.rettifica_firma, firma, _quando(dati), dati.motivo)
    return _scheda(request.auth, periodo.persona)


@router.post("/progressione/tappe/{tappa_id}/responsabilita", response=SchedaOut)
def responsabilita(request, tappa_id: int, dati: DataIn):
    """The confronto on the choices of the Partenza begins: passi di responsabilità."""
    tappa = _tappa(request, tappa_id)
    _esegui(servizi.avvia_responsabilita, tappa, _quando(dati), request.auth)
    return _scheda(request.auth, tappa.periodo.persona)


class ConclusioneIn(DataIn):
    tipo: TipoConclusione
    nota: str = ""


@router.post("/progressione/periodi/{periodo_id}/conclusione", response=SchedaOut)
def conclusione(request, periodo_id: int, dati: ConclusioneIn):
    """Partenza, saluto fraterno, interruzione or trasferimento: never automatic (V14)."""
    periodo = _periodo(request, periodo_id)
    _esegui(servizi.concludi, periodo, dati.tipo, _quando(dati), dati.nota, request.auth)
    return _scheda(request.auth, periodo.persona)


class PuntoStradaIn(Schema):
    data: date
    sintesi: str = ""
    servizio: str = ""
    # None leaves it as it is (who cannot read it cannot overwrite it).
    riservato: str | None = None
    obiettivi: list[int] = []


def _salva_punto(request, punto: PuntoStrada, dati: PuntoStradaIn):
    persona = punto.periodo.persona
    riservato = dati.riservato
    if riservato is not None and not policy.vede_riservato_punto_strada(request.auth, persona):
        riservato = None
    obiettivi = list(Obiettivo.objects.filter(pk__in=dati.obiettivi))
    with transaction.atomic():
        _esegui(
            servizi.salva_punto_strada,
            punto,
            request.auth,
            data=dati.data,
            sintesi=dati.sintesi,
            servizio=dati.servizio,
            riservato=riservato,
            obiettivi=obiettivi,
        )
    return _scheda(request.auth, persona)


@router.post("/progressione/periodi/{periodo_id}/punti-strada", response={201: SchedaOut})
def nuovo_punto_strada(request, periodo_id: int, dati: PuntoStradaIn):
    periodo = _periodo(request, periodo_id)
    return Status(201, _salva_punto(request, PuntoStrada(periodo=periodo), dati))


class VoceIn(Schema):
    testo: str


@router.put("/punti-strada/{punto_id}/voce", response=SchedaOut)
def voce_punto_strada(request, punto_id: int, dati: VoceIn):
    """Written by the rover or scolta only (DEC-188)."""
    punto = get_object_or_404(PuntoStrada.objects.select_related("periodo__persona"), pk=punto_id)
    persona = _persona(request, punto.periodo.persona_id)
    if not policy.puo_scrivere_voce_punto_strada(request.auth, persona):
        raise HttpError(403, "La propria rilettura la scrive il rover o la scolta.")
    _esegui(servizi.scrivi_voce, punto, dati.testo)
    return _scheda(request.auth, persona)


@router.put("/punti-strada/{punto_id}", response=SchedaOut)
def modifica_punto_strada(request, punto_id: int, dati: PuntoStradaIn):
    punto = get_object_or_404(PuntoStrada.objects.select_related("periodo"), pk=punto_id)
    _periodo(request, punto.periodo_id)
    return _salva_punto(request, punto, dati)


# --- Impegni and mete ----------------------------------------------------------------------


class PercorsoIn(Schema):
    testo: str
    termine: date | None = None


class MetaIn(PercorsoIn):
    riservata: bool = False


class ImpegnoIn(PercorsoIn):
    criterio_verifica: str = ""
    mete: list[int] = []
    # L/C: the stagione of the preda or volo.
    stagione_id: int | None = None


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
        Obiettivo,
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
            stagione=(
                get_object_or_404(Stagione, pk=dati.stagione_id) if dati.stagione_id else None
            ),
        )
        mete = list(Obiettivo.objects.filter(pk__in=dati.mete))
        _esegui(servizi.collega_mete, impegno, mete)
    return Status(201, _scheda(request.auth, persona))


MODELLI = {"mete": Obiettivo, "impegni": Impegno}


def _oggetto(request, tipo: str, oggetto_id: int):
    modello = MODELLI.get(tipo)
    if modello is None:
        raise HttpError(404, "Non trovato.")
    oggetto = get_object_or_404(modello.objects.select_related("periodo__persona"), pk=oggetto_id)
    persona = _persona(request, oggetto.periodo.persona_id)
    if (
        isinstance(oggetto, Obiettivo)
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
        if isinstance(oggetto, Obiettivo) and dati.riservata is not None:
            oggetto.riservata = dati.riservata
            oggetto.save(update_fields=["riservata", "aggiornato_il"])
        if isinstance(oggetto, Impegno) and dati.mete is not None:
            _esegui(servizi.collega_mete, oggetto, list(Obiettivo.objects.filter(pk__in=dati.mete)))
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
    specialita: int
    # V10: at least one brevetto in the sentiero, a reminder for the capi, never a block.
    brevetto: str | None


class SentieroUnita(Schema):
    unita: str
    branca: str
    ragazzi: list[RagazzoSentiero]
    puo_gestire: bool


def _brevetto(periodo) -> str | None:
    if periodo is None:
        return None
    brevetti = PercorsoCompetenza.objects.filter(periodo=periodo, tipo=TipoCompetenza.BREVETTO)
    if brevetti.filter(stato=StatoCompetenza.RICONOSCIUTO).exists():
        return "conquistato"
    if brevetti.exclude(stato=StatoCompetenza.INTERROTTO).exists():
        return "in corso"
    return None


@router.get("/unita/{unita_id}/progressione", response=SentieroUnita)
def sentiero_unita(request, unita_id: int):
    """Who has something to read again or to validate; sorted by name, never by
    "level" (spec §12.2). Cached on the capi's phones for meetings without network
    (DEC-95)."""
    unita = get_object_or_404(Unita, pk=unita_id)
    if not policy.e_capo_censito(request.auth):
        raise HttpError(403, "La vista dell'unità è dei capi.")
    if unita.tipo == TipoUnita.COMUNITA_CAPI:
        raise HttpError(400, "La Comunità capi non ha progressione personale.")
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
                    Obiettivo.objects.filter(periodo=periodo, stato=Stato.BOZZA).count()
                    if periodo
                    else 0
                ),
                "specialita": (
                    PercorsoCompetenza.objects.filter(
                        periodo=periodo,
                        tipo=(
                            TipoCompetenza.SPECIALITA_LC
                            if unita.branca == Branca.LC
                            else TipoCompetenza.SPECIALITA
                        ),
                        stato=StatoCompetenza.RICONOSCIUTO,
                    ).count()
                    if periodo
                    else 0
                ),
                "brevetto": _brevetto(periodo),
                "mete_aperte": (
                    Obiettivo.objects.filter(
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
        "branca": unita.branca,
        "ragazzi": righe,
        "puo_gestire": policy.e_staff(request.auth, unita),
    }


# --- Catalogs -------------------------------------------------------------------------------


class VoceOut(Schema):
    codice: str
    nome: str


class CataloghiOut(Schema):
    specialita: list[VoceOut]
    brevetti: list[VoceOut]
    specialita_squadriglia: list[VoceOut]
    specialita_lc: list[VoceOut]


@router.get("/progressione/cataloghi", response=CataloghiOut)
def cataloghi(request):
    """The current items (withdrawn ones are only kept in history, DEC-63)."""
    from .catalogo import voci

    def attive(tipo):
        return [{"codice": v.codice, "nome": v.nome} for v in voci(tipo) if not v.ritirata]

    return {
        "specialita": attive(TipoCompetenza.SPECIALITA),
        "brevetti": attive(TipoCompetenza.BREVETTO),
        "specialita_squadriglia": attive(TipoCompetenza.SPECIALITA_SQ),
        "specialita_lc": attive(TipoCompetenza.SPECIALITA_LC),
    }


# --- Specialità and brevetti of one E/G (DEC-62, DEC-63) ------------------------------------


class CompetenzaIn(Schema):
    tipo: TipoCompetenza
    codice: str
    carta: str = ""
    maestro: str = ""
    # Already conquered in a past year: recorded directly (spec §18.4).
    conquistata: DataIn | None = None


@router.post("/persone/{persona_id}/progressione/competenze", response={201: SchedaOut})
def nuova_competenza(request, persona_id: int, dati: CompetenzaIn):
    persona = _persona(request, persona_id)
    _gestore(request, persona)
    if dati.tipo == TipoCompetenza.SPECIALITA_SQ:
        raise HttpError(400, "Le specialità di squadriglia si registrano dalla pagina del reparto.")
    periodo = servizi.periodo_attivo(persona)
    if periodo is None:
        raise HttpError(400, "Il sentiero non è ancora aperto.")
    _esegui(
        servizi.nuova_competenza,
        dati.tipo,
        dati.codice,
        request.auth,
        periodo=periodo,
        carta=dati.carta,
        maestro=dati.maestro,
        storico=_quando(dati.conquistata) if dati.conquistata else None,
    )
    return Status(201, _scheda(request.auth, persona))


def _competenza(request, competenza_id: int) -> PercorsoCompetenza:
    """Who may see it: of a person, as their sentiero; of a patrol, the capi."""
    percorso = get_object_or_404(
        PercorsoCompetenza.objects.select_related("periodo__persona", "squadriglia__unita"),
        pk=competenza_id,
    )
    if percorso.periodo_id:
        _persona(request, percorso.periodo.persona_id)
    elif not policy.e_capo_censito(request.auth):
        raise HttpError(404, "Non trovato.")
    return percorso


def _gestore_competenza(request, percorso: PercorsoCompetenza) -> None:
    if percorso.periodo_id:
        _gestore(request, percorso.periodo.persona)
    elif not policy.puo_gestire_reparto_progressione(request.auth, percorso.squadriglia.unita):
        raise HttpError(403, "Lo registra lo staff del reparto.")


def _dopo_competenza(request, percorso: PercorsoCompetenza):
    if percorso.periodo_id:
        return _scheda(request.auth, percorso.periodo.persona)
    return _imprese(request.auth, percorso.squadriglia.unita)


class CompetenzaModificaIn(Schema):
    carta: str = ""
    maestro: str = ""
    confronto: str = ""
    collegati: list[int] = []


@router.put("/competenze/{competenza_id}", response=SchedaOut | dict)
def modifica_competenza(request, competenza_id: int, dati: CompetenzaModificaIn):
    """The carta, the maestro, the occasion of comparison (brevetto), the links."""
    percorso = _competenza(request, competenza_id)
    _gestore_competenza(request, percorso)
    with transaction.atomic():
        percorso.carta = dati.carta.strip()
        percorso.maestro = dati.maestro.strip()[:120]
        percorso.confronto = dati.confronto.strip()
        percorso.save()
        if percorso.tipo != TipoCompetenza.SPECIALITA:
            altri = list(PercorsoCompetenza.objects.filter(pk__in=dati.collegati))
            _esegui(servizi.collega_competenze, percorso, altri)
    return _dopo_competenza(request, percorso)


class PassoCompetenzaIn(Schema):
    il: date | None = None
    motivo: str = ""


@router.post("/competenze/{competenza_id}/distintivo", response=SchedaOut | dict)
def distintivo_competenza(request, competenza_id: int, dati: DataIn):
    percorso = _competenza(request, competenza_id)
    _gestore_competenza(request, percorso)
    _esegui(servizi.consegna_distintivo_competenza, percorso, _quando(dati))
    return _dopo_competenza(request, percorso)


@router.post("/competenze/{competenza_id}/{azione}", response=SchedaOut | dict)
def passo_competenza(request, competenza_id: int, azione: str, dati: PassoCompetenzaIn):
    """Spec §17.4. Asking for the verification of a personal path: the ragazzo and their
    CSQ too (DEC-13); the rest is the staff's."""
    percorso = _competenza(request, competenza_id)
    if azione == "proponi_verifica" and percorso.periodo_id:
        if not policy.puo_proporre_verifica(request.auth, percorso.periodo.persona):
            raise HttpError(
                403, "La verifica la propongono il ragazzo, il capo squadriglia o lo staff."
            )
    else:
        _gestore_competenza(request, percorso)
    _esegui(
        servizi.passo_competenza, percorso, azione, request.auth, il=dati.il, motivo=dati.motivo
    )
    return _dopo_competenza(request, percorso)


# --- Imprese and specialità di squadriglia (DEC-64, DEC-65) ---------------------------------


class ImpresaOut(Schema):
    id: int
    livello: LivelloImpresa
    livello_nome: str
    squadriglia_id: int | None
    squadriglia: str | None
    titolo: str
    descrizione: str
    dal: date
    al: date | None
    posti: list[PostoOut]
    consiglio: list[dict]
    # What the user may do with it (DEC-187).
    puo_modificare: bool
    puo_gestire_posti: bool


class SquadrigliaCompetenze(Schema):
    id: int
    nome: str
    competenze: list[CompetenzaOut]
    # Members' specialità and brevetti that may be linked to a patrol's path.
    individuali: list[dict]


class ImpreseOut(Schema):
    reparto_id: int
    reparto: str
    imprese: list[ImpresaOut]
    squadriglie: list[SquadrigliaCompetenze]
    ragazzi: list[dict]
    # The staff: everything; a CSQ also creates the imprese of their patrol (DEC-187).
    puo_gestire: bool
    puo_creare: bool
    sedi: list[dict]


def _imprese(user, reparto: Unita) -> dict:
    from apps.anagrafica.models import AppartenenzaSquadriglia

    capo = policy.e_capo_censito(user)
    gestisce = policy.puo_gestire_reparto_progressione(user, reparto)
    guidate = policy.squadriglie_guidate(user).filter(unita=reparto)
    imprese = (
        policy.imprese_visibili(user, reparto)
        .select_related("squadriglia", "reparto")
        .prefetch_related("consiglio")
    )
    ragazzi = Persona.objects.filter(
        pk__in=Appartenenza.objects.attive()
        .filter(unita=reparto, ruolo=RuoloAppartenenza.RAGAZZO)
        .values("persona_id")
    ).order_by("cognome", "nome")
    persona = policy.persona_di(user)
    if not capo and not (persona and imprese.filter(consiglio=persona).exists()):
        # A CSQ assigns posti only within their patrol: a practical limit, not a privacy
        # one (the ragazzi of a unit see each other's names, and patrols in a reparto, DEC-191).
        ragazzi = ragazzi.filter(
            pk__in=AppartenenzaSquadriglia.objects.attive()
            .filter(squadriglia__in=guidate)
            .values("persona_id")
        )
    squadriglie = []
    for sq in reparto.squadriglie.filter(attiva=True).order_by("nome"):
        if not capo:
            if guidate.filter(pk=sq.pk).exists():
                squadriglie.append(
                    {"id": sq.pk, "nome": sq.nome, "competenze": [], "individuali": []}
                )
            continue
        membri = (
            AppartenenzaSquadriglia.objects.attive().filter(squadriglia=sq).values("persona_id")
        )
        individuali = PercorsoCompetenza.objects.filter(
            periodo__persona_id__in=membri
        ).select_related("periodo__persona")
        squadriglie.append(
            {
                "id": sq.pk,
                "nome": sq.nome,
                "competenze": [
                    _competenza_out(c) for c in sq.competenze.prefetch_related("collegati")
                ],
                "individuali": [
                    {
                        "id": c.pk,
                        "testo": f"{c.nome} — {c.periodo.persona.nome} {c.periodo.persona.cognome}",
                    }
                    for c in individuali
                ],
            }
        )
    return {
        "reparto_id": reparto.pk,
        "reparto": str(reparto),
        "imprese": [
            {
                "id": i.pk,
                "livello": i.livello,
                "livello_nome": i.get_livello_display(),
                "squadriglia_id": i.squadriglia_id,
                "squadriglia": i.squadriglia.nome if i.squadriglia_id else None,
                "titolo": i.titolo,
                "descrizione": i.descrizione,
                "dal": i.dal,
                "al": i.al,
                "posti": [_posto_out(p) for p in i.posti.select_related("impresa", "persona")],
                "consiglio": [
                    {"id": p.pk, "nome": f"{p.cognome} {p.nome}"} for p in i.consiglio.all()
                ],
                "puo_modificare": policy.puo_modificare_impresa(user, i),
                "puo_gestire_posti": policy.puo_gestire_posti(user, i),
            }
            for i in imprese
        ],
        "squadriglie": squadriglie,
        "ragazzi": [{"id": p.pk, "nome": f"{p.cognome} {p.nome}"} for p in ragazzi],
        "puo_gestire": gestisce,
        "puo_creare": gestisce or guidate.exists(),
        "sedi": [{"valore": v, "etichetta": e} for v, e in SedeVerifica.choices],
    }


def _reparto(request, unita_id: int) -> Unita:
    reparto = get_object_or_404(Unita, pk=unita_id)
    if not (
        policy.e_capo_censito(request.auth) or policy.reparto_imprese(request.auth) == reparto.pk
    ):
        raise HttpError(
            403, "Le imprese le vedono i capi, i capi squadriglia e i Consigli d'impresa."
        )
    if reparto.branca != Branca.EG:
        raise HttpError(400, "Le imprese sono del reparto.")
    return reparto


def _gestore_reparto(request, reparto: Unita) -> None:
    if not policy.puo_gestire_reparto_progressione(request.auth, reparto):
        raise HttpError(403, "Le registra lo staff del reparto.")


@router.get("/unita/{unita_id}/imprese", response=ImpreseOut)
def imprese(request, unita_id: int):
    return _imprese(request.auth, _reparto(request, unita_id))


class ImpresaIn(Schema):
    livello: LivelloImpresa
    squadriglia_id: int | None = None
    titolo: str
    descrizione: str = ""
    dal: date
    al: date | None = None


def _salva_impresa(impresa: Impresa, dati: ImpresaIn) -> None:
    from apps.organizzazione.models import Squadriglia

    impresa.livello = dati.livello
    impresa.squadriglia = (
        get_object_or_404(Squadriglia, pk=dati.squadriglia_id)
        if dati.livello == LivelloImpresa.SQUADRIGLIA and dati.squadriglia_id
        else None
    )
    impresa.titolo = dati.titolo.strip()
    impresa.descrizione = dati.descrizione.strip()
    impresa.dal = dati.dal
    impresa.al = dati.al
    _esegui(impresa.full_clean)
    impresa.save()


@router.post("/unita/{unita_id}/imprese", response={201: ImpreseOut})
def nuova_impresa(request, unita_id: int, dati: ImpresaIn):
    from apps.organizzazione.models import Squadriglia

    reparto = _reparto(request, unita_id)
    squadriglia = (
        Squadriglia.objects.filter(pk=dati.squadriglia_id).first() if dati.squadriglia_id else None
    )
    if not policy.puo_creare_impresa(request.auth, reparto, dati.livello, squadriglia):
        raise HttpError(
            403,
            "Le imprese le registra lo staff; il capo squadriglia quelle della sua squadriglia.",
        )
    _salva_impresa(Impresa(reparto=reparto, creata_da=request.auth), dati)
    return Status(201, _imprese(request.auth, reparto))


def _impresa(request, impresa_id: int) -> tuple[Impresa, Unita]:
    impresa = get_object_or_404(Impresa.objects.select_related("reparto"), pk=impresa_id)
    reparto = _reparto(request, impresa.reparto_id)
    if not policy.imprese_visibili(request.auth, reparto).filter(pk=impresa.pk).exists():
        raise HttpError(404, "Impresa non trovata.")
    return impresa, reparto


@router.put("/imprese/{impresa_id}", response=ImpreseOut)
def modifica_impresa(request, impresa_id: int, dati: ImpresaIn):
    impresa, reparto = _impresa(request, impresa_id)
    if not policy.puo_modificare_impresa(request.auth, impresa):
        raise HttpError(403, "Non puoi modificare questa impresa.")
    if not policy.puo_gestire_reparto_progressione(request.auth, reparto) and (
        dati.livello != LivelloImpresa.SQUADRIGLIA or dati.squadriglia_id != impresa.squadriglia_id
    ):
        raise HttpError(403, "Resta un'impresa della tua squadriglia.")
    _salva_impresa(impresa, dati)
    return _imprese(request.auth, reparto)


class ConsiglioIn(Schema):
    persone: list[int]


@router.put("/imprese/{impresa_id}/consiglio", response=ImpreseOut)
def consiglio_impresa(request, impresa_id: int, dati: ConsiglioIn):
    """The Consiglio d'impresa of a reparto or Alta Squadriglia impresa, appointed by the
    staff among the ragazzi of the reparto (DEC-187)."""
    impresa, reparto = _impresa(request, impresa_id)
    _gestore_reparto(request, reparto)
    if impresa.livello == LivelloImpresa.SQUADRIGLIA:
        raise HttpError(400, "L'impresa di squadriglia la guida il capo squadriglia.")
    persone = list(servizi.ragazzi_di(reparto).filter(pk__in=dati.persone))
    if len(persone) != len(set(dati.persone)):
        raise HttpError(400, "Scegli ragazzi del reparto.")
    impresa.consiglio.set(persone)
    return _imprese(request.auth, reparto)


class PostoIn(Schema):
    persona_id: int
    ruolo: str
    impegno_id: int | None = None


@router.post("/imprese/{impresa_id}/posti", response={201: ImpreseOut})
def nuovo_posto(request, impresa_id: int, dati: PostoIn):
    from apps.anagrafica.models import AppartenenzaSquadriglia

    impresa, reparto = _impresa(request, impresa_id)
    if not policy.puo_gestire_posti(request.auth, impresa):
        raise HttpError(403, "Non puoi assegnare posti d'azione in questa impresa.")
    staff = policy.puo_gestire_reparto_progressione(request.auth, reparto)
    persona = get_object_or_404(Persona, pk=dati.persona_id)
    if not Appartenenza.objects.attive().filter(persona=persona, unita=reparto).exists():
        raise HttpError(400, "Scegli un ragazzo del reparto.")
    if (
        not staff
        and impresa.squadriglia_id
        and not AppartenenzaSquadriglia.objects.attive()
        .filter(persona=persona, squadriglia=impresa.squadriglia_id)
        .exists()
    ):
        raise HttpError(400, "Scegli uno della squadriglia.")
    if dati.impegno_id and not staff:
        # The impegni of the others are not the ragazzi's to read.
        raise HttpError(403, "Il collegamento all'impegno lo fa lo staff.")
    if not dati.ruolo.strip():
        raise HttpError(400, "Scrivi il posto d'azione.")
    impegno = (
        get_object_or_404(Impegno, pk=dati.impegno_id, periodo__persona=persona)
        if dati.impegno_id
        else None
    )
    PostoAzione.objects.create(
        impresa=impresa, persona=persona, ruolo=dati.ruolo.strip()[:160], impegno=impegno
    )
    return Status(201, _imprese(request.auth, reparto))


class VerificaPostoIn(Schema):
    il: date
    sede: str
    sede_descrizione: str = ""


@router.post("/posti-azione/{posto_id}/verifica", response=ImpreseOut)
def verifica_posto(request, posto_id: int, dati: VerificaPostoIn):
    posto = get_object_or_404(PostoAzione.objects.select_related("impresa"), pk=posto_id)
    impresa, reparto = _impresa(request, posto.impresa_id)
    if not policy.puo_gestire_posti(request.auth, impresa):
        raise HttpError(403, "Non puoi registrare questa verifica.")
    _esegui(
        servizi.verifica_posto,
        posto,
        request.auth,
        il=dati.il,
        sede=dati.sede,
        sede_descrizione=dati.sede_descrizione,
    )
    return _imprese(request.auth, reparto)


class SpecialitaSquadrigliaIn(Schema):
    codice: str
    carta: str = ""
    conquistata: DataIn | None = None


@router.post("/squadriglie/{squadriglia_id}/competenze", response={201: ImpreseOut})
def nuova_specialita_squadriglia(request, squadriglia_id: int, dati: SpecialitaSquadrigliaIn):
    from apps.organizzazione.models import Squadriglia

    squadriglia = get_object_or_404(Squadriglia, pk=squadriglia_id)
    reparto = _reparto(request, squadriglia.unita_id)
    _gestore_reparto(request, reparto)
    _esegui(
        servizi.nuova_competenza,
        TipoCompetenza.SPECIALITA_SQ,
        dati.codice,
        request.auth,
        squadriglia=squadriglia,
        carta=dati.carta,
        storico=_quando(dati.conquistata) if dati.conquistata else None,
    )
    return Status(201, _imprese(request.auth, reparto))


# --- Passaggi tra branche (DEC-69, DEC-174…DEC-177) -----------------------------------------


class PersonaPassaggioIO(Schema):
    persona_id: int
    persona: str = ""
    sintesi: str = ""
    # Undone after execution (DEC-178), with the reason.
    rettificata: bool = False
    motivo_rettifica: str = ""


class PassaggioOut(Schema):
    id: int
    unita_origine_id: int
    unita_origine: str
    unita_destinazione_id: int
    unita_destinazione: str
    data: date
    data_decisione: date | None
    data_cerimonia: date | None
    stato: StatoPassaggio
    stato_nome: str
    motivo_annullamento: str
    nota_rettifica: str
    persone: list[PersonaPassaggioIO]
    puo_gestire: bool


class PassaggiUnita(Schema):
    unita: str
    in_uscita: list[PassaggioOut]
    in_entrata: list[PassaggioOut]
    ragazzi: list[dict]
    destinazioni: list[dict]
    puo_preparare: bool


def _passaggio_out(user, p: Passaggio) -> dict:
    return {
        "id": p.pk,
        "unita_origine_id": p.unita_origine_id,
        "unita_origine": str(p.unita_origine),
        "unita_destinazione_id": p.unita_destinazione_id,
        "unita_destinazione": str(p.unita_destinazione),
        "data": p.data,
        "data_decisione": p.data_decisione,
        "data_cerimonia": p.data_cerimonia,
        "stato": p.stato,
        "stato_nome": p.get_stato_display(),
        "motivo_annullamento": p.motivo_annullamento,
        "nota_rettifica": p.nota_rettifica,
        "persone": [
            {
                "persona_id": r.persona_id,
                "persona": f"{r.persona.cognome} {r.persona.nome}",
                "sintesi": r.sintesi,
                "rettificata": r.rettificata_il is not None,
                "motivo_rettifica": r.motivo_rettifica,
            }
            for r in p.persone.select_related("persona")
        ],
        "puo_gestire": policy.puo_gestire_passaggi(user, p.unita_origine),
    }


def _passaggi(user, unita: Unita) -> dict:
    successiva = servizi.SUCCESSIVA.get(unita.branca)
    destinazioni = [
        u
        for u in Unita.objects.filter(attiva=True)
        if successiva is not None and u.branca == successiva
    ]
    relazioni = ("unita_origine", "unita_destinazione")
    return {
        "unita": str(unita),
        "in_uscita": [
            _passaggio_out(user, p)
            for p in Passaggio.objects.filter(unita_origine=unita).select_related(*relazioni)
        ],
        "in_entrata": [
            _passaggio_out(user, p)
            for p in Passaggio.objects.filter(unita_destinazione=unita).select_related(*relazioni)
        ],
        "ragazzi": [
            {"id": p.pk, "nome": f"{p.cognome} {p.nome}"}
            for p in servizi.ragazzi_di(unita).order_by("cognome", "nome")
        ],
        "destinazioni": [{"id": u.pk, "nome": str(u)} for u in destinazioni],
        "puo_preparare": bool(destinazioni) and policy.puo_gestire_passaggi(user, unita),
    }


def _unita_passaggi(request, unita_id: int) -> Unita:
    if not policy.e_capo_censito(request.auth):
        raise HttpError(403, "I passaggi li vedono i capi.")
    return get_object_or_404(Unita, pk=unita_id)


@router.get("/unita/{unita_id}/passaggi", response=PassaggiUnita)
def passaggi(request, unita_id: int):
    return _passaggi(request.auth, _unita_passaggi(request, unita_id))


class Motivo(Schema):
    motivo: str


class PassaggioIn(Schema):
    unita_destinazione_id: int
    data: date
    data_decisione: date | None = None
    data_cerimonia: date | None = None
    persone: list[PersonaPassaggioIO]


def _compila(request, passaggio: Passaggio, dati: PassaggioIn) -> None:
    passaggio.unita_destinazione = get_object_or_404(Unita, pk=dati.unita_destinazione_id)
    passaggio.data = dati.data
    passaggio.data_decisione = dati.data_decisione
    passaggio.data_cerimonia = dati.data_cerimonia
    persone = {p.pk: p for p in Persona.objects.filter(pk__in=[r.persona_id for r in dati.persone])}
    righe = [(persone[r.persona_id], r.sintesi) for r in dati.persone if r.persona_id in persone]
    _esegui(servizi.prepara_passaggio, passaggio, righe, request.auth)


@router.post("/unita/{unita_id}/passaggi", response={201: PassaggiUnita})
def prepara(request, unita_id: int, dati: PassaggioIn):
    unita = _unita_passaggi(request, unita_id)
    if not policy.puo_gestire_passaggi(request.auth, unita):
        raise HttpError(403, "Il passaggio lo prepara lo staff dell'unità o un capogruppo.")
    with transaction.atomic():
        _compila(request, Passaggio(unita_origine=unita), dati)
    return Status(201, _passaggi(request.auth, unita))


def _passaggio(request, passaggio_id: int) -> Passaggio:
    passaggio = get_object_or_404(
        Passaggio.objects.select_related("unita_origine", "unita_destinazione"), pk=passaggio_id
    )
    _unita_passaggi(request, passaggio.unita_origine_id)
    if not policy.puo_gestire_passaggi(request.auth, passaggio.unita_origine):
        raise HttpError(403, "Il passaggio lo gestisce lo staff dell'unità o un capogruppo.")
    return passaggio


@router.put("/passaggi/{passaggio_id}", response=PassaggiUnita)
def modifica_passaggio(request, passaggio_id: int, dati: PassaggioIn):
    passaggio = _passaggio(request, passaggio_id)
    with transaction.atomic():
        _compila(request, passaggio, dati)
    return _passaggi(request.auth, passaggio.unita_origine)


@router.post("/passaggi/{passaggio_id}/esegui", response=PassaggiUnita)
def esegui_passaggio(request, passaggio_id: int):
    """Also from the offline queue: executed twice = done (DEC-96)."""
    passaggio = _passaggio(request, passaggio_id)
    _esegui(servizi.esegui_passaggio, passaggio, request.auth)
    return _passaggi(request.auth, passaggio.unita_origine)


@router.post("/passaggi/{passaggio_id}/annulla", response=PassaggiUnita)
def annulla_passaggio(request, passaggio_id: int, dati: Motivo):
    passaggio = _passaggio(request, passaggio_id)
    _esegui(servizi.annulla_passaggio, passaggio, dati.motivo)
    return _passaggi(request.auth, passaggio.unita_origine)


class AnnullaEsecuzioneIn(Schema):
    motivo: str
    # None: everyone in the passage.
    persone: list[int] | None = None


@router.post("/passaggi/{passaggio_id}/annulla-esecuzione", response=PassaggiUnita)
def annulla_esecuzione(request, passaggio_id: int, dati: AnnullaEsecuzioneIn):
    """Executed by mistake (DEC-178): undone for some ragazzi or all, with the reason;
    refused when the new staff already recorded something or BuonaStrada was imported
    since."""
    passaggio = _passaggio(request, passaggio_id)
    persone = list(Persona.objects.filter(pk__in=dati.persone)) if dati.persone else None
    _esegui(servizi.annulla_esecuzione, passaggio, dati.motivo, request.auth, persone)
    return _passaggi(request.auth, passaggio.unita_origine)


class CorreggiDataIn(Schema):
    data: date
    motivo: str


@router.post("/passaggi/{passaggio_id}/correggi-data", response=PassaggiUnita)
def correggi_data(request, passaggio_id: int, dati: CorreggiDataIn):
    passaggio = _passaggio(request, passaggio_id)
    _esegui(servizi.correggi_data, passaggio, dati.data, dati.motivo)
    return _passaggi(request.auth, passaggio.unita_origine)


# --- L/C: stagioni di caccia o di volo (DEC-66, DEC-183; spec §4.2, §17.5) ------------------


class StagioneOut(Schema):
    id: int
    nome: str
    stato: StatoStagione
    stato_nome: str
    inizio_previsto: date
    fine_prevista: date
    lancio: date | None
    chiusa_il: date | None
    prede: int
    conquistate: int
    # Still open: to look at again with the capi, never conquered by the closing (V04).
    da_rileggere: list[str]
    avvisi: list[str]


class StagioniUnita(Schema):
    unita: str
    stagioni: list[StagioneOut]
    puo_gestire: bool


def _stagioni(user, unita: Unita) -> dict:
    righe = []
    for s in unita.stagioni.all():
        prede = s.prede.all()
        righe.append(
            {
                "id": s.pk,
                "nome": s.nome,
                "stato": s.stato,
                "stato_nome": s.get_stato_display(),
                "inizio_previsto": s.inizio_previsto,
                "fine_prevista": s.fine_prevista,
                "lancio": s.lancio,
                "chiusa_il": s.chiusa_il,
                "prede": prede.count(),
                "conquistate": prede.filter(stato=Stato.CONCLUSO).count(),
                "da_rileggere": [
                    f"{p.periodo.persona.cognome} {p.periodo.persona.nome}: {p.testo}"
                    for p in servizi.da_rileggere(s)
                ],
                "avvisi": servizi.avvisi_stagione(s),
            }
        )
    return {
        "unita": str(unita),
        "stagioni": righe,
        "puo_gestire": policy.puo_gestire_unita_progressione(user, unita),
    }


def _unita_lc_capo(request, unita_id: int) -> Unita:
    unita = get_object_or_404(Unita, pk=unita_id)
    if not policy.e_capo_censito(request.auth):
        raise HttpError(403, "Le stagioni le vedono i capi.")
    if unita.branca != Branca.LC:
        raise HttpError(400, "Le stagioni sono dei branchi e dei cerchi.")
    return unita


@router.get("/unita/{unita_id}/stagioni", response=StagioniUnita)
def stagioni(request, unita_id: int):
    return _stagioni(request.auth, _unita_lc_capo(request, unita_id))


class StagioneIn(Schema):
    nome: str
    inizio_previsto: date
    fine_prevista: date


def _gestore_stagioni(request, unita: Unita) -> None:
    if not policy.puo_gestire_unita_progressione(request.auth, unita):
        raise HttpError(403, "Le stagioni le gestisce lo staff dell'unità.")


@router.post("/unita/{unita_id}/stagioni", response={201: StagioniUnita})
def nuova_stagione(request, unita_id: int, dati: StagioneIn):
    unita = _unita_lc_capo(request, unita_id)
    _gestore_stagioni(request, unita)
    _esegui(servizi.salva_stagione, Stagione(unita=unita), request.auth, **dati.dict())
    return Status(201, _stagioni(request.auth, unita))


def _stagione(request, stagione_id: int) -> Stagione:
    stagione = get_object_or_404(Stagione.objects.select_related("unita"), pk=stagione_id)
    _unita_lc_capo(request, stagione.unita_id)
    _gestore_stagioni(request, stagione.unita)
    return stagione


@router.put("/stagioni/{stagione_id}", response=StagioniUnita)
def modifica_stagione(request, stagione_id: int, dati: StagioneIn):
    stagione = _stagione(request, stagione_id)
    _esegui(servizi.salva_stagione, stagione, request.auth, **dati.dict())
    return _stagioni(request.auth, stagione.unita)


class PassoStagioneIn(Schema):
    il: date | None = None


@router.post("/stagioni/{stagione_id}/{azione}", response=StagioniUnita)
def passo_stagione(request, stagione_id: int, azione: str, dati: PassoStagioneIn):
    """lancia (the festive launch opens it), chiudi (the actual end), annulla."""
    stagione = _stagione(request, stagione_id)
    il = dati.il or servizi.oggi()
    if azione == "lancia":
        _esegui(servizi.lancia_stagione, stagione, il)
    elif azione == "chiudi":
        _esegui(servizi.chiudi_stagione, stagione, il)
    elif azione == "annulla":
        _esegui(servizi.annulla_stagione, stagione)
    else:
        raise HttpError(404, "Operazione sconosciuta.")
    return _stagioni(request.auth, stagione.unita)


# --- Attachments (DEC-42, DEC-202) -----------------------------------------------------------


@router.post("/allegati-pp/{tipo}/{voce_id}", response={201: SchedaOut})
def carica_allegato(request, tipo: str, voce_id: int, titolo: Form[str], file: File[UploadedFile]):
    """An image or a PDF on an impegno, a meta or obiettivo, a specialità or brevetto."""
    from apps.buonacaccia.servizi import _file_con_nome_casuale

    if tipo == "competenze":
        voce = _competenza(request, voce_id)
        if voce.periodo_id is None:
            raise HttpError(400, "Gli allegati vanno sulle specialità e sui brevetti dei singoli.")
        persona = voce.periodo.persona
    else:
        voce, persona = _oggetto(request, tipo, voce_id)
    if not policy.puo_caricare_allegato_pp(request.auth, persona):
        raise HttpError(403, "Gli allegati li caricano lo staff e il ragazzo.")
    if not titolo.strip():
        raise HttpError(400, "Scrivi cos'è l'allegato.")
    salvato, tipo_file = _esegui(
        _file_con_nome_casuale,
        file,
        {"application/pdf": ".pdf", "image/jpeg": ".jpg", "image/png": ".png"},
        "Carica un PDF o un'immagine (JPEG o PNG).",
    )
    allegato = AllegatoPP(
        titolo=titolo.strip()[:120], tipo_file=tipo_file, file=salvato, caricato_da=request.auth
    )
    setattr(allegato, {"mete": "obiettivo", "impegni": "impegno"}.get(tipo, "competenza"), voce)
    _esegui(allegato.full_clean)
    allegato.save()
    return Status(201, _scheda(request.auth, persona))


def _allegato(request, allegato_id: int) -> tuple[AllegatoPP, Persona]:
    allegato = get_object_or_404(
        AllegatoPP.objects.select_related(
            "obiettivo__periodo__persona",
            "impegno__periodo__persona",
            "competenza__periodo__persona",
        ),
        pk=allegato_id,
    )
    if allegato.competenza_id:
        _competenza(request, allegato.competenza_id)
        persona = allegato.competenza.periodo.persona
    else:
        tipo = "mete" if allegato.obiettivo_id else "impegni"
        _, persona = _oggetto(request, tipo, allegato.voce.pk)
    return allegato, persona


@router.get("/allegati-pp/{allegato_id}")
def scarica_allegato(request, allegato_id: int):
    """Served only here, to who reads the item; the name carries no person's name."""
    allegato, _ = _allegato(request, allegato_id)
    estensione = {"application/pdf": "pdf", "image/jpeg": "jpg", "image/png": "png"}
    risposta = HttpResponse(allegato.file.read(), content_type=allegato.tipo_file)
    risposta["Content-Disposition"] = (
        f'inline; filename="allegato-{allegato.pk}.{estensione.get(allegato.tipo_file, "bin")}"'
    )
    risposta["Cache-Control"] = "private, no-store"
    risposta["X-Content-Type-Options"] = "nosniff"
    return risposta


@router.delete("/allegati-pp/{allegato_id}", response=SchedaOut)
def togli_allegato(request, allegato_id: int):
    """Who uploaded it, or the staff."""
    allegato, persona = _allegato(request, allegato_id)
    if not (
        allegato.caricato_da_id == request.auth.pk
        or policy.puo_gestire_progressione(request.auth, persona)
    ):
        raise HttpError(403, "Lo toglie chi l'ha caricato o lo staff.")
    allegato.file.delete(save=False)
    allegato.delete()
    return _scheda(request.auth, persona)
