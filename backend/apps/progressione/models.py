"""Progressione Personale (DEC-56…DEC-74), from the domain specification v1.0.

E/G first (DEC-56: phase 4 starts with the reparto as pilot):

- one identity for life; branch periods and phase periods (tappe, momenti, passi)
  are separate from memberships of units (DEC-57);
- the staff registers the entry in the sentiero and the tappa (DEC-171); the
  Promessa is an event with a date; the badge of a tappa is handed over with its own
  date, distinct from the entry in the tappa (DEC-58, V02, V06);
- tappe follow Scoperta → Competenza → Responsabilità, each step a decision of the
  Consiglio della Legge, never by seniority (V08); the end of Responsabilità does not
  close the sentiero (V16); a late entrant is placed after the Promessa without
  inventing the tappe in between (spec §17.6, PlaceAfterLateEntry);
- impegni and mete have six states and keep the revisions of their text (DEC-59);
  validation = "da verificare" → "concluso", with date, who and where (DEC-60,
  DEC-172); a meta may be private (DEC-173, V15);
- historical dates may be partial (DEC-70): a value and its precision, never a fake
  1 January.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.core.date_parziali import PrecisioneData
from apps.core.models import ModelloTracciato
from apps.organizzazione.models import Branca


class Fase(models.TextChoices):
    """Tappe E/G, momenti L/C and passi R/S share the three phases (spec §16.2)."""

    SCOPERTA = "SCOPERTA", "Scoperta"
    COMPETENZA = "COMPETENZA", "Competenza"
    RESPONSABILITA = "RESPONSABILITA", "Responsabilità"


ORDINE_FASI = [Fase.SCOPERTA, Fase.COMPETENZA, Fase.RESPONSABILITA]


class SedeVerifica(models.TextChoices):
    """Where a verification takes place (E/G artt. 42–43; DEC-172)."""

    CONSIGLIO_LEGGE = "CONSIGLIO_LEGGE", "Consiglio della Legge"
    CONSIGLIO_SQUADRIGLIA = "CONSIGLIO_SQ", "Consiglio di squadriglia"
    ALTA_SQUADRIGLIA = "ALTA_SQ", "Alta Squadriglia"
    # L/C: the conquest of prede and voli is verified with them (L/C art. 38).
    ANZIANI = "ANZIANI", "Con i vecchi lupi o le coccinelle anziane"
    ALTRO = "ALTRO", "Altro"


def _data(**campi) -> models.DateField:
    return models.DateField(**campi)


def _precisione() -> models.CharField:
    return models.CharField(
        max_length=6, choices=PrecisioneData.choices, default=PrecisioneData.GIORNO
    )


def _utente() -> models.ForeignKey:
    return models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )


class PeriodoBranca(ModelloTracciato):
    """The time a person spends in a branch (spec §8.1): opened by the staff,
    closed by a passaggio or an exit. One open period per person."""

    persona = models.ForeignKey(
        "anagrafica.Persona", on_delete=models.CASCADE, related_name="periodi_branca"
    )
    branca = models.CharField(max_length=4, choices=Branca.choices)
    data_inizio = _data()
    precisione_inizio = _precisione()
    data_fine = _data(null=True, blank=True)
    motivo_fine = models.CharField(max_length=200, blank=True)
    registrato_da = _utente()
    # Imported from another group's QdC: its name (DEC-46, DEC-213).
    provenienza = models.CharField(max_length=120, blank=True)

    class Meta:
        verbose_name = "periodo di branca"
        verbose_name_plural = "periodi di branca"
        ordering = ["data_inizio"]
        constraints = [
            models.UniqueConstraint(
                fields=["persona"],
                condition=Q(data_fine__isnull=True),
                name="un_periodo_di_branca_aperto",
            )
        ]

    def __str__(self) -> str:
        return f"{self.persona} in {self.get_branca_display()}"

    def tappa_attuale(self) -> Tappa | None:
        return self.tappe.filter(data_fine__isnull=True).first()


class Tappa(ModelloTracciato):
    """A phase period: a tappa E/G (spec §8.1 "periodo di progressione"). It starts
    with its date; its conclusion is recognised in the Consiglio della Legge
    (`completata_il`); it ends (`data_fine`, exclusive) when the next one starts or the
    branch period closes."""

    periodo = models.ForeignKey(PeriodoBranca, on_delete=models.CASCADE, related_name="tappe")
    fase = models.CharField(max_length=14, choices=Fase.choices)
    data_inizio = _data()
    precisione_inizio = _precisione()
    # A late entrant placed after the Promessa, not by a recognised conclusion.
    collocamento = models.BooleanField(default=False)
    motivazione = models.CharField(max_length=300, blank=True)
    completata_il = _data(null=True, blank=True)
    precisione_completata = _precisione()
    sede_completamento = models.CharField(max_length=16, choices=SedeVerifica.choices, blank=True)
    completata_da = _utente()
    data_fine = _data(null=True, blank=True)
    registrata_da = _utente()
    # Why a date was corrected (the audit log keeps the old values).
    nota_rettifica = models.CharField(max_length=300, blank=True)

    class Meta:
        verbose_name = "tappa"
        verbose_name_plural = "tappe"
        ordering = ["data_inizio", "creato_il"]
        constraints = [
            models.UniqueConstraint(
                fields=["periodo"],
                condition=Q(data_fine__isnull=True),
                name="una_tappa_aperta",
            )
        ]

    def __str__(self) -> str:
        return f"{self.get_fase_display()} di {self.periodo.persona}"


class Promessa(ModelloTracciato):
    """An event with a date, inside the Scoperta (V02); never withdrawn (V20): only a
    traced correction of a recording mistake."""

    periodo = models.OneToOneField(PeriodoBranca, on_delete=models.CASCADE, related_name="promessa")
    data = _data()
    precisione = _precisione()
    registrata_da = _utente()
    nota_rettifica = models.CharField(max_length=300, blank=True)

    class Meta:
        verbose_name = "Promessa"
        verbose_name_plural = "Promesse"

    def __str__(self) -> str:
        return f"Promessa di {self.periodo.persona}"


class ConsegnaDistintivo(ModelloTracciato):
    """The badge of a tappa, handed over at its start but with its own date (V06): it
    does not mark the tappa as completed."""

    tappa = models.OneToOneField(Tappa, on_delete=models.CASCADE, related_name="distintivo")
    data = _data()
    precisione = _precisione()
    registrata_da = _utente()
    nota_rettifica = models.CharField(max_length=300, blank=True)

    class Meta:
        verbose_name = "consegna del distintivo"
        verbose_name_plural = "consegne dei distintivi"

    def __str__(self) -> str:
        return f"Distintivo {self.tappa}"


# --- Impegni and mete (DEC-59…DEC-61) ------------------------------------------------------


class Stato(models.TextChoices):
    BOZZA = "BOZZA", "Bozza"
    CONCORDATO = "CONCORDATO", "Concordato"
    IN_CORSO = "IN_CORSO", "In corso"
    DA_VERIFICARE = "DA_VERIFICARE", "Da verificare"
    CONCLUSO = "CONCLUSO", "Concluso"
    INTERROTTO = "INTERROTTO", "Interrotto"


APERTI = (Stato.BOZZA, Stato.CONCORDATO, Stato.IN_CORSO, Stato.DA_VERIFICARE)


class Percorso(ModelloTracciato):
    """What impegni and mete share: text with revisions, state, who proposed what,
    the validation (spec §17.2, DEC-59, DEC-60)."""

    periodo = models.ForeignKey(PeriodoBranca, on_delete=models.CASCADE, related_name="+")
    testo = models.TextField()
    termine = _data(null=True, blank=True)
    stato = models.CharField(max_length=14, choices=Stato.choices, default=Stato.BOZZA)
    creato_da = _utente()
    # Inserted by the ragazzo (DEC-61): a draft until the staff agrees it.
    proposto_dal_ragazzo = models.BooleanField(default=False)
    concordato_il = _data(null=True, blank=True)
    avviato_il = _data(null=True, blank=True)
    verifica_proposta_da = _utente()
    verifica_proposta_il = models.DateTimeField(null=True, blank=True)
    # Validation (DEC-60, DEC-172): date, who (automatic), where.
    verificato_il = _data(null=True, blank=True)
    sede = models.CharField(max_length=16, choices=SedeVerifica.choices, blank=True)
    sede_descrizione = models.CharField(max_length=120, blank=True)
    verificato_da = _utente()
    interrotto_il = _data(null=True, blank=True)
    motivo_interruzione = models.CharField(max_length=300, blank=True)

    class Meta:
        abstract = True
        ordering = ["creato_il"]

    @property
    def aperto(self) -> bool:
        return self.stato in APERTI


class Obiettivo(Percorso):
    """A meta E/G (art. 33: introduced when the ragazzo can formulate it, V07) or an
    obiettivo R/S (art. 39: set or recalibrated in the Punto della Strada); spec §16.2
    "ObjectiveKind". A private one (`riservata`) is seen only by the ragazzo, the parents
    and the capi (DEC-173).

    The API calls them "mete" whatever the branch; the PWA names them by branch."""

    periodo = models.ForeignKey(PeriodoBranca, on_delete=models.CASCADE, related_name="mete")
    riservata = models.BooleanField(default=False)

    class Meta(Percorso.Meta):
        verbose_name = "meta o obiettivo"
        verbose_name_plural = "mete e obiettivi"

    def __str__(self) -> str:
        return f"Obiettivo di {self.periodo.persona}"


class Impegno(Percorso):
    """An impegno E/G (art. 32): concrete, verifiable, limited in time; with or without
    a meta (V07), possibly serving several. Also an impegno R/S, and in L/C a preda or
    a volo (art. 38), referred to the stagione instead of a deadline (spec §16.4)."""

    periodo = models.ForeignKey(PeriodoBranca, on_delete=models.CASCADE, related_name="impegni")
    criterio_verifica = models.TextField(blank=True)
    mete = models.ManyToManyField(Obiettivo, blank=True, related_name="impegni")
    stagione = models.ForeignKey(
        "Stagione", null=True, blank=True, on_delete=models.PROTECT, related_name="prede"
    )

    class Meta(Percorso.Meta):
        verbose_name = "impegno"
        verbose_name_plural = "impegni"

    def __str__(self) -> str:
        return f"Impegno di {self.periodo.persona}"


class Revisione(models.Model):
    """A former wording of an impegno or a meta (DEC-59): kept when the text changes."""

    meta = models.ForeignKey(
        Obiettivo, null=True, blank=True, on_delete=models.CASCADE, related_name="revisioni"
    )
    impegno = models.ForeignKey(
        Impegno, null=True, blank=True, on_delete=models.CASCADE, related_name="revisioni"
    )
    testo = models.TextField()
    criterio_verifica = models.TextField(blank=True)
    termine = _data(null=True, blank=True)
    sostituita_il = models.DateTimeField(auto_now_add=True)
    sostituita_da = _utente()

    class Meta:
        verbose_name = "revisione"
        verbose_name_plural = "revisioni"
        ordering = ["sostituita_il"]
        constraints = [
            models.CheckConstraint(
                condition=Q(meta__isnull=False, impegno__isnull=True)
                | Q(meta__isnull=True, impegno__isnull=False),
                name="revisione_di_una_cosa",
            )
        ]

    def __str__(self) -> str:
        return f"Revisione del {self.sostituita_il:%d/%m/%Y}"

    def clean(self) -> None:
        if (self.meta_id is None) == (self.impegno_id is None):
            raise ValidationError("Una revisione è di una meta o di un impegno.")


# --- Specialità, brevetti, specialità di squadriglia (DEC-62…DEC-64) -----------------------


class TipoCompetenza(models.TextChoices):
    SPECIALITA = "SPECIALITA", "Specialità"
    BREVETTO = "BREVETTO", "Brevetto di competenza"
    SPECIALITA_SQ = "SPECIALITA_SQ", "Specialità di squadriglia"
    # L/C art. 41: tests agreed with the capi, never the E/G procedure (spec §17.4).
    SPECIALITA_LC = "SPECIALITA_LC", "Specialità L/C"


class StatoCompetenza(models.TextChoices):
    """Spec §17.4: from proposed to recognised (DEC-62)."""

    PROPOSTO = "PROPOSTO", "Proposto"
    IN_CORSO = "IN_CORSO", "In corso"
    DA_VERIFICARE = "DA_VERIFICARE", "Da verificare"
    RICONOSCIUTO = "RICONOSCIUTO", "Conquistato"
    INTERROTTO = "INTERROTTO", "Interrotto"


class PercorsoCompetenza(ModelloTracciato):
    """The way to a specialità or a brevetto of one E/G, or to a specialità of a whole
    patrol (DEC-64, V19: the patrol is the holder, its members get nothing by it). It
    keeps the catalog's code, name and version as they were (DEC-63)."""

    tipo = models.CharField(max_length=14, choices=TipoCompetenza.choices)
    codice = models.CharField(max_length=10)
    nome = models.CharField(max_length=120)
    versione_catalogo = models.CharField(max_length=20)
    # Exactly one holder: a person's branch period, or a patrol.
    periodo = models.ForeignKey(
        PeriodoBranca, null=True, blank=True, on_delete=models.CASCADE, related_name="competenze"
    )
    squadriglia = models.ForeignKey(
        "organizzazione.Squadriglia",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="competenze",
    )
    stato = models.CharField(
        max_length=14, choices=StatoCompetenza.choices, default=StatoCompetenza.PROPOSTO
    )
    # The carta di specialità or di competenza, written in the app (DEC-62).
    carta = models.TextField(blank=True)
    # An E/G, a capo or an adult from outside: a name, never an account (DEC-62).
    maestro = models.CharField(max_length=120, blank=True)
    # Brevetto (art. 38, V09): the occasion of comparison on the competence.
    confronto = models.TextField(blank=True)
    # Brevetto: the specialità judged suitable; patrol: the individual specialità and
    # brevetti born from its path, even if not conquered (DEC-64).
    collegati = models.ManyToManyField("self", blank=True, symmetrical=False, related_name="+")
    avviato_il = _data(null=True, blank=True)
    verifica_proposta_il = models.DateTimeField(null=True, blank=True)
    verifica_proposta_da = _utente()
    riconosciuto_il = _data(null=True, blank=True)
    precisione_riconosciuto = _precisione()
    sede = models.CharField(max_length=16, choices=SedeVerifica.choices, blank=True)
    riconosciuto_da = _utente()
    # Recorded afterwards from a past year, with the precision known (spec §18.4).
    storico = models.BooleanField(default=False)
    distintivo_il = _data(null=True, blank=True)
    precisione_distintivo = _precisione()
    interrotto_il = _data(null=True, blank=True)
    motivo_interruzione = models.CharField(max_length=300, blank=True)
    creato_da = _utente()

    class Meta:
        verbose_name = "percorso di specialità o brevetto"
        verbose_name_plural = "percorsi di specialità e brevetti"
        ordering = ["creato_il"]
        constraints = [
            models.CheckConstraint(
                condition=Q(periodo__isnull=False, squadriglia__isnull=True)
                | Q(periodo__isnull=True, squadriglia__isnull=False),
                name="competenza_un_titolare",
            )
        ]

    def __str__(self) -> str:
        return f"{self.get_tipo_display()} {self.nome}"


# --- Imprese and posti d'azione (DEC-65) ----------------------------------------------------


class LivelloImpresa(models.TextChoices):
    REPARTO = "REPARTO", "Impresa di reparto"
    SQUADRIGLIA = "SQUADRIGLIA", "Impresa di squadriglia"
    ALTA_SQUADRIGLIA = "ALTA_SQ", "Impresa di Alta Squadriglia"


class Impresa(ModelloTracciato):
    reparto = models.ForeignKey(
        "organizzazione.Unita", on_delete=models.CASCADE, related_name="imprese"
    )
    livello = models.CharField(max_length=12, choices=LivelloImpresa.choices)
    squadriglia = models.ForeignKey(
        "organizzazione.Squadriglia",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="imprese",
    )
    titolo = models.CharField(max_length=160)
    descrizione = models.TextField(blank=True)
    dal = _data()
    al = _data(null=True, blank=True)
    creata_da = _utente()
    # Reparto and Alta Squadriglia: the ragazzi the staff appoints to run it; they
    # assign and verify the posti d'azione until it ends (DEC-187).
    consiglio = models.ManyToManyField(
        "anagrafica.Persona", blank=True, related_name="consigli_impresa"
    )

    class Meta:
        verbose_name = "impresa"
        verbose_name_plural = "imprese"
        ordering = ["-dal"]

    def __str__(self) -> str:
        return self.titolo

    def clean(self) -> None:
        errori = []
        if self.livello == LivelloImpresa.SQUADRIGLIA and not self.squadriglia_id:
            errori.append("Scegli la squadriglia.")
        if self.livello != LivelloImpresa.SQUADRIGLIA and self.squadriglia_id:
            errori.append("La squadriglia vale solo per un'impresa di squadriglia.")
        if self.squadriglia_id and self.squadriglia.unita_id != self.reparto_id:
            errori.append("La squadriglia non è di questo reparto.")
        if self.al and self.dal and self.al < self.dal:
            errori.append("La fine deve seguire l'inizio.")
        if errori:
            raise ValidationError(errori)

    @property
    def finita(self) -> bool:
        from django.utils import timezone

        return self.al is not None and self.al < timezone.localdate()


class PostoAzione(ModelloTracciato):
    """A role in an impresa (E/G art. 32: it may give rise to an impegno), verified in
    the Consiglio di squadriglia, the Consiglio della Legge or the Alta Squadriglia
    (artt. 42–43)."""

    impresa = models.ForeignKey(Impresa, on_delete=models.CASCADE, related_name="posti")
    persona = models.ForeignKey(
        "anagrafica.Persona", on_delete=models.CASCADE, related_name="posti_azione"
    )
    ruolo = models.CharField(max_length=160)
    impegno = models.ForeignKey(
        Impegno, null=True, blank=True, on_delete=models.SET_NULL, related_name="posti_azione"
    )
    verificato_il = _data(null=True, blank=True)
    sede = models.CharField(max_length=16, choices=SedeVerifica.choices, blank=True)
    sede_descrizione = models.CharField(max_length=120, blank=True)
    verificato_da = _utente()

    class Meta:
        verbose_name = "posto d'azione"
        verbose_name_plural = "posti d'azione"
        ordering = ["impresa", "creato_il"]

    def __str__(self) -> str:
        return f"{self.ruolo} — {self.persona}"


# --- Passaggi tra branche (DEC-69, DEC-174…DEC-177) -----------------------------------------


class StatoPassaggio(models.TextChoices):
    """Spec §17.9, prepared then executed (DEC-177)."""

    PREPARATO = "PREPARATO", "Preparato"
    ESEGUITO = "ESEGUITO", "Eseguito"
    ANNULLATO = "ANNULLATO", "Annullato"
    # Executed by mistake, then undone for everyone (spec §17.9, DEC-178).
    RETTIFICATO = "RETTIFICATO", "Annullato dopo l'esecuzione"


class Passaggio(ModelloTracciato):
    """The passage of some ragazzi of a unit to the next branch, decided by the Co.Ca.
    in a block (DEC-69). Executing it closes the branch periods and opens the new ones
    with their first phase (DEC-176), and moves the ragazzi to the new unit as a unit
    assigned in the app (DEC-175); tappe and specialità are never converted."""

    unita_origine = models.ForeignKey(
        "organizzazione.Unita", on_delete=models.PROTECT, related_name="passaggi_in_uscita"
    )
    unita_destinazione = models.ForeignKey(
        "organizzazione.Unita", on_delete=models.PROTECT, related_name="passaggi_in_entrata"
    )
    # The date it takes effect; the Co.Ca. decision and the ceremony may differ.
    data = _data()
    data_decisione = _data(null=True, blank=True)
    data_cerimonia = _data(null=True, blank=True)
    stato = models.CharField(
        max_length=12, choices=StatoPassaggio.choices, default=StatoPassaggio.PREPARATO
    )
    preparato_da = _utente()
    eseguito_da = _utente()
    eseguito_il = models.DateTimeField(null=True, blank=True)
    annullato_il = models.DateTimeField(null=True, blank=True)
    motivo_annullamento = models.CharField(max_length=300, blank=True)
    # Why the date was corrected after execution (the audit log keeps the old one).
    nota_rettifica = models.CharField(max_length=300, blank=True)

    class Meta:
        verbose_name = "passaggio"
        verbose_name_plural = "passaggi"
        ordering = ["-data"]

    def __str__(self) -> str:
        return f"Passaggio da {self.unita_origine} a {self.unita_destinazione}"


class PassaggioPersona(ModelloTracciato):
    """One ragazzo in a passage, with the summary for the new capi (spec §7)."""

    passaggio = models.ForeignKey(Passaggio, on_delete=models.CASCADE, related_name="persone")
    persona = models.ForeignKey(
        "anagrafica.Persona", on_delete=models.CASCADE, related_name="passaggi"
    )
    sintesi = models.TextField(blank=True)
    periodo_origine = models.ForeignKey(
        PeriodoBranca, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    periodo_destinazione = models.OneToOneField(
        PeriodoBranca,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="passaggio_in_entrata",
    )
    # What the execution closed and opened, to undo exactly that (DEC-178):
    # {"tappa": id, "appartenenze": [ids], "appartenenza_nuova": id,
    #  "squadriglie": [ids], "incarichi": [ids], "deroghe": [ids]}.
    chiusure = models.JSONField(default=dict, blank=True)
    rettificata_il = models.DateTimeField(null=True, blank=True)
    rettificata_da = _utente()
    motivo_rettifica = models.CharField(max_length=300, blank=True)

    class Meta:
        verbose_name = "ragazzo in un passaggio"
        verbose_name_plural = "ragazzi nei passaggi"
        ordering = ["persona__cognome", "persona__nome"]
        constraints = [
            models.UniqueConstraint(fields=["passaggio", "persona"], name="passaggio_persona_unica")
        ]

    def __str__(self) -> str:
        return f"{self.persona} — {self.passaggio}"


# --- R/S: Carta di clan, Punto della Strada, conclusione (DEC-67, DEC-179…DEC-181) ----------


class FirmaCarta(ModelloTracciato):
    """The signature of the Carta di clan, recorded with its date only (DEC-67): the
    event that opens the passi di competenza (V12). The text of the Carta comes later
    (phase 6)."""

    periodo = models.OneToOneField(
        PeriodoBranca, on_delete=models.CASCADE, related_name="firma_carta"
    )
    data = _data()
    precisione = _precisione()
    registrata_da = _utente()
    nota_rettifica = models.CharField(max_length=300, blank=True)

    class Meta:
        verbose_name = "firma della Carta di clan"
        verbose_name_plural = "firme della Carta di clan"

    def __str__(self) -> str:
        return f"Carta di clan di {self.periodo.persona}"


class PuntoStrada(ModelloTracciato):
    """A Punto della Strada, simple and repeatable (DEC-67, art. 39): a dated reading of
    the way, the service verified, the obiettivi set or recalibrated. `riservato` holds
    what was faced in confidence with the capi and the AE: only the R/S and the capi see
    it (DEC-180, V15); the summary follows the usual rules."""

    periodo = models.ForeignKey(
        PeriodoBranca, on_delete=models.CASCADE, related_name="punti_strada"
    )
    data = _data()
    sintesi = models.TextField(blank=True)
    servizio = models.TextField(blank=True)
    riservato = models.TextField(blank=True)
    # The rover's or scolta's own reading, written by them; read like `riservato`
    # (DEC-188, spec §11.2 "voce del ragazzo").
    voce = models.TextField(blank=True)
    obiettivi = models.ManyToManyField(Obiettivo, blank=True, related_name="punti_strada")
    creato_da = _utente()

    class Meta:
        verbose_name = "Punto della Strada"
        verbose_name_plural = "Punti della Strada"
        ordering = ["data", "creato_il"]

    def __str__(self) -> str:
        return f"Punto della Strada di {self.periodo.persona} del {self.data:%d/%m/%Y}"


class TipoConclusione(models.TextChoices):
    """Spec §16.2 ClosureKind: none is a failure, none is automatic (V14)."""

    PARTENZA = "PARTENZA", "Partenza"
    SALUTO_FRATERNO = "SALUTO_FRATERNO", "Saluto fraterno"
    INTERRUZIONE = "INTERRUZIONE", "Interruzione"
    TRASFERIMENTO = "TRASFERIMENTO", "Trasferimento"


class Conclusione(ModelloTracciato):
    """How the R/S way ends, with type and date (DEC-67): it closes the branch period
    only, the clan membership is BuonaStrada's (DEC-181)."""

    periodo = models.OneToOneField(
        PeriodoBranca, on_delete=models.CASCADE, related_name="conclusione"
    )
    tipo = models.CharField(max_length=16, choices=TipoConclusione.choices)
    data = _data()
    precisione = _precisione()
    nota = models.CharField(max_length=300, blank=True)
    registrata_da = _utente()

    class Meta:
        verbose_name = "conclusione del percorso"
        verbose_name_plural = "conclusioni del percorso"

    def __str__(self) -> str:
        return f"{self.get_tipo_display()} di {self.periodo.persona}"


# --- L/C: stagione di caccia o di volo (DEC-66, DEC-182…; spec §4.2, §17.5) ----------------


class StatoStagione(models.TextChoices):
    PREVISTA = "PREVISTA", "In programma"
    APERTA = "APERTA", "Aperta"
    CHIUSA = "CHIUSA", "Chiusa"
    ANNULLATA = "ANNULLATA", "Annullata"


class Stagione(ModelloTracciato):
    """The common time of the branco or cerchio in which each child plays their prede
    or voli: opened by a festive launch after the Promesse, about three or four months,
    closed before the holidays (L/C art. 38). Closing it never conquers anything (V04):
    what is still open is listed for the capi to look at again."""

    unita = models.ForeignKey(
        "organizzazione.Unita", on_delete=models.PROTECT, related_name="stagioni"
    )
    nome = models.CharField(max_length=120)
    inizio_previsto = _data()
    fine_prevista = _data()
    stato = models.CharField(
        max_length=10, choices=StatoStagione.choices, default=StatoStagione.PREVISTA
    )
    lancio = _data(null=True, blank=True)
    chiusa_il = _data(null=True, blank=True)
    creata_da = _utente()

    class Meta:
        verbose_name = "stagione di caccia o di volo"
        verbose_name_plural = "stagioni di caccia o di volo"
        ordering = ["-inizio_previsto"]

    def __str__(self) -> str:
        return self.nome


# --- Attachments (DEC-42, DEC-202) ---------------------------------------------------------


class AllegatoPP(ModelloTracciato):
    """An image or a PDF on an impegno (preda, volo), a meta or obiettivo, a specialità
    or brevetto: uploaded by the staff or the ragazzo, read by who reads the item, at most
    10 MB, checked on its first bytes, random file name, served only by the API."""

    obiettivo = models.ForeignKey(
        Obiettivo, null=True, blank=True, on_delete=models.CASCADE, related_name="allegati"
    )
    impegno = models.ForeignKey(
        Impegno, null=True, blank=True, on_delete=models.CASCADE, related_name="allegati"
    )
    competenza = models.ForeignKey(
        PercorsoCompetenza, null=True, blank=True, on_delete=models.CASCADE, related_name="allegati"
    )
    file = models.FileField(upload_to="progressione/allegati/")
    tipo_file = models.CharField(max_length=30)
    # What it is, written by who uploads it (the original file name may hold names).
    titolo = models.CharField(max_length=120)
    caricato_da = _utente()

    class Meta:
        verbose_name = "allegato alla Progressione"
        verbose_name_plural = "allegati alla Progressione"
        ordering = ["creato_il"]

    def __str__(self) -> str:
        return self.titolo

    def clean(self) -> None:
        if (
            sum(x is not None for x in (self.obiettivo_id, self.impegno_id, self.competenza_id))
            != 1
        ):
            raise ValidationError("Un allegato va su una sola voce.")

    @property
    def voce(self):
        return self.obiettivo or self.impegno or self.competenza
