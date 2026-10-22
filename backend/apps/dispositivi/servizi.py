from importlib import import_module

from django.conf import settings
from django.utils import timezone

from .models import Dispositivo


def revoca(dispositivo: Dispositivo, da) -> None:
    """Revoke a device: its session ends now, its local data is wiped at the next contact
    or when its offline window expires (DEC-97)."""
    if dispositivo.revocato:
        return
    dispositivo.revocato_il = timezone.now()
    dispositivo.revocato_da = da
    dispositivo.save(update_fields=["revocato_il", "revocato_da", "aggiornato_il"])
    if dispositivo.chiave_sessione:
        motore = import_module(settings.SESSION_ENGINE)
        motore.SessionStore().delete(dispositivo.chiave_sessione)
