"""Notes on a ragazzo (DEC-39, DEC-40) and the rules on the relationship with a minor
given by the parents (DEC-43).

- A staff note: the Co.Ca. always reads it; the staff may share it with the ragazzo,
  the parents and, in E/G only, the CSQ. "For everyone" means those three, never the
  other members of the patrol (DEC-39).
- A CSQ note on a member of their patrol: staff and Co.Ca. always read it; the CSQ
  chooses whether the member and the parents read it, and the staff may change that
  (DEC-40).
- Written by the unit staff and the capigruppo (DEC-197); changed or removed only by the
  author, the last write wins (DEC-96, DEC-198).
- The rules on the relationship with the minor are for the Co.Ca. only, shown in evidence
  and available offline at camp; every read is logged (DEC-43, DEC-95, DEC-199).

Not in the Django admin: it would bypass these rules.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.anagrafica.models import Persona
from apps.core.models import ModelloTracciato


class TipoNota(models.TextChoices):
    STAFF = "STAFF", "Nota di staff"
    CSQ = "CSQ", "Nota del capo squadriglia"


class Nota(ModelloTracciato):
    persona = models.ForeignKey(Persona, on_delete=models.CASCADE, related_name="note")
    tipo = models.CharField(max_length=6, choices=TipoNota.choices)
    testo = models.TextField()
    autore = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    # Who outside the Co.Ca. reads it.
    visibile_ragazzo = models.BooleanField(default=False)
    visibile_genitori = models.BooleanField(default=False)
    # Staff notes on an E/G only.
    visibile_csq = models.BooleanField(default=False)

    class Meta:
        verbose_name = "nota"
        verbose_name_plural = "note"
        ordering = ["-creato_il"]

    def __str__(self) -> str:
        return f"{self.get_tipo_display()} su {self.persona}"

    def clean(self) -> None:
        if not self.testo.strip():
            raise ValidationError("Scrivi la nota.")
        if self.tipo == TipoNota.CSQ and self.visibile_csq:
            raise ValidationError("Una nota del capo squadriglia la legge già il capo squadriglia.")

    @property
    def condivisa_fuori_coca(self) -> bool:
        """The app shows what goes beyond the Co.Ca. (DEC-39)."""
        return self.visibile_ragazzo or self.visibile_genitori or self.visibile_csq


class RegoleRapporto(ModelloTracciato):
    """What the parents indicated on the signed form about the relationship with the
    minor (e.g. after a separation), "valid until new written instructions"."""

    persona = models.OneToOneField(
        Persona, on_delete=models.CASCADE, related_name="regole_rapporto"
    )
    testo = models.TextField()
    registrate_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = "regole sul rapporto con il minore"
        verbose_name_plural = "regole sul rapporto con il minore"

    def __str__(self) -> str:
        return f"Regole sul rapporto con {self.persona}"
