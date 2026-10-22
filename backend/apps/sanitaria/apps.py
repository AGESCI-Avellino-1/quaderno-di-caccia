from django.apps import AppConfig


class SanitariaConfig(AppConfig):
    name = "apps.sanitaria"
    verbose_name = "Dati sanitari"

    def ready(self) -> None:
        from auditlog.registry import auditlog

        from . import models

        for modello in (models.InformazioniSanitarie, models.Allergia, models.Farmaco):
            auditlog.register(modello)
