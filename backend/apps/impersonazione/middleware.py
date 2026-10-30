"""Swaps `request.user` for the impersonated account (see models).

It runs after auditlog's middleware, so the author of the changes in the audit log stays
the real user, and after the device middleware, so revocation still applies to the
real user's device. `request.impersonatore` is the real user, None otherwise.
"""

import re

from django.contrib.auth import logout
from django.http import JsonResponse
from django.utils import timezone

from .models import Impersonazione

CHIAVE_SESSIONE = "qdc_impersonazione"
CODICE_BLOCCATA = "impersonazione"

# The account and the person's own choices: never while acting as someone else.
BLOCCATE = [
    (None, re.compile(r"^/admin/")),
    ("scrittura", re.compile(r"^/_allauth/")),
    (None, re.compile(r"^/api/v1/dispositivi(?!/[^/]+/stato$)")),  # devices, PIN
    (None, re.compile(r"^/api/v1/calendario(/rigenera)?$")),  # the secret feed address
    ("scrittura", re.compile(r"^/api/v1/persone/\d+/visibilita-genitori$")),  # DEC-26
    ("scrittura", re.compile(r"^/api/v1/io/email$")),  # DEC-157
    (None, re.compile(r"^/api/v1/richieste-diritti")),  # DEC-102
    (None, re.compile(r"^/api/v1/persone/\d+/fascicolo$")),
    (None, re.compile(r"^/api/v1/campo/")),  # offline downloads: nothing is saved
    (None, re.compile(r"^/api/v1/impersonazion(e|i)(?!/fine$)")),  # never nested
]
LETTURE = {"GET", "HEAD", "OPTIONS"}
USCITA = re.compile(r"^/_allauth/[^/]+/v1/auth/session$")


def bloccata(metodo: str, percorso: str) -> bool:
    return any(
        regola.match(percorso) and (tipo is None or metodo not in LETTURE)
        for tipo, regola in BLOCCATE
    )


class ImpersonazioneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.impersonatore = None
        request.impersonazione = None
        pk = request.session.get(CHIAVE_SESSIONE) if hasattr(request, "session") else None
        if pk is None or not request.user.is_authenticated:
            return self.get_response(request)
        impersonazione = (
            Impersonazione.objects.in_corso()
            .filter(pk=pk, impersonatore=request.user)
            .select_related("impersonato")
            .first()
        )
        if impersonazione is None or not _ancora_ammessa(request.user, impersonazione):
            Impersonazione.objects.filter(pk=pk, finita_il__isnull=True).update(
                finita_il=timezone.now()
            )
            request.session.pop(CHIAVE_SESSIONE, None)
            return self.get_response(request)
        if request.method == "DELETE" and USCITA.match(request.path):
            # Logging out ends everything: the real user goes too.
            impersonazione.termina()
            logout(request)
            return self.get_response(request)
        if bloccata(request.method, request.path):
            return JsonResponse(
                {
                    "detail": "Mentre usi l'app al posto di un'altra persona non puoi "
                    "cambiare il suo account né le sue scelte personali.",
                    "codice": CODICE_BLOCCATA,
                },
                status=403,
            )
        request.impersonatore = request.user
        request.impersonazione = impersonazione
        request.user = impersonazione.impersonato
        return self.get_response(request)


def _ancora_ammessa(utente, impersonazione: Impersonazione) -> bool:
    """Roles change: checked again on every request."""
    from apps.permessi.policy import puo_impersonare

    return puo_impersonare(utente, impersonazione.impersonato)
