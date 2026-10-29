"""Requests from data subjects: access, rectification, erasure, export (DEC-102).

The capigruppo answer them, as delegates of the controller, and pass them on to the
national office (DEC-98; maintainer, 2026-10-29). The register shows what was asked,
when, and when it was answered: the answer is due within a month (GDPR art. 12).
"""

from datetime import date, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.anagrafica.models import Persona
from apps.core.models import ModelloTracciato

TERMINE = timedelta(days=30)


class TipoRichiesta(models.TextChoices):
    ACCESSO = "ACCESSO", "Accesso ai dati"
    ESPORTAZIONE = "ESPORTAZIONE", "Copia dei dati (portabilità)"
    RETTIFICA = "RETTIFICA", "Rettifica"
    CANCELLAZIONE = "CANCELLAZIONE", "Cancellazione"
    ALTRO = "ALTRO", "Altro (limitazione, opposizione…)"


class RichiestaDiritti(ModelloTracciato):
    persona = models.ForeignKey(Persona, on_delete=models.PROTECT, related_name="richieste_diritti")
    tipo = models.CharField(max_length=13, choices=TipoRichiesta.choices)
    # Who asked: the member, a parent, a lawyer… in words, as received.
    richiedente = models.CharField(max_length=200)
    ricevuta_il = models.DateField()
    note = models.TextField(blank=True)
    inoltrata_nazionale_il = models.DateField(null=True, blank=True)
    evasa_il = models.DateField(null=True, blank=True)
    registrata_da = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        verbose_name = "richiesta di un interessato"
        verbose_name_plural = "richieste degli interessati"
        ordering = ["evasa_il", "ricevuta_il"]

    def __str__(self) -> str:
        return f"{self.get_tipo_display()} — {self.persona}"

    @property
    def scadenza(self) -> date:
        return self.ricevuta_il + TERMINE

    def clean(self) -> None:
        if not self.richiedente.strip():
            raise ValidationError("Indica chi ha fatto la richiesta.")
        oggi = date.today()
        if self.ricevuta_il and self.ricevuta_il > oggi:
            raise ValidationError("La data di ricezione non può essere nel futuro.")
        for campo, etichetta in (
            ("inoltrata_nazionale_il", "L'inoltro al nazionale"),
            ("evasa_il", "La chiusura"),
        ):
            valore = getattr(self, campo)
            if valore and self.ricevuta_il and valore < self.ricevuta_il:
                raise ValidationError(f"{etichetta} non può precedere la ricezione.")
            if valore and valore > oggi:
                raise ValidationError(f"{etichetta} non può essere nel futuro.")
