from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router, Schema, Status
from ninja.errors import HttpError

from apps.anagrafica.models import Persona
from apps.permessi import policy

from .adapters import CHIAVE_SESSIONE_INVITO
from .models import Invito, MetodoVerificaGenitore
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
    tutelati: list[PersonaBreve]


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
        "tutelati": list(policy.tutelati(user)),
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
