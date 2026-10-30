from django.apps import AppConfig


class ProgressioneConfig(AppConfig):
    name = "apps.progressione"
    verbose_name = "Progressione Personale"

    def ready(self) -> None:
        from auditlog.registry import auditlog

        from . import models

        for modello in (
            models.PeriodoBranca,
            models.Tappa,
            models.Promessa,
            models.ConsegnaDistintivo,
            models.MetaEG,
            models.Impegno,
            models.PercorsoCompetenza,
            models.Impresa,
            models.PostoAzione,
            models.Passaggio,
            models.PassaggioPersona,
        ):
            auditlog.register(modello)
