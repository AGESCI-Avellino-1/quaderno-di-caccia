from datetime import date, datetime

from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import File, Router, Schema, Status, UploadedFile
from ninja.errors import HttpError

from apps.organizzazione.models import Incarico, RuoloIncarico, Squadriglia
from apps.permessi import policy
from apps.permessi.policy import LivelloAccesso

from . import servizi
from .models import (
    CAMPI_BUONASTRADA,
    CAMPI_CONSENSO,
    ETICHETTE_CAMPI,
    PROFESSIONI,
    STATI_APERTI,
    Appartenenza,
    AppartenenzaSquadriglia,
    CorrezioneAnagrafica,
    FotoProfilo,
    Persona,
    RelazioneTutela,
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
    # The person and the Co.Ca. only (DEC-296).
    professione: str | None = None
    indirizzo: str | None = None
    comune: str | None = None
    consenso_foto: bool | None = None
    unita: list[str] = []
    # Profile photo (DEC-42, DEC-201): whether there is one the caller may see.
    foto: bool = False
    puo_caricare_foto: bool = False
    # A parent who becomes a capo: a capogruppo starts the joining (DEC-282).
    puo_iscrivere_in_coca: bool = False
    # The capi see the earlier photos (DEC-42) and who read the sensitive data (DEC-101).
    vede_storico_foto: bool = False
    vede_registro_accessi: bool = False
    # The capi's file (DEC-47, DEC-206), when the person has been a capo.
    fascicolo_capo: bool = False


@router.get("/persone", response=list[PersonaElenco])
def elenco_persone(request, unita: int | None = None, tipo: str | None = None):
    """The people the caller sees. `tipo`: "soci" (members, capi and ragazzi, provisional
    codes included) or "genitori" (who holds parental responsibility for someone); with
    `unita`, the unit's members or their parents. A capo who is also a parent is in both."""
    persone = policy.persone_visibili(request.auth)
    membri = Appartenenza.objects.attive()
    if unita is not None:
        membri = membri.filter(unita_id=unita)
    if tipo == "genitori":
        tutori = RelazioneTutela.objects.all()
        if unita is not None:
            tutori = tutori.filter(minore_id__in=membri.values("persona_id"))
        persone = persone.filter(pk__in=tutori.values("tutore_id"))
    else:
        if unita is not None:
            persone = persone.filter(pk__in=membri.values("persona_id"))
        if tipo == "soci":
            persone = persone.exclude(codice_socio__isnull=True).exclude(codice_socio="")
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
    if policy.vede_professione(request.auth, persona):
        dati["professione"] = persona.professione
    dati["foto"] = policy.puo_vedere_foto(request.auth, persona) and persona.foto_profilo.exists()
    dati["puo_caricare_foto"] = policy.puo_caricare_foto(request.auth, persona)
    dati["puo_iscrivere_in_coca"] = policy.puo_iscrivere_genitore_in_coca(request.auth, persona)
    dati["vede_storico_foto"] = policy.vede_storico_foto(request.auth, persona)
    dati["vede_registro_accessi"] = policy.puo_vedere_registro_accessi(request.auth)
    dati["fascicolo_capo"] = policy.puo_vedere_fascicolo_capo(request.auth, persona)
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


def _tipo(campo: str, valore: str = "") -> tuple[str, list[dict]]:
    if campo == "professione":
        # BuonaStrada's list, plus the value it has now if BuonaStrada added one.
        professioni = [*PROFESSIONI, *([valore] if valore and valore not in PROFESSIONI else [])]
        return "scelta", [{"valore": p, "etichetta": p.capitalize()} for p in professioni]
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
        tipo, scelte = _tipo(campo, servizi.come_testo(getattr(persona, campo)))
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
    if dati.campo in CAMPI_CONSENSO and getattr(request, "impersonatore", None):
        raise HttpError(403, "I consensi li dà solo la persona, non chi usa l'app al suo posto.")
    nuova = dati.valore.strip()
    if dati.campo == "professione" and nuova not in (*PROFESSIONI, "", persona.professione):
        raise HttpError(400, "Scegli la professione tra quelle di BuonaStrada.")
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
    # The caller may open their file: the avatar is a link (DEC-314).
    scheda: bool = False

    @staticmethod
    def resolve_scheda(obj, context) -> bool:
        return policy.scheda_apribile(context["request"], obj["id"])


class TelefonoGenitore(Schema):
    figlio_id: int
    # The parent, to choose them for the phone's contacts (DEC-302).
    id: int
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
                {
                    "figlio_id": p.pk,
                    "id": g.pk,
                    "nome": g.nome,
                    "cognome": g.cognome,
                    "telefono": g.cellulare,
                }
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


# --- Optional emails (GDPR art. 21; DEC-157) ----------------------------------------


class PreferenzeEmailIO(Schema):
    eventi: bool = True
    promemoria_quote: bool = True
    maggiore_eta: bool = True
    riepiloghi: bool = True
    avvisi: bool = True


def _mia_persona(request) -> Persona:
    persona = policy.persona_di(request.auth)
    if persona is None:
        raise HttpError(404, "Il tuo account non è ancora collegato a una persona del gruppo.")
    return persona


@router.get("/io/email", response=PreferenzeEmailIO)
def mie_preferenze_email(request):
    from .models import PreferenzeEmail

    preferenze = PreferenzeEmail.objects.filter(persona=_mia_persona(request)).first()
    return preferenze or PreferenzeEmailIO()


@router.put("/io/email", response=PreferenzeEmailIO)
def scegli_preferenze_email(request, dati: PreferenzeEmailIO):
    from .models import PreferenzeEmail

    preferenze, _ = PreferenzeEmail.objects.update_or_create(
        persona=_mia_persona(request), defaults=dati.dict()
    )
    return preferenze


# --- Phone numbers into the phone's contacts (DEC-302) ----------------------------------


@router.get("/rubrica")
def rubrica(request, persone: str):
    """A vCard file with the chosen people, for the capi and the CSQ: only numbers they
    already see, name and numbers only. Not in the access log (DEC-302)."""
    user = request.auth
    if not policy.puo_usare_rubrica(user):
        raise HttpError(403, "Solo i capi e i capi squadriglia aggiungono numeri alla rubrica.")
    try:
        scelte = {int(x) for x in persone.split(",") if x.strip()}
    except ValueError:
        raise HttpError(400, "Scelta delle persone non valida.") from None
    contatti: dict[int, tuple[Persona, list[tuple[str, str, str]]]] = {}

    def aggiungi(persona: Persona, numero: str, tipo: str = "CELL", nota: str = ""):
        if numero and persona.pk in scelte:
            voce = contatti.setdefault(persona.pk, (persona, []))
            if numero not in [n for n, _, _ in voce[1]]:
                voce[1].append((numero, tipo, nota))

    if policy.e_capo(user):
        for p in Persona.objects.filter(pk__in=scelte).order_by("cognome", "nome"):
            if policy.puo_vedere_dati_sensibili(user, p):
                aggiungi(p, p.cellulare)
                aggiungi(p, p.telefono_fisso, "VOICE")
    membri, genitori = policy.rubrica_squadriglia(user)
    for p in membri.order_by("cognome", "nome"):
        numero, genitore = servizi.telefono_in_squadriglia(p)
        aggiungi(p, numero, nota=f"numero di {genitore.nome} (genitore)" if genitore else "")
    for g in genitori.exclude(cellulare="").order_by("cognome", "nome"):
        aggiungi(g, g.cellulare)
    if not contatti:
        raise HttpError(404, "Nessun numero di telefono tra le persone scelte.")
    risposta = HttpResponse(
        servizi.vcard(list(contatti.values())), content_type="text/vcard; charset=utf-8"
    )
    risposta["Content-Disposition"] = 'attachment; filename="contatti.vcf"'
    risposta["Cache-Control"] = "no-store"
    return risposta


# --- Profile photo (DEC-42, DEC-201) --------------------------------------------------------


def _foto_visibile(request, persona_id: int) -> Persona:
    persona = get_object_or_404(Persona, pk=persona_id)
    if not policy.puo_vedere_foto(request.auth, persona):
        raise HttpError(404, "Foto non trovata.")
    return persona


@router.get("/persone/{persona_id}/foto")
def foto(request, persona_id: int, foto_id: int | None = None):
    """The current photo; an earlier one by its id, for the capi."""
    persona = _foto_visibile(request, persona_id)
    tutte = persona.foto_profilo.all()
    if foto_id is not None:
        if not policy.vede_storico_foto(request.auth, persona):
            raise HttpError(404, "Foto non trovata.")
        scelta = tutte.filter(pk=foto_id).first()
    else:
        scelta = tutte.first()
    if scelta is None:
        raise HttpError(404, "Nessuna foto.")
    risposta = HttpResponse(scelta.file.read(), content_type="image/jpeg")
    risposta["Cache-Control"] = "private, no-store"
    return risposta


class FotoStorico(Schema):
    id: int
    creata_il: datetime


@router.get("/persone/{persona_id}/foto/storico", response=list[FotoStorico])
def storico_foto(request, persona_id: int):
    persona = _foto_visibile(request, persona_id)
    if not policy.vede_storico_foto(request.auth, persona):
        raise HttpError(403, "Le foto precedenti le vedono i capi.")
    return [{"id": f.pk, "creata_il": f.creato_il} for f in persona.foto_profilo.all()]


@router.post("/persone/{persona_id}/foto", response={201: PersonaDettaglio})
def carica_foto(request, persona_id: int, file: File[UploadedFile]):
    """A new photo: the earlier ones stay in the history (DEC-42)."""
    import uuid

    from django.core.files.base import ContentFile

    from apps.buonacaccia.servizi import prepara_foto

    persona = get_object_or_404(Persona, pk=persona_id)
    if not policy.puo_caricare_foto(request.auth, persona):
        raise HttpError(403, "La foto la caricano i genitori, il maggiorenne o lo staff.")
    try:
        jpeg = prepara_foto(file)
    except ValidationError as errore:
        raise HttpError(400, " ".join(errore.messages)) from errore
    nuova = FotoProfilo(persona=persona, caricata_da=request.auth)
    nuova.file.save(f"{uuid.uuid4().hex}.jpg", ContentFile(jpeg), save=True)
    return Status(201, dettaglio_persona(request, persona_id))


# --- Scout path (DEC-287) ---------------------------------------------------------------


class PeriodoPercorsoOut(Schema):
    id: int | None
    gruppo: str
    altro_gruppo: bool
    unita: str
    ruolo: str
    ruolo_nome: str
    anni: str
    ricostruito: bool
    rimovibile: bool


class PercorsoOut(Schema):
    anno_ingresso: str
    periodi: list[PeriodoPercorsoOut]
    puo_modificare: bool


class PeriodoPercorsoIn(Schema):
    # Empty: this group.
    gruppo: str = ""
    unita: str
    ruolo: str
    anno_inizio: int
    anno_fine: int


def _percorso(request, persona: Persona) -> dict:
    from .percorso import percorso

    return percorso(persona) | {
        "puo_modificare": policy.puo_modificare_percorso(request.auth, persona)
    }


@router.get("/persone/{persona_id}/percorso", response=PercorsoOut)
def percorso_scout(request, persona_id: int):
    persona = get_object_or_404(Persona, pk=persona_id)
    if not policy.vede_percorso(request.auth, persona):
        raise HttpError(404, "Persona non trovata.")
    return _percorso(request, persona)


@router.post("/persone/{persona_id}/percorso", response={201: PercorsoOut})
def aggiungi_periodo_percorso(request, persona_id: int, dati: PeriodoPercorsoIn):
    from apps.core.models import FonteDato

    from .models import PeriodoPercorso, RuoloAppartenenza

    persona = get_object_or_404(Persona, pk=persona_id)
    if not policy.vede_percorso(request.auth, persona):
        raise HttpError(404, "Persona non trovata.")
    if not policy.puo_modificare_percorso(request.auth, persona):
        raise HttpError(403, "Il percorso lo completano il capo stesso o i capigruppo.")
    if dati.ruolo not in RuoloAppartenenza.values:
        raise HttpError(400, "Indica se era ragazzo o capo.")
    periodo = PeriodoPercorso(
        persona=persona,
        gruppo=dati.gruppo.strip()[:160],
        unita=dati.unita.strip()[:160],
        ruolo=dati.ruolo,
        anno_inizio=dati.anno_inizio,
        anno_fine=dati.anno_fine,
        fonte=FonteDato.RICOSTRUITO,
        registrato_da=request.auth,
    )
    try:
        periodo.full_clean()
    except ValidationError as errore:
        raise HttpError(400, " ".join(errore.messages)) from errore
    periodo.save()
    return Status(201, _percorso(request, persona))


@router.delete("/percorso/{periodo_id}", response=PercorsoOut)
def togli_periodo_percorso(request, periodo_id: int):
    from apps.core.models import FonteDato

    from .models import PeriodoPercorso

    periodo = get_object_or_404(PeriodoPercorso, pk=periodo_id)
    persona = periodo.persona
    if not policy.vede_percorso(request.auth, persona):
        raise HttpError(404, "Periodo non trovato.")
    if not policy.puo_modificare_percorso(request.auth, persona):
        raise HttpError(403, "Il percorso lo completano il capo stesso o i capigruppo.")
    if periodo.fonte != FonteDato.RICOSTRUITO:
        raise HttpError(400, "Si tolgono solo i periodi aggiunti a mano.")
    periodo.delete()
    return _percorso(request, persona)
