"""Base settings shared by every environment.

Decision references (DEC-nn) point to the requirements document
"Quaderno di Caccia (QdC) — Analisi dei requisiti".
"""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR.parent / ".env", overwrite=False)

SECRET_KEY = env("DJANGO_SECRET_KEY", default="insecure-dev-key-change-me")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

# Public URL of the PWA (same origin as the API in dev and prod, see README).
FRONTEND_URL = env("QDC_FRONTEND_URL", default="http://localhost:5173")

INSTALLED_APPS = [
    # The admin also for the technical administrators appointed in the app (DEC-166).
    "apps.accounts.config_amministrazione.AmministrazioneConfig",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Authentication (DEC-21, DEC-22): email, login by code, passkeys, Google, Apple.
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.apple",
    "allauth.mfa",
    "allauth.headless",
    # Security and audit trail.
    "axes",
    "auditlog",
    # QdC apps.
    "apps.core",
    "apps.accounts",
    "apps.organizzazione",
    "apps.anagrafica",
    "apps.importazione",
    "apps.permessi",
    "apps.dispositivi",
    "apps.sanitaria",
    "apps.diritti",
    "apps.iscrizioni",
    "apps.quote",
    "apps.cassa",
    "apps.eventi",
    "apps.buonacaccia",
    "apps.impersonazione",
    "apps.progressione",
    "apps.note",
    "apps.fascicolo",
    "apps.archivio",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "auditlog.middleware.AuditlogMiddleware",
    # Revoked devices are logged out; the offline window is renewed (DEC-97).
    "apps.dispositivi.middleware.DispositivoMiddleware",
    # Acting as another user: after auditlog (the real user stays the author of every
    # change) and after the device check (it applies to the real user's device).
    "apps.impersonazione.middleware.ImpersonazioneMiddleware",
    # Replayed offline writes are answered from storage, never executed twice (DEC-96).
    "apps.core.idempotenza.IdempotenzaMiddleware",
    # Must stay last (django-axes requirement).
    "axes.middleware.AxesMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {
    "default": env.db("DATABASE_URL", default="postgres://qdc:qdc@localhost:5432/qdc"),
}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DJANGO_CONN_MAX_AGE", default=60)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    # django-axes must be first.
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
    # Every model permission in the admin to the technical administrators (DEC-166).
    "apps.accounts.amministrazione.PermessiAmministratore",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "it"
TIME_ZONE = "Europe/Rome"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# Uploaded files (BuonaStrada exports, later receipts and profile photos) live outside
# the web root and are served only through permission-checked views.
MEDIA_ROOT = env("QDC_MEDIA_ROOT", default=str(BASE_DIR / "media"))
MEDIA_URL = "/media-non-pubblico/"

# --- Sessions (DEC-23: 30-day session on the device) -------------------------------
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# --- django-allauth (DEC-21, DEC-22, DEC-24) ---------------------------------------
ACCOUNT_ADAPTER = "apps.accounts.adapters.AccountAdapter"
SOCIALACCOUNT_ADAPTER = "apps.accounts.adapters.SocialAccountAdapter"
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
# allauth's emails name the site by its host ("localhost:5173"): name the app instead.
ACCOUNT_EMAIL_SUBJECT_PREFIX = "Quaderno di Caccia: "
ACCOUNT_LOGIN_BY_CODE_ENABLED = True
ACCOUNT_LOGOUT_ON_PASSWORD_CHANGE = False

HEADLESS_ONLY = True
HEADLESS_CLIENTS = ("browser", "app")
HEADLESS_FRONTEND_URLS = {
    "account_confirm_email": f"{FRONTEND_URL}/account/verifica-email/{{key}}",
    "account_reset_password": f"{FRONTEND_URL}/account/reimposta-password",
    "account_reset_password_from_key": f"{FRONTEND_URL}/account/reimposta-password/{{key}}",
    "account_signup": f"{FRONTEND_URL}/account/registrazione",
    "socialaccount_login_error": f"{FRONTEND_URL}/account/errore-social",
}

MFA_SUPPORTED_TYPES = ["totp", "recovery_codes", "webauthn"]
MFA_PASSKEY_LOGIN_ENABLED = True
# Sign-up only happens through an invitation (DEC-21): passkeys are added after.
MFA_PASSKEY_SIGNUP_ENABLED = False

SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APPS": [
            {
                "client_id": env("QDC_GOOGLE_CLIENT_ID", default=""),
                "secret": env("QDC_GOOGLE_SECRET", default=""),
            }
        ],
        "SCOPE": ["email", "profile"],
    },
    "apple": {
        "APPS": [
            {
                "client_id": env("QDC_APPLE_CLIENT_ID", default=""),
                "secret": env("QDC_APPLE_KEY_ID", default=""),
                "key": env("QDC_APPLE_TEAM_ID", default=""),
                "settings": {"certificate_key": env("QDC_APPLE_PRIVATE_KEY", default="")},
            }
        ],
    },
}

# --- django-axes ---------------------------------------------------------------
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1  # hours
AXES_LOCKOUT_PARAMETERS = ["ip_address", ["username", "user_agent"]]
AXES_USERNAME_FORM_FIELD = "email"

# --- Email (Django 6.1 MAILERS; EMAIL_BACKEND is deprecated) ---------------------
MAILERS = {"default": {"BACKEND": "django.core.mail.backends.console.EmailBackend"}}
DEFAULT_FROM_EMAIL = env(
    "DJANGO_DEFAULT_FROM_EMAIL", default="Quaderno di Caccia <noreply@localhost>"
)

# --- QdC -------------------------------------------------------------------------
# Invitation links expire after this many days (DEC-21).
QDC_INVITO_VALIDITA_GIORNI = env.int("QDC_INVITO_VALIDITA_GIORNI", default=14)
# A device that does not reach the server for this many days deletes its offline data
# by itself (DEC-97). Camps last up to 12 days (DEC-94).
QDC_OFFLINE_GIORNI = env.int("QDC_OFFLINE_GIORNI", default=14)
# The group's shared Drive for the archives (DEC-196, DEC-212): the path of the service
# account's JSON key and the id of the folder. Empty: archiving is not available.
QDC_DRIVE_CREDENZIALI = env("QDC_DRIVE_CREDENZIALI", default="")
QDC_DRIVE_CARTELLA = env("QDC_DRIVE_CARTELLA", default="")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": env("DJANGO_LOG_LEVEL", default="INFO")},
}
