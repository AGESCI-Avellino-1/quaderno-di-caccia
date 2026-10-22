from django.apps import AppConfig


class OrganizzazioneConfig(AppConfig):
    name = "apps.organizzazione"
    verbose_name = "Organizzazione del gruppo"

    def ready(self) -> None:
        from auditlog.registry import auditlog

        from . import models

        for modello in (models.Gruppo, models.Unita, models.Squadriglia, models.Incarico):
            auditlog.register(modello)
