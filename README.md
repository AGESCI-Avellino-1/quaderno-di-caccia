# Quaderno di Caccia (QdC)

[![CI](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/actions/workflows/ci.yml/badge.svg)](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/actions/workflows/ci.yml)
[![Licenza: MIT](https://img.shields.io/badge/licenza-MIT-yellow.svg)](LICENSE)
[![Python 3.14](https://img.shields.io/badge/python-3.14-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Django 6.1](https://img.shields.io/badge/django-6.1-092E20?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Vue 3](https://img.shields.io/badge/vue-3.5-4FC08D?logo=vuedotjs&logoColor=white)](https://vuejs.org/)
[![PWA](https://img.shields.io/badge/PWA-offline-5A0FC8?logo=pwa&logoColor=white)](https://web.dev/explore/progressive-web-apps)
[![PostgreSQL 18](https://img.shields.io/badge/postgresql-18-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![uv](https://img.shields.io/badge/uv-managed-DE5FE9?logo=uv&logoColor=white)](https://docs.astral.sh/uv/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Stato: fase 1](https://img.shields.io/badge/stato-fase%201%20in%20corso-orange)](#stato)

L'app del Gruppo Scout AGESCI **Avellino 1** per anagrafica, fascicolo personale,
Progressione Personale, eventi e presenze, quote e cassa. I capi la usano anche senza
rete (riunioni in sede, campi); ragazzi e genitori vedono solo la propria parte.
Altri gruppi possono installarne una copia.

> Il nome è quello del quaderno di caccia cartaceo dei ragazzi, che resta: nei testi
> per le famiglie scriviamo "l'app QdC".

## Indice

- [Stato](#stato)
- [Documentazione](#documentazione)
- [Struttura del repository](#struttura-del-repository)
- [Sviluppo](#sviluppo)
- [Primo avvio dei dati](#primo-avvio-dei-dati)
- [Produzione](#produzione)
- [Dati personali e sicurezza](#dati-personali-e-sicurezza)
- [Licenze](#licenze)

## Stato

Fasi 1–5 pronte (fondamenta, quote e cassa, eventi e presenze, fascicolo completo);
Progressione Personale pronta per tutte le branche. Tra le funzioni principali:

- account con invito (email, codice via email, passkey, Google, Apple), ruoli con
  diarchia, unità e squadriglie, regole di visibilità per ogni ruolo;
- importazione dell'export **"Ricerca Soci" di BuonaStrada** con anteprima, genitori e
  fratelli riconosciuti in automatico, correzioni dell'app mai sovrascritte;
- PWA installabile, con copia cifrata dei dati sul telefono per l'uso offline, sblocco
  con PIN o impronta, revoca a distanza dei dispositivi e coda delle modifiche fatte
  senza rete;
- farmaci, allergie e intolleranze compilati dai genitori (o trascritti dai capi) e la
  pagina **Al campo** con i dati dell'unità consultabili anche senza rete;
- quote, pagamenti, ricevute e prima nota; eventi, presenze, calendario ed eventi
  BuonaCaccia; Progressione Personale L/C, E/G e R/S con i passaggi tra branche;
- scheda sanitaria completa con stampa, note, fascicolo del ragazzo e dei capi, chiusura
  dell'anno e archivio sul Drive del gruppo.

Le fasi successive (bacheca, estratto conto, documentazione di uso) sono descritte
nell'analisi e nella roadmap di
[`CLAUDE.md`](CLAUDE.md#roadmap-phases-from-the-analysis).

## Documentazione

| Documento | Per chi |
| --- | --- |
| [`docs/analisi/analisi-requisiti.md`](docs/analisi/analisi-requisiti.md) | Tutti: cosa fa l'app e perché. Ogni decisione ha un codice `DEC-nn` |
| [`CLAUDE.md`](CLAUDE.md) | Sviluppatori (e Claude Code): regole, architettura, roadmap |
| [`backend/CLAUDE.md`](backend/CLAUDE.md), [`frontend/CLAUDE.md`](frontend/CLAUDE.md) | Dettagli delle due parti |
| [`backend/data/cataloghi/`](backend/data/cataloghi/README.md) | Voci del Modello D, specialità e brevetti |

## Struttura del repository

```
backend/    Django 6.1 + API (django-ninja) + autenticazione (django-allauth)
frontend/   PWA Vue 3 + TypeScript (Vite)
docs/       analisi dei requisiti
deploy/     configurazioni del reverse proxy (nginx in Docker, nginx o Apache sul server)
scripts/    configure-prod.sh, backup-db.sh
compose.dev.yml          solo PostgreSQL, per lo sviluppo
compose.prod.yml         produzione: db + backend + app (nginx)
compose.nginx-docker.yml aggiunta per la modalità "nginx in Docker"
```

## Sviluppo

### Requisiti

- [mise](https://mise.jdx.dev/) (installa Python 3.14, Node 22 e uv nelle versioni
  giuste), oppure le tre cose a mano;
- Docker, per il PostgreSQL di sviluppo.

### Avvio

```bash
mise install
mise run setup        # crea .env, avvia PostgreSQL, installa le dipendenze, migra il database
mise run backend      # Django su http://localhost:8000
mise run frontend     # app su http://localhost:5173  ← si usa questa
```

Le email (codici di accesso, inviti) in sviluppo compaiono nel terminale di Django.
Se l'amministratore tecnico accende le «Email di prova» nelle Impostazioni, finiscono
invece in Mailpit (avviato da `mise run db` insieme a PostgreSQL), che lui apre dal menu
Amministrazione all'indirizzo `/mailpit/`.
`mise tasks` elenca gli altri comandi (`test`, `lint`, `format`, `importa`…).

### IDE

- **Backend → PyCharm**: aprire la cartella `backend/` come progetto e scegliere come
  interprete `backend/.venv` (creato da `uv sync`). Il supporto Django (template,
  `manage.py`, run configuration) è nelle funzioni Pro. Le run configuration
  *Django runserver* e *pytest* sono già in `backend/.run/`.
- **Frontend → WebStorm**: aprire la cartella `frontend/`; riconosce Vue, TypeScript,
  ESLint e Prettier dal progetto. Run configuration *dev* e *test* in `frontend/.run/`.
  In alternativa PyCharm Pro include lo stesso supporto Vue/TypeScript, e si può
  aprire la radice del repository con entrambe le cartelle.
  *[da verificare]* JetBrains offre licenze gratuite per l'uso non commerciale e per
  i progetti open source: controllare quale si applica al gruppo.
- Per lo sviluppo con **Claude Code**, partire dalla radice del repository: legge
  `CLAUDE.md` e le regole di ciascuna parte.

### Controlli prima di un commit

```bash
mise run lint && mise run test
```

La CI (GitHub Actions) ripete gli stessi controlli, esegue i test del backend su
PostgreSQL e costruisce le immagini Docker.

## Primo avvio dei dati

Su un'installazione vuota nessuno può ancora invitare qualcuno dall'app. L'ordine è:

```bash
cd backend
uv run python manage.py createsuperuser                                  # amministratore tecnico
uv run python manage.py importa_buonastrada RicercaSoci.csv              # anteprima
uv run python manage.py importa_buonastrada RicercaSoci.csv --applica    # importa
uv run python manage.py crea_invito <codice socio> <email> --capogruppo  # primo capogruppo
```

L'amministratore tecnico gestisce account e importazioni, ma **non vede i dati
educativi** dei ragazzi (DEC-12). Dal capogruppo in poi gli inviti partono dall'app.
In produzione gli stessi comandi si lanciano con
`docker compose exec web python manage.py …`.

> L'export di BuonaStrada contiene dati di minori: non va mai messo nel repository né
> lasciato sul server dopo l'importazione.

## Produzione

Tutto gira in Docker: PostgreSQL, Django (gunicorn) e un nginx (`app`) che serve la PWA
e inoltra a Django i percorsi delle API, così app e API stanno sullo stesso indirizzo.
Davanti serve un reverse proxy con HTTPS, scelto con lo script:

```bash
scripts/configure-prod.sh --proxy nginx-host --domain qdc.esempio.org
```

| `--proxy` | Quando usarlo |
| --- | --- |
| `nginx-docker` | Server dedicato: l'nginx del container pubblica le porte 80/443 e gestisce il certificato |
| `nginx-host` | Sul server c'è già nginx: lo script genera il virtual host in `deploy/generated/` |
| `apache-host` | Sul server c'è già Apache: idem, per Apache |

Lo script crea `.env` (con segreti generati, che non sovrascrive se lo rilanci),
imposta dominio e numero di proxy e stampa i passi successivi (certificato, attivazione
del virtual host). Poi:

```bash
# completare in .env le voci DJANGO_EMAIL_* (SMTP)
docker compose up -d --build
docker compose exec web python manage.py createsuperuser
```

Le migrazioni si applicano all'avvio del container `web`.

Alcuni comandi vanno lanciati ogni giorno (quote da emettere, promemoria, riepiloghi ai
capigruppo, presenze da riassumere): l'esempio pronto, con l'elenco, è in
[`deploy/cron/qdc.crontab`](deploy/cron/qdc.crontab); si copia con `crontab -e`
correggendo il percorso dell'installazione (con Podman, `podman compose`).

La guida di installazione completa, per chi installa una copia per il suo gruppo, è in
[`docs/installazione/`](docs/installazione/index.md) (`mise run docs:installazione`).

### Email di prova (Mailpit)

Su un server di prova si possono trattenere tutte le email in Mailpit invece di
spedirle: in `.env` `QDC_MAILPIT_CONSENTITO=true`, poi
`COMPOSE_PROFILES=mailpit docker compose up -d`. L'amministratore tecnico la accende e la
spegne nelle Impostazioni e legge le email su `/mailpit/` (solo lui, attraverso Django:
Mailpit non pubblica porte). Non usarla sul server con i dati veri: in Mailpit finiscono
anche i codici di accesso e gli inviti, che fanno entrare come chiunque.

### Drive del gruppo per l'archivio

Due anni dopo l'uscita il fascicolo di una persona va, come file ZIP, in una cartella del
Drive condiviso del gruppo (Google Workspace); solo dopo il caricamento verificato l'app
cancella i dati, tenendo nome e anni nel gruppo. Per collegare il Drive, una volta:

1. in Google Cloud, crea un progetto, abilita la «Google Drive API» e crea un *account di
   servizio*; scaricane la chiave JSON;
2. nel Drive condiviso del gruppo aggiungi l'indirizzo email dell'account di servizio come
   *Gestore contenuti* e crea la cartella per gli archivi; copiane l'id (la parte finale
   dell'indirizzo della cartella);
3. metti la chiave in `secrets/drive.json` accanto a `compose.prod.yml` (la cartella
   `secrets/` non va mai nel repository) e in `.env`:
   `QDC_DRIVE_CREDENZIALI=/run/qdc-secrets/drive.json` e `QDC_DRIVE_CARTELLA=<id>`;
4. genera una volta la chiave che riconosce chi rientra dopo l'archiviazione
   (`openssl rand -hex 32`) e mettila in `.env` come `QDC_IMPRONTA_CHIAVE`. **Conservala
   insieme ai backup e non cambiarla mai**, nemmeno se rigeneri `DJANGO_SECRET_KEY` o
   sposti l'app su un altro server: con una chiave diversa chi è stato archiviato non viene
   più riconosciuto in automatico quando torna (resta solo il caricamento a mano dello ZIP);
5. riavvia `web`. Nella pagina del gruppo, sezione «Archivio», sparisce l'avviso
   «L'archivio non è ancora configurato».

Per il backup del database: `scripts/backup-db.sh` (il file contiene dati di minori: va
conservato cifrato).

## Dati personali e sicurezza

Il titolare del trattamento è AGESCI nazionale; i capigruppo sono delegati (DEC-98).
In sintesi:

- chi vede cosa è deciso in un solo punto del backend (`apps/permessi/policy.py`), con
  test per ogni ruolo;
- accesso con invito, passkey o codice via email, limite ai tentativi di accesso,
  registro delle modifiche su tutti i dati;
- i dati copiati sul telefono sono **cifrati** e si aprono con un PIN di almeno 6 cifre,
  o con impronta o volto (DEC-97). L'app si blocca dopo 5 minuti senza uso; dopo 5 PIN
  sbagliati, all'uscita dall'account o se il telefono non si collega per 14 giorni la
  copia viene cancellata;
- un telefono perso si scollega a distanza, dal proprietario o da un capogruppo
  (pagina *Dispositivi*): alla prima riapertura con la rete cancella i propri dati;
- al campo, offline, i capi hanno contatti, farmaci, allergie e intolleranze dei
  ragazzi, non l'intera scheda medica (DEC-55); ogni lettura e ogni scaricamento di
  questi dati viene registrato ed è consultabile dalla Co.Ca. (DEC-101);
- nessun dato reale nel repository: i test usano un export inventato.

Per segnalare un problema di sicurezza scrivere al responsabile del progetto, non
aprire una issue pubblica.

## Licenze

- Codice: [MIT](LICENSE) © 2026 Andrea Bruno.
- Colori e variabili del tema (`frontend/src/theme/_palette.scss`, `_branche.scss`): da
  [django-agesci-campania-theme](https://github.com/AGESCI-Campania/django-agesci-campania-theme),
  licenza MIT (copia in `frontend/src/theme/LICENSE-django-agesci-campania-theme`).
- Carattere Titillium Web: SIL Open Font License 1.1
  ([`frontend/src/assets/fonts/OFL.txt`](frontend/src/assets/fonts/OFL.txt)).
- Loghi ed emblemi AGESCI: proprietà dell'associazione, usati secondo il manuale
  dell'immagine coordinata. Le icone dell'app usano per ora l'emblema del Gruppo
  Avellino 1, in attesa di un'icona dedicata.
