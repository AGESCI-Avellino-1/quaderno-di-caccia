"""Production settings: everything in Docker, behind the reverse proxy chosen with
scripts/configure-prod.sh. All secrets come from the environment."""

from .base import *

DEBUG = False
SECRET_KEY = env("DJANGO_SECRET_KEY")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = env.int("DJANGO_HSTS_SECONDS", default=60 * 60 * 24 * 30)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# No HSTS preload: being on the browsers' preload list is practically irreversible, a
# choice for whoever owns the domain, not for this app.
SILENCED_SYSTEM_CHECKS = ["security.W021"]
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"

MAILERS["reale"] = {
    "BACKEND": "django.core.mail.backends.smtp.EmailBackend",
    "OPTIONS": {
        "host": env("DJANGO_EMAIL_HOST", default="localhost"),
        "port": env.int("DJANGO_EMAIL_PORT", default=587),
        "username": env("DJANGO_EMAIL_HOST_USER", default=""),
        "password": env("DJANGO_EMAIL_HOST_PASSWORD", default=""),
        "use_tls": env.bool("DJANGO_EMAIL_USE_TLS", default=True),
    },
}

# Behind a reverse proxy the client IP comes from X-Forwarded-For.
AXES_IPWARE_PROXY_COUNT = env.int("QDC_PROXY_COUNT", default=1)
AXES_IPWARE_META_PRECEDENCE_ORDER = ["HTTP_X_FORWARDED_FOR", "REMOTE_ADDR"]
