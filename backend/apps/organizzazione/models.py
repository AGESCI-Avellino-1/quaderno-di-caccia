"""Group structure: group, units, patrols, roles (DEC-10..DEC-18, DEC-34..DEC-37)."""

from datetime import date

from django.core.exceptions import ValidationError
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
    denominazione_sociale = models.CharField(max_length=200, blank=True)
    rappresentante_legale = models.CharField(max_length=200, blank=True)
    # Reference date for age (DEC-37), default 30 April.
    mese_riferimento_eta = models.PositiveSmallIntegerField(default=4)
    giorno_riferimento_eta = models.PositiveSmallIntegerField(default=30)
    # A link where families pay outside the app, e.g. paypal.me (DEC-83).
    link_pagamento = models.URLField(blank=True)

    class Meta:
        verbose_name = "gruppo"
        verbose_name_plural = "gruppi"

    def __str__(self) -> str:
        return self.denominazione


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
    # Parallel male/female units working together are two units linked by a note (DEC-36).
    collegata_a = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    nota_collegamento = models.CharField(max_length=200, blank=True)
    attiva = models.BooleanField(default=True)

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
        testo = f"{self.get_tipo_display()} {self.nome}".strip()
        return f"{testo} ({self.codice})" if self.codice else testo

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
    def diarchia(self) -> bool:
        """Mixed units have two unit leaders; single-sex units have one."""
        return self.composizione == Composizione.MISTA or self.tipo == TipoUnita.COMUNITA_CAPI


class Squadriglia(ModelloTracciato):
    """Single-sex patrol inside a Reparto (no diarchy)."""

    unita = models.ForeignKey(Unita, on_delete=models.PROTECT, related_name="squadriglie")
    nome = models.CharField(max_length=80)
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
    CAPOGRUPPO = "CAPOGRUPPO", "Capogruppo"
    TESORIERE_GRUPPO = "TESORIERE_GRUPPO", "Tesoriere di gruppo"
    CAPO_UNITA = "CAPO_UNITA", "Capo unità"
    # The capi serving a unit (DEC-09, DEC-10). An Incarico, not an Appartenenza: capi
    # belong to the Co.Ca. from the BuonaStrada import, and a second CAPO membership
    # would look to the import like a change of unit.
    STAFF = "STAFF", "Staff di unità"
    TESORIERE_UNITA = "TESORIERE_UNITA", "Tesoriere di unità"
    CSQ = "CSQ", "Capo squadriglia"
    VCSQ = "VCSQ", "Vice capo squadriglia"


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

RUOLI_DI_GRUPPO = {RuoloIncarico.CAPOGRUPPO, RuoloIncarico.TESORIERE_GRUPPO}
RUOLI_DI_UNITA = {RuoloIncarico.CAPO_UNITA, RuoloIncarico.TESORIERE_UNITA, RuoloIncarico.STAFF}
RUOLI_DI_SQUADRIGLIA = {RuoloIncarico.CSQ, RuoloIncarico.VCSQ}


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
    data_inizio = models.DateField(default=date.today)
    # End date is exclusive; null = still active.
    data_fine = models.DateField(null=True, blank=True)

    objects = IncaricoQuerySet.as_manager()

    class Meta:
        verbose_name = "incarico"
        verbose_name_plural = "incarichi"

    def __str__(self) -> str:
        return f"{self.get_ruolo_display()} — {self.persona}"

    def clean(self) -> None:
        ruolo = RuoloIncarico(self.ruolo)
        if ruolo in RUOLI_DI_GRUPPO and not self.gruppo_id:
            raise ValidationError("Un incarico di gruppo richiede il gruppo.")
        if ruolo in RUOLI_DI_UNITA and not self.unita_id:
            raise ValidationError("Un incarico di unità richiede l'unità.")
        if ruolo in RUOLI_DI_SQUADRIGLIA and not self.squadriglia_id:
            raise ValidationError("Un incarico di squadriglia richiede la squadriglia.")
        if self.data_fine and self.data_fine <= self.data_inizio:
            raise ValidationError("La data di fine deve seguire quella di inizio.")
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
        (DEC-11); CSQ and VCSQ are members of their patrol (DEC-13, DEC-14)."""
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
