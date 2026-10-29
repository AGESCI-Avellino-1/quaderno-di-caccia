from django.apps import AppConfig


class CassaConfig(AppConfig):
    name = "apps.cassa"
    verbose_name = "Prima nota"

    def ready(self) -> None:
        from auditlog.registry import auditlog

        from . import models

        auditlog.register(models.Cassa)
        auditlog.register(models.Movimento)
        auditlog.register(models.VerificaCassa)
        auditlog.register(models.SpesaAnticipata)
