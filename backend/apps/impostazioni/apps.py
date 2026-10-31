from django.apps import AppConfig


class ImpostazioniConfig(AppConfig):
    name = "apps.impostazioni"
    verbose_name = "Impostazioni"

    def ready(self) -> None:
        from auditlog.registry import auditlog

        from . import models

        auditlog.register(models.Impostazioni)
