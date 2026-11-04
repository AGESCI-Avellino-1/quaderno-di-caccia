from django.apps import AppConfig


class NotificheConfig(AppConfig):
    name = "apps.notifiche"
    verbose_name = "Notifiche sul telefono"

    def ready(self) -> None:
        from auditlog.registry import auditlog

        from . import models

        # The addresses and keys of a browser are secrets of its own: not in the audit log.
        auditlog.register(models.PreferenzePush)
