"""Users and invitations (DEC-21, DEC-24)."""

import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.core.models import ModelloTracciato


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **extra):
        if not email:
            raise ValueError("L'email è obbligatoria.")
        user = self.model(email=self.normalize_email(email), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra)

    def create_superuser(self, email: str, password: str | None = None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("amministratore_tecnico", True)
        return self._create_user(email, password, **extra)


class User(AbstractUser):
    """Email-based user. Domain data lives on anagrafica.Persona (user.persona)."""

    username = None
    email = models.EmailField("email", unique=True)
    # Technical administrator: catalogs, imports, accounts (DEC-12).
    amministratore_tecnico = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    objects = UserManager()

    class Meta:
        verbose_name = "utente"
        verbose_name_plural = "utenti"

    def __str__(self) -> str:
        return self.email


def _nuovo_token() -> str:
    return secrets.token_urlsafe(32)


def _scadenza_predefinita():
    return timezone.now() + timedelta(days=settings.QDC_INVITO_VALIDITA_GIORNI)


class MetodoVerificaGenitore(models.TextChoices):
    """How the app verified that the consent came from a parent (DEC-24)."""

    ACCOUNT_GENITORE = "ACCOUNT_GENITORE", "Dall'account del genitore collegato"
    IN_PRESENZA = "IN_PRESENZA", "In presenza, davanti a un capo"
    MODULO_FIRMATO = "MODULO_FIRMATO", "Modulo firmato consegnato"


class Invito(ModelloTracciato):
    """Invitation that opens sign-up for one email and links the account to a Persona."""

    email = models.EmailField()
    persona = models.ForeignKey(
        "anagrafica.Persona", on_delete=models.CASCADE, related_name="inviti"
    )
    token = models.CharField(max_length=64, unique=True, default=_nuovo_token, editable=False)
    scadenza = models.DateTimeField(default=_scadenza_predefinita)
    creato_da = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    usato_il = models.DateTimeField(null=True, blank=True)
    # Parental consent, mandatory for members under 14 (DEC-24, art. 2-quinquies).
    consenso_genitore_da = models.ForeignKey(
        "anagrafica.Persona",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="consensi_dati",
    )
    consenso_genitore_il = models.DateTimeField(null=True, blank=True)
    consenso_genitore_metodo = models.CharField(
        max_length=20, choices=MetodoVerificaGenitore.choices, blank=True
    )

    class Meta:
        verbose_name = "invito"
        verbose_name_plural = "inviti"

    def __str__(self) -> str:
        return f"Invito per {self.email}"

    @property
    def valido(self) -> bool:
        return self.usato_il is None and self.scadenza > timezone.now()

    def richiede_consenso_genitore(self) -> bool:
        eta = self.persona.eta()
        return eta is not None and eta < 14

    def clean(self) -> None:
        if self.richiede_consenso_genitore():
            if not (
                self.consenso_genitore_da_id
                and self.consenso_genitore_il
                and self.consenso_genitore_metodo
            ):
                raise ValidationError(
                    "Sotto i 14 anni serve il consenso del genitore: chi, quando e come "
                    "è stato verificato."
                )
            if not self.persona.tutori.filter(
                tutore_id=self.consenso_genitore_da_id, responsabilita_genitoriale=True
            ).exists():
                raise ValidationError(
                    "Il consenso deve venire da chi esercita la responsabilità genitoriale."
                )
            if (
                self.consenso_genitore_metodo == MetodoVerificaGenitore.ACCOUNT_GENITORE
                and self.consenso_genitore_da
                and self.consenso_genitore_da.utente_id is None
            ):
                raise ValidationError(
                    "Questo genitore non ha un account: indica come è stato verificato."
                )
