"""Group structure: group, units, patrols, roles (DEC-10..DEC-18, DEC-34..DEC-37)."""

from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q

from apps.core.models import ModelloTracciato


class Branca(models.TextChoices):
    LC = "LC", "Lupetti e Coccinelle"
    EG = "EG", "Esploratori e Guide"
    RS = "RS", "Rover e Scolte"
    COCA = "COCA", "Comunità Capi"


class TipoUnita(models.TextChoices):
    BRANCO = "BRANCO", "Branco"
    CERCHIO = "CERCHIO", "Cerchio"
    BRANCO_CERCHIO = "BRANCO_CERCHIO", "Branco/Cerchio"
    REPARTO = "REPARTO", "Reparto"
    NOVIZIATO = "NOVIZIATO", "Noviziato"
    CLAN_FUOCO = "CLAN_FUOCO", "Clan/Fuoco"
    COMUNITA_CAPI = "COMUNITA_CAPI", "Comunità Capi"


BRANCA_DEL_TIPO = {
    TipoUnita.BRANCO: Branca.LC,
    TipoUnita.CERCHIO: Branca.LC,
    TipoUnita.BRANCO_CERCHIO: Branca.LC,
    TipoUnita.REPARTO: Branca.EG,
    TipoUnita.NOVIZIATO: Branca.RS,
    TipoUnita.CLAN_FUOCO: Branca.RS,
    TipoUnita.COMUNITA_CAPI: Branca.COCA,
}


class Composizione(models.TextChoices):
    MASCHILE = "M", "Maschile"
    FEMMINILE = "F", "Femminile"
    MISTA = "X", "Mista"


class Ambiente(models.TextChoices):
    GIUNGLA = "GIUNGLA", "Giungla"
    BOSCO = "BOSCO", "Bosco"
    NESSUNO = "NESSUNO", "Nessuno"


class Gruppo(ModelloTracciato):
    """The group owning this installation (one installation per group, DEC-107)."""

    denominazione = models.CharField(max_length=120)  # e.g. "Avellino 1"
    ordinale = models.CharField(max_length=10, blank=True)  # BuonaStrada ORDINALE, e.g. T0001
    zona = models.CharField(max_length=120, blank=True)
    regione = models.CharField(max_length=120, blank=True)
    codice_fiscale = models.CharField(max_length=16, blank=True)
    # Not in the BuonaStrada export: written only by the capigruppo (DEC-374).
    partita_iva = models.CharField(
        max_length=11,
        blank=True,
        validators=[
            RegexValidator(r"^\d{11}$", "La partita IVA è fatta di 11 cifre.", code="partita_iva")
        ],
    )
    denominazione_sociale = models.CharField(max_length=200, blank=True)
    rappresentante_legale = models.CharField(max_length=200, blank=True)
    # Reference date for age (DEC-37), default 30 April.
    mese_riferimento_eta = models.PositiveSmallIntegerField(default=4)
    giorno_riferimento_eta = models.PositiveSmallIntegerField(default=30)
    # How families pay (DEC-83, DEC-253), each way enabled on its own: cash to the capi,
    # bank transfer, PayPal. Checked and computed in quote/modi_pagamento.py.
    contanti_attivo = models.BooleanField(default=True)
    # Credit or debit cards to the capi (a POS): not every group has one.
    carte_attivo = models.BooleanField(default=False)
    bonifico_attivo = models.BooleanField(default=False)
    iban = models.CharField(max_length=34, blank=True)
    intestatario_conto = models.CharField(max_length=140, blank=True)
    # Optional, for payments from abroad.
    banca = models.CharField(max_length=140, blank=True)
    bic = models.CharField(max_length=11, blank=True)
    paypal_attivo = models.BooleanField(default=False)
    # The PayPal link, e.g. paypal.me (the name comes from before DEC-253).
    link_pagamento = models.URLField(blank=True)
    # PayPal's costs passed on to the family: none, a fixed amount, a percentage, or by
    # bands of amount ([{"fino_a": "10.00" | None, "quota": "0.25"}, …], ascending).
    paypal_maggiorazione = models.CharField(
        max_length=12,
        choices=[
            ("NESSUNA", "Nessuna"),
            ("FISSA", "Fissa"),
            ("PERCENTUALE", "In percentuale"),
            ("FASCE", "A fasce"),
        ],
        default="NESSUNA",
    )
    paypal_valore = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    paypal_fasce = models.JSONField(default=list, blank=True)
    # Letterhead of every print (the AGESCI forms, receipts), set by the capigruppo
    # (DEC-192).
    sede_indirizzo = models.CharField(max_length=200, blank=True)
    sede_cap = models.CharField(max_length=5, blank=True)
    sede_comune = models.CharField(max_length=120, blank=True)
    sede_provincia = models.CharField(max_length=2, blank=True)
    telefono = models.CharField(max_length=30, blank=True)
    cellulare = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    pec = models.EmailField(blank=True)
    sito = models.URLField(blank=True)
    runts_repertorio = models.CharField(max_length=30, blank=True)
    runts_data = models.DateField(null=True, blank=True)
    # A new Progetto Educativo di Gruppo is being written: only a label (DEC-343).
    peg_in_redazione = models.BooleanField(default=False)
    # PNG or JPEG, re-encoded by Pillow; served only to the prints.
    logo = models.ImageField(upload_to="gruppo/", blank=True)

    class Meta:
        verbose_name = "gruppo"
        verbose_name_plural = "gruppi"

    def __str__(self) -> str:
        return self.denominazione


# Default ages of each branch for the waiting list (DEC-260): minimum and maximum.
ETA_DELLA_BRANCA = {Branca.LC: (8, 11), Branca.EG: (12, 16), Branca.RS: (16, 20)}


class Unita(ModelloTracciato):
    gruppo = models.ForeignKey(Gruppo, on_delete=models.PROTECT, related_name="unita")
    # Given by the group, not by BuonaStrada, and it may repeat (e.g. "Reparto
    # Millennium"); optional only for the Co.Ca. (DEC-128).
    nome = models.CharField(max_length=120, blank=True)
    tipo = models.CharField(max_length=20, choices=TipoUnita.choices)
    composizione = models.CharField(max_length=1, choices=Composizione.choices)
    ambiente = models.CharField(max_length=10, choices=Ambiente.choices, default=Ambiente.NESSUNO)
    # BuonaStrada identifiers: unit code (CUN) and progressive (PROG).
    codice_unita = models.CharField(max_length=4, blank=True)
    progressivo = models.PositiveSmallIntegerField(null=True, blank=True)
    durata_anni = models.PositiveSmallIntegerField(null=True, blank=True)
    # Parallel units working together are two units linked by a note (DEC-36), both ways
    # and in pairs only: set through `servizi.collega` (DEC-279).
    collegata_a = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    nota_collegamento = models.CharField(max_length=200, blank=True)
    # Linked units with one cash box since this day (DEC-288), the same on both; None:
    # each unit has its own. Set only by cassa.servizi.unisci_casse / dividi_casse.
    cassa_comune_dal = models.DateField(null=True, blank=True)
    attiva = models.BooleanField(default=True)
    # Closed, with only archived people in its history: out of every list, back when one
    # of them returns (DEC-275).
    archiviata_il = models.DateField(null=True, blank=True)
    # Ages for the waiting list (DEC-260), at the reference date of DEC-37; None = the
    # branch's default (`ETA_DELLA_BRANCA`). Hints, never constraints.
    eta_minima = models.PositiveSmallIntegerField(null=True, blank=True)
    eta_massima = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        verbose_name = "unità"
        verbose_name_plural = "unità"
        constraints = [
            models.UniqueConstraint(
                fields=["gruppo", "codice_unita", "progressivo"],
                condition=~Q(codice_unita=""),
                name="unita_codice_buonastrada_unico",
            ),
        ]

    def __str__(self) -> str:
        """Type, name, code: "Clan/Fuoco Hirpinia (T1)" (DEC-128). The
        name is the group's and may repeat or be missing; the BuonaStrada code does not."""
        testo = f"{self.nome_tipo} {self.nome}".strip()
        return f"{testo} ({self.codice})" if self.codice else testo

    @property
    def nome_tipo(self) -> str:
        """A branco/cerchio is called by its setting once known (DEC-225)."""
        if self.tipo == TipoUnita.BRANCO_CERCHIO:
            return {Ambiente.GIUNGLA: "Branco", Ambiente.BOSCO: "Cerchio"}.get(
                self.ambiente, self.get_tipo_display()
            )
        return self.get_tipo_display()

    @property
    def senza_ambiente(self) -> bool:
        """An L/C unit whose setting (giungla or bosco) is not known yet (DEC-225)."""
        return BRANCA_DEL_TIPO.get(self.tipo) == Branca.LC and self.ambiente == Ambiente.NESSUNO

    @property
    def senza_nome(self) -> bool:
        """Created by the import: the group has still to name it (the Co.Ca. may not)."""
        return not self.nome.strip() and self.tipo != TipoUnita.COMUNITA_CAPI

    def clean(self) -> None:
        if not self.nome.strip() and self.tipo != TipoUnita.COMUNITA_CAPI:
            raise ValidationError("Dai un nome all'unità: solo la Co.Ca. può non averlo.")

    @property
    def codice(self) -> str:
        """BuonaStrada unit code, e.g. O1 for a reparto, G1 for the Co.Ca."""
        if not self.codice_unita:
            return ""
        return f"{self.codice_unita}{self.progressivo or ''}"

    @property
    def branca(self) -> Branca:
        return BRANCA_DEL_TIPO[TipoUnita(self.tipo)]

    @property
    def eta(self) -> tuple[int, int] | None:
        """Minimum and maximum age for the waiting list; None for the Co.Ca."""
        base = ETA_DELLA_BRANCA.get(self.branca)
        if base is None:
            return None
        return (self.eta_minima or base[0], self.eta_massima or base[1])

    @property
    def diarchia(self) -> bool:
        """Mixed units have two unit leaders; single-sex units have one."""
        return self.composizione == Composizione.MISTA or self.tipo == TipoUnita.COMUNITA_CAPI


class TipoAnimale(models.TextChoices):
    GENERALE = "GENERALE", "Generale"
    NAUTICO = "NAUTICO", "Nautico"


class AnimaleSquadriglia(ModelloTracciato):
    """An animal a patrol takes its name from: one list for the group, starting from the
    catalog (DEC-350). Chosen by a patrol, even a closed one, it is switched off and not
    deleted (DEC-352). Its image is `simbolo`, shipped with the app, or `immagine`, uploaded
    and cleaned (DEC-354)."""

    nome = models.CharField(max_length=60, unique=True)
    # The patrol's name (DEC-351).
    plurale = models.CharField(max_length=80, unique=True)
    tipo = models.CharField(max_length=8, choices=TipoAnimale.choices, default=TipoAnimale.GENERALE)
    colore_1 = models.CharField(max_length=20, blank=True)
    significato_1 = models.CharField(max_length=200, blank=True)
    colore_2 = models.CharField(max_length=20, blank=True)
    significato_2 = models.CharField(max_length=200, blank=True)
    richiamo = models.CharField(max_length=200, blank=True)
    simbolo = models.SlugField(max_length=60, blank=True)
    immagine = models.FileField(upload_to="animali/", blank=True)
    attivo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "animale di squadriglia"
        verbose_name_plural = "animali di squadriglia"
        ordering = ["nome"]

    def __str__(self) -> str:
        return self.nome

    def clean(self) -> None:
        from .animali import COLORI

        for colore in (self.colore_1, self.colore_2):
            if colore and colore not in COLORI:
                raise ValidationError(f"«{colore}» non è tra i colori proposti.")


class Squadriglia(ModelloTracciato):
    """Single-sex patrol inside a Reparto (no diarchy)."""

    unita = models.ForeignKey(Unita, on_delete=models.PROTECT, related_name="squadriglie")
    # With an animal, its plural (DEC-351). Without one, a name from before the animals.
    nome = models.CharField(max_length=80)
    animale = models.ForeignKey(
        AnimaleSquadriglia,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="squadriglie",
    )
    sesso = models.CharField(max_length=1, choices=[("M", "Maschile"), ("F", "Femminile")])
    attiva = models.BooleanField(default=True)

    class Meta:
        verbose_name = "squadriglia"
        verbose_name_plural = "squadriglie"
        constraints = [
            models.UniqueConstraint(fields=["unita", "nome"], name="squadriglia_nome_unico"),
        ]

    def __str__(self) -> str:
        return f"Sq. {self.nome}"

    def clean(self) -> None:
        if self.unita_id and self.unita.tipo != TipoUnita.REPARTO:
            raise ValidationError("Una squadriglia appartiene sempre a un reparto.")


class RuoloIncarico(models.TextChoices):
    """Service roles (in a unit, or at the disposal of the Co.Ca.) and additional roles
    (capogruppo, treasurers, technical administrator), which add up freely: one capo may
    be capogruppo, capo unità, treasurer and administrator at once (DEC-165). CSQ, VCSQ
    and the other patrol roles are the ragazzi's."""

    CAPOGRUPPO = "CAPOGRUPPO", "Capogruppo"
    # The group's assistente ecclesiastico: the powers of a capogruppo everywhere,
    # appointed by the capigruppo (DEC-281).
    AE_GRUPPO = "AE_GRUPPO", "Assistente ecclesiastico di gruppo"
    TESORIERE_GRUPPO = "TESORIERE_GRUPPO", "Tesoriere di gruppo"
    CAPO_UNITA = "CAPO_UNITA", "Capo unità"
    # The capi serving a unit (DEC-09, DEC-10). An Incarico, not an Appartenenza: capi
    # belong to the Co.Ca. from the BuonaStrada import, and a second CAPO membership
    # would look to the import like a change of unit.
    STAFF = "STAFF", "Staff di unità"
    TESORIERE_UNITA = "TESORIERE_UNITA", "Tesoriere di unità"
    # A unit's assistente ecclesiastico: counts as its staff, appointed by the capo unità
    # and the capigruppo (DEC-281).
    AE_UNITA = "AE_UNITA", "Assistente ecclesiastico di unità"
    # The service of a capo of the Co.Ca. outside the units, one of the two; excludes any
    # unit service (DEC-165, DEC-293).
    SUPPORTO_GRUPPO = "SUPPORTO_GRUPPO", "Servizio di supporto al gruppo"
    SUPPORTO_EDUCATIVO = "SUPPORTO_EDUCATIVO", "Servizio di supporto all'azione educativa"
    # Replaced by the two above (DEC-293): no longer assigned, kept for the history.
    A_DISPOSIZIONE = "A_DISPOSIZIONE", "A disposizione"
    # Appointed by the capigruppo; the first one is created from the command line
    # (User.amministratore_tecnico). Always a capo (DEC-12, DEC-114, DEC-166).
    AMMINISTRATORE = "AMMINISTRATORE", "Amministratore tecnico"
    CSQ = "CSQ", "Capo squadriglia"
    VCSQ = "VCSQ", "Vice capo squadriglia"
    # The other patrol roles (DEC-321): several holders, no permissions at all.
    CASSIERE = "CASSIERE", "Cassiere"
    CICALA = "CICALA", "Cicala"
    CRONISTA = "CRONISTA", "Cronista"
    GUARDIANO_ANGOLO = "GUARDIANO_ANGOLO", "Guardiano dell'angolo"
    GUARDIANO_STILE = "GUARDIANO_STILE", "Guardiano dello stile"
    GUARDIANO_TEMPO = "GUARDIANO_TEMPO", "Guardiano del tempo"
    INFERMIERE = "INFERMIERE", "Infermiere"
    LITURGISTA = "LITURGISTA", "Liturgista"
    MAGAZZINIERE = "MAGAZZINIERE", "Magazziniere"
    AIUTO_MAGAZZINIERE = "AIUTO_MAGAZZINIERE", "Aiuto magazziniere"
    MERCURIO = "MERCURIO", "Mercurio"
    # A lupetto or coccinella of a branco or cerchio, appointed by its staff (DEC-66,
    # DEC-182).
    CONSIGLIO_ANZIANI = "CONSIGLIO_ANZIANI", "Consiglio degli Anziani"
    # A role the capigruppo defined (DEC-347): the name and the rest are on Incarico.tipo. No
    # permission asks for it, so it gives none.
    DEFINITO = "DEFINITO", "Incarico definito dal gruppo"


# Maximum number of simultaneous holders. None = depends on the unit (diarchy).
# Roles missing here (STAFF) have no limit.
TITOLARI_MASSIMI = {
    RuoloIncarico.CAPOGRUPPO: 2,  # diarchy (DEC-18)
    RuoloIncarico.TESORIERE_GRUPPO: 2,
    RuoloIncarico.CAPO_UNITA: None,
    RuoloIncarico.TESORIERE_UNITA: 2,
    RuoloIncarico.CSQ: 1,
    RuoloIncarico.VCSQ: 1,
}

RUOLI_DI_GRUPPO = {
    RuoloIncarico.CAPOGRUPPO,
    RuoloIncarico.AE_GRUPPO,
    RuoloIncarico.TESORIERE_GRUPPO,
    RuoloIncarico.SUPPORTO_GRUPPO,
    RuoloIncarico.SUPPORTO_EDUCATIVO,
    RuoloIncarico.A_DISPOSIZIONE,
    RuoloIncarico.AMMINISTRATORE,
}
RUOLI_DI_UNITA = {
    RuoloIncarico.CAPO_UNITA,
    RuoloIncarico.AE_UNITA,
    RuoloIncarico.TESORIERE_UNITA,
    RuoloIncarico.STAFF,
    RuoloIncarico.CONSIGLIO_ANZIANI,
}
GUIDE_DI_SQUADRIGLIA = {RuoloIncarico.CSQ, RuoloIncarico.VCSQ}
INCARICHI_DI_SQUADRIGLIA = {
    RuoloIncarico.CASSIERE,
    RuoloIncarico.CICALA,
    RuoloIncarico.CRONISTA,
    RuoloIncarico.GUARDIANO_ANGOLO,
    RuoloIncarico.GUARDIANO_STILE,
    RuoloIncarico.GUARDIANO_TEMPO,
    RuoloIncarico.INFERMIERE,
    RuoloIncarico.LITURGISTA,
    RuoloIncarico.MAGAZZINIERE,
    RuoloIncarico.AIUTO_MAGAZZINIERE,
    RuoloIncarico.MERCURIO,
}
RUOLI_DI_SQUADRIGLIA = GUIDE_DI_SQUADRIGLIA | INCARICHI_DI_SQUADRIGLIA
# Outside the units: one at a time, never with a unit service (DEC-165, DEC-293).
SERVIZI_DI_SUPPORTO = {
    RuoloIncarico.SUPPORTO_GRUPPO,
    RuoloIncarico.SUPPORTO_EDUCATIVO,
    RuoloIncarico.A_DISPOSIZIONE,
}
# Every capo of the Co.Ca. has a service: one or more units, or a support service (not
# both, DEC-165, DEC-293); the assistenti ecclesiastici serve the group or a unit (DEC-281).
SERVIZIO_IN_UNITA = {RuoloIncarico.CAPO_UNITA, RuoloIncarico.STAFF, RuoloIncarico.AE_UNITA}
INCARICHI_DI_SERVIZIO = SERVIZIO_IN_UNITA | SERVIZI_DI_SUPPORTO | {RuoloIncarico.AE_GRUPPO}
RUOLI_AGGIUNTIVI = {
    RuoloIncarico.CAPOGRUPPO,
    RuoloIncarico.AE_GRUPPO,
    RuoloIncarico.TESORIERE_GRUPPO,
    RuoloIncarico.TESORIERE_UNITA,
    RuoloIncarico.AMMINISTRATORE,
}


class AmbitoIncarico(models.TextChoices):
    GRUPPO = "GRUPPO", "Di gruppo"
    UNITA = "UNITA", "Di unità"


# How the API names a role the group defined, next to the plain RuoloIncarico values.
PREFISSO_DEFINITO = f"{RuoloIncarico.DEFINITO.value}:"
# The support services, the group's own included (DEC-348).
Q_SERVIZI_SUPPORTO = models.Q(ruolo__in=SERVIZI_DI_SUPPORTO) | models.Q(
    tipo__di_servizio=True, tipo__ambito=AmbitoIncarico.GRUPPO
)
# Who serves in a unit as far as services go, the group's own roles included (DEC-348).
Q_SERVIZI_IN_UNITA = models.Q(ruolo__in=SERVIZIO_IN_UNITA) | models.Q(
    tipo__di_servizio=True, tipo__ambito=AmbitoIncarico.UNITA
)


class TipoIncarico(ModelloTracciato):
    """A role the capigruppo defined for capi, on top of the fixed ones (DEC-347). It gives
    no permission. What a role in use is (group or unit, service or not) no longer changes:
    its history would change meaning. A role in use is switched off, never deleted."""

    nome = models.CharField(max_length=80, unique=True)
    ambito = models.CharField(max_length=6, choices=AmbitoIncarico.choices)
    # A group one works like a support service, a unit one counts like the staff for the
    # services, without the staff's permissions (DEC-348).
    di_servizio = models.BooleanField(default=False)
    # Only for the quick choice in the PDF list of the roles (DEC-349).
    educativo = models.BooleanField(default=True)
    attivo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "tipo di incarico"
        verbose_name_plural = "tipi di incarico"
        ordering = ["nome"]

    def __str__(self) -> str:
        return self.nome

    @property
    def codice(self) -> str:
        return f"{PREFISSO_DEFINITO}{self.pk}"

    def clean(self) -> None:
        self.nome = self.nome.strip()
        if self.nome.casefold() in {r.label.casefold() for r in RuoloIncarico}:
            raise ValidationError(f"«{self.nome}» è già un incarico dell'app.")
        if not self.pk or not self.incarichi.exists():
            return
        prima = TipoIncarico.objects.get(pk=self.pk)
        if prima.ambito != self.ambito or prima.di_servizio != self.di_servizio:
            raise ValidationError(
                "Questo incarico è già stato assegnato: non può cambiare tra gruppo e unità, né "
                "tra di servizio e aggiuntivo. Disattivalo e definiscine un altro."
            )


class IncaricoQuerySet(models.QuerySet):
    def attivi(self, al_giorno: date | None = None):
        giorno = al_giorno or date.today()
        return self.filter(data_inizio__lte=giorno).filter(
            Q(data_fine__isnull=True) | Q(data_fine__gt=giorno)
        )


class Incarico(ModelloTracciato):
    """A role held by a person for a period. Diarchy = up to two concurrent holders;
    a vacant seat is simply a missing holder (DEC-18)."""

    persona = models.ForeignKey(
        "anagrafica.Persona", on_delete=models.PROTECT, related_name="incarichi"
    )
    ruolo = models.CharField(max_length=20, choices=RuoloIncarico.choices)
    gruppo = models.ForeignKey(
        Gruppo, null=True, blank=True, on_delete=models.PROTECT, related_name="incarichi"
    )
    unita = models.ForeignKey(
        Unita, null=True, blank=True, on_delete=models.PROTECT, related_name="incarichi"
    )
    squadriglia = models.ForeignKey(
        Squadriglia, null=True, blank=True, on_delete=models.PROTECT, related_name="incarichi"
    )
    # Only with the role DEFINITO (DEC-347).
    tipo = models.ForeignKey(
        TipoIncarico, null=True, blank=True, on_delete=models.PROTECT, related_name="incarichi"
    )
    data_inizio = models.DateField(default=date.today)
    # End date is exclusive; null = still active.
    data_fine = models.DateField(null=True, blank=True)

    objects = IncaricoQuerySet.as_manager()

    class Meta:
        verbose_name = "incarico"
        verbose_name_plural = "incarichi"

    def __str__(self) -> str:
        return f"{self.get_ruolo_display()} — {self.persona}"

    def get_ruolo_display(self) -> str:
        """The name of the role, the group's own too: every reader goes through here."""
        if self.tipo_id:
            return self.tipo.nome
        return RuoloIncarico(self.ruolo).label

    @property
    def codice_ruolo(self) -> str:
        """The role as the API and the PDF list name it."""
        return self.tipo.codice if self.tipo_id else str(RuoloIncarico(self.ruolo).value)

    @property
    def e_di_servizio(self) -> bool:
        """Whether the capo has a service through this role (DEC-165, DEC-348)."""
        return self.ruolo in INCARICHI_DI_SERVIZIO or bool(self.tipo_id and self.tipo.di_servizio)

    def clean(self) -> None:
        ruolo = RuoloIncarico(self.ruolo)
        self._controlla_tipo(ruolo)
        if ruolo in RUOLI_DI_GRUPPO and not self.gruppo_id:
            raise ValidationError("Un incarico di gruppo richiede il gruppo.")
        if ruolo in RUOLI_DI_UNITA and not self.unita_id:
            raise ValidationError("Un incarico di unità richiede l'unità.")
        if ruolo in RUOLI_DI_SQUADRIGLIA and not self.squadriglia_id:
            raise ValidationError("Un incarico di squadriglia richiede la squadriglia.")
        if self.data_fine and self.data_fine <= self.data_inizio:
            raise ValidationError("La data di fine deve seguire quella di inizio.")
        self._controlla_servizio(ruolo)
        if self._state.adding:
            # Only on appointment: closing the role of someone who has meanwhile left
            # the service must stay possible (DEC-20).
            self._controlla_titolare(ruolo)
        concorrenti = (
            Incarico.objects.attivi(self.data_inizio)
            .filter(
                ruolo=self.ruolo,
                gruppo=self.gruppo_id,
                unita=self.unita_id,
                squadriglia=self.squadriglia_id,
                tipo=self.tipo_id,
            )
            .exclude(pk=self.pk)
        )
        if concorrenti.filter(persona=self.persona_id).exists():
            raise ValidationError(f"{self.persona} ha già questo incarico.")
        massimo = self.titolari_massimi()
        if massimo is not None and concorrenti.count() >= massimo:
            raise ValidationError(
                f"Il ruolo {self.get_ruolo_display()} ammette al massimo {massimo} titolari."
            )

    def _controlla_tipo(self, ruolo: RuoloIncarico) -> None:
        """A role the group defined needs its type, in the place the type says (DEC-347)."""
        if ruolo != RuoloIncarico.DEFINITO:
            if self.tipo_id:
                raise ValidationError("Solo un incarico definito dal gruppo ha un tipo.")
            return
        if not self.tipo_id:
            raise ValidationError("Scegli l'incarico definito dal gruppo.")
        if self._state.adding and not self.tipo.attivo:
            raise ValidationError(f"L'incarico {self.tipo} è disattivato: non si assegna più.")
        if self.tipo.ambito == AmbitoIncarico.GRUPPO:
            if not self.gruppo_id or self.unita_id:
                raise ValidationError("Un incarico di gruppo richiede il gruppo.")
            return
        if not self.unita_id or self.gruppo_id:
            raise ValidationError("Un incarico di unità richiede l'unità.")
        if self.unita.tipo == TipoUnita.COMUNITA_CAPI:
            raise ValidationError("In Comunità capi si assegnano gli incarichi di gruppo.")

    def _controlla_servizio(self, ruolo: RuoloIncarico) -> None:
        """A support service excludes service in a unit and the other support services; the
        roles the group defined as services follow the same rule (DEC-348)."""
        tipo_servizio = self.tipo if self.tipo_id and self.tipo.di_servizio else None
        supporto = ruolo in SERVIZI_DI_SUPPORTO or (
            tipo_servizio is not None and tipo_servizio.ambito == AmbitoIncarico.GRUPPO
        )
        in_unita = ruolo in SERVIZIO_IN_UNITA or (
            tipo_servizio is not None and tipo_servizio.ambito == AmbitoIncarico.UNITA
        )
        if supporto:
            altri = Q_SERVIZI_IN_UNITA
            messaggio = "fa servizio in un'unità: chiudi prima quell'incarico."
            # The same one twice is "already holds this role", further on in clean().
            if (
                self._sovrapposti(Q_SERVIZI_SUPPORTO)
                .exclude(ruolo=ruolo, tipo=self.tipo_id)
                .exists()
            ):
                raise ValidationError(
                    f"{self.persona} ha già un servizio di supporto: chiudi prima quello."
                )
        elif in_unita:
            altri = Q_SERVIZI_SUPPORTO
            messaggio = "ha un servizio di supporto: chiudi prima quell'incarico."
        else:
            return
        if self._sovrapposti(altri).exists():
            raise ValidationError(f"{self.persona} {messaggio}")

    def _sovrapposti(self, filtro: Q):
        """The person's roles matching `filtro` overlapping this one's period."""
        sovrapposti = (
            Incarico.objects.filter(filtro, persona=self.persona_id)
            .filter(Q(data_fine__isnull=True) | Q(data_fine__gt=self.data_inizio))
            .exclude(pk=self.pk)
        )
        if self.data_fine:
            sovrapposti = sovrapposti.filter(data_inizio__lt=self.data_fine)
        return sovrapposti

    def titolari_massimi(self) -> int | None:
        """Holders allowed at the same time; None = no limit (staff)."""
        ruolo = RuoloIncarico(self.ruolo)
        if ruolo not in TITOLARI_MASSIMI:
            return None
        massimo = TITOLARI_MASSIMI[ruolo]
        if massimo is None:
            return 2 if self.unita and self.unita.diarchia else 1
        return massimo

    def _controlla_titolare(self, ruolo: RuoloIncarico) -> None:
        """Who may hold the role on its start date: roles of capi go to capi (DEC-09,
        DEC-10, DEC-11); a R/S unit treasurer may be a rover or scolta of that unit
        (DEC-11); patrol roles go to members of the patrol (DEC-13, DEC-14, DEC-321); the
        Consiglio degli Anziani is made of the unit's lupetti and coccinelle (DEC-182)."""
        from apps.anagrafica.models import (
            Appartenenza,
            AppartenenzaSquadriglia,
            RuoloAppartenenza,
        )

        if not self.persona_id:
            return
        attive = Appartenenza.objects.attive(self.data_inizio).filter(persona=self.persona_id)
        e_capo = attive.filter(ruolo=RuoloAppartenenza.CAPO).exists()
        if ruolo in RUOLI_DI_SQUADRIGLIA:
            if not attive.filter(
                ruolo=RuoloAppartenenza.RAGAZZO, unita=self.squadriglia.unita_id
            ).exists():
                raise ValidationError(
                    f"{self.persona} non è un ragazzo o una ragazza di {self.squadriglia.unita}."
                )
            if (
                not AppartenenzaSquadriglia.objects.attive(self.data_inizio)
                .filter(persona=self.persona_id, squadriglia=self.squadriglia_id)
                .exists()
            ):
                raise ValidationError(f"{self.persona} non fa parte di {self.squadriglia}.")
            return
        if ruolo == RuoloIncarico.CONSIGLIO_ANZIANI:
            if self.unita.branca != Branca.LC:
                raise ValidationError("Il Consiglio degli Anziani è di un branco o un cerchio.")
            if attive.filter(ruolo=RuoloAppartenenza.RAGAZZO, unita=self.unita).exists():
                return
            raise ValidationError(f"{self.persona} non è un bambino o una bambina di {self.unita}.")
        if ruolo == RuoloIncarico.TESORIERE_UNITA and self.unita.branca == Branca.RS:
            if e_capo or attive.filter(ruolo=RuoloAppartenenza.RAGAZZO, unita=self.unita).exists():
                return
            raise ValidationError(
                f"{self.persona} non è un capo né un rover o una scolta di {self.unita}."
            )
        if not e_capo:
            raise ValidationError(
                f"{self.persona} non risulta capo: l'incarico di "
                f"{self.get_ruolo_display().lower()} spetta a un capo."
            )
        if ruolo in {RuoloIncarico.AE_GRUPPO, RuoloIncarico.AE_UNITA}:
            from apps.anagrafica.models import e_presbitero

            # Only a presbitero, by the profession from BuonaStrada (DEC-296).
            if not e_presbitero(self.persona.professione):
                raise ValidationError(
                    f"Solo un presbitero può essere assistente ecclesiastico: nella scheda di "
                    f"{self.persona} la professione non è «Presbitero». Se serve, correggila prima."
                )


class AnnoChiuso(ModelloTracciato):
    """An associative year closed by a capogruppo (DEC-45, DEC-209): from then on its
    attendance, Progressione, fees and cash book do not change. A capogruppo may reopen
    it with a reason until a date of their choice (at most 30 days, DEC-210)."""

    # By its end year, as BuonaStrada (2025/26 = 2026).
    anno = models.PositiveSmallIntegerField(unique=True)
    chiuso_il = models.DateTimeField()
    chiuso_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    riaperto_fino_al = models.DateTimeField(null=True, blank=True)
    motivo_riapertura = models.CharField(max_length=300, blank=True)
    riaperto_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        verbose_name = "anno associativo chiuso"
        verbose_name_plural = "anni associativi chiusi"
        ordering = ["-anno"]

    def __str__(self) -> str:
        return f"Anno {self.anno - 1}/{str(self.anno)[-2:]}"

    @property
    def riaperto(self) -> bool:
        from django.utils import timezone

        return self.riaperto_fino_al is not None and self.riaperto_fino_al > timezone.now()
