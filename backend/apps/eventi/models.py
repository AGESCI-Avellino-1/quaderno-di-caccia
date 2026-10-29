"""Events, recurring meetings, participants and attendance (DEC-75, DEC-78).

Decided with the maintainer on 2026-10-29 (not yet in the analysis):
- participants are by default all the members of the units involved (the whole group
  for a group event);
- the family (or the adult member) says the member will not take part; the staff (the
  Co.Ca. for group events) may not invite a member, with a reason the family sees;
- attendance is present, absent or excused, marked by capi only, also offline, at
  recurring meetings and at every other event (for a camp, once for the event);
- BuonaCaccia events come after this phase;
- patrol meetings are patrol events: the CSQ, a member they delegate (to create them
  only) or the reparto staff create them, and the CSQ marks their attendance; the staff
  also creates the patrol's mission (with notes for the parents the ragazzi do not
  see) and other activities of one patrol;
- the staff creates events for the Consiglio Capi (CSQ), the Con.Ca.Vi. (CSQ and
  VCSQ) and the Alta Squadriglia (chosen by the staff each year), of one or more
  reparti of the group.
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
    riunione = models.ForeignKey(
        RiunioneRicorrente, null=True, blank=True, on_delete=models.CASCADE, related_name="eventi"
    )
    annullato_il = models.DateTimeField(null=True, blank=True)
    motivo_annullamento = models.CharField(max_length=300, blank=True)
    creato_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        verbose_name = "evento"
        verbose_name_plural = "eventi"
        ordering = ["inizio"]

    def __str__(self) -> str:
        return f"{self.titolo} ({self.inizio:%d/%m/%Y})"

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
        if self.cerchia != Cerchia.TUTTI and self.livello != Livello.UNITA:
            errori.append("Consiglio Capi, Con.Ca.Vi. e Alta Squadriglia sono eventi di reparto.")
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
