"""People and their memberships over time (DEC-27..DEC-37, DEC-57).

A Persona is a stable identity for the whole life in the group. Memberships of
units and patrols are periods, never overwritten (DEC-57).
"""

from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.core.anno import eta_in_data
from apps.core.models import FonteDato, ModelloTracciato


class StatoSocio(models.TextChoices):
    """BuonaStrada 'CODICE STATUS SOCIO' (DEC-28)."""

    RINNOVO = "R", "Rinnovo adesione"
    SOSPESO = "S", "Sospeso (in attesa di rinnovo)"
    DECADUTO = "D", "Sospeso da più di un anno"


class Persona(ModelloTracciato):
    # --- Owned by BuonaStrada (DEC-30) -------------------------------------------
    codice_socio = models.CharField(max_length=10, unique=True, null=True, blank=True)
    nome = models.CharField(max_length=80)
    cognome = models.CharField(max_length=80)
    sesso = models.CharField(max_length=1, choices=[("M", "M"), ("F", "F")], blank=True)
    data_nascita = models.DateField(null=True, blank=True)
    luogo_nascita = models.CharField(max_length=120, blank=True)
    codice_fiscale = models.CharField(max_length=16, unique=True, null=True, blank=True)
    indirizzo = models.CharField(max_length=200, blank=True)
    civico = models.CharField(max_length=20, blank=True)
    comune = models.CharField(max_length=120, blank=True)
    provincia = models.CharField(max_length=2, blank=True)
    cap = models.CharField(max_length=5, blank=True)
    email = models.EmailField(blank=True)
    cellulare = models.CharField(max_length=30, blank=True)
    stato_socio = models.CharField(max_length=1, choices=StatoSocio.choices, blank=True)
    # Consents imported from BuonaStrada (DEC-30, consents table in the requirements).
    consenso_iscrizione = models.BooleanField(null=True, blank=True)  # CONSENSO 2A
    consenso_foto = models.BooleanField(null=True, blank=True)  # CONSENSO 2B [da verificare]
    consenso_commerciale = models.BooleanField(null=True, blank=True)  # CONSENSO 2C
    consenso_riviste = models.BooleanField(null=True, blank=True)  # CONSENSO RIVISTE
    # Leader data (DEC-35).
    livello_formazione = models.PositiveSmallIntegerField(null=True, blank=True)
    anno_ingresso_coca = models.PositiveSmallIntegerField(null=True, blank=True)
    numero_nomina = models.CharField(max_length=20, blank=True)
    data_nomina = models.DateField(null=True, blank=True)

    # --- Owned by the app -----------------------------------------------------------
    utente = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="persona",
    )
    ultima_importazione = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "persona"
        verbose_name_plural = "persone"
        ordering = ["cognome", "nome"]

    def __str__(self) -> str:
        return f"{self.cognome} {self.nome}"

    @property
    def e_socio(self) -> bool:
        return bool(self.codice_socio)

    def eta(self, al_giorno: date | None = None) -> int | None:
        if not self.data_nascita:
            return None
        return eta_in_data(self.data_nascita, al_giorno or date.today())

    def e_minorenne(self, al_giorno: date | None = None) -> bool:
        eta = self.eta(al_giorno)
        return eta is not None and eta < 18


# Fields that BuonaStrada owns: imports update them unless a correction is pending.
CAMPI_BUONASTRADA = (
    "nome",
    "cognome",
    "sesso",
    "data_nascita",
    "luogo_nascita",
    "codice_fiscale",
    "indirizzo",
    "civico",
    "comune",
    "provincia",
    "cap",
    "email",
    "cellulare",
    "stato_socio",
    "consenso_iscrizione",
    "consenso_foto",
    "consenso_commerciale",
    "consenso_riviste",
    "livello_formazione",
    "anno_ingresso_coca",
    "numero_nomina",
    "data_nomina",
)


class TipoTutela(models.TextChoices):
    GENITORE = "GENITORE", "Genitore"
    UNICO_GENITORE = "UNICO_GENITORE", "Unico genitore"
    TUTORE = "TUTORE", "Tutore"


class RelazioneTutela(ModelloTracciato):
    """Parent/guardian of a member. Siblings share a guardian with the same
    codice fiscale (DEC-33)."""

    tutore = models.ForeignKey(Persona, on_delete=models.CASCADE, related_name="tutele")
    minore = models.ForeignKey(Persona, on_delete=models.CASCADE, related_name="tutori")
    tipo = models.CharField(max_length=20, choices=TipoTutela.choices)
    # A parent without parental responsibility has no account (DEC-16).
    responsabilita_genitoriale = models.BooleanField(default=True)
    fonte = models.CharField(max_length=12, choices=FonteDato.choices, default=FonteDato.APP)

    class Meta:
        verbose_name = "relazione di tutela"
        verbose_name_plural = "relazioni di tutela"
        constraints = [
            models.UniqueConstraint(fields=["tutore", "minore"], name="tutela_unica"),
            models.CheckConstraint(
                condition=~Q(tutore=models.F("minore")), name="tutela_non_riflessiva"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.tutore} → {self.minore}"


class RuoloAppartenenza(models.TextChoices):
    RAGAZZO = "RAGAZZO", "Ragazzo/a"
    CAPO = "CAPO", "Capo"


class AppartenenzaQuerySet(models.QuerySet):
    def attive(self, al_giorno: date | None = None):
        giorno = al_giorno or date.today()
        return self.filter(data_inizio__lte=giorno).filter(
            Q(data_fine__isnull=True) | Q(data_fine__gt=giorno)
        )


class Appartenenza(ModelloTracciato):
    """Membership of a unit for a period (end date exclusive, null = ongoing)."""

    persona = models.ForeignKey(Persona, on_delete=models.CASCADE, related_name="appartenenze")
    unita = models.ForeignKey(
        "organizzazione.Unita", on_delete=models.PROTECT, related_name="appartenenze"
    )
    ruolo = models.CharField(max_length=10, choices=RuoloAppartenenza.choices)
    data_inizio = models.DateField()
    data_fine = models.DateField(null=True, blank=True)
    fonte = models.CharField(max_length=12, choices=FonteDato.choices, default=FonteDato.APP)

    objects = AppartenenzaQuerySet.as_manager()

    class Meta:
        verbose_name = "appartenenza"
        verbose_name_plural = "appartenenze"
        ordering = ["-data_inizio"]

    def __str__(self) -> str:
        return f"{self.persona} in {self.unita} ({self.get_ruolo_display()})"

    def clean(self) -> None:
        if self.data_fine and self.data_fine <= self.data_inizio:
            raise ValidationError("La data di fine deve seguire quella di inizio.")


class AppartenenzaSquadriglia(ModelloTracciato):
    """Patrol membership; patrols are per year and may change mid-year (DEC-65)."""

    persona = models.ForeignKey(
        Persona, on_delete=models.CASCADE, related_name="appartenenze_squadriglia"
    )
    squadriglia = models.ForeignKey(
        "organizzazione.Squadriglia", on_delete=models.PROTECT, related_name="membri"
    )
    data_inizio = models.DateField()
    data_fine = models.DateField(null=True, blank=True)

    objects = AppartenenzaQuerySet.as_manager()

    class Meta:
        verbose_name = "appartenenza a squadriglia"
        verbose_name_plural = "appartenenze a squadriglia"


class StatoCorrezione(models.TextChoices):
    IN_ATTESA = "IN_ATTESA", "In attesa di BuonaStrada"
    RECEPITA = "RECEPITA", "Recepita da BuonaStrada"
    SCARTATA = "SCARTATA", "Scartata"


class CorrezioneAnagrafica(ModelloTracciato):
    """A correction to a BuonaStrada-owned field made in the app (DEC-31).

    The corrected value is applied immediately to the Persona; while the correction
    is pending, imports do not overwrite the field and report the difference.
    """

    persona = models.ForeignKey(Persona, on_delete=models.CASCADE, related_name="correzioni")
    campo = models.CharField(max_length=40)
    valore_precedente = models.TextField(blank=True)
    valore_corretto = models.TextField(blank=True)
    stato = models.CharField(
        max_length=10, choices=StatoCorrezione.choices, default=StatoCorrezione.IN_ATTESA
    )
    richiesta_da = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        verbose_name = "correzione anagrafica"
        verbose_name_plural = "correzioni anagrafiche"
        constraints = [
            models.UniqueConstraint(
                fields=["persona", "campo"],
                condition=Q(stato="IN_ATTESA"),
                name="una_correzione_in_attesa_per_campo",
            ),
        ]

    def clean(self) -> None:
        if self.campo not in CAMPI_BUONASTRADA:
            raise ValidationError(f"Il campo {self.campo} non è gestito da BuonaStrada.")
