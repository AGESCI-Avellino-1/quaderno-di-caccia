"""Single NinjaAPI instance. Every router enforces permissions through apps.permessi."""

from allauth.headless.contrib.ninja.security import x_session_token_auth
from django.conf import settings
from ninja import NinjaAPI
from ninja.security import django_auth

from apps.accounts.api import router as accounts_router
from apps.anagrafica.api import router as anagrafica_router
from apps.archivio.api import router as archivio_router
from apps.bacheca.api import router as bacheca_router
from apps.banca.api import router as banca_router
from apps.buonacaccia.api import router as buonacaccia_router
from apps.cassa.api import router as cassa_router
from apps.core.api import router as core_router
from apps.diritti.api import router as diritti_router
from apps.dispositivi.api import router as dispositivi_router
from apps.eventi.api import router as eventi_router
from apps.fascicolo.api import router as fascicolo_router
from apps.impersonazione.api import router as impersonazione_router
from apps.importazione.api import router as importazione_router
from apps.iscrizioni.api import router as iscrizioni_router
from apps.note.api import router as note_router
from apps.organizzazione.api import router as organizzazione_router
from apps.progressione.api import router as progressione_router
from apps.quote.api import router as quote_router
from apps.sanitaria.api import router as sanitaria_router

# Browser client: session cookie + CSRF. Store app (Capacitor): X-Session-Token.
api = NinjaAPI(
    title="Quaderno di Caccia API",
    version="1",
    urls_namespace="api",
    auth=[django_auth, x_session_token_auth],
    # Interactive docs and schema only in development: no public map of the API.
    docs_url="/docs" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
)

api.add_router("/", core_router)
api.add_router("/", accounts_router)
api.add_router("/", organizzazione_router)
api.add_router("/", anagrafica_router)
api.add_router("/", importazione_router)
api.add_router("/", dispositivi_router)
api.add_router("/", sanitaria_router)
api.add_router("/", diritti_router)
api.add_router("/", iscrizioni_router)
api.add_router("/", quote_router)
api.add_router("/", cassa_router)
api.add_router("/", eventi_router)
api.add_router("/", buonacaccia_router)
api.add_router("/", impersonazione_router)
api.add_router("/", progressione_router)
api.add_router("/", note_router)
api.add_router("/", fascicolo_router)
api.add_router("/", archivio_router)
api.add_router("/", bacheca_router)
api.add_router("/", banca_router)
