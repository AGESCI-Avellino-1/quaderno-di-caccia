"""Push notifications (DEC-345): standard Web Push, no outside service."""

from django.conf import settings
from django.db import models

from apps.anagrafica.models import Persona
from apps.core.models import ModelloTracciato


class ChiaviPush(ModelloTracciato):
    """This installation's keys, made the first time they are needed: nothing to configure.
    The private one is encrypted with QDC_CHIAVE_SEGRETI, like the SMTP password (DEC-277)."""

    pubblica = models.CharField(max_length=120)
    privata_cifrata = models.TextField()

    class Meta:
        verbose_name = "chiavi delle notifiche"
        verbose_name_plural = "chiavi delle notifiche"


class IscrizionePush(ModelloTracciato):
    """A browser that said yes. It lasts as long as its session: logging out, a revoked device
    or another account on the same browser end it (DEC-345)."""

    utente = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="iscrizioni_push"
    )
    endpoint = models.TextField(unique=True)
    p256dh = models.CharField(max_length=200)
    auth = models.CharField(max_length=100)
    sessione = models.CharField(max_length=40)

    class Meta:
        verbose_name = "iscrizione alle notifiche"
        verbose_name_plural = "iscrizioni alle notifiche"

    def __str__(self) -> str:
        return f"Notifiche di {self.utente_id}"


class PreferenzePush(ModelloTracciato):
    """Which notifications a person wants, the same on all their devices. On the same kinds as
    the emails: «promemoria_quote» covers fees and BuonaCaccia, «riepiloghi» what the capi are
    reminded of."""

    persona = models.OneToOneField(
        Persona, on_delete=models.CASCADE, related_name="preferenze_push"
    )
    eventi = models.BooleanField(default=True)
    promemoria_quote = models.BooleanField(default=True)
    riepiloghi = models.BooleanField(default=True)
    avvisi = models.BooleanField(default=True)

    class Meta:
        verbose_name = "preferenze delle notifiche"
        verbose_name_plural = "preferenze delle notifiche"

    def __str__(self) -> str:
        return f"Notifiche di {self.persona}"


class PushInCoda(models.Model):
    """Sent by the «posta» service: a request must not wait for hundreds of phones."""

    iscrizione = models.ForeignKey(IscrizionePush, on_delete=models.CASCADE, related_name="+")
    dati = models.JSONField()
    creato_il = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "notifica in coda"
        verbose_name_plural = "notifiche in coda"
        ordering = ["pk"]

    def __str__(self) -> str:
        return f"Notifica {self.pk}"
