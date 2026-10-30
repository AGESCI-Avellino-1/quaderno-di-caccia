from django.apps import AppConfig


class BancaConfig(AppConfig):
    name = "apps.banca"
    verbose_name = "Estratto conto della banca"

    def ready(self) -> None:
        from auditlog.registry import auditlog

        from . import models

        auditlog.register(models.CartaUnita)
        auditlog.register(models.EstrattoConto)
        auditlog.register(models.RigaBanca, exclude_fields=["dettaglio"])
