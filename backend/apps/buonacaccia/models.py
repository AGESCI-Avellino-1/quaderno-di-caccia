"""Events on BuonaCaccia (DEC-158…DEC-164): QdC is the staff's notebook, it never talks
to BuonaCaccia.

- every BuonaCaccia event (a given Piccole Orme, a campetto, an EPPPI…) is one external
  event (`Evento` with level ESTERNO) with single participants; two members at the same
  event = one event in the app (DEC-158);
- the registration of a minor is recorded by the staff of their unit or a capogruppo:
  date, admitted or on the waiting list, 9 days for release form, event form and
  payment, cancellation without losing the fee up to 7 days before the start; reminders
  to the staff before each deadline (DEC-158);
- the management link is seen only by who manages the registration (DEC-159);
- release form uploaded through the app or just ticked, with a deadline and reminders to
  the family; loaded on BuonaCaccia, validated or rejected with the reason (DEC-160);
- event forms built by the staff, saved and versioned, answered by the participant or
  their parent; the staff's presentation only for capi (DEC-161);
- the photo, prepared as a JPEG of at most 1 MB (DEC-162);
- the family's fee, without family discount; the payment to BuonaCaccia is an outflow in
  A.2 (DEC-163);
- adults register by themselves: only their participation; for capi training camps also
  the fee they paid, listed for the Zona at the end of the year (DEC-164).
"""

from datetime import date, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import ModelloTracciato

# Deadlines set by BuonaCaccia (DEC-158) and by the analysis (DEC-160).
GIORNI_PER_COMPLETARE = 9
GIORNI_PRIMA_PER_CANCELLARE = 7
GIORNI_PRIMA_LIBERATORIA = 2
# The photo BuonaCaccia accepts (DEC-162).
DIMENSIONE_FOTO = 1024 * 1024


class TipoCampoFormazione(models.TextChoices):
    """Capi training camps for the Zona's list (DEC-164, DEC-170). A module and "other"
    need a description."""

    CFT = "CFT", "Campo di Formazione Tirocinanti (CFT)"
    CFM = "CFM", "Campo di Formazione Metodologica (CFM)"
    CFA = "CFA", "Campo di Formazione Associativa (CFA)"
    CCG = "CCG", "Campo per Capigruppo (CCG)"
    MODULO = "MODULO", "Modulo formativo"
    ALTRO = "ALTRO", "Altro"


class EventoBuonaCaccia(ModelloTracciato):
    """What an external event adds to `Evento`."""

    evento = models.OneToOneField(
        "eventi.Evento", on_delete=models.CASCADE, related_name="buonacaccia"
    )
    formazione_capi = models.BooleanField(default=False)
    # Lived once only, in Responsabilità, at least three days (L/C art. 43, V11): the
    # app warns, never blocks (DEC-184).
    piccole_orme = models.BooleanField(default=False)
    tipo_campo = models.CharField(max_length=8, choices=TipoCampoFormazione.choices, blank=True)
    # The title of a module, or what "other" is.
    specifica = models.CharField(max_length=160, blank=True)
    scheda = models.ForeignKey(
        "VersioneScheda",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="eventi",
    )

    class Meta:
        verbose_name = "evento su BuonaCaccia"
        verbose_name_plural = "eventi su BuonaCaccia"

    def __str__(self) -> str:
        return str(self.evento)

    def clean(self) -> None:
        errori = []
        if self.formazione_capi and not self.tipo_campo:
            errori.append("Scegli il tipo di campo di formazione.")
        if not self.formazione_capi and self.tipo_campo:
            errori.append("Il tipo di campo vale solo per la formazione capi.")
        if self.piccole_orme and self.formazione_capi:
            errori.append("Le Piccole Orme non sono un campo di formazione capi.")
        if self.tipo_campo == TipoCampoFormazione.MODULO and not self.specifica.strip():
            errori.append("Scrivi il titolo del modulo formativo.")
        if self.tipo_campo == TipoCampoFormazione.ALTRO and not self.specifica.strip():
            errori.append("Specifica che tipo di campo è.")
        if errori:
            raise ValidationError(errori)

    @property
    def tipo_campo_testo(self) -> str:
        if self.tipo_campo in (TipoCampoFormazione.MODULO, TipoCampoFormazione.ALTRO):
            return f"{self.get_tipo_campo_display()}: {self.specifica}"
        return self.get_tipo_campo_display()


# --- Event forms (DEC-161) ----------------------------------------------------------------


class TipoDomanda(models.TextChoices):
    SCELTA_SINGOLA = "SCELTA_SINGOLA", "Scelta singola"
    SCELTA_MULTIPLA = "SCELTA_MULTIPLA", "Scelta multipla"
    BREVE = "BREVE", "Risposta breve"
    LUNGA = "LUNGA", "Risposta lunga"
    SI_NO = "SI_NO", "Sì / no"
    FOTO = "FOTO", "Foto"


class ModelloScheda(ModelloTracciato):
    """A form the staff reuses over the years (e.g. "Piccole Orme"). Its questions are in
    versions: a change saves a new one, registrations keep theirs."""

    nome = models.CharField(max_length=120)
    creato_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        verbose_name = "scheda di un evento"
        verbose_name_plural = "schede degli eventi"
        ordering = ["nome"]

    def __str__(self) -> str:
        return self.nome

    def ultima(self) -> VersioneScheda | None:
        return self.versioni.order_by("-numero").first()


class VersioneScheda(ModelloTracciato):
    """The questions, as a list:
    [{"id": "a1b2", "tipo": "SCELTA_SINGOLA", "testo": "…", "opzioni": ["…"],
      "obbligatoria": true}]. The id stays the same when a question is kept in a new
    version, so answers given to an older version still match."""

    modello = models.ForeignKey(ModelloScheda, on_delete=models.CASCADE, related_name="versioni")
    numero = models.PositiveSmallIntegerField()
    domande = models.JSONField(default=list)
    creata_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        verbose_name = "versione di una scheda"
        verbose_name_plural = "versioni delle schede"
        ordering = ["modello", "numero"]
        constraints = [
            models.UniqueConstraint(fields=["modello", "numero"], name="versione_scheda_unica")
        ]

    def __str__(self) -> str:
        return f"{self.modello} (versione {self.numero})"

    def clean(self) -> None:
        errori = []
        if not self.domande:
            errori.append("Aggiungi almeno una domanda.")
        ids = set()
        for domanda in self.domande:
            if not isinstance(domanda, dict) or not str(domanda.get("testo", "")).strip():
                errori.append("Ogni domanda ha un testo.")
                continue
            if domanda.get("tipo") not in TipoDomanda.values:
                errori.append("Tipo di domanda sconosciuto.")
            if domanda.get("id") in ids or not domanda.get("id"):
                errori.append("Domande con lo stesso identificativo.")
            ids.add(domanda.get("id"))
            opzioni = [o for o in domanda.get("opzioni") or [] if str(o).strip()]
            scelta = domanda.get("tipo") in (
                TipoDomanda.SCELTA_SINGOLA,
                TipoDomanda.SCELTA_MULTIPLA,
            )
            if scelta and len(opzioni) < 2:
                errori.append(f"Indica almeno due scelte per «{domanda['testo']}».")
        if sum(1 for d in self.domande if d.get("tipo") == TipoDomanda.FOTO) > 1:
            errori.append("La scheda chiede al massimo una foto.")
        if errori:
            raise ValidationError(list(dict.fromkeys(errori)))

    @property
    def chiede_foto(self) -> bool:
        return any(d.get("tipo") == TipoDomanda.FOTO for d in self.domande)


# --- Registrations of minors (DEC-158…DEC-163) -------------------------------------------


class StatoIscrizione(models.TextChoices):
    AMMESSO = "AMMESSO", "Ammesso"
    IN_ATTESA = "IN_ATTESA", "In lista d'attesa"
    NON_AMMESSO = "NON_AMMESSO", "Non ammesso"
    CANCELLATA = "CANCELLATA", "Iscrizione cancellata"


ATTIVE = (StatoIscrizione.AMMESSO, StatoIscrizione.IN_ATTESA)


class ModoLiberatoria(models.TextChoices):
    """DEC-160, chosen by the staff."""

    APP = "APP", "Passa dall'app"
    ALTRI_CANALI = "ALTRI_CANALI", "Arriva per altri canali"


class EsitoLiberatoria(models.TextChoices):
    VALIDATA = "VALIDATA", "Validata dalla segreteria"
    RIGETTATA = "RIGETTATA", "Rigettata dalla segreteria"


class IscrizioneBuonaCaccia(ModelloTracciato):
    """The staff's record of a minor's registration on BuonaCaccia. Files are stored
    under random names and read only through the API (policy, access log): never in the
    admin."""

    partecipazione = models.OneToOneField(
        "eventi.Partecipazione", on_delete=models.CASCADE, related_name="iscrizione_buonacaccia"
    )
    iscritto_il = models.DateField(help_text="Data dell'iscrizione su BuonaCaccia.")
    stato = models.CharField(max_length=12, choices=StatoIscrizione.choices)
    cancellata_il = models.DateField(null=True, blank=True)
    # DEC-159: only who manages the registration sees it.
    link_gestione = models.URLField(max_length=500, blank=True)
    # Release form (DEC-160).
    modo_liberatoria = models.CharField(
        max_length=12, choices=ModoLiberatoria.choices, default=ModoLiberatoria.APP
    )
    scadenza_liberatoria = models.DateField(null=True, blank=True)
    liberatoria_da_firmare = models.FileField(upload_to="buonacaccia/liberatorie/", blank=True)
    liberatoria_firmata = models.FileField(upload_to="buonacaccia/firmate/", blank=True)
    tipo_firmata = models.CharField(max_length=40, blank=True)
    liberatoria_ricevuta_il = models.DateField(null=True, blank=True)
    liberatoria_caricata_il = models.DateField(
        null=True, blank=True, help_text="Caricata su BuonaCaccia."
    )
    esito_liberatoria = models.CharField(
        max_length=10, choices=EsitoLiberatoria.choices, blank=True
    )
    motivo_rigetto = models.CharField(max_length=300, blank=True)
    # Event form (DEC-161, DEC-162): answers seen by the family, presentation by capi only.
    risposte = models.JSONField(default=dict, blank=True)
    risposte_di = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    risposte_il = models.DateTimeField(null=True, blank=True)
    foto = models.FileField(upload_to="buonacaccia/foto/", blank=True)
    presentazione = models.TextField(blank=True)
    scheda_inviata_il = models.DateField(
        null=True, blank=True, help_text="Scheda compilata su BuonaCaccia."
    )
    # Payment on BuonaCaccia and the family's fee (DEC-163).
    pagata_il = models.DateField(null=True, blank=True, help_text="Pagata su BuonaCaccia.")
    quota = models.OneToOneField(
        "quote.Quota",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="iscrizione_buonacaccia",
    )
    # Reminders already sent: {"staff-scadenza-2": "2026-11-03", …}.
    promemoria = models.JSONField(default=dict, blank=True)
    registrata_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        verbose_name = "iscrizione su BuonaCaccia"
        verbose_name_plural = "iscrizioni su BuonaCaccia"

    def __str__(self) -> str:
        return f"Iscrizione di {self.partecipazione.persona} a {self.partecipazione.evento}"

    @property
    def attiva(self) -> bool:
        return self.stato in ATTIVE

    @property
    def scadenza(self) -> date:
        """Release form, event form and payment on BuonaCaccia (DEC-158)."""
        return self.iscritto_il + timedelta(days=GIORNI_PER_COMPLETARE)

    @property
    def limite_cancellazione(self) -> date:
        from django.utils import timezone

        inizio = timezone.localdate(self.partecipazione.evento.inizio)
        return inizio - timedelta(days=GIORNI_PRIMA_PER_CANCELLARE)

    @property
    def scadenza_della_liberatoria(self) -> date:
        """Set by the staff or, by default, two days before the registration's (DEC-160)."""
        return self.scadenza_liberatoria or self.scadenza - timedelta(days=GIORNI_PRIMA_LIBERATORIA)


class QuotaFormazione(ModelloTracciato):
    """The fee a capo paid to BuonaCaccia for a training camp (DEC-164), for the Zona."""

    partecipazione = models.OneToOneField(
        "eventi.Partecipazione", on_delete=models.CASCADE, related_name="quota_formazione"
    )
    importo = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        verbose_name = "quota di un campo di formazione"
        verbose_name_plural = "quote dei campi di formazione"

    def __str__(self) -> str:
        return f"{self.importo} € per {self.partecipazione}"
