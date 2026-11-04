# Novità del Quaderno di Caccia

Le novità di ogni versione, dalla più recente. `scripts/aggiorna.sh` mostra le sezioni tra la
versione installata e quella nuova prima di chiedere se aggiornare. Il dettaglio di ogni
versione, con il manuale in PDF, è nella pagina
[Releases](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases).

## 1.12.0 — 4 novembre 2026

### Novità

**Organigramma**: dopo gli incarichi di Comunità capi ci sono gli staff delle unità, una sezione per unità (L/C, E/G, R/S) con capo unità, staff e assistente ecclesiastico. Si guardano soltanto: si nominano sempre dalla pagina dell'unità, che si apre toccando il suo nome.

**Elenco degli incarichi in PDF**:

- cognome e nome in maiuscolo, come negli elenchi di BuonaStrada;
- in ogni unità prima i capi unità e in Comunità capi prima i capigruppo, la capo prima del capo; poi gli altri per cognome;
- nel menu «Incarichi da includere», oltre a «Tutti» e «Nessuno», «Educativi» (tutti tranne tesorieri e amministratore tecnico) e «Non educativi» (tesoriere di gruppo, tesoriere di unità, amministratore tecnico).

### Aggiornare

```bash
scripts/aggiorna.sh v1.12.0
```

Nessuna migrazione del database. `.env`, `compose.prod.yml` e virtual host non cambiano.

## 1.11.0 — 4 novembre 2026

### Novità

**Riunioni**, separate dagli eventi, nel menu «Riunioni»:

- si creano come serie (per esempio ogni sabato dal 1° ottobre al 31 maggio) o singole; di una serie si annulla o si sposta una sola riunione, e solo allora parte un'email;
- tipi: di unità e di Comunità capi, di squadriglia, di Alta Squadriglia, Consiglio Capi, Con.Ca.Vi. e Consiglio degli Anziani;
- uniforme sì o no, informazioni scritte con l'editor, nessuna quota; presenze e calendario come prima;
- le località del gruppo (sedi, basi) le gestiscono i capigruppo nelle Impostazioni; una località nuova scritta creando una riunione entra subito nell'elenco;
- le riunioni già create sono diventate riunioni, con le loro presenze.

**Turni di squadriglia e di sestiglia**: dalla pagina dell'unità lo staff definisce i turni (pulizia, preghiera…) e le sestiglie, e li fa girare ogni settimana o ogni mese. Ognuno vede il turno della sua squadriglia o sestiglia sulle riunioni; lo staff può cambiarlo a mano.

**Email un po' alla volta**: le email a molte persone partono a blocchi (di base 20, poi 2 minuti di pausa, al massimo 400 al giorno), cambiabili in Impostazioni. Codici di accesso e nuove password partono subito.

**Account**:

- in Soci e Genitori, «Invita chi non ha un account» manda l'invito a più persone insieme;
- il link personale per un ragazzo dai 14 ai 18 anni senza account: lo generano lo staff, i capigruppo e il capo squadriglia, e si manda come si vuole (WhatsApp, a voce…); i genitori ricevono un'email quando l'account è creato;
- un capogruppo porta un genitore in Comunità capi con «Porta in Comunità capi…» e può annullare finché il codice socio è provvisorio; il vecchio link di iscrizione da capo non c'è più (quelli già mandati valgono fino alla scadenza);
- l'amministratore tecnico ha la pagina «Account», con tutti gli account e le azioni su ognuno (sblocca, disattiva, cambia l'email, cancella…): ogni azione chiede un motivo e la persona riceve un'email.

**Piccole cose**: cliccando sull'avatar accanto a un nome si apre la scheda, se si ha il permesso di vederla; nel PDF dell'organigramma i tipi di incarico si scelgono da un menu a scelta multipla; nell'elenco degli incarichi in PDF chi ha un codice provvisorio è «NUOVO CENSITO».

### Aggiornare

```bash
scripts/aggiorna.sh v1.11.0
```

Sei migrazioni del database, applicate da sole all'avvio. In `compose.prod.yml` c'è un servizio nuovo, `posta`, che manda le email in coda: si avvia con gli altri. Dopo l'aggiornamento controlla con `docker compose ps` che `posta` sia avviato; se resta fermo, le email a molte persone aspettano (i suoi messaggi sono in `docker compose logs posta`). In `.env.example` c'è la voce facoltativa `QDC_EMAIL_IN_CODA` (di base attiva): non serve aggiungerla. Il virtual host non cambia.

## 1.10.0 — 3 novembre 2026

### Novità

**Editor di testo** (modelli e piè di pagina delle email, privacy policy e termini):

- le immagini si ridimensionano: selezionandole compaiono **Piccola**, **Media**, **Grande** e **Originale**, e sul computer si può trascinare un angolo; nelle email un'immagine non è mai più larga del messaggio, anche sul telefono;
- testo e immagini si allineano a sinistra, al centro o a destra;
- il pulsante **HTML** mostra il codice da modificare a mano; restano solo gli elementi che le email possono contenere, e l'editor dice cosa ha tolto.

**Aggiornamenti più chiari**: `scripts/aggiorna.sh` mostra, prima di chiedere se aggiornare, le novità di ogni versione tra quella installata e quella nuova, prese da questo file (`CHANGELOG.md`). Lo fa lo script della versione installata: si vede dagli aggiornamenti che partono dalla 1.10.

**Manutenzione del progetto**: Node 26 (la versione a supporto lungo) per costruire l'app; gli aggiornamenti automatici delle librerie aspettano due settimane dall'uscita di una versione, tranne quelli di sicurezza.

### Aggiornare

```bash
scripts/aggiorna.sh v1.10.0
```

Nessuna migrazione del database. `.env` e virtual host non cambiano. L'immagine dell'app si costruisce con Node 26: lo scarica da solo la build.

## 1.9.0 — 3 novembre 2026

### Novità

**Invita nel gruppo**: chiunque usi l'app, genitori e ragazzi compresi, trova nel menu e nella Home, in «Il mio gruppo», la voce «Invita nel gruppo», con:

- il link della lista d'attesa, da mandare con il pulsante «Condividi» del telefono (WhatsApp, email…) o da copiare;
- il QR code da far inquadrare, che si può anche scaricare come immagine per volantini e post; link e QR funzionano anche senza rete;
- un volantino A4 in PDF da stampare, con l'intestazione del gruppo, un breve testo, il QR code e il link.

Il link è uguale per tutti e non dice chi l'ha condiviso. In fondo alla pagina pubblica della lista d'attesa c'è lo stesso pulsante «Condividi», così chi riceve il link può girarlo.

I capigruppo cambiano il testo del volantino nelle Impostazioni, in «Volantino della lista d'attesa», con i segnaposto [Gruppo] e [Sigla gruppo], e possono tornare al testo di base.

### Aggiornare

```bash
scripts/aggiorna.sh v1.9.0
```

Una migrazione del database (il testo del volantino), applicata da sola all'avvio. `.env` e virtual host non cambiano.

## 1.8.0 — 3 novembre 2026

I campi nuovi di Bootstrap 6 (tema 3.0.0a3), il PIN di 6 cifre, l'Organigramma, la Progressione divisa per unità, i pulsanti accanto ai numeri di telefono e i numeri nella rubrica.

### Novità

- **PIN di 6 cifre**: si sceglie e si scrive in sei caselle, e l'app si sblocca da sola alla sesta cifra.
  - Chi aveva scelto un PIN più lungo tocca «Il tuo PIN è più lungo di 6 cifre?», lo scrive una volta e subito dopo ne sceglie uno nuovo di 6 cifre. I dati sul telefono restano.
- **Codici nelle caselle**: il codice via email (8 lettere e cifre, anche con il trattino) e quello dell'app di autenticazione; si entra appena il codice è completo. Per il secondo fattore resta il codice di recupero.
- **Password**: ognuna si può mostrare in chiaro con l'occhio accanto; quelle nuove dicono quanto sono robuste.
- **Organigramma**: è il nuovo nome di «Incarichi di gruppo».
- **Modelli delle email**: in una pagina a parte, con un link dalle Impostazioni.
- **Progressione per unità**: chi serve in più unità trova una scheda per unità, con nome e codice, e dentro Progressione, Imprese, Carta di clan e Passaggi. Con due reparti in parallelo si vede subito di quale unità è ogni voce.
- **Pulsanti accanto ai numeri di telefono**: chiama e WhatsApp, e se vuoi anche SMS. Ognuno sceglie quali vedere in «Privacy e preferenze» (il nuovo nome di «Privacy»), e la scelta vale su tutti i suoi dispositivi.
- **Numeri nella rubrica del telefono**: i capi (elenco dei soci e dei genitori, pagina dell'unità) e il capo squadriglia («La mia squadriglia») scelgono le persone e scaricano un file di contatti che il telefono propone di salvare.
  - Si può solo con la rete, e solo per i numeri che già vedi.
  - Nel file ci sono solo nome e numeri.
- **Altri componenti nuovi**:
  - avatar con foto o iniziali negli elenchi;
  - sezioni apribili nella Home;
  - «€» dentro i campi importo;
  - passi in fila per la Progressione, le stagioni L/C e la richiesta di iscrizione;
  - scelte a chip per il «A chi» degli avvisi e per l'unità nell'elenco delle persone.

### Aggiornare

```bash
scripts/aggiorna.sh v1.8.0
```

Una migrazione del database (i pulsanti dei telefoni), applicata da sola all'avvio. `.env` e virtual host non cambiano.

## 1.7.0 — 3 novembre 2026

La professione da BuonaStrada, gli assistenti ecclesiastici solo presbiteri, l'ordine delle unità nell'elenco degli incarichi e la propria foto nel menu.

### Novità

- **Professione**: arriva da BuonaStrada per tutti i soci che l'hanno.
  - **Chi la vede:** la persona stessa e tutta la Comunità capi, nella scheda.
  - **Correzione:** come gli altri dati di BuonaStrada, scegliendo tra i valori di BuonaStrada.
- **Assistenti ecclesiastici**: di gruppo o di unità, può esserlo solo un presbitero.
  - Nel menu delle nomine compaiono solo i capi con la professione «Presbitero».
  - Una nomina senza quella professione viene rifiutata. Gli assistenti già nominati restano.
- **Elenco degli incarichi in PDF, per unità**: prima la Comunità capi, poi le unità L/C, E/G e R/S, ciascuna branca in ordine di codice.
- **La tua foto nel menu**: se nella tua scheda c'è una foto, compare al posto delle iniziali accanto al tuo nome. Senza rete tornano le iniziali.

### Aggiornare

```bash
scripts/aggiorna.sh v1.7.0
```

Una migrazione del database (la professione), applicata da sola all'avvio. `.env` e virtual host non cambiano. La professione si riempie con la prossima importazione da BuonaStrada: fino ad allora l'elenco per nominare un assistente ecclesiastico è vuoto. Se serve prima, correggi la professione dalla scheda del capo. Se aggiorni dalla 1.5.0, leggi anche le note della [1.6.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.6.0): prima va indicato in `.env` il logo del gruppo (`QDC_LOGO`).

## 1.6.1 — 3 novembre 2026

Correzione dell'elenco degli incarichi in PDF.

### Novità

- **Elenco degli incarichi, raggruppato per unità**: ogni incarico sta nella sua sezione. Gli incarichi di un'unità sono nell'unità; quelli di gruppo (capogruppo, assistente ecclesiastico di gruppo, tesoriere di gruppo, amministratore, servizi di supporto) sono in Comunità capi.
  - **Un capo in più sezioni:** compare in ognuna in cui ha un incarico spuntato, anche più volte. Per esempio, un capogruppo che è anche nello staff del reparto è sia nel reparto sia in Comunità capi.
  - **Accanto al nome:** solo gli incarichi di quella sezione.
  - **Capi senza servizio:** chi non ha un incarico di servizio (per esempio un tesoriere) compare anche in Comunità capi, con «Servizio di supporto al gruppo».

### Aggiornare

Dalla 1.5.0 in poi:

```bash
scripts/aggiorna.sh v1.6.1
```

Nessuna migrazione del database; `.env` e virtual host non cambiano. Se aggiorni dalla 1.5.0, leggi anche le note della [1.6.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.6.0): prima di aggiornare va indicato in `.env` il logo del gruppo (`QDC_LOGO`).

## 1.6.0 — 3 novembre 2026

Una sola passkey per entrare e sbloccare l'app, e un'installazione nuova senza riferimenti all'Avellino 1.

### Novità

- **Una sola passkey per dispositivo**: l'impronta o il volto sbloccano l'app con la stessa passkey che fa entrare con «Accedi con passkey».
  - **Niente più passkey di sblocco a parte:** prima comparivano anche all'accesso e davano «Codice errato».
  - **Dove si crea:** in *Password e sicurezza* → *Passkey per entrare*; quella del dispositivo è segnata «sblocca questo dispositivo». Si crea anche spuntando l'impronta quando si sceglie il PIN. Chi ha una password la conferma prima, per sicurezza.
  - **Il segreto che sblocca i dati resta sul dispositivo:** non arriva mai al server, e lo sblocco funziona senza rete.
  - **Rimuovere la passkey:** l'app si sblocca con il PIN, e il browser la toglie dal gestore delle password se lo permette.
  - **Browser che non danno il segreto** (per esempio Chrome installato come app sul Mac): la passkey serve per entrare e i dati si sbloccano con il PIN. Sul Mac l'app suggerisce Safari, con *File → Aggiungi al Dock*.
  - **Vecchie passkey di sblocco:** funzionano finché non crei la passkey del dispositivo, poi vengono tolte. Se all'accesso ne scegli una, l'app spiega cosa fare.
- **Logo**: un'installazione nuova ha il logo AGESCI per le icone dell'app, la barra in alto e le pagine di errore. Il gruppo può mettere il suo (vedi sotto).
- **Esempi nei testi dell'app** generici, senza l'Avellino 1.

### Per chi installa

- **Il logo del gruppo**: metti il file in `resources/` (SVG, oppure PNG quadrato di almeno 512 pixel) e indicalo in `.env` con `QDC_LOGO=resources/…`. Vuota, vale il logo AGESCI. Le icone si ricavano da quel file quando si costruisce l'app.
- L'immagine dell'app si costruisce dalla radice del repository (nuovo `.dockerignore`).
- **Nuova voce in `.env.example`:** `QDC_LOGO`.

### Aggiornare

Prima di aggiornare, **se il gruppo usa già il suo logo**, aggiungi `QDC_LOGO` in `.env` (vedi sotto): altrimenti dopo l'aggiornamento l'app mostra il logo AGESCI. Poi, dalla 1.5.0:

```bash
scripts/aggiorna.sh v1.6.0
```

Lo script mostra la voce nuova di `.env.example` e chiede se proseguire. Da una versione precedente alla 1.5.0 aggiorna a mano (pagina *Aggiornamenti* della guida). Nessuna migrazione del database; i virtual host non cambiano.

### Per l'Avellino 1 (qdc.avellino1.it)

Il logo del gruppo usato finora è nel repository, in `resources/logo-avellino1.png`. Sul server, con l'utente che gestisce l'app:

```bash
cd /srv/qdc            # la cartella dell'installazione
echo 'QDC_LOGO=resources/logo-avellino1.png' >> .env
scripts/aggiorna.sh v1.6.0
```

Se hai già aggiornato senza questa riga, aggiungila e ricostruisci: `docker compose up -d --build`. Per controllare, apri l'app: in alto deve esserci il logo dell'Avellino 1. Telefoni e computer con l'app installata aggiornano l'icona da soli, a volte dopo qualche giorno.

## 1.5.0 — 3 novembre 2026

Servizi di supporto in Comunità capi, sblocco con l'impronta più chiaro e un comando per aggiornare l'app.

### Novità

- **Servizi di supporto** al posto di «a disposizione»: «Servizio di supporto al gruppo» e «Servizio di supporto all'azione educativa» sono incarichi della Comunità capi.
  - **Regole:** ogni capo ne ha uno solo, li nominano i capigruppo e finiscono da soli quando il capo viene assegnato a un'unità.
  - **Chi era «a disposizione»:** l'incarico resta nello storico. In **Incarichi di gruppo** un avviso elenca chi lo ha ancora: assegnandogli uno dei due servizi, «a disposizione» si chiude da solo.
  - **Elenco degli incarichi in PDF:** un capo con soli incarichi aggiuntivi, per esempio tesoriere, compare in Co.Ca. con «Servizio di supporto al gruppo».
  - **Anni di servizio ricostruiti:** si possono indicare anche i due servizi di supporto.
- **Lista d'attesa**: è l'età a decidere chi si contatta. Per un maggiorenne il modulo non chiede più un genitore e non c'è più la casella «Sono io». I maggiorenni già in lista tramite un genitore restano così.
- **Trasferimento del fascicolo** a un altro gruppo: il file porta anche il percorso scout.
  - **Per chi lo riceve:** gli anni nel gruppo di provenienza diventano anni «in un altro gruppo», e i periodi già presenti non si raddoppiano.
  - **Rientro dall'archivio:** tornano gli anni in altri gruppi e quelli ricostruiti.
  - **File vecchi:** quelli delle versioni precedenti si leggono ancora.
- **Sblocco con impronta o volto**:
  - l'app chiede la passkey di questo dispositivo, invece di proporre il telefono con un QR code (da provare con l'app installata con Chrome su Mac);
  - quando l'app cancella i dati, o quando spegni l'impronta, chiede al gestore delle password di togliere la passkey che non serve più, se il browser lo permette;
  - il nome della passkey dice il dispositivo e la data.
- **«Questo dispositivo»** al posto di «questo telefono» nei messaggi sui dati salvati, anche su computer e tablet.

### Per chi installa

- **Servizio di sistema**: `sudo scripts/installa-servizio.sh` installa un servizio systemd. L'app parte all'avvio del server e si gestisce con `systemctl status|restart|stop qdc`, sia con Docker sia con Podman. Con Podman sostituisce `podman-restart.service`.
- **Aggiornamento con un comando**: `scripts/aggiorna.sh` aggiorna all'ultima versione, `scripts/aggiorna.sh vX.Y.Z` a una versione precisa.
  - **Passi:** mette la manutenzione, fa il backup, installa la versione nuova, controlla che l'app risponda e toglie la manutenzione.
  - **Se l'app non risponde:** torna da solo alla versione di prima. Se il database era già cambiato, dice di ripristinare il backup appena fatto.
- **Manutenzione dal server**: nuovo comando `python manage.py manutenzione [attiva|disattiva]`.

### Aggiornare

Prima fai un backup (pagina *Backup* della guida). Poi:

```bash
git fetch --tags
git checkout v1.5.0
docker compose up -d --build
```

Dalla prossima versione basterà `scripts/aggiorna.sh`. Due migrazioni del database, applicate da sole all'avvio. `.env` e virtual host non cambiano. Da una versione prima della 1.2.0 leggi anche le note della [1.2.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.2.0).

## 1.4.0 — 3 novembre 2026

Nuove funzioni per famiglie e capi, e la scheda sanitaria del gruppo al posto di quella AGESCI.

### Novità

- **Installare l'app**: su telefono e computer un banner spiega come installarla (il pulsante «Installa» dove il browser lo offre, le istruzioni su iPhone, iPad, Safari per Mac e Firefox per Android). Chiuso, ricompare dopo 14 giorni.
- **Home**: i gruppi di funzioni si aprono e si chiudono toccando il titolo, uno alla volta, e l'app ricorda l'ultimo aperto. Su un gruppo chiuso compare il numero delle cose da fare. Bacheca e Calendario restano sempre visibili.
- **Calendario**: nuova pagina, nella Home e nel menu sotto Eventi, con il mese o l'elenco dei prossimi eventi propri o dei figli. Per i capi ci sono tre viste: la propria unità, Co.Ca. e unità, tutto il gruppo. Si scarica il file del calendario (`.ics`), di tutti gli eventi o di uno solo dalla sua pagina, e c'è il link per iscriversi al calendario.
- **Percorso scout** nella scheda di ogni socio: i periodi da ragazzo e da capo, uno per riga, e l'anno di ingresso nel gruppo. Gli anni in altri gruppi arrivano dall'importazione da BuonaStrada. I periodi mancanti li aggiungono il capo stesso o un capogruppo. Negli anni di servizio dei capi compare il gruppo.
- **Elenco degli incarichi in PDF**, su carta intestata, per i capigruppo: si scelgono i tipi di incarico e si raggruppa per unità o per incarico. Si stampano gli incarichi di oggi o quelli alla fine di un anno passato.
- **Capi senza servizio**: un capogruppo senza un'unità non viene più segnalato.
- **Cassa comune di due unità collegate**: si uniscono dalla pagina dell'unità e i saldi si sommano. I tesorieri valgono per tutte e due. Si dividono di nuovo solo a inizio anno, prima del primo movimento.
- **Scheda sanitaria del gruppo**:
  - **Contenuti:** anamnesi, allergie in cinque tipi con sì/no, farmaco salvavita, data dell'antitetanica, farmaci da banco, telefono fisso o del lavoro dei genitori.
  - **Al campo:** il farmaco salvavita e l'autorizzazione ai farmaci da banco ci sono anche senza rete.
  - **Stampa:** sul modello del gruppo, con una versione per i maggiorenni. I testi di dichiarazione e consenso si cambiano nelle Impostazioni.
  - **Documenti e scheda firmata:** la famiglia li carica, un capo li verifica e li salva sul Drive del gruppo o sul suo computer. Poi vengono cancellati dal server.
  - **Allergie già inserite:** quelle generiche diventano «alimentari».

### Aggiornare

Prima fai un backup (pagina *Backup* della guida). Poi:

```bash
git fetch --tags
git checkout v1.4.0
docker compose up -d --build
```

Sette migrazioni del database, applicate da sole all'avvio. I virtual host non cambiano. In `.env` c'è una variabile nuova e facoltativa, `QDC_BANNER_INSTALLAZIONE_GIORNI`: è il numero di giorni dopo cui il banner chiuso ricompare (di base 14). Da una versione prima della 1.2.0 leggi anche le note della [1.2.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.2.0).

## 1.3.0 — 2 novembre 2026

Le note emerse installando l'app all'Avellino 1.

### Novità

- **Unità collegate**: il collegamento vale in tutte e due le direzioni e solo a coppie. Per cambiarlo si toglie prima quello esistente; si propongono solo unità attive e non ancora collegate. Per i permessi lo staff delle due unità conta come uno solo, tranne la cassa, che resta di ogni unità. I collegamenti esistenti diventano reciproci da soli; se uno è in conflitto, la pagina dell'unità lo segnala.
- **Ambientazione** (giungla o bosco) solo per il Branco/Cerchio.
- **Squadriglie dei reparti monosessuali**: solo dello stesso sesso del reparto. Una dell'altro sesso già esistente viene segnalata, da correggere o chiudere.
- **Assistenti ecclesiastici**: l'incarico di gruppo, con i poteri di un capogruppo, e quello di unità, che vale come lo staff.
- **Soci e Genitori**: due voci di menu al posto di Persone.
- **Un genitore che diventa capo**: dalla sua scheda un capogruppo gli manda il link per iscriversi in Comunità capi, con i dati che l'app ha già.
- **Importazione da BuonaStrada**: un dato sbagliato (un'email nella colonna del cellulare, un codice fiscale di 17 caratteri) non ferma più l'importazione. Viene lasciato fuori con un avviso.

### Guida di installazione

- Nuova pagina *Controllare l'installazione*: porta, moduli di Apache, pagina di errore, container, risposta in locale e dal dominio, Drive, posta.
- `scripts/configure-prod.sh` controlla che la porta dei container sia libera e propone la prima libera.
- Nuovo comando `manage.py controlla_drive`: verifica l'impostazione del Drive dell'archivio senza scriverci niente.
- Un solo utente gestisce l'app; un solo motore tra Docker e Podman; con un pannello, togliere le direttive di proxy che il pannello mette da sé; invito del primo capogruppo; posta in `.env` prima di `createsuperuser`.

### Aggiornare

Prima fai un backup (pagina *Backup* della guida). Poi:

```bash
git fetch --tags
git checkout v1.3.0
docker compose up -d --build
```

Due migrazioni del database, applicate da sole all'avvio. `.env` e i virtual host non cambiano. Da una versione prima della 1.2.0 leggi anche le note della [1.2.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.2.0).

## 1.2.1 — 2 novembre 2026

Versione di sola documentazione: l'app è la stessa della 1.2.0.

### Guida di installazione

- **Quale progetto Google Cloud usare**: Gmail (pagina *La posta*) e l'archivio sul Drive (pagina *Archivio sul Drive*) possono stare nello stesso progetto, perché l'account di servizio del Drive non usa la schermata di consenso. Resta a parte il progetto dell'accesso con Google.

### Aggiornare

Non serve aggiornare un'installazione già alla 1.2.0. Da una versione precedente segui la [guida di installazione](https://qdc-installazione.readthedocs.io), pagina *Aggiornamenti*, e le note della [1.2.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.2.0) (nuova voce `QDC_CHIAVE_SEGRETI`, email da accendere per gruppo):

```bash
git fetch --tags
git checkout v1.2.1
docker compose up -d --build
```

## 1.2.0 — 2 novembre 2026

### Novità

- **Storico da BuonaStrada**: un export con più anni porta nell'app solo chi c'è nell'ultimo anno, con i periodi passati nelle unità (anno di ingresso nel gruppo, percorso, anni in Co.Ca.). Chi si è appena disiscritto entra **sospeso**, con il suo storico, così lo ritrovi se torna; dopo due anni lo propone l'archiviazione. Le unità che esistevano solo nel passato nascono chiuse.
- **Chi arriva da un altro gruppo** (in BuonaStrada «rinnovo con trasferimento») entra come un nuovo socio, con una nota per i capi.
- **Unità**: un'unità chiusa in cui tutti sono stati archiviati si archivia da *Fine anno e archivio* e torna da sola se rientra qualcuno; un'unità chiusa e vuota, creata per errore, si elimina.
- **Chi riceve le email**: nelle Impostazioni tre interruttori, Capi, Genitori e Ragazzi, spenti all'inizio. Puoi importare e preparare tutto, poi accendere un gruppo alla volta dopo avergli presentato l'app. Codici di accesso, inviti, iscrizione e lista d'attesa partono sempre.
- **Server di posta dalle Impostazioni** (amministratore tecnico): SMTP con la password cifrata, oppure **Gmail con un accesso Google**, senza password; sempre con un'email di prova.

### Correzioni importanti

- L'import da BuonaStrada legge le date di nascita dei genitori senza zeri iniziali e i genitori nati all'estero, come negli export del 2027: prima andavano persi.
- Lo stato I di BuonaStrada non fa più saltare la riga.

### Aggiornare

Segui la [guida di installazione](https://qdc-installazione.readthedocs.io), pagina *Aggiornamenti*: backup, poi

```bash
git fetch --tags
git checkout v1.2.0
docker compose up -d --build
```

Novità per chi installa:

- Nuova voce `QDC_CHIAVE_SEGRETI` in `.env`: cifra password e segreti della posta salvati nelle Impostazioni. Rilancia `scripts/configure-prod.sh` con le stesse opzioni per generarla (le voci che hai già restano), oppure generala tu (`python3 -c 'import secrets; print(secrets.token_hex(32))'`). Conservala con i backup.
- **Dopo l'aggiornamento le email a capi, genitori e ragazzi non partono** finché un capogruppo non accende i loro gruppi in *Impostazioni › Chi riceve le email*. Se l'app è già in uso con tutti, accendili subito.
- Nuova pagina della guida, *La posta*: client OAuth di Google per Gmail e relay SMTP di Google.

## 1.1.0 — 1 novembre 2026

### Novità

- **Manutenzione**: l'amministratore tecnico, dalle Impostazioni, mette l'app in manutenzione con un messaggio. Entrano solo gli amministratori tecnici; tutti gli altri vedono il messaggio, e i dati e le modifiche salvati sul telefono non si perdono.
- **Accessi bloccati**: l'amministratore tecnico vede chi è bloccato per troppe password sbagliate (per account o per indirizzo) e lo sblocca.
- **Pagine di errore** con l'aspetto dell'app e parole semplici, anche quando il server non risponde.
- **Apache con un pannello** (Virtualmin e simili): `configure-prod.sh --proxy apache-vhost` genera solo le direttive da aggiungere al sito creato dal pannello.
- **Backup** anche dei file caricati (moduli firmati, foto, giustificativi), con il ripristino spiegato e provato.

### Correzioni importanti

- Dietro il reverse proxy l'app vedeva per tutti lo stesso indirizzo: bastavano 5 password sbagliate di chiunque per bloccare l'accesso a tutto il gruppo per un'ora. Ora conta l'indirizzo vero di chi si collega, e il registro delle modifiche non accetta più un indirizzo falsificato.
- Dopo una modifica di `.env` e `docker compose up -d`, l'app poteva rispondere con un errore finché non si riavviava il container `app`: ora riparte da solo.
- I log non contengono più l'email digitata all'accesso né il browser.

### Aggiornare

Segui la [guida di installazione](https://qdc-installazione.readthedocs.io), pagina *Aggiornamenti*: backup, poi

```bash
git fetch --tags
git checkout v1.1.0
docker compose up -d --build
```

Da questa versione si installano le versioni rilasciate, non il ramo `main`. Novità per chi installa:

- `scripts/configure-prod.sh` genera `QDC_IMPRONTA_CHIAVE` se manca: se l'avevi già, resta quella.
- Con `nginx-host`, `apache-host` o `apache-vhost` rilancia lo script con le stesse opzioni e rimetti il virtual host o le direttive generati in `deploy/generated/`: contengono la pagina mostrata quando l'app non risponde.
- L'esempio `deploy/cron/qdc.crontab` ha il backup notturno: aggiungi la riga al tuo crontab.

## 1.0.0 — 31 ottobre 2026

Prima release del Quaderno di Caccia, l'app del gruppo AGESCI Avellino 1.

### Cosa c'è

- **Anagrafica e famiglie** da BuonaStrada, con le correzioni da inoltrare alla segreteria, gli inviti, l'iscrizione dall'app e la lista d'attesa.
- **Protezione del telefono**: dati cifrati con PIN o impronta, uso senza rete, revoca a distanza.
- **Scheda sanitaria** con la vista «Al campo» anche offline, il modulo AGESCI da firmare e il registro degli accessi.
- **Eventi e presenze**, anche offline; eventi su BuonaCaccia con liberatorie e schede.
- **Quote e cassa**: pagamenti e ricevute, PayPal e bonifici segnalati dalle famiglie, prima nota e rendiconto Modello D, estratto conto della banca.
- **Progressione Personale** per lupetti e coccinelle, esploratori e guide, rover e scolte; passaggi tra le branche.
- **Fascicolo**: note dei capi, fascicolo dell'anno, servizio e formazione dei capi, fine anno e archivio.
- **Bacheca**, impostazioni del gruppo, modelli delle email, privacy policy e termini.
