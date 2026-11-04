from django.apps import AppConfig


class VerbaliConfig(AppConfig):
    name = "apps.verbali"
    verbose_name = "Verbali delle riunioni"

    def ready(self) -> None:
        from auditlog.registry import auditlog

        from . import models

        # The text stays out of the audit log, which the technical administrator reads
        # (DEC-329); so does the upload session, a secret address on Google's side.
        auditlog.register(models.Verbale, exclude_fields=["testo"])
        auditlog.register(models.AllegatoVerbale, exclude_fields=["sessione"])
