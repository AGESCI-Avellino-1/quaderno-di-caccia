from django.contrib import admin
from django.urls import include, path

from apps.impostazioni.views import mailpit
from config.api import api

urlpatterns = [
    path("admin/", admin.site.urls),
    # Provider callbacks (Google, Apple) still need the classic allauth URLs.
    path("accounts/", include("allauth.urls")),
    # Headless authentication API used by the PWA: /_allauth/{browser|app}/v1/...
    path("_allauth/", include("allauth.headless.urls")),
    path("api/v1/", api.urls),
    # Email test mode (DEC-249): technical administrator only, the view decides.
    path("mailpit/", mailpit),
    path("mailpit/<path:percorso>", mailpit),
]
