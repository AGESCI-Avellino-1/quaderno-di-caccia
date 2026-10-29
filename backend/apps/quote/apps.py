from django.apps import AppConfig


class QuoteConfig(AppConfig):
    name = "apps.quote"
    verbose_name = "Quote e pagamenti"

    def ready(self) -> None:
        from auditlog.registry import auditlog

        from . import models

        auditlog.register(models.TipoQuota)
        auditlog.register(models.Quota)
        auditlog.register(models.Agevolazione)
        auditlog.register(models.LegameConiugale)
        auditlog.register(models.Pagamento)
        auditlog.register(models.RipartizionePagamento)
