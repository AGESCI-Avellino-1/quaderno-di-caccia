# Aggiornamenti

Le nuove versioni sono nella pagina
[Releases](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases) del progetto,
ognuna con le sue note e il PDF del manuale d'uso: leggi le note prima di aggiornare.

## Con lo script

Con l'utente che gestisce l'app:

```bash
cd /srv/qdc
scripts/aggiorna.sh            # all'ultima versione
scripts/aggiorna.sh v1.5.0     # a una versione precisa
```

Lo script:

1. controlla che nessun file dell'app sia stato modificato a mano e trova la versione (senza
   indicarla, l'ultima: il tag `vX.Y.Z` più recente);
2. se cambia `.env.example`, ti mostra le differenze e chiede se proseguire: confrontale con il
   tuo `.env` e aggiungi le voci nuove che ti servono; se cambiano le configurazioni del
   reverse proxy sul server, ti dice di rilanciare `scripts/configure-prod.sh`;
3. mette l'app in **manutenzione** (se c'era già, la lascia alla fine);
4. fa il [backup](backup) del database e dei file;
5. passa alla versione nuova, la ricostruisce e la riavvia (con `sudo systemctl restart`, se
   hai installato il [servizio di sistema](installazione), e allora ti chiede la password di
   sudo);
6. aspetta fino a 5 minuti che l'app risponda: le migrazioni del database si applicano da
   sole all'avvio;
7. toglie la manutenzione.

Con `--si` non chiede conferme (le differenze le mostra comunque).

### Se l'app non risponde

Lo script **torna da solo alla versione di prima**. Poi:

- se il database non era ancora cambiato, riavvia la versione di prima, controlla che
  risponda e toglie la manutenzione: l'app è come prima dell'aggiornamento. Guarda le righe di
  `docker compose logs web` che lo script mostra e segnala il problema;
- se la versione nuova aveva già cambiato il database, la versione di prima potrebbe non
  funzionare: lo script lascia l'app in manutenzione e ti dice il nome del backup appena
  fatto. [Ripristinalo](backup) (con la versione di prima, che ora è quella in uso), controlla
  che l'app risponda e togli la manutenzione con `docker compose exec web python manage.py
  manutenzione disattiva`, o dall'app.

Aggiornando da una versione fino alla 1.4 lo script non riesce a mettere la manutenzione da sé:
te lo dice, e puoi metterla dall'app prima di proseguire.

## A mano

Prima di ogni aggiornamento fai un [backup](backup). Poi, con il numero della versione nuova
al posto di `v1.5.0`:

```bash
cd /srv/qdc
git fetch --tags
git checkout v1.5.0
docker compose up -d --build
```

Le migrazioni del database si applicano da sole all'avvio del container `web`. Se cambia
`.env.example`, confrontalo con il tuo `.env` per le voci nuove (per vederlo:
`git diff v1.4.0 v1.5.0 -- .env.example`, con la versione che avevi e quella nuova).

## Dopo l'aggiornamento

Se usi `nginx-host`, `apache-host` o `apache-vhost`, e le note della versione dicono che
cambiano, rilancia `scripts/configure-prod.sh` con le stesse opzioni e confronta il file in
`deploy/generated/` con il virtual host o le direttive installate.

Per un aggiornamento importante, provalo prima su un [server di prova](prova).
