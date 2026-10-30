from django.apps import AppConfig


class BachecaConfig(AppConfig):
    name = "apps.bacheca"
    verbose_name = "Bacheca degli avvisi"

    def ready(self) -> None:
        from auditlog.registry import auditlog

        from . import models

        auditlog.register(models.Avviso)
        auditlog.register(models.AllegatoAvviso)
