"""Test settings: SQLite in memory unless DATABASE_URL is set (CI runs on PostgreSQL)."""

from .base import *

DEBUG = False
SECRET_KEY = "test-only-secret-key"  # noqa: S105
QDC_IMPRONTA_CHIAVE = "test-only-impronta"
QDC_CHIAVE_SEGRETI = "test-only-segreti"
DATABASES = {"default": env.db("DATABASE_URL", default="sqlite://:memory:")}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
MAILERS = {"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}}
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
MIDDLEWARE = [m for m in MIDDLEWARE if m != "whitenoise.middleware.WhiteNoiseMiddleware"]
AXES_ENABLED = False
QDC_EMAIL_IN_CODA = False  # the queue's tests switch it on
LOGGING = {"version": 1, "disable_existing_loggers": False}
