from django.apps import AppConfig


class AnagraficaConfig(AppConfig):
    name = "apps.anagrafica"
    verbose_name = "Anagrafica"

    def ready(self) -> None:
        from auditlog.registry import auditlog

        from . import models

        for modello in (
            models.Persona,
            models.RelazioneTutela,
            models.Appartenenza,
            models.AppartenenzaSquadriglia,
            models.CorrezioneAnagrafica,
        ):
            auditlog.register(modello)
