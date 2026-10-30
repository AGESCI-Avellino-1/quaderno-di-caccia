"""Fees, family discount, agevolazioni, payments and receipts (DEC-80…DEC-84, DEC-92).

- only the group sets the fee types (capigruppo and group treasurer), each type says
  who owes it (all members, ragazzi, capi, given units) (DEC-145);
- the monthly unit fee is one fee per chosen month (DEC-145);
- the family discount is a fixed amount per fee type, taken off the fee of every
  member of the family when at least two members of the family are in the group
  (siblings, a parent with their children, spouses), never on the national fee
  (DEC-146);
- a payment may cover several fees of the same family, also in part (deposits), with
  one receipt per payment (DEC-148);
- camp, outing and external event fees come with the events (phase 3): set by the
  capi of the event, also in instalments (e.g. two deposits on fixed dates and the
  balance before leaving), each instalment a fee with its due date
  (DEC-141).
"""

from datetime import date
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q, Sum

from apps.core.anno import AnnoAssociativo
from apps.core.models import ModelloTracciato

ZERO = Decimal("0.00")
CENTESIMO = Decimal("0.01")

NOMI_MESI = (
    "gennaio",
    "febbraio",
    "marzo",
    "aprile",
    "maggio",
    "giugno",
    "luglio",
    "agosto",
    "settembre",
    "ottobre",
    "novembre",
    "dicembre",
)
# Months in the order of the associative year (October first).
MESI_ANNO = (10, 11, 12, 1, 2, 3, 4, 5, 6, 7, 8, 9)


def _euro(**campi) -> models.DecimalField:
    return models.DecimalField(max_digits=8, decimal_places=2, **campi)


class CategoriaQuota(models.TextChoices):
    """DEC-80; BuonaCaccia's external events come later."""

    CENSIMENTO = "CENSIMENTO", "Censimento (quota nazionale)"
    GRUPPO = "GRUPPO", "Quota di gruppo"
    MENSILE = "MENSILE", "Quota mensile di unità"
    EVENTO = "EVENTO", "Quota di un evento"  # DEC-77


class Destinatari(models.TextChoices):
    TUTTI = "TUTTI", "Tutti i soci"
    RAGAZZI = "RAGAZZI", "Solo i ragazzi"
    CAPI = "CAPI", "Solo i capi"
    UNITA = "UNITA", "Le unità indicate"


class TipoQuota(ModelloTracciato):
    """A fee of an associative year, set by the group."""

    nome = models.CharField(max_length=120)
    categoria = models.CharField(max_length=12, choices=CategoriaQuota.choices)
    anno = models.PositiveSmallIntegerField(help_text="Anno associativo (anno in cui finisce).")
    importo = _euro(validators=[MinValueValidator(CENTESIMO)])
    # DEC-81: off every member's fee when the family has two or more members; 0 = none.
    sconto_famiglia = _euro(default=ZERO, validators=[MinValueValidator(ZERO)])
    destinatari = models.CharField(max_length=8, choices=Destinatari.choices)
    unita = models.ManyToManyField("organizzazione.Unita", blank=True, related_name="tipi_quota")
    # One due date for the year, or (monthly fee) the months and the day of the month.
    scadenza = models.DateField(null=True, blank=True)
    mesi = models.JSONField(default=list, blank=True)
    giorno_scadenza = models.PositiveSmallIntegerField(null=True, blank=True)
    # An event's fee (DEC-77): owed by its participants, in one or more instalments
    # [{"descrizione": "Primo acconto", "importo": "50.00", "scadenza": "2026-05-01"}].
    evento = models.OneToOneField(
        "eventi.Evento", null=True, blank=True, on_delete=models.CASCADE, related_name="quota"
    )
    rate = models.JSONField(default=list, blank=True)

    class Meta:
        verbose_name = "tipo di quota"
        verbose_name_plural = "tipi di quota"
        ordering = ["-anno", "categoria", "nome"]

    def __str__(self) -> str:
        return f"{self.nome} {AnnoAssociativo(self.anno).etichetta}"

    @property
    def anno_associativo(self) -> AnnoAssociativo:
        return AnnoAssociativo(self.anno)

    def clean(self) -> None:
        errori = []
        if self.categoria == CategoriaQuota.CENSIMENTO and self.sconto_famiglia:
            errori.append("La quota nazionale non ha lo sconto per la famiglia.")
        if self.importo is not None and self.sconto_famiglia > self.importo:
            errori.append("Lo sconto per la famiglia non può superare l'importo.")
        if self.categoria == CategoriaQuota.EVENTO:
            errori += self._errori_rate()
        elif self.categoria == CategoriaQuota.MENSILE:
            if not self.mesi or any(m not in MESI_ANNO for m in self.mesi):
                errori.append("Indica i mesi della quota mensile.")
            if not self.giorno_scadenza or not 1 <= self.giorno_scadenza <= 28:
                errori.append("Indica il giorno del mese entro cui pagare (da 1 a 28).")
        else:
            if self.scadenza is None:
                errori.append("Indica la scadenza.")
            elif not self.anno_associativo.contiene(self.scadenza):
                errori.append("La scadenza deve cadere nell'anno associativo della quota.")
        if errori:
            raise ValidationError(errori)

    def _errori_rate(self) -> list[str]:
        if self.evento_id is None:
            return ["La quota di un evento va collegata all'evento."]
        if not self.rate:
            return ["Indica almeno una rata."]
        errori, scadenze = [], set()
        for rata in self.rate:
            try:
                importo = Decimal(str(rata["importo"]))
                scadenza = date.fromisoformat(str(rata["scadenza"]))
            except KeyError, ValueError, ArithmeticError:
                return ["Ogni rata ha un importo e una scadenza."]
            if importo <= 0:
                errori.append("Gli importi delle rate devono essere positivi.")
            if scadenza in scadenze:
                errori.append("Due rate non possono scadere lo stesso giorno.")
            scadenze.add(scadenza)
        if not errori and self.sconto_famiglia > Decimal(str(self.rate_ordinate()[-1]["importo"])):
            errori.append("Lo sconto per la famiglia non può superare l'ultima rata.")
        return errori

    def rate_ordinate(self) -> list[dict]:
        return sorted(self.rate, key=lambda r: str(r["scadenza"]))

    def importo_del_periodo(self, periodo: date) -> Decimal:
        if self.categoria == CategoriaQuota.EVENTO:
            for rata in self.rate:
                if date.fromisoformat(str(rata["scadenza"])) == periodo:
                    return Decimal(str(rata["importo"]))
        return self.importo

    def periodi(self) -> list[tuple[date, date]]:
        """(period, due date) pairs. A yearly fee has one period, the start of the year;
        a monthly fee one per month, in the order of the year; an event's fee one per
        instalment, the period being its due date."""
        anno = self.anno_associativo
        if self.categoria == CategoriaQuota.EVENTO:
            return [(date.fromisoformat(str(r["scadenza"])),) * 2 for r in self.rate_ordinate()]
        if self.categoria != CategoriaQuota.MENSILE:
            return [(anno.inizio, self.scadenza)]
        periodi = []
        for mese in MESI_ANNO:
            if mese in self.mesi:
                anno_solare = anno.anno_fine - 1 if mese >= 10 else anno.anno_fine
                periodi.append(
                    (date(anno_solare, mese, 1), date(anno_solare, mese, self.giorno_scadenza))
                )
        return periodi


class QuotaQuerySet(models.QuerySet):
    def valide(self):
        return self.filter(annullata_il__isnull=True)


class Quota(ModelloTracciato):
    """What one member owes for one fee type and period. Amount and discount are
    copied at issue: later changes of the type do not touch issued fees."""

    tipo = models.ForeignKey(TipoQuota, on_delete=models.PROTECT, related_name="quote")
    persona = models.ForeignKey(
        "anagrafica.Persona", on_delete=models.PROTECT, related_name="quote"
    )
    periodo = models.DateField()  # first day of the month, or of the year
    scadenza = models.DateField()
    importo = _euro()
    sconto = _euro(default=ZERO)
    annullata_il = models.DateTimeField(null=True, blank=True)
    annullata_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    motivo_annullamento = models.CharField(max_length=300, blank=True)
    # The reminder before the due date (DEC-79), sent once.
    promemoria_il = models.DateField(null=True, blank=True)

    objects = QuotaQuerySet.as_manager()

    class Meta:
        verbose_name = "quota"
        verbose_name_plural = "quote"
        ordering = ["periodo", "tipo__nome"]
        constraints = [
            models.UniqueConstraint(fields=["tipo", "persona", "periodo"], name="quota_unica")
        ]

    def __str__(self) -> str:
        return f"{self.descrizione} — {self.persona}"

    @property
    def descrizione(self) -> str:
        if self.tipo.categoria == CategoriaQuota.MENSILE:
            return f"{self.tipo.nome}, {NOMI_MESI[self.periodo.month - 1]} {self.periodo.year}"
        if self.tipo.categoria == CategoriaQuota.EVENTO:
            rata = next(
                (
                    r
                    for r in self.tipo.rate
                    if date.fromisoformat(str(r["scadenza"])) == self.periodo
                ),
                None,
            )
            if rata and len(self.tipo.rate) > 1:
                return f"{self.tipo.nome}, {rata.get('descrizione') or 'rata'}"
            return self.tipo.nome
        return str(self.tipo)

    @property
    def agevolata(self) -> Decimal:
        agevolazione = getattr(self, "agevolazione", None)
        return agevolazione.importo if agevolazione else ZERO

    @property
    def dovuto(self) -> Decimal:
        """What the family pays: amount less discount and agevolazione (DEC-82: the part
        covered by the group's cash is not an income)."""
        return self.importo - self.sconto - self.agevolata

    @property
    def pagato(self) -> Decimal:
        totale = self.pagamenti.filter(pagamento__annullato_il__isnull=True).aggregate(
            totale=Sum("importo")
        )["totale"]
        return totale or ZERO

    @property
    def residuo(self) -> Decimal:
        return self.dovuto - self.pagato


class Agevolazione(ModelloTracciato):
    """The group's cash covers all or part of a fee (DEC-82). Decided by the Co.Ca.,
    recorded by a capogruppo or the group treasurer; the family sees the amount, the
    note stays with the Co.Ca."""

    quota = models.OneToOneField(Quota, on_delete=models.CASCADE, related_name="agevolazione")
    importo = _euro(validators=[MinValueValidator(CENTESIMO)])
    decisa_il = models.DateField(help_text="Data della decisione della Co.Ca.")
    nota = models.CharField(max_length=300, blank=True)
    registrata_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        verbose_name = "agevolazione"
        verbose_name_plural = "agevolazioni"

    def __str__(self) -> str:
        return f"Agevolazione di {self.importo} € su {self.quota}"

    def clean(self) -> None:
        if self.importo and self.importo > self.quota.importo - self.quota.sconto:
            raise ValidationError("L'agevolazione non può superare la quota.")


class LegameConiugale(ModelloTracciato):
    """Two spouses, both members, for the family discount when the app does not link
    them through a common child (DEC-81)."""

    persona = models.ForeignKey(
        "anagrafica.Persona", on_delete=models.CASCADE, related_name="legami_coniugali"
    )
    coniuge = models.ForeignKey("anagrafica.Persona", on_delete=models.CASCADE, related_name="+")

    class Meta:
        verbose_name = "legame coniugale"
        verbose_name_plural = "legami coniugali"
        constraints = [
            models.UniqueConstraint(fields=["persona", "coniuge"], name="coniugi_unici"),
            models.CheckConstraint(
                condition=Q(persona__lt=models.F("coniuge")), name="coniugi_in_ordine"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.persona} e {self.coniuge}"


class MetodoPagamento(models.TextChoices):
    """DEC-83: no payment inside the app, only the record of one made outside."""

    CONTANTI = "CONTANTI", "Contanti"
    BONIFICO = "BONIFICO", "Bonifico"
    ALTRO = "ALTRO", "Altro"


class Pagamento(ModelloTracciato):
    """Money received from a family, spread over one or more of its fees. Never edited:
    a mistake is fixed by cancelling it (its receipt number stays, marked cancelled)."""

    data = models.DateField()
    importo = _euro(validators=[MinValueValidator(CENTESIMO)])
    metodo = models.CharField(max_length=10, choices=MetodoPagamento.choices)
    versato_da = models.CharField(max_length=160, help_text="Chi ha pagato, per la ricevuta.")
    note = models.CharField(max_length=300, blank=True)
    registrato_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    # Receipt (DEC-84): numbered per associative year of the payment date.
    anno_ricevuta = models.PositiveSmallIntegerField()
    numero_ricevuta = models.PositiveIntegerField()
    ricevuta_inviata_il = models.DateTimeField(null=True, blank=True)
    annullato_il = models.DateTimeField(null=True, blank=True)
    annullato_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    motivo_annullamento = models.CharField(max_length=300, blank=True)

    class Meta:
        verbose_name = "pagamento"
        verbose_name_plural = "pagamenti"
        ordering = ["-data", "-numero_ricevuta"]
        constraints = [
            models.UniqueConstraint(
                fields=["anno_ricevuta", "numero_ricevuta"], name="ricevuta_unica"
            )
        ]

    def __str__(self) -> str:
        return f"Ricevuta {self.numero} ({self.importo} €)"

    @property
    def numero(self) -> str:
        """e.g. 2026-27/015 (DEC-84)."""
        return f"{self.anno_ricevuta - 1}-{str(self.anno_ricevuta)[-2:]}/{self.numero_ricevuta:03d}"


class RipartizionePagamento(models.Model):
    """The part of a payment that goes to one fee."""

    pagamento = models.ForeignKey(Pagamento, on_delete=models.CASCADE, related_name="righe")
    quota = models.ForeignKey(Quota, on_delete=models.PROTECT, related_name="pagamenti")
    importo = _euro(validators=[MinValueValidator(CENTESIMO)])

    class Meta:
        verbose_name = "ripartizione del pagamento"
        verbose_name_plural = "ripartizioni dei pagamenti"
        constraints = [
            models.UniqueConstraint(fields=["pagamento", "quota"], name="ripartizione_unica")
        ]

    def __str__(self) -> str:
        return f"{self.importo} € su {self.quota}"


class ContatoreRicevute(models.Model):
    """Last receipt number of an associative year."""

    anno = models.PositiveSmallIntegerField(unique=True)
    ultimo = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "contatore delle ricevute"
        verbose_name_plural = "contatori delle ricevute"

    def __str__(self) -> str:
        return f"Ricevute {AnnoAssociativo(self.anno).etichetta}: {self.ultimo}"
