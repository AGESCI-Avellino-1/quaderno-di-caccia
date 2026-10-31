# Lavori giornalieri

Alcuni comandi vanno lanciati ogni giorno: emettono le quote, mandano promemoria e
riepiloghi, riassumono le presenze vecchie. L'esempio pronto è in
`deploy/cron/qdc.crontab`.

| Comando | Cosa fa | Ora nell'esempio |
| --- | --- | --- |
| `riassumi_presenze` | le presenze più vecchie di due anni diventano totali per anno | 03:40 |
| `emetti_quote` | emette le quote il cui periodo è iniziato (le mensili il primo del mese) | 06:05 |
| `segnala_correzioni` | ai capigruppo, le correzioni da inoltrare a BuonaStrada | 07:15 |
| `avvisa_maggiore_eta` | a chi compie 18 anni e ai genitori | 07:20 |
| `promemoria_iscrizioni` | richieste di iscrizione nuove, promemoria, sospensioni | 07:25 |
| `promemoria_quote` | le quote non pagate in scadenza entro una settimana | 07:30 |
| `promemoria_buonacaccia` | le scadenze delle iscrizioni agli eventi su BuonaCaccia | 07:35 |
| `promemoria_lista_attesa` | dopo due anni in lista d'attesa, chiede se restare | 07:40 |
| `promemoria_fine_anno` | ai capigruppo, l'anno da chiudere e chi è da archiviare | 07:50 |

Per installarli, come l'utente che usa Docker:

```bash
crontab -e
```

e copia le righe di `deploy/cron/qdc.crontab`, correggendo il percorso `/srv/qdc` se hai
installato altrove (con Podman, `podman compose` al posto di `docker compose`). Gli orari sono
sfalsati perché le email non partano tutte insieme.
