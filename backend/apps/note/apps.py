from django.apps import AppConfig


class NoteConfig(AppConfig):
    name = "apps.note"
    verbose_name = "Note e regole sul rapporto con il minore"

    def ready(self) -> None:
        from auditlog.registry import auditlog

        from . import models

        auditlog.register(models.Nota)
        auditlog.register(models.RegoleRapporto)
