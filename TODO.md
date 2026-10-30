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
| 3 | Eventi e presenze | ✅ | eventi, presenze, quote a rate, calendario, email, autofinanziamento e budget dei campi, eventi su BuonaCaccia (DEC-158…DEC-164, fatti il 30/10; da provare nel browser) |
| 4 | Progressione Personale | 🚧 | E/G a blocchi (dettaglio sotto): blocchi 1–3 fatti (E/G e passaggi), ora R/S; poi R/S e L/C. Riferimento: specifica PP v1.0 (in `ignored/`, non nel repository) |
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
| 2.10 | Autofinanziamento come evento e budget dei campi (fatti con la fase 3, punto 3.5) | DEC-90, DEC-91, DEC-156 | ✅ |

### 3. Fase 3 — Eventi e presenze

Le decisioni prese con il maintainer il 29/10/2026 sono nell'analisi come DEC-137…DEC-144
(partecipanti, presenze, squadriglie e consigli, quote a rate, email, calendario, eventi su
BuonaCaccia) e DEC-156 (autofinanziamento e budget dei campi).

| # | Attività | Rif. | Stato |
| --- | --- | --- | --- |
| 3.1 | Eventi a quattro livelli (gruppo, branca, unità, squadriglia), unità coinvolte, partecipanti con assenze comunicate e non invitati; riunioni ricorrenti; riunioni e missione di squadriglia, delega, Consiglio Capi, Con.Ca.Vi., Alta Squadriglia | DEC-75 | ✅ |
| 3.2 | Presenze offline (presente, assente, giustificato), foglio da stampare, dettaglio per due anni poi totali per anno (`riassumi_presenze`) | DEC-78 | ✅ |
| 3.3 | Quote degli eventi, anche a rate, generate per i partecipanti (tolte se non partecipa e non pagate, tornano se partecipa di nuovo), importo per persona fino a zero | DEC-77 | ✅ |
| 3.4 | Calendario personale (iCal, link segreto rigenerabile) ed email di nuovi eventi, modifiche di date o luogo, annullamenti (non per le singole riunioni ricorrenti) e promemoria delle quote in scadenza (`promemoria_quote`, 7 giorni prima) | DEC-79 | ✅ |
| 3.5 | Movimenti di prima nota collegati a un evento (gli incassi delle sue quote da soli) e rendiconto dell'evento; budget dei campi (due valori su tre, contributo dello staff a parte, agevolazioni come contributo dalla cassa) | DEC-90, DEC-91, DEC-82 | ✅ |
| 3.6 | Eventi su BuonaCaccia: iscrizioni con scadenze, link di gestione per i capi, liberatoria, schede con domande riusabili, foto, quota per la famiglia, formazione capi per la Zona (`apps/buonacaccia`, promemoria con `promemoria_buonacaccia`); la foto profilo (DEC-162) arriverà con il fascicolo | DEC-158…DEC-164 | ✅ |

### 4. Fase 4 — Progressione Personale

Riferimento: «Specifica di dominio e requisiti per lo sviluppo» v1.0 (DEC-56), ridotta dalle
decisioni DEC-56…DEC-74; scelte del 30/10: lo staff apre sentiero e tappa, la verifica ha
la sede, le mete possono essere riservate, lavoro a blocchi con un commit ciascuno. Ogni
blocco si prova nel browser prima del commit; i casi di prova della specifica (§13,
§19.3) diventano test (DEC-73).

| # | Attività | Rif. | Stato |
| --- | --- | --- | --- |
| 4.1 | E/G, blocco 1: apertura del sentiero, tappe (Scoperta, Competenza, Responsabilità) riconosciute nel Consiglio della Legge, collocamento di chi entra più grande, Promessa, consegna del distintivo, date parziali e rettifiche tracciate; mete (anche riservate) e impegni con i sei stati, revisioni del testo, proposta di verifica (ragazzo, capo squadriglia), convalida con data, chi e sede; anche offline; scheda del sentiero e vista di reparto | DEC-57…DEC-61, DEC-70…DEC-73, DEC-171…DEC-173 | ✅ provato nel browser il 30/10 (staff e ragazza) |
| 4.2 | E/G, blocco 2: specialità e brevetti con carta, maestro (anche esterno) e riconoscimento; specialità di squadriglia; imprese di reparto, squadriglia e Alta Squadriglia con posti d'azione; promemoria del brevetto | DEC-62…DEC-65, V09, V10 | ✅ provato nel browser il 30/10 |
| 4.3 | Passaggi di branca decisi dalla Co.Ca., in blocco per unità, con sintesi per i nuovi capi | DEC-69, DEC-174…DEC-177 | ✅ provato nel browser il 30/10 (il report completo per i passaggi, DEC-41, resta alla fase 5) |
| 4.4 | R/S: passi, Carta di clan, Punto della Strada, EPPPI, conclusione (Partenza, saluto fraterno…) | DEC-67, DEC-68 | ⏳ |
| 4.5 | L/C: momenti, stagione come etichetta, prede e voli, specialità L/C, Piccole Orme, Consiglio degli Anziani | DEC-66, DEC-68 | ⏳ |

Dopo la fase 4: fascicolo completo con scheda medica e percorso di
formazione dei capi inserito a mano (fase 5, DEC-47), poi la fase 6: vedi la tabella "Fasi".

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

## Decisioni prese durante le fasi 2 e 3

Le decisioni prese con il maintainer il 29/10/2026 sono nell'analisi: eventi e presenze
DEC-137…DEC-144, quote e cassa DEC-145…DEC-156, email facoltative DEC-157.

## Punti aperti da confermare

| Punto | Riferimento |
| --- | --- |
| Revoca dispositivi e idempotenza solo con sessione browser (servirà per l'app negli store) | DEC-105 |
