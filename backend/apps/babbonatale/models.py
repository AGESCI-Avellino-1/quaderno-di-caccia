"""Babbo Natale segreto (DEC-422).

Who gives a gift to whom (`Partecipante.a_chi`) is read only by the giver and, for a minor who
gets it through them, by their parents: never by the organisers or the capigruppo,
never in the audit log (not registered) or the logs. The one exception is
the Django admin, read only, for the technical administrator alone (`admin.py`, DEC-436). It is
kept in clear in the database (maintainer's choice, DEC-422).
"""

from datetime import date, timedelta

from django.conf import settings
from django.db import models

from apps.anagrafica.models import Persona
from apps.core.models import ModelloTracciato

# How long after the delivery a participant still sees the entry (DEC-422).
VISIBILE_DOPO = timedelta(days=30)
MINIMO_PARTECIPANTI = 3


class ScambioRegali(ModelloTracciato):
    """An exchange: a draft until the draw, then drawn, closed after the delivery day."""

    nome = models.CharField(max_length=120)
    # The unit whose staff manages it; none = the group's, managed by the capigruppo.
    unita = models.ForeignKey(
        "organizzazione.Unita",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="scambi_regali",
    )
    consegna_il = models.DateField()
    luogo = models.CharField(max_length=200, blank=True)
    creato_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    estratto_il = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "scambio di regali"
        verbose_name_plural = "scambi di regali"
        ordering = ["-consegna_il", "-pk"]

    def __str__(self) -> str:
        return self.nome

    @property
    def estratto(self) -> bool:
        return self.estratto_il is not None

    def chiuso(self, oggi: date | None = None) -> bool:
        """After the delivery day: nothing changes any more."""
        return (oggi or date.today()) > self.consegna_il

    def visibile_ai_partecipanti(self, oggi: date | None = None) -> bool:
        return self.estratto and (oggi or date.today()) <= self.consegna_il + VISIBILE_DOPO


class Partecipante(models.Model):
    """A participant; after the draw, who they give their gift to. Not a ModelloTracciato and
    not in the audit log: when it changed would tell who was moved (DEC-422)."""

    scambio = models.ForeignKey(
        ScambioRegali, on_delete=models.CASCADE, related_name="partecipanti"
    )
    persona = models.ForeignKey(Persona, on_delete=models.CASCADE, related_name="scambi_regali")
    a_chi = models.ForeignKey(
        Persona, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        verbose_name = "partecipante"
        verbose_name_plural = "partecipanti"
        constraints = [
            models.UniqueConstraint(fields=["scambio", "persona"], name="partecipante_unico"),
        ]

    def __str__(self) -> str:
        return f"Partecipante {self.pk}"
