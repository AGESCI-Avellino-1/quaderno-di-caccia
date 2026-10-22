from django.conf import settings
from django.db import models

from apps.core.models import ModelloTracciato


class StatoImportazione(models.TextChoices):
    ANTEPRIMA = "ANTEPRIMA", "Anteprima"
    APPLICATA = "APPLICATA", "Applicata"
    ANNULLATA = "ANNULLATA", "Annullata"


class ImportazioneBuonaStrada(ModelloTracciato):
    """One upload of the "Ricerca Soci" export: preview first, then apply (DEC-27)."""

    file = models.FileField(upload_to="importazioni/%Y/")
    nome_file = models.CharField(max_length=200)
    sha256 = models.CharField(max_length=64)
    anno_scout = models.PositiveSmallIntegerField(null=True, blank=True)
    stato = models.CharField(
        max_length=10, choices=StatoImportazione.choices, default=StatoImportazione.ANTEPRIMA
    )
    riepilogo = models.JSONField(default=dict)
    caricata_da = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    applicata_da = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    applicata_il = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "importazione da BuonaStrada"
        verbose_name_plural = "importazioni da BuonaStrada"
        ordering = ["-creato_il"]

    def __str__(self) -> str:
        return f"{self.nome_file} ({self.get_stato_display()})"
