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
| `apache-vhost` | Sul server c'è già Apache e il virtual host del dominio lo crea un pannello (Virtualmin, ISPConfig, Plesk…): lo script genera solo le direttive da aggiungere, vedi [sotto](#apache-con-un-pannello) |

Con `nginx-host`, `apache-host` e `apache-vhost` i container ascoltano solo su `127.0.0.1`,
sulla porta `8080` (cambiala con `--port`). Con `nginx-host` e `apache-host` segui i comandi
che lo script stampa per installare il virtual host e prendere il certificato con certbot.

(apache-con-un-pannello)=
### Apache con un pannello (Virtualmin e simili)

Quando il server è gestito da un pannello, il virtual host del dominio lo crea il pannello,
che si occupa anche del certificato, dei log e della porta 80. Non serve un virtual host
nuovo: basta aggiungere a quello che c'è le direttive che mandano tutto all'app.

1. Nel pannello crea il sito per il dominio (per esempio `qdc.esempio.org`), con HTTPS e il
   certificato Let's Encrypt. PHP, database e posta del pannello non servono all'app.
2. Genera le direttive:

   ```bash
   scripts/configure-prod.sh --proxy apache-vhost --domain qdc.esempio.org
   ```

   Lo script le scrive in `deploy/generated/qdc-apache-vhost.conf`.
3. Copia la prima parte del file (fino a «Inside `<VirtualHost *:80>`») dentro il virtual host
   **HTTPS** (porta 443) del dominio, in fondo alle direttive che ci sono già. In Virtualmin:
   **Web Configuration → Configure SSL Website → Edit Directives**.
4. Se il pannello non reindirizza già da HTTP a HTTPS (in Virtualmin è un'opzione del sito),
   aggiungi al virtual host della porta 80 le ultime tre righe del file, senza il `#`.
5. Controlla che i moduli `proxy`, `proxy_http` e `headers` di Apache siano attivi, poi
   ricarica Apache:

   ```bash
   sudo a2enmod proxy proxy_http headers
   sudo apachectl configtest && sudo systemctl reload apache2
   ```

   Su Rocky, Alma e RHEL i moduli sono già attivi e il servizio si chiama `httpd`:
   `sudo systemctl reload httpd`.

Le direttive mandano all'app tutto tranne `/.well-known/`, che resta al pannello: serve a
rinnovare il certificato. La cartella del sito (`public_html`), i file `.htaccess` e PHP
non vengono più usati per quel dominio.

:::{warning}
Non aggiungere altre righe su `X-Forwarded-For`, come quelle di alcuni modelli di
Virtualmin: Apache aggiunge già da solo l'indirizzo di chi si collega, ed è quello che
l'app usa per bloccare chi sbaglia la password troppe volte.
:::

Se rifai il sito dal pannello (o lo ricrea un ripristino del pannello), rimetti le direttive.

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
