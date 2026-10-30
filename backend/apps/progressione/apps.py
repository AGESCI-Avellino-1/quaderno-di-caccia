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
            models.Obiettivo,
            models.Impegno,
            models.PercorsoCompetenza,
            models.Impresa,
            models.PostoAzione,
            models.Passaggio,
            models.PassaggioPersona,
            models.FirmaCarta,
            models.CartaClan,
            models.Conclusione,
            models.Stagione,
            models.AllegatoPP,
        ):
            auditlog.register(modello)
        # What was faced in confidence stays out of the audit log, which the technical
        # administrator reads (DEC-180).
        auditlog.register(models.PuntoStrada, exclude_fields=["riservato", "voce"])
