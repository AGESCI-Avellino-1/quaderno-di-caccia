from datetime import date, datetime

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router, Schema
from ninja.errors import HttpError

from apps.organizzazione.models import Incarico, RuoloIncarico, Squadriglia
from apps.permessi import policy
from apps.permessi.policy import LivelloAccesso

from . import servizi
from .models import (
    CAMPI_BUONASTRADA,
    ETICHETTE_CAMPI,
    STATI_APERTI,
    Appartenenza,
    AppartenenzaSquadriglia,
    CorrezioneAnagrafica,
    Persona,
    StatoCorrezione,
    VisibilitaGenitori,
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
    # Joined from the app, not yet in BuonaStrada.
    codice_provvisorio: bool = False
    # Joined from the app and the deadline to complete passed (shown to the capi).
    iscrizione_sospesa: bool = False
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
    }
    scheda = policy.puo_vedere_scheda(request.auth, persona)
    if scheda or livello == LivelloAccesso.SQUADRIGLIA:
        attive = Appartenenza.objects.attive().filter(persona=persona)
        dati["unita"] = [str(a.unita) for a in attive]
    if scheda:
        dati |= {
            "data_nascita": persona.data_nascita,
            "codice_socio": persona.codice_socio,
            "codice_provvisorio": servizi.e_codice_provvisorio(persona.codice_socio),
            "iscrizione_sospesa": persona.iscrizioni.filter(stato="SOSPESA").exists(),
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


# --- Phones within the patrol (DEC-13, DEC-115) ---------------------------------


class TelefonoMembro(Schema):
    id: int
    nome: str
    cognome: str
    incarico: str | None  # "Capo squadriglia", "Vice capo squadriglia"
    telefono: str | None
    # Name of the parent whose number it is, when the child has none of their own.
    del_genitore: str | None


class TelefonoGenitore(Schema):
    figlio_id: int
    nome: str
    cognome: str
    telefono: str


class MiaSquadriglia(Schema):
    id: int
    nome: str
    reparto: str
    sono_capo: bool
    membri: list[TelefonoMembro]
    genitori: list[TelefonoGenitore]  # for the CSQ only


class ImpostazioneTelefono(Schema):
    in_squadriglia: bool
    proprio: str  # the person's own mobile from BuonaStrada, "" if none: it wins
    genitore_id: int | None  # parent chosen for this child
    famiglia_id: int | None  # parent chosen for all the children without a phone
    nascosto: bool
    genitori: list[Scelta]  # valore = parent id, etichetta = "Mario Rossi (333…)"


class NuovaImpostazioneTelefono(Schema):
    genitore_id: int | None = None
    per_tutti_i_figli: bool = False
    nascosto: bool = False


def _membri(squadriglia: Squadriglia, capo: bool) -> tuple[list[dict], list[dict]]:
    oggi = date.today()
    persone = [
        a.persona
        for a in AppartenenzaSquadriglia.objects.attive(oggi)
        .filter(squadriglia=squadriglia)
        .select_related("persona__telefono_squadriglia_da")
        .order_by("persona__cognome", "persona__nome")
    ]
    incarichi = dict(
        Incarico.objects.attivi()
        .filter(squadriglia=squadriglia, ruolo__in=[RuoloIncarico.CSQ, RuoloIncarico.VCSQ])
        .values_list("persona_id", "ruolo")
    )
    membri, genitori = [], []
    for p in persone:
        numero, genitore = servizi.telefono_in_squadriglia(p)
        visibile = capo or not p.telefono_squadriglia_nascosto
        ruolo = incarichi.get(p.pk)
        membri.append(
            {
                "id": p.pk,
                "nome": p.nome,
                "cognome": p.cognome,
                "incarico": RuoloIncarico(ruolo).label if ruolo else None,
                "telefono": (numero or None) if visibile else None,
                "del_genitore": genitore.nome if genitore and visibile and numero else None,
            }
        )
        if capo:
            genitori += [
                {"figlio_id": p.pk, "nome": g.nome, "cognome": g.cognome, "telefono": g.cellulare}
                for g in servizi.genitori_con_telefono(p).order_by("cognome", "nome")
            ]
    return membri, genitori


@router.get("/mia-squadriglia", response=list[MiaSquadriglia])
def mie_squadriglie(request):
    """Phones of the patrol for its members: each member sees the others' phone, the
    CSQ also the parents' (DEC-13, DEC-115). Phones only, no email."""
    guidate = set(policy.squadriglie_guidate(request.auth).values_list("pk", flat=True))
    risultato = []
    for sq in policy.squadriglie_di(request.auth).select_related("unita").order_by("nome"):
        capo = sq.pk in guidate
        membri, genitori = _membri(sq, capo)
        risultato.append(
            {
                "id": sq.pk,
                "nome": sq.nome,
                "reparto": sq.unita.nome,
                "sono_capo": capo,
                "membri": membri,
                "genitori": genitori,
            }
        )
    return risultato


def _impostazione(persona: Persona) -> dict:
    return {
        "in_squadriglia": AppartenenzaSquadriglia.objects.attive().filter(persona=persona).exists(),
        "proprio": persona.cellulare,
        "genitore_id": persona.telefono_squadriglia_da_id,
        "famiglia_id": getattr(servizi.telefono_di_famiglia(persona), "pk", None),
        "nascosto": persona.telefono_squadriglia_nascosto,
        "genitori": [
            {"valore": str(g.pk), "etichetta": f"{g.nome} {g.cognome} ({g.cellulare})"}
            for g in servizi.genitori_con_telefono(persona).order_by("cognome", "nome")
        ],
    }


def _persona_per_telefono(request, persona_id: int) -> Persona:
    persona = get_object_or_404(Persona, pk=persona_id)
    if not policy.puo_impostare_telefono_squadriglia(request.auth, persona):
        raise HttpError(404, "Persona non trovata.")
    return persona


@router.get("/persone/{persona_id}/telefono-squadriglia", response=ImpostazioneTelefono)
def telefono_squadriglia(request, persona_id: int):
    return _impostazione(_persona_per_telefono(request, persona_id))


@router.put("/persone/{persona_id}/telefono-squadriglia", response=ImpostazioneTelefono)
def imposta_telefono_squadriglia(request, persona_id: int, dati: NuovaImpostazioneTelefono):
    persona = _persona_per_telefono(request, persona_id)
    genitore = Persona.objects.filter(pk=dati.genitore_id).first() if dati.genitore_id else None
    try:
        servizi.imposta_telefono_squadriglia(
            persona, genitore, dati.nascosto, per_tutti_i_figli=dati.per_tutti_i_figli
        )
    except ValidationError as errore:
        raise HttpError(400, " ".join(errore.messages)) from errore
    return _impostazione(persona)


# --- What the parents of an adult see (DEC-26) ----------------------------------------


class VisibilitaGenitoriIO(Schema):
    contatti: bool = True
    sanitarie: bool = True
    scheda: bool = True
    quote: bool = True


class VisibilitaGenitoriOut(VisibilitaGenitoriIO):
    decisa_il: datetime | None
    genitori: list[str]  # names of the parents concerned


def _visibilita(persona: Persona) -> dict:
    scelta = VisibilitaGenitori.objects.filter(persona=persona).first()
    genitori = Persona.objects.filter(
        tutele__minore=persona, tutele__responsabilita_genitoriale=True
    ).order_by("cognome", "nome")
    return {
        "contatti": scelta.contatti if scelta else True,
        "sanitarie": scelta.sanitarie if scelta else True,
        "scheda": scelta.scheda if scelta else True,
        "quote": scelta.quote if scelta else True,
        "decisa_il": scelta.decisa_il if scelta else None,
        "genitori": [f"{g.nome} {g.cognome}" for g in genitori],
    }


def _persona_adulta(request, persona_id: int) -> Persona:
    persona = get_object_or_404(Persona, pk=persona_id)
    if not policy.puo_scegliere_visibilita_genitori(request.auth, persona):
        raise HttpError(404, "Persona non trovata.")
    return persona


@router.get("/persone/{persona_id}/visibilita-genitori", response=VisibilitaGenitoriOut)
def visibilita_genitori(request, persona_id: int):
    return _visibilita(_persona_adulta(request, persona_id))


@router.put("/persone/{persona_id}/visibilita-genitori", response=VisibilitaGenitoriOut)
def scegli_visibilita_genitori(request, persona_id: int, dati: VisibilitaGenitoriIO):
    persona = _persona_adulta(request, persona_id)
    VisibilitaGenitori.objects.update_or_create(
        persona=persona,
        defaults={
            "contatti": dati.contatti,
            "sanitarie": dati.sanitarie,
            "scheda": dati.scheda,
            "quote": dati.quote,
            "decisa_il": timezone.now(),
        },
    )
    return _visibilita(persona)
