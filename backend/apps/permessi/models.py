"""Log of who read or downloaded sensitive data (DEC-101).

Changes are already tracked by django-auditlog; this records READS, which auditlog does
not see. Consulted by the Co.Ca.; parents and judicial authorities on request.
"""

from django.conf import settings
from django.db import models

from apps.anagrafica.models import Persona


class Categoria(models.TextChoices):
    SANITARIE = "SANITARIE", "Informazioni sanitarie"
    DEROGA_SQ = "DEROGA_SQ", "Eccezione sulla squadriglia"
    FASCICOLO = "FASCICOLO", "Fascicolo completo"
    MODULI = "MODULI", "Moduli firmati"
    ISCRIZIONI = "ISCRIZIONI", "Dati per BuonaStrada"


class Azione(models.TextChoices):
    LETTURA = "LETTURA", "Lettura"
    SCARICO_OFFLINE = "SCARICO_OFFLINE", "Scaricate sul dispositivo"
    MODIFICA = "MODIFICA", "Modifica"
    ESPORTAZIONE = "ESPORTAZIONE", "Esportazione per un diritto dell'interessato"
    CANCELLAZIONE = "CANCELLAZIONE", "Cancellazione per un diritto dell'interessato"


class AccessoDatoSensibile(models.Model):
    utente = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    persona = models.ForeignKey(Persona, on_delete=models.CASCADE, related_name="accessi_sensibili")
    categoria = models.CharField(max_length=12, choices=Categoria.choices)
    azione = models.CharField(max_length=16, choices=Azione.choices)
    dispositivo = models.ForeignKey(
        "dispositivi.Dispositivo",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    creato_il = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "accesso a dati sensibili"
        verbose_name_plural = "accessi a dati sensibili"
        ordering = ["-creato_il"]

    def __str__(self) -> str:
        return f"{self.get_azione_display()} {self.get_categoria_display()} di {self.persona}"


def registra_accessi(request, persone, categoria: str, azione: str) -> None:
    """One row per person: the Co.Ca. can answer "who saw my child's data?"."""
    dispositivo = getattr(request, "dispositivo", None)
    AccessoDatoSensibile.objects.bulk_create(
        AccessoDatoSensibile(
            utente=request.auth,
            persona=persona,
            categoria=categoria,
            azione=azione,
            dispositivo=dispositivo,
        )
        for persona in persone
    )
