from django.apps import AppConfig


class AttesaConfig(AppConfig):
    """The waiting list (DEC-256…DEC-263). Its models are NOT in the audit log: who
    leaves the list must leave no data behind, not even in the history (DEC-263)."""

    name = "apps.attesa"
    verbose_name = "Lista d'attesa"
