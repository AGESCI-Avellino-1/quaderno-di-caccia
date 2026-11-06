# Novità del Quaderno di Caccia

Le novità di ogni versione, dalla più recente. `scripts/aggiorna.sh` mostra le sezioni tra la
versione installata e quella nuova prima di chiedere se aggiornare. Il dettaglio di ogni
versione, con il manuale in PDF, è nella pagina
[Releases](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases).

## 1.21.0 — 6 novembre 2026

### Novità

**Notifica di prova** ([#39](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/39)): in **Impostazioni › Server di posta**, gli amministratori tecnici trovano **Manda una notifica di prova a me**. Parte subito verso i propri dispositivi con le notifiche attive, anche se qualche tipo di notifica è spento, e per ognuno dice se il servizio di notifiche l'ha accettata o il codice di errore. Serve a capire se un problema è nell'invio o sul dispositivo.

### Aggiornare

```bash
scripts/aggiorna.sh v1.21.0
```

Nessuna migrazione del database.

### Documentazione

Il capitolo sull'amministratore tecnico del manuale spiega il nuovo pulsante.

Provata con i test: l'invio vero al servizio di notifiche non è ancora provato col nuovo pulsante, e si può fare solo da un server in produzione. Se qualcosa non va, segnalalo con una issue.

## 1.20.1 — 6 novembre 2026

### Novità

**Nome del PDF dei verbali** ([#38](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/38)): il PDF di un verbale ora ha il titolo della riunione e la data, per esempio `Comunità capi-22112026.pdf`, invece di un numero. I verbali separati hanno un nome fisso con la data: `verbale_legale_rappresentante-22112026.pdf` per la nomina del legale rappresentante e il cambio di sede legale, `verbale_bilancio-22112026.pdf` per l'approvazione del bilancio. Lo ZIP con gli allegati non cambia.

### Aggiornare

```bash
scripts/aggiorna.sh v1.20.1
```

Nessuna migrazione del database.

Provata con i test: non ancora scaricando un PDF su un telefono o dall'app installata. Se qualcosa non va, segnalalo con una issue.

## 1.20.0 — 6 novembre 2026

### Novità

**Dati della riunione e del gruppo nei verbali** ([#36](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/36)): sopra il testo dei verbali scritti a mano ci sono dei pulsanti per inserire **[Data]**, **[Ora di inizio]**, **[Ora di fine]**, **[Denominazione gruppo]**, **[Codice fiscale gruppo]**, **[Partita IVA gruppo]**, **[Indirizzo completo]**, **[Indirizzo]** e **[Luogo]**, cioè solo la città. Chi scrive li vede tra parentesi quadre, chi legge la bozza vede il valore. Quando il verbale diventa definitivo il valore si copia nel testo e non cambia più, anche se poi la riunione cambia. I verbali già definitivi e i testi generati dal modello dell'assemblea restano come sono.

**Anteprima del verbale** ([#36](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/36)): il tasto **Anteprima** apre una finestra con il testo come risulterà, compreso quello non ancora salvato, e dice quali dati mancano. Lo dice anche la conferma di **Rendi definitivo**. Un dato che manca sparisce dal testo. La città si riconosce solo dopo il CAP nell'indirizzo: se non c'è, la scrivi a mano.

**Partita IVA del gruppo** ([#36](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/36)): si scrive nelle **Impostazioni**, in **Intestazione delle stampe**. È facoltativa e la cambiano i capigruppo; l'importazione da BuonaStrada non la tocca.

**File nell'app installata su un Mac** ([#37](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/37)): nell'app installata da Safari sul Mac i file si scaricano di nuovo come nel browser, invece di aprire un foglio di condivisione senza un modo per salvarli. Su iPhone e iPad non cambia nulla.

### Aggiornare

```bash
scripts/aggiorna.sh v1.20.0
```

Una migrazione del database, applicata da sola all'avvio: aggiunge il campo della partita IVA.

### Documentazione

Il manuale spiega i dati da inserire nei verbali e l'anteprima, con una nuova schermata. Dalle stesse pagine nasce anche un manuale senza gli indirizzi e il logo di Avellino 1 nel testo e nel sito, solo online ([#35](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/35)): le schermate restano le stesse, con quel logo.

Provata con i test e, per l'anteprima dei verbali, in un browser automatico. Il download sul Mac e la scrittura del verbale su un iPhone non sono ancora provati sui dispositivi veri. Se qualcosa non va, segnalalo con una issue.

## 1.19.1 — 6 novembre 2026

### Novità

**La barra non finisce più fuori schermo su iPhone** ([#34](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/34)): con l'app installata, dopo aver usato la tastiera o la fotocamera, barra e percorso di pagina potevano restare sopra il bordo dello schermo, e si usciva solo riavviando l'app. Ora la pagina resta sulla parte di schermo che il telefono mostra davvero, in tutte le pagine.

**Foto dello scontrino in Le mie spese** ([#34](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/34)): dopo aver registrato una spesa il campo della foto si svuota. Prima continuava a mostrare il file appena usato, e la spesa successiva poteva partire senza scontrino anche se il nome si vedeva: se hai registrato più spese di seguito, controlla che abbiano il link **Giustificativo**.

### Aggiornare

```bash
scripts/aggiorna.sh v1.19.1
```

Nessuna migrazione del database.

### Documentazione

La guida di installazione segue i menu attuali di Google Cloud per l'accesso con Google ([#33](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/33)).

Provata con i test e, solo per l'aspetto delle pagine, su un iPhone simulato con iOS 27: la correzione della barra non è ancora provata con la tastiera e la fotocamera su un telefono vero. Se qualcosa non va, segnalalo con una issue.

## 1.19.0 — 6 novembre 2026

### Novità

**Versione dell'app nel piè di pagina** ([#32](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/32)): nei titoli e nella riga del piè di pagina delle **Impostazioni** si può scrivere **[Release]**, che mostra la versione dell'app aperta su quel telefono o computer, per esempio v1.19.0. Serve quando qualcuno segnala un errore: si vede subito se sta usando l'ultima versione. Un telefono che non ha ancora accettato l'aggiornamento mostra il numero vecchio.

Il segnaposto è facoltativo: se il gruppo non lo scrive non cambia nulla. La riga del piè di pagina si vede anche prima dell'accesso, quindi chi lo usa lì mostra la versione anche a chi non ha un account. Nelle pagine di privacy e termini non vale.

### Aggiornare

```bash
scripts/aggiorna.sh v1.19.0
```

Nessuna migrazione del database. Per vedere la versione, scrivi per esempio `Versione [Release]` nella riga del piè di pagina.

### Documentazione

Il capitolo sulle impostazioni del manuale spiega il nuovo segnaposto.

Provata con i test e in Chromium sulla build di produzione, prima dell'accesso: non ancora su un telefono né durante un aggiornamento dell'app. Se qualcosa non va, segnalalo con una issue.

## 1.18.1 — 5 novembre 2026

### Novità

**Regolamento nella convocazione dell'assemblea** ([#30](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/30)): in una nuova assemblea dei soci il punto **Regolamento dell'Assemblea** parte non spuntato, perché si tratta solo se ci sono modifiche. Gli altri quattro punti restano spuntati e, se serve, il Regolamento si spunta a mano.

### Aggiornare

```bash
scripts/aggiorna.sh v1.18.1
```

Nessuna migrazione del database. Le assemblee con la convocazione già salvata restano come sono.

### Documentazione

Il manuale dell'assemblea descrive la nuova proposta, con la schermata aggiornata.

Provata con i test e in Chromium, aprendo la convocazione di una nuova assemblea. Se qualcosa non va, segnalalo con una issue.

## 1.18.0 — 5 novembre 2026

### Novità

**Nome e numero civico delle località** ([#29](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/29)):

- Oltre al **Nome** che la identifica nell'elenco (per esempio «Sede»), una località può avere un **Nome completo** (per esempio quello della parrocchia che la ospita). Se c'è, è quello che leggono gli invitati nella pagina della riunione, nelle email e nel calendario, e la convocazione dell'assemblea lo propone nel campo «presso».
- Il **Numero civico** ha un campo suo. Scegliendo una proposta il numero scritto resta, a meno che la proposta non ne abbia uno suo: spesso il servizio di ricerca ha solo la via. Il numero compare dopo la via, anche nel link **mappa**.

### Aggiornare

```bash
scripts/aggiorna.sh v1.18.0
```

Una migrazione del database, applicata da sola all'avvio. Dopo l'aggiornamento:

- le località già salvate restano come sono: per aggiungere nome completo e civico, aprile da **Impostazioni**. Salvando, le riunioni future mostrano il nuovo nome; quelle passate no.

Provata con i test e in Chromium, con Photon vero, creando una località nuova con il suo nome e il civico: non ancora la modifica di una località già salvata né le email su un server vero. Se qualcosa non va, segnalalo con una issue.

## 1.17.0 — 5 novembre 2026

### Novità

**Ordine del giorno delle riunioni** ([#26](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/26)): le riunioni della Comunità capi e dei genitori hanno il loro ordine del giorno.

- Si scrive creando la riunione, se è una sola; per quelle di ogni settimana, sulla singola riunione. Lo scrive chi gestisce la riunione e lo legge chi la vede; per la Comunità capi solo i capi. Serve la rete: non resta salvato sul telefono.
- Nel verbale c'è già `[Ordine del giorno]`, che si può togliere o spostare. Quando il verbale diventa definitivo, al suo posto si copia il testo, che non cambia più.
- L'email di convocazione lo riporta, se c'è. Se cambia dopo l'invio non parte un'altra email.
- Nell'assemblea dei soci i cinque punti del modello sono già tutti spuntati: si tolgono quelli che non servono. L'email di convocazione ora li riporta.

**Indirizzi delle località** ([#27](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/27)): mentre scrivi l'indirizzo di una località, l'app propone quelli trovati su OpenStreetMap, con il servizio gratuito Photon. Si può sempre scrivere a mano; le risposte arrivano in qualche secondo e senza risposta le proposte non compaiono. Il link **mappa** della riunione ora c'è anche per le località che hanno solo l'indirizzo.

**Azienda nei contatti** ([#28](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/28)): il file per la rubrica del telefono riporta come azienda il gruppo e chi è la persona: per esempio «AGESCI Avellino 1 - Reparto Antares», oppure «Capo», «Genitore», «Socio». Gruppo e unità restano nella rubrica del telefono, fuori dalla protezione con il PIN, anche per i minorenni.

### Aggiornare

```bash
scripts/aggiorna.sh v1.17.0
```

Una migrazione del database, applicata da sola all'avvio. Dopo l'aggiornamento:

- se avete personalizzato l'email **Convocazione di una riunione**, l'app userà il testo standard finché non aggiungete `[Ordine del giorno]` nel vostro: i capigruppo ricevono un avviso, una sola volta;
- se avete salvato una vostra privacy policy, aggiungete a mano che gli indirizzi di sedi e basi cercati passano dal servizio Photon: la frase nuova è solo nel testo standard;
- per non usare il servizio pubblico, o per usarne uno vostro, c'è `QDC_PHOTON_URL` in `.env`: vuota, niente proposte;
- le assemblee mai compilate partono con tutti i punti spuntati; quelle con dati salvati restano come sono.

Provata con i test e in Chromium, con Photon vero: non ancora il file dei contatti su un telefono, l'email di convocazione su un server di posta vero né le proposte sulle località del vostro gruppo. Se qualcosa non va, segnalalo con una issue.

## 1.16.0 — 5 novembre 2026

### Novità

**Criteri di ammissione dell'anno** ([#25](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/25)): i requisiti e i criteri che la Comunità capi delibera ogni anno, sulla carta intestata del gruppo.

- I capigruppo li compilano da **Download**, partendo da un testo di esempio modificabile, con il riferimento al verbale e i numeri massimi per unità.
- Chiunque li scarica in Download e, anche senza account, quando mette qualcuno in lista d'attesa. Se quelli dell'anno mancano, si vedono gli ultimi, con l'avviso che sono solo una traccia.
- Se cambiano durante l'anno si crea una nuova versione, con la data da cui vale. Le altre restano visibili, ognuna con il suo periodo.
- I numeri massimi non bloccano nulla: chi decide una richiesta vede quanti ragazzi ha l'unità e, se è già al massimo, un avviso. I numeri compaiono anche nella lista d'attesa dei capi.
- Le richieste di iscrizione in attesa mostrano i giorni che restano per rispondere: sessanta dalla richiesta, come chiede lo Statuto. Dieci giorni prima del termine chi decide riceve un'email.

### Aggiornare

```bash
scripts/aggiorna.sh v1.16.0
```

Due migrazioni del database, applicate da sole all'avvio. Dopo l'aggiornamento:

- il testo di esempio dei criteri va verificato con lo Statuto e il Regolamento e adattato alle decisioni della Comunità capi: il documento è pubblico, senza nomi né dati di persone;
- le richieste già in attesa da più di cinquanta giorni fanno partire subito un'email a chi decide, una sola volta per richiesta; quelle oltre i sessanta giorni risultano con il termine superato;
- finché mancano i criteri dell'anno, il primo di ogni mese i capigruppo ricevono un promemoria.

## 1.15.0 — 5 novembre 2026

### Novità

**Animali di squadriglia** ([#22](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/22)): un elenco unico per il gruppo, con 93 animali già pronti, generali e nautici: immagine, colori con i loro significati per il guidoncino e richiamo.

- Una squadriglia nuova si crea scegliendo l'animale: il suo nome è il plurale («Sq. Pantere»), non si scrive più a mano.
- L'immagine compare accanto al nome nell'unità, in «La mia squadriglia», negli eventi, nelle riunioni e nelle imprese, anche ai genitori. Senza rete restano quelle degli animali usati dalle squadriglie.
- L'elenco lo leggono ragazzi e staff dei reparti e i capigruppo; lo modificano gli staff dei reparti e i capigruppo. Una modifica vale ovunque. Un animale scelto da una squadriglia, anche chiusa, si disattiva e non si cancella.
- Per un animale nuovo si carica un'immagine SVG, PNG o JPEG. Un SVG viene ripulito e resta solo il disegno; se contiene collegamenti esterni viene rifiutato.

**Scheda incarichi** ([#23](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/23)): dall'organigramma, tutti i capi la leggono e i capigruppo definiscono nuovi incarichi per i capi, di gruppo o di unità, aggiuntivi o di servizio, educativi o no. Li assegnano solo i capigruppo e **non danno nessun permesso**: anche un servizio di unità non fa entrare il capo nello staff. Compaiono nell'organigramma, nel suo PDF e nel fascicolo del capo. Quelli già assegnati si disattivano e non si cancellano.

### Aggiornare

```bash
scripts/aggiorna.sh v1.15.0
```

Tre migrazioni del database, applicate da sole all'avvio: caricano i 93 animali e collegano le squadriglie il cui nome coincide con uno di loro, al singolare o al plurale, dando loro il plurale. Dopo l'aggiornamento:

- nella pagina di ogni reparto, **Da controllare** segnala le squadriglie con un nome diverso: lo staff o un capogruppo sceglie l'animale sotto il nome, e la squadriglia ne prende il plurale;
- c'è una dipendenza nuova, `py_svg_hush`, installata da sola con l'immagine del server.

## 1.14.0 — 4 novembre 2026

### Novità

**Modelli AGESCI per l'assemblea e la Comunità capi** ([#20](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/20)): convocazione e verbale dell'assemblea si compilano dai dati e il testo lo scrive l'app, sulla carta intestata del gruppo.

- La convocazione ha l'ordine del giorno a scelta, la prima convocazione di base alle 00:00 del giorno e la seconda all'orario della riunione; l'anno del bilancio e quello di elezione e quota si scelgono a parte.
- Il verbale chiede ore, scrutatori, voti (favorevoli e contrari, oppure unanimità), risultato di bilancio a mano e quote: se manca qualcosa non diventa definitivo. I verbali già scritti restano come sono.
- A richiesta, il verbale separato di approvazione del bilancio, con gli stessi dati.
- Nelle riunioni di Comunità capi, quando serve, il verbale su Capi Gruppo, rappresentante legale e sede, con le sole parti cambiate.

**Download** ([#19](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/19)): una nuova voce con i documenti caricati dai capi (PDF, Word, Excel, PowerPoint, fino a 20 MB), per la Comunità capi, per le unità e per i genitori. Alla scadenza il documento si cancella anche dal server, dopo un avviso una settimana prima.

**Progetto Educativo di Gruppo** ([#18](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/18)): lo caricano i capigruppo, soci e genitori vedono tutte le versioni in Download, chiunque vede quella in vigore all'indirizzo `/peg`, collegato dalla pagina di accesso e aperto ai motori di ricerca.

**Progetto del capo** ([#17](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/17)): nel fascicolo del capo, come testo o PDF, con le versioni. Lo scrive solo il capo, lo legge la Comunità capi; il PDF si legge dentro la pagina.

**Notifiche sul telefono** ([#21](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/21)): su riunioni ed eventi, scadenze di quote e BuonaCaccia, bacheca e documenti, avvisi per i capi. Per ogni tipo si sceglie email, notifica o entrambe, in Privacy e preferenze. Su iPhone servono l'app sulla schermata Home e il permesso. Il testo non contiene mai nomi di persone, importi o dati sanitari.

**Calendario** ([#16](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/16)): per i capi la nuova vista **Tutti i miei eventi** è quella predefinita. Le altre viste ora contano anche gli assistenti ecclesiastici di unità e le unità collegate.

### Aggiornare

```bash
scripts/aggiorna.sh v1.14.0
```

Sette migrazioni del database, applicate da sole all'avvio. Dopo l'aggiornamento:

- aggiungi al crontab il lavoro `pulisci_documenti` (la riga è in `deploy/cron/qdc.crontab`), altrimenti i documenti scaduti spariscono dalla vista ma non dal server;
- le notifiche non si configurano, ma servono `QDC_CHIAVE_SEGRETI` in `.env` e che il server raggiunga i servizi di Apple, Google, Mozilla e Microsoft; le invia il servizio `posta`;
- se il gruppo ha personalizzato l'informativa privacy, aggiungi il paragrafo sulle notifiche: è cambiato solo il testo predefinito;
- la prima volta che apri il calendario, la vista ricordata dal browser riparte da **Tutti i miei eventi**.

Le notifiche non sono ancora state provate su telefoni veri: se non arrivano, segnalalo con una issue.

## 1.13.1 — 4 novembre 2026

### Novità

**Schermata di avvio**: nell'app installata si vedeva solo per un istante ([#15](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/15)). Ora resta per almeno due secondi dall'apertura, mentre l'app si carica sotto; nel browser sparisce appena l'app è pronta, come prima.

### Aggiornare

```bash
scripts/aggiorna.sh v1.13.1
```

Nessuna migrazione del database. In `.env` non devi cambiare nulla: per una durata diversa scrivi i secondi in `QDC_DURATA_AVVIO` (vuota: 2; `0`: non aspetta), prima di aggiornare.

## 1.13.0 — 4 novembre 2026

### Novità

**Verbali delle riunioni**: le riunioni di Comunità capi, dei genitori, di squadriglia, di Alta Squadriglia, di Consiglio Capi e di Con.Ca.Vi. e l'assemblea dei soci hanno un verbale, nella pagina della riunione.

- Si scrive con l'editor di testo, in bozza; chi ha la responsabilità della riunione può affidarlo a un'altra persona, poi lo rende definitivo o lo riapre indicando il motivo.
- Da definitivo si scarica in PDF su carta intestata, con lo spazio per le firme dove serve, e in uno ZIP con gli allegati.
- Gli allegati (PDF, immagini, Word, Excel, PowerPoint, audio e video) stanno sul Drive del gruppo, fino a 2 GB per file; senza Drive sul server, fino a 20 MB.
- Si scrive e si legge solo con la rete: il verbale non resta sul telefono.
- Per Comunità capi, riunioni dei genitori e assemblea arriva un promemoria se il verbale non è definitivo una settimana dopo.

**Riunioni dei genitori**: di una o più unità o di tutto il gruppo. Si aggiungono i documenti, poi si invia la convocazione con un'email agli invitati. Le presenze le segna lo staff. Un rover o una scolta maggiorenne può scegliere di partecipare al posto dei genitori.

**Assemblea dei soci**: la convocano i capigruppo per tutto il gruppo. Nel verbale ci sono presidente, segretari e l'elenco dei presenti con il diritto di voto; le votazioni si fanno fuori dall'app.

**Incarichi di squadriglia**: cassiere, cicala, cronista, guardiano dell'angolo, dello stile e del tempo, infermiere, liturgista, magazziniere e aiuto, mercurio. Li assegnano il capo squadriglia e lo staff del reparto; non danno permessi nell'app.

**Schermata di avvio**: all'apertura l'app mostra una pagina di quaderno con l'etichetta, il logo e il nome del gruppo.

### Aggiornare

Prima di aggiornare, in `.env` scrivi il nome del gruppo per la schermata di avvio (vuoto: solo il nome dell'app):

```bash
QDC_NOME_AVVIO=AGESCI Gruppo Avellino 1
```

Poi:

```bash
scripts/aggiorna.sh v1.13.0
```

Otto migrazioni del database, applicate da sole all'avvio. Dopo l'aggiornamento:

- aggiungi al crontab il lavoro `promemoria_verbali` (la riga è in `deploy/cron/qdc.crontab`);
- la convocazione delle riunioni dei genitori e dell'assemblea, e i nuovi documenti, partono **sempre**, anche con le email ai genitori spente nelle impostazioni;
- il server web ora lavora a thread (`--threads 4`), per poter scaricare file grandi;
- se usi il Drive, nella cartella dell'archivio l'app crea da sola `Verbali`: chi gestisce il Drive condiviso può vedere quei file;
- su un iPhone dove l'app era già installata, la nuova schermata di avvio può comparire solo reinstallandola sulla schermata Home.

## 1.12.1 — 4 novembre 2026

### Correzioni

**File sull'iPhone**: con l'app installata su iPhone, un PDF si apriva a tutto schermo senza modo di tornare all'app, di condividerlo o di salvarlo. Ora il file resta nell'app: si apre una finestra con «Condividi o salva», da cui si invia o si salva su File, e «Chiudi». Su Android, sul computer e nel browser non cambia nulla.

### Aggiornare

```bash
scripts/aggiorna.sh v1.12.1
```

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
