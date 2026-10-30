"""The admin app with the QdC site (apps.accounts.amministrazione). Kept apart: it is
imported while the apps load, before models and forms can be."""

from django.contrib.admin.apps import AdminConfig


class AmministrazioneConfig(AdminConfig):
    default_site = "apps.accounts.amministrazione.AmministrazioneQdc"
