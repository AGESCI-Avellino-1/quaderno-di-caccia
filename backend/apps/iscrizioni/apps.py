from django.apps import AppConfig


class IscrizioniConfig(AppConfig):
    name = "apps.iscrizioni"
    verbose_name = "Iscrizioni dall'app"

    def ready(self) -> None:
        from auditlog.registry import auditlog

        from . import models

        auditlog.register(models.CodiceIscrizione)
        auditlog.register(models.RichiestaIscrizione)
