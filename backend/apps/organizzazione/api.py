from datetime import date

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import File, Query, Router, Schema, Status, UploadedFile
from ninja.errors import HttpError

from apps.anagrafica.models import (
    Appartenenza,
    AppartenenzaSquadriglia,
    DerogaSquadriglia,
    Persona,
    RuoloAppartenenza,
)
from apps.anagrafica.servizi import con_unita
from apps.core.anno import compie_anni
from apps.permessi import policy
from apps.permessi.models import Azione, Categoria, registra_accessi

from . import servizi
from .animali import AnimaleBreve, breve
from .models import (
    GUIDE_DI_SQUADRIGLIA,
    INCARICHI_DI_SERVIZIO,
    INCARICHI_DI_SQUADRIGLIA,
    PREFISSO_DEFINITO,
    Q_SERVIZI_IN_UNITA,
    Q_SERVIZI_SUPPORTO,
    RUOLI_DI_GRUPPO,
    RUOLI_DI_SQUADRIGLIA,
    RUOLI_DI_UNITA,
    SERVIZI_DI_SUPPORTO,
    SERVIZIO_IN_UNITA,
    Ambiente,
    AmbitoIncarico,
    AnimaleSquadriglia,
    Composizione,
    Gruppo,
    Incarico,
    RuoloIncarico,
    Squadriglia,
    TipoIncarico,
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
    # Archived: out of the lists, back when someone of its history returns (DEC-275).
    archiviata_il: date | None = None
    collegata_a: int | None
    collegata_nome: str = ""
    nota_collegamento: str
    # Shared cash with the linked unit since this day (DEC-288).
    cassa_comune_dal: date | None = None
    # Ages for the waiting list (DEC-260); None for the Co.Ca.
    eta_minima: int | None = None
    eta_massima: int | None = None

    @staticmethod
    def resolve_eta_minima(obj: Unita) -> int | None:
        return obj.eta[0] if obj.eta else None

    @staticmethod
    def resolve_eta_massima(obj: Unita) -> int | None:
        return obj.eta[1] if obj.eta else None

    @staticmethod
    def resolve_branca(obj: Unita) -> str:
        return obj.branca.value

    @staticmethod
    def resolve_collegata_a(obj: Unita) -> int | None:
        return obj.collegata_a_id

    @staticmethod
    def resolve_collegata_nome(obj: Unita) -> str:
        return str(obj.collegata_a) if obj.collegata_a_id else ""


class UnitaIn(Schema):
    nome: str
    tipo: TipoUnita
    composizione: Composizione
    ambiente: Ambiente = Ambiente.NESSUNO
    # Parallel units, linked both ways and in pairs (DEC-36, DEC-279).
    collegata_a: int | None = None
    nota_collegamento: str = ""
    attiva: bool = True


@router.get("/unita", response=list[UnitaOut])
def elenco_unita(request, tutte: bool = False):
    """Units of the group: visible to any capo (DEC-09). `tutte` adds closed ones, not
    the archived ones (DEC-275)."""
    if not policy.puo_vedere_organizzazione(request.auth):
        raise HttpError(403, "Riservato ai capi.")
    unita = (
        Unita.objects.filter(archiviata_il__isnull=True)
        if tutte
        else Unita.objects.filter(attiva=True)
    )
    return unita


@transaction.atomic
def _applica_unita(unita: Unita, dati: UnitaIn) -> Unita:
    altra = None
    if dati.collegata_a is not None:
        if dati.collegata_a == unita.pk:
            raise HttpError(400, "Un'unità non può essere collegata a sé stessa.")
        altra = get_object_or_404(Unita, pk=dati.collegata_a, gruppo=unita.gruppo)
    unita.nome = dati.nome.strip()
    unita.tipo = dati.tipo
    unita.composizione = dati.composizione
    # The setting tells a branco from a cerchio (DEC-225): chosen for a Branco/Cerchio,
    # implied by a Branco or a Cerchio, none outside L/C.
    unita.ambiente = {
        TipoUnita.BRANCO: Ambiente.GIUNGLA,
        TipoUnita.CERCHIO: Ambiente.BOSCO,
        TipoUnita.BRANCO_CERCHIO: dati.ambiente,
    }.get(unita.tipo, Ambiente.NESSUNO)
    unita.attiva = dati.attiva
    _salva(unita)
    # Linked both ways, in pairs only (DEC-279).
    try:
        servizi.collega(unita, altra, dati.nota_collegamento)
    except ValidationError as errore:
        raise HttpError(400, " ".join(errore.messages)) from errore
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


@router.delete("/unita/{unita_id}", response={204: None})
def elimina_unita(request, unita_id: int):
    """Only a closed unit nobody was ever in and nothing refers to (DEC-273)."""
    if not policy.puo_gestire_unita(request.auth):
        raise HttpError(403, "Solo i capigruppo eliminano le unità.")
    try:
        servizi.cancella_unita(get_object_or_404(Unita, pk=unita_id))
    except ValidationError as errore:
        raise HttpError(400, " ".join(errore.messages)) from errore
    return Status(204, None)


# --- Roles (DEC-11, DEC-14, DEC-18) --------------------------------------------------------


class PersonaBreve(Schema):
    id: int
    nome: str
    cognome: str
    # The caller may open their file: the avatar is a link (DEC-314).
    scheda: bool = False

    @staticmethod
    def resolve_scheda(obj, context) -> bool:
        persona_id = obj["id"] if isinstance(obj, dict) else obj.pk
        return policy.scheda_apribile(context["request"], persona_id)


class IncaricoOut(Schema):
    id: int
    ruolo: str
    ruolo_nome: str
    persona: PersonaBreve
    data_inizio: date
    data_fine: date | None
    # A role of a type switched off is no longer offered, but can still be closed (DEC-347).
    chiudibile: bool = False

    @staticmethod
    def resolve_ruolo(obj: Incarico) -> str:
        return obj.codice_ruolo

    @staticmethod
    def resolve_ruolo_nome(obj: Incarico) -> str:
        return obj.get_ruolo_display()

    @staticmethod
    def resolve_chiudibile(obj: Incarico, context) -> bool:
        return bool(obj.tipo_id) and policy.puo_nominare(
            context["request"].auth, RuoloIncarico.DEFINITO
        )


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


def _nomina_definiti(user, **filtri) -> list[dict]:
    """The roles the group defined the user may assign (DEC-347)."""
    if not policy.puo_nominare(user, RuoloIncarico.DEFINITO):
        return []
    return [
        {"valore": t.codice, "etichetta": t.nome}
        for t in TipoIncarico.objects.filter(attivo=True, **filtri)
    ]


class MembroOut(Schema):
    """An active patrol membership (DEC-65)."""

    id: int
    persona: PersonaBreve
    data_inizio: date


class SquadrigliaOut(Schema):
    id: int
    nome: str
    animale: AnimaleBreve | None = None
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
    # The ages for the waiting list (DEC-260): its staff and the capigruppo.
    puo_modificare_eta: bool = False
    # Closed and empty: created by mistake, the capigruppo may delete it (DEC-273).
    puo_eliminare: bool = False
    # Unit roles the caller may assign (and close).
    nomina: list[Scelta]
    # Shared cash with the linked unit (DEC-288): may unite, may split now.
    puo_unire_casse: bool = False
    puo_dividere_casse: bool = False


def _casse_unite(utente, unita: Unita) -> dict:
    from apps.cassa.servizi import puo_dividere

    puo = policy.puo_unire_casse(utente, unita)
    return {
        "puo_unire_casse": puo and not unita.cassa_comune_dal,
        "puo_dividere_casse": puo and puo_dividere(unita),
    }


@router.post("/unita/{unita_id}/casse-unite", response=UnitaOut)
def unisci_casse(request, unita_id: int):
    """One cash box for two linked units from today (DEC-288)."""
    from apps.cassa.servizi import unisci_casse as unisci

    unita = get_object_or_404(Unita, pk=unita_id)
    if not policy.puo_unire_casse(request.auth, unita):
        raise HttpError(403, "Uniscono le casse i capi unità delle due unità e i capigruppo.")
    try:
        unisci(unita, request.auth)
    except ValidationError as errore:
        raise HttpError(400, " ".join(errore.messages)) from errore
    unita.refresh_from_db()
    return unita


@router.delete("/unita/{unita_id}/casse-unite", response=UnitaOut)
def dividi_casse(request, unita_id: int):
    """Each unit with its own cash again: at the start of a year only (DEC-288)."""
    from apps.cassa.servizi import dividi_casse as dividi

    unita = get_object_or_404(Unita, pk=unita_id)
    if not policy.puo_unire_casse(request.auth, unita):
        raise HttpError(403, "Dividono le casse i capi unità delle due unità e i capigruppo.")
    try:
        dividi(unita)
    except ValidationError as errore:
        raise HttpError(400, " ".join(errore.messages)) from errore
    unita.refresh_from_db()
    return unita


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


def _avvisi_animali(unita: Unita) -> list[str]:
    """Patrols from before the animals, whose name matched none (DEC-351)."""
    return [
        f"La squadriglia {s.nome} non ha ancora un animale: sceglilo qui sotto."
        for s in unita.squadriglie.filter(attiva=True, animale__isnull=True)
    ]


def _avvisi_collegamento(unita: Unita) -> list[str]:
    """A one-way link left by the migration to two-way links (DEC-279)."""
    altra = unita.collegata_a
    if altra is None or altra.collegata_a_id == unita.pk:
        return []
    return [
        (
            f"Il collegamento con {altra} vale solo da questa parte: {altra} è collegata a "
            f"{altra.collegata_a}. Togli uno dei due collegamenti con «Modifica» e rifallo."
            if altra.collegata_a_id
            else f"Il collegamento con {altra} vale solo da questa parte: rifallo con «Modifica»."
        )
    ]


def _avvisi_sesso_squadriglie(unita: Unita) -> list[str]:
    """Patrols of the other sex in a single-sex reparto, left from before (DEC-280)."""
    if unita.composizione == Composizione.MISTA:
        return []
    return [
        f"La squadriglia {s.nome} è {s.get_sesso_display().lower()}, ma il reparto è "
        f"{unita.get_composizione_display().lower()}: correggila o chiudila."
        for s in unita.squadriglie.filter(attiva=True).exclude(sesso=unita.composizione)
    ]


# As in the list of the roles (DEC-321): the guides first.
RUOLI_DI_SQUADRIGLIA_IN_ORDINE = [r for r in RuoloIncarico if r in RUOLI_DI_SQUADRIGLIA]


def _incarichi(**filtri):
    return (
        Incarico.objects.attivi()
        .filter(**filtri)
        .select_related("persona", "tipo")
        .order_by("ruolo", "persona__cognome", "persona__nome")
    )


def _incarichi_della_squadriglia(squadriglia: Squadriglia) -> list[Incarico]:
    """The guides first, then the other roles as listed (DEC-321)."""
    return sorted(
        _incarichi(squadriglia=squadriglia),
        key=lambda i: RUOLI_DI_SQUADRIGLIA_IN_ORDINE.index(RuoloIncarico(i.ruolo)),
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
            "animale": breve(s.animale),
            "sesso": s.sesso,
            "attiva": s.attiva,
            "membri": list(
                AppartenenzaSquadriglia.objects.attive()
                .filter(squadriglia=s)
                .select_related("persona")
                .order_by("persona__cognome", "persona__nome")
            ),
            "incarichi": _incarichi_della_squadriglia(s),
            "nomina": _nomina(utente, RUOLI_DI_SQUADRIGLIA_IN_ORDINE, squadriglia=s),
        }
        for s in unita.squadriglie.select_related("animale").order_by("-attiva", "nome")
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
        + _avvisi_collegamento(unita)
        + (_avvisi_sesso_squadriglie(unita) if unita.tipo == TipoUnita.REPARTO else [])
        + (_avvisi_animali(unita) if unita.tipo == TipoUnita.REPARTO else [])
        + (_avvisi_squadriglie(unita) if unita.tipo == TipoUnita.REPARTO else [])
        + _avvisi_maggiore_eta(unita),
        "puo_modificare": policy.puo_gestire_unita(utente),
        "puo_eliminare": policy.puo_gestire_unita(utente)
        and not unita.attiva
        and not unita.appartenenze.exists(),
        "puo_gestire_squadriglie": unita.tipo == TipoUnita.REPARTO
        and policy.puo_gestire_squadriglie(utente, unita),
        "puo_modificare_eta": unita.eta is not None
        and policy.puo_modificare_eta_unita(utente, unita),
        **_casse_unite(utente, unita),
        "nomina": _nomina(
            utente,
            (
                RuoloIncarico.CAPO_UNITA,
                RuoloIncarico.STAFF,
                RuoloIncarico.AE_UNITA,
                RuoloIncarico.TESORIERE_UNITA,
                RuoloIncarico.CONSIGLIO_ANZIANI,
            ),
            unita=unita,
        )
        + (
            _nomina_definiti(utente, ambito=AmbitoIncarico.UNITA)
            if unita.tipo != TipoUnita.COMUNITA_CAPI
            else []
        ),
    }


class StaffUnita(Schema):
    unita_id: int
    unita: str
    incarichi: list[IncaricoOut]
    # What a capogruppo may assign from the Organigramma; empty for the others (DEC-384).
    nomina: list[Scelta]


class CapoInPiuUnita(Schema):
    persona: PersonaBreve
    unita: list[str]


class IncarichiGruppo(Schema):
    # Additional group roles: capigruppo, group treasurers, technical administrators.
    incarichi: list[IncaricoOut]
    nomina: list[Scelta]
    # Capi of the Co.Ca. serving outside the units; "a disposizione" until replaced.
    supporto: list[IncaricoOut]
    nomina_supporto: list[Scelta]
    # For the capigruppo: capi with no service at all, to sort out.
    senza_servizio: list[PersonaBreve]
    # For the capigruppo: who serves more than one unit, a warning and no more (DEC-384).
    capi_in_piu_unita: list[CapoInPiuUnita]
    # The staff of every active unit (DEC-316), appointed here by the capigruppo (DEC-384).
    staff_unita: list[StaffUnita]


# "A disposizione" is no longer assigned (DEC-293).
NUOVI_SERVIZI_DI_SUPPORTO = (RuoloIncarico.SUPPORTO_GRUPPO, RuoloIncarico.SUPPORTO_EDUCATIVO)

RUOLI_AGGIUNTIVI_DI_GRUPPO = (
    RuoloIncarico.CAPOGRUPPO,
    RuoloIncarico.AE_GRUPPO,
    RuoloIncarico.TESORIERE_GRUPPO,
    RuoloIncarico.AMMINISTRATORE,
)


def capi_senza_servizio():
    """Active capi with neither a unit nor a support service (DEC-165, DEC-293). A capogruppo
    serves the group: not one to sort out (maintainer, 02/11)."""
    capi = Appartenenza.objects.attive().filter(ruolo=RuoloAppartenenza.CAPO)
    in_servizio = Incarico.objects.attivi().filter(
        Q(ruolo__in=INCARICHI_DI_SERVIZIO | {RuoloIncarico.CAPOGRUPPO}) | Q(tipo__di_servizio=True)
    )
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
        "incarichi": list(
            _incarichi().filter(
                Q(ruolo__in=RUOLI_AGGIUNTIVI_DI_GRUPPO)
                | Q(tipo__ambito=AmbitoIncarico.GRUPPO, tipo__di_servizio=False)
            )
        ),
        "nomina": _nomina(request.auth, RUOLI_AGGIUNTIVI_DI_GRUPPO)
        + _nomina_definiti(request.auth, ambito=AmbitoIncarico.GRUPPO, di_servizio=False),
        "supporto": list(_incarichi().filter(Q_SERVIZI_SUPPORTO)),
        "nomina_supporto": _nomina(request.auth, NUOVI_SERVIZI_DI_SUPPORTO)
        + _nomina_definiti(request.auth, ambito=AmbitoIncarico.GRUPPO, di_servizio=True),
        "senza_servizio": (
            list(capi_senza_servizio()) if policy.e_capogruppo(request.auth) else []
        ),
        "capi_in_piu_unita": capi_in_piu_unita() if policy.e_capogruppo(request.auth) else [],
        "staff_unita": (
            staff_delle_unita(request.auth)
            if policy.puo_vedere_organizzazione(request.auth)
            else []
        ),
    }


RUOLI_STAFF_DI_UNITA = (RuoloIncarico.CAPO_UNITA, RuoloIncarico.STAFF, RuoloIncarico.AE_UNITA)


def capi_in_piu_unita() -> list[dict]:
    """Who is capo unità or staff of more than one unit (DEC-384). Two linked units have one
    staff and count as one (DEC-279); the assistente ecclesiastico does not count."""
    incarichi = (
        Incarico.objects.attivi()
        .filter(
            ruolo__in=(RuoloIncarico.CAPO_UNITA, RuoloIncarico.STAFF),
            unita__attiva=True,
        )
        .exclude(unita__tipo=TipoUnita.COMUNITA_CAPI)
        .select_related("persona", "unita")
        .order_by("persona__cognome", "persona__nome")
    )
    per_capo: dict[int, tuple[Persona, dict[int, Unita]]] = {}
    for i in incarichi:
        per_capo.setdefault(i.persona_id, (i.persona, {}))[1][i.unita_id] = i.unita
    return [
        {
            "persona": persona,
            "unita": [str(u) for u in sorted(unita.values(), key=lambda u: u.chiave_ordine)],
        }
        for persona, unita in per_capo.values()
        if len({min(u.pk, u.collegata_a_id or u.pk) for u in unita.values()}) > 1
    ]


def staff_delle_unita(user) -> list[dict]:
    """Capo unità, staff and assistente ecclesiastico of every active unit but the Co.Ca.,
    in the units' order (DEC-316, DEC-378). A capogruppo also appoints them here; the others
    only look (DEC-384)."""
    unita = list(Unita.objects.filter(attiva=True).exclude(tipo=TipoUnita.COMUNITA_CAPI))
    per_unita: dict[int, list[Incarico]] = {}
    # With the services the group defined for a unit, after the others (DEC-348).
    for i in _incarichi(unita__in=unita).filter(Q_SERVIZI_IN_UNITA):
        per_unita.setdefault(i.unita_id, []).append(i)
    ordine = {r: n for n, r in enumerate(RUOLI_STAFF_DI_UNITA)}
    capogruppo = policy.e_capogruppo(user)
    return [
        {
            "unita_id": u.pk,
            "unita": str(u),
            "incarichi": sorted(
                per_unita.get(u.pk, []), key=lambda i: ordine.get(i.ruolo, len(ordine))
            ),
            "nomina": (
                _nomina(user, RUOLI_STAFF_DI_UNITA, unita=u)
                + _nomina_definiti(user, ambito=AmbitoIncarico.UNITA, di_servizio=True)
                if capogruppo
                else []
            ),
        }
        for u in unita
    ]


class OpzioneElenco(Schema):
    valore: str
    nome: str


class RuoloElenco(OpzioneElenco):
    # For the quick choice of the educational roles or the others (DEC-318).
    educativo: bool


class OpzioniElencoIncarichi(Schema):
    ruoli: list[RuoloElenco]
    # Associative years with roles, latest first: "2026" = 2025/26 (DEC-37).
    anni: list[OpzioneElenco]


@router.get("/gruppo/incarichi/elenco", response=OpzioniElencoIncarichi)
def opzioni_elenco_incarichi(request):
    """What the PDF list of the roles can include (DEC-284)."""
    if not policy.puo_esportare_incarichi(request.auth):
        raise HttpError(403, "Riservato ai capigruppo.")
    from apps.core.anno import AnnoAssociativo

    from .elenco_incarichi import NON_EDUCATIVI, RUOLI_ELENCO, tipi_elencabili

    corrente = AnnoAssociativo.corrente().anno_fine
    primo = (
        Incarico.objects.filter(ruolo__in=[*RUOLI_ELENCO, RuoloIncarico.DEFINITO])
        .order_by("data_inizio")
        .first()
    )
    dal = AnnoAssociativo.da_data(primo.data_inizio).anno_fine if primo else corrente
    usati = set(Incarico.objects.values_list("ruolo", flat=True).distinct())
    return {
        "ruoli": [
            {"valore": r.value, "nome": r.label, "educativo": r not in NON_EDUCATIVI}
            for r in RUOLI_ELENCO
            if r != RuoloIncarico.A_DISPOSIZIONE or r in usati
        ]
        + [
            {"valore": t.codice, "nome": t.nome, "educativo": t.educativo}
            for t in tipi_elencabili().order_by("nome")
        ],
        "anni": [
            {"valore": str(a), "nome": AnnoAssociativo(a).etichetta}
            for a in range(corrente, dal - 1, -1)
        ],
    }


@router.get("/gruppo/incarichi/elenco.pdf")
def elenco_incarichi_pdf(
    request,
    ruoli: Query[list[str]],
    raggruppa: str = "unita",
    anno: int | None = None,
):
    """The group's roles on the letterhead, never stored (DEC-284)."""
    if not policy.puo_esportare_incarichi(request.auth):
        raise HttpError(403, "Riservato ai capigruppo.")
    from . import elenco_incarichi as elenco

    validi = {r.value for r in elenco.RUOLI_ELENCO} | {t.codice for t in elenco.tipi_elencabili()}
    if not ruoli or not set(ruoli) <= validi:
        raise HttpError(400, "Scegli almeno un tipo di incarico tra quelli proposti.")
    if raggruppa not in ("unita", "incarico"):
        raise HttpError(400, "Raggruppa per unità o per incarico.")
    giorno = elenco.giorno_di_riferimento(anno)
    if giorno > date.today():
        raise HttpError(400, "Scegli l'anno in corso o uno passato.")
    contenuto = elenco.pdf(elenco.sezioni(set(ruoli), raggruppa, giorno), giorno, raggruppa)
    risposta = HttpResponse(contenuto, content_type="application/pdf")
    risposta["Content-Disposition"] = 'attachment; filename="incarichi-del-gruppo.pdf"'
    risposta["Cache-Control"] = "no-store"
    return risposta


class CapoDaScegliere(Schema):
    id: int
    nome: str
    cognome: str
    # Next to the name, to tell namesakes apart (DEC-395).
    unita: str = ""


@router.get("/capi", response=list[CapoDaScegliere])
def elenco_capi(request, presbiteri: bool = False):
    """Active capi: who can be appointed to staff and group roles. `presbiteri`: only who
    may be assistente ecclesiastico (DEC-296)."""
    if not policy.puo_vedere_incarichi_di_gruppo(request.auth):
        raise HttpError(403, "Riservato ai capi.")
    capi = Appartenenza.objects.attive().filter(ruolo=RuoloAppartenenza.CAPO)
    persone = Persona.objects.filter(pk__in=capi.values("persona_id"))
    if presbiteri:
        persone = persone.filter(
            Q(professione__icontains="presbitero") | Q(professione__icontains="sacerdote")
        )
    return con_unita(persone.order_by("cognome", "nome"))


class NuovoIncarico(Schema):
    persona_id: int
    # A RuoloIncarico value or, for a role the group defined, "DEFINITO:<id>" (DEC-347).
    ruolo: str
    unita_id: int | None = None
    squadriglia_id: int | None = None
    data_inizio: date | None = None


def _ruolo_scelto(valore: str) -> tuple[RuoloIncarico, TipoIncarico | None]:
    if valore.startswith(PREFISSO_DEFINITO):
        numero = valore.removeprefix(PREFISSO_DEFINITO)
        if not numero.isdecimal():
            raise HttpError(404, "Incarico non trovato.")
        return RuoloIncarico.DEFINITO, get_object_or_404(TipoIncarico, pk=int(numero))
    try:
        ruolo = RuoloIncarico(valore)
    except ValueError as errore:
        raise HttpError(400, "Incarico sconosciuto.") from errore
    if ruolo == RuoloIncarico.DEFINITO:
        raise HttpError(400, "Scegli l'incarico definito dal gruppo.")
    return ruolo, None


@router.post("/incarichi", response={201: IncaricoOut})
def crea_incarico(request, dati: NuovoIncarico):
    ruolo, tipo = _ruolo_scelto(dati.ruolo)
    if ruolo == RuoloIncarico.A_DISPOSIZIONE:
        raise HttpError(
            400, "«A disposizione» non si assegna più: scegli uno dei due servizi di supporto."
        )
    incarico = Incarico(
        persona=get_object_or_404(Persona, pk=dati.persona_id),
        ruolo=ruolo,
        tipo=tipo,
        data_inizio=dati.data_inizio or timezone.localdate(),
    )
    if ruolo in RUOLI_DI_GRUPPO or (tipo and tipo.ambito == AmbitoIncarico.GRUPPO):
        incarico.gruppo = _gruppo()
    elif ruolo in RUOLI_DI_UNITA or tipo:
        incarico.unita = get_object_or_404(Unita, pk=dati.unita_id or 0)
    elif ruolo in RUOLI_DI_SQUADRIGLIA:
        incarico.squadriglia = get_object_or_404(
            Squadriglia.objects.select_related("unita"), pk=dati.squadriglia_id or 0
        )
    if not policy.puo_nominare(
        request.auth, ruolo, unita=incarico.unita, squadriglia=incarico.squadriglia
    ):
        raise HttpError(403, "Non puoi assegnare questo incarico.")
    servizio_di = tipo.ambito if tipo and tipo.di_servizio else None
    with transaction.atomic():
        if ruolo in SERVIZIO_IN_UNITA or servizio_di == AmbitoIncarico.UNITA:
            # Back in a unit: the support service ends by itself (DEC-165, DEC-293, DEC-348).
            _chiudi(incarico.persona, incarico.data_inizio, Q_SERVIZI_SUPPORTO)
        elif ruolo in SERVIZI_DI_SUPPORTO or servizio_di == AmbitoIncarico.GRUPPO:
            # A new service replaces "a disposizione" (DEC-293, DEC-348).
            _chiudi(incarico.persona, incarico.data_inizio, {RuoloIncarico.A_DISPOSIZIONE})
        _salva(incarico)
    return Status(201, incarico)


def _chiudi(persona: Persona, giorno: date, ruoli: set[RuoloIncarico] | Q) -> None:
    filtro = ruoli if isinstance(ruoli, Q) else Q(ruolo__in=ruoli)
    for incarico in Incarico.objects.filter(
        filtro, persona=persona, data_inizio__lte=giorno
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


# --- Roles the group defines (DEC-347...DEC-349) ----------------------------------------------


class IncaricoEsistente(Schema):
    """A fixed role, read only in the list (DEC-349)."""

    nome: str
    ambito: str
    di_servizio: bool
    educativo: bool


class TipoIncaricoIn(Schema):
    nome: str
    ambito: AmbitoIncarico
    di_servizio: bool = False
    educativo: bool = True
    attivo: bool = True


class TipoIncaricoOut(Schema):
    id: int
    nome: str
    ambito: str
    di_servizio: bool
    educativo: bool
    attivo: bool
    # Assigned at least once: what it is no longer changes, it is not deleted.
    usato: bool

    @staticmethod
    def resolve_usato(obj: TipoIncarico) -> bool:
        return obj.incarichi.exists()


class SchedaIncarichi(Schema):
    esistenti: list[IncaricoEsistente]
    definiti: list[TipoIncaricoOut]
    puo_modificare: bool


def _tipo_da_modificare(request, tipo_id: int | None = None) -> TipoIncarico:
    if not policy.puo_definire_incarichi(request.auth):
        raise HttpError(403, "Gli incarichi li definiscono i capigruppo.")
    return get_object_or_404(TipoIncarico, pk=tipo_id) if tipo_id else TipoIncarico()


def _applica_tipo(tipo: TipoIncarico, dati: TipoIncaricoIn) -> TipoIncarico:
    for campo in ("nome", "ambito", "di_servizio", "educativo", "attivo"):
        setattr(tipo, campo, getattr(dati, campo))
    _salva(tipo)
    return tipo


@router.get("/gruppo/scheda-incarichi", response=SchedaIncarichi)
def scheda_incarichi(request):
    """Every role of the capi: the fixed ones to read, the group's own to change."""
    if not policy.puo_vedere_incarichi_di_gruppo(request.auth):
        raise HttpError(403, "Riservato ai capi.")
    from .elenco_incarichi import NON_EDUCATIVI, RUOLI_ELENCO

    return {
        "esistenti": [
            {
                "nome": r.label,
                "ambito": AmbitoIncarico.GRUPPO if r in RUOLI_DI_GRUPPO else AmbitoIncarico.UNITA,
                "di_servizio": r in INCARICHI_DI_SERVIZIO,
                "educativo": r not in NON_EDUCATIVI,
            }
            for r in RUOLI_ELENCO
            if r != RuoloIncarico.A_DISPOSIZIONE
        ],
        "definiti": list(TipoIncarico.objects.all()),
        "puo_modificare": policy.puo_definire_incarichi(request.auth),
    }


@router.post("/gruppo/tipi-incarico", response={201: TipoIncaricoOut})
def crea_tipo_incarico(request, dati: TipoIncaricoIn):
    return Status(201, _applica_tipo(_tipo_da_modificare(request), dati))


@router.put("/gruppo/tipi-incarico/{tipo_id}", response=TipoIncaricoOut)
def modifica_tipo_incarico(request, tipo_id: int, dati: TipoIncaricoIn):
    return _applica_tipo(_tipo_da_modificare(request, tipo_id), dati)


@router.delete("/gruppo/tipi-incarico/{tipo_id}", response={204: None})
def elimina_tipo_incarico(request, tipo_id: int):
    tipo = _tipo_da_modificare(request, tipo_id)
    if tipo.incarichi.exists():
        raise HttpError(400, "Questo incarico è già stato assegnato: puoi solo disattivarlo.")
    tipo.delete()
    return Status(204, None)


# --- Patrols (Squadriglie) -----------------------------------------------------------------


class SquadrigliaIn(Schema):
    # Its plural is the patrol's name: required for a new patrol (DEC-351).
    animale_id: int | None = None
    sesso: str
    attiva: bool = True


class SquadrigliaBreve(Schema):
    id: int
    nome: str
    animale: AnimaleBreve | None = None
    sesso: str
    attiva: bool

    @staticmethod
    def resolve_animale(obj: Squadriglia) -> dict | None:
        return breve(obj.animale)


def _applica_squadriglia(squadriglia: Squadriglia, dati: SquadrigliaIn) -> Squadriglia:
    # A single-sex reparto has patrols of its own sex only (DEC-280). One of the other sex
    # left from before may still be renamed or closed, not created or turned into one.
    composizione = squadriglia.unita.composizione
    if (
        composizione != Composizione.MISTA
        and dati.sesso != composizione
        and (squadriglia.pk is None or dati.sesso != squadriglia.sesso)
    ):
        genere = "maschili" if composizione == Composizione.MASCHILE else "femminili"
        raise HttpError(
            400,
            f"Il reparto è {Composizione(composizione).label.lower()}: le sue squadriglie sono solo {genere}.",
        )
    if dati.animale_id is None and squadriglia.pk is None:
        raise HttpError(400, "Scegli l'animale della squadriglia.")
    if dati.animale_id is not None and dati.animale_id != squadriglia.animale_id:
        animale = get_object_or_404(AnimaleSquadriglia, pk=dati.animale_id)
        if not animale.attivo:
            raise HttpError(400, f"{animale} è disattivato: scegline un altro.")
        giusta = (
            Squadriglia.objects.filter(unita=squadriglia.unita, nome=animale.plurale)
            .exclude(pk=squadriglia.pk)
            .first()
        )
        if giusta is not None:
            raise HttpError(
                400,
                f"In questo reparto c'è già la squadriglia {giusta.nome}"
                f"{'' if giusta.attiva else ' (chiusa: puoi riaprirla)'}.",
            )
        squadriglia.animale = animale
        squadriglia.nome = animale.plurale
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
        .filter(
            persona=appartenenza.persona_id,
            squadriglia=appartenenza.squadriglia_id,
            ruolo__in=GUIDE_DI_SQUADRIGLIA,
        )
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
        # A patrol role belongs to the patrol: it ends with the membership (DEC-321).
        _chiudi(persona, oggi, INCARICHI_DI_SQUADRIGLIA)
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
    _chiudi(appartenenza.persona, oggi, INCARICHI_DI_SQUADRIGLIA)  # DEC-321
    return {"id": appartenenza_id, "rimosso": _chiudi_periodo(appartenenza, oggi)}


class IncarichiDiSquadriglia(Schema):
    id: int
    nome: str
    animale: AnimaleBreve | None = None
    incarichi: list[IncaricoOut]
    nomina: list[Scelta]


def _incarichi_di_squadriglia(request, squadriglia: Squadriglia) -> dict:
    """404, not 403: who may not read them does not learn which patrol it is (DEC-321)."""
    if not policy.puo_vedere_incarichi_squadriglia(request.auth, squadriglia):
        raise HttpError(404, "Non trovato.")
    return {
        "id": squadriglia.pk,
        "nome": squadriglia.nome,
        "animale": breve(squadriglia.animale),
        "incarichi": _incarichi_della_squadriglia(squadriglia),
        "nomina": _nomina(request.auth, RUOLI_DI_SQUADRIGLIA_IN_ORDINE, squadriglia=squadriglia),
    }


@router.get("/squadriglie/{squadriglia_id}/incarichi", response=IncarichiDiSquadriglia)
def incarichi_della_squadriglia(request, squadriglia_id: int):
    squadriglia = get_object_or_404(Squadriglia.objects.select_related("unita"), pk=squadriglia_id)
    return _incarichi_di_squadriglia(request, squadriglia)


@router.get("/persone/{persona_id}/incarichi-squadriglia", response=IncarichiDiSquadriglia)
def incarichi_della_squadriglia_di(request, persona_id: int):
    """The patrol of a person, seen from their file (by the parents, above all)."""
    membro = (
        AppartenenzaSquadriglia.objects.attive()
        .filter(persona=persona_id)
        .select_related("squadriglia__unita")
        .first()
    )
    if membro is None:
        raise HttpError(404, "Non trovato.")
    return _incarichi_di_squadriglia(request, membro.squadriglia)


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
        raise HttpError(400, f"{persona} non è un ragazzo/a di {reparto}.")
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
    # The official name for the prints, not the one in the title (DEC-245); None
    # leaves it as it is (older clients).
    denominazione: str | None = None
    denominazione_sociale: str = ""
    codice_fiscale: str = ""
    partita_iva: str = ""
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


CAMPI_INTESTAZIONE = [
    c for c in IntestazioneIO.model_fields if c not in ("runts_data", "denominazione")
]


def _intestazione(request) -> dict:
    gruppo = Gruppo.objects.first()
    if gruppo is None:
        return {"puo_modificare": False}
    return {
        **{c: getattr(gruppo, c) for c in CAMPI_INTESTAZIONE},
        "denominazione": gruppo.denominazione,
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
    if dati.denominazione is not None:
        if not dati.denominazione.strip():
            raise HttpError(400, "Scrivi la denominazione del gruppo.")
        gruppo.denominazione = dati.denominazione.strip()
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
