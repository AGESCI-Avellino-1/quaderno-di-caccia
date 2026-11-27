from django.apps import AppConfig


class CerimonieConfig(AppConfig):
    """The book of the group's ceremonies and traditions (DEC-437), a feature the group may
    switch off (DEC-421)."""

    name = "apps.cerimonie"
    verbose_name = "Cerimonie e tradizioni"

    def ready(self) -> None:
        from auditlog.registry import auditlog

        from . import models

        # The text stays out of the audit log, like the totem ceremony and the PEG (DEC-416):
        # a long text, often reserved; who changed what and when is still recorded. Who was
        # added by hand neither: the names would outlive an erasure (DEC-102).
        auditlog.register(models.VoceLibro, exclude_fields=["testo"])
        auditlog.register(models.PartecipazioneVoce)
