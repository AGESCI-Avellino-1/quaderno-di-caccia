# Installazione

## Scaricare il codice

```bash
git clone https://github.com/AGESCI-Avellino-1/quaderno-di-caccia.git /srv/qdc
cd /srv/qdc
```

Negli esempi l'installazione è in `/srv/qdc`: se scegli un'altra cartella, cambiala anche
nei lavori giornalieri.

## Configurare

Lo script `scripts/configure-prod.sh` crea il file `.env` con i segreti generati (non li
sovrascrive se lo rilanci), imposta dominio e reverse proxy e stampa i passi successivi.

```bash
scripts/configure-prod.sh --proxy nginx-host --domain qdc.esempio.org
```

| `--proxy` | Quando usarlo |
| --- | --- |
| `nginx-docker` | Server dedicato: l'nginx del container pubblica le porte 80 e 443 e gestisce il certificato |
| `nginx-host` | Sul server c'è già nginx: lo script genera il virtual host in `deploy/generated/` |
| `apache-host` | Sul server c'è già Apache: lo script genera il virtual host in `deploy/generated/` |

Con `nginx-host` e `apache-host` i container ascoltano solo su `127.0.0.1`, sulla porta
`8080` (cambiala con `--port`). Segui i comandi che lo script stampa per installare il
virtual host e prendere il certificato con certbot.

:::{warning}
`.env` contiene password e chiavi: resta sul server, leggibile solo dal suo proprietario
(lo script lo imposta così), e non va mai nel repository.
:::

## La posta

In `.env` completa le voci SMTP:

```bash
DJANGO_EMAIL_HOST=smtp.esempio.org
DJANGO_EMAIL_PORT=587
DJANGO_EMAIL_HOST_USER=noreply@esempio.org
DJANGO_EMAIL_HOST_PASSWORD=…
DJANGO_EMAIL_USE_TLS=true
DJANGO_DEFAULT_FROM_EMAIL=Quaderno di Caccia <noreply@esempio.org>
```

## Avviare

```bash
docker compose up -d --build
```

Il file `.env` dice a Compose quali file usare. Le migrazioni del database si applicano da
sole all'avvio del container `web`. Quando `docker compose ps` mostra `web` in salute, apri
l'indirizzo del sito: vedi la pagina di accesso.

## Altre impostazioni in `.env`

| Voce | A cosa serve | Di base |
| --- | --- | --- |
| `QDC_INVITO_VALIDITA_GIORNI` | per quanti giorni vale un invito | 14 |
| `QDC_OFFLINE_GIORNI` | per quanti giorni un telefono tiene i dati senza collegarsi | 14 |
| `QDC_DRIVE_CREDENZIALI`, `QDC_DRIVE_CARTELLA`, `QDC_IMPRONTA_CHIAVE` | archivio sul Drive | vuote: vedi [Archivio sul Drive](archivio) |
| `QDC_GOOGLE_*`, `QDC_APPLE_*` | accesso con Google e Apple | vuote: vedi [Accesso con Google e Apple](google-apple) |
| `QDC_MAILPIT_CONSENTITO` | permette la modalità di prova delle email | `false`: vedi [Server di prova](prova) |

Dopo ogni modifica di `.env`: `docker compose up -d`.
