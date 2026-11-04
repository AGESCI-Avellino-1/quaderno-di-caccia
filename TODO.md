# TODO — manutenzione

Situazione delle [issue](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues) e delle
[segnalazioni di sicurezza](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/security/advisories)
su GitHub, aggiornata il 04/11/2026 (ultima versione: v1.13.1). Le cose ancora aperte del periodo di
sviluppo sono in [TODO_SVILUPPO.md](TODO_SVILUPPO.md).

## Aperte

| Issue                                                                    | Titolo                                                            | Tipo     | Impatto | Difficoltà | Status |
| ------------------------------------------------------------------------ | ----------------------------------------------------------------- | -------- | ------- | ---------- | ------ |
| [#21](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/21) | Notifiche push sull'app installata                                | Funzione | Medio   | Media      | WIP    |
| [#20](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/20) | Modelli di convocazione e verbali del gruppo su carta intestata   | Funzione | Medio   | Alta       | VER    |
| [#19](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/19) | Download: documenti del gruppo scaricabili in app                 | Funzione | Basso   | Media      | VER    |
| [#18](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/18) | Progetto Educativo di Gruppo (PEG): caricamento e storico         | Funzione | Medio   | Media      | VER    |
| [#17](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/17) | Progetto del capo: inserimento e consultazione da parte della Co.Ca. | Funzione | Basso   | Media      | VER    |
| [#16](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/16) | Calendario: voce «Tutti i miei eventi» come selezione predefinita | Modifica | Basso   | Bassa      | VER    |

Nessuna segnalazione di sicurezza aperta.

### Da verificare sul server (senza issue)

Tempi della build con `scripts/aggiorna.sh`, passo per passo: dove va il tempo. Sul Mac (04/11) le
immagini della schermata di avvio prendono circa 2,5 s su 8,4 di `npm run build`. Da guardare: le
immagini (si possono generare in un passo Docker a parte, rifatto solo se cambiano logo, nome del
gruppo o `scripts/avvio.ts`), `npm ci` rifatto a ogni versione perché cambia il numero in
`package.json` e `package-lock.json`, l'immagine del backend.

## Valutazioni

Valutazioni fatte leggendo le issue, i modelli e il codice: nulla è ancora stato sviluppato. Ordine di
sviluppo consigliato: #16, poi #19 e #18 insieme (il PEG si consulta da Download), poi #17, poi #20;
#21 può partire in ogni momento, gli avvisi di #18 e #19 la useranno quando ci sarà.

### #21 Notifiche push

**Decisioni:** DEC-345. **Fattibile.** Il testo passa cifrato dai servizi di Apple e Google. Su iPhone
funziona solo con l'app sulla schermata Home e dopo il permesso, quindi le email restano.

**Cose da fare.**

1. Chiavi del server in `.env` e nella guida di installazione; una libreria Python da scegliere,
   controllando la versione installata.
2. Service worker: oggi lo genera `vite-plugin-pwa` (`generateSW`), va esteso per ricevere le push e
   aprire la pagina giusta al tocco.
3. Registrazione per utente e browser, legata alla sessione e non a `Dispositivo` (che esiste solo con la
   protezione attiva), cancellata all'uscita, alla revoca, se entra un altro account o se il servizio
   risponde che non vale più.
4. Invio accanto a `impostazioni.email.invia`, tipo per tipo, in coda come le email (DEC-311), bloccato
   durante l'impersonazione. Un testo breve per ogni tipo, senza dati personali.
5. Preferenze: da `PreferenzeEmail` (cinque gruppi di email facoltative) a una scelta email, push o
   entrambe per tipo di avviso, con migrazione delle scelte attuali. Le email sempre inviate restano.
6. Invito nell'app installata e pulsante nelle preferenze; su iPhone senza app installata, spiegazione.
7. Da provare su iPhone e Android veri. Manuale e informativa privacy da aggiornare.

**Rischio.** La scelta per persona tocca il filtro di tutte le email facoltative, che finora ha solo
cinque gruppi: da controllare in sviluppo quanti tipi mostrare, per non fare una pagina di 40 righe.

### #20 Modelli di convocazione e verbali

**Decisioni:** DEC-336…DEC-340. **Fattibile**, è la più grande del gruppo.

**Cose da fare.**

1. Più verbali per riunione: `Verbale.evento` da uno a uno a uno per modello, con API, promemoria, copia
   dei presenti e pagina del verbale.
2. Dati nuovi: luogo strutturato (`Localita.indirizzo` oggi è un testo unico), prima convocazione,
   ordine del giorno e anni, ore effettive, scrutatori, voti per delibera, risultato di bilancio, quote,
   parti del verbale della Co.Ca. con Capi Gruppo, rappresentante e sede.
3. Testi dei modelli nel codice e moduli con anteprima; controlli per il definitivo; copia dei dati.
4. PDF da `verbali/stampa.py` con titoli e firme dei modelli; il PDF della convocazione diventa un
   documento della convocazione (DEC-327).
5. Test, manuale e dati di prova.

**Scelte fatte in sviluppo.** Il verbale principale resta uno per riunione: i verbali in più sono
`VerbaleCollegato`, così il flusso già rilasciato non cambia. Il verbale collegato lo compilano solo i
capigruppo, non chi è indicato come redattore. Agli esiti del voto il testo aggiunge «con N voti favorevoli
e M contrari» o «all'unanimità» anche in elezione e quota, dove il modello non li prevede [da verificare
col maintainer].

**Da provare nel browser.** Testato con i test automatici e controllando i PDF generati; non provato a mano
nell'interfaccia. Le schermate del manuale non sono rigenerate.

### #19 Download e #18 PEG

**Decisioni:** DEC-341, DEC-342 (#19), DEC-343, DEC-344 (#18). **Fattibili.**

**Cose da fare.**

1. Nuova app con documento, destinatari e visibilità in `policy.py`, con i test di ogni ruolo.
2. Controllo dei tipi di file: `TIPI` dei verbali va spostato in comune.
3. Comando giornaliero nel cron che cancella i documenti scaduti e i loro file.
4. Versioni del PEG, etichetta «in redazione» sul gruppo, pagina pubblica e scaricamento senza login con
   un limite alle richieste: primo file aperto a chi non ha un account, solo la versione in vigore.
5. Voce di menu, tipi di email facoltativi con le preferenze, manuale.

**Da controllare.** Il peso del PEG vero rispetto ai 20 MB. Con «tutti i capi vedono tutto», la
destinazione «Co.Ca.» vuol dire in pratica «nessuna famiglia».

### #17 Progetto del capo

**Decisioni:** DEC-335. **Fattibile.**

**Cose da fare.**

1. Modello in `apps/fascicolo`, sezione in `FascicoloCapoView`, permessi di lettura già esistenti.
2. Lettore del testo di `verbali/stampa.py` da spostare in comune, per il PDF su foglio semplice.
3. pdf.js caricato solo quando serve: dipendenza nuova, da provare sui telefoni. nginx risponde
   `X-Frame-Options: DENY`, ma pdf.js disegna nella pagina e non lo richiede.
4. Esportazione e cancellazione (`diritti`), archivio e trasferimento del fascicolo.

**Scelta fatta in sviluppo.** Il trasferimento a un altro gruppo porta solo i testi: un PDF non starebbe nel
file, che deve restare sotto i 20 MB dei proxy. I PDF restano nello ZIP dell'archivio.

**Provato in Chromium** (il PDF si disegna nella pagina). Da provare su iPhone e Android.

### #16 Calendario

**Decisioni:** DEC-334. **Fattibile.** Impatto e difficoltà abbassati rispetto alla prima stima.

**Cose da fare.**

1. Vista `miei` in `eventi/calendario.py`, con `policy._unita_servite` anche nelle due viste che oggi
   contano solo staff e capo unità.
2. Passaggio una tantum alla nuova vista nel browser; test; riga nel manuale.

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
