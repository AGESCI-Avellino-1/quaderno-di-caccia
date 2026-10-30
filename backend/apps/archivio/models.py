"""Archiving two years after leaving (DEC-44, DEC-196, DEC-211): the file goes as a ZIP
to the group's shared Drive, checked, and only then the data leave the app; name and
years in the units stay, to recognise who comes back."""

from django.conf import settings
from django.db import models

from apps.anagrafica.models import Persona
from apps.core.models import ModelloTracciato


class Archiviazione(ModelloTracciato):
    persona = models.ForeignKey(
        Persona, null=True, blank=True, on_delete=models.SET_NULL, related_name="archiviazioni"
    )
    # Copied: the archive is found on the Drive by this name.
    nome = models.CharField(max_length=170)
    file_drive = models.CharField(max_length=120)
    nome_file = models.CharField(max_length=200)
    md5 = models.CharField(max_length=32)
    dimensione = models.PositiveBigIntegerField()
    confermata_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        verbose_name = "archiviazione"
        verbose_name_plural = "archiviazioni"
        ordering = ["-creato_il"]

    def __str__(self) -> str:
        return f"Archivio di {self.nome}"
