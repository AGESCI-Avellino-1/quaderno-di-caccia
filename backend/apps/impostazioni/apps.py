from django.apps import AppConfig


class ImpostazioniConfig(AppConfig):
    name = "apps.impostazioni"
    verbose_name = "Impostazioni"

    def ready(self) -> None:
        from auditlog.registry import auditlog

        from . import models

        # The SMTP password stays out of the audit log, even encrypted (DEC-277).
        auditlog.register(
            models.Impostazioni,
            exclude_fields=["smtp_password", "gmail_client_secret", "gmail_refresh_token"],
        )
        auditlog.register(models.ModelloEmail)
