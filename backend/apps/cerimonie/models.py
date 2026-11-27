"""The book of ceremonies and traditions (DEC-437).

An entry belongs to the group or to a unit. Every capo of the Co.Ca. reads every entry; a
ragazzo/a, while an active member, reads the entries they were added to by hand (block 1: the
conditions come later); the parents never. Who sees what is decided in `policy.voci_visibili`.
"""

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
