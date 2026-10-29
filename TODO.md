# TODO — stato dei lavori

Legenda: ✅ fatto · 🚧 in corso · ⏳ da fare · 💤 rimandato

Dettagli dei requisiti: [analisi dei requisiti](docs/analisi/analisi-requisiti.md)
(sezione "Fasi di sviluppo"). Note tecniche: [CLAUDE.md](CLAUDE.md),
[backend/CLAUDE.md](backend/CLAUDE.md), [frontend/CLAUDE.md](frontend/CLAUDE.md).

## Fasi

La precedenza va alla PWA: ogni fase si completa sulla PWA. L'app per gli store è in
standby: si valuterà più avanti se realizzarla (maintainer, 29/10/2026).

| # | Fase | Stato | Note |
| --- | --- | --- | --- |
| 1 | Fondamenta | ✅ | vedi dettaglio sotto; provata nel browser il 29/10/2026; restano le attività del maintainer in "Prossimi passi" |
| 2 | Quote e cassa | ✅ | quote, pagamenti, ricevute, prima nota e rendiconto; restano per la fase 3 autofinanziamento, budget dei campi e quote BuonaCaccia |
| 3 | Eventi e presenze | ⏳ | — |
| 4 | Progressione Personale | ⏳ | pronti i cataloghi di specialità/brevetti in `backend/data/cataloghi/`; prima E/G, poi R/S e L/C |
| 5 | Fascicolo completo | ⏳ | anticipati i dati sanitari essenziali (fase 1) |
| 6 | Dopo | ⏳ | bacheca, estratto conto (importazione dei movimenti della banca e abbinamento a quote e versamenti: note sul formato in [docs/analisi/estratto-conto-banca.md](docs/analisi/estratto-conto-banca.md)), Carta di clan |
| 7 | App negli store (Capacitor) | 💤 | in standby: si valuterà se realizzarla; DEC-105; prima un prototipo per la regola Apple 4.2 |
| 8 | Realizzazione documentazione di uso | ⏳ | installazione (per i gruppi che installano la propria copia) e uso per l'Avellino 1, sulla PWA (senza app negli store); l'analisi si fa quando ci si arriva |

## Prossimi passi

### 1. Chiudere la fase 1

| Attività | Chi | Stato |
| --- | --- | --- |
| Confermare le scelte segnate `[da verificare]` (29/10): dati obbligatori per BuonaStrada, promemoria, sospensione, chi corregge cosa (ora DEC-124, DEC-125, DEC-129, DEC-130) | maintainer | ✅ applicate |
| Riportare nell'analisi le decisioni del 28 e 29/10 (DEC-110…DEC-136) | sviluppo | ✅ 29/10 |
| In produzione, programmare i comandi giornalieri: esempio pronto in [deploy/cron/qdc.crontab](deploy/cron/qdc.crontab) | chi installa | ⏳ |
| Avviso nella pagina dell'unità finché non ha un nome (le unità importate nascono senza); unità mostrate come "Tipo Nome (Codice)" | sviluppo | ✅ |
| Prove nel browser: scarto di una correzione, cancellazione per un diritto GDPR, avvisi dei 18 anni, eccezioni sulla squadriglia, sospensione di un'iscrizione, uso senza server (copia cifrata) | sviluppo | ✅ 29/10 |
| Prove che servono un telefono o account esterni veri: passkey e impronta, accesso con Google e Apple | maintainer | ⏳ |

### 2. Fase 2 — Quote e cassa

Ordine proposto: prima quote e pagamenti (servono alle famiglie), poi la prima nota.
Autofinanziamento e budget dei campi dipendono dagli eventi (fase 3); l'estratto conto
bancario è della fase 6 (DEC-93).

| # | Attività | Rif. | Stato |
| --- | --- | --- | --- |
| 2.1 | Tipi di quota: censimento (quota nazionale), quota di gruppo, quota mensile di unità (una quota per mese); importi per anno associativo; li fissa solo il gruppo; campi, uscite ed eventi esterni con la fase 3 | DEC-80 | ✅ |
| 2.2 | Sconto famiglia automatico: importo fisso per tipo di quota, su ogni socio quando il nucleo (fratelli, genitori e figli, coniugi) ha almeno due soci; mai sulla quota nazionale | DEC-81, DEC-33 | ✅ |
| 2.3 | Agevolazioni: la cassa di gruppo copre in tutto o in parte una quota; chi la decide e chi la vede (il tesoriere R/S no) | DEC-82, DEC-11 | ✅ |
| 2.4 | Pagamenti registrati (contanti, bonifico, altro; link di pagamento), anche offline come registrazioni da accodare | DEC-83, DEC-96 | ✅ |
| 2.5 | Ricevute PDF non fiscali, numerate per anno associativo, inviate al genitore | DEC-84 | ✅ |
| 2.6 | Vista del genitore: quote dovute e pagate con sconti e agevolazioni; chi non ha pagato lo vedono solo Co.Ca. e famiglia; il genitore resta collegato alle quote del figlio maggiorenne finché questo non lo scollega | DEC-16, DEC-92, DEC-26 | ✅ |
| 2.7 | Prima nota per cassa: conto bancario e casse contanti per unità, configurabili; giroconti | DEC-85, DEC-88 | ✅ |
| 2.8 | Uscite con foto del giustificativo, anche offline; rimborsi ai capi | DEC-86 | ✅ |
| 2.9 | Categorie del Modello D dal catalogo, rendiconto con i totali da ricopiare; le quote anticipate su BuonaCaccia (A.2) arrivano con gli eventi esterni della fase 3 | DEC-87, DEC-89 | ✅ |
| 2.10 | Autofinanziamento come evento e budget dei campi (dopo la fase 3) | DEC-90, DEC-91 | 💤 |

### 3. Fasi successive

Eventi e presenze (fase 3), Progressione Personale (fase 4), fascicolo completo con
scheda medica e percorso di formazione dei capi inserito a mano (fase 5, DEC-47), poi la
fase 6 e l'app negli store: vedi la tabella "Fasi".

Per la fase 3 (maintainer, 29/10/2026, da riportare nell'analisi): le quote di campi e
uscite, rimandate dalla fase 2, arrivano con gli eventi. La quota del campo estivo (E/G)
e delle Vacanze di Branco/Cerchio (L/C) si può configurare "a rate", con passi a
scadenze fissate: di solito due rate a date stabilite più il saldo prima della
partenza. Ogni rata sarà una quota con la sua scadenza, e i pagamenti con acconti e la
ripartizione su più quote della fase 2 valgono anche per le rate.

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
| Gestione di unità, staff, incarichi e squadriglie | ✅ | DEC-10, DEC-11, DEC-14, DEC-18; pagine Unità e Capigruppo; DEC-110…DEC-112 |
| Composizione delle squadriglie (chi è in quale squadriglia, spostamenti durante l'anno) | ✅ | DEC-30, DEC-65; pagina dell'unità |
| Squadriglie maschili o femminili, eccezioni decise dalla Co.Ca., uscita dal reparto | ✅ | scheda persona e pagina dell'unità |
| Correzioni ai dati inviate ai capigruppo (scheda persona, pagina Correzioni, email giornaliera, chiusura all'importazione) | ✅ | DEC-31, `apps/anagrafica/servizi.py`, comando `segnala_correzioni` |
| Ai 18 anni: scelta di cosa vedono i genitori, avvisi via email, avviso ai capi se manca l'account | ✅ | DEC-26, `anagrafica.VisibilitaGenitori`, comando `avvisa_maggiore_eta` |
| Diritti GDPR: registro delle richieste, fascicolo completo (JSON e pagina stampabile), cancellazione | ✅ | DEC-102, `apps/diritti` |
| Iscrizione dall'app con codice, link o QR code: richiesta, approvazione, codice socio provvisorio, capo "in attesa" | ✅ | `apps/iscrizioni`: codici, richiesta, approvazione, completamento con scadenza e sospensione, moduli firmati, elenco per BuonaStrada (XLSX/PDF), chiusura all'importazione |
| Contatti in squadriglia (pagina "La mia squadriglia" anche offline, numero del genitore, numero nascosto) | ✅ | DEC-13, `anagrafica/api.py`, `components/TelefonoSquadriglia.vue` |
| Esigenze alimentari non mediche nella scheda e nella vista "Al campo" | ✅ | DEC-49, `sanitaria.InformazioniSanitarie.esigenze_alimentari` |

## Decisioni prese durante la fase 1

Le decisioni prese con il maintainer il 28 e 29/10/2026 sono nell'analisi come
DEC-110…DEC-136 ([docs/analisi/analisi-requisiti.md](docs/analisi/analisi-requisiti.md)):
ruoli e squadriglie DEC-110…DEC-115 e DEC-131…DEC-133, account DEC-116…DEC-119,
iscrizione dall'app DEC-120…DEC-127, unità DEC-128, correzioni e importazione
DEC-129, DEC-130, formazione dei capi DEC-134 (fase 5), esigenze alimentari DEC-135,
diritti GDPR DEC-136.

## Decisioni della fase 2 da riportare nell'analisi

Prese con il maintainer il 29/10/2026, ancora senza codice DEC:

| Punto | Decisione | Precisa |
| --- | --- | --- |
| Chi fissa le quote | Solo il gruppo (capigruppo e tesoriere di gruppo), per tutti i tipi, anche la mensile di unità | DEC-80 |
| A chi si applica | Per ogni tipo si sceglie: tutti i soci, solo i ragazzi, solo i capi, le unità indicate | DEC-80 |
| Quota mensile | Una quota per ogni mese scelto, con un giorno di scadenza; chi entra a metà anno paga dai mesi successivi | DEC-80 |
| Sconto famiglia | Importo fisso in euro per tipo di quota, tolto alla quota di ogni socio quando il nucleo familiare ha almeno due soci; il nucleo comprende fratelli, genitore socio e figli soci, coniugi soci (anche senza figli soci, indicati a mano); mai sulla quota nazionale | DEC-81 |
| Agevolazioni | Le registrano i capigruppo e il tesoriere di gruppo (capo); la famiglia vede l'importo, la nota resta alla Co.Ca. | DEC-82 |
| Pagamenti | Li registrano tesoriere di gruppo, capigruppo, tesoriere di unità, capo unità e staff dell'unità del socio; un pagamento si ripartisce su più quote della stessa famiglia, anche in parte (acconti); una ricevuta per pagamento | DEC-83, DEC-84 |
| Campi, uscite, eventi esterni | Rimandati alla fase 3, con le rate a scadenze fisse per campo estivo e Vacanze di Branco/Cerchio | DEC-80 |
| Casse | Un solo conto bancario del gruppo: ogni movimento indica l'unità (anche quelli con la carta di unità); una cassa contanti per unità; le configurano capigruppo e tesoriere di gruppo | DEC-85 |
| Chi registra in prima nota | Tesoriere di gruppo e capigruppo su tutte le casse; tesoriere di unità e capo unità per la loro unità | DEC-11, DEC-85 |
| Chi vede la prima nota | La Co.Ca. tutto (anche il rendiconto); il tesoriere R/S ragazzo solo i movimenti della sua unità, non il saldo del conto bancario | DEC-11 |
| Incassi delle quote | Entrano da soli: contanti nella cassa dell'unità del socio, il resto nel conto (chi registra può scegliere); voce A.1 per censimento e quota di gruppo, A.2 per la mensile; annullare il pagamento storna i movimenti | DEC-83, DEC-87 |
| Correzioni | Un movimento non si modifica: si storna con un motivo e si registra di nuovo | DEC-96 |
| Saldi | Saldo iniziale per cassa, poi verifiche di cassa del tesoriere o del capo unità: una differenza diventa una rettifica motivata (fuori dal Modello D) | DEC-11 |
| Rimborsi ai capi | Il capo registra la spesa anticipata con la foto; diventa un'uscita (Rimborsi spese volontari) quando il tesoriere la rimborsa | DEC-86 |
| Giustificativi | Foto facoltativa; le uscite senza giustificativo restano segnalate e la foto si può aggiungere dopo | DEC-86 |
| `[da verificare]` | Un capo non ancora in BuonaStrada non vede le quote degli altri; i pagamenti sbagliati si annullano (il numero di ricevuta resta, segnato annullato), non si modificano; li annullano capigruppo e tesoriere di gruppo; le rettifiche delle verifiche di cassa restano fuori dai totali del Modello D (mostrate a parte) e non si stornano (si fa una nuova verifica); il conto del gruppo lo verificano capigruppo e tesoriere di gruppo; un pagamento registrato prima di configurare le casse non entra in prima nota | — |

## Punti aperti da confermare

| Punto | Riferimento |
| --- | --- |
| Revoca dispositivi e idempotenza solo con sessione browser (servirà per l'app negli store) | DEC-105 |
