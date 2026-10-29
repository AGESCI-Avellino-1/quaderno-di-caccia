from django.apps import AppConfig


class EventiConfig(AppConfig):
    name = "apps.eventi"
    verbose_name = "Eventi e presenze"

    def ready(self) -> None:
        from auditlog.registry import auditlog

        from . import models

        auditlog.register(models.Evento)
        auditlog.register(models.RiunioneRicorrente)
        auditlog.register(models.Partecipazione)
        auditlog.register(models.Presenza)
        auditlog.register(models.DelegaSquadriglia)
        auditlog.register(models.MembroAltaSquadriglia)
