# Backup e ripristino

## Backup

Lo script salva il database e i file caricati (moduli firmati, foto, giustificativi delle
spese), con la stessa data nel nome:

```bash
scripts/backup-db.sh               # crea backups/qdc-<data>.sql.gz e backups/qdc-<data>.media.tar.gz
KEEP_DAYS=30 scripts/backup-db.sh  # e cancella quelli più vecchi di 30 giorni
```

Va lanciato con l'app in funzione. Usa Docker se c'è, altrimenti Podman. L'esempio dei
[lavori giornalieri](lavori-giornalieri) lo lancia ogni notte e tiene gli ultimi 30 giorni.

Un backup che resta solo sul server si perde insieme al server: copia regolarmente i file di
`backups/` su un altro computer o su uno spazio esterno, sempre cifrati.

I due file vanno sempre insieme: il database dice quali moduli e foto esistono, l'archivio dei
file li contiene. Con il solo database l'app mostra i moduli, ma non riesce ad aprirli.

Oltre ai backup, conserva una copia di:

- il file `.env` (segreti e configurazione), in particolare **`QDC_IMPRONTA_CHIAVE`**, che
  non si può rigenerare (vedi [Archivio sul Drive](archivio));
- la cartella `secrets/`.

:::{warning}
I backup contengono dati di minori, anche sanitari: conservali e spostali solo **cifrati**, e
mai nel repository (la cartella `backups/` è esclusa).
:::

## Ripristino

Il ripristino sostituisce **tutto** il contenuto dell'app con quello del backup: quello che è
stato fatto dopo il backup si perde. Avvisa i capi, perché dovranno rifare le modifiche
successive (presenze, pagamenti, schede).

Usa una versione dell'app **uguale o più recente** di quella che ha fatto il backup: all'avvio
l'app aggiorna da sola il database alla sua versione, ma non può tornare indietro.

1. **Su un server nuovo**, installa l'app come nella pagina [Installazione](installazione), ma
   rimetti al loro posto il file `.env` e la cartella `secrets/` del vecchio server prima di
   avviarla. Poi `docker compose up -d --build` e aspetta che `docker compose ps` mostri `web`
   in salute. Sul server di sempre questo passo non serve.

2. Ferma l'app, lasciando acceso solo il database:

   ```bash
   docker compose stop app web
   ```

3. Svuota il database:

   ```bash
   docker compose exec -T db sh -c 'dropdb -U "$POSTGRES_USER" "$POSTGRES_DB" && createdb -U "$POSTGRES_USER" "$POSTGRES_DB"'
   ```

4. Carica il backup del database (cambia la data con quella del tuo file):

   ```bash
   gunzip -c backups/qdc-20261101-053233.sql.gz \
     | docker compose exec -T db sh -c 'psql -q -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1'
   ```

   Se si ferma con un errore, non andare avanti: il database è a metà. Ripeti dal passo 3.

5. Rimetti i file caricati, al posto di quelli che ci sono ora:

   ```bash
   docker compose run --rm --no-deps -T --entrypoint sh web \
     -c 'find /data/media -mindepth 1 -delete && tar -xzf - -C /data/media' \
     < backups/qdc-20261101-053233.media.tar.gz
   ```

6. Riavvia:

   ```bash
   docker compose up -d
   ```

7. Controlla: entra nell'app, apri la scheda di una persona e un modulo firmato o una foto.

I telefoni restano collegati: le sessioni e i dispositivi sono nel backup. Un dispositivo
registrato dopo il backup, invece, non esiste più sul server: alla prossima apertura l'app su
quel telefono si cancella e chiede di entrare di nuovo.
