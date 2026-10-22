from django.conf import settings
from django.db import models


class ModelloTracciato(models.Model):
    """Abstract base: creation and update timestamps on every domain record."""

    creato_il = models.DateTimeField(auto_now_add=True)
    aggiornato_il = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class FonteDato(models.TextChoices):
    """Where a record comes from (DEC-30, DEC-31, DEC-46)."""

    BUONASTRADA = "BUONASTRADA", "BuonaStrada"
    APP = "APP", "Inserito nell'app"
    RICOSTRUITO = "RICOSTRUITO", "Ricostruito"


class RichiestaIdempotente(models.Model):
    """Stored response of a write sent with an Idempotency-Key (apps.core.idempotenza)."""

    utente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    chiave = models.CharField(max_length=36)
    metodo = models.CharField(max_length=10)
    percorso = models.CharField(max_length=300)
    stato_http = models.PositiveSmallIntegerField()
    content_type = models.CharField(max_length=100)
    corpo = models.TextField()
    creato_il = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "richiesta idempotente"
        verbose_name_plural = "richieste idempotenti"
        constraints = [
            models.UniqueConstraint(fields=["utente", "chiave"], name="chiave_idempotenza_unica")
        ]

    def __str__(self) -> str:
        return f"{self.metodo} {self.percorso} [{self.chiave}]"
