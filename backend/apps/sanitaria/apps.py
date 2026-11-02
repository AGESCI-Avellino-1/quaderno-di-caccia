from django.apps import AppConfig


class SanitariaConfig(AppConfig):
    name = "apps.sanitaria"
    verbose_name = "Dati sanitari"

    def ready(self) -> None:
        from auditlog.registry import auditlog

        from . import models

        for modello in (
            models.InformazioniSanitarie,
            models.Allergia,
            models.Farmaco,
            models.ReperibilitaEvento,
        ):
            auditlog.register(modello)
        # The original file name may carry the person's name: out of the audit log.
        auditlog.register(models.AllegatoSanitario, exclude_fields=["nome_file", "file"])
