"""The Download page (DEC-341, DEC-342): documents of the group, and the Progetto Educativo di
Gruppo with its history (DEC-343, DEC-344). Who reads and who writes: apps.permessi.policy."""

from datetime import date, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.core.anno import AnnoAssociativo
from apps.core.models import ModelloTracciato

GIORNI_AGGIORNATO = 7  # DEC-342


class Durata(models.TextChoices):
    ANNO = "ANNO", "Per un anno associativo"
    DATA = "DATA", "Fino a una data"
    SEMPRE = "SEMPRE", "Finché non viene eliminato"


class Documento(ModelloTracciato):
    titolo = models.CharField(max_length=160)
    descrizione = models.CharField(max_length=500)
    # A random name on disk: the original may contain someone's.
    file = models.FileField(upload_to="documenti/")
    nome_file = models.CharField(max_length=200)
    tipo_file = models.CharField(max_length=120)
    dimensione = models.BigIntegerField()
    durata = models.CharField(max_length=6, choices=Durata.choices)
    # With ANNO, labelled by its end year as everywhere; with DATA, the last day.
    anno = models.PositiveSmallIntegerField(null=True, blank=True)
    scade_il = models.DateField(null=True, blank=True)
    # Who reads it, besides the capi (DEC-341). Parents of the units only when they are chosen.
    per_coca = models.BooleanField(default=False)
    per_genitori = models.BooleanField(default=False)
    unita = models.ManyToManyField("organizzazione.Unita", blank=True, related_name="documenti")
    unita_ragazzi = models.BooleanField(default=False)
    unita_genitori = models.BooleanField(default=False)
    # Only when the file changes, never for the other fields (DEC-342).
    file_cambiato_il = models.DateTimeField(null=True, blank=True)
    autore = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    # Told once that it is about to go (DEC-346); a new last day starts again.
    avvisato_scadenza_il = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "documento"
        verbose_name_plural = "documenti"
        ordering = ["titolo"]

    def __str__(self) -> str:
        return self.titolo

    @property
    def ultimo_giorno(self) -> date | None:
        if self.durata == Durata.ANNO and self.anno:
            return AnnoAssociativo(self.anno).fine
        return self.scade_il if self.durata == Durata.DATA else None

    @property
    def aggiornato(self) -> bool:
        if self.file_cambiato_il is None:
            return False
        return timezone.now() - self.file_cambiato_il < timedelta(days=GIORNI_AGGIORNATO)


class VersionePeg(ModelloTracciato):
    """The latest loaded is in force until a new one comes: not tied to a year (DEC-343)."""

    # One of the two: a PDF (preferred) or the text from the editor.
    file = models.FileField(upload_to="peg/", blank=True)
    nome_file = models.CharField(max_length=200, blank=True)
    dimensione = models.BigIntegerField(default=0)
    testo = models.TextField(blank=True)
    # The day the Co.Ca. approved it, and the length it gave itself: «2026/2029».
    approvato_il = models.DateField()
    durata = models.CharField(max_length=40, blank=True)
    caricata_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        verbose_name = "versione del Progetto Educativo di Gruppo"
        verbose_name_plural = "versioni del Progetto Educativo di Gruppo"
        ordering = ["-creato_il", "-pk"]

    def __str__(self) -> str:
        return f"Progetto Educativo di Gruppo del {self.approvato_il:%d/%m/%Y}"


class VersioneCriteri(ModelloTracciato):
    """The admission criteria of an associative year, as the Co.Ca. decided them (DEC-355). A
    change is a new version, from a day of the year; the others stay, each valid until the
    next one begins (DEC-356)."""

    # By its end year, as everywhere (2025/26 = 2026).
    anno = models.PositiveSmallIntegerField()
    valida_dal = models.DateField()
    verbale_numero = models.CharField(max_length=30)
    verbale_data = models.DateField()
    # HTML cleaned by the server.
    testo = models.TextField()
    caricata_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        verbose_name = "versione dei criteri di ammissione"
        verbose_name_plural = "versioni dei criteri di ammissione"
        ordering = ["-anno", "-valida_dal"]
        constraints = [
            models.UniqueConstraint(
                fields=["anno", "valida_dal"], name="criteri_un_inizio_per_giorno"
            ),
        ]

    def __str__(self) -> str:
        return f"Criteri {self.anno}, dal {self.valida_dal:%d/%m/%Y}"

    def clean(self) -> None:
        if not self.anno or not self.valida_dal:
            return
        if not AnnoAssociativo(self.anno).contiene(self.valida_dal):
            raise ValidationError(
                f"La data di inizio deve stare nell'anno {AnnoAssociativo(self.anno).etichetta}."
            )
        if not self.testo.strip():
            raise ValidationError("Scrivi il testo dei criteri.")


class MassimoUnita(ModelloTracciato):
    """The maximum of ragazzi of a unit in a version of the criteria; none = no limit. It warns
    who approves a request and stops nothing (DEC-358)."""

    versione = models.ForeignKey(VersioneCriteri, on_delete=models.CASCADE, related_name="massimi")
    unita = models.ForeignKey("organizzazione.Unita", on_delete=models.CASCADE, related_name="+")
    massimo = models.PositiveSmallIntegerField()

    class Meta:
        verbose_name = "numero massimo di un'unità"
        verbose_name_plural = "numeri massimi delle unità"
        constraints = [
            models.UniqueConstraint(fields=["versione", "unita"], name="criteri_massimo_unico"),
        ]

    def __str__(self) -> str:
        return f"{self.unita}: {self.massimo}"
