from django.apps import AppConfig


class FascicoloConfig(AppConfig):
    """The ragazzo's file of a year and the passage report, which gather what the other
    apps keep (DEC-38, DEC-41); the capi's file (DEC-47)."""

    name = "apps.fascicolo"
    verbose_name = "Fascicolo personale"

    def ready(self) -> None:
        from auditlog.registry import auditlog

        from . import models

        auditlog.register(models.ServizioPassato)
        auditlog.register(models.Formazione)
