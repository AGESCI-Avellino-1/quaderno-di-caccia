from django.apps import AppConfig


class BabboNataleConfig(AppConfig):
    """Babbo Natale segreto: anonymous gift exchanges (DEC-422), a feature the group may switch
    off (DEC-421)."""

    name = "apps.babbonatale"
    verbose_name = "Babbo Natale segreto"

    def ready(self) -> None:
        from auditlog.registry import auditlog

        from . import models

        # The exchange only: who gives a gift to whom never goes in the audit log (DEC-422).
        auditlog.register(models.ScambioRegali)
