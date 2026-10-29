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
| 1 | Fondamenta | 🚧 | vedi dettaglio sotto |
| 2 | Quote e cassa | ⏳ | pronto solo il catalogo `backend/data/cataloghi/modello_d_2024_2025.json` |
| 3 | Eventi e presenze | ⏳ | — |
| 4 | Progressione Personale | ⏳ | pronti i cataloghi di specialità/brevetti in `backend/data/cataloghi/`; prima E/G, poi R/S e L/C |
| 5 | Fascicolo completo | ⏳ | anticipati i dati sanitari essenziali (fase 1) |
| 6 | Dopo | ⏳ | bacheca, estratto conto, Carta di clan |
| 7 | App negli store (Capacitor) | 💤 | ultima, dopo la fase 6; DEC-105; prima un prototipo per la regola Apple 4.2 |

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
| Diritti GDPR (accesso, cancellazione) | ⏳ | DEC-102 |
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
dell'analisi), da realizzare:

| Punto | Decisione | Rif. |
| --- | --- | --- |
| Contatti in squadriglia | Ogni squadrigliere vede il solo telefono degli altri squadriglieri. Il CSQ vede anche i contatti dei genitori di tutta la squadriglia; il vice CSQ vede come uno squadrigliere. Numero mostrato: il cellulare del ragazzo in BuonaStrada se c'è (i minorenni non sono obbligati ad averlo, e sotto la branca R/S non si può inserire); altrimenti quello di un genitore o tutore scelto per quel figlio; altrimenti quello scelto per tutti i figli senza cellulare; altrimenti nessuno. Il genitore (o il ragazzo maggiorenne) può nascondere il numero agli squadriglieri; il CSQ lo vede comunque. Numero e visibilità li impostano genitore, maggiorenne, staff dell'unità e capigruppo. Solo telefono, anche per i genitori visti dal CSQ; copia cifrata sul telefono per le uscite | DEC-13 |
| Account dai 14 anni | Invito del capo unità o di un capogruppo, senza approvazione del genitore (come già fatto) | DEC-24 |
| Ai 18 anni | Finché l'R/S non decide, i genitori continuano a vedere quello che vedevano (senza modificarlo). L'R/S sceglie per categoria (contatti e indirizzo; farmaci, allergie e alimentazione; scheda e attività), uguale per tutti i genitori. Email all'R/S e ai genitori un mese prima e il giorno dei 18 anni; se non ha un account, la pagina dell'unità lo segnala ai capi. Il collegamento del genitore alle quote arriva con la fase 2 | DEC-26 |
| Correzioni ai dati di BuonaStrada | Le fanno il genitore (dati suoi e dei figli), il maggiorenne (i suoi), lo staff dell'unità e i capigruppo (ragazzi dell'unità). Contatti e indirizzo tutti; nome, codice fiscale e data di nascita solo i capigruppo. Consensi, stato socio, formazione e nomina: genitore (figli), staff dell'unità (suoi soci), capigruppo; l'amministratore tecnico corregge tutto. I capigruppo vedono l'elenco, inoltrano loro alla segreteria e segnano "inoltrata"; la correzione si chiude quando l'importazione la ritrova in BuonaStrada. Un capogruppo può scartarla con un motivo: torna il valore di prima. Email riassuntiva ai capigruppo, al massimo una al giorno | DEC-31 |
| Differenze tra app e BuonaStrada all'importazione | Chi importa indica la data di aggiornamento dei dati di BuonaStrada; per ogni differenza (dati corretti nell'app, unità assegnate nell'app) sceglie quale dato vince, con proposto il più recente (a parità, BuonaStrada). Se vince BuonaStrada la correzione si chiude come "superata da BuonaStrada" | DEC-31, DEC-34 |
| Percorso di formazione dei capi | Inserito a mano dal capo o da un capogruppo; da BuonaStrada solo il livello | DEC-47 |
| Esigenze alimentari non mediche | Nella scheda personale, trattate come i dati sanitari (anche le religiose, dato particolare GDPR): stesse persone, offline al campo, registro accessi | DEC-49 |
| Delega e diritti GDPR | La delega dei capigruppo copre l'app: si realizzano accesso, rettifica, cancellazione, esportazione, gestite dai capigruppo, che le girano al nazionale | DEC-98, DEC-102 |

## Punti aperti da confermare

| Punto | Riferimento |
| --- | --- |
| Revoca dispositivi e idempotenza solo con sessione browser (servirà per l'app negli store) | DEC-105 |
