from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import ModelloTracciato

from . import segnaposto

TITOLO_COMPLETO = "[Nome sito] - [Gruppo]"
TITOLO_BREVE = "[Sigla sito] - [Sigla gruppo]"
# Shown when the technical administrator leaves the message empty (DEC-268).
MESSAGGIO_MANUTENZIONE = (
    "L'app è in manutenzione. Torna tra un po': i dati salvati sul telefono e le modifiche "
    "in attesa non si perdono."
)


class SicurezzaSmtp(models.TextChoices):
    STARTTLS = "STARTTLS", "STARTTLS (di solito porta 587)"
    SSL = "SSL", "SSL/TLS (di solito porta 465)"
    NESSUNA = "NESSUNA", "Nessuna (solo in una rete fidata)"


class ModoInvio(models.TextChoices):
    SMTP = "SMTP", "Server SMTP"
    GMAIL = "GMAIL", "Gmail con accesso Google"


# Who receives the emails, by group (DEC-276).
GRUPPI_EMAIL = ("capi", "genitori", "ragazzi")


class Impostazioni(ModelloTracciato):
    """The installation's settings, one row (DEC-245…DEC-248).

    The names here are for the title only: the group's official data for the prints
    stay on `organizzazione.Gruppo` (DEC-245).
    """

    nome_sito = models.CharField(max_length=80, default="Quaderno di Caccia")
    sigla_sito = models.CharField(max_length=20, default="QdC", blank=True)
    # Empty: "AGESCI" and the BuonaStrada name (`nome_del_gruppo`).
    nome_gruppo = models.CharField(max_length=120, blank=True)
    sigla_gruppo = models.CharField(max_length=20, blank=True)
    titolo_completo = models.CharField(max_length=200, default=TITOLO_COMPLETO)
    titolo_breve = models.CharField(max_length=120, default=TITOLO_BREVE)
    # Shown above the fixed line of the footer (DEC-247).
    riga_piede = models.CharField(max_length=300, blank=True)
    # Email test mode (DEC-249): emails go to Mailpit, nobody receives them. Effective only
    # where settings.QDC_MAILPIT_CONSENTITO: see `email_di_prova_attiva`.
    email_di_prova = models.BooleanField(default=False)
    # Privacy policy and terms (DEC-266): the group's text, cleaned HTML with
    # placeholders; empty = the default in `pagine.PAGINE`. The date tells the cookie
    # banner to show again.
    # The common footer of the emails (DEC-250): HTML with placeholders; the plain text is
    # derived from it unless written here; the email types that go without it.
    piede_email = models.TextField(blank=True)
    piede_email_testo = models.TextField(blank=True)
    email_senza_piede = models.JSONField(default=list, blank=True)
    privacy = models.TextField(blank=True)
    privacy_aggiornata_il = models.DateField(null=True, blank=True)
    termini = models.TextField(blank=True)
    termini_aggiornati_il = models.DateField(null=True, blank=True)
    # Maintenance (DEC-268): only the technical administrators get in
    # (`manutenzione.ManutenzioneMiddleware`); the message is shown to everybody else.
    manutenzione = models.BooleanField(default=False)
    messaggio_manutenzione = models.TextField(blank=True)
    # Who receives the emails (DEC-276): off at first, switched on one group at a time;
    # the emails a group did not get are only counted.
    email_capi = models.BooleanField(default=False)
    email_genitori = models.BooleanField(default=False)
    email_ragazzi = models.BooleanField(default=False)
    email_scartate = models.JSONField(default=dict, blank=True)
    # The SMTP server (DEC-277); no host = the one in the server's configuration. The
    # password is encrypted (`segreti`) and never sent back.
    smtp_host = models.CharField(max_length=200, blank=True)
    smtp_porta = models.PositiveIntegerField(default=587)
    smtp_sicurezza = models.CharField(
        max_length=8, choices=SicurezzaSmtp.choices, default=SicurezzaSmtp.STARTTLS
    )
    smtp_utente = models.CharField(max_length=200, blank=True)
    smtp_password = models.TextField(blank=True)
    # "Name <address>"; empty = the server's configuration.
    mittente = models.CharField(max_length=200, blank=True)
    # Or Gmail, linked once with a Google login (DEC-278): the group's OAuth client, its
    # secret and the refresh token encrypted like the SMTP password.
    modo_invio = models.CharField(max_length=5, choices=ModoInvio.choices, default=ModoInvio.SMTP)
    gmail_client_id = models.CharField(max_length=200, blank=True)
    gmail_client_secret = models.TextField(blank=True)
    gmail_refresh_token = models.TextField(blank=True)
    gmail_indirizzo = models.EmailField(blank=True)

    class Meta:
        verbose_name = "impostazioni"
        verbose_name_plural = "impostazioni"

    def __str__(self) -> str:
        return "Impostazioni"

    def clean(self) -> None:
        errori = {}
        for campo in ("titolo_completo", "titolo_breve", "riga_piede"):
            ignoti = segnaposto.sconosciuti(getattr(self, campo), segnaposto.DEL_TITOLO)
            if ignoti:
                elenco = ", ".join(f"[{n}]" for n in ignoti)
                errori[campo] = f"Segnaposto sconosciuto: {elenco}."
        if errori:
            raise ValidationError(errori)

    @classmethod
    def carica(cls) -> Impostazioni:
        return cls.objects.get_or_create(pk=1)[0]

    def email_di_prova_attiva(self) -> bool:
        from django.conf import settings

        return self.email_di_prova and settings.QDC_MAILPIT_CONSENTITO

    def email_accese(self) -> set[str]:
        return {g for g in GRUPPI_EMAIL if getattr(self, f"email_{g}")}

    def avviso_manutenzione(self) -> str:
        return self.messaggio_manutenzione.strip() or MESSAGGIO_MANUTENZIONE

    def nome_del_gruppo(self) -> str:
        if self.nome_gruppo:
            return self.nome_gruppo
        from apps.organizzazione.models import Gruppo

        gruppo = Gruppo.objects.first()
        return f"AGESCI {gruppo.denominazione}" if gruppo else "AGESCI"


class ModelloEmail(ModelloTracciato):
    """A template of an email the group has personalised (DEC-250). Without a row the
    default in `email.TIPI` is used; deleting the row goes back to it."""

    chiave = models.CharField(max_length=60, unique=True)
    oggetto = models.CharField(max_length=200)
    # HTML from the editor, cleaned by `html.pulisci` before saving.
    corpo = models.TextField()
    modificato_da = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    # When the capigruppo were told that an update made a placeholder indispensable that
    # this template lacks; cleared at every save.
    avvisato_il = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "modello di email"
        verbose_name_plural = "modelli di email"

    def __str__(self) -> str:
        return self.chiave


class ImmagineEmail(ModelloTracciato):
    """An image for the email templates and the footer (DEC-250): re-encoded on upload
    (no metadata), under a random name; emails carry it inline, pages show it from
    `/api/v1/immagini/<nome>`. Logos and the like, never personal photos."""

    file = models.FileField(upload_to="immagini-email/")
    tipo = models.CharField(max_length=20)
    caricata_da = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        verbose_name = "immagine delle email"
        verbose_name_plural = "immagini delle email"

    def __str__(self) -> str:
        return self.nome

    @property
    def nome(self) -> str:
        return self.file.name.rsplit("/", 1)[-1]
