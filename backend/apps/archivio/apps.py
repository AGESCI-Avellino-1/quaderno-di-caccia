from django.apps import AppConfig


class ArchivioConfig(AppConfig):
    name = "apps.archivio"
    verbose_name = "Fine anno e archivio"

    def ready(self) -> None:
        from auditlog.registry import auditlog

        from . import models

        auditlog.register(models.Archiviazione)
