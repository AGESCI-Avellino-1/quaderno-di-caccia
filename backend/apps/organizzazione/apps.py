from django.apps import AppConfig


class OrganizzazioneConfig(AppConfig):
    name = "apps.organizzazione"
    verbose_name = "Organizzazione del gruppo"

    def ready(self) -> None:
        from auditlog.registry import auditlog

        from . import models

        for modello in (
            models.Gruppo,
            models.Unita,
            models.Squadriglia,
            models.AnimaleSquadriglia,
            models.Incarico,
            models.TipoIncarico,
            models.AnnoChiuso,
            models.BozzaSquadriglie,
            models.SquadrigliaInBozza,
            models.MembroInBozza,
        ):
            auditlog.register(modello)
