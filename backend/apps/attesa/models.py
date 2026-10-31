import secrets

from django.conf import settings
from django.db import models

from apps.core.models import ModelloTracciato


def _token() -> str:
    return secrets.token_urlsafe(24)


class StatoAttesa(models.TextChoices):
    DA_CONTATTARE = "DA_CONTATTARE", "Da contattare"
    CONTATTATO = "CONTATTATO", "Contattato"


class InAttesa(ModelloTracciato):
    """Someone who wants to join the group (DEC-256): a child put on the list by a parent,
    an adult by themself, or anyone by a capo (DEC-258). Deleted when they leave the list,
    whatever the reason (DEC-263)."""

    nome = models.CharField(max_length=80)
    cognome = models.CharField(max_length=80)
    sesso = models.CharField(max_length=1, choices=[("M", "Maschio"), ("F", "Femmina")])
    data_nascita = models.DateField()
    luogo_nascita = models.CharField(max_length=120)
    # Who to contact: a parent, or the adult themself (then the names repeat).
    da_se = models.BooleanField(default=False)
    contatto_nome = models.CharField(max_length=80)
    contatto_cognome = models.CharField(max_length=80)
    telefono = models.CharField(max_length=30)
    email = models.EmailField()
    indirizzo = models.CharField(max_length=200)
    comune = models.CharField(max_length=120)
    provincia = models.CharField(max_length=2)
    cap = models.CharField(max_length=5)
    # The personal link to change or leave (DEC-257): a secret, never shown to the capi.
    token = models.CharField(max_length=40, unique=True, default=_token, editable=False)
    privacy_accettata_il = models.DateTimeField()
    inserito_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    stato = models.CharField(
        max_length=14, choices=StatoAttesa.choices, default=StatoAttesa.DA_CONTATTARE
    )
    contattato_per = models.ForeignKey(
        "organizzazione.Unita",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    contattato_il = models.DateField(null=True, blank=True)
    contattato_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    # The two-year question (DEC-262): last confirmation, when asked, the reminder.
    confermato_il = models.DateField(null=True, blank=True)
    conferma_chiesta_il = models.DateField(null=True, blank=True)
    promemoria_il = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "persona in lista d'attesa"
        verbose_name_plural = "lista d'attesa"
        ordering = ["creato_il"]

    def __str__(self) -> str:
        return f"{self.nome} {self.cognome}"


class ConteggioAttesa(models.Model):
    """What remains of the list, without names (DEC-263): per associative year, how many
    entered, joined the group, left."""

    anno = models.PositiveSmallIntegerField(unique=True)
    entrati = models.PositiveIntegerField(default=0)
    iscritti = models.PositiveIntegerField(default=0)
    usciti = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "conteggio della lista d'attesa"
        verbose_name_plural = "conteggi della lista d'attesa"

    def __str__(self) -> str:
        return f"Lista d'attesa {self.anno}"
