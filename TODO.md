# TODO — stato dei lavori

Legenda: ✅ fatto · 🚧 in corso · ⏳ da fare · 💤 rimandato

Dettagli dei requisiti: [analisi dei requisiti](docs/analisi/analisi-requisiti.md)
(sezione "Fasi di sviluppo"). Note tecniche: [CLAUDE.md](CLAUDE.md),
[backend/CLAUDE.md](backend/CLAUDE.md), [frontend/CLAUDE.md](frontend/CLAUDE.md).

## Fasi

La precedenza va alla PWA: ogni fase si completa sulla PWA. L'app per gli store arriva
per ultima, dopo tutte le altre fasi.

| # | Fase | Stato | Note |
| --- | --- | --- | --- |
| 1 | Fondamenta | ✅ | vedi dettaglio sotto; provata nel browser il 29/10/2026, restano alcune verifiche (vedi "Prossimi passi") |
| 2 | Quote e cassa | ⏳ | **la prossima**; pronto il catalogo `backend/data/cataloghi/modello_d_2024_2025.json` |
| 3 | Eventi e presenze | ⏳ | — |
| 4 | Progressione Personale | ⏳ | pronti i cataloghi di specialità/brevetti in `backend/data/cataloghi/`; prima E/G, poi R/S e L/C |
| 5 | Fascicolo completo | ⏳ | anticipati i dati sanitari essenziali (fase 1) |
| 6 | Dopo | ⏳ | bacheca, estratto conto, Carta di clan |
| 7 | App negli store (Capacitor) | 💤 | ultima, dopo la fase 6; DEC-105; prima un prototipo per la regola Apple 4.2 |

## Prossimi passi

### 1. Chiudere la fase 1

| Attività | Chi | Stato |
| --- | --- | --- |
| Confermare le scelte segnate `[da verificare]`: quali campi BuonaStrada sono obbligatori per inserire un socio (oggi: sesso, luogo di nascita, indirizzo, comune, provincia, CAP; cellulare del genitore); promemoria dell'iscrizione 7 giorni prima della scadenza; sospensione dell'intero account (anche per gli altri figli già soci); all'importazione i dati di BuonaStrada vincono su quelli inseriti con l'iscrizione; sesso e luogo di nascita trattati come dati d'identità nelle correzioni; il maggiorenne non corregge i propri consensi; inoltro e scarto delle correzioni solo ai capigruppo (non all'amministratore tecnico) | maintainer | ⏳ |
| Riportare nell'analisi le decisioni del 28 e 29/10 (tabelle sotto), per dar loro un codice DEC | maintainer | ⏳ |
| In produzione, programmare con cron i comandi giornalieri `segnala_correzioni`, `avvisa_maggiore_eta`, `promemoria_iscrizioni` (righe nel README) | chi installa | ⏳ |
| Prove nel browser non ancora fatte: scarto di una correzione, cancellazione per un diritto GDPR, avvisi dei 18 anni, eccezioni sulla squadriglia, sospensione di un'iscrizione, uso senza rete, passkey, Google e Apple | sviluppo | ⏳ |
| Proposta da decidere: avviso nella pagina dell'unità finché ha il nome provvisorio dato dall'importazione | maintainer | ⏳ |

### 2. Fase 2 — Quote e cassa

Ordine proposto: prima quote e pagamenti (servono alle famiglie), poi la prima nota.
Autofinanziamento e budget dei campi dipendono dagli eventi (fase 3); l'estratto conto
bancario è della fase 6 (DEC-93).

| # | Attività | Rif. | Stato |
| --- | --- | --- | --- |
| 2.1 | Tipi di quota: censimento (quota nazionale), quota di gruppo, quota mensile di unità, campi e uscite, eventi esterni; importi per anno associativo | DEC-80 | ⏳ |
| 2.2 | Sconto fratelli automatico, attivabile per tipo di quota, mai sulla quota nazionale | DEC-81, DEC-33 | ⏳ |
| 2.3 | Agevolazioni: la cassa di gruppo copre in tutto o in parte una quota; chi la decide e chi la vede (il tesoriere R/S no) | DEC-82, DEC-11 | ⏳ |
| 2.4 | Pagamenti registrati (contanti, bonifico, altro; link di pagamento), anche offline come registrazioni da accodare | DEC-83, DEC-96 | ⏳ |
| 2.5 | Ricevute PDF non fiscali, numerate per anno associativo, inviate al genitore | DEC-84 | ⏳ |
| 2.6 | Vista del genitore: quote dovute e pagate con sconti e agevolazioni; chi non ha pagato lo vedono solo Co.Ca. e famiglia; il genitore resta collegato alle quote del figlio maggiorenne finché questo non lo scollega | DEC-16, DEC-92, DEC-26 | ⏳ |
| 2.7 | Prima nota per cassa: conto bancario e casse contanti per unità, configurabili; giroconti | DEC-85, DEC-88 | ⏳ |
| 2.8 | Uscite con foto del giustificativo, anche offline; rimborsi ai capi | DEC-86 | ⏳ |
| 2.9 | Categorie del Modello D dal catalogo; quote anticipate su BuonaCaccia in A.2 | DEC-87, DEC-89 | ⏳ |
| 2.10 | Autofinanziamento come evento e budget dei campi (dopo la fase 3) | DEC-90, DEC-91 | 💤 |

### 3. Fasi successive

Eventi e presenze (fase 3), Progressione Personale (fase 4), fascicolo completo con
scheda medica e percorso di formazione dei capi inserito a mano (fase 5, DEC-47), poi la
fase 6 e l'app negli store: vedi la tabella "Fasi".

## Fase 1 — Fondamenta

| Attività | Stato | Riferimento |
| --- | --- | --- |
| Modelli: persone, famiglie, unità, appartenenze, incarichi | ✅ | `apps/anagrafica`, `apps/organizzazione` |
| Permessi (chi vede cosa) | ✅ | `apps/permessi/policy.py` (DEC-09…DEC-20) |
| Importazione da BuonaStrada (comando, API, interfaccia) | ✅ | DEC-27…DEC-35, `apps/importazione` |
| Inviti (API, email, comando `crea_invito`) | ✅ | `apps/accounts` |
| Accesso: password, codice via email, passkey, Google, Apple | ✅ | DEC-21, DEC-22 |
| PWA con dati offline cifrati, PIN e biometria | ✅ | DEC-97 |
| Revoca e scadenza dei dispositivi | ✅ | DEC-23, `apps/dispositivi` |
| Farmaci, allergie, intolleranze + vista "Al campo" offline | ✅ | DEC-55, `apps/sanitaria` |
| Registro degli accessi ai dati sanitari | ✅ | DEC-101 |
| Interfaccia per invitare (scheda persona: persona e genitori, consenso sotto i 14 anni, annullamento) | ✅ | DEC-21, DEC-24, DEC-25, `components/AccountPersona.vue` |
| Gestione di unità, staff, incarichi e squadriglie | ✅ | DEC-10, DEC-11, DEC-14, DEC-18; pagine Unità e Capigruppo; vedi "Decisioni da riportare nell'analisi" |
| Composizione delle squadriglie (chi è in quale squadriglia, spostamenti durante l'anno) | ✅ | DEC-30, DEC-65; pagina dell'unità |
| Squadriglie maschili o femminili, eccezioni decise dalla Co.Ca., uscita dal reparto | ✅ | scheda persona e pagina dell'unità |
| Correzioni ai dati inviate ai capigruppo (scheda persona, pagina Correzioni, email giornaliera, chiusura all'importazione) | ✅ | DEC-31, `apps/anagrafica/servizi.py`, comando `segnala_correzioni` |
| Ai 18 anni: scelta di cosa vedono i genitori, avvisi via email, avviso ai capi se manca l'account | ✅ | DEC-26, `anagrafica.VisibilitaGenitori`, comando `avvisa_maggiore_eta` |
| Diritti GDPR: registro delle richieste, fascicolo completo (JSON e pagina stampabile), cancellazione | ✅ | DEC-102, `apps/diritti` |
| Iscrizione dall'app con codice, link o QR code: richiesta, approvazione, codice socio provvisorio, capo "in attesa" | ✅ | `apps/iscrizioni`: codici, richiesta, approvazione, completamento con scadenza e sospensione, moduli firmati, elenco per BuonaStrada (XLSX/PDF), chiusura all'importazione |
| Contatti in squadriglia (pagina "La mia squadriglia" anche offline, numero del genitore, numero nascosto) | ✅ | DEC-13, `anagrafica/api.py`, `components/TelefonoSquadriglia.vue` |
| Esigenze alimentari non mediche nella scheda e nella vista "Al campo" | ✅ | DEC-49, `sanitaria.InformazioniSanitarie.esigenze_alimentari` |

## Decisioni da riportare nell'analisi

Prese con il maintainer il 28/10/2026, ancora senza codice DEC.

| Chi nomina | Chi può farlo |
| --- | --- |
| Capo squadriglia e vice | Tutto lo staff del reparto |
| Capigruppo e tesoriere di gruppo | I capigruppo in carica; l'amministratore tecnico al primo avvio o se mancano |
| Tesoriere di unità | Il capo unità e i capigruppo |
| Creazione, chiusura e composizione delle squadriglie | Lo staff del reparto e i capigruppo |
| Dati sanitari | Li scrivono lo staff dell'unità e i capigruppo (per tutte le unità) |

| Regola | Decisione |
| --- | --- |
| Squadriglie maschili o femminili | Controllo all'inserimento; se il sesso manca in BuonaStrada l'inserimento è permesso e la pagina del reparto lo segnala |
| Eccezioni (identità di genere, transizioni) | Decide la Co.Ca., registra un capogruppo con la motivazione; le vedono solo i capi, ogni lettura va nel registro accessi; valgono finché la persona resta nel reparto |
| Uscita dal reparto | La squadriglia è organo di base del reparto: chi esce dal reparto esce dalla squadriglia (e dagli incarichi di CSQ e vice) |
| Email degli inviti (precisa DEC-25) | Ogni account ha la sua email: un ragazzo non si invita con l'email di un genitore |
| Registro delle modifiche nell'admin | Accettato: l'amministratore tecnico è sempre un capo o ha la delega dei capigruppo per i dati |

Prese con il maintainer il 29/10/2026 (chiudono i "Punti ancora da verificare"
dell'analisi); tutte realizzate tranne il percorso di formazione dei capi (fase 5):

| Punto | Decisione | Rif. |
| --- | --- | --- |
| Contatti in squadriglia | Ogni squadrigliere vede il solo telefono degli altri squadriglieri. Il CSQ vede anche i contatti dei genitori di tutta la squadriglia; il vice CSQ vede come uno squadrigliere. Numero mostrato: il cellulare del ragazzo in BuonaStrada se c'è (i minorenni non sono obbligati ad averlo, e sotto la branca R/S non si può inserire); altrimenti quello di un genitore o tutore scelto per quel figlio; altrimenti quello scelto per tutti i figli senza cellulare; altrimenti nessuno. Il genitore (o il ragazzo maggiorenne) può nascondere il numero agli squadriglieri; il CSQ lo vede comunque. Numero e visibilità li impostano genitore, maggiorenne, staff dell'unità e capigruppo. Solo telefono, anche per i genitori visti dal CSQ; copia cifrata sul telefono per le uscite | DEC-13 |
| Account dai 14 anni | Invito del capo unità o di un capogruppo, senza approvazione del genitore (come già fatto) | DEC-24 |
| Ai 18 anni | Finché l'R/S non decide, i genitori continuano a vedere quello che vedevano (senza modificarlo). L'R/S sceglie per categoria (contatti e indirizzo; farmaci, allergie e alimentazione; scheda e attività), uguale per tutti i genitori. Email all'R/S e ai genitori un mese prima e il giorno dei 18 anni; se non ha un account, la pagina dell'unità lo segnala ai capi. Il collegamento del genitore alle quote arriva con la fase 2 | DEC-26 |
| Correzioni ai dati di BuonaStrada | Le fanno il genitore (dati suoi e dei figli), il maggiorenne (i suoi), lo staff dell'unità e i capigruppo (ragazzi dell'unità). Contatti e indirizzo tutti; nome, codice fiscale e data di nascita solo i capigruppo. Consensi, stato socio, formazione e nomina: genitore (figli), staff dell'unità (suoi soci), capigruppo; l'amministratore tecnico corregge tutto. I capigruppo vedono l'elenco, inoltrano loro alla segreteria e segnano "inoltrata"; la correzione si chiude quando l'importazione la ritrova in BuonaStrada. Un capogruppo può scartarla con un motivo: torna il valore di prima. Email riassuntiva ai capigruppo, al massimo una al giorno | DEC-31 |
| Iscrizione dall'app | Codice di iscrizione per l'unità (riusabile fino alla scadenza) o personale (una volta), anche come link e QR code. Il genitore iscrive il figlio minorenne; il maggiorenne si iscrive da sé; in Co.Ca. solo maggiorenni. L'account resta "in attesa" finché la richiesta non è accolta: dallo staff dell'unità o dai capigruppo; per i capi solo dai capigruppo. Accolta, il socio ha un codice socio provvisorio 9 + 9 cifre (es. 9000000001) finché l'importazione da BuonaStrada non lo sostituisce (ritrovandolo dal codice fiscale). Un capo non ancora in BuonaStrada vede organizzazione e nomi, non i dati delicati. Dati minimi all'iscrizione, il resto entro una scadenza fissata all'approvazione, poi sospensione; moduli firmati caricati e verificati dallo staff; elenco per i capigruppo esportabile in XLSX e PDF | — |
| Nome e codice delle unità | Il nome lo dà il gruppo (non è in BuonaStrada) e può ripetersi; è obbligatorio, tranne per la Co.Ca. Il codice BuonaStrada (es. O1, G1 per la Co.Ca.) è univoco e si mostra sempre accanto al nome. All'importazione le unità nuove ricevono un nome provvisorio dal tipo, la Co.Ca. nessuno | — |
| Differenze tra app e BuonaStrada all'importazione | Chi importa indica la data di aggiornamento dei dati di BuonaStrada; per ogni differenza (dati corretti nell'app, unità assegnate nell'app) sceglie quale dato vince, con proposto il più recente (a parità, l'app). Se vince BuonaStrada la correzione si chiude come "superata da BuonaStrada" | DEC-31, DEC-34 |
| Percorso di formazione dei capi | Inserito a mano dal capo o da un capogruppo; da BuonaStrada solo il livello | DEC-47 |
| Esigenze alimentari non mediche | Nella scheda personale, trattate come i dati sanitari (anche le religiose, dato particolare GDPR): stesse persone, offline al campo, registro accessi | DEC-49 |
| Delega e diritti GDPR | La delega dei capigruppo copre l'app: si realizzano accesso, rettifica, cancellazione, esportazione, gestite dai capigruppo, che le girano al nazionale. Fascicolo e cancellazione solo dai capigruppo; fascicolo in JSON e pagina leggibile; la cancellazione toglie i dati che esistono solo nell'app e rende anonimo chi non è più socio (né genitore di un socio), tenendo i periodi nelle unità; registro delle richieste con scadenza a un mese | DEC-98, DEC-102 |

## Punti aperti da confermare

| Punto | Riferimento |
| --- | --- |
| Revoca dispositivi e idempotenza solo con sessione browser (servirà per l'app negli store) | DEC-105 |
