"""Test settings: SQLite in memory unless DATABASE_URL is set (CI runs on PostgreSQL)."""

from .base import *

DEBUG = False
SECRET_KEY = "test-only-secret-key"  # noqa: S105
DATABASES = {"default": env.db("DATABASE_URL", default="sqlite://:memory:")}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
MAILERS = {"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}}
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
MIDDLEWARE = [m for m in MIDDLEWARE if m != "whitenoise.middleware.WhiteNoiseMiddleware"]
AXES_ENABLED = False
LOGGING = {"version": 1, "disable_existing_loggers": False}
