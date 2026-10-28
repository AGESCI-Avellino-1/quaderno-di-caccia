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

    def __str__(self) -> str:
        return f"{self.persona} in {self.squadriglia}"

    def clean(self) -> None:
        if self.data_fine and self.data_fine <= self.data_inizio:
            raise ValidationError("La data di fine deve seguire quella di inizio.")
        if not self._state.adding:
            return  # closing stays possible after the person left the reparto
        squadriglia = self.squadriglia
        if not squadriglia.attiva:
            raise ValidationError(f"{squadriglia} è chiusa.")
        if (
            not Appartenenza.objects.attive(self.data_inizio)
            .filter(persona=self.persona_id, unita=squadriglia.unita_id)
            .filter(ruolo=RuoloAppartenenza.RAGAZZO)
            .exists()
        ):
            raise ValidationError(
                f"{self.persona} non è un ragazzo o una ragazza di {squadriglia.unita}."
            )
        # One patrol at a time: a change closes the previous membership first.
        if (
            AppartenenzaSquadriglia.objects.attive(self.data_inizio)
            .filter(persona=self.persona_id)
            .exclude(pk=self.pk)
            .exists()
        ):
            raise ValidationError(f"{self.persona} è già in una squadriglia.")
        # Patrols are single-sex. A missing sex (not in BuonaStrada) does not block: the
        # unit page reports it instead.
        persona = self.persona
        if (
            persona.sesso
            and persona.sesso != squadriglia.sesso
            and not DerogaSquadriglia.objects.valide(self.data_inizio)
            .filter(
                persona=persona,
                reparto=squadriglia.unita_id,
                sesso_squadriglia=squadriglia.sesso,
            )
            .exists()
        ):
            raise ValidationError(
                f"{squadriglia} è {squadriglia.get_sesso_display().lower()}: per inserire "
                f"{persona} serve un'eccezione decisa dalla Co.Ca. e registrata da un "
                "capogruppo."
            )


class DerogaQuerySet(models.QuerySet):
    def valide(self, al_giorno: date | None = None):
        """Not revoked, and the person is still a ragazzo of that reparto: the exception
        lasts as long as they stay there."""
        giorno = al_giorno or date.today()
        nel_reparto = Appartenenza.objects.attive(giorno).filter(
            persona=models.OuterRef("persona"),
            unita=models.OuterRef("reparto"),
            ruolo=RuoloAppartenenza.RAGAZZO,
        )
        return (
            self.filter(data_decisione__lte=giorno)
            .filter(Q(revocata_il__isnull=True) | Q(revocata_il__gt=giorno))
            .filter(models.Exists(nel_reparto))
        )


class DerogaSquadriglia(ModelloTracciato):
    """Exception to single-sex patrols (gender identity, transition), decided by the Co.Ca.
    and recorded by a capogruppo. Decided with the maintainer on 2026-10-28, not yet in the
    analysis (see TODO.md).

    Special-category data (GDPR art. 9), handled like health data: not in the Django admin,
    `motivazione` excluded from the audit log, reads and changes in the access log (DEC-101),
    never cached on devices. Visible to the capi only.
    """

    persona = models.ForeignKey(
        Persona, on_delete=models.CASCADE, related_name="deroghe_squadriglia"
    )
    reparto = models.ForeignKey("organizzazione.Unita", on_delete=models.PROTECT, related_name="+")
    # The patrols the person may join: "F" = female patrols.
    sesso_squadriglia = models.CharField(
        max_length=1, choices=[("M", "Maschili"), ("F", "Femminili")]
    )
    # Date of the Co.Ca. meeting that decided it.
    data_decisione = models.DateField()
    motivazione = models.TextField()
    registrata_da = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    # Exclusive like every period end; null = in force.
    revocata_il = models.DateField(null=True, blank=True)

    objects = DerogaQuerySet.as_manager()

    class Meta:
        verbose_name = "eccezione sulla squadriglia"
        verbose_name_plural = "eccezioni sulla squadriglia"

    def __str__(self) -> str:
        # No reason here: __str__ ends up in logs and in the audit log.
        return f"Eccezione sulla squadriglia per {self.persona}"

    def clean(self) -> None:
        from apps.organizzazione.models import TipoUnita

        if self.reparto_id and self.reparto.tipo != TipoUnita.REPARTO:
            raise ValidationError("Le squadriglie esistono solo nei reparti.")
        if not self.motivazione.strip():
            raise ValidationError("Scrivi la motivazione decisa dalla Co.Ca.")
        if self.data_decisione and self.data_decisione > date.today():
            raise ValidationError("La decisione della Co.Ca. non può essere nel futuro.")
        if self.revocata_il and self.revocata_il <= self.data_decisione:
            raise ValidationError("La revoca deve seguire la decisione.")


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
