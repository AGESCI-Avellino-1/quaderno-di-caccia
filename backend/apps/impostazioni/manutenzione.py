"""Maintenance (DEC-268): while it lasts only the technical administrators get in.

Everybody else gets 503 with the message: the PWA takes a 503 as "server not reachable",
so the copies on the phone stay readable and the queued writes wait (offline/outbox.ts).
Left open: what the PWA needs to show the message and the privacy pages (`/sito`,
`/pagine/…`), the containers' health check, and the login itself, so that an
administrator can get in; anyone else who logs in is logged out at once.
"""

from django.contrib.auth import logout
from django.http import JsonResponse

from apps.permessi import policy

from .models import Impostazioni

CODICE_MANUTENZIONE = "manutenzione"
SEMPRE_APERTI = ("/api/v1/sito", "/api/v1/salute")
PAGINE_APERTE = "/api/v1/pagine/"
# Where one logs in: the PWA's allauth API, allauth's own pages (Google and Apple come
# back there) and the Django admin's login page.
ACCESSO = ("/_allauth/", "/accounts/", "/admin/")


def _in_manutenzione() -> JsonResponse:
    return JsonResponse(
        {"detail": Impostazioni.carica().avviso_manutenzione(), "codice": CODICE_MANUTENZIONE},
        status=503,
        headers={"Retry-After": "300"},
    )


class ManutenzioneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        percorso = request.path
        if percorso in SEMPRE_APERTI or percorso.startswith(PAGINE_APERTE):
            return self.get_response(request)
        if not Impostazioni.objects.filter(pk=1, manutenzione=True).exists():
            return self.get_response(request)
        if policy.puo_gestire_manutenzione(request.user):
            return self.get_response(request)
        if request.user.is_authenticated:
            # Logging out stays possible.
            if request.method == "DELETE" and percorso.endswith("/auth/session"):
                return self.get_response(request)
            return _in_manutenzione()
        # Anonymous: only logging in, never signing up.
        if not percorso.startswith(ACCESSO) or "signup" in percorso:
            return _in_manutenzione()
        risposta = self.get_response(request)
        if request.user.is_authenticated and not policy.puo_gestire_manutenzione(request.user):
            logout(request)
            # Google and Apple come back to an allauth page that redirects to the PWA:
            # let the redirect go, the PWA shows the message on the login page.
            if percorso.startswith("/_allauth/"):
                return _in_manutenzione()
        return risposta
