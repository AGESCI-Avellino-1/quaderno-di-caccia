"""Start and end the use of the app as another user (see models)."""

from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.anagrafica.models import Persona
from apps.permessi import policy

from .middleware import CHIAVE_SESSIONE
from .models import DURATA, Impersonazione


def nome(utente) -> str:
    persona = Persona.objects.filter(utente=utente).first()
    return f"{persona.nome} {persona.cognome}" if persona else utente.email


def inizia(request, bersaglio, motivo: str) -> Impersonazione:
    if getattr(request, "impersonatore", None) is not None:
        raise ValidationError("Torna prima a te.")
    if not motivo.strip():
        raise ValidationError("Scrivi perché: la persona lo leggerà.")
    if not policy.puo_impersonare(request.auth, bersaglio):
        raise PermissionError
    impersonazione = Impersonazione.objects.create(
        impersonatore=request.auth,
        nome_impersonatore=nome(request.auth),
        impersonato=bersaglio,
        motivo=motivo.strip()[:300],
        scade_il=timezone.now() + DURATA,
    )
    request.session[CHIAVE_SESSIONE] = impersonazione.pk
    return impersonazione


def termina(request) -> None:
    impersonazione = getattr(request, "impersonazione", None)
    if impersonazione is not None:
        impersonazione.termina()
    request.session.pop(CHIAVE_SESSIONE, None)
