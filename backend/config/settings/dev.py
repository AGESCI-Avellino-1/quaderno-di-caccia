"""Development settings: Django runs on the host, PostgreSQL in Docker (compose.dev.yml)."""

from .base import *

DEBUG = True
# Vite dev server always allowed; anything else from .env is kept (e.g. a phone on the LAN).
ALLOWED_HOSTS = [*dict.fromkeys([*ALLOWED_HOSTS, "localhost", "127.0.0.1"])]
CSRF_TRUSTED_ORIGINS = [
    *dict.fromkeys([*CSRF_TRUSTED_ORIGINS, "http://localhost:5173", "http://127.0.0.1:5173"])
]

# WebAuthn/passkeys over plain http on localhost.
MFA_WEBAUTHN_ALLOW_INSECURE_ORIGIN = True

# allauth headless OpenAPI spec at /_allauth/openapi.html: verify endpoints there,
# never guess them.
HEADLESS_SERVE_SPECIFICATION = True

# The email test mode is always possible in development (DEC-249): Mailpit runs with the
# database (compose.dev.yml).
QDC_MAILPIT_CONSENTITO = True
