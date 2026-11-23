from django.apps import AppConfig


class TribuConfig(AppConfig):
    """Totem names and the tribe (DEC-416)."""

    name = "apps.tribu"
    verbose_name = "Nomi di totem"

    def ready(self) -> None:
        from auditlog.registry import auditlog

        from . import models

        # The images and why a capo took one away stay in the history (DEC-416).
        auditlog.register(models.Totem)
        auditlog.register(models.ModificaTotem)
