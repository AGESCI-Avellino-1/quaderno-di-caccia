"""The minutes of a meeting (DEC-322…DEC-331)."""

from django.conf import settings
from django.db import models

from apps.core.models import ModelloTracciato


class TipoVerbale(models.TextChoices):
    """Which meetings have minutes (DEC-322). Worked out from the meeting, never stored."""

    COCA = "COCA", "Comunità capi"
    SQUADRIGLIA = "SQUADRIGLIA", "Squadriglia"
    ALTA_SQUADRIGLIA = "ALTA_SQ", "Alta Squadriglia"
    CONSIGLIO_CAPI = "CONCA", "Consiglio Capi"
    CONSIGLIO_CAPI_VICE = "CONCAVI", "Consiglio Capi e Vice"
    GENITORI = "GENITORI", "Riunione dei genitori"


class StatoVerbale(models.TextChoices):
    BOZZA = "BOZZA", "Bozza"
    DEFINITIVO = "DEFINITIVO", "Definitivo"


class Verbale(ModelloTracciato):
    # PROTECT: meetings are cancelled, never deleted, and minutes are not lost with them.
    evento = models.OneToOneField("eventi.Evento", on_delete=models.PROTECT, related_name="verbale")
    # HTML cleaned on the server. Never in the audit log (DEC-329).
    testo = models.TextField(blank=True)
    stato = models.CharField(
        max_length=10, choices=StatoVerbale.choices, default=StatoVerbale.BOZZA
    )
    # "There are no minutes for this meeting": stops the reminders (DEC-322, DEC-331).
    non_previsto = models.BooleanField(default=False)
    # Who was chosen to write them, for this meeting only (DEC-324).
    redattore = models.ForeignKey(
        "anagrafica.Persona", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    # Who wrote them last, also as a name: it signs the PDF and may have to outlive the
    # person's erasure for five years (DEC-324, DEC-328).
    autore = models.ForeignKey(
        "anagrafica.Persona", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    autore_nome = models.CharField(max_length=200, blank=True)
    # The name kept only for the five years (DEC-328): to be removed when they are over.
    nome_a_scadenza = models.BooleanField(default=False)
    definitivo_il = models.DateTimeField(null=True, blank=True)
    definitivo_da = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    # The last reopening: its reason stays in the audit log (DEC-324).
    riaperto_il = models.DateTimeField(null=True, blank=True)
    motivo_riapertura = models.CharField(max_length=300, blank=True)
    # Reminders sent (DEC-331).
    promemoria_inviati = models.PositiveSmallIntegerField(default=0)
    ultimo_promemoria = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "verbale"
        verbose_name_plural = "verbali"

    def __str__(self) -> str:
        return f"Verbale di {self.evento}"

    @property
    def definitivo(self) -> bool:
        return self.stato == StatoVerbale.DEFINITIVO


class AllegatoVerbale(ModelloTracciato):
    """A file of the minutes, on the group's Drive or, without one, on the server (DEC-330).
    Incomplete until its last piece arrives: nobody sees it before."""

    verbale = models.ForeignKey(Verbale, on_delete=models.CASCADE, related_name="allegati")
    nome_file = models.CharField(max_length=200)
    tipo_file = models.CharField(max_length=120)
    dimensione = models.BigIntegerField()
    ricevuti = models.BigIntegerField(default=0)
    completo = models.BooleanField(default=False)
    # Sent with the convocation and read by who is invited, before any minutes (DEC-327).
    di_convocazione = models.BooleanField(default=False)
    drive_id = models.CharField(max_length=120, blank=True)
    # Where the pieces go while uploading: a secret address, emptied at the end.
    sessione = models.TextField(blank=True)
    file = models.FileField(upload_to="verbali/", blank=True)
    caricato_da = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        verbose_name = "allegato di un verbale"
        verbose_name_plural = "allegati dei verbali"
        ordering = ["creato_il"]

    def __str__(self) -> str:
        return self.nome_file
