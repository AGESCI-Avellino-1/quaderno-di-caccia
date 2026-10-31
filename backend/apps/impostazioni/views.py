"""Mailpit's web interface behind Django (DEC-249): only the technical administrator, only
where the test mode is allowed. Mailpit itself publishes no port on a server.

Not CSRF-protected: Mailpit's own page sends PUT and DELETE without Django's token. The
session cookie is SameSite=Lax, so another site cannot make those requests with it.
"""

import urllib.error
import urllib.request

from django.conf import settings
from django.http import Http404, HttpResponse
from django.views.decorators.csrf import csrf_exempt

from apps.permessi import policy

INOLTRATE = ("Content-Type", "Accept")
RESTITUITE = ("Content-Type", "Content-Disposition", "Cache-Control")


@csrf_exempt
def mailpit(request, percorso: str = ""):
    # 404, not 403: who may not use it need not know it exists.
    if not settings.QDC_MAILPIT_CONSENTITO or not policy.e_amministratore(request.user):
        raise Http404
    url = f"{settings.QDC_MAILPIT_URL.rstrip('/')}/mailpit/{percorso}"
    if request.META.get("QUERY_STRING"):
        url += f"?{request.META['QUERY_STRING']}"
    richiesta = urllib.request.Request(  # noqa: S310 - fixed host from the settings
        url,
        data=request.body or None,
        method=request.method,
        headers={h: request.headers[h] for h in INOLTRATE if h in request.headers},
    )
    try:
        with urllib.request.urlopen(richiesta, timeout=15) as risposta:  # noqa: S310
            stato, intestazioni, corpo = risposta.status, risposta.headers, risposta.read()
    except urllib.error.HTTPError as errore:
        stato, intestazioni, corpo = errore.code, errore.headers, errore.read()
    except urllib.error.URLError, TimeoutError:
        return HttpResponse(
            "Mailpit non risponde: va avviato insieme al server (vedi la guida di "
            "installazione).",
            status=503,
            content_type="text/plain; charset=utf-8",
        )
    uscita = HttpResponse(corpo, status=stato)
    for h in RESTITUITE:
        if h in intestazioni:
            uscita[h] = intestazioni[h]
    return uscita
