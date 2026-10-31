from django.apps import AppConfig


class IscrizioniConfig(AppConfig):
    name = "apps.iscrizioni"
    verbose_name = "Iscrizioni dall'app"

    def ready(self) -> None:
        from auditlog.registry import auditlog

        from . import models

        # The waiting list's data it may carry leave no trace in the history (DEC-263).
        auditlog.register(models.CodiceIscrizione, exclude_fields=["dati_proposti"])
        auditlog.register(models.RichiestaIscrizione)
        auditlog.register(models.ModuloVuoto)
        auditlog.register(models.AllegatoIscrizione)
