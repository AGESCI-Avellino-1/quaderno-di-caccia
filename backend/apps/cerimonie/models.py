"""The book of ceremonies and traditions (DEC-437).

An entry belongs to the group or to a unit, with the register of who lived it. Every capo of the Co.Ca. reads every entry; a
ragazzo/a, while an active member, reads the entries whose conditions they meet or they were
added to by hand; the parents never. Who sees what is decided in `policy.voci_visibili`.
"""

from django.conf import settings
from django.db import models

from apps.anagrafica.models import Persona
from apps.core.models import ModelloTracciato


class TipoVoce(models.TextChoices):
    CERIMONIA = "CERIMONIA", "Cerimonia"
    TRADIZIONE = "TRADIZIONE", "Tradizione"


# Written with the editor: room for a long text, not for a book (as the totem ceremony).
LUNGHEZZA_TESTO = 100_000


class VoceLibro(ModelloTracciato):
    titolo = models.CharField(max_length=200)
    tipo = models.CharField(max_length=12, choices=TipoVoce.choices, default=TipoVoce.CERIMONIA)
    # The editor's cleaned HTML, no images (attachments come apart).
    testo = models.TextField(blank=True)
    # The unit whose staff writes it; none = the group's, written by the capigruppo.
    unita = models.ForeignKey(
        "organizzazione.Unita",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="voci_libro",
    )
    # The totem ceremony, once in the settings (DEC-416): «La mia tribù» links to it.
    cerimonia_del_totem = models.BooleanField(default=False)
    # Ragazzi/e who read it whatever the conditions say.
    aggiunti = models.ManyToManyField(Persona, blank=True, related_name="voci_libro")
    # Groups of conditions (`condizioni.py`): all of a group, one group is enough.
    condizioni = models.JSONField(default=list, blank=True)

    class Meta:
        verbose_name = "voce del libro delle cerimonie"
        verbose_name_plural = "voci del libro delle cerimonie"
        ordering = ["tipo", "titolo", "pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["cerimonia_del_totem"],
                condition=models.Q(cerimonia_del_totem=True),
                name="una_sola_cerimonia_del_totem",
            )
        ]

    def __str__(self) -> str:
        return self.titolo


class PartecipazioneVoce(ModelloTracciato):
    """Who lived an entry, and when: the register (DEC-437, block 3). Active ragazzi/e and capi
    are marked, also for past years; who later leaves stays. Read by every capo and by the
    other participants of the same entry."""

    voce = models.ForeignKey(VoceLibro, on_delete=models.CASCADE, related_name="partecipazioni")
    persona = models.ForeignKey(
        Persona, on_delete=models.CASCADE, related_name="partecipazioni_voci"
    )
    data = models.DateField()
    registrata_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        verbose_name = "partecipazione a una voce del libro"
        verbose_name_plural = "partecipazioni alle voci del libro"
        ordering = ["-data", "persona__cognome", "persona__nome"]
        constraints = [
            models.UniqueConstraint(fields=["voce", "persona"], name="una_partecipazione_per_voce")
        ]

    def __str__(self) -> str:
        return f"{self.persona} in {self.voce}"
