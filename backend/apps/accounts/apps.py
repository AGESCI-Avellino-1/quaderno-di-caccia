from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = "apps.accounts"
    verbose_name = "Account"

    def ready(self) -> None:
        from auditlog.registry import auditlog

        from . import models

        auditlog.register(models.User, exclude_fields=["password", "last_login"])
        auditlog.register(models.Invito, exclude_fields=["token"])
