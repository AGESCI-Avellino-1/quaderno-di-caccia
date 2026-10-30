"""The capi's file (DEC-47, DEC-134, DEC-206…DEC-208): what the app cannot work out by
itself. The years of service from the app on come from the roles (`Incarico`); before,
they are entered by hand, year by year, marked as rebuilt. Training is entered by hand
by the capo or a capogruppo; BuonaStrada gives only the level, and the camps recorded
as BuonaCaccia events show by themselves."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.anagrafica.models import Persona
from apps.buonacaccia.models import TipoCampoFormazione
from apps.core.date_parziali import PrecisioneData
from apps.core.models import ModelloTracciato


class RuoloPassato(models.TextChoices):
    CAPO_UNITA = "CAPO_UNITA", "Capo unità"
    STAFF = "STAFF", "Staff di unità"
    CAPOGRUPPO = "CAPOGRUPPO", "Capogruppo"
    TESORIERE = "TESORIERE", "Tesoriere"
    A_DISPOSIZIONE = "A_DISPOSIZIONE", "A disposizione"
    ALTRO = "ALTRO", "Altro"


class ServizioPassato(ModelloTracciato):
    """A year of service before the app, rebuilt by hand (DEC-46, DEC-207)."""

    persona = models.ForeignKey(Persona, on_delete=models.CASCADE, related_name="servizi_passati")
    # The associative year by its end year, as BuonaStrada (2025/26 = 2026).
    anno = models.PositiveSmallIntegerField()
    unita = models.ForeignKey(
        "organizzazione.Unita", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    # A unit that is not (or no longer) in the app.
    unita_testo = models.CharField(max_length=120, blank=True)
    ruolo = models.CharField(max_length=16, choices=RuoloPassato.choices)
    note = models.CharField(max_length=300, blank=True)
    registrato_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = "anno di servizio ricostruito"
        verbose_name_plural = "anni di servizio ricostruiti"
        ordering = ["-anno"]

    def __str__(self) -> str:
        return f"{self.persona}, {self.anno}"

    def clean(self) -> None:
        if self.ruolo == RuoloPassato.ALTRO and not self.note.strip():
            raise ValidationError("Scrivi quale ruolo nelle note.")


class Formazione(ModelloTracciato):
    """A training camp or module, entered by hand (DEC-134, DEC-208)."""

    persona = models.ForeignKey(Persona, on_delete=models.CASCADE, related_name="formazione")
    tipo = models.CharField(max_length=8, choices=TipoCampoFormazione.choices)
    # The title of a module, or what "other" is.
    specifica = models.CharField(max_length=160, blank=True)
    data = models.DateField()
    precisione = models.CharField(
        max_length=6, choices=PrecisioneData.choices, default=PrecisioneData.GIORNO
    )
    luogo = models.CharField(max_length=120, blank=True)
    note = models.CharField(max_length=300, blank=True)
    registrata_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = "formazione"
        verbose_name_plural = "formazione"
        ordering = ["-data"]

    def __str__(self) -> str:
        return f"{self.get_tipo_display()} di {self.persona}"

    def clean(self) -> None:
        if self.tipo in (TipoCampoFormazione.MODULO, TipoCampoFormazione.ALTRO) and not (
            self.specifica.strip()
        ):
            raise ValidationError(
                "Scrivi il titolo del modulo."
                if self.tipo == TipoCampoFormazione.MODULO
                else "Specifica che tipo di formazione è."
            )
