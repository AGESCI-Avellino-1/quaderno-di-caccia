from django.apps import AppConfig


class FascicoloConfig(AppConfig):
    """The ragazzo's file of a year and the passage report: no models of its own, it
    gathers what the other apps keep (DEC-38, DEC-41)."""

    name = "apps.fascicolo"
    verbose_name = "Fascicolo personale"
