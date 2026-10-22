from django.apps import AppConfig


class DispositiviConfig(AppConfig):
    name = "apps.dispositivi"
    verbose_name = "Dispositivi"

    def ready(self) -> None:
        from auditlog.registry import auditlog

        from . import models

        auditlog.register(models.Dispositivo, exclude_fields=["chiave_sessione", "ultimo_contatto"])
