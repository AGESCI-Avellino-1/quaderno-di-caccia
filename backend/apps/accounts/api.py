from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router, Schema, Status
from ninja.errors import HttpError

from apps.anagrafica.models import Persona
from apps.iscrizioni.models import DA_COMPLETARE, RichiestaIscrizione, StatoIscrizione
from apps.permessi import policy

from .adapters import CHIAVE_SESSIONE_INVITO
from .models import Invito, MetodoVerificaGenitore, User
from .servizi import invia_invito

router = Router(tags=["account"])


class PersonaBreve(Schema):
    id: int
    nome: str
    cognome: str


class Profilo(Schema):
    email: str
    persona: PersonaBreve | None
    # Theme key for <html data-branca> (django-agesci-campania-theme names).
    branca: str
    capo: bool
    capogruppo: bool
    tesoriere: bool
    amministratore_tecnico: bool
    squadriglie_guidate: list[int]
    # Patrols the user is a member of (shows "La mia squadriglia").
    squadriglie: list[int]
    # Joining from the app: own requests, and requests this user decides (waiting).
    mie_iscrizioni: int
    iscrizioni_da_decidere: int
    # Accepted registrations with signed forms waiting for this user's check.
    iscrizioni_da_verificare: int
    # Capigruppo: completed registrations to enter in BuonaStrada.
    iscrizioni_da_inserire: int
    capo_in_attesa: bool
    tutelati: list[PersonaBreve]
    # Fees: the group sets them; units whose payment situation the user may see.
    gestisce_quote: bool
    unita_quote: list[int]


@router.get("/io", response=Profilo)
def profilo(request):
    """Who am I and which roles do I hold: drives the PWA navigation."""
    user = request.auth
    persona = policy.persona_di(user)
    return {
        "email": user.email,
        "persona": persona,
        "branca": policy.tema_branca(user),
        "capo": policy.e_capo(user),
        "capogruppo": policy.e_capogruppo(user),
        "tesoriere": policy.e_tesoriere(user),
        "amministratore_tecnico": policy.e_amministratore(user),
        "squadriglie_guidate": list(policy.squadriglie_guidate(user).values_list("id", flat=True)),
        "squadriglie": list(policy.squadriglie_di(user).values_list("id", flat=True)),
        "mie_iscrizioni": RichiestaIscrizione.objects.filter(utente=user).count(),
        "iscrizioni_da_decidere": RichiestaIscrizione.objects.filter(
            unita__in=policy.unita_da_approvare(user), stato=StatoIscrizione.IN_ATTESA
        ).count(),
        "iscrizioni_da_verificare": RichiestaIscrizione.objects.filter(
            unita__in=policy.unita_da_approvare(user),
            stato__in=DA_COMPLETARE,
            moduli_verificati_il__isnull=True,
            allegati__isnull=False,
        )
        .distinct()
        .count(),
        "iscrizioni_da_inserire": (
            RichiestaIscrizione.objects.filter(stato=StatoIscrizione.COMPLETATA).count()
            if policy.puo_gestire_iscrizioni_buonastrada(user)
            else 0
        ),
        "capo_in_attesa": policy.e_capo_in_attesa(user),
        "tutelati": list(policy.tutelati(user)),
        "gestisce_quote": policy.puo_gestire_quote(user),
        "unita_quote": policy.unita_situazione_quote(user),
    }


class NuovoInvito(Schema):
    persona_id: int
    email: str
    consenso_genitore_da_id: int | None = None
    consenso_genitore_metodo: MetodoVerificaGenitore | None = None


class InvitoCreato(Schema):
    id: int
    email: str
    token: str
    scadenza: str


@router.post("/inviti", response={201: InvitoCreato})
def crea_invito(request, dati: NuovoInvito):
    persona = get_object_or_404(Persona, pk=dati.persona_id)
    if not policy.puo_invitare(request.auth, persona):
        raise HttpError(403, "Non puoi invitare questa persona.")
    # An invite is consumed only by a new account linked to a Persona without one
    # (adapters.collega_invito): anything else would create an orphan account.
    if persona.utente_id is not None:
        raise HttpError(400, "Questa persona ha già un account.")
    if User.objects.filter(email__iexact=dati.email).exists():
        raise HttpError(400, "Esiste già un account con questa email.")
    # One email per person: a child is not invited with a parent's address, which the
    # parent needs for their own account (DEC-116, refines DEC-25).
    if Persona.objects.exclude(pk=persona.pk).filter(email__iexact=dati.email).exists():
        raise HttpError(
            400,
            "Questa email è di un'altra persona (ad esempio un genitore): ogni account "
            "ha bisogno di un'email sua.",
        )
    invito = Invito(email=dati.email, persona=persona, creato_da=request.auth)
    if dati.consenso_genitore_da_id:
        invito.consenso_genitore_da_id = dati.consenso_genitore_da_id
        invito.consenso_genitore_il = timezone.now()
        invito.consenso_genitore_metodo = dati.consenso_genitore_metodo or ""
    try:
        invito.full_clean()
    except ValidationError as errore:
        raise HttpError(400, " ".join(errore.messages)) from errore
    invito.save()
    invia_invito(invito)
    return Status(
        201,
        {
            "id": invito.pk,
            "email": invito.email,
            "token": invito.token,
            "scadenza": invito.scadenza.isoformat(),
        },
    )


class InvitoOut(Schema):
    id: int
    email: str
    creato_il: str
    scadenza: str
    usato_il: str | None
    valido: bool


class SchedaAccount(Schema):
    id: int
    nome: str
    cognome: str
    ha_account: bool
    puo_invitare: bool
    richiede_consenso_genitore: bool
    # The person's own address from the registry, proposed in the invitation form.
    email: str | None
    inviti: list[InvitoOut]


class Scelta(Schema):
    valore: str
    etichetta: str


class StatoAccount(Schema):
    persona: SchedaAccount
    # Parents with parental responsibility: the only ones who may have an account and
    # give consent (DEC-16, DEC-24).
    genitori: list[SchedaAccount]
    metodi_consenso: list[Scelta]


def _invito_out(invito: Invito) -> dict:
    return {
        "id": invito.pk,
        "email": invito.email,
        "creato_il": invito.creato_il.isoformat(),
        "scadenza": invito.scadenza.isoformat(),
        "usato_il": invito.usato_il.isoformat() if invito.usato_il else None,
        "valido": invito.valido,
    }


def _scheda_account(user, persona: Persona) -> dict:
    return {
        "id": persona.pk,
        "nome": persona.nome,
        "cognome": persona.cognome,
        "ha_account": persona.utente_id is not None,
        "puo_invitare": policy.puo_invitare(user, persona),
        "richiede_consenso_genitore": Invito(persona=persona).richiede_consenso_genitore(),
        "email": persona.email or None,
        "inviti": [_invito_out(i) for i in persona.inviti.order_by("-creato_il")],
    }


@router.get("/persone/{persona_id}/account", response=StatoAccount)
def stato_account(request, persona_id: int):
    """Who has an account and which invitations are open, for the person and their
    parents: the panel from which a capogruppo or capo unità invites (DEC-21)."""
    persona = get_object_or_404(Persona, pk=persona_id)
    if not policy.puo_invitare(request.auth, persona):
        raise HttpError(404, "Persona non trovata.")
    genitori = list(
        Persona.objects.filter(
            tutele__minore=persona, tutele__responsabilita_genitoriale=True
        ).order_by("cognome", "nome")
    )
    return {
        "persona": _scheda_account(request.auth, persona),
        "genitori": [_scheda_account(request.auth, g) for g in genitori],
        "metodi_consenso": [
            {"valore": valore, "etichetta": etichetta}
            for valore, etichetta in MetodoVerificaGenitore.choices
        ],
    }


@router.post("/inviti/{invito_id}/annulla", response=InvitoOut)
def annulla_invito(request, invito_id: int):
    """Withdraw an unused invitation, e.g. sent to a wrong address: the link stops
    working at once."""
    invito = get_object_or_404(Invito.objects.select_related("persona"), pk=invito_id)
    if not policy.puo_invitare(request.auth, invito.persona):
        raise HttpError(404, "Invito non trovato.")
    if invito.usato_il is not None:
        raise HttpError(409, "L'invito è già stato usato.")
    if invito.valido:
        invito.scadenza = timezone.now()
        invito.save(update_fields=["scadenza", "aggiornato_il"])
    return _invito_out(invito)


class AccettaInvito(Schema):
    token: str


class EsitoInvito(Schema):
    email: str
    persona: str


@router.post("/inviti/accetta", response=EsitoInvito, auth=None)
def accetta_invito(request, dati: AccettaInvito):
    """Validate an invitation and open sign-up for this browser session (DEC-21).

    The PWA then completes sign-up through allauth headless with the same email.
    """
    invito = Invito.objects.select_related("persona").filter(token=dati.token).first()
    if invito is None or not invito.valido:
        raise HttpError(404, "Invito non valido o scaduto.")
    request.session[CHIAVE_SESSIONE_INVITO] = invito.token
    return {"email": invito.email, "persona": str(invito.persona)}
