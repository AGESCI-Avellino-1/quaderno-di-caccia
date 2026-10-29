# Decisioni da riportare nell'analisi

Bozza per il documento "Analisi requisiti — Decisioni" (artifact originale). Raccoglie
le decisioni prese con il maintainer durante lo sviluppo della fase 1 (28 e 29 ottobre
2026), scritte come quelle dell'analisi. **Non hanno ancora un codice**: si numerano
nel documento originale, nella sezione indicata; poi il codice va citato nel codice
sorgente al posto di "maintainer, 2026-10-2x" e questa bozza si può cancellare.

## Ruoli e permessi

| Decisione | Origine |
| --- | --- |
| Lo **staff dell'unità** si registra come incarico "Staff di unità" (oltre al capo unità), senza limite di persone. I capi restano nella Co.Ca. come appartenenza. | Maintainer 28/10 |
| **Chi nomina**: capo squadriglia e vice li nomina tutto lo staff del reparto; capigruppo e tesoriere di gruppo i capigruppo in carica (l'amministratore tecnico solo al primo avvio o se non ce ne sono); il tesoriere di unità il capo unità e i capigruppo. | Maintainer 28/10 |
| **Squadriglie**: le creano, chiudono e compongono lo staff del reparto e i capigruppo. Una squadriglia alla volta; CSQ e vice ne fanno parte e chiudono l'incarico prima di cambiarla. | Maintainer 28/10 |
| **Dati sanitari**: li scrivono lo staff dell'unità della persona e i capigruppo (per tutte le unità), oltre a genitori e maggiorenni. | Maintainer 28/10 |
| Il **registro delle modifiche** (anche dei dati sanitari) è visibile all'amministratore tecnico, che è sempre un capo o ha la delega dei capigruppo per i dati. | Maintainer 28/10 |
| **Contatti in squadriglia**: ogni squadrigliere vede il solo telefono degli altri; il capo squadriglia vede anche il telefono dei genitori di tutta la squadriglia; il vice vede come uno squadrigliere. Niente email. Il numero mostrato è il cellulare del ragazzo in BuonaStrada se c'è; altrimenti quello di un genitore o tutore scelto per quel figlio; altrimenti quello scelto per tutti i figli senza cellulare; altrimenti nessuno. Il genitore (o il maggiorenne) può nasconderlo agli squadriglieri, non al capo squadriglia. Lo impostano genitore, maggiorenne, staff dell'unità e capigruppo. Copia cifrata sul telefono per le uscite. | Maintainer 29/10 (DEC-13) |

## Squadriglie maschili e femminili

| Decisione | Origine |
| --- | --- |
| Il sesso della squadriglia si controlla all'inserimento; se manca il sesso in BuonaStrada l'inserimento è permesso e la pagina del reparto lo segnala. | Maintainer 28/10 |
| **Eccezioni** (identità di genere, transizioni): le decide la Co.Ca., le registra un capogruppo con la motivazione; le vedono solo i capi e ogni lettura va nel registro degli accessi; valgono finché la persona resta nel reparto. | Maintainer 28/10 |
| La squadriglia è organo di base del reparto: chi esce dal reparto esce dalla squadriglia e dagli incarichi di capo e vice. | Maintainer 28/10 |

## Account e accesso

| Decisione | Origine |
| --- | --- |
| **Ogni account ha la sua email**: un ragazzo non si invita (né si iscrive) con l'email di un genitore. | Maintainer 28/10 (precisa DEC-25) |
| Dai 14 anni l'account si apre con l'invito del capo unità o di un capogruppo, senza approvazione del genitore. | Maintainer 29/10 (DEC-24) |
| Chi si registra da un invito non deve confermare l'email una seconda volta: l'invito è arrivato a quell'indirizzo. | Maintainer 29/10 |
| **Ai 18 anni** l'R/S sceglie per categoria, uguale per tutti i genitori, cosa vedono: contatti e indirizzo; farmaci, allergie e alimentazione; scheda e attività. Finché non sceglie vedono tutto, senza poter modificare. Email all'R/S e a ciascun genitore un mese prima e il giorno del compleanno; se non ha un account la pagina dell'unità lo segnala ai capi. Il collegamento alle quote arriva con la fase 2. | Maintainer 29/10 (DEC-26) |

## Iscrizione dall'app

| Decisione | Origine |
| --- | --- |
| Un nuovo socio si iscrive dall'app con un **codice di iscrizione** (anche come link o QR code): per l'unità, valido fino a una data, oppure personale, valido una volta. Lo creano lo staff dell'unità e i capigruppo; per la Co.Ca. solo i capigruppo. | Maintainer 29/10 |
| Il genitore iscrive il figlio minorenne (il figlio avrà poi un account con un invito); il maggiorenne si iscrive da sé; in Co.Ca. solo maggiorenni. L'account resta "in attesa" finché la richiesta non è accolta. | Maintainer 29/10 |
| La richiesta la accolgono lo staff dell'unità o i capigruppo; per i capi solo i capigruppo. Accolta, il socio ha un **codice socio provvisorio**: 9 seguito da un progressivo, 10 cifre (es. 9000000001). L'importazione da BuonaStrada lo ritrova dal codice fiscale e lo sostituisce con il codice vero: su codice socio e dati vince BuonaStrada. | Maintainer 29/10 |
| Un **capo non ancora in BuonaStrada** vede organizzazione e nomi, ma non i dati delicati degli altri soci. | Maintainer 29/10 |
| All'iscrizione si chiedono nome, cognome, codice fiscale e data di nascita; il resto entro una **scadenza** fissata da chi accoglie: sesso, luogo di nascita, indirizzo, comune, provincia, CAP; per il maggiorenne cellulare ed email; per il minore i genitori, come in BuonaStrada (genitore singolo con affidamento esclusivo oppure entrambi i genitori o tutori), con codice fiscale, cellulare ed email; i consensi (2A, 2B, 2C, riviste) dai moduli firmati. | Maintainer 29/10 |
| Promemoria alla famiglia 7 giorni prima della scadenza; scaduto il termine l'iscrizione è **sospesa**: la famiglia non vede più quel socio finché non completa (un maggiorenne iscritto da sé torna in attesa). Lo staff la vede come sospesa. | Maintainer 29/10 |
| I capigruppo caricano i **moduli vuoti** (informativa, consensi); la famiglia li scarica, li firma a mano e carica le scansioni; un capo dello staff (o un capogruppo) le verifica e riporta i consensi. Le scansioni si conservano finché il socio resta nel gruppo; le vedono i capi, con il registro degli accessi. | Maintainer 29/10 |
| I capigruppo hanno l'elenco delle **iscrizioni da inserire in BuonaStrada**, esportabile in Excel e PDF, e le segnano come inserite. | Maintainer 29/10 |

## Anagrafica e importazione

| Decisione | Origine |
| --- | --- |
| Il **nome dell'unità** lo dà il gruppo (non è in BuonaStrada) e può ripetersi: è obbligatorio tranne per la Co.Ca. Il **codice unità** di BuonaStrada (lettera e progressivo, es. O1; G1 per la Co.Ca.) è univoco e si mostra sempre accanto al nome. Le unità create dall'importazione hanno un nome provvisorio, segnalato finché il gruppo non lo cambia. | Maintainer 29/10 |
| **Correzioni**: contatti e indirizzo li correggono il genitore (suoi e dei figli minorenni), il maggiorenne (i suoi, anche i consensi), lo staff dell'unità e i capigruppo; sesso e luogo di nascita lo staff e i capigruppo; nome, cognome, data di nascita e codice fiscale solo i capigruppo; l'amministratore tecnico corregge tutto. I capigruppo e l'amministratore tecnico vedono l'elenco, le inoltrano alla segreteria e le segnano "inoltrate", oppure le scartano con un motivo (torna il valore di prima). Email riassuntiva ai capigruppo, al massimo una al giorno. La correzione si chiude quando l'importazione la ritrova. | Maintainer 29/10 (DEC-31) |
| **Differenze all'importazione**: chi importa indica la data di aggiornamento dei dati di BuonaStrada; per ogni differenza (dati corretti nell'app, unità assegnate nell'app) sceglie quale dato vince; è proposto il più recente, a parità l'app. Se vince BuonaStrada la correzione si chiude come "superata". | Maintainer 29/10 (DEC-31, DEC-34) |

## Fascicolo e dati sanitari

| Decisione | Origine |
| --- | --- |
| **Esigenze alimentari non mediche** (vegetariano, religiose…) nella scheda, con le stesse regole dei dati sanitari: stesse persone, offline al campo, registro degli accessi. Si scrive cosa non mangia, non il motivo. | Maintainer 29/10 (DEC-49) |
| Il **percorso di formazione dei capi** si inserisce a mano (dal capo o da un capogruppo); da BuonaStrada arriva solo il livello. | Maintainer 29/10 (DEC-47) |

## Privacy

| Decisione | Origine |
| --- | --- |
| La delega dei capigruppo copre l'app. **Diritti degli interessati** gestiti dai capigruppo, che girano le richieste al nazionale: registro delle richieste con scadenza a un mese; fascicolo completo in file (JSON) e pagina stampabile; cancellazione dei dati che esistono solo nell'app, con anonimizzazione di chi non è più socio né genitore di un socio (restano i periodi nelle unità). | Maintainer 29/10 (DEC-98, DEC-102) |
