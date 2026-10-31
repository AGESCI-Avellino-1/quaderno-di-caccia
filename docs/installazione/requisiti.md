# Cosa serve

- Un **server Linux** raggiungibile da internet, con **Docker** e Docker Compose (oppure
  Podman con `podman compose`). Tutto gira in container: PostgreSQL, Django e un nginx che
  serve l'app e le API sullo stesso indirizzo.
- Un **nome a dominio** (per esempio `qdc.esempio.org`) che punta al server, e un
  certificato **HTTPS** (lo script di configurazione ti indica i comandi di certbot).
- Davanti ai container, un **reverse proxy**: l'nginx incluso, se il server è dedicato,
  oppure l'nginx o l'Apache già presenti sul server.
- Una **casella di posta** con accesso SMTP, da cui partono codici di accesso, inviti,
  ricevute e avvisi.
- `git` e `python3` sul server (lo script di configurazione genera i segreti con Python).
- Per l'**archivio** dei fascicoli (facoltativo ma consigliato): un **Drive condiviso** di
  Google Workspace del gruppo (vedi [Archivio sul Drive](archivio)).
- Per entrare con **Google** o **Apple** (facoltativo): un progetto Google Cloud e un
  account sviluppatore Apple (vedi [Accesso con Google e Apple](google-apple)).
- L'export **Ricerca soci** del gruppo da BuonaStrada, scaricato da un capogruppo.
