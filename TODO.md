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
| 4 | Progressione Personale | ✅ | a blocchi (dettaglio sotto): E/G, passaggi, R/S, L/C, più le scelte confermate il 30/10 (DEC-186…DEC-190). Riferimento: [specifica PP v1.0](docs/analisi/specifica-pp.md) |
| 5 | Fascicolo completo | ✅ | a blocchi (dettaglio sotto): scheda medica con stampa, note e regole, fascicolo del ragazzo e dei capi, fine anno e archivio |
| 6 | Dopo | ✅ | a blocchi: 6.1 bacheca ✅ (DEC-218…DEC-220, provata nel browser il 30/10), 6.2 estratto conto ✅ (DEC-221…DEC-224, provato nel browser il 30/10 con un estratto sintetico; il file vero della banca si legge), 6.3 Carta di clan ✅ (DEC-227…DEC-229, provata nel browser il 30/10). Note: estratto conto (importazione dei movimenti della banca e abbinamento a quote e versamenti: note sul formato in [docs/analisi/estratto-conto-banca.md](docs/analisi/estratto-conto-banca.md)), Carta di clan |
| 7 | App negli store (Capacitor) | 💤 | in standby: si valuterà se realizzarla; DEC-105; prima un prototipo per la regola Apple 4.2 |
| 8 | Realizzazione documentazione di uso | 🚧 | in pausa dal 31/10 per la nuova navigazione, le impostazioni e i modelli delle email (blocchi N.1…N.5 sotto, DEC-241…DEC-251); analisi: [docs/analisi/manuali.md](docs/analisi/manuali.md) (DEC-230…DEC-239); blocco 1 ✅ (30/10): impianto Sphinx, PDF, dati di prova e screenshot automatici, introduzione, primo accesso e protezione del telefono del genitore; blocco 2 ✅ (30/10): il resto della parte genitore (manca il capitolo sulle iscrizioni agli eventi BuonaCaccia); poi ragazzi, capi, capigruppo; da valutare l'account Read the Docs. Era: installazione (per i gruppi che installano la propria copia) e uso per l'Avellino 1, sulla PWA (senza app negli store); l'analisi si fa quando ci si arriva |

## Prossimi passi

### 1. Chiudere la fase 1

| Attività | Chi | Stato |
| --- | --- | --- |
| Confermare le scelte segnate `[da verificare]` (29/10): dati obbligatori per BuonaStrada, promemoria, sospensione, chi corregge cosa (ora DEC-124, DEC-125, DEC-129, DEC-130) | maintainer | ✅ applicate |
| Riportare nell'analisi le decisioni del 28 e 29/10 (DEC-110…DEC-136) | sviluppo | ✅ 29/10 |
| In produzione, programmare i comandi giornalieri: esempio pronto in [deploy/cron/qdc.crontab](deploy/cron/qdc.crontab) | chi installa | ⏳ |
| Collegare il Drive condiviso del gruppo per l'archivio (account di servizio, cartella, chiave `QDC_IMPRONTA_CHIAVE` da conservare: vedi README) e provare un'archiviazione vera | chi installa | ⏳ |
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
| 4.3 | Passaggi di branca decisi dalla Co.Ca., in blocco per unità, con sintesi per i nuovi capi | DEC-69, DEC-174…DEC-178 | ✅ provato nel browser il 30/10, con conferma prima dell'esecuzione e rettifica di un passaggio eseguito per errore (il report completo per i passaggi, DEC-41, resta alla fase 5) |
| 4.4 | R/S: passi, Carta di clan, Punto della Strada, EPPPI, conclusione (Partenza, saluto fraterno…) | DEC-67, DEC-68, DEC-179…DEC-181 | ✅ provato nel browser il 30/10 (l'EPPPI resta una partecipazione a un evento BuonaCaccia, DEC-68: nessuno strumento a parte) |
| 4.5 | L/C: momenti, stagione come etichetta, prede e voli, specialità L/C, Piccole Orme, Consiglio degli Anziani | DEC-66, DEC-68, DEC-182…DEC-185 | ✅ provato nel browser il 30/10 |
| 4.6 | Scelte confermate dopo i blocchi: Progressione scritta solo dallo staff, imprese guidate dal capo squadriglia e dal Consiglio d'impresa, data della conquista, rilettura del rover nel Punto della Strada, rientro in clan, avvisi sulla durata della stagione; specifica PP nel repository | DEC-186…DEC-190 | ✅ |

### 5. Fase 5 — Fascicolo completo

Scelte del 30/10: prima la scheda medica, poi le note; un commit per blocco, provato nel
browser. Moduli AGESCI di riferimento in `ignored/schede_adesione_e_mediche/` (non nel
repository).

| # | Attività | Rif. | Stato |
| --- | --- | --- | --- |
| 5.1 | Scheda medica completa: tessera sanitaria, reperibilità annuale e per un singolo evento, antitetanica, note, campi facoltativi; data dell'ultima firma su carta e della prescrizione, con avviso se la scheda cambia dopo; stampa del modulo AGESCI precompilato (minorenni e maggiorenni) e delle schede dei partecipanti a un evento; intestazione del gruppo e logo | DEC-48…DEC-54, DEC-192…DEC-195 | ✅ provato nel browser il 30/10 |
| 5.2 | Note di staff e del capo squadriglia con visibilità; regole sul rapporto con il minore (riservate alla Co.Ca., anche offline) | DEC-39, DEC-40, DEC-43, DEC-95, DEC-197…DEC-199 | ✅ provato nel browser il 30/10 (capo e genitore) |
| 5.3 | Fascicolo del ragazzo: foto profilo storicizzata, allegati alla Progressione, autorizzazioni, presenze per anno, report per i passaggi | DEC-38, DEC-41, DEC-42, DEC-200…DEC-205 | ✅ provato nel browser il 30/10 (foto ritagliata, allegato, fascicolo) |
| 5.4 | Fascicolo dei capi: anni di servizio, unità e ruoli, formazione inserita a mano | DEC-47, DEC-134, DEC-206…DEC-208 | ✅ provato nel browser il 30/10 |
| 5.5 | Fine anno e uscita: congelamento e riapertura dell'anno, archiviazione dopo due anni con caricamento automatico sul Drive del gruppo, esportazione e importazione del fascicolo tra gruppi | DEC-44…DEC-46, DEC-196, DEC-209…DEC-217 | ✅ provato nel browser il 30/10 (chiusura e riapertura); il caricamento sul Drive vero va provato all'installazione |

### Navigazione, impostazioni ed email (prima di continuare il manuale)

Appunti del maintainer del 31/10/2026, dopo un giro di prova con i dati del manuale; decisioni
nell'analisi come DEC-241…DEC-251 (sezione «Navigazione, impostazioni ed email»). Il manuale
(fase 8) è in pausa finché questi blocchi non sono fatti: le schermate e i passi dei capitoli
già scritti cambiano. Un commit per blocco, provato nel browser.

| # | Attività | Rif. | Stato |
| --- | --- | --- | --- |
| N.1 | Impostazioni (capigruppo e amministratore tecnico): nome e sigla del sito e del gruppo, separati dai dati ufficiali per le stampe; titolo completo e breve con segnaposto; riga del piè di pagina sopra quella fissa; intestazione delle stampe e link di pagamento spostati qui dalle quote | DEC-245…DEC-248 | ✅ provato nel browser il 31/10 (titoli, piè di pagina, segnaposto sbagliato rifiutato) |
| N.2 | Menu laterale (sidebar del tema 3.0.0a2, icone Bootstrap Icons incluse nell'app per l'offline), gruppi e voci secondo i permessi, avatar con il menu del profilo, homepage a gruppi con i contatori, breadcrumb con la tenda, nomi nuovi e pagina Privacy | DEC-241…DEC-244, DEC-251 | ✅ provato nel browser il 31/10 come capogruppo (computer e telefono); gli altri profili coperti dai test del menu |
| N.2b | Correzioni del maintainer al menu (31/10): la pagina occupa sempre la finestra, scorre solo il contenuto, piè di pagina sempre in fondo da computer (da telefono alla fine del contenuto) e menu a tutta altezza; gruppi del menu che si chiudono | DEC-241 | ✅ provato nel browser il 31/10 (computer e telefono) |
| N.2c | Menu a fisarmonica (maintainer, 31/10): gruppi tutti chiusi all'inizio, ognuno con la sua icona; aprirne uno chiude gli altri; si apre da solo quello della pagina mostrata | DEC-241 | ✅ provato nel browser il 31/10 |
| N.1b | I dati ufficiali del gruppo corretti nell'app (denominazione sociale, codice fiscale) non sono più riscritti dall'importazione da BuonaStrada: l'app vince (maintainer, 31/10) | DEC-252 | ✅ |
| N.1c | Pagamenti nelle Impostazioni: contanti, bonifico (IBAN e intestazione) e PayPal (link e quota aggiuntiva fissa, in percentuale o a fasce), ognuno abilitato a parte e mostrato con la sua icona nelle quote della famiglia solo se abilitato | DEC-253 | ✅ provato nel browser il 31/10 (fasce, IBAN, pagina della famiglia); la registrazione in prima nota è il blocco N.1g |
| N.1d | PayPal a fasce: voce «Oltre» a parte, obbligatoria, per gli importi sopra la fascia più alta (maintainer, 31/10) | DEC-253 | ✅ provato nel browser il 31/10 |
| N.1e | Pagamenti (maintainer, 31/10): link PayPal con l'importo già dentro (base + importo, es. …/paypalme/nome/50.50) per ogni quota e per il totale; carte ai capi abilitabili a parte dai contanti; banca e BIC/SWIFT con l'IBAN | DEC-253 | ✅ provato nel browser il 31/10 |
| N.1f | Link PayPal: sempre indirizzo base più importo, qualunque sia il formato del link (maintainer, 31/10) | DEC-253 | ✅ |
| N.1g | Pagamenti PayPal in prima nota: cassa «PayPal», due entrate (quota con ricevuta; «Quota PayPal» in A.10 «Altre entrate»), uscita «Trattenuta PayPal» se chi verifica scrive l'accreditato | DEC-254 | ✅ provato nel browser il 31/10 (saldo del conto PayPal = accreditato) |
| N.1h | Pagamenti segnalati dalla famiglia (maintainer, 31/10): pagando con il pulsante PayPal o dichiarando un bonifico la quota resta «in verifica», con la ricevuta (PDF o immagine) caricabile anche dopo; un capo verifica (dalla ricevuta o dall'estratto conto PayPal/banca) e il pagamento si chiude con la sua ricevuta. Scelte del 31/10: PayPal confermato al ritorno nell'app, ricevuta cancellata alla verifica, verifica di chi registra i pagamenti con un contatore | DEC-255 | ✅ provato nel browser il 31/10 (segnalazione dopo PayPal, verifica, ricevuta) |
| N.1i | Conto PayPal creato da solo alla prima abilitazione di PayPal; «Quota PayPal» sotto D.1 «Da rapporti bancari», «Trattenuta PayPal» sotto A.2 con gli oneri bancari (maintainer, 31/10) | DEC-254 | ✅ coperto dai test (nel database di prova il conto PayPal c'era già) |
| N.3 | Modalità di prova delle email con Mailpit: servizio compose, proxy riservato all'amministratore tecnico, permesso del server (`QDC_MAILPIT_CONSENTITO`, sempre in sviluppo), avviso a tutti i collegati e sulla pagina di accesso | DEC-249 | ✅ provato il 31/10: un codice di accesso finisce in Mailpit e si legge da `/mailpit/` come amministratore tecnico (404 per gli altri), avviso nel browser |
| N.4 | Modelli delle email: tutte le email (anche quelle di allauth) da un registro di modelli con segnaposto, editor di testo formattato, HTML ripulito sul server, testo semplice ricavato, segnaposto indispensabili controllati al salvataggio, ritorno al modello di base, anteprima | DEC-250 | ✅ provato nel browser il 31/10 (modello dell'invito: segnaposto mancante rifiutato, reinserito, anteprima); 28 email, comprese le 6 di allauth; ricevute e riepiloghi ora partono uno per indirizzo |
| N.5 | Manuale: rigenerare le schermate e rivedere i passi dei capitoli già scritti (introduzione, genitore) per la nuova navigazione | DEC-238 | ⏳ |

### Lista d'attesa (prima di continuare il manuale)

Richiesta del maintainer del 31/10/2026: la lista d'attesa di chi vuole entrare nel gruppo,
con la sua sezione del manuale. Decisioni nell'analisi quando confermate.

| # | Attività | Rif. | Stato |
| --- | --- | --- | --- |
| L.1 | Analisi: dati, chi vede e gestisce, conferma dell'email, promemoria dei due anni, età minime e massime delle unità, privacy | DEC-256…DEC-263 | ✅ 31/10 |
| L.2 | Iscrizione pubblica alla lista (genitore o maggiorenne, senza account), email di conferma con il link per modificare o cancellarsi, link ritrovabile con l'email; inserimento da parte di un capo | DEC-256…DEC-258 | ✅ provato nel browser il 31/10 |
| L.3 | Vista dei capi: per età nell'anno in corso e nel successivo, branca e unità consigliate (età minime e massime per unità), contattato / da contattare e per quale unità | DEC-259…DEC-261 | ✅ provato nel browser il 31/10 |
| L.4 | Iscrizione: l'unità scelta, il link al genitore (o al maggiorenne) per i dati dell'iscrizione, che prosegue come l'iscrizione dall'app (DEC-120…DEC-127) | DEC-261 | ✅ provato nel browser il 31/10 |
| L.5 | Promemoria dei due anni (contati da quando si raggiunge l'età minima di un'unità del gruppo), uscita dopo 30 giorni senza risposta | DEC-262, DEC-263 | ✅ coperto dai test (comando giornaliero) |
| L.6 | Manuale: la sezione della lista d'attesa (famiglie e capi) | DEC-238 | ⏳ |

### Privacy policy, termini e cookie (in questa sessione, dopo la lista d'attesa)

Richiesta del maintainer del 31/10/2026.

| # | Attività | Rif. | Stato |
| --- | --- | --- | --- |
| P.1 | Privacy policy: pagina pubblica con un testo di base precompilato, che capigruppo e amministratore tecnico modificano con l'editor nelle Impostazioni; link nel piè di pagina e dal modulo della lista d'attesa | — | ⏳ |
| P.2 | Termini e condizioni: come la privacy policy | — | ⏳ |
| P.3 | Cookie banner (l'app usa solo cookie tecnici: da decidere con il maintainer se solo informativo) | — | ⏳ |

### 8. Fase 8 — Documentazione di uso (appunti per quando ci si arriva)

Argomenti da spiegare bene ai capi, perché non sono chiari a tutti:

- **Regole sul rapporto con il minore** (DEC-43, DEC-199): cosa sono (le indicazioni
  che i genitori scrivono sul modulo sanitario per i minorenni, per esempio dopo una
  separazione: chi può riprendere il ragazzo all'uscita, a chi non dare informazioni,
  provvedimenti del giudice), perché le leggono solo i capi, che valgono finché i
  genitori non danno nuove indicazioni scritte, dove si trovano al campo anche senza rete.

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
