# TODO — stato dei lavori

Legenda: ✅ fatto · 🚧 in corso · ⏳ da fare · 💤 rimandato

Dettagli dei requisiti: [analisi dei requisiti](docs/analisi/analisi-requisiti.md)
(sezione "Fasi di sviluppo"). Note tecniche: [CLAUDE.md](CLAUDE.md),
[backend/CLAUDE.md](backend/CLAUDE.md), [frontend/CLAUDE.md](frontend/CLAUDE.md).

In cima ci sono i punti aperti; sotto, le fasi e lo storico di quello che è stato fatto.

## Punti aperti

### Da sviluppare

#### N.26 — Logo AGESCI per le installazioni generiche ✅ 03/11

Fatto (DEC-294): icone AGESCI in `frontend/public` da `resources/AGESCI.svg` (`scripts/icone.ts`, con `sharp`); `QDC_LOGO` in `.env` applicato da `vite.config.ts` a una copia di `public/`; immagine dell'app costruita dalla radice del repository (`.dockerignore`), provata con Podman con il logo dell'Avellino 1; logo dell'Avellino 1 in `resources/logo-avellino1.png` per le schermate del manuale; guida di installazione con logo AGESCI e autore Andrea Bruno (link a bruand81.it nel piè di pagina); esempi generici; sezione «Il logo del gruppo» nella guida. Il file HTML scaricato per errore (`File_AGESCI.svg`) non è entrato nel repository.

Richiesta del maintainer (03/11): chi installa l'app per un altro gruppo deve trovare un
sistema pulito, senza riferimenti all'Avellino 1. Nuovo DEC nell'analisi prima di
svilupparla. Deciso il 03/11:

1. **Logo di base: AGESCI**, da `resources/File_AGESCI.svg`. Attenzione: il file oggi nel
   repository (aggiunto, non ancora nel commit) **non è un SVG ma la pagina HTML di Wikimedia
   Commons**: va sostituito con il file originale prima di svilupparla.
2. **Logo alternativo**: chi installa mette un altro file in `resources/` e ne indica il nome
   in `.env` (per esempio `QDC_LOGO=resources/logo-gruppo.svg`; vuota = AGESCI), SVG o PNG
   quadrato. Da quel file, alla costruzione dell'immagine dell'app, si ricavano le icone (oggi
   PNG fissi in `frontend/public`: favicon 16 e 32, `apple-touch-icon`, icone della PWA 192,
   512 e «maskable»), il logo della barra in alto (`App.vue`) e quello delle pagine di errore
   (`backend/templates/errori/base.html`, `frontend/public/errori/50x.html`).
3. **Documentazione**: la guida di installazione usa il logo AGESCI; il manuale d'uso resta con
   quello dell'Avellino 1 (oggi entrambi usano `docs/_static/logo.png`).
4. **Il logo dell'Avellino 1 resta nel repository** (per esempio `resources/logo-avellino1.png`,
   ricavato dalle icone di oggi): lo usano il manuale e le schermate del manuale
   (`schermate.ts` costruisce l'app con quel logo); un'installazione nuova non lo usa mai.
5. **Esempi testuali generici** al posto dell'Avellino 1 («es. AGESCI Avellino 1», «AVELLINO 1»
   nei suggerimenti della carta intestata, `https://qdc.avellino1.it` negli esempi dei
   modelli email…): per esempio «AGESCI Nomeluogo 1» e `https://qdc.esempio.it`. Restano i
   link al progetto su GitHub e la frase della guida che dice che l'app è nata per l'Avellino 1.
6. **Guida di installazione**: copyright e autore Andrea Bruno, con il link a bruand81.it.
7. **Con la release**: istruzioni per qdc.avellino1.it, che dopo l'aggiornamento avrebbe il
   logo AGESCI e deve tornare a quello del gruppo (il file in `resources/` e `QDC_LOGO` in
   `.env`), anche nelle note della versione.

#### N.27 — Una sola passkey per dispositivo, per entrare e per sbloccare ✅ 03/11 (provata dal maintainer in produzione)

Fatto (DEC-295): la passkey di accesso creata con il PRF sblocca anche i dati; il segreto è tolto dalla risposta prima che allauth la salvi (test, e controllato nel database); `GET /api/v1/io/passkey` per gli id delle credenziali (bloccato in impersonazione); rimuovere la passkey spegne l'impronta e la segnala al gestore; senza PRF resta il PIN con il suggerimento di Safari sul Mac; messaggio chiaro all'accesso per una passkey sconosciuta. Provato in Chromium con un autenticatore virtuale con PRF: protezione, conferma della password, passkey unica (stesso id sul server), sblocco con l'impronta, accesso con la passkey, rimozione, passkey sconosciuta all'accesso. Scoperto provando: allauth 65.20 chiede di confermare la password prima di aggiungere una passkey anche subito dopo l'accesso; la pagina della protezione allora porta a «Password e sicurezza». Da provare dal maintainer sui dispositivi veri.

Segnalazione del maintainer (03/11, con la 1.5.0 su qdc.avellino1.it):

- **iPhone, PWA installata**: «Accedi con passkey» propone anche le passkey di sblocco
  (sincronizzate dal portachiavi di iCloud, stesso sito); scegliendone una il server non la
  conosce e allauth risponde «Codice errato» (`mfa/webauthn/internal/auth.py`: lo user handle
  della passkey di sblocco è casuale, `biometria.creaCredenziale`).
- **Mac, app installata con Chrome**: attivando l'impronta compare «Impronta o volto non
  disponibili»: Chrome crea la passkey ma non dà il segreto PRF (nella scheda normale sì).
  Ogni tentativo lascia una passkey inutile in Password di Apple.

Deciso il 03/11 (cambia DEC-97: nuovo DEC nell'analisi):

1. **Una sola passkey per dispositivo**: la passkey di accesso (allauth, registrata sul server)
   serve anche a sbloccare senza rete, con il segreto PRF; niente più passkey di sblocco
   separate. Da verificare nello sviluppo: aggiungere l'estensione `prf` alla creazione
   della passkey di allauth (`passkey.crea`, opzioni JSON di simplewebauthn); sbloccare con
   `get()` sulle passkey di accesso dell'account (anche una sincronizzata da un altro
   dispositivo), con un sale per dispositivo; attivare l'impronta crea la passkey di accesso
   se il dispositivo non ne ha (allauth chiede un accesso recente); cosa succede se la passkey
   viene cancellata in Dispositivi (lo sblocco con impronta va riattivato, resta il PIN);
   passaggio delle installazioni con la vecchia passkey di sblocco (segnalarla al gestore
   perché la tolga) [da verificare].
2. **Senza segreto PRF** (l'app di Chrome sul Mac): l'app propone il solo PIN e, sul Mac,
   suggerisce Safari con «Aggiungi al Dock». Con il punto 1 la passkey creata è comunque una
   passkey di accesso valida: si tiene per entrare, non si usa per sbloccare (prima della
   decisione 1 il maintainer aveva scelto di toglierla).
3. Manuale (protezione del dispositivo, accesso con passkey) e schermate da aggiornare.

Intanto, per il maintainer: sbloccare con il PIN; in Password di Apple cancellare tutte le
passkey di qdc.avellino1.it e, se serve entrare con la passkey, crearne una sola di accesso
da Dispositivi (non fa sbloccare l'app finché N.27 non è sviluppata).

#### N.28 — Elenco degli incarichi per unità: ogni capo in ogni sezione dei suoi incarichi ✅ 03/11

Fatto con test (`elenco_incarichi._per_unita`); DEC-284 precisato nell'analisi; manuale e schermate aggiornati.

Rif. DEC-284, DEC-293. Chiarimento del maintainer (03/11, sul PDF della 1.6.0): nel raggruppamento
per unità la Co.Ca. deve esserci con i capigruppo e l'AE di gruppo anche se fanno servizio in
un'unità; chi ha incarichi in più unità compare in più unità, anche se così compare più volte.
Deciso il 03/11:

1. ogni incarico ha la sua sezione: quelli di unità nella loro unità (capo unità, staff, AE di
   unità, tesoriere di unità), quelli di gruppo in Co.Ca. (capogruppo, AE di gruppo, tesoriere
   di gruppo, amministratore, servizi di supporto); un capo compare in ogni sezione in cui ha un
   incarico tra i tipi scelti;
2. accanto al nome, in ogni sezione, solo gli incarichi di quella sezione;
3. capigruppo e AE di gruppo in Co.Ca. solo se il loro tipo è scelto per la stampa;
4. chi non ha incarichi di servizio (per esempio un tesoriere di unità) compare nella sua unità
   e anche in Co.Ca. con «Servizio di supporto al gruppo» (N.22);
5. sviluppo subito e release 1.6.1.

#### N.29 — Professione da BuonaStrada, regola degli AE, ordine del PDF degli incarichi ✅ 03/11

Richiesta del maintainer (03/11). Fatto con test (DEC-296): professione importata per tutti i
soci che l'hanno, vista dalla persona e dalla Co.Ca. nella scheda, corretta scegliendo tra i
valori di BuonaStrada; nomina di un AE rifiutata se la professione non dice presbitero o
sacerdote, e nel menu delle nomine solo i presbiteri; nel PDF per unità prima la Co.Ca., poi
L/C, E/G, R/S per codice. Controllato su un'esportazione vera (in `ignored/`, solo conteggi): la
professione è un elenco fisso di 25 valori con «PRESBITERO»; **non importati**: la nazionalità
(codice numerico, e la tabella dei codici di BuonaStrada non è disponibile: si ignora, maintainer 03/11) e gli incarichi
associativi (colonne vuote in tutte le righe di «Ricerca Soci»; l'esportazione degli incarichi di BuonaStrada è prevista ma non funziona: si ignorano, maintainer 03/11). In produzione (1.7.0) il
maintainer ha reimportato il primo import unito in un file solo: professione arrivata, tutto
funziona (03/11).

#### N.30 — Foto del profilo nell'avatar ✅ 03/11

Fatto con test (DEC-297): `/io` dice `foto_id`, il menu laterale mostra la foto (iniziali senza rete o se non si carica), aggiornata quando si carica una foto nuova della propria scheda; vista nella schermata di Giulia con la sua foto di prova.

Richiesta del maintainer (03/11): se la persona collegata all'account ha una foto nel profilo,
l'avatar (in basso nel menu laterale, oggi le iniziali) mostra quella foto.

#### N.31 — Tema 3.0.0a3: i componenti nuovi di Bootstrap 6 nella PWA ✅ 03/11 (DEC-298)

Richiesta del maintainer (03/11): con il tema 3.0.0a3 (stesso Bootstrap 6.0.0-alpha.1) usare
i componenti nuovi ovunque si può. Nuovo DEC nell'analisi prima di svilupparla (cambia DEC-97
sul PIN: DEC-298). Via del maintainer il 03/11. Analisi:

- **Il tema**: dei tre file copiati cambia solo `_branche.scss` (colori «subtle» della branca
  `generico`, prima bianchi): da ricopiare byte per byte. I tag del tema sono template Django:
  nella PWA si rifà lo stesso markup in componenti Vue. Il JavaScript di Bootstrap oggi non è
  caricato: si importano solo i moduli che servono (`otp-input`, `strength`) nei componenti,
  creati al montaggio e distrutti allo smontaggio.
- **Password con il pulsante per mostrarla** (`CampoPassword.vue`, markup di
  `_password_toggle_button.html`): accesso, sblocco con password in `PasskeyAccesso`, server
  di posta (`ServerPosta`, due campi).
- **Password nuove con la robustezza** (`.strength`, messaggi in italiano, almeno 8 caratteri
  come `MinimumLengthValidator`; decide sempre il server): invito, iscrizione, reimposta
  password, cambio password.
- **Codice OTP** (`.otp`, evento `complete.bs.otp`): codice via email all'accesso (oggi 8
  caratteri lettere e cifre `XXXX-XXXX`, due gruppi da 4), codice dell'app di autenticazione
  (6 cifre); entra da solo appena completo.
- **PIN di 6 cifre esatte** (oggi «almeno 6», `LUNGHEZZA_MINIMA_PIN`): OTP mascherato in
  protezione (scelta e conferma) e sblocco, che sblocca appena raggiunte le 6 cifre.
- **Avatar** (`.avatar`, iniziali o foto): menu laterale, scheda della persona, elenchi.
- **Accordion** (`.accordion`, `<details name>` come oggi): gruppi della Home, al posto dello
  stile `qdc-gruppo-home`; gli altri `<details>` (fine anno, deroghe, banca, modelli email,
  piede, impostazioni) come `accordion-flush accordion-sm`.
- **Altri da valutare**: form adorn con «€» negli importi (una ventina di campi), stepper
  (tappe del sentiero E/G, stagioni L/C, sezioni dell'iscrizione), chip (destinatari delle
  email, filtri). Non servono: datepicker (i campi data del browser vanno bene sul telefono),
  carousel, range.

Blocco 1 fatto con test (03/11): `_branche.scss` del tema 3.0.0a3; `CampoPassword` (occhio, robustezza nelle password nuove), `CampoOtp` (codice via email, app di autenticazione, PIN), PIN di 6 cifre con sblocco alla sesta e ripiego per i PIN più lunghi (`cassaforte.cambiaPin`, tiene i dati), `Avatar` (menu, elenchi di persone, squadriglia, staff e incarichi: iniziali, perché gli elenchi non portano la foto), accordion nella Home e `SezioneApribile` al posto degli altri `<details>`; manuale e schermate di accesso, protezione e sblocco rifatte (provate con Playwright). Blocco 2 fatto con test (03/11): `CampoImporto` («€» dentro i campi importo, una ventina, tolto «(€)» dalle etichette), `Passi` (stepper: tappe/momenti/passi della Progressione, stagioni L/C, passi della richiesta in «La mia iscrizione»; il modulo di iscrizione è una pagina sola e non ha passi), `SceltaChip` («A chi» degli avvisi, unità nell'elenco delle persone); schermate del manuale rifatte. Confermate dal maintainer il 03/11 le tre scelte: i passi dell'iscrizione in «La mia iscrizione» (il modulo resta una pagina sola), le iniziali negli avatar degli elenchi (senza foto), i chip sul «A chi» degli avvisi (le email per gruppi restano interruttori). Da provare dal maintainer: accesso con il codice via email e con l'app di autenticazione, ripiego per un PIN più lungo.

Il secondo fattore accetta anche i codici di recupero (non di 6 cifre): sotto l'OTP un link
«Usa un codice di recupero» con il campo normale.

Deciso il 03/11:

1. **PIN più lunghi di 6 cifre già impostati**: sotto le caselle «Il tuo PIN è più lungo?»
   apre il campo di oggi; dopo lo sblocco l'app chiede di scegliere un PIN nuovo di 6 cifre.
2. **Codice via email**: resta di 8 caratteri tra lettere e cifre (OTP alfanumerico, due
   gruppi da 4).
3. **Altri componenti**: tutti e quattro, «€» negli importi, stepper, chip, avatar negli
   elenchi (persone, squadriglia, staff).

#### N.32 — «Incarichi di gruppo» diventa «Organigramma» ✅ 03/11 (DEC-299)

Richiesta del maintainer (03/11). Voce del menu (`navigazione/menu.ts`), titolo della pagina
(`GruppoView.vue`, `router/pagine.ts`), link nella pagina delle unità (`UnitaView.vue`), test del
menu e manuale (`gruppo/amministratore.md`, `fine-anno.md`, `index.md`, `organizzazione.md`).
Solo il nome: la pagina e l'indirizzo restano gli stessi.

#### N.33 — Modelli delle email in una pagina a parte ✅ 03/11 (DEC-300)

Richiesta del maintainer (03/11): nelle Impostazioni i modelli sono troppi. Deciso il 03/11:
**pagina a parte** «Modelli delle email»; nelle Impostazioni resta un link. Ogni modello si apre
come oggi (`ModelloEmailView`), e il breadcrumb porta alla nuova pagina invece che alle
Impostazioni. Manuale e schermate da aggiornare.

#### N.34 — Chiamare e scrivere dai numeri di telefono ✅ 03/11 (DEC-301)

Richiesta del maintainer (03/11): ovunque compare un numero, pulsanti accanto per chiamare o
scrivere. Deciso il 03/11:

- Tre pulsanti possibili: **Chiama** (`tel:`), **WhatsApp** (`https://wa.me/…`, con il prefisso
  +39 aggiunto quando il numero non ne ha uno) e **SMS** (`sms:`).
- **Ognuno sceglie quali vedere**, nelle impostazioni della propria persona (non del sito): di
  base Chiama e WhatsApp. La scelta sta sul server, con l'account, e vale su tutti i suoi
  dispositivi: nella pagina delle scelte sulle email, che diventa «Le mie preferenze» (deciso
  il 03/11).
- Un solo componente per ogni numero mostrato: scheda della persona, squadriglia, al campo,
  lista d'attesa, reperibilità degli eventi, contatti sanitari… (dove oggi c'è un link `tel:`
  o il numero scritto).

#### N.35 — Numeri di telefono nella rubrica, per capi e capi squadriglia ✅ 03/11 (DEC-302, file vCard da provare sui telefoni veri)

Richiesta del maintainer (03/11): solo capi e CSQ scelgono uno o più numeri e li aggiungono
alla rubrica del telefono. Un sito non può scrivere nella rubrica: l'app fa scaricare un file
di contatti (vCard, `.vcf`) che il telefono propone di salvare. Deciso il 03/11:

- **Solo con la rete**: il file nasce solo da dati letti dal server in quel momento; senza rete
  il pulsante non c'è. Il file resta sul telefono fuori dalla protezione col PIN: dentro solo
  nome e numero.
- Solo i numeri che la persona già vede: i capi quelli delle loro unità (ragazzi e genitori),
  il CSQ quelli della sua squadriglia (`/mia-squadriglia`, DEC-13). Si scelgono dall'elenco dei
  soci e dei genitori, dalla pagina dell'unità e da «La mia squadriglia» (deciso il 03/11).
  Decide la policy, con un endpoint che prepara il file e i test per ogni ruolo. Il download
  non va nel registro degli accessi (deciso il 03/11).

#### N.36 — Progressione personale raggruppata per unità ✅ 03/11 (DEC-303)

Segnalazione del maintainer (03/11, con due reparti in parallelo, «Reparto Millenium (M1)» e
«(N1)»): nella Home le voci Imprese e Passaggi sono schede sciolte e non si capisce di quale
unità siano (`navigazione/menu.ts`, `progressione()`: le `sottovoce` nella Home diventano schede
come le altre). Deciso il 03/11: **una scheda per unità**, con il nome e il codice
dell'unità, e dentro i link Progressione, Imprese (reparto), Carta di clan (clan) e Passaggi;
nel menu laterale l'unità diventa un titoletto con le sue voci sotto. Le «Imprese» del CSQ e
la Progressione del ragazzo restano come oggi.

DEC-299…DEC-303 nell'analisi (03/11). Via del maintainer il 03/11, con la release dopo.

#### N.37 — Link e QR code per condividere la lista d'attesa ✅ 03/11 (DEC-304)

Richiesta del maintainer (03/11): chiunque usi l'app, anche un genitore o un ragazzo, genera
un link da condividere e un QR code per la lista d'attesa. La lista è già pubblica
(`/lista-attesa`, DEC-256): il link è quello. Il QR si disegna sul telefono, così funziona anche
senza rete. Deciso il 03/11:

- **Dove**: una voce «Invita nel gruppo» nel menu laterale e una scheda nella Home, uguali per
  tutti; in più un pulsante «Condividi» in fondo alla pagina pubblica della lista d'attesa, così
  chi la riceve può girarla.
- **Cosa si fa**: il pulsante «Condividi» del telefono (WhatsApp, email…) e «Copia il link»; il
  QR grande sullo schermo da far inquadrare; il QR da scaricare come immagine PNG; un volantino
  A4 in PDF con logo e nome del gruppo, QR e poche righe di testo.
- **Nessuna traccia**: il link è uguale per tutti, non dice chi l'ha condiviso.
- **Testo del volantino**: c'è un testo di base con il nome del gruppo («Vuoi entrare nel
  gruppo scout …? Inquadra il codice e mettiti in lista d'attesa»), che i capigruppo modificano
  dalle Impostazioni e possono riportare al testo di base (deciso il 03/11).
- **Senza rete**: il QR si disegna sul telefono con una libreria MIT, quindi funziona anche
  offline (confermato il 03/11).

Fatto: pagina «Invita nel gruppo» (`/invita`, `InvitaView.vue`) con `CondividiLink.vue` e
`QrCode.vue` (libreria `uqr`, MIT, in `navigazione/condividi.ts`); il volantino è
`attesa/volantino.py` (QR di reportlab), `GET /volantino-lista-attesa.pdf`; il testo in
`Impostazioni.volantino_attesa` (`TestoVolantino.vue`). Policy `puo_condividere_lista_attesa` e
`puo_modificare_volantino_attesa`. Da provare sui telefoni veri: «Condividi» e la lettura del QR
stampato.

#### N.38 — Immagini ridimensionabili e HTML nell'editor di testo ✅ 03/11 (DEC-305)

Segnalazione del maintainer (03/11, con il logo nel piè di pagina delle email, enorme): in tutti
i campi con l'editor di testo (`EditorTesto.vue`: modelli e piè di pagina delle email, privacy
policy e termini) un'immagine inserita si deve poter ridimensionare, e si vuole poter modificare
direttamente l'HTML. Oggi il server pulisce l'HTML (`impostazioni/html.py`, nh3) e per `img`
tiene solo `src`, `alt` e `width`; Tiptap 3.32 ha già il ridimensionamento delle immagini
(`resize` in `@tiptap/extension-image`).

Deciso il 03/11:

- **Dimensione delle immagini**: si trascina l'angolo dell'immagine; selezionandola compaiono
  anche Piccola, Media, Grande e Originale (comode sul telefono). La larghezza resta in
  `width`, come oggi; nelle email l'immagine non supera mai la larghezza del messaggio.
- **HTML**: un pulsante «HTML» passa dal testo al codice e ritorno, per chiunque può già
  modificare quel testo.
- **Cosa resta**: gli elementi di oggi più l'allineamento (sinistra, centro, destra) di testo e
  immagini; il resto lo toglie il server, e l'editor avvisa quando qualcosa è stato tolto.

Fatto: `EditorTesto.vue` con le immagini in linea e ridimensionabili (`Image.extend` applica la
larghezza scelta con i pulsanti, che Tiptap applicherebbe solo trascinando), `TextAlign` e il modo
HTML con `sito/html.ts` (copia della lista del server, solo per avvisare); il server tiene
`style` solo con `text-align` e aggiunge alle immagini delle email `max-width:100%`
(`html.per_email`).

#### N.39 — Lo script di aggiornamento mostra cosa cambia ✅ 03/11

Richiesta del maintainer (03/11, prima della release): `scripts/aggiorna.sh` mostra l'elenco
delle modifiche dalla versione installata a quella nuova. Deciso il 03/11: un `CHANGELOG.md` in
italiano nel progetto, ricostruito dalle note delle release passate e aggiornato a ogni
release; lo script ne mostra le sezioni tra la versione installata e la nuova **prima** di
chiedere se aggiornare. Lo script che gira è quello della versione installata: l'elenco compare
negli aggiornamenti che partono dalla 1.10.

### Richieste del 03/11 (sera), da raccogliere

Richieste del maintainer del 03/11, solo annotate: si sviluppano quando il maintainer dice di
partire. Risposte alle domande date il 03/11; prima dello sviluppo, i DEC nuovi nell'analisi.

#### N.40 — Organigramma: tipi di incarico scelti da un menu a selezione multipla ⏳

Nel PDF dell'organigramma i tipi di incarico da includere si scelgono oggi con caselle di
spunta: al loro posto un menu a tendina con più scelte (combobox). **Solo lì** (deciso il 03/11):
l'assegnazione degli incarichi resta com'è. Da verificare cosa offre Bootstrap 6 alpha (forse un
componente nostro).

#### N.41 — Genitore che diventa capo, in due passi annullabili ⏳ (sostituisce DEC-282)

Deciso il 03/11:

1. **Entra in Co.Ca.**: lo fa un capogruppo dalla scheda del genitore; il genitore entra con i
   dati che l'app ha già e un **codice socio provvisorio** `9…` (come chi si iscrive dall'app,
   DEC-120), quindi è un capo in attesa che non vede dati sensibili; resta genitore dei figli.
2. **Invito all'account**, se non ne ha già uno da genitore (se ce l'ha, vede subito la parte da
   capo). I dati da capo mancanti li completa nella scheda o arrivano da BuonaStrada.

Si **annulla finché il codice è provvisorio** (cioè finché l'import di BuonaStrada non lo
riconosce), anche dopo l'invito: torna solo genitore e gli incarichi dati nel frattempo si
chiudono. Il **link di iscrizione in Co.Ca. di DEC-282 si toglie**.

#### N.42 — Inviti a più persone insieme ⏳

Deciso il 03/11: nell'**elenco delle persone** un filtro «senza account», caselle di selezione e
«Invita i selezionati». Lo usa chi oggi può invitare quelle persone (la policy si controlla per
ognuna). Solo genitori e maggiorenni (capi e ragazzi) con un'email, senza account e senza un
invito ancora valido. Le email passano dall'invio graduale (N.46).

#### N.43 — Minorenni invitati con un link personale ⏳ (cambia DEC-116)

Deciso il 03/11:

- Il link porta il codice socio **e un segreto casuale**; scade dopo **30 giorni**, vale **una
  volta**, si rigenera (il vecchio smette di valere). Si può mandare per qualsiasi canale.
- Chi lo apre conferma la **data di nascita**, poi inserisce la sua email (da confermare) e
  attiva l'account.
- Lo generano lo **staff dell'unità**, i **capigruppo** e il **capo squadriglia** per i suoi
  squadriglieri; dai **14 anni** (DEC-117); solo per chi non ha ancora un account.
- Quando il ragazzo attiva l'account, i **genitori ricevono un'email** di avviso.

#### N.44 — Riunioni separate dagli eventi, con serie, località e uniforme ⏳

Le riunioni **non sono eventi** (mai quote). Oggi `eventi.RiunioneRicorrente` genera un `Evento`
di tipo `RIUNIONE` per data.

- **Serie**: ripetizione (per esempio ogni sabato 16:30–18:30 dal 1° ottobre al 31 maggio); si
  annullano singole riunioni.
- **Uniforme sì/no** per la serie o per la singola riunione; **informazioni** sulla singola
  riunione con l'editor di testo.
- **Tipi e chi le crea**: di unità (Co.Ca. compresa); di squadriglia (il capo squadriglia); di
  Alta Squadriglia (staff, eventualmente di unità collegate); Consiglio Capi e Con.Ca.Vi. (staff
  dell'unità); Consiglio degli Anziani (staff, eventualmente congiunto).
- **In calendario**, anche nel feed iCal.

Deciso il 03/11:

- **Presenze** sulle riunioni come oggi (offline, registrazioni che si aggiungono).
- **Conversione**: le riunioni ricorrenti e gli eventi `RIUNIONE` esistenti diventano riunioni
  con le loro presenze; le riunioni di squadriglia diventano riunioni; la **missione di
  squadriglia resta un evento**.
- **Località**: elenco del gruppo gestito dai **capigruppo** (nome, indirizzo, link alla mappa
  facoltativo: sedi, basi); una località nuova scritta creando una riunione **entra subito
  nell'elenco** e i capigruppo la correggono o la tolgono. L'elenco vale anche per gli eventi.
- **Chi vede** informazioni, uniforme e località: gli invitati e i genitori dei minorenni
  invitati.
- **Email** solo quando una singola riunione è annullata o spostata (tipo facoltativo,
  DEC-157); niente per la creazione della serie né per le informazioni.

#### N.45 — Turni di squadriglia e di sestiglia ⏳ (dopo N.44)

Lo staff (eventualmente di unità collegate) sceglie i turni e li assegna a rotazione alle
squadriglie o sestiglie, ogni settimana o ogni mese. Squadriglieri, genitori e ragazzi della
sestiglia vedono il proprio turno per quella riunione e per le successive, sulla riunione in
calendario.

Deciso il 03/11:

- Le **sestiglie** (oggi non esistono) sono **solo gruppi di bambini per i turni**, composti
  dallo staff del branco/cerchio, senza capo sestiglia.
- **Rotazione settimanale**: scala a ogni riunione tenuta; le annullate e le settimane senza
  riunioni non contano. **Mensile**: cambia alla **prima riunione del mese**.
- Lo staff **corregge a mano** l'assegnazione di una singola riunione; dopo, la rotazione
  riprende dall'ordine previsto.

#### N.46 — Invio graduale delle email in blocco ⏳

Deciso il 03/11: una **coda di invio** sul server, smaltita ogni minuto da un comando (cron);
**blocchi di 20 email, poi 2 minuti di pausa**; **tetto di 400 al giorno**, oltre il quale le
email aspettano il giorno dopo; valori modificabili dall'amministratore tecnico nelle
Impostazioni, dove si vede quante sono in attesa. Partono **subito, fuori coda**, le email
singole chieste dalla persona: codice di accesso, nuova password, conferma dell'indirizzo, avvisi
sull'account. Gli inviti in blocco (N.42) e gli avvisi a molti passano dalla coda.

#### N.47 — Account della piattaforma per l'amministratore tecnico ⏳

Deciso il 03/11: pagina con tutti gli account: email, persona collegata (o nessuna), creazione
e ultimo accesso, metodi di accesso (password, passkey, Google, Apple, secondo fattore),
dispositivi, blocco per troppi tentativi. Nessun dato della scheda. **Si gestisce tutto**:
sbloccare i tentativi, disattivare e riattivare, cambiare l'email, revocare dispositivi, togliere
passkey o secondo fattore, cancellare l'account. **Cancellare toglie solo l'accesso** (account,
passkey, dispositivi, sessioni): la persona e i suoi dati restano (per quelli c'è la richiesta
dell'interessato, DEC-102). Ogni azione chiede un **motivo**, resta nel registro delle modifiche,
e l'interessato riceve un'**email** quando cambiano l'email o i metodi di accesso o l'account è
cancellato. Pagina e azioni sono **bloccate mentre si usa l'app al posto di un altro**
(DEC-167, `middleware.BLOCCATE`), confermato il 03/11.

#### N.48 — Dall'avatar alla scheda della persona ⏳

Cliccando sull'avatar accanto a un nome (solo sull'avatar) si apre la scheda della persona o del
genitore. Deciso il 03/11: **lo dice il server**: ogni elenco di persone porta, per ognuna, se
chi guarda può aprirne la scheda (dalla policy); solo allora l'avatar (`components/Avatar.vue`) è
cliccabile. Il server ricontrolla comunque all'apertura.

#### N.49 — PDF degli incarichi: «NUOVO CENSITO» al posto del codice provvisorio ⏳

Nell'elenco degli incarichi in PDF (`organizzazione/elenco_incarichi.py`, DEC-284), per i capi con
codice socio provvisorio (`9…`, nuovi iscritti, DEC-120) al posto del codice si scrive «NUOVO
CENSITO».

### Fatto nel giro del 03/11

Il maintainer ha dato il via il 03/11. Ordine: N.25 con N.22 (stesso codice), N.21, N.20,
N.24, N.23. Un commit per voce; manuale e schermate si aggiornano con ogni voce.

#### N.25 — «A disposizione» diviso in due incarichi ✅ 03/11

Rif. DEC-165, DEC-284, DEC-293 (nell'analisi dal 03/11). Fatto il 03/11 con test; pagina e PDF visti con le schermate del manuale. Nominare uno dei due servizi chiude da sé un «a disposizione» ancora in corso.

Richiesta del maintainer (03/11): «Servizio di supporto al gruppo» e «Servizio di
supporto all'azione educativa», veri incarichi di Comunità capi; nell'app non danno
poteri diversi da quelli degli altri capi. Deciso il 03/11:

1. sostituiscono «a disposizione», che non si nomina più;
2. gli incarichi «a disposizione» già registrati, in corso e chiusi, e gli anni di
   servizio ricostruiti restano per lo storico; i capigruppo vedono chi lo ha ancora in
   corso e scelgono uno dei due nuovi;
3. stesse regole di oggi: escludono il servizio in un'unità, finiscono da sé quando il
   capo viene assegnato a un'unità, li nominano i capigruppo; un capo ne ha uno solo.

Da toccare: `organizzazione/models.RuoloIncarico` e `Incarico._controlla_servizio`,
`organizzazione/api` (capi senza servizio, nomina, fine automatica), `policy.py`,
`fascicolo` (anni di servizio ricostruiti), `elenco_incarichi`, `GruppoView.vue`,
`StampaIncarichi.vue`, menu, manuale (`gruppo/organizzazione.md`) e schermate.

#### N.22 — Elenco degli incarichi: capo con un solo incarico aggiuntivo ✅ 03/11

Rif. DEC-284. Un capo con solo un incarico aggiuntivo (per esempio tesoriere, nessun
incarico di servizio), nel raggruppamento per unità, resta in Co.Ca. (maintainer, 03/11).
Deciso il 03/11, con N.25: accanto al nome compare «Servizio di supporto al gruppo»,
sempre, anche se quel tipo non è tra quelli scelti per la stampa; solo nel PDF, senza
registrare l'incarico (confermato dal maintainer il 03/11).
`organizzazione/elenco_incarichi._per_unita`, test in `tests/test_elenco_incarichi.py`.

#### N.21 — Lista d'attesa di un maggiorenne ✅ 03/11

Fatto con test (server e componente): la casella non c'è più, l'età decide anche sul server; manuale aggiornato.

Rif. DEC-256…DEC-258, DEC-261. Se chi viene messo in lista è maggiorenne, il modulo non
chiede i dati del genitore (maintainer, 03/11). Oggi `components/ModuloAttesa.vue` mostra
a un maggiorenne la casella «Sono io: sono maggiorenne e mi iscrivo da solo» e, se non la
si spunta, chiede nome e cognome del genitore; come per il modulo di iscrizione (L.4c),
deve deciderlo l'età e non una scelta. Server: `attesa/servizi._applica`.
Deciso il 03/11: le voci già in lista di maggiorenni con il genitore come contatto
restano come sono.

#### N.20 — Percorso scout nel trasferimento del fascicolo ✅ 03/11

Fatto con test: formato del fascicolo versione 2 (la 1 si legge ancora), conteggio nell'esito dell'importazione, manuale e analisi (DEC-287) aggiornati.

Rif. DEC-213, DEC-287. Oggi `fascicolo.trasferimento` non porta con sé i periodi del
percorso scout (`PeriodoPercorso` e i periodi nelle unità del gruppo): vanno nel file
trasferito e, per il gruppo che lo riceve, i periodi nel nostro gruppo diventano periodi
«in un altro gruppo». Deciso il 03/11:

1. chi riceve salta i periodi del fascicolo che ha già (stesso gruppo, anni e ruolo,
   per esempio venuti da BuonaStrada) e aggiunge gli altri;
2. al rientro dall'archivio (DEC-215) i periodi nelle nostre unità si ignorano, perché
   sono già nell'app: tornano solo quelli in altri gruppi e quelli ricostruiti.

#### N.24 — Sblocco con impronta e passkey di sblocco ✅ 03/11 (da provare sul Mac)

Fatto con test: richiesta con `hints: ['client-device']` e `transports: ['internal']`; la passkey che non serve più si segnala al gestore con `signalUnknownCredential` (alla cancellazione dei dati, allo spegnimento e al rifacimento dell'impronta); nome con dispositivo e data; «questo dispositivo» nei messaggi, nelle schermate e nel manuale. Da provare dal maintainer: l'app installata con Chrome sul Mac (se mostra ancora il QR, o un errore, resta il PIN) e se Password di Apple toglie davvero la passkey e cosa mostra del nome.

Rif. DEC-97. Segnalazioni del maintainer del 03/11.

- **App installata con Chrome su Mac**: nella scheda di Chrome «Sblocca con impronta o
  volto» chiede Touch ID; nella stessa app installata come app di Chrome (stesso
  profilo, stessi dati) Chrome mostra solo il QR per usare il telefono, che funziona
  perché la passkey di sblocco del Mac è sincronizzata sull'iPhone dal portachiavi di
  iCloud. In Password di Apple le passkey sono due (una del Mac, una dell'iPhone),
  nessuna nel gestore delle password di Chrome; nel riquadro di Chrome non ci sono altre
  scelte. La richiesta (`sicurezza/biometria.leggiSegreto`) è identica nei due casi:
  sembra un limite di Chrome nella finestra dell'app [da verificare]. Da provare:
  `hints: ['client-device']` e `transports: ['internal']` nella richiesta; se non basta,
  nell'app installata su Mac lasciare il PIN in primo piano.
- **Passkey di sblocco orfane**: ogni volta che i dati del dispositivo vengono cancellati
  (uscita, scadenza, revoca, altro account: `cassaforte.cancella`) il nuovo accesso crea
  PIN e passkey nuovi, come vuole DEC-97, ma la passkey vecchia resta nel gestore delle
  password (Password di Apple, Google…); lo stesso quando si spegne l'impronta in
  Dispositivi (`disattivaBiometria`). Da fare: (1) prima di dimenticare l'id della
  credenziale, chiedere al gestore di toglierla con
  `PublicKeyCredential.signalUnknownCredential({ rpId, credentialId })`, dove c'è
  (supporto di Chrome e Safari [da verificare]; dove manca resta com'è); (2) nome della
  passkey riconoscibile in Password di Apple (oggi mostra solo l'email, anche se
  `displayName` è «Sblocco QdC — email»): verificare cosa mostra Apple e aggiungere
  dispositivo e data.
- **«Questo telefono»**: la schermata «App bloccata» lo dice anche su un computer.
  Deciso il 03/11: «questo dispositivo» in tutti i messaggi della protezione dei dati e
  nel manuale dove li cita.

#### N.23 — Avvio con systemd e aggiornamento ✅ 03/11 (servizio da provare su Linux)

Fatto: `scripts/installa-servizio.sh`, `scripts/aggiorna.sh`, comando `manage.py manutenzione` (con test), guida di installazione (installazione, aggiornamenti, controlli) e capitolo dell'amministratore tecnico; DEC-292 nell'analisi. `aggiorna.sh` provato davvero con Podman su una copia di prova: da v1.4.0, aggiornamento riuscito, versione che non si costruisce, versione che non parte (torna indietro e toglie la manutenzione) e versione che cambia il database e non parte (lascia la manutenzione e indica il backup; ripristino della guida eseguito, l'app riparte). Il servizio systemd non si può provare su un Mac: file del servizio generato e controllato a vista; da provare su un server Linux (Docker e Podman), anche `systemctl restart` dentro `aggiorna.sh`.

Rif. nuovo DEC-292 nell'analisi. Richiesta del maintainer (03/11): uno script che
installa un servizio per avviare l'app con `systemctl` (start, stop, restart, status,
avvio al boot), e un modo per aggiornarla quando gira come servizio. Oggi i container
ripartono con `restart: unless-stopped` e, con Podman, con `podman-restart.service`;
l'aggiornamento è a mano (`docs/installazione/aggiornamenti.md`: backup, `git checkout`
del tag, `docker compose up -d --build`). Deciso il 03/11:

1. vale per Docker e per Podman, lo script capisce quale c'è;
2. servizio di sistema (`/etc/systemd/system`, con `User=` l'utente che gestisce l'app,
   parte al boot), installato con sudo;
3. aggiornamento con un comando manuale, `scripts/aggiorna.sh` con la versione (senza,
   l'ultimo tag vX.Y.Z dopo `git fetch --tags`, senza chiamate a GitHub): manutenzione
   messa dallo script (serve un comando di gestione), backup, avviso se cambia
   `.env.example`, checkout del tag, build, restart del servizio, controllo di
   `/api/v1/salute`, manutenzione tolta quando l'app risponde;
4. se dopo l'aggiornamento l'app non risponde, lo script rimette da solo la versione di
   prima e, se le migrazioni hanno già cambiato il database, dice di ripristinarlo dal
   backup appena fatto;
5. documentazione: nella guida di installazione le pagine del servizio systemd
   (installazione, comandi `systemctl`, controlli) e dell'aggiornamento con lo script
   (`aggiornamenti.md`, `installazione.md`, `controlli.md`); nel manuale d'uso, capitolo
   dell'amministratore tecnico (`docs/manuale/gruppo/amministratore.md`), come si
   aggiorna l'app: dove leggere le note della versione, la manutenzione,
   `scripts/aggiorna.sh`, cosa fare se torna alla versione di prima.

### Da decidere

| Punto | Rif. |
| --- | --- |
| Revoca dispositivi e idempotenza solo con sessione browser (servirà per l'app negli store) | DEC-105 |

### Da provare

Sviluppato e coperto dai test, manca la prova vera.

| Cosa | Chi | Rif. |
| --- | --- | --- |
| Accesso con Google e Apple su account veri (passkey e impronta provate dal maintainer con la 1.6.0, 03/11) | maintainer | DEC-21, DEC-22 |
| Banner per installare l'app su un iPhone e un Android veri | maintainer | N.15 |
| Servizio systemd su un server Linux (Docker e Podman) e `scripts/aggiorna.sh` con il servizio | chi installa | N.23 |
| Eventi e presenze (fase 3) nel browser | sviluppo | fase 3 |
| Cancellare o archiviare un'unità nel browser | sviluppo | I.2 |
| Interruttori delle email e server SMTP dalle Impostazioni nel browser | sviluppo | E.1, E.2 |
| Caricamento e verifica degli allegati della scheda sanitaria nel browser | sviluppo | N.11 |

### All'installazione

| Attività | Chi | Rif. |
| --- | --- | --- |
| In produzione, programmare i comandi giornalieri: esempio pronto in [deploy/cron/qdc.crontab](deploy/cron/qdc.crontab) | chi installa | fase 1 |
| Collegare il Drive condiviso del gruppo per l'archivio (account di servizio, cartella, chiave `QDC_IMPRONTA_CHIAVE` da conservare: vedi README) e provare un'archiviazione vera e il caricamento degli allegati sanitari | chi installa | N.11, N.13 |
| Collegare la casella Gmail con l'accesso Google | chi installa | E.4 |

### Rimandati

| Cosa | Rif. |
| --- | --- |
| App negli store (Capacitor, fase 7): in standby, prima un prototipo per la regola Apple 4.2 | DEC-105 |
| Microsoft 365 con OAuth (Graph): si sente prima AGESCI per il tenant istituzionale | E.3, DEC-277 |

### Appunti per il manuale

Argomenti da spiegare bene ai capi, perché non sono chiari a tutti:

- **Regole sul rapporto con il minore** (DEC-43, DEC-199): cosa sono (le indicazioni
  che i genitori scrivono sul modulo sanitario per i minorenni, per esempio dopo una
  separazione: chi può riprendere il ragazzo all'uscita, a chi non dare informazioni,
  provvedimenti del giudice), perché le leggono solo i capi, che valgono finché i
  genitori non danno nuove indicazioni scritte, dove si trovano al campo anche senza rete.

## Fasi

La precedenza va alla PWA: ogni fase si completa sulla PWA. L'app per gli store è in
standby: si valuterà più avanti se realizzarla (maintainer, 29/10/2026).

| # | Fase | Stato | Note |
| --- | --- | --- | --- |
| 1 | Fondamenta | ✅ | vedi dettaglio sotto; provata nel browser il 29/10/2026; restano le prove in "Da provare" e "All'installazione" |
| 2 | Quote e cassa | ✅ | quote, pagamenti, ricevute, prima nota e rendiconto; restano per la fase 3 autofinanziamento, budget dei campi e quote BuonaCaccia |
| 3 | Eventi e presenze | ✅ | eventi, presenze, quote a rate, calendario, email, autofinanziamento e budget dei campi, eventi su BuonaCaccia (DEC-158…DEC-164, fatti il 30/10; da provare nel browser) |
| 4 | Progressione Personale | ✅ | a blocchi (dettaglio sotto): E/G, passaggi, R/S, L/C, più le scelte confermate il 30/10 (DEC-186…DEC-190). Riferimento: [specifica PP v1.0](docs/analisi/specifica-pp.md) |
| 5 | Fascicolo completo | ✅ | a blocchi (dettaglio sotto): scheda medica con stampa, note e regole, fascicolo del ragazzo e dei capi, fine anno e archivio |
| 6 | Dopo | ✅ | a blocchi: 6.1 bacheca ✅ (DEC-218…DEC-220, provata nel browser il 30/10), 6.2 estratto conto ✅ (DEC-221…DEC-224, provato nel browser il 30/10 con un estratto sintetico; il file vero della banca si legge), 6.3 Carta di clan ✅ (DEC-227…DEC-229, provata nel browser il 30/10). Note: estratto conto (importazione dei movimenti della banca e abbinamento a quote e versamenti: note sul formato in [docs/analisi/estratto-conto-banca.md](docs/analisi/estratto-conto-banca.md)), Carta di clan |
| 7 | App negli store (Capacitor) | 💤 | in standby: si valuterà se realizzarla; DEC-105; prima un prototipo per la regola Apple 4.2 |
| 8 | Realizzazione documentazione di uso | ✅ | manuale d'uso ✅ 31/10 per tutti i profili (genitore, ragazzo E/G, R/S e L/C, capo, capigruppo, tesorieri, amministratore tecnico), su https://avellino1-qdc.readthedocs.io e in PDF nelle release (v1.0.0 il 31/10, v1.1.0 il 01/11 con manutenzione, sblocchi, pagine di errore, Apache con un pannello e le correzioni su IP del client, nginx dopo una modifica di `.env` e log di axes; v1.2.0 il 02/11 con lo storico da BuonaStrada, l'archiviazione delle unità, le email un gruppo alla volta e il server di posta dalle Impostazioni, anche Gmail con un accesso Google; v1.2.1 il 02/11 con la guida di installazione che chiarisce quale progetto Google Cloud usare per Gmail e per il Drive; v1.3.0 il 02/11 con le note dell'installazione: unità collegate, assistenti ecclesiastici, Soci e Genitori, genitore che diventa capo, squadriglie dei reparti monosessuali, import che non si ferma su un dato sbagliato, controlli dell'installazione e del Drive; v1.4.0 il 03/11 con il banner per installare l'app, i gruppi della Home richiudibili, il calendario, il percorso scout, l'elenco degli incarichi in PDF, la cassa comune delle unità collegate e la scheda sanitaria del gruppo con i suoi allegati; v1.5.0 il 03/11 con i servizi di supporto al posto di «a disposizione», la lista d'attesa di un maggiorenne, il percorso scout nel trasferimento del fascicolo, la passkey di sblocco e il servizio systemd con lo script di aggiornamento; v1.6.0 il 03/11 con il logo AGESCI di base e quello del gruppo scelto all'installazione, e una sola passkey per entrare e sbloccare; v1.6.1 il 03/11 con l'elenco degli incarichi per unità che mostra ogni capo in ogni sezione dei suoi incarichi; v1.7.0 il 03/11 con la professione da BuonaStrada, la regola degli assistenti ecclesiastici, l'ordine delle unità nel PDF degli incarichi e la foto nell'avatar; v1.8.0 il 03/11 con i componenti di Bootstrap 6 del tema 3.0.0a3, il PIN di 6 cifre, l'Organigramma, i modelli delle email in una pagina, la Progressione per unità, i pulsanti accanto ai telefoni e i numeri nella rubrica; v1.9.0 il 03/11 con «Invita nel gruppo»: link, QR code e volantino della lista d'attesa; v1.10.0 il 03/11 con le immagini ridimensionabili, l'allineamento e l'HTML nell'editor di testo, le novità mostrate dallo script di aggiornamento e Node 26); guida di installazione (https://qdc-installazione.readthedocs.io) riletta con il maintainer il 01/11; ripristino da un backup scritto e provato il 01/11 (8.7). Dettaglio dei blocchi sotto; analisi: [docs/analisi/manuali.md](docs/analisi/manuali.md) (DEC-230…DEC-239) |

## Storico dei lavori

Tutto quello che è stato fatto, per blocchi; i punti ancora aperti sono in cima.

### 1. Chiudere la fase 1

| Attività | Chi | Stato |
| --- | --- | --- |
| Confermare le scelte segnate `[da verificare]` (29/10): dati obbligatori per BuonaStrada, promemoria, sospensione, chi corregge cosa (ora DEC-124, DEC-125, DEC-129, DEC-130) | maintainer | ✅ applicate |
| Riportare nell'analisi le decisioni del 28 e 29/10 (DEC-110…DEC-136) | sviluppo | ✅ 29/10 |
| Avviso nella pagina dell'unità finché non ha un nome (le unità importate nascono senza); unità mostrate come "Tipo Nome (Codice)" | sviluppo | ✅ |
| Prove nel browser: scarto di una correzione, cancellazione per un diritto GDPR, avvisi dei 18 anni, eccezioni sulla squadriglia, sospensione di un'iscrizione, uso senza server (copia cifrata) | sviluppo | ✅ 29/10 |

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
| N.4b | Editor con tabelle e immagini; piè di pagina comune delle email, con immagini, nelle email scelte (tutte di base), con la sua versione solo testo ricavata e modificabile; immagini incorporate nelle email (scelte del 31/10) | DEC-250 | ✅ provato nel browser il 31/10 (logo e tabella nel piè di pagina, email con l'immagine incorporata) |
| N.5 | Manuale: rigenerare le schermate e rivedere i passi dei capitoli già scritti (introduzione, genitore) per la nuova navigazione; nuove sezioni: come ci si muove (Home, menu laterale, menu del profilo, percorso), avviso sui cookie e privacy policy, pagare con bonifico o PayPal e segnalarlo, nuova richiesta di iscrizione con «Calcola» | DEC-238 | ✅ 31/10 (tutte le schermate rifatte) |

### Lista d'attesa (prima di continuare il manuale)

Richiesta del maintainer del 31/10/2026: la lista d'attesa di chi vuole entrare nel gruppo,
con la sua sezione del manuale. Decisioni nell'analisi quando confermate.

| # | Attività | Rif. | Stato |
| --- | --- | --- | --- |
| L.1 | Analisi: dati, chi vede e gestisce, conferma dell'email, promemoria dei due anni, età minime e massime delle unità, privacy | DEC-256…DEC-263 | ✅ 31/10 |
| L.2 | Iscrizione pubblica alla lista (genitore o maggiorenne, senza account), email di conferma con il link per modificare o cancellarsi, link ritrovabile con l'email; inserimento da parte di un capo | DEC-256…DEC-258 | ✅ provato nel browser il 31/10 |
| L.3 | Vista dei capi: per età nell'anno in corso e nel successivo, branca e unità consigliate (età minime e massime per unità), contattato / da contattare e per quale unità | DEC-259…DEC-261 | ✅ provato nel browser il 31/10 |
| L.4 | Iscrizione: l'unità scelta, il link al genitore (o al maggiorenne) per i dati dell'iscrizione, che prosegue come l'iscrizione dall'app (DEC-120…DEC-127) | DEC-261 | ✅ provato nel browser il 31/10 |
| L.4b | Il modulo di iscrizione con codice chiede subito il sesso del ragazzo e, per un minore, i genitori o il tutore con la responsabilità genitoriale (uno o due) con telefono ed email; dalla lista d'attesa arrivano già compilati (maintainer, 31/10) | DEC-264 | ✅ provato nel browser il 31/10 |
| L.4c | Modulo di iscrizione: genitore o «me stesso» lo decide l'età (maggiorenne si iscrive da sé), non una scelta; un link personale dalla lista vale solo per quella persona (nome, cognome e data di nascita bloccati, controllati anche dal server) (maintainer, 31/10) | DEC-261, DEC-121 | ✅ provato nel browser il 31/10 |
| L.5 | Promemoria dei due anni (contati da quando si raggiunge l'età minima di un'unità del gruppo), uscita dopo 30 giorni senza risposta | DEC-262, DEC-263 | ✅ coperto dai test (comando giornaliero) |
| L.6 | Manuale: la sezione della lista d'attesa (famiglie e capi) | DEC-238 | ✅ 31/10: famiglie nel capitolo del genitore (voce di prova con link fisso nei dati del manuale), capi nella parte del capo (8.5a) |

### Privacy policy, termini e cookie (in questa sessione, dopo la lista d'attesa)

Richiesta del maintainer del 31/10/2026.

| # | Attività | Rif. | Stato |
| --- | --- | --- | --- |
| P.1 | Privacy policy: pagina pubblica con un testo di base precompilato, che capigruppo e amministratore tecnico modificano con l'editor nelle Impostazioni; link nel piè di pagina e dal modulo della lista d'attesa | DEC-266 | ✅ provato nel browser il 31/10 |
| P.2 | Termini e condizioni: come la privacy policy | DEC-266 | ✅ provato nel browser il 31/10 |
| P.3 | Cookie banner solo informativo (l'app usa solo cookie tecnici): «Ho capito» ricordato nel browser, unica eccezione alla regola sui dati in chiaro; ricompare se la privacy policy cambia. Privacy policy e termini pubblicati e linkati, senza accettazione salvata (scelte del 31/10) | DEC-266 | ✅ provato nel browser il 31/10 |

### Calcolo del codice fiscale (richiesta del 31/10)

| # | Attività | Rif. | Stato |
| --- | --- | --- | --- |
| C.1 | Ovunque si scrive un codice fiscale: pulsante che lo calcola da nome, cognome, sesso, data e luogo di nascita e lo propone (chi lo inserisce verifica). Serve l'elenco dei codici dei comuni e degli stati esteri (fonte ISTAT, scelta del 31/10: l'elenco dei comuni c'è; quello degli stati esteri ha i link ISTAT rotti, da chiedere al maintainer) | DEC-265 | ✅ provato nel browser il 31/10 per i comuni; 💤 stati esteri: serve il file ISTAT dal portale SITUAS; rimandati dal maintainer il 02/11 |

### 8. Fase 8 — Documentazione di uso

Un commit per blocco; le schermate vengono sempre da `mise run docs:schermate`.

| # | Attività | Rif. | Stato |
| --- | --- | --- | --- |
| 8.1 | Impianto, introduzione, accesso e protezione del telefono | DEC-230…DEC-239 | ✅ 30/10 |
| 8.2 | Il resto della parte genitore, riallineata il 31/10 alla nuova navigazione | DEC-233, DEC-238 | ✅ 31/10 |
| 8.3 | Genitore: iscrizioni agli eventi BuonaCaccia (scheda, foto, liberatoria, quota); nei dati di prova un evento BuonaCaccia con l'iscrizione di Giulia | DEC-158…DEC-163, DEC-168 | ✅ 31/10 |
| 8.4 | Parte ragazzo, comune ed E/G: accesso, scheda (e cosa cambia a 18 anni), Sentiero E/G (proporre mete e impegni, pronto per la verifica), capo squadriglia (telefoni, note, imprese), eventi e privacy; nei dati di prova un impegno e una specialità di Giulia in corso | DEC-237 | ✅ 31/10 |
| 8.4b | Parte ragazzo, R/S: Carta di clan (proporre una versione), obiettivi, passi, Punto della Strada con la parte riservata; nei dati di prova la strada di Chiara (Carta di clan in vigore e firmata, obiettivo, servizio, Punto della Strada) | DEC-179…DEC-181, DEC-227…DEC-229 | ✅ 31/10 |
| 8.4c | Parte ragazzo, L/C: testo semplice con le parole dell'ambientazione (bosco per il cerchio di prova), da rileggere con lo staff L/C; nei dati di prova la stagione del cerchio, un volo e una specialità di Sofia; bozza scritta il 31/10, segnata `[da verificare]`, da far rileggere allo staff L/C; corretti «Nuovo volo» e la descrizione della Progressione L/C nella Home | DEC-182…DEC-185, DEC-237 | ✅ 31/10, approvato dal maintainer |
| 8.5a | Parte capo, blocco 1: chi sei, accesso e uso senza rete, l'unità (membri, squadriglie, eccezioni, incarichi, età), persone (scheda, correzioni, inviti, foto, codice fiscale), lista d'attesa (L.6) e richieste di iscrizione, al campo (regole sul rapporto con il minore), scheda sanitaria, note; nei dati di prova una richiesta di iscrizione da accogliere, le regole su Luca e una nota di staff | DEC-233, DEC-238 | ✅ 31/10 |
| 8.5b | Parte capo, blocco 2: eventi e presenze (anche offline), iscrizioni BuonaCaccia, Progressione per branca, passaggi | DEC-233, DEC-238 | ✅ 31/10 |
| 8.5c | Parte capo, blocco 3: fascicolo dell'anno e del capo, bacheca, le mie spese, usare l'app al posto di un ragazzo o di un genitore | DEC-233, DEC-238 | ✅ 31/10 |
| 8.7 | Guida di installazione, progetto Read the Docs a parte (`docs/installazione/`): requisiti, installazione con Docker e reverse proxy, posta, primo avvio (amministratore tecnico, importazione, primo capogruppo), lavori giornalieri, Drive per l'archivio e chiave per i rientri, accesso con Google e Apple, server di prova con Mailpit, backup, aggiornamenti, sicurezza | DEC-230, DEC-231 | ✅ 31/10, riletta con il maintainer il 01/11 (versioni rilasciate al posto di main, chiave dell'impronta generata dallo script, backup notturno nel cron, Podman al riavvio, primo accesso con il codice via email, segnalazioni di sicurezza private su GitHub con `SECURITY.md`); ripristino da un backup ✅ 01/11, provato su una copia di produzione locale (volumi cancellati, database e file caricati tornati; ora `backup-db.sh` salva anche i file caricati); Google e Apple: passi di configurazione delle due piattaforme (maintainer, 31/10) |
| 8.R | Due progetti Read the Docs separati sullo stesso account (maintainer, 31/10): il manuale d'uso nella sua cartella Sphinx con il suo `.readthedocs.yaml`; la guida di installazione avrà la sua; in Read the Docs, nelle impostazioni avanzate del progetto, va indicato `docs/manuale/.readthedocs.yaml` | DEC-231 | ✅ 31/10: https://avellino1-qdc.readthedocs.io (manuale d'uso) e https://qdc-installazione.readthedocs.io (installazione), creati dal maintainer con Claude, ognuno con il suo webhook GitHub (integrazione «Webhook per GitHub» su Read the Docs, webhook nel repository) che li ricostruisce a ogni push e tag; prima release v1.0.0 con il PDF del manuale |
| 8.6a | Parte capogruppo: importazione da BuonaStrada e differenze, correzioni da inoltrare, iscrizioni da inserire e modulistica, unità e incarichi, eccezioni sulle squadriglie, dispositivi, richieste privacy, fine anno e archivio | DEC-233, DEC-238 | ✅ 31/10 |
| 8.6b | Impostazioni (sito, stampe, pagamenti), modelli delle email, privacy policy e termini; amministratore tecnico (pannello di amministrazione, modalità di prova delle email) | DEC-233, DEC-238 | ✅ 31/10 |
| 8.6c | Tesorieri: quote, agevolazioni, pagamenti e ricevute, pagamenti da verificare, prima nota e rendiconto, estratto conto | DEC-233, DEC-238 | ✅ 31/10 |
| 8.8 | Apache con un virtual host già creato da un pannello (il caso reale è Virtualmin, ma vale per qualunque pannello): `configure-prod.sh --proxy apache-vhost` genera solo le direttive da aggiungere al virtual host HTTPS che c'è già, certificato e porta 80 restano al pannello; pagina della guida di installazione (richiesta del maintainer, 01/11) | DEC-231 | ✅ 01/11, provato con un Apache in container configurato come un sito di Virtualmin (app, API, accesso con CSRF, `/.well-known/` lasciato al pannello, redirect); percorso del menu di Virtualmin confermato dal maintainer (01/11). Trovati e corretti nella prova: l'IP del client per axes e auditlog (prima era sempre quello dell'nginx del container) e l'nginx di `app` che restava sull'indirizzo vecchio di `web` dopo una modifica di `.env` |

### Manutenzione e sblocchi (01/11)

Richiesta del maintainer del 01/11; decisioni nell'analisi come DEC-268, DEC-269.

| # | Attività | Rif. | Stato |
| --- | --- | --- | --- |
| A.1 | Manutenzione: interruttore e messaggio nelle Impostazioni per l'amministratore tecnico; tutti gli altri fermati (anche le pagine pubbliche, tranne accesso, privacy e termini), con la coda offline al sicuro; barra per l'amministratore tecnico | DEC-268 | ✅ 01/11 (provato nel browser con le schermate del manuale: accensione dalla pagina, genitore già dentro fermato, elenco dei blocchi) |
| A.2 | Sblocco degli accessi: blocchi in corso per account e per indirizzo, sblocco del singolo blocco | DEC-269 | ✅ 01/11 (provato nel browser con le schermate del manuale: accensione dalla pagina, genitore già dentro fermato, elenco dei blocchi) |
| A.3 | Manuale: le due funzioni nella parte dell'amministratore tecnico | DEC-238 | ✅ 01/11 |
| A.4 | Pagine di errore nel tema del sito, con messaggi che spiegano cosa fare senza dettagli tecnici: 40x e 50x nella PWA, nelle pagine di Django fuori dalle API e nell'nginx del container `app` quando Django non risponde (richiesta del maintainer, 01/11) | DEC-270 | ✅ 01/11: provato con i container veri (la 503 della manutenzione passa intatta da nginx, Apache e nginx sull'host; con Django o con tutto il container spenti si vede la pagina dell'app) e nel browser (pagina non trovata della PWA) |

### Primo import con lo storico (02/11)

Richiesta del maintainer del 02/11, prima dell'installazione per l'Avellino 1; decisioni
nell'analisi come DEC-271…DEC-275. Il file da importare si prepara in `ignored/` (mai
nel repository).

| # | Attività | Rif. | Stato |
| --- | --- | --- | --- |
| I.1 | Import con più anni: solo i soci attivi nell'ultimo anno, con i periodi passati chiusi nelle unità; righe di altri gruppi saltate; stato I come R; unità solo del passato create disattivate; date dei genitori senza zeri e genitori nati all'estero (export 2027) | DEC-271…DEC-273 | ✅ 02/11 (provato con il file vero su un database di prova: 52 soci, 65 genitori, 82 periodi passati, Branco L1 e Reparti O1/O2 disattivati) |
| I.4 | Chi si è appena disiscritto entra sospeso, con lo storico chiuso e i genitori; dopo due anni l'archiviazione | DEC-274 | ✅ 02/11 (provato con il file vero: 14 sospesi, 38 attivi) |
| I.2 | Cancellare un'unità disattivata e vuota (creata per errore); archiviare un'unità con soli archiviati nello storico, ripristinata al rientro | DEC-273, DEC-275 | ✅ 02/11 (test; non ancora provato nel browser) |
| I.3 | File unico per l'Avellino 1: storico + 2027 scelto dal maintainer + capo da altro gruppo + due capi riattivati | DEC-271, DEC-274 | ✅ 02/11: `ignored/primoimport/import-iniziale.csv` dalle conferme del maintainer (38 confermati, 14 appena usciti con i dati della riga 2027) |

### Email un po' alla volta e server di posta (02/11)

Richiesta del maintainer del 02/11, per presentare l'app prima ai capi, poi a genitori e
ragazzi; decisioni nell'analisi come DEC-276…DEC-278.

| # | Attività | Rif. | Stato |
| --- | --- | --- | --- |
| E.1 | Interruttori Capi, Genitori, Ragazzi: email scartate per i gruppi spenti, con il conteggio; sempre consegnati accesso, inviti, iscrizione e lista d'attesa | DEC-276 | ✅ 02/11 (test; non ancora provato nel browser) |
| E.2 | Server SMTP dalle Impostazioni (amministratore tecnico), password cifrata, email di prova | DEC-277 | ✅ 02/11 (test; non ancora provato nel browser) |
| E.4 | Gmail con accesso Google una tantum (OAuth, API di Gmail); guida: client OAuth in Google Cloud e relay SMTP di Google | DEC-278 | ✅ 02/11 (test con Google simulato; il collegamento vero si prova all'installazione) |

### Note dall'installazione dell'Avellino 1 (02/11)

Annotate dal maintainer durante l'installazione; installazione finita il 02/11, si sviluppano ora, un commit per nota. Le note N.20…N.25 sono in cima, fra i punti aperti.

| # | Attività | Rif. | Stato |
| --- | --- | --- | --- |
| N.1 | `scripts/configure-prod.sh`: `--port` esiste già, ma lo script non controlla che la porta sia libera; con `nginx-host`, `apache-host` e `apache-vhost` controllarla e, se occupata, proporre la prima libera | — | ✅ 02/11 |
| N.2 | Guida di installazione: una sezione di controlli per verificare l'installazione, passo per passo. Porta dei container libera (`ss -ltnp`); moduli di Apache (`apachectl -M`); pagina di errore leggibile da Apache (`sudo -u www-data test -r …/errori/50x.html`); container in salute (`docker compose ps`); l'app risponde in locale (`curl -sI http://127.0.0.1:8080/`) e dal dominio con una GET (`curl -s https://…/api/v1/salute` → `{"stato": "ok"}`: con `curl -I`, cioè HEAD, risponde 405); posta in `.env` prima di `createsuperuser`, se no il codice del primo accesso non arriva | — | ✅ 02/11 |
| N.3 | Guida di installazione, cose emerse installando: un solo utente gestisce l'app (`docker compose`, cron, backup) e deve stare nel gruppo `docker` (che equivale a root) o essere root; se sul server ci sono sia Docker sia Podman, usarne uno solo; con Virtualmin, togliere le direttive di proxy già presenti nel virtual host (un `ProxyPass /` verso un'altra porta messo prima vince, e le righe `X-Forwarded-For`) e ricontrollarle quando il pannello riscrive il file | — | ✅ 02/11 |
| N.4 | Import da BuonaStrada: un dato non valido non deve fermare l'import (oggi va in errore su PostgreSQL). Il primo export vero aveva un'email nella colonna del cellulare (34 caratteri, il campo ne tiene 30) e il codice fiscale di un genitore di 17 caratteri. Il dato viene scartato con un avviso non bloccante, nell'anteprima e dopo l'applicazione, così chi importa chiede il dato corretto e lo aggiorna su BuonaStrada. Casi nell'export sintetico, con test; i test locali girano su SQLite, che non controlla le lunghezze | DEC-29 |✅ 02/11 |
| N.5 | Guida di installazione, «Primo avvio», passo 3: dice che il primo capogruppo si può nominare anche dall'app (**Incarichi di gruppo**), ma non che l'amministratore tecnico dall'app non può invitarlo (gli inviti partono solo da capigruppo e capi unità): l'invito va comunque fatto con `crea_invito`, senza `--capogruppo` se l'incarico è già registrato | DEC-21 | ✅ 02/11 |
| N.6 | Modulo dell'unità (`components/ModuloUnita.vue`): «Ambientazione» solo per il tipo Branco/Cerchio (Giungla per il branco, Bosco per il cerchio). «Collegata a» resta per tutti i tipi (serve anche alle unità monosessuali parallele, DEC-36), ma il menu propone solo le unità attive e non ancora collegate, non quelle archiviate o non attive (correzione del maintainer del 02/11). Il collegamento è reciproco: collegare A a B collega anche B ad A, e togliere o cambiare il collegamento da una parte lo aggiorna anche dall'altra (maintainer, 02/11). Le unità si collegano solo a coppie: se A o B è già collegata a un'altra unità, il collegamento viene rifiutato con un messaggio che spiega di togliere prima quello esistente, esplicitamente (maintainer, 02/11). Lo staff di ciascuna di due unità collegate vede e modifica la Progressione Personale di tutti i ragazzi di entrambe (maintainer, 02/11); anzi, per i permessi lo staff delle unità collegate è sempre congiunto (maintainer, 02/11: `policy._unita_servite`); cassa e tesoriere di unità restano separati finché non si uniscono le casse (N.14). Oggi il collegamento è solo una nota (DEC-36) e `policy.py` non lo legge: serve un nuovo DEC nell'analisi, una funzione nella policy e i test per ogni ruolo. Su BuonaStrada sono tutti Branco/Cerchio (export di tutta la zona del 30/10), quindi l'ambientazione serve e DEC-225 resta com'è | DEC-36, DEC-225, DEC-279 | ✅ 02/11 |
| N.7 | Incarichi: manca l'**Assistente Ecclesiastico di gruppo**, incarico di gruppo con gli stessi poteri di un capogruppo; aggiungere anche l'**Assistente Ecclesiastico di unità**, incarico di servizio in un'unità. Oggi l'AE conta solo come capo (DEC-09). Deciso dal maintainer il 02/11: l'AE di gruppo ha i poteri di un capogruppo ovunque (ogni controllo da capogruppo della policy, anche chiusura dell'anno, diritti e impersonazione) e lo nominano i capigruppo; l'AE di unità vale come lo staff e lo nominano capo unità e capigruppo. BuonaStrada non esporta gli incarichi: si inseriscono nell'app | DEC-09, DEC-10, DEC-165, DEC-281 | ✅ 02/11 |
| N.8 | Un genitore che diventa capo (capita spesso): una funzione apposta che precompila la richiesta di iscrizione in Co.Ca. con i dati che l'app ha già di lui (anagrafica, contatti, codice fiscale), così completa solo quello che manca per diventare socio. Oggi l'iscrizione con un codice per la Co.Ca. c'è (`apps/iscrizioni`), ma riparte da zero; l'import riconosce già il genitore per codice fiscale quando arriva da BuonaStrada come socio. Deciso dal maintainer il 02/11: la avvia il capogruppo dalla scheda del genitore; si precompilano tutti i dati che si ricavano dalla scheda del genitore | DEC-120…DEC-127, DEC-282 | ✅ 02/11 |
| N.10 | **Percorso scout** di ogni socio attivo, nella sua scheda: tutti i periodi da ragazzo e da capo, con unità e anni, e l'anno di ingresso nel gruppo. I periodi importati da BuonaStrada ci sono già nel database (DEC-271 li prevede anche per «percorso nelle unità»), ma nessuna pagina li mostra: la scheda ha solo le unità attuali, il fascicolo del capo solo gli anni in Co.Ca. Va mostrato anche il percorso **in altri gruppi**, quando BuonaStrada ce lo dà (per esempio la capo arrivata dal Montoro 1). Nel fascicolo del capo, «Anni di servizio» dice anche **di quale gruppo** era la Co.Ca. o l'unità. Deciso dal maintainer il 02/11: gli anni in altri gruppi, quando l'export li ha, si importano (cambia DEC-271, «le righe di altri gruppi non si importano»: nuovo DEC nell'analisi), conservati con gruppo e unità come testo, senza creare unità di altri gruppi nell'app; il percorso lo vedono i capi, la persona stessa e i genitori di un minore; poi il 02/11: un periodo per riga; il percorso si completa a mano (il capo per sé e i capigruppo, segnato come ricostruito); gli anni di servizio ricostruiti indicano il gruppo (testo libero, vuoto = il nostro) | DEC-271, DEC-206, DEC-207, DEC-287 | ✅ 02/11 (`anagrafica/percorso.py`, `PeriodoPercorso`, import degli anni in altri gruppi, gruppo negli anni di servizio, `PercorsoScout.vue`, con test); visto nel browser con le schermate; il trasferimento del fascicolo a un altro gruppo non porta ancora i periodi del percorso |
| N.11 | **Scheda sanitaria del gruppo** al posto di quella AGESCI (modello in `ignored/scheda_sanitaria_scout.pdf`; quella AGESCI è solo un'indicazione, questa è più completa). Da aggiungere: genitori con cellulare e telefono fisso o di lavoro, contatto di fiducia; medico con nome e telefono separati; anamnesi con quattro domande sì/no e dettaglio (patologie rilevanti, interventi o traumi recenti, disturbi del sonno, occhiali, lenti o apparecchio ortodontico); allergie in cinque categorie, ognuna con sì/no (farmaci, alimentari, intolleranze alimentari, punture d'insetto, ambientali); farmaco salvavita sì/no; data dell'ultimo richiamo antitetanico (oggi solo sì/no); autorizzazione ai farmaci da banco sì/no; allegati (tessera sanitaria o codice fiscale, documento d'identità del ragazzo e del genitore che firma). Decisioni del maintainer del 02/11: (1) l'app produce la scheda già compilata, su carta intestata del gruppo, da firmare e caricare; (2) farmaco salvavita e autorizzazione ai farmaci da banco vanno anche offline sui telefoni dei capi (estende DEC-55, DEC-95); (3) gli allegati si caricano nell'app, un capo li verifica e li salva sul Drive del gruppo (se configurato) o li scarica sul suo computer: quando conferma il salvataggio, vengono cancellati dal server. Ogni lettura nel registro degli accessi. Nuovi DEC nell'analisi prima di svilupparla; (4) anche la scheda firmata caricata segue lo stesso percorso degli allegati: sul server restano i dati e la data della firma, non la scansione; poi il 02/11: allergie con le cinque categorie e un sì/no per categoria; fisso o lavoro nella scheda del genitore; il contatto di fiducia è la reperibilità di oggi; versione per maggiorenni firmata dall'interessato; tessera sanitaria, gruppo sanguigno, altre vaccinazioni e note restano in «Altre informazioni»; testi di dichiarazione e consenso modificabili dalle Impostazioni; nessuna scheda AGESCI da migrare (installazione appena fatta); dopo la cancellazione resta «verificato il … da …» per ogni documento | DEC-48…DEC-55, DEC-95, DEC-101, DEC-192, DEC-289…DEC-291 | ✅ 02/11 in tre blocchi: dati e modulo della scheda del gruppo (fisso del genitore, salvavita e farmaci da banco anche al campo), stampa sul modello del gruppo con i testi di dichiarazione e consenso nelle Impostazioni, allegati e scheda firmata verificati e poi cancellati dal server (`sanitaria/allegati.py`); tutto con test; modulo visto nel browser con le schermate, PDF controllato a vista; caricamento e verifica degli allegati non ancora provati nel browser, il Drive vero si prova all'installazione |
| N.12 | Squadriglie di un reparto monosessuale (`Unita.composizione` maschile o femminile): la squadriglia può essere solo dello stesso sesso del reparto (maintainer, 02/11). Oggi nessun controllo: `crea_squadriglia` e la modifica in `organizzazione/api.py` accettano qualsiasi sesso, e il modulo in `views/UnitaDettaglioView.vue` propone sempre la scelta (con «F» già selezionato). Da fare: il server rifiuta un sesso diverso con un messaggio chiaro, e il modulo, per un reparto monosessuale, imposta il sesso da solo e non lo chiede; test per creazione e modifica. Una squadriglia dell'altro sesso già esistente in un reparto monosessuale viene segnalata con un avviso sulla pagina dell'unità, come quello delle unità senza nome, perché lo staff la corregga (maintainer, 02/11). Nei reparti misti resta tutto com'è | DEC-112, DEC-36, DEC-280 | ✅ 02/11 |
| N.13 | **Controllo della cartella del Drive**: un controllo che verifichi che il Drive condiviso dell'archivio sia impostato bene (credenziali dell'account di servizio, cartella raggiungibile, permesso di scrivere), con un messaggio chiaro su cosa correggere (maintainer, 02/11) | DEC-196, DEC-209…DEC-217 |✅ 02/11: `manage.py controlla_drive`, senza scrivere sul Drive; il caricamento vero resta da provare all'installazione |
| N.14 | **Cassa comune di due unità collegate**: nella pagina di una delle due unità collegate una scelta «casse unite» (si copia nell'altra): da allora una sola cassa e i tesorieri di unità valgono per tutte e due. Si possono dividere di nuovo solo all'inizio di un anno associativo, quando non ci sono ancora movimenti (maintainer, 02/11). Da mettere nell'analisi (nuovo DEC) prima di svilupparla: oggi cassa e tesoriere restano di ogni unità (DEC-279); poi il 02/11: le uniscono e le dividono i capi unità e i capigruppo; resta una sola cassa con i saldi sommati; i movimenti sono della coppia e il rendiconto le mostra insieme | DEC-279, DEC-145…DEC-155, DEC-288 | ✅ 02/11 (`Unita.cassa_comune_dal`, `cassa.servizi.unisci_casse` / `dividi_casse`, permessi dei tesorieri sulla coppia, pulsanti nella pagina dell'unità, con test); i pulsanti non sono ancora stati provati nel browser |
| N.15 | **Banner per installare la PWA** con le istruzioni (maintainer, 02/11). Deciso dal maintainer il 02/11: compare prima e dopo l'accesso, ovunque la PWA si possa installare (Chrome, Edge e Samsung Internet con il pulsante «Installa»; iPhone e iPad, Safari sul Mac e Firefox su Android con le istruzioni); non compare se l'app è già installata e aperta dalla sua icona; si chiude e dopo `QDC_BANNER_INSTALLAZIONE_GIORNI` giorni (di base 14, in `.env`) può ricomparire. Manuale (`docs/manuale/introduzione.md`) e guida di installazione aggiornati | DEC-283 | ✅ 02/11 (`pwa/installazione.ts`, `BannerInstallazione.vue`, con test); da provare su un iPhone e un Android veri; nessuna schermata nel manuale (nel Chrome delle schermate il tasto «Installa» non compare) |
| N.16 | **Export degli incarichi del gruppo in PDF** su carta intestata del gruppo (come le stampe in `core/stampa.py`) (maintainer, 02/11). Si scelgono i **tipi di incarico** da includere (capogruppo, AE di gruppo, capo unità, staff, AE di unità, a disposizione, tesorieri, amministratore) e come raggruppare i capi: **per unità** (chi è «a disposizione» va in Co.Ca.; la Co.Ca. contiene solo i capigruppo e gli AE di gruppo senza incarichi in un'unità, più i capi a disposizione) oppure **per incarico**. Deciso dal maintainer il 02/11: (1) lo fanno solo i capigruppo; (2) per ogni capo codice socio, nome, cognome e livello di formazione capi (`Persona.livello_formazione`, da BuonaStrada), nessun contatto; (3) nel raggruppamento per unità gli incarichi aggiuntivi (tesoriere, amministratore…) compaiono accanto al nome, se il loro tipo è tra quelli scelti; (4) di base gli incarichi in corso oggi, oppure quelli di un anno associativo precedente scelto: di quell'anno valgono solo gli incarichi attivi alla fine dell'anno (30 settembre), non quelli tenuti prima e poi cambiati. Nuovo DEC nell'analisi prima di svilupparla. (5) il livello di formazione è quello di oggi (l'app non ne tiene la storia), anche per un anno passato (confermato dal maintainer il 02/11) | DEC-165, DEC-281, DEC-37, DEC-284 | ✅ 02/11 (`organizzazione/elenco_incarichi.py`, `/gruppo/incarichi/elenco.pdf`, `StampaIncarichi.vue`, con test); pagina vista nel browser con le schermate, PDF controllato a vista |
| N.17 | **Avviso «Capi senza servizio»** in Incarichi di gruppo: un capogruppo senza incarichi in un'unità non va segnalato (maintainer, 02/11). Oggi `organizzazione/api.capi_senza_servizio` esclude solo chi ha un incarico di servizio (unità, AE di gruppo, a disposizione), non i capigruppo | DEC-165 | ✅ 02/11 |
| N.18 | **Home con i gruppi di funzioni richiudibili** (`views/HomeView.vue`, gruppi da `navigazione/menu.gruppiMenu`): ogni gruppo si apre e si chiude toccando il suo titolo e la Bacheca resta sempre visibile (maintainer, 02/11). Deciso dal maintainer il 02/11: (1) al più un gruppo aperto alla volta: aprirne uno chiude gli altri; (2) l'app ricorda quale era aperto l'ultima volta e lo riapre (nel browser, come la chiusura dei banner: solo la chiave del gruppo, nessun dato personale); la prima volta sono tutti chiusi; (3) su un gruppo chiuso il titolo mostra il numero delle cose da fare delle sue voci (i contatori di oggi, sommati). Nuovo DEC nell'analisi e nota in `frontend/CLAUDE.md` fra le eccezioni a `localStorage`; manuale e schermate della Home da aggiornare | DEC-241, DEC-285 | ✅ 02/11, visto nel browser con le schermate del manuale (le scene aprono le voci dai gruppi chiusi) |
| N.19 | **Calendario**, una funzione nuova (maintainer, 02/11): mostra un calendario (mese) e/o, a scelta, l'elenco dei prossimi eventi che riguardano chi è collegato o i suoi figli, e permette di scaricare o abbonarsi al calendario. Oggi c'è già il link personale segreto per abbonarsi (DEC-79, DEC-143: `GET /calendario`, `/calendario/{token}.ics`, rigenerabile; per i capi tre viste: la sua unità, Co.Ca. e unità, tutto il gruppo), in fondo alla pagina **Eventi** (`components/MioCalendario.vue`); non c'è una vista a calendario né lo scaricamento di un file `.ics`. Deciso dal maintainer il 02/11: (1) voce nella Home accanto alla Bacheca, sempre visibile come lei (vedi N.18), e nel menu dentro il gruppo degli eventi; (2) si scarica il file `.ics` di tutti gli eventi e quello del singolo evento (anche dalla sua pagina); il link per abbonarsi passa in questa pagina; (3) un capo sceglie fra le tre viste di DEC-143; (4) la scelta calendario o elenco (e la vista del capo) si ricorda nel browser, come per i gruppi della Home; (5) per ora solo online, l'offline si valuterà poi. Nuovo DEC nell'analisi; manuale e schermate da aggiornare | DEC-79, DEC-143, DEC-286 | ✅ 02/11 (`CalendarioView.vue`, `eventi/calendario.ts`, file `.ics` di tutti gli eventi e del singolo evento, con test); visto nel browser con le schermate |
| N.9 | Separare **Persone** in **Soci** (tutti i censiti: capi e ragazzi) e **Genitori** (`views/PersoneView.vue` e menu): due voci di menu e due pagine, ciascuna con la sua ricerca (maintainer, 02/11) | — |✅ 02/11 |

### Mancanze trovate scrivendo il manuale (31/10)

Richiesta del maintainer del 31/10: correggerle. Un commit per blocco; il manuale si aggiorna con ogni blocco.

| # | Attività | Rif. | Stato |
| --- | --- | --- | --- |
| M.1 | Piccole correzioni: la ricevuta di un pagamento dall'estratto conto parte per email come le altre; l'amministratore tecnico vede «Tutti i dispositivi del gruppo»; descrizione di «Impostazioni» nel menu; percorso in alto nelle pagine dei ragazzi | DEC-84, DEC-222, DEC-23, DEC-244 | ✅ 31/10 (provato nel browser con le schermate: sentiero dei ragazzi, Carta di clan della scolta, passaggi) |
| M.2 | Scheda della persona: registro degli accessi ai dati delicati e foto precedenti, per i capi | DEC-101, DEC-42 | ✅ 31/10 (provato nel browser; nei dati di prova due foto inventate di Giulia) |
| M.3 | Correggere le date di una tappa (inizio, riconoscimento, distintivo) con il motivo | DEC-171…DEC-173 | ✅ 31/10 (provato nel browser) |
| M.4 | Modificare un evento | DEC-75, DEC-79 | ✅ 31/10 (provato nel browser: salvataggio e riapertura) |
| M.5 | Lo staff del reparto delega le riunioni di squadriglia dalla pagina dell'unità (deciso dal maintainer il 31/10) | DEC-267 | ✅ 31/10 (provato nel browser: delega e revoca dallo staff) |
| M.7 | Estratto conto: il nome nella causale pesa di più nella proposta delle quote, così il bonifico per Luca propone le quote di Luca (maintainer, 31/10) | DEC-222 | ✅ 31/10 (provato nel browser con l'estratto di prova) |
| M.6 | Nei dati di prova un estratto conto della banca inventato, per le schermate | DEC-235 | ✅ 31/10 |

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
