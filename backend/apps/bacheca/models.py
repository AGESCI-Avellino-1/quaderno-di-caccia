"""The notice board (DEC-03, DEC-218…DEC-220): notices only, no chat, no replies, no
read receipts.

- Published by the unit staff for their unit and by the capigruppo for the whole group
  or any unit; a notice for the Co.Ca. by any capo. Changed or removed by the author and
  the capigruppo.
- Addressed to the families and ragazzi of a unit or of the whole group, to the
  parents only or the ragazzi only, or to the capi (the Co.Ca.).
- Shown until the chosen day; past it only the capi see it, as an archive.
- On publishing, an optional email (a kind the reader may refuse, DEC-157).
- Attachments: PDF and images up to 10 MB, checked on their first bytes, random names,
  served only by the API. Online only.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import ModelloTracciato
from apps.organizzazione.models import Unita


class Destinatari(models.TextChoices):
    FAMIGLIE = "FAMIGLIE", "Famiglie e ragazzi"
    GENITORI = "GENITORI", "Solo i genitori"
    RAGAZZI = "RAGAZZI", "Solo i ragazzi"
    CAPI = "CAPI", "Comunità capi"


class Avviso(ModelloTracciato):
    titolo = models.CharField(max_length=160)
    testo = models.TextField()
    # Empty: the whole group.
    unita = models.ForeignKey(
        Unita, null=True, blank=True, on_delete=models.CASCADE, related_name="avvisi"
    )
    destinatari = models.CharField(max_length=8, choices=Destinatari.choices)
    # The last day it is shown.
    scade_il = models.DateField()
    autore = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    email_inviata_il = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "avviso"
        verbose_name_plural = "avvisi"
        ordering = ["-creato_il"]

    def __str__(self) -> str:
        return self.titolo

    def clean(self) -> None:
        if not self.titolo.strip() or not self.testo.strip():
            raise ValidationError("Scrivi il titolo e il testo dell'avviso.")
        if self.destinatari == Destinatari.CAPI and self.unita_id is not None:
            raise ValidationError("Gli avvisi per i capi sono per tutta la Comunità capi.")


class AllegatoAvviso(ModelloTracciato):
    avviso = models.ForeignKey(Avviso, on_delete=models.CASCADE, related_name="allegati")
    file = models.FileField(upload_to="bacheca/")
    tipo_file = models.CharField(max_length=30)
    # What it is, written by who uploads it (the original file name is not kept).
    titolo = models.CharField(max_length=120)

    class Meta:
        verbose_name = "allegato a un avviso"
        verbose_name_plural = "allegati agli avvisi"
        ordering = ["creato_il"]

    def __str__(self) -> str:
        return self.titolo
