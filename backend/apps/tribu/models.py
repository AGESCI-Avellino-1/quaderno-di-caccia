from django.db import models

from apps.anagrafica.models import Persona
from apps.core.models import ModelloTracciato


class Totem(ModelloTracciato):
    """A member's totem name (DEC-416): free text, an animal or a plant with an adjective,
    from the reparto up, capi included. Doubles are allowed.

    The image is a JPEG under a random name, served only by the API. One uploaded by a
    ragazzo waits in `immagine_in_attesa` until a capo approves it; meanwhile the others
    keep seeing `immagine`."""

    persona = models.OneToOneField(Persona, on_delete=models.CASCADE, related_name="totem")
    nome = models.CharField(max_length=80)
    immagine = models.ImageField(upload_to="totem/", blank=True)
    immagine_in_attesa = models.ImageField(upload_to="totem/", blank=True)
    # Why a capo refused or took away the image, for the owner until the next upload.
    avviso_immagine = models.CharField(max_length=300, blank=True)

    class Meta:
        verbose_name = "nome di totem"
        verbose_name_plural = "nomi di totem"
        ordering = ["nome"]

    def __str__(self) -> str:
        return self.nome


class ModificaTotem(ModelloTracciato):
    """The «Modifica totem» switch (DEC-418): while it exists, the person may write their own
    totem name once. A capo with a totem turns it on, never for themself (the capigruppo
    while no capo has one); any change of the totem name turns it off."""

    persona = models.OneToOneField(Persona, on_delete=models.CASCADE, related_name="modifica_totem")

    class Meta:
        verbose_name = "modifica del nome di totem"
        verbose_name_plural = "modifiche del nome di totem"

    def __str__(self) -> str:
        return f"Modifica del totem di {self.persona}"
