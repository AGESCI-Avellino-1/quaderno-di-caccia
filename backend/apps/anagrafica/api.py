from datetime import date, datetime

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from ninja import Router, Schema
from ninja.errors import HttpError

from apps.permessi import policy
from apps.permessi.policy import LivelloAccesso

from . import servizi
from .models import (
    CAMPI_BUONASTRADA,
    ETICHETTE_CAMPI,
    STATI_APERTI,
    Appartenenza,
    CorrezioneAnagrafica,
    Persona,
    StatoCorrezione,
)

router = Router(tags=["anagrafica"])


class PersonaElenco(Schema):
    id: int
    nome: str
    cognome: str
    codice_socio: str | None


class PersonaDettaglio(Schema):
    """Fields are filled according to the caller's access level (apps.permessi)."""

    id: int
    nome: str
    cognome: str
    livello_accesso: str
    data_nascita: date | None = None
    codice_socio: str | None = None
    email: str | None = None
    cellulare: str | None = None
    indirizzo: str | None = None
    comune: str | None = None
    consenso_foto: bool | None = None
    unita: list[str] = []


@router.get("/persone", response=list[PersonaElenco])
def elenco_persone(request, unita: int | None = None):
    persone = policy.persone_visibili(request.auth)
    if unita is not None:
        ids = Appartenenza.objects.attive().filter(unita_id=unita).values("persona_id")
        persone = persone.filter(pk__in=ids)
    return persone.order_by("cognome", "nome")


@router.get("/persone/{persona_id}", response=PersonaDettaglio)
def dettaglio_persona(request, persona_id: int):
    persona = get_object_or_404(Persona, pk=persona_id)
    livello = policy.livello_accesso(request.auth, persona)
    if livello == LivelloAccesso.NESSUNO:
        raise HttpError(404, "Persona non trovata.")
    dati = {
        "id": persona.pk,
        "nome": persona.nome,
        "cognome": persona.cognome,
        "livello_accesso": livello.value,
        "unita": [str(a.unita) for a in Appartenenza.objects.attive().filter(persona=persona)],
    }
    if livello != LivelloAccesso.SQUADRIGLIA:
        dati |= {
            "data_nascita": persona.data_nascita,
            "codice_socio": persona.codice_socio,
            "consenso_foto": persona.consenso_foto,
        }
    if policy.puo_vedere_dati_sensibili(request.auth, persona):
        dati |= {
            "email": persona.email,
            "cellulare": persona.cellulare,
            "indirizzo": f"{persona.indirizzo} {persona.civico}".strip(),
            "comune": persona.comune,
        }
    return dati


# --- Corrections to BuonaStrada data (DEC-31) ---------------------------------------


class Scelta(Schema):
    valore: str
    etichetta: str


class PersonaBreve(Schema):
    id: int
    nome: str
    cognome: str
    codice_socio: str | None


class CorrezioneOut(Schema):
    id: int
    campo: str
    etichetta: str
    valore_precedente: str
    valore_corretto: str
    stato: str
    stato_nome: str
    creata_il: datetime
    richiesta_da: str | None
    inoltrata_il: datetime | None
    chiusa_il: datetime | None
    motivo_scarto: str


class CorrezioneElenco(CorrezioneOut):
    persona: PersonaBreve


class CampoCorreggibile(Schema):
    campo: str
    etichetta: str
    tipo: str  # testo, data, numero, si_no, scelta
    valore: str
    scelte: list[Scelta] = []
    correzione: CorrezioneOut | None = None


class SchedaCorrezioni(Schema):
    campi: list[CampoCorreggibile]
    chiuse: list[CorrezioneOut]


class NuovaCorrezione(Schema):
    campo: str
    valore: str


class Scarto(Schema):
    motivo: str


def _nome_utente(utente) -> str | None:
    if utente is None:
        return None
    persona = policy.persona_di(utente)
    return f"{persona.nome} {persona.cognome}" if persona else utente.email


def _correzione_out(c: CorrezioneAnagrafica) -> dict:
    return {
        "id": c.pk,
        "campo": c.campo,
        "etichetta": ETICHETTE_CAMPI.get(c.campo, c.campo),
        "valore_precedente": c.valore_precedente,
        "valore_corretto": c.valore_corretto,
        "stato": c.stato,
        "stato_nome": c.get_stato_display(),
        "creata_il": c.creato_il,
        "richiesta_da": _nome_utente(c.richiesta_da),
        "inoltrata_il": c.inoltrata_il,
        "chiusa_il": c.chiusa_il,
        "motivo_scarto": c.motivo_scarto,
    }


def _tipo(campo: str) -> tuple[str, list[dict]]:
    field = Persona._meta.get_field(campo)
    if field.choices:
        return "scelta", [{"valore": str(v), "etichetta": str(e)} for v, e in field.choices]
    tipo = field.get_internal_type()
    if tipo == "DateField":
        return "data", []
    if tipo == "BooleanField":
        return "si_no", []
    if tipo in {"PositiveSmallIntegerField", "IntegerField"}:
        return "numero", []
    return "testo", []


def _scheda(user, persona: Persona) -> dict:
    ammessi = policy.campi_correggibili(user, persona)
    if not ammessi:
        raise HttpError(404, "Persona non trovata.")
    correzioni = list(
        CorrezioneAnagrafica.objects.filter(persona=persona, campo__in=ammessi)
        .select_related("richiesta_da")
        .order_by("-creato_il")
    )
    aperte = {c.campo: c for c in correzioni if c.stato in STATI_APERTI}
    campi = []
    for campo in CAMPI_BUONASTRADA:  # model order: identity, contacts, the rest
        if campo not in ammessi:
            continue
        tipo, scelte = _tipo(campo)
        aperta = aperte.get(campo)
        campi.append(
            {
                "campo": campo,
                "etichetta": ETICHETTE_CAMPI[campo],
                "tipo": tipo,
                "valore": servizi.come_testo(getattr(persona, campo)),
                "scelte": scelte,
                "correzione": _correzione_out(aperta) if aperta else None,
            }
        )
    chiuse = [_correzione_out(c) for c in correzioni if c.stato not in STATI_APERTI][:20]
    return {"campi": campi, "chiuse": chiuse}


@router.get("/persone/{persona_id}/correzioni", response=SchedaCorrezioni)
def scheda_correzioni(request, persona_id: int):
    persona = get_object_or_404(Persona, pk=persona_id)
    return _scheda(request.auth, persona)


@router.post("/persone/{persona_id}/correzioni", response=SchedaCorrezioni)
def correggi(request, persona_id: int, dati: NuovaCorrezione):
    persona = get_object_or_404(Persona, pk=persona_id)
    ammessi = policy.campi_correggibili(request.auth, persona)
    if not ammessi:
        raise HttpError(404, "Persona non trovata.")
    if dati.campo not in ammessi:
        raise HttpError(403, "Questo dato lo possono correggere solo i capigruppo.")
    try:
        servizi.correggi_campo(persona, dati.campo, dati.valore, richiesta_da=request.auth)
    except ValidationError as errore:
        raise HttpError(400, " ".join(errore.messages)) from errore
    persona.refresh_from_db()
    return _scheda(request.auth, persona)


@router.get("/correzioni", response=list[CorrezioneElenco])
def elenco_correzioni(request, aperte: bool = True):
    """For the capigruppo: what to forward to the regional office (DEC-31)."""
    if not policy.puo_gestire_correzioni(request.auth):
        raise HttpError(403, "Le correzioni le gestiscono i capigruppo.")
    correzioni = CorrezioneAnagrafica.objects.select_related("persona", "richiesta_da")
    if aperte:
        correzioni = correzioni.filter(stato__in=STATI_APERTI).order_by("stato", "creato_il")
    else:
        correzioni = correzioni.exclude(stato__in=STATI_APERTI).order_by("-chiusa_il")[:100]
    return [_correzione_out(c) | {"persona": c.persona} for c in correzioni]


def _correzione_da_gestire(request, correzione_id: int) -> CorrezioneAnagrafica:
    if not policy.puo_gestire_correzioni(request.auth):
        raise HttpError(403, "Le correzioni le gestiscono i capigruppo.")
    return get_object_or_404(
        CorrezioneAnagrafica.objects.select_related("persona", "richiesta_da"),
        pk=correzione_id,
    )


@router.post("/correzioni/{correzione_id}/inoltra", response=CorrezioneElenco)
def inoltra(request, correzione_id: int):
    correzione = _correzione_da_gestire(request, correzione_id)
    if correzione.stato != StatoCorrezione.IN_ATTESA:
        raise HttpError(409, "Questa correzione non è da inoltrare.")
    servizi.inoltra_correzione(correzione, request.auth)
    return _correzione_out(correzione) | {"persona": correzione.persona}


@router.post("/correzioni/{correzione_id}/scarta", response=CorrezioneElenco)
def scarta(request, correzione_id: int, dati: Scarto):
    correzione = _correzione_da_gestire(request, correzione_id)
    if not correzione.aperta:
        raise HttpError(409, "Questa correzione è già chiusa.")
    try:
        servizi.scarta_correzione(correzione, request.auth, dati.motivo)
    except ValidationError as errore:
        raise HttpError(400, " ".join(errore.messages)) from errore
    return _correzione_out(correzione) | {"persona": correzione.persona}
