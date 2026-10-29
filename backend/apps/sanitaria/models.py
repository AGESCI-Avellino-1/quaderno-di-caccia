"""Health essentials needed at camp (DEC-48 core, DEC-55, DEC-95).

Only medicines, allergies, intolerances and non-medical dietary needs live here,
anticipated to phase 1 because the capi need them offline at camp. The full medical form (tessera sanitaria, emergency
contacts, printing, signatures: DEC-48..DEC-54) is phase 5 and will extend this app.
"""

from django.conf import settings
from django.db import models

from apps.anagrafica.models import Persona
from apps.core.models import ModelloTracciato


class InseritoDa(models.TextChoices):
    """Who wrote the data (DEC-50, DEC-55): parents or the adult member in the app,
    or a capo transcribing the signed paper form."""

    GENITORE = "GENITORE", "Genitore"
    INTERESSATO = "INTERESSATO", "L'interessato (maggiorenne)"
    CAPO = "CAPO", "Capo (trascritto dalla scheda cartacea)"


class InformazioniSanitarie(ModelloTracciato):
    persona = models.OneToOneField(
        Persona, on_delete=models.CASCADE, related_name="informazioni_sanitarie"
    )
    # "Nessuna" is a statement, different from "not filled in yet": at camp the capo
    # must know which of the two it is.
    nessuna_allergia = models.BooleanField(default=False)
    nessun_farmaco = models.BooleanField(default=False)
    # Non-medical dietary needs (vegetarian, no pork…), DEC-49. A religious need is a
    # special category of data: kept here, with the same access rules and log as health
    # data (maintainer, 2026-10-29). The form asks for the need, not the reason.
    esigenze_alimentari = models.CharField(max_length=300, blank=True)
    aggiornate_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    inserite_da = models.CharField(max_length=12, choices=InseritoDa.choices)

    class Meta:
        verbose_name = "informazioni sanitarie essenziali"
        verbose_name_plural = "informazioni sanitarie essenziali"

    def __str__(self) -> str:
        return f"Informazioni sanitarie di {self.persona}"


class TipoAllergia(models.TextChoices):
    ALLERGIA = "ALLERGIA", "Allergia"
    INTOLLERANZA = "INTOLLERANZA", "Intolleranza"


class Gravita(models.TextChoices):
    """Degree of reaction (DEC-48)."""

    LIEVE = "LIEVE", "Lieve"
    MODERATA = "MODERATA", "Moderata"
    GRAVE = "GRAVE", "Grave (rischio per la vita)"


class Allergia(models.Model):
    informazioni = models.ForeignKey(
        InformazioniSanitarie, on_delete=models.CASCADE, related_name="allergie"
    )
    tipo = models.CharField(max_length=12, choices=TipoAllergia.choices)
    sostanza = models.CharField(max_length=120, help_text="Alimento, farmaco, insetto, polline…")
    gravita = models.CharField(max_length=8, choices=Gravita.choices)
    reazione = models.CharField(max_length=300, blank=True, help_text="Cosa succede.")
    cosa_fare = models.CharField(
        max_length=300, blank=True, help_text="Es. «adrenalina autoiniettabile nello zaino»."
    )

    class Meta:
        verbose_name = "allergia o intolleranza"
        verbose_name_plural = "allergie e intolleranze"
        ordering = ["pk"]

    def __str__(self) -> str:
        return f"{self.get_tipo_display()}: {self.sostanza}"


class Farmaco(models.Model):
    """Ongoing treatment (DEC-48: farmaco, posologia, orari, autonomia)."""

    informazioni = models.ForeignKey(
        InformazioniSanitarie, on_delete=models.CASCADE, related_name="farmaci"
    )
    nome = models.CharField(max_length=120)
    posologia = models.CharField(max_length=200)
    orari = models.CharField(max_length=200, blank=True)
    autonomo = models.BooleanField(
        default=False, help_text="Il ragazzo assume il farmaco da solo, senza un capo."
    )
    note = models.CharField(max_length=300, blank=True)

    class Meta:
        verbose_name = "farmaco"
        verbose_name_plural = "farmaci"
        ordering = ["pk"]

    def __str__(self) -> str:
        return self.nome
