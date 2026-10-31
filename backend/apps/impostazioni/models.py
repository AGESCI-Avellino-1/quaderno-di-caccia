from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import ModelloTracciato

from . import segnaposto

TITOLO_COMPLETO = "[Nome sito] - [Gruppo]"
TITOLO_BREVE = "[Sigla sito] - [Sigla gruppo]"


class Impostazioni(ModelloTracciato):
    """The installation's settings, one row (DEC-245…DEC-248).

    The names here are for the title only: the group's official data for the prints
    stay on `organizzazione.Gruppo` (DEC-245).
    """

    nome_sito = models.CharField(max_length=80, default="Quaderno di Caccia")
    sigla_sito = models.CharField(max_length=20, default="QdC", blank=True)
    # Empty: "AGESCI" and the BuonaStrada name (`nome_del_gruppo`).
    nome_gruppo = models.CharField(max_length=120, blank=True)
    sigla_gruppo = models.CharField(max_length=20, blank=True)
    titolo_completo = models.CharField(max_length=200, default=TITOLO_COMPLETO)
    titolo_breve = models.CharField(max_length=120, default=TITOLO_BREVE)
    # Shown above the fixed line of the footer (DEC-247).
    riga_piede = models.CharField(max_length=300, blank=True)
    # Email test mode (DEC-249): emails go to Mailpit, nobody receives them. Effective only
    # where settings.QDC_MAILPIT_CONSENTITO: see `email_di_prova_attiva`.
    email_di_prova = models.BooleanField(default=False)

    class Meta:
        verbose_name = "impostazioni"
        verbose_name_plural = "impostazioni"

    def __str__(self) -> str:
        return "Impostazioni"

    def clean(self) -> None:
        errori = {}
        for campo in ("titolo_completo", "titolo_breve", "riga_piede"):
            ignoti = segnaposto.sconosciuti(getattr(self, campo), segnaposto.DEL_TITOLO)
            if ignoti:
                elenco = ", ".join(f"[{n}]" for n in ignoti)
                errori[campo] = f"Segnaposto sconosciuto: {elenco}."
        if errori:
            raise ValidationError(errori)

    @classmethod
    def carica(cls) -> Impostazioni:
        return cls.objects.get_or_create(pk=1)[0]

    def email_di_prova_attiva(self) -> bool:
        from django.conf import settings

        return self.email_di_prova and settings.QDC_MAILPIT_CONSENTITO

    def nome_del_gruppo(self) -> str:
        if self.nome_gruppo:
            return self.nome_gruppo
        from apps.organizzazione.models import Gruppo

        gruppo = Gruppo.objects.first()
        return f"AGESCI {gruppo.denominazione}" if gruppo else "AGESCI"
