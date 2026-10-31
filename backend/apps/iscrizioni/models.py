"""New members joining from the app (DEC-120…DEC-127).

A capo hands out a registration code (QR code, link or the code itself): reusable for
a unit for a period (e.g. an open day) or personal and single use. Whoever uses it
asks to join that unit: a parent for a minor, the adult member for themself. The unit
staff, or a capogruppo (only a capogruppo for the Co.Ca.), approves the request: the
member gets a provisional codice socio until the group enters them in BuonaStrada.
"""

import secrets
from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.anagrafica.models import Persona
from apps.core.models import ModelloTracciato
from apps.organizzazione.models import TipoUnita, Unita

# No 0/O, 1/I/L: the code may be typed by hand from a poster.
ALFABETO = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
LUNGHEZZA_CODICE = 8


def _nuovo_codice() -> str:
    return "".join(secrets.choice(ALFABETO) for _ in range(LUNGHEZZA_CODICE))


def normalizza_codice(testo: str) -> str:
    return "".join(c for c in testo.upper() if c.isalnum())


class TipoCodice(models.TextChoices):
    UNITA = "UNITA", "Per l'unità (più persone, fino alla scadenza)"
    PERSONALE = "PERSONALE", "Personale (una sola iscrizione)"


class CodiceIscrizione(ModelloTracciato):
    codice = models.CharField(max_length=12, unique=True, default=_nuovo_codice, editable=False)
    unita = models.ForeignKey(Unita, on_delete=models.PROTECT, related_name="codici_iscrizione")
    tipo = models.CharField(max_length=10, choices=TipoCodice.choices)
    scadenza = models.DateField()
    usi = models.PositiveIntegerField(default=0)
    attivo = models.BooleanField(default=True)
    creato_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    # A personal code from the waiting list (DEC-261): its data, to fill in the form and,
    # at the approval, the new member's card; emptied then.
    dati_proposti = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "codice di iscrizione"
        verbose_name_plural = "codici di iscrizione"
        ordering = ["-creato_il"]

    def __str__(self) -> str:
        return f"{self.codice} ({self.unita})"

    @property
    def per_capi(self) -> bool:
        return self.unita.tipo == TipoUnita.COMUNITA_CAPI

    @property
    def valido(self) -> bool:
        if not self.attivo or self.scadenza < date.today() or not self.unita.attiva:
            return False
        return self.tipo != TipoCodice.PERSONALE or self.usi == 0

    def clean(self) -> None:
        if self.scadenza and self._state.adding and self.scadenza < date.today():
            raise ValidationError("La scadenza non può essere nel passato.")


class StatoIscrizione(models.TextChoices):
    IN_ATTESA = "IN_ATTESA", "In attesa di approvazione"
    APPROVATA = "APPROVATA", "Accolta: dati e moduli da completare"
    SOSPESA = "SOSPESA", "Sospesa: scaduto il termine per completare"
    COMPLETATA = "COMPLETATA", "Completa: da inserire in BuonaStrada"
    INSERITA = "INSERITA", "Inserita in BuonaStrada: in attesa dell'importazione"
    RECEPITA = "RECEPITA", "In BuonaStrada, con il codice socio definitivo"
    RIFIUTATA = "RIFIUTATA", "Non accolta"


# Accepted but not yet complete: the family still has something to do.
DA_COMPLETARE = (StatoIscrizione.APPROVATA, StatoIscrizione.SOSPESA)
# Accepted and not yet found in a BuonaStrada import.
NON_RECEPITE = (*DA_COMPLETARE, StatoIscrizione.COMPLETATA, StatoIscrizione.INSERITA)

# What BuonaStrada requires to enter a member (DEC-124): name, surname,
# codice fiscale and birth date are asked with the request; the rest here. Their own
# mobile and email for an adult (any unit) and for a minor in Clan/Fuoco or Noviziato;
# for a minor, the parents (one, with exclusive custody, or both) with codice fiscale,
# mobile and email; the consents come from the signed forms.
CAMPI_SOCIO = (
    "sesso",
    "luogo_nascita",
    "indirizzo",
    "civico",
    "comune",
    "provincia",
    "cap",
    "cellulare",
    "email",
)
CAMPI_SOCIO_OBBLIGATORI = ("sesso", "luogo_nascita", "indirizzo", "comune", "provincia", "cap")
CAMPI_CONTATTO_OBBLIGATORI = ("cellulare", "email")
UNITA_CONTATTI_OBBLIGATORI = (TipoUnita.CLAN_FUOCO, TipoUnita.NOVIZIATO)


class RichiestaIscrizione(ModelloTracciato):
    codice = models.ForeignKey(
        CodiceIscrizione, null=True, on_delete=models.SET_NULL, related_name="richieste"
    )
    unita = models.ForeignKey(Unita, on_delete=models.PROTECT, related_name="richieste_iscrizione")
    # The account that asked: the parent of a minor, or the adult member.
    utente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="richieste_iscrizione",
    )
    # The new member: the minimal data; the rest is completed after the approval.
    nome = models.CharField(max_length=80)
    cognome = models.CharField(max_length=80)
    data_nascita = models.DateField()
    codice_fiscale = models.CharField(max_length=16)
    email = models.EmailField(blank=True)
    # The parent who asks for a minor (their email is the account's).
    genitore_nome = models.CharField(max_length=80, blank=True)
    genitore_cognome = models.CharField(max_length=80, blank=True)
    genitore_codice_fiscale = models.CharField(max_length=16, blank=True)
    # Asked at once since DEC-264: the child's sex, how the parental responsibility is
    # held (both parents, one, a guardian: as BuonaStrada), the contacts.
    sesso = models.CharField(max_length=1, blank=True)
    # Optional at the request: with sex and date it lets the app propose the codice fiscale.
    luogo_nascita = models.CharField(max_length=120, blank=True)
    responsabilita = models.CharField(
        max_length=14,
        blank=True,
        choices=[
            ("GENITORI", "Entrambi i genitori"),
            ("UNICO_GENITORE", "Un solo genitore"),
            ("TUTORE", "Un tutore"),
        ],
    )
    genitore_cellulare = models.CharField(max_length=30, blank=True)
    altro_nome = models.CharField(max_length=80, blank=True)
    altro_cognome = models.CharField(max_length=80, blank=True)
    altro_codice_fiscale = models.CharField(max_length=16, blank=True)
    altro_cellulare = models.CharField(max_length=30, blank=True)
    altro_email = models.EmailField(blank=True)

    stato = models.CharField(
        max_length=10, choices=StatoIscrizione.choices, default=StatoIscrizione.IN_ATTESA
    )
    persona = models.ForeignKey(
        Persona, null=True, blank=True, on_delete=models.SET_NULL, related_name="iscrizioni"
    )
    decisa_il = models.DateTimeField(null=True, blank=True)
    decisa_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    motivo_rifiuto = models.TextField(blank=True)
    # A minor's parents, as BuonaStrada asks: one with exclusive custody (True) or both
    # (False); None until the family says.
    genitore_unico = models.BooleanField(null=True, blank=True)
    # By when the family completes the data and the signed forms.
    scadenza_completamento = models.DateField(null=True, blank=True)
    completata_il = models.DateTimeField(null=True, blank=True)
    # Emails already sent (management command promemoria_iscrizioni).
    segnalata_il = models.DateTimeField(null=True, blank=True)  # to the approvers
    promemoria_il = models.DateField(null=True, blank=True)  # to the family
    sospesa_il = models.DateField(null=True, blank=True)
    # A member of the unit staff (or a capogruppo) checked the signed forms.
    moduli_verificati_il = models.DateTimeField(null=True, blank=True)
    moduli_verificati_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    # A capogruppo entered the member in BuonaStrada; the import then finds them.
    inserita_il = models.DateTimeField(null=True, blank=True)
    inserita_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    recepita_il = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "richiesta di iscrizione"
        verbose_name_plural = "richieste di iscrizione"
        ordering = ["-creato_il"]

    def __str__(self) -> str:
        return f"Iscrizione di {self.cognome} {self.nome} a {self.unita}"

    @property
    def contatti_obbligatori(self) -> bool:
        """Own mobile and email: adults, and minors in Clan/Fuoco or Noviziato."""
        return not self.per_minore or self.unita.tipo in UNITA_CONTATTI_OBBLIGATORI

    @property
    def per_minore(self) -> bool:
        from apps.core.anno import eta_in_data

        return eta_in_data(self.data_nascita, timezone.localdate()) < 18

    def _clean_responsabilita(self) -> None:
        """Who holds the parental responsibility, with their contacts (DEC-264)."""
        from apps.anagrafica.servizi import codice_fiscale_valido

        if not self.responsabilita:
            raise ValidationError(
                "Indica chi ha la responsabilità genitoriale: entrambi i genitori, uno solo o "
                "un tutore."
            )
        if not self.genitore_cellulare.strip():
            raise ValidationError("Scrivi il tuo numero di telefono.")
        if self.responsabilita != "GENITORI":
            return
        if not (self.altro_nome.strip() and self.altro_cognome.strip()):
            raise ValidationError("Scrivi nome e cognome dell'altro genitore.")
        if not codice_fiscale_valido(self.altro_codice_fiscale):
            raise ValidationError("Il codice fiscale dell'altro genitore non è valido.")
        if self.altro_codice_fiscale in (self.codice_fiscale, self.genitore_codice_fiscale):
            raise ValidationError("Il codice fiscale dell'altro genitore è già usato qui.")
        if not (self.altro_cellulare.strip() and self.altro_email.strip()):
            raise ValidationError("Scrivi telefono ed email dell'altro genitore.")

    def clean(self) -> None:
        from apps.anagrafica.servizi import codice_fiscale_valido

        for campo, etichetta in (("nome", "il nome"), ("cognome", "il cognome")):
            if not getattr(self, campo).strip():
                raise ValidationError(f"Scrivi {etichetta}.")
        if self.data_nascita and self.data_nascita >= date.today():
            raise ValidationError("La data di nascita non è valida.")
        if not codice_fiscale_valido(self.codice_fiscale):
            raise ValidationError("Il codice fiscale non è valido.")
        if self.sesso not in ("M", "F"):
            raise ValidationError("Indica il sesso.")
        if self.data_nascita and self.per_minore:
            if self.unita_id and self.unita.tipo == TipoUnita.COMUNITA_CAPI:
                raise ValidationError("In Comunità Capi si iscrivono solo maggiorenni.")
            if not (self.genitore_nome.strip() and self.genitore_cognome.strip()):
                raise ValidationError("Per un minorenne scrivi nome e cognome del genitore.")
            if not codice_fiscale_valido(self.genitore_codice_fiscale):
                raise ValidationError("Il codice fiscale del genitore non è valido.")
            if self.genitore_codice_fiscale == self.codice_fiscale:
                raise ValidationError(
                    "Il codice fiscale del genitore è uguale a quello del figlio."
                )
            self._clean_responsabilita()
        elif self.data_nascita and not self.email:
            raise ValidationError("Scrivi l'email.")


# --- Signed forms (DEC-126) ---------------------------------------------------------------

DIMENSIONE_MASSIMA = 10 * 1024 * 1024
# First bytes of the accepted files: PDF, JPEG, PNG.
FIRME_FILE = {b"%PDF": "application/pdf", b"\xff\xd8\xff": "image/jpeg", b"\x89PNG": "image/png"}


def tipo_file(inizio: bytes) -> str | None:
    """The content type from the first bytes, None if not an accepted kind."""
    return next((tipo for firma, tipo in FIRME_FILE.items() if inizio.startswith(firma)), None)


class ModuloVuoto(ModelloTracciato):
    """Blank forms (privacy notice, consents…) the family downloads, signs by hand and
    uploads again. The capigruppo keep them up to date."""

    titolo = models.CharField(max_length=120)
    file = models.FileField(upload_to="modulistica/")
    attivo = models.BooleanField(default=True)
    caricato_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        verbose_name = "modulo vuoto"
        verbose_name_plural = "modulistica"
        ordering = ["titolo"]

    def __str__(self) -> str:
        return self.titolo


class AllegatoIscrizione(ModelloTracciato):
    """A scan of a signed form. Personal data with signatures: never in the admin, read
    only through the API (policy, access log), kept while the member is in the group."""

    richiesta = models.ForeignKey(
        RichiestaIscrizione, on_delete=models.CASCADE, related_name="allegati"
    )
    file = models.FileField(upload_to="iscrizioni/%Y/")
    nome_file = models.CharField(max_length=200)
    tipo_contenuto = models.CharField(max_length=40)
    caricato_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        verbose_name = "modulo firmato"
        verbose_name_plural = "moduli firmati"
        ordering = ["creato_il"]

    def __str__(self) -> str:
        return f"{self.nome_file} ({self.richiesta})"
