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


class MetaEG(Percorso):
    """A meta E/G (art. 33): introduced when the ragazzo can formulate it (V07). A
    private one (`riservata`) is seen only by the ragazzo, the parents and the capi
    (DEC-173)."""

    periodo = models.ForeignKey(PeriodoBranca, on_delete=models.CASCADE, related_name="mete")
    riservata = models.BooleanField(default=False)

    class Meta(Percorso.Meta):
        verbose_name = "meta"
        verbose_name_plural = "mete"

    def __str__(self) -> str:
        return f"Meta di {self.periodo.persona}"


class Impegno(Percorso):
    """An impegno E/G (art. 32): concrete, verifiable, limited in time; with or without
    a meta (V07), possibly serving several."""

    periodo = models.ForeignKey(PeriodoBranca, on_delete=models.CASCADE, related_name="impegni")
    criterio_verifica = models.TextField(blank=True)
    mete = models.ManyToManyField(MetaEG, blank=True, related_name="impegni")

    class Meta(Percorso.Meta):
        verbose_name = "impegno"
        verbose_name_plural = "impegni"

    def __str__(self) -> str:
        return f"Impegno di {self.periodo.persona}"


class Revisione(models.Model):
    """A former wording of an impegno or a meta (DEC-59): kept when the text changes."""

    meta = models.ForeignKey(
        MetaEG, null=True, blank=True, on_delete=models.CASCADE, related_name="revisioni"
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
