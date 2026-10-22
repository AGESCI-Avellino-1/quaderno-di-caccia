"""Idempotency for writes replayed by the offline queue (DEC-96, PP-Q).

The PWA sends every queued write with an ``Idempotency-Key`` header (a UUID created
when the user acted, while offline). If the same user sends the same key again, the
stored response is returned and the write is NOT executed a second time.

Scope: /api/v1/ writes by session-authenticated users. The store app (X-Session-Token)
authenticates inside django-ninja, after middleware: extend this when that client
lands (see CLAUDE.md, roadmap).
"""

import uuid

from django.db import IntegrityError, transaction
from django.http import HttpResponse, JsonResponse

from .models import RichiestaIdempotente

INTESTAZIONE = "HTTP_IDEMPOTENCY_KEY"
METODI_SCRITTURA = {"POST", "PUT", "PATCH", "DELETE"}
PREFISSO_API = "/api/v1/"


class IdempotenzaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        chiave = request.META.get(INTESTAZIONE)
        if (
            not chiave
            or request.method not in METODI_SCRITTURA
            or not request.path.startswith(PREFISSO_API)
            or not request.user.is_authenticated
        ):
            return self.get_response(request)
        try:
            chiave = str(uuid.UUID(chiave))
        except ValueError:
            return JsonResponse({"detail": "Idempotency-Key deve essere un UUID."}, status=400)

        precedente = RichiestaIdempotente.objects.filter(utente=request.user, chiave=chiave).first()
        if precedente is not None:
            if (precedente.metodo, precedente.percorso) != (request.method, request.path):
                return JsonResponse(
                    {"detail": "Idempotency-Key già usata per un'altra richiesta."}, status=422
                )
            risposta = HttpResponse(
                precedente.corpo,
                status=precedente.stato_http,
                content_type=precedente.content_type,
            )
            risposta["Idempotent-Replayed"] = "true"
            return risposta

        risposta = self.get_response(request)
        if 200 <= risposta.status_code < 300 and not getattr(risposta, "streaming", False):
            try:
                with transaction.atomic():
                    RichiestaIdempotente.objects.create(
                        utente=request.user,
                        chiave=chiave,
                        metodo=request.method,
                        percorso=request.path,
                        stato_http=risposta.status_code,
                        content_type=risposta.get("Content-Type", "application/json"),
                        corpo=risposta.content.decode("utf-8", errors="replace"),
                    )
            except IntegrityError:
                pass  # a concurrent replay stored it first: same effect
        return risposta
