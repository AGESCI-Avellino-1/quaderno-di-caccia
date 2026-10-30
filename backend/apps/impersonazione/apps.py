from django.apps import AppConfig


class ImpersonazioneConfig(AppConfig):
    name = "apps.impersonazione"
    verbose_name = "Uso dell'app al posto di un altro"

    def ready(self) -> None:
        from auditlog.registry import auditlog

        from . import models

        auditlog.register(models.Impersonazione)
