"""Events, recurring meetings, participants and attendance (DEC-75, DEC-78).

- participants are by default all the members of the units involved (the whole group
  for a group event) (DEC-137);
- the family (or the adult member) says the member will not take part; the staff (the
  Co.Ca. for group events) may not invite a member, with a reason the family sees
  (DEC-137);
- attendance is present, absent or excused, marked by capi only, also offline, at
  recurring meetings and at every other event (for a camp, once for the event)
  (DEC-138);
- BuonaCaccia events are external events with single participants, recorded by the
  staff (minors) or the adult themself (DEC-144, DEC-158…DEC-164, `apps.buonacaccia`);
- patrol meetings are patrol events: the CSQ, a member they delegate (to create them
  only) or the reparto staff create them, and the CSQ marks their attendance; the staff
  also creates the patrol's mission (with notes for the parents the ragazzi do not
  see) and other activities of one patrol (DEC-139);
- the staff creates events for the Consiglio Capi (CSQ), the Con.Ca.Vi. (CSQ and
  VCSQ) and the Alta Squadriglia (chosen by the staff each year), of one or more
  reparti of the group (DEC-140);
- meetings are not events for who uses the app (DEC-310): their own page, never a fee.
  Each one is still an `Evento` of type RIUNIONE, so attendance, the calendar and the
  offline copy are the same; a series (`RiunioneRicorrente`) has its kind, its place and
  whether the uniform is worn, which a single meeting may change.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import ModelloTracciato
from apps.organizzazione.models import Branca


class Livello(models.TextChoices):
    """DEC-75."""

    GRUPPO = "GRUPPO", "Gruppo"
    BRANCA = "BRANCA", "Branca"
    UNITA = "UNITA", "Unità"
    SQUADRIGLIA = "SQUADRIGLIA", "Squadriglia"
    # Organised outside the group, on BuonaCaccia (DEC-158): single participants.
    ESTERNO = "ESTERNO", "Evento su BuonaCaccia"


class TipoEvento(models.TextChoices):
    RIUNIONE = "RIUNIONE", "Riunione"
    USCITA = "USCITA", "Uscita"
    CAMPO = "CAMPO", "Campo"
    AUTOFINANZIAMENTO = "AUTOFINANZIAMENTO", "Autofinanziamento"  # DEC-90
    MISSIONE = "MISSIONE", "Missione di squadriglia"
    ALTRO = "ALTRO", "Altro evento"


class Cerchia(models.TextChoices):
    """Who of the reparti involved is invited."""

    TUTTI = "TUTTI", "Tutti"
    CONSIGLIO_CAPI = "CONCA", "Consiglio Capi"
    CONSIGLIO_CAPI_VICE = "CONCAVI", "Consiglio Capi e Vice"
    ALTA_SQUADRIGLIA = "ALTA_SQ", "Alta Squadriglia"
    # Of a branco or cerchio (DEC-310): its Consiglio degli Anziani.
    CONSIGLIO_ANZIANI = "CDA", "Consiglio degli Anziani"
    # The parents of the unit's members, or of the whole group (DEC-325).
    GENITORI = "GENITORI", "Riunione dei genitori"
    # The members of age and the parents of the minors, for the whole group (DEC-326).
    SOCI = "SOCI", "Assemblea dei soci"


# Convened one at a time with an email and documents; nobody says whether they come (DEC-327).
CERCHIE_CONVOCATE = {Cerchia.GENITORI, Cerchia.SOCI}

# Who of a reparto is invited, and who of a branco or cerchio.
CERCHIE_DI_REPARTO = {
    Cerchia.CONSIGLIO_CAPI,
    Cerchia.CONSIGLIO_CAPI_VICE,
    Cerchia.ALTA_SQUADRIGLIA,
}


class Localita(ModelloTracciato):
    """A place of the group for meetings and events (DEC-310): the seats, a base. The
    capigruppo keep the list; who creates a meeting may add a new one."""

    # How the list calls it: "Sede".
    nome = models.CharField(max_length=120)
    # Its own name, whatever the address (DEC-367): what who is invited reads, when there is one.
    denominazione = models.CharField(max_length=200, blank=True)
    indirizzo = models.CharField(max_length=250, blank=True)
    # Apart from the address: the search service often has only the street (DEC-366).
    civico = models.CharField(max_length=20, blank=True)
    mappa = models.URLField(blank=True)
    attiva = models.BooleanField(default=True)
    creata_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        verbose_name = "località"
        verbose_name_plural = "località"
        ordering = ["nome"]

    def __str__(self) -> str:
        return self.nome

    @property
    def nome_visibile(self) -> str:
        return self.denominazione or self.nome

    @property
    def indirizzo_completo(self) -> str:
        """The number right after the street: "Via Roma 1, 83100 Avellino"."""
        if not self.civico or not self.indirizzo:
            return self.indirizzo
        via, virgola, resto = self.indirizzo.partition(",")
        return f"{via.rstrip()} {self.civico}{virgola}{resto}"


class RiunioneRicorrente(ModelloTracciato):
    """e.g. every Saturday 16–18 from October to June (DEC-78): the app creates one
    event per date, each with its own attendance; a single date can be cancelled."""

    unita = models.ForeignKey(
        "organizzazione.Unita", on_delete=models.PROTECT, related_name="riunioni_ricorrenti"
    )
    giorno_settimana = models.PositiveSmallIntegerField(help_text="0 = lunedì, 6 = domenica.")
    ora_inizio = models.TimeField()
    ora_fine = models.TimeField()
    luogo = models.CharField(max_length=200, blank=True)
    dal = models.DateField()
    al = models.DateField()
    creata_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    # DEC-310: the kind of meeting (the unit's, a patrol's, a council of the unit and the
    # unit linked to it), its place and the uniform.
    titolo = models.CharField(max_length=160, blank=True)
    cerchia = models.CharField(max_length=8, choices=Cerchia.choices, default=Cerchia.TUTTI)
    unita_insieme = models.ManyToManyField(
        "organizzazione.Unita", blank=True, related_name="riunioni_insieme"
    )
    squadriglia = models.ForeignKey(
        "organizzazione.Squadriglia",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="riunioni_ricorrenti",
    )
    localita = models.ForeignKey(
        Localita, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    uniforme = models.BooleanField(default=True)

    class Meta:
        verbose_name = "riunione ricorrente"
        verbose_name_plural = "riunioni ricorrenti"

    def __str__(self) -> str:
        return f"Riunioni di {self.unita}"

    def clean(self) -> None:
        errori = []
        if not 0 <= self.giorno_settimana <= 6:
            errori.append("Scegli il giorno della settimana.")
        if self.ora_fine and self.ora_inizio and self.ora_fine <= self.ora_inizio:
            errori.append("L'ora di fine deve seguire quella di inizio.")
        if self.al and self.dal and self.al < self.dal:
            errori.append("La data di fine deve seguire quella di inizio.")
        elif self.al and self.dal and (self.al - self.dal).days > 366:
            errori.append("Le riunioni ricorrenti coprono al massimo un anno.")
        if errori:
            raise ValidationError(errori)


class Evento(ModelloTracciato):
    titolo = models.CharField(max_length=160)
    tipo = models.CharField(max_length=20, choices=TipoEvento.choices)
    livello = models.CharField(max_length=12, choices=Livello.choices)
    # Who is involved, by level: the branch, the units (one or more), the patrol.
    branca = models.CharField(max_length=4, choices=Branca.choices, blank=True)
    unita = models.ManyToManyField("organizzazione.Unita", blank=True, related_name="eventi")
    squadriglia = models.ForeignKey(
        "organizzazione.Squadriglia",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="eventi",
    )
    inizio = models.DateTimeField()
    fine = models.DateTimeField()
    luogo = models.CharField(max_length=200, blank=True)
    descrizione = models.TextField(blank=True)
    # Notes the parents and the capi read, the ragazzi do not (a patrol's mission).
    note_genitori = models.TextField(blank=True)
    cerchia = models.CharField(max_length=8, choices=Cerchia.choices, default=Cerchia.TUTTI)
    # Camp budget (DEC-91): two of the three are set, the third follows from the number
    # of participants: totale = quota × participants + quota_staff × staff + contributo.
    # The staff (all the staff of the units involved) has its own contribution per head,
    # also zero, counted in the budget only (DEC-156).
    budget_quota = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    budget_contributo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    budget_totale = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    budget_quota_staff = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    riunione = models.ForeignKey(
        RiunioneRicorrente, null=True, blank=True, on_delete=models.CASCADE, related_name="eventi"
    )
    localita = models.ForeignKey(
        Localita, null=True, blank=True, on_delete=models.SET_NULL, related_name="eventi"
    )
    # A meeting (DEC-310): with the uniform or not (None: as its series) and what the
    # staff writes about it, as cleaned HTML.
    uniforme = models.BooleanField(null=True, blank=True)
    informazioni = models.TextField(blank=True)
    # The agenda of a Co.Ca. or parents' meeting, as cleaned HTML (DEC-362): read through its
    # own endpoint, out of the audit log and of the offline copy (DEC-365).
    ordine_del_giorno = models.TextField(blank=True)
    # In the audit log in its place: who changed it and when, never the text.
    ordine_del_giorno_cambiato_il = models.DateTimeField(null=True, blank=True)
    annullato_il = models.DateTimeField(null=True, blank=True)
    motivo_annullamento = models.CharField(max_length=300, blank=True)
    # When the convocation went out, with its attachments (DEC-327).
    convocata_il = models.DateTimeField(null=True, blank=True)
    # At the assembly attendance is marked by the capigruppo or who they choose (DEC-326).
    presenze_da = models.ForeignKey(
        "anagrafica.Persona", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    creato_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        verbose_name = "evento"
        verbose_name_plural = "eventi"
        ordering = ["inizio"]

    def __str__(self) -> str:
        return f"{self.titolo} ({self.inizio:%d/%m/%Y})"

    def con_uniforme(self) -> bool | None:
        """A meeting's uniform: its own choice, or its series' (DEC-310)."""
        if self.tipo != TipoEvento.RIUNIONE:
            return None
        if self.uniforme is not None:
            return self.uniforme
        return self.riunione.uniforme if self.riunione_id else None

    def clean(self) -> None:
        errori = []
        if self.fine and self.inizio and self.fine < self.inizio:
            errori.append("La fine deve seguire l'inizio.")
        if self.livello == Livello.BRANCA and not self.branca:
            errori.append("Scegli la branca.")
        if self.livello == Livello.SQUADRIGLIA and not self.squadriglia_id:
            errori.append("Scegli la squadriglia.")
        if self.tipo == TipoEvento.MISSIONE and self.livello != Livello.SQUADRIGLIA:
            errori.append("La missione è di una squadriglia.")
        if self.tipo == TipoEvento.RIUNIONE and self.livello == Livello.ESTERNO:
            errori.append("Un evento su BuonaCaccia non è una riunione.")
        if self.cerchia == Cerchia.GENITORI:
            if self.livello not in (Livello.UNITA, Livello.GRUPPO):
                errori.append("Una riunione dei genitori è di una o più unità o del gruppo.")
        elif self.cerchia == Cerchia.SOCI:
            if self.livello != Livello.GRUPPO:
                errori.append("L'assemblea dei soci è di tutto il gruppo.")
        elif self.cerchia != Cerchia.TUTTI and self.livello != Livello.UNITA:
            errori.append(
                "Consiglio Capi, Con.Ca.Vi., Alta Squadriglia e Consiglio degli Anziani "
                "sono riunioni di un'unità."
            )
        if errori:
            raise ValidationError(errori)


class StatoPartecipazione(models.TextChoices):
    INVITATO = "INVITATO", "Invitato"
    NON_PARTECIPA = "NON_PARTECIPA", "Non partecipa"  # said by the family
    NON_INVITATO = "NON_INVITATO", "Non invitato"  # decided by the staff, with a reason


class Partecipazione(ModelloTracciato):
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name="partecipazioni")
    persona = models.ForeignKey(
        "anagrafica.Persona", on_delete=models.CASCADE, related_name="partecipazioni"
    )
    stato = models.CharField(
        max_length=14, choices=StatoPartecipazione.choices, default=StatoPartecipazione.INVITATO
    )
    motivo = models.CharField(max_length=300, blank=True)
    cambiato_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        verbose_name = "partecipazione"
        verbose_name_plural = "partecipazioni"
        constraints = [
            models.UniqueConstraint(fields=["evento", "persona"], name="partecipazione_unica")
        ]

    def __str__(self) -> str:
        return f"{self.persona} a {self.evento}: {self.get_stato_display()}"


class StatoPresenza(models.TextChoices):
    PRESENTE = "PRESENTE", "Presente"
    ASSENTE = "ASSENTE", "Assente"
    GIUSTIFICATO = "GIUSTIFICATO", "Assente giustificato"


class Presenza(ModelloTracciato):
    """One record per member and event: marked offline it never conflicts with another
    member's (DEC-96); for the same member the last mark wins."""

    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name="presenze")
    persona = models.ForeignKey(
        "anagrafica.Persona", on_delete=models.CASCADE, related_name="presenze"
    )
    stato = models.CharField(max_length=12, choices=StatoPresenza.choices)
    registrata_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        verbose_name = "presenza"
        verbose_name_plural = "presenze"
        constraints = [models.UniqueConstraint(fields=["evento", "persona"], name="presenza_unica")]

    def __str__(self) -> str:
        return f"{self.persona} a {self.evento}: {self.get_stato_display()}"


class PresenzeAnnue(models.Model):
    """What stays after two years (DEC-78): totals per member and associative year."""

    persona = models.ForeignKey(
        "anagrafica.Persona", on_delete=models.CASCADE, related_name="presenze_annue"
    )
    anno = models.PositiveSmallIntegerField()
    presenti = models.PositiveIntegerField(default=0)
    assenti = models.PositiveIntegerField(default=0)
    giustificati = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "presenze di un anno"
        verbose_name_plural = "presenze per anno"
        constraints = [
            models.UniqueConstraint(fields=["persona", "anno"], name="presenze_annue_uniche")
        ]

    def __str__(self) -> str:
        return f"Presenze di {self.persona} nel {self.anno}"


class DelegaSquadriglia(ModelloTracciato):
    """A member the CSQ delegates to create the patrol's meetings (not to mark their
    attendance). One at a time."""

    squadriglia = models.ForeignKey(
        "organizzazione.Squadriglia", on_delete=models.CASCADE, related_name="deleghe"
    )
    persona = models.ForeignKey(
        "anagrafica.Persona", on_delete=models.CASCADE, related_name="deleghe_squadriglia"
    )
    revocata_il = models.DateTimeField(null=True, blank=True)
    data_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        verbose_name = "delega di squadriglia"
        verbose_name_plural = "deleghe di squadriglia"
        constraints = [
            models.UniqueConstraint(
                fields=["squadriglia"],
                condition=models.Q(revocata_il__isnull=True),
                name="una_delega_alla_volta",
            )
        ]

    def __str__(self) -> str:
        return f"{self.persona} per {self.squadriglia}"


class MembroAltaSquadriglia(ModelloTracciato):
    """Chosen by the reparto staff, year by year."""

    reparto = models.ForeignKey(
        "organizzazione.Unita", on_delete=models.CASCADE, related_name="alta_squadriglia"
    )
    persona = models.ForeignKey(
        "anagrafica.Persona", on_delete=models.CASCADE, related_name="alta_squadriglia"
    )
    anno = models.PositiveSmallIntegerField(help_text="Anno associativo (anno in cui finisce).")

    class Meta:
        verbose_name = "membro dell'Alta Squadriglia"
        verbose_name_plural = "Alta Squadriglia"
        constraints = [
            models.UniqueConstraint(fields=["reparto", "persona", "anno"], name="alta_sq_unica")
        ]

    def __str__(self) -> str:
        return f"{self.persona} in Alta Squadriglia ({self.anno})"


def _token() -> str:
    import secrets

    return secrets.token_urlsafe(32)


class CalendarioPersonale(ModelloTracciato):
    """The secret address of a user's calendar feed (DEC-79): calendar apps cannot log
    in, so the long random token is the key. Regenerating it turns the old one off."""

    utente = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="calendario"
    )
    token = models.CharField(max_length=64, unique=True, default=_token)

    class Meta:
        verbose_name = "calendario personale"
        verbose_name_plural = "calendari personali"

    def __str__(self) -> str:
        return f"Calendario di {self.utente}"

    def rigenera(self) -> None:
        self.token = _token()
        self.save(update_fields=["token", "aggiornato_il"])


# --- Turns of the patrols and of the sestiglie (DEC-312) -------------------------------------


class Sestiglia(ModelloTracciato):
    """A group of children of a branco or cerchio, for the turns only (DEC-312): no
    capo sestiglia, made by the staff."""

    unita = models.ForeignKey(
        "organizzazione.Unita", on_delete=models.PROTECT, related_name="sestiglie"
    )
    nome = models.CharField(max_length=80)
    attiva = models.BooleanField(default=True)

    class Meta:
        verbose_name = "sestiglia"
        verbose_name_plural = "sestiglie"
        ordering = ["nome"]

    def __str__(self) -> str:
        return f"Sestiglia {self.nome}"


class MembroSestiglia(ModelloTracciato):
    """One sestiglia at a time; leaving it closes the period."""

    sestiglia = models.ForeignKey(Sestiglia, on_delete=models.CASCADE, related_name="membri")
    persona = models.ForeignKey(
        "anagrafica.Persona", on_delete=models.CASCADE, related_name="sestiglie"
    )
    data_inizio = models.DateField()
    data_fine = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "membro di una sestiglia"
        verbose_name_plural = "membri delle sestiglie"

    def __str__(self) -> str:
        return f"{self.persona} in {self.sestiglia}"


class Rotazione(models.TextChoices):
    SETTIMANALE = "SETTIMANALE", "Ogni settimana"
    MENSILE = "MENSILE", "Ogni mese"


class TurniUnita(ModelloTracciato):
    """The turns of a reparto (to its patrols) or of a branco/cerchio (to its sestiglie),
    in rotation from `dal`, also with the unit linked to it (DEC-312). Weekly: one step
    at every meeting of the unit held (cancelled ones do not count); monthly: one step at
    the first meeting of each month."""

    unita = models.OneToOneField(
        "organizzazione.Unita", on_delete=models.CASCADE, related_name="turni"
    )
    con_collegata = models.BooleanField(default=False)
    nomi = models.JSONField(default=list)  # the turns, in order
    rotazione = models.CharField(
        max_length=12, choices=Rotazione.choices, default=Rotazione.SETTIMANALE
    )
    dal = models.DateField()

    class Meta:
        verbose_name = "turni di un'unità"
        verbose_name_plural = "turni delle unità"

    def __str__(self) -> str:
        return f"Turni di {self.unita}"


class TurnoCambiato(ModelloTracciato):
    """The staff gave one turn of one meeting to another group (DEC-312); the rotation
    goes on as planned afterwards."""

    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name="turni_cambiati")
    turno = models.CharField(max_length=80)
    squadriglia = models.ForeignKey(
        "organizzazione.Squadriglia", null=True, blank=True, on_delete=models.CASCADE
    )
    sestiglia = models.ForeignKey(Sestiglia, null=True, blank=True, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "turno cambiato"
        verbose_name_plural = "turni cambiati"
        constraints = [
            models.UniqueConstraint(fields=["evento", "turno"], name="turno_cambiato_unico")
        ]

    def __str__(self) -> str:
        return f"{self.turno} ({self.evento})"
