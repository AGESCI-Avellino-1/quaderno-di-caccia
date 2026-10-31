# Backup

Il database si salva con lo script:

```bash
scripts/backup-db.sh               # crea backups/qdc-<data>.sql.gz
KEEP_DAYS=30 scripts/backup-db.sh  # e cancella quelli più vecchi di 30 giorni
```

Puoi lanciarlo ogni notte dal cron, come i lavori giornalieri.

Oltre al database, conserva:

- il file `.env` (segreti e configurazione), in particolare **`QDC_IMPRONTA_CHIAVE`**, che
  non si può rigenerare (vedi [Archivio sul Drive](archivio));
- la cartella `secrets/`;
- il volume `media` dei container, con i file caricati (moduli firmati, foto, giustificativi).

:::{warning}
I backup contengono dati di minori, anche sanitari: conservali e spostali solo **cifrati**, e
mai nel repository (la cartella `backups/` è esclusa).
:::
