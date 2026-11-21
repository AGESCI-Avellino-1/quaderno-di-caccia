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
