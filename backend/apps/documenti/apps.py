from django.apps import AppConfig


class DocumentiConfig(AppConfig):
    name = "apps.documenti"
    verbose_name = "Documenti e Progetto Educativo di Gruppo"

    def ready(self) -> None:
        from auditlog.registry import auditlog

        from . import models

        auditlog.register(models.Documento)
        auditlog.register(models.VersionePeg, exclude_fields=["testo"])
