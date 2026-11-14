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

    NUOVA = "N", "Nuova adesione"
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
    # From BuonaStrada, one of PROFESSIONI; seen by the person and the Co.Ca. (DEC-296).
    professione = models.CharField(max_length=100, blank=True)
    # A landline or work number, entered in the app (not in BuonaStrada): on the medical
    # form of every child (DEC-289).
    telefono_fisso = models.CharField(max_length=30, blank=True)
    stato_socio = models.CharField(max_length=1, choices=StatoSocio.choices, blank=True)
    # Consents imported from BuonaStrada (DEC-30, consents table in the requirements).
    consenso_iscrizione = models.BooleanField(null=True, blank=True)  # CONSENSO 2A
    consenso_foto = models.BooleanField(null=True, blank=True)  # CONSENSO 2B (confirmed 22/10)
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
    # Phone shown to the other members of the patrol (DEC-13, DEC-115),
    # see anagrafica.servizi.telefono_in_squadriglia: the child's own BuonaStrada mobile
    # if any, else the parent chosen for this child, else the parent chosen for all the
    # children without a phone. The number can be hidden from the members (never from
    # the CSQ).
    telefono_squadriglia_da = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Genitore di cui mostrare il cellulare in squadriglia, se manca il proprio.",
    )
    telefono_squadriglia_nascosto = models.BooleanField(default=False)
    # On a parent: their mobile is the patrol number of every child without one.
    telefono_per_i_figli = models.BooleanField(default=False)
    # A capo whose joining is complete outside the app, waiting only for BuonaStrada's
    # code: a capogruppo lets them in as if registered (DEC-400). Pointless once the code
    # is real; the import clears it.
    abilitato_come_censito_il = models.DateTimeField(null=True, blank=True)
    abilitato_come_censito_da = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

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
    "professione",
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

# Who may correct which field (DEC-31, DEC-129), see
# policy.campi_correggibili: contacts, address and consents also by the adult member
# themself; sex and place of birth by the unit staff too, not by the parents; the rest
# of identity only by the capigruppo.
# The values of BuonaStrada's PROFESSIONE (export of 2026): the choices of a correction. Not a
# constraint on the field: a new value from BuonaStrada is still imported (DEC-296).
PROFESSIONI = (
    "ALTRA ATTIVITA",
    "ALTRA LIBERA PROFESSIONE",
    "ARTIGIANO",
    "AVVOCATO",
    "COMMERCIANTE",
    "DIRIGENTE SETTORE PRIVATO",
    "DIRIGENTE SETTORE PUBBLICO",
    "DISOCCUPATO",
    "DOCENTE UNIVERSITARIO",
    "IMPIEGATO SETTORE PRIVATO CON ALTRE FORME CONTRATTUALI",
    "IMPIEGATO SETTORE PRIVATO TEMPO DETERMINATO",
    "IMPIEGATO SETTORE PRIVATO TEMPO INDETERMINATO",
    "IMPIEGATO SETTORE PUBBLICO CON ALTRE FORME CONTRATTUALI",
    "IMPIEGATO SETTORE PUBBLICO TEMPO DETERMINATO",
    "IMPIEGATO SETTORE PUBBLICO TEMPO INDETERMINATO",
    "INFERMIERE",
    "INSEGNANTE",
    "MEDICO",
    "OPERAIO",
    "PENSIONATO/A",
    "PRESBITERO",
    "PSICOLOGO",
    "RELIGIOSO/A",
    "STUDENTE SCUOLA SUPERIORE",
    "STUDENTE UNIVERSITARIO",
)


def e_presbitero(professione: str) -> bool:
    """Only a presbitero may be assistente ecclesiastico (DEC-296)."""
    testo = professione.casefold()
    return "presbitero" in testo or "sacerdote" in testo


CAMPI_CONTATTO = ("indirizzo", "civico", "comune", "provincia", "cap", "email", "cellulare")
CAMPI_CONSENSO = (
    "consenso_iscrizione",
    "consenso_foto",
    "consenso_commerciale",
    "consenso_riviste",
)
CAMPI_IDENTITA = ("nome", "cognome", "sesso", "data_nascita", "luogo_nascita", "codice_fiscale")
CAMPI_IDENTITA_STAFF = ("sesso", "luogo_nascita")

ETICHETTE_CAMPI = {
    "nome": "Nome",
    "cognome": "Cognome",
    "sesso": "Sesso",
    "data_nascita": "Data di nascita",
    "luogo_nascita": "Luogo di nascita",
    "codice_fiscale": "Codice fiscale",
    "indirizzo": "Indirizzo",
    "civico": "Numero civico",
    "comune": "Comune",
    "provincia": "Provincia",
    "cap": "CAP",
    "email": "Email",
    "cellulare": "Cellulare",
    "professione": "Professione",
    "stato_socio": "Stato del socio",
    "consenso_iscrizione": "Consenso per l'iscrizione (2A)",
    "consenso_foto": "Consenso per le foto (2B)",
    "consenso_commerciale": "Consenso commerciale (2C)",
    "consenso_riviste": "Consenso per le riviste",
    "livello_formazione": "Livello di formazione",
    "anno_ingresso_coca": "Anno di ingresso in Co.Ca.",
    "numero_nomina": "Numero di nomina a capo",
    "data_nomina": "Data di nomina a capo",
}


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


class PeriodoPercorso(ModelloTracciato):
    """A period of the scout path outside the app's units (DEC-287): in another group,
    from the BuonaStrada export or rebuilt by hand, or in this group before BuonaStrada
    (by hand). Group and unit are text: no unit of another group is created."""

    persona = models.ForeignKey(Persona, on_delete=models.CASCADE, related_name="periodi_percorso")
    # Empty: this group.
    gruppo = models.CharField(max_length=160, blank=True)
    unita = models.CharField(max_length=160)
    ruolo = models.CharField(max_length=10, choices=RuoloAppartenenza.choices)
    # Associative years by their end year, as BuonaStrada (2025/26 = 2026), both included.
    anno_inizio = models.PositiveSmallIntegerField()
    anno_fine = models.PositiveSmallIntegerField()
    fonte = models.CharField(
        max_length=12, choices=FonteDato.choices, default=FonteDato.RICOSTRUITO
    )
    registrato_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = "periodo del percorso scout"
        verbose_name_plural = "periodi del percorso scout"
        ordering = ["anno_inizio"]

    def __str__(self) -> str:
        return f"{self.persona}: {self.unita}, {self.anno_inizio}–{self.anno_fine}"

    def clean(self) -> None:
        from apps.core.anno import AnnoAssociativo

        if not self.unita.strip():
            raise ValidationError("Indica l'unità.")
        ultimo = AnnoAssociativo.corrente().anno_fine
        if not 1950 < self.anno_inizio <= self.anno_fine <= ultimo:
            raise ValidationError(
                "Controlla gli anni: il primo non può venire dopo l'ultimo, né dopo quello in corso."
            )


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
            raise ValidationError(f"{squadriglia} è archiviata.")
        if (
            not Appartenenza.objects.attive(self.data_inizio)
            .filter(persona=self.persona_id, unita=squadriglia.unita_id)
            .filter(ruolo=RuoloAppartenenza.RAGAZZO)
            .exists()
        ):
            raise ValidationError(f"{self.persona} non è un ragazzo/a di {squadriglia.unita}.")
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
    and recorded by a capogruppo (DEC-132).

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
    IN_ATTESA = "IN_ATTESA", "Da inoltrare alla segreteria"
    INOLTRATA = "INOLTRATA", "Inoltrata alla segreteria"
    RECEPITA = "RECEPITA", "Recepita da BuonaStrada"
    SUPERATA = "SUPERATA", "Superata da BuonaStrada"
    SCARTATA = "SCARTATA", "Scartata"


# Still "in attesa di BuonaStrada": the app value wins over imports (DEC-31).
STATI_APERTI = (StatoCorrezione.IN_ATTESA, StatoCorrezione.INOLTRATA)


class CorrezioneAnagrafica(ModelloTracciato):
    """A correction to a BuonaStrada-owned field made in the app (DEC-31).

    The corrected value is applied immediately to the Persona; while the correction
    is open, imports do not overwrite the field and report the difference. The
    capigruppo forward it to the regional office themselves and mark it INOLTRATA; the
    import closes it (RECEPITA) when BuonaStrada has the same value. A capogruppo may
    discard it (SCARTATA, with a reason): the previous value comes back.
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
    inoltrata_il = models.DateTimeField(null=True, blank=True)
    inoltrata_da = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    chiusa_il = models.DateTimeField(null=True, blank=True)
    chiusa_da = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    motivo_scarto = models.TextField(blank=True)
    # Set when the daily summary email to the capigruppo has mentioned it.
    segnalata_il = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "correzione anagrafica"
        verbose_name_plural = "correzioni anagrafiche"
        constraints = [
            models.UniqueConstraint(
                fields=["persona", "campo"],
                condition=Q(stato__in=["IN_ATTESA", "INOLTRATA"]),
                name="una_correzione_aperta_per_campo",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.persona}: {ETICHETTE_CAMPI.get(self.campo, self.campo)}"

    @property
    def aperta(self) -> bool:
        return self.stato in STATI_APERTI

    def clean(self) -> None:
        if self.campo not in CAMPI_BUONASTRADA:
            raise ValidationError(f"Il campo {self.campo} non è gestito da BuonaStrada.")
        if self.stato == StatoCorrezione.SCARTATA and not self.motivo_scarto.strip():
            raise ValidationError("Scrivi il motivo dello scarto.")


class VisibilitaGenitori(ModelloTracciato):
    """What the parents of an adult member still see (DEC-26).

    At 18 the R/S decides, by category, for all parents alike; until they do, the
    parents keep seeing everything (DEC-119). Parents never write the
    data of an adult.
    """

    persona = models.OneToOneField(
        Persona, on_delete=models.CASCADE, related_name="visibilita_genitori"
    )
    contatti = models.BooleanField(default=True, help_text="Contatti e indirizzo.")
    sanitarie = models.BooleanField(default=True, help_text="Farmaci, allergie, alimentazione.")
    scheda = models.BooleanField(
        default=True, help_text="Dati della scheda e attività (progressione, presenze)."
    )
    # DEC-26: the parent stays linked to the fees until the R/S unlinks them.
    quote = models.BooleanField(default=True, help_text="Quote, pagamenti e ricevute.")
    # At a meeting of the parents the adult member comes in their place (DEC-325).
    al_posto_dei_genitori = models.BooleanField(
        default=False, help_text="Alle riunioni dei genitori partecipa lui al loro posto."
    )
    decisa_il = models.DateTimeField(null=True, blank=True)
    # Alerts already sent (management command avvisa_maggiore_eta).
    avviso_mese_prima = models.DateField(null=True, blank=True)
    avviso_compleanno = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "visibilità ai genitori"
        verbose_name_plural = "visibilità ai genitori"

    def __str__(self) -> str:
        return f"Visibilità ai genitori di {self.persona}"


class ContatoreCodiceProvvisorio(models.Model):
    """Last provisional codice socio given to a member joining from the app, before
    BuonaStrada assigns the real one (DEC-122). A single row."""

    ultimo = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "contatore dei codici socio provvisori"

    def __str__(self) -> str:
        return f"Ultimo codice provvisorio: {self.ultimo}"


class PreferenzeEmail(ModelloTracciato):
    """Which of the optional emails a person receives (DEC-157: the right
    to object to communications based on the group's legitimate interest, GDPR art.
    21). On the person, not the account: parents get emails before they have one.
    Always sent, not listed here: access codes, invitations, security warnings, the
    registration from the app and the receipts of payments."""

    persona = models.OneToOneField(
        Persona, on_delete=models.CASCADE, related_name="preferenze_email"
    )
    eventi = models.BooleanField(default=True, help_text="Nuovi eventi, cambi, annullamenti.")
    promemoria_quote = models.BooleanField(default=True, help_text="Quote in scadenza.")
    maggiore_eta = models.BooleanField(default=True, help_text="Avvisi dei 18 anni.")
    riepiloghi = models.BooleanField(
        default=True, help_text="Riepiloghi per i capi: correzioni, iscrizioni da decidere."
    )
    avvisi = models.BooleanField(default=True, help_text="Avvisi della bacheca, documenti nuovi.")

    class Meta:
        verbose_name = "preferenze email"
        verbose_name_plural = "preferenze email"

    def __str__(self) -> str:
        return f"Email di {self.persona}"


class FotoProfilo(ModelloTracciato):
    """The profile photo, to recognise the ragazzi (DEC-42, DEC-201): the latest is the
    current one, the earlier ones stay for the capi. A JPEG of at most 1 MB under a
    random name, metadata dropped; served only by the API."""

    persona = models.ForeignKey(Persona, on_delete=models.CASCADE, related_name="foto_profilo")
    file = models.ImageField(upload_to="foto/")
    caricata_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = "foto profilo"
        verbose_name_plural = "foto profilo"
        ordering = ["-creato_il"]

    def __str__(self) -> str:
        return f"Foto di {self.persona}"
