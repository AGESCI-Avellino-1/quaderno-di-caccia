# Aggiornamenti

Prima di ogni aggiornamento fai un [backup](backup). Poi:

```bash
cd /srv/qdc
git pull
docker compose up -d --build
```

Le migrazioni del database si applicano da sole all'avvio del container `web`. Se cambia
`.env.example`, confrontalo con il tuo `.env` per le voci nuove.

Per un aggiornamento importante, provalo prima su un [server di prova](prova).
