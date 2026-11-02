# Aggiornamenti

Le nuove versioni sono nella pagina
[Releases](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases) del progetto,
ognuna con le sue note e il PDF del manuale d'uso: leggi le note prima di aggiornare.

Prima di ogni aggiornamento fai un [backup](backup). Poi, con il numero della versione nuova
al posto di `v1.3.0`:

```bash
cd /srv/qdc
git fetch --tags
git checkout v1.3.0
docker compose up -d --build
```

Le migrazioni del database si applicano da sole all'avvio del container `web`. Se cambia
`.env.example`, confrontalo con il tuo `.env` per le voci nuove (per vederlo:
`git diff v1.2.0 v1.3.0 -- .env.example`, con la versione che avevi e quella nuova).

Se usi `nginx-host`, `apache-host` o `apache-vhost`, rilancia anche
`scripts/configure-prod.sh` con le stesse opzioni e confronta il file in `deploy/generated/`
con il virtual host o le direttive installate: le note della versione dicono quando cambiano.

Per un aggiornamento importante, provalo prima su un [server di prova](prova).
