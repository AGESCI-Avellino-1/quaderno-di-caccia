"""Phones and computers that keep QdC data offline (DEC-23, DEC-97).

A device is registered when its user sets up the local protection (PIN, biometrics).
Its id is stored in the server-side session, so revoking it cannot be dodged by the
client: the next request from that session is logged out and told to wipe its data.
"""

import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import ModelloTracciato

CHIAVE_SESSIONE_DISPOSITIVO = "qdc_dispositivo"


class DispositivoQuerySet(models.QuerySet):
    def attivi(self):
        return self.filter(revocato_il__isnull=True)


class Dispositivo(ModelloTracciato):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    utente = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="dispositivi"
    )
    nome = models.CharField(max_length=80, help_text="Es. «iPhone di Laura».")
    user_agent = models.CharField(max_length=300, blank=True)
    chiave_sessione = models.CharField(max_length=40, blank=True, editable=False)
    ultimo_contatto = models.DateTimeField(default=timezone.now)
    revocato_il = models.DateTimeField(null=True, blank=True)
    revocato_da = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    objects = DispositivoQuerySet.as_manager()

    class Meta:
        verbose_name = "dispositivo"
        verbose_name_plural = "dispositivi"
        ordering = ["-ultimo_contatto"]

    def __str__(self) -> str:
        return f"{self.nome} ({self.utente})"

    @property
    def revocato(self) -> bool:
        return self.revocato_il is not None

    def offline_fino_al(self):
        """Until when the device may keep data without talking to the server (DEC-97).
        Past this moment the app deletes its local data by itself."""
        return self.ultimo_contatto + timedelta(days=settings.QDC_OFFLINE_GIORNI)
