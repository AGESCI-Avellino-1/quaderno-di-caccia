from datetime import date

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import File, Router, Schema, Status, UploadedFile
from ninja.errors import HttpError

from apps.anagrafica.models import (
    Appartenenza,
    AppartenenzaSquadriglia,
    DerogaSquadriglia,
    Persona,
    RuoloAppartenenza,
)
from apps.core.anno import compie_anni
from apps.permessi import policy
from apps.permessi.models import Azione, Categoria, registra_accessi

from .models import (
    INCARICHI_DI_SERVIZIO,
    RUOLI_DI_GRUPPO,
    RUOLI_DI_SQUADRIGLIA,
    RUOLI_DI_UNITA,
    SERVIZIO_IN_UNITA,
    Ambiente,
    Composizione,
    Gruppo,
    Incarico,
    RuoloIncarico,
    Squadriglia,
    TipoUnita,
    Unita,
)

router = Router(tags=["organizzazione"])


def _salva(oggetto) -> None:
    try:
        oggetto.full_clean()
    except ValidationError as errore:
        raise HttpError(400, " ".join(errore.messages)) from errore
    oggetto.save()


def _gruppo() -> Gruppo:
    gruppo = Gruppo.objects.first()  # one installation per group (DEC-107)
    if gruppo is None:
        raise HttpError(409, "Il gruppo non esiste ancora: importa prima l'export di BuonaStrada.")
    return gruppo


# --- Units (DEC-10, DEC-36) ----------------------------------------------------------------


class UnitaOut(Schema):
    id: int
    nome: str
    codice: str  # BuonaStrada code (O1, G1…), "" for units created in the app
    senza_nome: bool
    tipo: str
    branca: str
    composizione: str
    ambiente: str
    attiva: bool
    collegata_a: int | None
    nota_collegamento: str

    @staticmethod
    def resolve_branca(obj: Unita) -> str:
        return obj.branca.value

    @staticmethod
    def resolve_collegata_a(obj: Unita) -> int | None:
        return obj.collegata_a_id


class UnitaIn(Schema):
    nome: str
    tipo: TipoUnita
    composizione: Composizione
    ambiente: Ambiente = Ambiente.NESSUNO
    # Parallel male/female units are linked by a note (DEC-36).
    collegata_a: int | None = None
    nota_collegamento: str = ""
    attiva: bool = True


@router.get("/unita", response=list[UnitaOut])
def elenco_unita(request, tutte: bool = False):
    """Units of the group: visible to any capo (DEC-09). `tutte` adds closed ones."""
    if not policy.puo_vedere_organizzazione(request.auth):
        raise HttpError(403, "Riservato ai capi.")
    unita = Unita.objects.all() if tutte else Unita.objects.filter(attiva=True)
    return unita.order_by("tipo", "nome")


def _applica_unita(unita: Unita, dati: UnitaIn) -> Unita:
    if dati.collegata_a is not None:
        if dati.collegata_a == unita.pk:
            raise HttpError(400, "Un'unità non può essere collegata a sé stessa.")
        unita.collegata_a = get_object_or_404(Unita, pk=dati.collegata_a, gruppo=unita.gruppo)
    else:
        unita.collegata_a = None
    unita.nome = dati.nome.strip()
    unita.tipo = dati.tipo
    unita.composizione = dati.composizione
    unita.ambiente = dati.ambiente
    unita.nota_collegamento = dati.nota_collegamento.strip()
    unita.attiva = dati.attiva
    _salva(unita)
    return unita


@router.post("/unita", response={201: UnitaOut})
def crea_unita(request, dati: UnitaIn):
    if not policy.puo_gestire_unita(request.auth):
        raise HttpError(403, "Solo i capigruppo creano le unità.")
    return Status(201, _applica_unita(Unita(gruppo=_gruppo()), dati))


@router.put("/unita/{unita_id}", response=UnitaOut)
def modifica_unita(request, unita_id: int, dati: UnitaIn):
    """BuonaStrada codes (unit code, progressive) are not editable here: the import
    matches units through them."""
    if not policy.puo_gestire_unita(request.auth):
        raise HttpError(403, "Solo i capigruppo modificano le unità.")
    return _applica_unita(get_object_or_404(Unita, pk=unita_id), dati)


# --- Roles (DEC-11, DEC-14, DEC-18) --------------------------------------------------------


class PersonaBreve(Schema):
    id: int
    nome: str
    cognome: str


class IncaricoOut(Schema):
    id: int
    ruolo: str
    ruolo_nome: str
    persona: PersonaBreve
    data_inizio: date
    data_fine: date | None

    @staticmethod
    def resolve_ruolo_nome(obj: Incarico) -> str:
        return obj.get_ruolo_display()


class Scelta(Schema):
    valore: str
    etichetta: str


def _nomina(user, ruoli, **dove) -> list[dict]:
    """The roles among `ruoli` the user may assign (and close) there."""
    return [
        {"valore": r.value, "etichetta": r.label}
        for r in ruoli
        if policy.puo_nominare(user, r, **dove)
    ]


class MembroOut(Schema):
    """An active patrol membership (DEC-65)."""

    id: int
    persona: PersonaBreve
    data_inizio: date


class SquadrigliaOut(Schema):
    id: int
    nome: str
    sesso: str
    attiva: bool
    membri: list[MembroOut]
    incarichi: list[IncaricoOut]
    # Roles the caller may assign in this patrol.
    nomina: list[Scelta]


class UnitaDettaglio(Schema):
    unita: UnitaOut
    incarichi: list[IncaricoOut]
    squadriglie: list[SquadrigliaOut]
    # Ragazzi of a reparto who are in no patrol today.
    senza_squadriglia: list[PersonaBreve]
    # Patrol members the single-sex check cannot vouch for.
    avvisi: list[str]
    puo_modificare: bool
    puo_gestire_squadriglie: bool
    # Unit roles the caller may assign (and close).
    nomina: list[Scelta]


def _avvisi_maggiore_eta(unita: Unita) -> list[str]:
    """Members turning 18 within a month, or since a month, without an account: at 18
    they choose what their parents see, so the capi should invite them (DEC-26)."""
    oggi = date.today()
    avvisi = []
    for a in (
        Appartenenza.objects.attive()
        .filter(unita=unita, ruolo=RuoloAppartenenza.RAGAZZO, persona__utente__isnull=True)
        .exclude(persona__data_nascita__isnull=True)
        .select_related("persona")
        .order_by("persona__cognome", "persona__nome")
    ):
        giorno = compie_anni(a.persona.data_nascita, 18)
        if abs((giorno - oggi).days) <= 30:
            verbo = "ha compiuto" if giorno <= oggi else "compie"
            avvisi.append(
                f"{a.persona} {verbo} 18 anni il {giorno.strftime('%d/%m/%Y')} e non ha un "
                "account: invitalo, così sceglie cosa possono vedere i genitori."
            )
    return avvisi


def _avvisi_squadriglie(unita: Unita) -> list[str]:
    """Check the composition against single-sex patrols: members without a sex in
    BuonaStrada, and members of the other sex without a valid Co.Ca. exception (e.g.
    the exception was revoked, or the sex was corrected after the import)."""
    avvisi = []
    membri = (
        AppartenenzaSquadriglia.objects.attive()
        .filter(squadriglia__unita=unita, squadriglia__attiva=True)
        .select_related("persona", "squadriglia")
        .order_by("persona__cognome", "persona__nome")
    )
    deroghe = set(
        DerogaSquadriglia.objects.valide()
        .filter(reparto=unita)
        .values_list("persona_id", "sesso_squadriglia")
    )
    for m in membri:
        persona, squadriglia = m.persona, m.squadriglia
        if not persona.sesso:
            avvisi.append(
                f"{persona}: il sesso non è indicato in BuonaStrada, la squadriglia non si "
                "può controllare."
            )
        elif persona.sesso != squadriglia.sesso and (persona.pk, squadriglia.sesso) not in deroghe:
            avvisi.append(
                f"{persona} è in {squadriglia} ({squadriglia.get_sesso_display().lower()}) "
                "senza un'eccezione valida della Co.Ca."
            )
    return avvisi


def _incarichi(**filtri):
    return (
        Incarico.objects.attivi()
        .filter(**filtri)
        .select_related("persona")
        .order_by("ruolo", "persona__cognome", "persona__nome")
    )


@router.get("/unita/{unita_id}", response=UnitaDettaglio)
def dettaglio_unita(request, unita_id: int):
    """Staff, roles and patrols of a unit (DEC-09: any capo reads them)."""
    if not policy.puo_vedere_organizzazione(request.auth):
        raise HttpError(403, "Riservato ai capi.")
    unita = get_object_or_404(Unita, pk=unita_id)
    utente = request.auth
    squadriglie = [
        {
            "id": s.pk,
            "nome": s.nome,
            "sesso": s.sesso,
            "attiva": s.attiva,
            "membri": list(
                AppartenenzaSquadriglia.objects.attive()
                .filter(squadriglia=s)
                .select_related("persona")
                .order_by("persona__cognome", "persona__nome")
            ),
            "incarichi": list(_incarichi(squadriglia=s)),
            "nomina": _nomina(utente, (RuoloIncarico.CSQ, RuoloIncarico.VCSQ), squadriglia=s),
        }
        for s in unita.squadriglie.order_by("-attiva", "nome")
    ]
    senza_squadriglia = Persona.objects.none()
    if unita.tipo == TipoUnita.REPARTO:
        ragazzi = Appartenenza.objects.attive().filter(unita=unita, ruolo=RuoloAppartenenza.RAGAZZO)
        in_squadriglia = AppartenenzaSquadriglia.objects.attive().values("persona_id")
        senza_squadriglia = (
            Persona.objects.filter(pk__in=ragazzi.values("persona_id"))
            .exclude(pk__in=in_squadriglia)
            .order_by("cognome", "nome")
        )
    return {
        "unita": unita,
        "incarichi": list(_incarichi(unita=unita)),
        "squadriglie": squadriglie,
        "senza_squadriglia": list(senza_squadriglia),
        "avvisi": (
            ["L'unità non ha ancora un nome: daglielo con «Modifica»."] if unita.senza_nome else []
        )
        + (
            [
                "Manca l'ambientazione (giungla per un branco, bosco per un cerchio): "
                "sceglila con «Modifica»."
            ]
            if unita.senza_ambiente
            else []
        )
        + (_avvisi_squadriglie(unita) if unita.tipo == TipoUnita.REPARTO else [])
        + _avvisi_maggiore_eta(unita),
        "puo_modificare": policy.puo_gestire_unita(utente),
        "puo_gestire_squadriglie": unita.tipo == TipoUnita.REPARTO
        and policy.puo_gestire_squadriglie(utente, unita),
        "nomina": _nomina(
            utente,
            (
                RuoloIncarico.CAPO_UNITA,
                RuoloIncarico.STAFF,
                RuoloIncarico.TESORIERE_UNITA,
                RuoloIncarico.CONSIGLIO_ANZIANI,
            ),
            unita=unita,
        ),
    }


class IncarichiGruppo(Schema):
    # Additional group roles: capigruppo, group treasurers, technical administrators.
    incarichi: list[IncaricoOut]
    nomina: list[Scelta]
    # Capi of the Co.Ca. serving in no unit for now.
    a_disposizione: list[IncaricoOut]
    nomina_a_disposizione: list[Scelta]
    # For the capigruppo: capi with no service at all, to sort out.
    senza_servizio: list[PersonaBreve]


RUOLI_AGGIUNTIVI_DI_GRUPPO = (
    RuoloIncarico.CAPOGRUPPO,
    RuoloIncarico.TESORIERE_GRUPPO,
    RuoloIncarico.AMMINISTRATORE,
)


def capi_senza_servizio():
    """Active capi with neither a unit nor "a disposizione" (DEC-165)."""
    capi = Appartenenza.objects.attive().filter(ruolo=RuoloAppartenenza.CAPO)
    in_servizio = Incarico.objects.attivi().filter(ruolo__in=INCARICHI_DI_SERVIZIO)
    return (
        Persona.objects.filter(pk__in=capi.values("persona_id"))
        .exclude(pk__in=in_servizio.values("persona_id"))
        .order_by("cognome", "nome")
    )


@router.get("/gruppo/incarichi", response=IncarichiGruppo)
def incarichi_di_gruppo(request):
    if not policy.puo_vedere_incarichi_di_gruppo(request.auth):
        raise HttpError(403, "Riservato ai capi.")
    return {
        "incarichi": list(_incarichi(ruolo__in=RUOLI_AGGIUNTIVI_DI_GRUPPO)),
        "nomina": _nomina(request.auth, RUOLI_AGGIUNTIVI_DI_GRUPPO),
        "a_disposizione": list(_incarichi(ruolo=RuoloIncarico.A_DISPOSIZIONE)),
        "nomina_a_disposizione": _nomina(request.auth, (RuoloIncarico.A_DISPOSIZIONE,)),
        "senza_servizio": (
            list(capi_senza_servizio()) if policy.e_capogruppo(request.auth) else []
        ),
    }


@router.get("/capi", response=list[PersonaBreve])
def elenco_capi(request):
    """Active capi: who can be appointed to staff and group roles."""
    if not policy.puo_vedere_incarichi_di_gruppo(request.auth):
        raise HttpError(403, "Riservato ai capi.")
    capi = Appartenenza.objects.attive().filter(ruolo=RuoloAppartenenza.CAPO)
    return Persona.objects.filter(pk__in=capi.values("persona_id")).order_by("cognome", "nome")


class NuovoIncarico(Schema):
    persona_id: int
    ruolo: RuoloIncarico
    unita_id: int | None = None
    squadriglia_id: int | None = None
    data_inizio: date | None = None


@router.post("/incarichi", response={201: IncaricoOut})
def crea_incarico(request, dati: NuovoIncarico):
    incarico = Incarico(
        persona=get_object_or_404(Persona, pk=dati.persona_id),
        ruolo=dati.ruolo,
        data_inizio=dati.data_inizio or timezone.localdate(),
    )
    if dati.ruolo in RUOLI_DI_GRUPPO:
        incarico.gruppo = _gruppo()
    elif dati.ruolo in RUOLI_DI_UNITA:
        incarico.unita = get_object_or_404(Unita, pk=dati.unita_id or 0)
    elif dati.ruolo in RUOLI_DI_SQUADRIGLIA:
        incarico.squadriglia = get_object_or_404(
            Squadriglia.objects.select_related("unita"), pk=dati.squadriglia_id or 0
        )
    if not policy.puo_nominare(
        request.auth, dati.ruolo, unita=incarico.unita, squadriglia=incarico.squadriglia
    ):
        raise HttpError(403, "Non puoi assegnare questo incarico.")
    with transaction.atomic():
        if dati.ruolo in SERVIZIO_IN_UNITA:
            # Back in a unit: "a disposizione" ends by itself.
            _chiudi_a_disposizione(incarico.persona, incarico.data_inizio)
        _salva(incarico)
    return Status(201, incarico)


def _chiudi_a_disposizione(persona: Persona, giorno: date) -> None:
    for incarico in Incarico.objects.filter(
        persona=persona, ruolo=RuoloIncarico.A_DISPOSIZIONE, data_inizio__lte=giorno
    ).filter(Q(data_fine__isnull=True) | Q(data_fine__gt=giorno)):
        if incarico.data_inizio == giorno:
            incarico.delete()  # started the same day: never really in effect
        else:
            incarico.data_fine = giorno
            incarico.save(update_fields=["data_fine", "aggiornato_il"])


class ChiusuraIncarico(Schema):
    # Exclusive like every period end: today = the role is over from today.
    data_fine: date | None = None


class EsitoChiusura(Schema):
    id: int
    # True when the role had not started yet (e.g. a mistake fixed the same day):
    # it is removed instead of closed. The audit log keeps track of it.
    rimosso: bool
    data_fine: date | None


@router.post("/incarichi/{incarico_id}/termina", response=EsitoChiusura)
@transaction.atomic
def termina_incarico(request, incarico_id: int, dati: ChiusuraIncarico):
    incarico = get_object_or_404(
        Incarico.objects.select_related("unita", "squadriglia__unita"), pk=incarico_id
    )
    if not policy.puo_nominare(
        request.auth,
        RuoloIncarico(incarico.ruolo),
        unita=incarico.unita,
        squadriglia=incarico.squadriglia,
    ):
        raise HttpError(403, "Non puoi chiudere questo incarico.")
    if incarico.data_fine is not None and incarico.data_fine <= timezone.localdate():
        raise HttpError(409, "L'incarico è già concluso.")
    fine = dati.data_fine or timezone.localdate()
    if dati.data_fine is None and incarico.data_inizio >= fine:
        incarico.delete()
        return {"id": incarico_id, "rimosso": True, "data_fine": None}
    incarico.data_fine = fine
    _salva(incarico)
    return {"id": incarico.pk, "rimosso": False, "data_fine": incarico.data_fine}


# --- Patrols (Squadriglie) -----------------------------------------------------------------


class SquadrigliaIn(Schema):
    nome: str
    sesso: str
    attiva: bool = True


class SquadrigliaBreve(Schema):
    id: int
    nome: str
    sesso: str
    attiva: bool


def _applica_squadriglia(squadriglia: Squadriglia, dati: SquadrigliaIn) -> Squadriglia:
    squadriglia.nome = dati.nome.strip()
    squadriglia.sesso = dati.sesso
    squadriglia.attiva = dati.attiva
    _salva(squadriglia)
    return squadriglia


@router.post("/unita/{unita_id}/squadriglie", response={201: SquadrigliaBreve})
def crea_squadriglia(request, unita_id: int, dati: SquadrigliaIn):
    unita = get_object_or_404(Unita, pk=unita_id)
    if not policy.puo_gestire_squadriglie(request.auth, unita):
        raise HttpError(403, "Non puoi gestire le squadriglie di questa unità.")
    return Status(201, _applica_squadriglia(Squadriglia(unita=unita), dati))


@router.put("/squadriglie/{squadriglia_id}", response=SquadrigliaBreve)
def modifica_squadriglia(request, squadriglia_id: int, dati: SquadrigliaIn):
    squadriglia = get_object_or_404(Squadriglia.objects.select_related("unita"), pk=squadriglia_id)
    if not policy.puo_gestire_squadriglie(request.auth, squadriglia.unita):
        raise HttpError(403, "Non puoi gestire le squadriglie di questa unità.")
    return _applica_squadriglia(squadriglia, dati)


# --- Patrol members (DEC-30, DEC-65) ------------------------------------------------------
# Composed by the same people who create them (policy.puo_gestire_squadriglie),
# DEC-112.


def _chiudi_periodo(oggetto, fine: date) -> bool:
    """Close a period from `fine` (exclusive). A period starting that same day never
    took effect: it is removed instead (the audit log keeps it). True if removed."""
    if oggetto.data_inizio >= fine:
        oggetto.delete()
        return True
    oggetto.data_fine = fine
    _salva(oggetto)
    return False


def _controlla_incarichi_di_squadriglia(appartenenza: AppartenenzaSquadriglia) -> None:
    if (
        Incarico.objects.attivi()
        .filter(persona=appartenenza.persona_id, squadriglia=appartenenza.squadriglia_id)
        .exists()
    ):
        raise HttpError(
            400,
            f"{appartenenza.persona} è capo o vice capo di {appartenenza.squadriglia}: "
            "chiudi prima l'incarico.",
        )


class NuovoMembro(Schema):
    persona_id: int


@router.post("/squadriglie/{squadriglia_id}/membri", response={201: MembroOut})
@transaction.atomic
def aggiungi_membro(request, squadriglia_id: int, dati: NuovoMembro):
    """Put a ragazzo in a patrol from today; a change of patrol closes the previous
    membership on the same day (DEC-65)."""
    squadriglia = get_object_or_404(Squadriglia.objects.select_related("unita"), pk=squadriglia_id)
    if not policy.puo_gestire_squadriglie(request.auth, squadriglia.unita):
        raise HttpError(403, "Non puoi gestire le squadriglie di questa unità.")
    persona = get_object_or_404(Persona, pk=dati.persona_id)
    oggi = timezone.localdate()
    for precedente in AppartenenzaSquadriglia.objects.attive(oggi).filter(persona=persona):
        if precedente.squadriglia_id == squadriglia.pk:
            raise HttpError(400, f"{persona} è già in {squadriglia}.")
        _controlla_incarichi_di_squadriglia(precedente)
        _chiudi_periodo(precedente, oggi)
    membro = AppartenenzaSquadriglia(persona=persona, squadriglia=squadriglia, data_inizio=oggi)
    _salva(membro)
    return Status(201, membro)


class EsitoUscita(Schema):
    id: int
    rimosso: bool


@router.post("/membri-squadriglia/{appartenenza_id}/termina", response=EsitoUscita)
@transaction.atomic
def togli_membro(request, appartenenza_id: int):
    """Take a ragazzo out of the patrol from today."""
    appartenenza = get_object_or_404(
        AppartenenzaSquadriglia.objects.select_related("squadriglia__unita", "persona"),
        pk=appartenenza_id,
    )
    if not policy.puo_gestire_squadriglie(request.auth, appartenenza.squadriglia.unita):
        raise HttpError(403, "Non puoi gestire le squadriglie di questa unità.")
    oggi = timezone.localdate()
    if appartenenza.data_fine is not None and appartenenza.data_fine <= oggi:
        raise HttpError(409, "Non fa già più parte della squadriglia.")
    _controlla_incarichi_di_squadriglia(appartenenza)
    return {"id": appartenenza_id, "rimosso": _chiudi_periodo(appartenenza, oggi)}


# --- Exceptions to single-sex patrols ------------------------------------------------------
# DEC-132: the Co.Ca. decides, a
# capogruppo records it, only capi see it; valid while the person stays in the reparto.
# Special-category data: every read and change goes to the access log (DEC-101).


class DerogaOut(Schema):
    id: int
    reparto: str
    sesso_squadriglia: str
    # "Femminili" / "Maschili"
    squadriglie_ammesse: str
    data_decisione: date
    motivazione: str
    registrata_da: str | None
    revocata_il: date | None
    valida: bool


class DerogheSquadriglia(Schema):
    deroghe: list[DerogaOut]
    puo_gestire: bool
    # Reparti the person belongs to today: where a new exception can apply.
    reparti: list[Scelta]


def _deroga_out(deroga: DerogaSquadriglia, valide: set[int]) -> dict:
    return {
        "id": deroga.pk,
        "reparto": str(deroga.reparto),
        "sesso_squadriglia": deroga.sesso_squadriglia,
        "squadriglie_ammesse": deroga.get_sesso_squadriglia_display(),
        "data_decisione": deroga.data_decisione,
        "motivazione": deroga.motivazione,
        "registrata_da": deroga.registrata_da.email if deroga.registrata_da else None,
        "revocata_il": deroga.revocata_il,
        "valida": deroga.pk in valide,
    }


def _persona_per_deroghe(request, persona_id: int) -> Persona:
    persona = get_object_or_404(Persona, pk=persona_id)
    if not policy.puo_vedere_deroghe_squadriglia(request.auth):
        raise HttpError(404, "Persona non trovata.")
    return persona


@router.get("/persone/{persona_id}/deroghe-squadriglia", response=DerogheSquadriglia)
def deroghe_squadriglia(request, persona_id: int):
    persona = _persona_per_deroghe(request, persona_id)
    deroghe = list(
        DerogaSquadriglia.objects.filter(persona=persona)
        .select_related("reparto", "registrata_da")
        .order_by("-data_decisione")
    )
    if deroghe:
        # Logged only when there is something to read: opening a person page without
        # exceptions must not fill the log.
        registra_accessi(request, [persona], Categoria.DEROGA_SQ, Azione.LETTURA)
    valide = set(
        DerogaSquadriglia.objects.valide().filter(persona=persona).values_list("pk", flat=True)
    )
    reparti = Unita.objects.filter(
        tipo=TipoUnita.REPARTO,
        pk__in=Appartenenza.objects.attive()
        .filter(persona=persona, ruolo=RuoloAppartenenza.RAGAZZO)
        .values("unita_id"),
    )
    return {
        "deroghe": [_deroga_out(d, valide) for d in deroghe],
        "puo_gestire": policy.puo_gestire_deroghe_squadriglia(request.auth),
        "reparti": [{"valore": str(u.pk), "etichetta": u.nome} for u in reparti],
    }


class NuovaDeroga(Schema):
    reparto_id: int
    sesso_squadriglia: str
    data_decisione: date
    motivazione: str


@router.post("/persone/{persona_id}/deroghe-squadriglia", response={201: DerogaOut})
@transaction.atomic
def registra_deroga(request, persona_id: int, dati: NuovaDeroga):
    persona = _persona_per_deroghe(request, persona_id)
    if not policy.puo_gestire_deroghe_squadriglia(request.auth):
        raise HttpError(403, "L'eccezione decisa dalla Co.Ca. la registra un capogruppo.")
    reparto = get_object_or_404(Unita, pk=dati.reparto_id)
    if (
        not Appartenenza.objects.attive()
        .filter(persona=persona, unita=reparto, ruolo=RuoloAppartenenza.RAGAZZO)
        .exists()
    ):
        raise HttpError(400, f"{persona} non è un ragazzo o una ragazza di {reparto}.")
    deroga = DerogaSquadriglia(
        persona=persona,
        reparto=reparto,
        sesso_squadriglia=dati.sesso_squadriglia,
        data_decisione=dati.data_decisione,
        motivazione=dati.motivazione.strip(),
        registrata_da=request.auth,
    )
    _salva(deroga)
    registra_accessi(request, [persona], Categoria.DEROGA_SQ, Azione.MODIFICA)
    valide = set(
        DerogaSquadriglia.objects.valide().filter(pk=deroga.pk).values_list("pk", flat=True)
    )
    return Status(201, _deroga_out(deroga, valide))


@router.post("/deroghe-squadriglia/{deroga_id}/revoca", response=DerogaOut)
@transaction.atomic
def revoca_deroga(request, deroga_id: int):
    """From today the person can no longer join patrols of the other sex. If they are
    already in one, the unit page reports it: the staff decides where they go."""
    deroga = get_object_or_404(
        DerogaSquadriglia.objects.select_related("persona", "reparto", "registrata_da"),
        pk=deroga_id,
    )
    if not policy.puo_vedere_deroghe_squadriglia(request.auth):
        raise HttpError(404, "Eccezione non trovata.")
    if not policy.puo_gestire_deroghe_squadriglia(request.auth):
        raise HttpError(403, "L'eccezione la revoca un capogruppo.")
    oggi = timezone.localdate()
    if deroga.revocata_il is not None and deroga.revocata_il <= oggi:
        raise HttpError(409, "L'eccezione è già revocata.")
    # A decision dated today ends the same day: never in force, revocata_il = decision.
    deroga.revocata_il = max(oggi, deroga.data_decisione)
    deroga.save(update_fields=["revocata_il", "aggiornato_il"])
    registra_accessi(request, [deroga.persona], Categoria.DEROGA_SQ, Azione.MODIFICA)
    return _deroga_out(deroga, set())


# --- Letterhead of the prints (DEC-192) -----------------------------------------------------


class IntestazioneIO(Schema):
    denominazione_sociale: str = ""
    codice_fiscale: str = ""
    sede_indirizzo: str = ""
    sede_cap: str = ""
    sede_comune: str = ""
    sede_provincia: str = ""
    telefono: str = ""
    cellulare: str = ""
    email: str = ""
    pec: str = ""
    sito: str = ""
    runts_repertorio: str = ""
    runts_data: date | None = None


class IntestazioneOut(IntestazioneIO):
    logo: bool = False
    puo_modificare: bool = False


CAMPI_INTESTAZIONE = [c for c in IntestazioneIO.model_fields if c != "runts_data"]


def _intestazione(request) -> dict:
    gruppo = Gruppo.objects.first()
    if gruppo is None:
        return {"puo_modificare": False}
    return {
        **{c: getattr(gruppo, c) for c in CAMPI_INTESTAZIONE},
        "runts_data": gruppo.runts_data,
        "logo": bool(gruppo.logo),
        "puo_modificare": policy.e_capogruppo(request.auth),
    }


@router.get("/gruppo/intestazione", response=IntestazioneOut)
def intestazione(request):
    if not policy.e_capo_censito(request.auth):
        raise HttpError(403, "Riservato ai capi.")
    return _intestazione(request)


def _gruppo_da_modificare(request) -> Gruppo:
    if not policy.e_capogruppo(request.auth):
        raise HttpError(403, "I dati del gruppo li modificano i capigruppo.")
    gruppo = Gruppo.objects.first()
    if gruppo is None:
        raise HttpError(400, "Importa prima i dati del gruppo da BuonaStrada.")
    return gruppo


@router.put("/gruppo/intestazione", response=IntestazioneOut)
def salva_intestazione(request, dati: IntestazioneIO):
    gruppo = _gruppo_da_modificare(request)
    for campo in CAMPI_INTESTAZIONE:
        setattr(gruppo, campo, getattr(dati, campo).strip())
    gruppo.sede_provincia = gruppo.sede_provincia.upper()
    gruppo.runts_data = dati.runts_data
    try:
        gruppo.full_clean()
    except ValidationError as errore:
        raise HttpError(400, " ".join(errore.messages)) from errore
    gruppo.save()
    return _intestazione(request)


@router.post("/gruppo/logo", response=IntestazioneOut)
def carica_logo(request, file: File[UploadedFile]):
    """PNG or JPEG, re-encoded as PNG by Pillow (no metadata), at most 600 px."""
    import io
    import secrets

    from django.core.files.base import ContentFile
    from PIL import Image, UnidentifiedImageError

    gruppo = _gruppo_da_modificare(request)
    if file.size > 5 * 1024 * 1024:
        raise HttpError(400, "Il logo è troppo grande: al massimo 5 MB.")
    try:
        immagine = Image.open(file)
        immagine.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as errore:
        raise HttpError(400, "Carica un'immagine PNG o JPEG.") from errore
    immagine = immagine.convert("RGBA")
    immagine.thumbnail((600, 600))
    buffer = io.BytesIO()
    immagine.save(buffer, "PNG", optimize=True)
    if gruppo.logo:
        gruppo.logo.delete(save=False)
    gruppo.logo.save(f"{secrets.token_hex(16)}.png", ContentFile(buffer.getvalue()), save=True)
    return _intestazione(request)


@router.delete("/gruppo/logo", response=IntestazioneOut)
def togli_logo(request):
    gruppo = _gruppo_da_modificare(request)
    if gruppo.logo:
        gruppo.logo.delete(save=True)
    return _intestazione(request)
