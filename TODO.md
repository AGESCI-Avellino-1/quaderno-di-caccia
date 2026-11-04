# TODO — manutenzione

Situazione delle [issue](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues) e delle
[segnalazioni di sicurezza](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/security/advisories)
su GitHub, aggiornata il 04/11/2026 (ultima versione: v1.13.1). Le cose ancora aperte del periodo di
sviluppo sono in [TODO_SVILUPPO.md](TODO_SVILUPPO.md).

## Aperte

| Issue                                                                    | Titolo                                                            | Tipo     | Impatto | Difficoltà | Status |
| ------------------------------------------------------------------------ | ----------------------------------------------------------------- | -------- | ------- | ---------- | ------ |
| [#21](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/21) | Notifiche push sull'app installata                                | Funzione | Medio   | Media      |        |
| [#20](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/20) | Modelli di convocazione e verbali del gruppo su carta intestata   | Funzione | Medio   | Alta       | VAL    |
| [#19](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/19) | Download: documenti del gruppo scaricabili in app                 | Funzione | Basso   | Media      | VAL    |
| [#18](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/18) | Progetto Educativo di Gruppo (PEG): caricamento e storico         | Funzione | Medio   | Media      | VAL    |
| [#17](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/17) | Progetto del capo: inserimento e consultazione da parte della Co.Ca. | Funzione | Basso   | Media      | VAL    |
| [#16](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/16) | Calendario: voce «Tutti i miei eventi» come selezione predefinita | Modifica | Basso   | Bassa      | VAL    |

Nessuna segnalazione di sicurezza aperta.

## Valutazioni

Valutazioni fatte leggendo le issue, i modelli e il codice: nulla è ancora stato sviluppato. Tra
parentesi, dopo ogni domanda, la risposta consigliata. Ordine di sviluppo consigliato: #16, poi #19 e
#18 insieme (il PEG si consulta da Download), poi #17, poi #20.

### #20 Modelli di convocazione e verbali

**Fattibile.** La carta intestata c'è già (`core/stampa.py`), con logo, dati del gruppo, banda e
piede. Rispetto ai modelli mancano la riga «Associazione di Promozione Sociale-APS», «sezione APS»
nel piede e il marchio WAGGGS/WOSM.

**Cose da fare.**

1. Testi dei modelli come quelli delle email: predefiniti nel codice, con i segnaposto. Gli articoli
   citati (4, 6, 14) dipendono dal Regolamento di ogni gruppo.
2. Nel verbale, «Usa un modello» inserisce il testo nell'editor già compilato con ciò che l'app sa:
   gruppo e codice fiscale, data, ora e luogo, anni e date del bilancio, risultato da
   `cassa.servizi.modello_d`, elenco di capi e assistenti ecclesiastici, presidente e segretari se
   già indicati.
3. Il PDF passa da `verbali/stampa.py`: titolo del modello e firme del modello.
4. Convocazione: ordine del giorno a punti scelti, ora di seconda convocazione (campo nuovo su
   `Evento`), PDF su carta intestata che diventa un documento della convocazione, così il flusso
   attuale (allegato all'email e letto nell'app) resta uguale. I punti scelti precompilano il verbale.
5. Test, manuale e dati di prova.

**Differenze dalle decisioni già prese.**

- **Due verbali per una riunione.** Oggi `Verbale.evento` è uno a uno. I modelli del bilancio e della
  Co.Ca. parlano di chiusura di «questa parte» della riunione, quindi sembrano documenti separati
  accanto al verbale ordinario. Servirebbe una riga per modello su ogni riunione, il punto più
  delicato: tocca API, promemoria e copia dei presenti.
- **Firme.** Per la Co.Ca. DEC-324 prevede chi ha scritto, il modello le firme dei presenti e dei Capi
  Gruppo. Il modello del bilancio aggiunge la dichiarazione di conformità dei Capi Gruppo.
- **Presidente.** DEC-326 ne prevede uno e uno o più segretari, i modelli «il/i Presidente/i» e un
  segretario.
- **Dati personali.** Il verbale della Co.Ca. riporta codice fiscale, nascita e residenza dei Capi
  Gruppo. Per DEC-323 lo leggono tutti i capi e il testo resta anche dopo una cancellazione (DEC-328).
  Il precompilato andrebbe generato solo per i capigruppo.

**Da decidere.**

1. Il verbale del bilancio e quello dei Capi Gruppo stanno accanto al verbale ordinario della stessa
   riunione? (Sì.)
2. Firme: si seguono i modelli, solo quando si usano? (Sì.)
3. Più presidenti e il segretario unico: DEC-326 resta com'è e il testo si adatta? (Sì.)
4. Il verbale con i dati dei Capi Gruppo lo leggono tutti i capi, come gli altri della Co.Ca.?
   (Sì: è un atto della Co.Ca. e le letture sono già registrate.)
5. Nessun effetto automatico: né incarichi, né rappresentante legale, né sede del gruppo cambiano
   rendendo definitivo il verbale? (Nessuno, come da issue. Il rappresentante legale resta quello
   dell'importazione, la sede si cambia a mano nei dati del gruppo.)
6. I testi li può modificare il capogruppo, come le email? (Sì.)
7. Campi non compilati: `[…]` nel testo blocca il definitivo? (Sì.)
8. Refusi dei modelli, per esempio la residenza con «CAP [città di nascita]» e «20aa/20aa»: si
   correggono? (Sì.)
9. Si aggiungono alla carta intestata di tutte le stampe la riga APS e il marchio WAGGGS/WOSM? (Sì, se
   il gruppo può usare il marchio.)
10. Serve anche il file Word? (No, solo PDF, come gli altri verbali.)

### #19 Download

**Fattibile.** Nuova app con un documento, i destinatari e la funzione di visibilità in `policy.py`.
Il controllo dei tipi di file c'è già nei verbali (`TIPI`), da spostare in comune. Voce di menu per
tutti, solo online come la Bacheca. Ogni ruolo con i suoi test, manuale compreso.

**Da decidere.**

1. Un capo qualsiasi può caricare per un'unità non sua? (Sì, come chiede la issue; esclusi i capi con
   codice provvisorio.)
2. Chi modifica ed elimina? (Chi ha caricato e i capigruppo, come in Bacheca.)
3. Chi vede tutto? (Chi ha caricato e i capigruppo, per poter gestire.)
4. Scaduto: sparisce soltanto o si cancella il file? (Sparisce per chi legge, resta a chi gestisce per
   rinnovarlo o eliminarlo; cancellazione automatica dopo un anno.)
5. «Anno associativo»: quale? (Quello in corso al caricamento, scade il 30/09; rinnovabile.)
6. Per quanto resta «aggiornato»? (30 giorni: per ogni lettore servirebbe registrare chi ha aperto il
   file.)
7. Dove stanno i file e quanto possono pesare? (Sul server, fino a 20 MB, il limite già impostato.
   Drive solo se serviranno file più grandi.)
8. Genitori di maggiorenni? (Come il calendario: secondo la scelta del figlio, DEC-26.)
9. Email a ogni nuovo documento? (No.)

### #18 PEG

**Fattibile.** Versioni con PDF o testo, l'ultima caricata è in vigore. Etichetta «in redazione» sul
gruppo. Solo i capigruppo scrivono. È il primo file aperto a chi non ha un account: pagina pubblica e
scaricamento senza login, con un limite alle richieste e solo sulla versione in vigore.

**Da decidere.**

1. Una versione caricata per sbaglio? (Il capogruppo può eliminarla o sostituirla, e torna in vigore
   la precedente.)
2. Data di inizio? (Da indicare, proposta oggi; è in vigore da subito.)
3. L'etichetta «in redazione» la vedono anche gli esterni? (Sì.)
4. Pagina pubblica: motori di ricerca? (Link diretto `/peg`, collegato dalla pagina di accesso, senza
   indicizzazione.)
5. Email alle famiglie per un nuovo PEG? (No, eventualmente un avviso in Bacheca.)
6. Dove e quanto pesa? (Sul server, fino a 20 MB. Da controllare sul PEG vero. Al caricamento un
   avviso ricorda che il documento è pubblico.)

### #17 Progetto del capo

**Fattibile.** Sta nel fascicolo del capo (`apps/fascicolo`, `FascicoloCapoView`), con lo stesso
permesso di lettura (DEC-206). Editor e PDF ci sono già: il lettore del testo di `verbali/stampa.py`
va spostato in comune. Va aggiunto a esportazione e cancellazione (`diritti`), archivio e
trasferimento del fascicolo.

**Il PDF incorporato non è gratis.** nginx risponde `X-Frame-Options: DENY` e sui telefoni il browser
non mostra in modo affidabile un PDF dentro una pagina [da verificare su dispositivi veri]. La
strada solida è pdf.js caricato solo quando serve, una dipendenza nuova; l'alternativa senza
dipendenze è aprirlo con la finestra già fatta per #12.

**Da decidere.**

1. Storico? (Sì: versioni con data, l'ultima in vigore, le altre consultabili, senza legarle all'anno
   scout.)
2. Chi modifica oltre al capo? (Nessuno: i capigruppo leggono soltanto.)
3. Carta intestata nel PDF generato? (Sì, costa poco ed è uguale ai verbali.)
4. Offline? (No, come i verbali.)
5. Sta nel fascicolo del capo? (Sì.)
6. PDF incorporato: pdf.js o finestra di #12? (Finestra di #12 per ora: nessuna dipendenza nuova.)
7. Il testo nel registro delle modifiche? (No, come per i verbali.)

### #16 Calendario

**Fattibile, solo sui capi.** Impatto e difficoltà abbassati rispetto alla prima stima. Una vista in
più in `eventi/calendario.py`: inviti propri, eventi dei figli, unità servite e loro squadriglie,
Co.Ca. I link già attivi per abbonarsi non cambiano; DEC-143 e DEC-286 vanno aggiornate.

**Difformità dalla issue.** Chi non è capo oggi vede solo gli eventi a cui lui o i figli partecipano
(`policy.eventi_visibili`). Mostrargli tutti gli eventi dell'unità allargherebbe un permesso.

**Trovato durante l'analisi.** Le viste attuali contano solo staff e capo unità: restano fuori gli
assistenti ecclesiastici di unità (DEC-281) e le unità collegate (DEC-279). La nuova vista usa
`policy._unita_servite`, che li comprende.

**Da decidere.**

1. Per chi non è capo resta com'è, senza selettore? (Sì.)
2. La nuova vista comprende tutti gli eventi di gruppo, anche senza invito? (No: solo quelli a cui si è
   invitati; per gli altri c'è «Tutto il gruppo».)
3. Chi ha già una vista ricordata dal browser passa alla nuova una volta? (Sì.)
4. Correggere anche le viste attuali per assistenti e unità collegate? (Sì, è una riga.)

### Da verificare sul server (senza issue)

Tempi della build con `scripts/aggiorna.sh`, passo per passo: dove va il tempo. Sul Mac (04/11) le
immagini della schermata di avvio prendono circa 2,5 s su 8,4 di `npm run build`. Da guardare: le
immagini (si possono generare in un passo Docker a parte, rifatto solo se cambiano logo, nome del
gruppo o `scripts/avvio.ts`), `npm ci` rifatto a ogni versione perché cambia il numero in
`package.json` e `package-lock.json`, l'immagine del backend.

## Chiuse

| Issue | Titolo | Release |
| ----- | ------ | ------- |
| [#15](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/15) | Schermata di avvio: durata minima configurabile (DEC-333) | [v1.13.1](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.13.1) |
| [#14](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/14) | Schermata di avvio | [v1.13.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.13.0) |
| [#13](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/13) | Verbali | [v1.13.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.13.0) |
| [#12](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/12) | Errore in pdf PWA | [v1.12.1](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.12.1) |

## Non fatte

| Issue | Titolo | Motivo |
| ----- | ------ | ------ |

## Come si usa

Questo file si aggiorna su richiesta, leggendo la situazione su GitHub. Una richiesta nata fuori da
GitHub diventa prima una issue.

**Impatto** è il rischio di fare danni al codice esistente implementando la soluzione.
**Impatto** e **Difficoltà** valgono Basso/Bassa, Medio/Media oppure Alto/Alta.

| Status | Significato                                                                          |
| ------ | ------------------------------------------------------------------------------------ |
| vuoto  | Appena scaricata da GitHub                                                           |
| VAL    | Valutate complessità, fattibilità e cose da fare; implementazione non ancora avviata |
| WIP    | Da sviluppare, ci stiamo lavorando                                                   |
| VER    | Sviluppo completato, in attesa dell'ok del maintainer                                |
| CLSD   | Chiusa con la soluzione: passa alla tabella «Chiuse», con la release                 |
| NO     | Non fattibile o si decide di non procedere: passa alla tabella «Non fatte»           |

- **Analisi:** ogni decisione presa su una issue va nei documenti di analisi, con il suo codice.
- **Chiusura con soluzione:** dopo lo sviluppo la issue passa a VER. Quando il maintainer dà l'ok e
  la release è pubblicata, si chiude su GitHub indicando la release nel commento di chiusura.
- **Non si procede:** la issue passa a NO e si chiude su GitHub.
- **Segnalazioni di sicurezza non ancora pubbliche:** questo file è pubblico, quindi finché la
  segnalazione non è pubblicata si scrive solo il suo codice GHSA, senza titolo né valutazioni. I
  dettagli delle segnalazioni attive stanno in `TODO_security.md`, che resta sul computer del
  maintainer e non va su GitHub.
