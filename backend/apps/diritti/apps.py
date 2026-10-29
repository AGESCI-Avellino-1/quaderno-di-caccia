from django.apps import AppConfig


class DirittiConfig(AppConfig):
    name = "apps.diritti"
    verbose_name = "Diritti degli interessati"

    def ready(self) -> None:
        from auditlog.registry import auditlog

        from . import models

        auditlog.register(models.RichiestaDiritti)
