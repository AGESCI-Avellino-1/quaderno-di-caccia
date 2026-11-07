# Installazione

## Scaricare il codice

```bash
git clone https://github.com/AGESCI-Avellino-1/quaderno-di-caccia.git /srv/qdc
cd /srv/qdc
git checkout v1.27.0
```

Installa sempre una **versione rilasciata**: le trovi, con il PDF del manuale d'uso, nella
pagina [Releases](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases) del
progetto; al posto di `v1.27.0` metti l'ultima. Il ramo `main` è quello di sviluppo e può
contenere lavori non ancora provati.

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

Lo script genera anche `QDC_IMPRONTA_CHIAVE`, la chiave che riconosce chi torna nel gruppo
dopo l'archiviazione: non si può rigenerare, quindi conserva una copia di `.env` insieme ai
backup (vedi [Archivio sul Drive](archivio)).

:::{warning}
`.env` contiene password e chiavi: resta sul server, leggibile solo dal suo proprietario
(lo script lo imposta così), e non va mai nel repository.
:::

Con `nginx-host`, `apache-host` e `apache-vhost` i container ascoltano solo su `127.0.0.1`,
sulla porta `8080` (cambiala con `--port`). Lo script controlla che la porta sia libera: se
la usa già un altro programma propone la prima libera (o, lanciato senza terminale, la
indica e si ferma). Con `nginx-host` e `apache-host` segui i comandi
che lo script stampa per installare il virtual host e prendere il certificato con certbot.

Quando l'app non risponde (per esempio durante un aggiornamento) il reverse proxy mostra una
pagina che lo spiega con l'aspetto dell'app, presa dalla cartella dell'installazione
(`frontend/public/errori/`): nginx o Apache devono poterla leggere. Se sposti l'installazione,
rilancia lo script e rimetti il virtual host o le direttive.

(apache-con-un-pannello)=
### Apache con un pannello (Virtualmin e simili)

Quando il server è gestito da un pannello, il virtual host del dominio lo crea il pannello,
che si occupa anche del certificato, dei log e della porta 80. Non serve un virtual host
nuovo: basta aggiungere a quello che c'è le direttive che mandano tutto all'app.

1. Nel pannello crea il sito per il dominio (per esempio `qdc.esempio.org`), con HTTPS e il
   certificato Let's Encrypt. PHP, database e posta del pannello non servono all'app.
   Se il pannello ha già messo nel virtual host direttive di proxy (`ProxyPass`,
   `ProxyPassReverse`, righe con `X-Forwarded-For`), toglile: un `ProxyPass /` verso un'altra
   porta che viene prima delle direttive dell'app vince su di loro, e l'app non si vede.
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

Il pannello riscrive il virtual host quando cambi le impostazioni del sito, rinnovi il
certificato da lì o ripristini un backup del pannello: ogni volta ricontrolla che le
direttive dell'app ci siano ancora e che non siano tornate quelle di proxy del pannello (i
[controlli](controlli) dicono subito se l'app risponde dal dominio).

## La posta

Il server di posta lo imposta l'amministratore tecnico dall'app, in **Impostazioni**, **Server
di posta**, con un'email di prova: SMTP, oppure Gmail con un accesso Google senza password.
Le strade, con il client OAuth di Google e il relay SMTP di Google, sono in [La
posta](posta).

In alternativa, o finché nessuno la imposta dall'app, completa in `.env` le voci SMTP:

```bash
DJANGO_EMAIL_HOST=smtp.esempio.org
DJANGO_EMAIL_PORT=587
DJANGO_EMAIL_HOST_USER=noreply@esempio.org
DJANGO_EMAIL_HOST_PASSWORD=…
DJANGO_EMAIL_USE_TLS=true
DJANGO_DEFAULT_FROM_EMAIL=Quaderno di Caccia <noreply@esempio.org>
```

Le email ai capi, ai genitori e ai ragazzi/e partono solo dopo che i capigruppo le accendono
nelle Impostazioni (**Chi riceve le email**): codici di accesso e inviti partono sempre.

## La schermata di avvio

All'apertura l'app mostra una pagina a righe con un'etichetta: il logo, il nome dell'app e, se lo
scrivi in `.env`, quello del gruppo (`QDC_NOME_AVVIO=AGESCI Gruppo Avellino 1`). Come il logo, si
ricava quando si costruisce l'app: se cambia, serve `docker compose up -d --build`. Su un iPhone
dove l'app era già installata, la nuova schermata può comparire solo reinstallandola sulla schermata
Home.

L'app installata tiene la schermata per almeno due secondi dall'apertura; nel browser sparisce appena
l'app è pronta. Per cambiare la durata scrivi in `.env` i secondi (`QDC_DURATA_AVVIO=3`, oppure `0`
per non aspettare), poi di nuovo `docker compose up -d --build`.

## Il logo del gruppo

Le icone dell'app (quella sul telefono e nel browser) e il logo nella barra in alto sono, di
base, il logo AGESCI. Per usare quello del gruppo:

1. copia il file nella cartella `resources/` dell'installazione: un SVG, oppure un PNG
   quadrato di almeno 512 pixel di lato;
2. scrivi il suo percorso in `.env`:

   ```bash
   QDC_LOGO=resources/logo-gruppo.svg
   ```

Le icone si ricavano dal file quando si costruisce l'app: se cambi il logo dopo l'avvio, dai
di nuovo `docker compose up -d --build`. Il file in `resources/` non fa parte del codice: gli
aggiornamenti non lo toccano. Il logo della carta intestata (stampe, ricevute) è un'altra
cosa: lo carica un capogruppo dall'app, in **Impostazioni**.

## Avviare

```bash
docker compose up -d --build
```

Il file `.env` dice a Compose quali file usare. Le migrazioni del database si applicano da
sole all'avvio del container `web`. Quando `docker compose ps` mostra `web` in salute, apri
l'indirizzo del sito: vedi la pagina di accesso. Se non la vedi, segui i
[controlli](controlli) passo per passo.

## Il servizio di sistema

Perché l'app parta da sola quando il server si riavvia, e per gestirla con `systemctl`,
installa il servizio di sistema. Una volta, con l'utente che gestisce l'app (quello che ha
dato `docker compose up`):

```bash
cd /srv/qdc
sudo scripts/installa-servizio.sh
```

Lo script capisce se c'è Docker o Podman, scrive `/etc/systemd/system/qdc.service` (i
container girano con il tuo utente) e lo attiva. Con Podman senza root fa anche in modo che
i container partano senza che nessuno entri nel server (`loginctl enable-linger`): il vecchio
`podman-restart.service` non serve più.

Da allora:

```bash
sudo systemctl status qdc     # com'è: «active (exited)» vuol dire avviata
sudo systemctl restart qdc    # riavvia l'app
sudo systemctl stop qdc       # ferma l'app
sudo systemctl start qdc      # la avvia
```

`status` dice se il servizio ha avviato i container; com'è ciascun container lo dice
`docker compose ps` (vedi i [controlli](controlli)). Riavvia il server una volta e
controlla che l'app risponda.

Con più installazioni sullo stesso server (per esempio un [server di prova](prova)) dai a
ciascuna il suo nome: `sudo scripts/installa-servizio.sh --nome qdc-prova`. Per togliere il
servizio senza fermare l'app: `sudo scripts/installa-servizio.sh --rimuovi`.

## Altre impostazioni in `.env`

| Voce | A cosa serve | Di base |
| --- | --- | --- |
| `QDC_INVITO_VALIDITA_GIORNI` | per quanti giorni vale un invito | 14 |
| `QDC_OFFLINE_GIORNI` | per quanti giorni un telefono tiene i dati senza collegarsi | 14 |
| `QDC_PHOTON_URL` | il servizio che propone gli indirizzi delle località, quello pubblico di Photon o uno tuo; vuota: niente proposte, gli indirizzi si scrivono a mano | `https://photon.komoot.io` |
| `QDC_NOME_AVVIO` | il nome del gruppo sulla schermata di avvio, sotto quello dell'app | vuota: solo il nome dell'app |
| `QDC_DURATA_AVVIO` | per quanti secondi, almeno, l'app installata mostra la schermata di avvio; 0: solo finché non è pronta | 2 |
| `QDC_LOGO` | il logo del gruppo per le icone dell'app | vuota: il logo AGESCI (vedi sopra) |
| `QDC_BANNER_INSTALLAZIONE_GIORNI` | dopo quanti giorni l'invito a installare l'app, chiuso, può ricomparire | 14 |
| `QDC_DRIVE_CREDENZIALI`, `QDC_DRIVE_CARTELLA`, `QDC_IMPRONTA_CHIAVE` | archivio sul Drive | vuote: vedi [Archivio sul Drive](archivio) |
| `QDC_GOOGLE_*`, `QDC_APPLE_*` | accesso con Google e Apple | vuote: vedi [Accesso con Google e Apple](google-apple) |
| `QDC_MAILPIT_CONSENTITO` | permette la modalità di prova delle email | `false`: vedi [Server di prova](prova) |

Dopo ogni modifica di `.env`: `docker compose up -d`.
