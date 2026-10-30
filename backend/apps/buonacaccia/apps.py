from django.apps import AppConfig


class BuonaCacciaConfig(AppConfig):
    name = "apps.buonacaccia"
    verbose_name = "Eventi su BuonaCaccia"

    def ready(self) -> None:
        from auditlog.registry import auditlog

        from . import models

        auditlog.register(models.EventoBuonaCaccia)
        auditlog.register(models.ModelloScheda)
        auditlog.register(models.VersioneScheda)
        # The management link deletes a registration on BuonaCaccia (DEC-159): it stays
        # out of the audit log, which the technical administrator reads.
        auditlog.register(
            models.IscrizioneBuonaCaccia, exclude_fields=["link_gestione", "promemoria"]
        )
        auditlog.register(models.QuotaFormazione)
