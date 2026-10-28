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
        # Special-category data: the reason stays out of the audit log (which the admin
        # shows); who changed it and when is in the access log (DEC-101).
        auditlog.register(models.DerogaSquadriglia, exclude_fields=["motivazione"])
