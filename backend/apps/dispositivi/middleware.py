"""Enforces device revocation and renews the offline window on every request (DEC-97)."""

from datetime import timedelta

from django.contrib.auth import logout
from django.http import JsonResponse
from django.utils import timezone

from .models import CHIAVE_SESSIONE_DISPOSITIVO, Dispositivo

INTESTAZIONE_SCADENZA = "X-QdC-Offline-Fino-Al"
CODICE_REVOCATO = "dispositivo_revocato"
AGGIORNA_OGNI = timedelta(minutes=5)


class DispositivoMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.dispositivo = None
        id_dispositivo = request.session.get(CHIAVE_SESSIONE_DISPOSITIVO)
        if id_dispositivo and request.user.is_authenticated:
            dispositivo = Dispositivo.objects.filter(pk=id_dispositivo, utente=request.user).first()
            if dispositivo is None or dispositivo.revocato:
                logout(request)
                return JsonResponse(
                    {
                        "detail": "Questo dispositivo è stato scollegato: i dati salvati qui "
                        "sono stati cancellati.",
                        "codice": CODICE_REVOCATO,
                    },
                    status=401,
                )
            request.dispositivo = dispositivo
            ora = timezone.now()
            modifiche = []
            if ora - dispositivo.ultimo_contatto > AGGIORNA_OGNI:
                dispositivo.ultimo_contatto = ora
                modifiche.append("ultimo_contatto")
            if request.session.session_key and (
                request.session.session_key != dispositivo.chiave_sessione
            ):
                dispositivo.chiave_sessione = request.session.session_key
                modifiche.append("chiave_sessione")
            if modifiche:
                Dispositivo.objects.filter(pk=dispositivo.pk).update(
                    **{campo: getattr(dispositivo, campo) for campo in modifiche}
                )

        risposta = self.get_response(request)
        dispositivo = getattr(request, "dispositivo", None)
        if dispositivo is not None and not dispositivo.revocato:
            risposta[INTESTAZIONE_SCADENZA] = dispositivo.offline_fino_al().isoformat()
        return risposta
