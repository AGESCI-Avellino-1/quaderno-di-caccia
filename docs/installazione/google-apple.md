# Accesso con Google e Apple

Oltre alla password, al codice via email e alle passkey, le persone possono entrare con un
account Google o Apple che abbia la stessa email del loro account. È facoltativo: se le voci
restano vuote, con Google e Apple non si entra e restano gli altri modi.

In `.env`:

```bash
# Google: client OAuth di tipo «Applicazione web» in Google Cloud
QDC_GOOGLE_CLIENT_ID=
QDC_GOOGLE_SECRET=

# Apple: «Sign in with Apple» da un account sviluppatore
QDC_APPLE_CLIENT_ID=      # il Services ID
QDC_APPLE_KEY_ID=
QDC_APPLE_TEAM_ID=
QDC_APPLE_PRIVATE_KEY=    # il contenuto della chiave .p8
```

Poi `docker compose up -d`.

:::{note}
L'accesso con Google e Apple non è ancora stato provato con account veri. Prima di
annunciarlo alle famiglie, provalo tu con un account Google e uno Apple.
:::
