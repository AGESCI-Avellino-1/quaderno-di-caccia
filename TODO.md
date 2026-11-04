# TODO — manutenzione

Situazione delle [issue](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues) e delle
[segnalazioni di sicurezza](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/security/advisories)
su GitHub, aggiornata il 04/11/2026 (ultima versione: v1.12.0). Le cose ancora aperte del periodo di
sviluppo sono in [TODO_SVILUPPO.md](TODO_SVILUPPO.md).

## Aperte

| Issue                                                                    | Titolo            | Tipo     | Impatto | Difficoltà | Status |
| ------------------------------------------------------------------------ | ----------------- | -------- | ------- | ---------- | ------ |
| [#13](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/13) | Verbali           | Funzione | Medio   | Alta       | VAL    |
| [#12](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/12) | Errore in pdf PWA | Errore   | Basso   | Media      | VER    |

Nessuna segnalazione di sicurezza aperta.

## Valutazioni

Valutazioni fatte leggendo le issue e il codice: nulla è ancora stato sviluppato.

### #12 Errore in pdf PWA

**Causa probabile.** Con la PWA installata su iPhone, un link a un file apre il PDF a tutto schermo
dentro l'app, senza comandi per tornare indietro, condividere o salvare (nello screenshot, il PDF
degli incarichi: un link con `download`, servito come `attachment`). Finché non si chiude l'app a
mano si resta bloccati. Il comportamento di iOS 27 non è ancora stato riprodotto.

**Fattibile**, con un intervento solo nel frontend, senza toccare dati e permessi:

1. Un unico gestore dei clic a livello di app, attivo solo con la PWA installata su iOS
   (`pwa/installazione.ts`), per i link a file serviti da `/api/v1/`: non si toccano una per una le
   circa 30 pagine e i link futuri sono già coperti.
2. Il file si scarica con la sessione dell'utente e resta solo in memoria: nulla finisce sul
   dispositivo senza una scelta della persona, e il registro degli accessi lato server non cambia.
3. Compare una finestra dell'app con «Condividi o salva» (foglio di condivisione di iOS, da cui si
   salva su File) e «Chiudi». Serve il secondo tocco perché Safari può rifiutare la condivisione se
   arriva dopo l'attesa dello scaricamento.
4. Stesso trattamento per i tre scaricamenti creati dalla pagina (QR, rubrica, fascicolo JSON).
5. Messaggi in italiano per file negato o assenza di rete; test automatici del gestore.

**Stato.** Sviluppata (`pwa/file.ts`, `FileDaSalvare.vue`), con test automatici e prova in Chromium con
viewport da telefono. Manca la prova su iPhone.

**Decisione.** DEC-320 nell'[analisi](docs/analisi/analisi-requisiti.md).

**Rischi e verifiche.** Da provare su un iPhone vero con la PWA installata: PDF, immagini, Excel e il
file del calendario (che deve ancora aggiungersi al calendario). Android e computer restano come
sono, salvo problemi segnalati. Non servono nuove decisioni nell'analisi.

### #13 Verbali

**Cosa c'è già.** Le riunioni di Co.Ca., squadriglia, Alta Squadriglia, Consiglio Capi e Con.Ca.Vi.
(`Evento` di tipo riunione); editor (`EditorTesto.vue`); pulizia dell'HTML
(`impostazioni/html.py`); carta intestata e PDF (`core/stampa.py`); chiusura dell'anno; registro
delle modifiche.

**Cosa manca.**

- Il verbale: testo, chi lo scrive, stato, pagina nell'app, PDF. Serve un convertitore dal testo
  dell'editor al PDF.
- Gli incarichi di squadriglia: si possono aggiungere come ruoli senza limite di persone, senza
  permessi e chiusi da soli quando si lascia il reparto. Oggi sono elencati nei `RUOLI_DI_SQUADRIGLIA`
  solo capo e vice, quindi va verificata ogni pagina che li mostra.
- Le riunioni dei genitori **non esistono** come tipo: oggi gli invitati sono solo i soci
  (`eventi/servizi.previsti`), e nei dati di prova l'«Assemblea dei genitori» è un avviso in bacheca.
  Vanno aggiunti invitati, visibilità, calendario e presenze dei genitori: è la parte più delicata.
- L'assemblea dei soci: soci maggiorenni più genitori in rappresentanza dei minorenni; presidente e
  segretari nel verbale.
- Permessi in `policy.py` con i test per ogni ruolo; esportazione e cancellazione dei dati
  (`diritti/servizi.py`); manuale.

**Fattibile a blocchi:**

| Blocco | Contenuto                                                        | Impatto | Difficoltà |
| ------ | ---------------------------------------------------------------- | ------- | ---------- |
| 1      | Incarichi di squadriglia, assegnati dal capo squadriglia         | Basso   | Bassa      |
| 2      | Verbale, PDF e allegati su Drive per le riunioni che esistono già | Medio   | Alta       |
| 3      | Riunioni dei genitori, con invitati e presenze                   | Alto    | Media      |
| 4      | Assemblea dei soci, con rappresentanza, presidente e segretari   | Alto    | Alta       |

**Decisioni.** Sono nell'[analisi](docs/analisi/analisi-requisiti.md), sezione «Verbali delle riunioni»
(DEC-321…DEC-331). L'elenco degli incarichi viene da `ignored/Incarichi di Squadriglia.pdf`, sul computer
del maintainer. Una versione per la #12 (uscita con la 1.12.1) e una per la #13, alla fine dei quattro
blocchi.

**Da verificare in sviluppo: allegati su Drive.** Oggi l'app carica su Drive solo gli archivi, tenendoli in
memoria, e il server accetta file fino a 20 MB. Per audio e video servono caricamento a pezzi (forse diretto
dal browser a Drive), lettura attraverso l'app per applicare i permessi e uno ZIP che non stia tutto in
memoria.

## Chiuse

| Issue | Titolo | Release |
| ----- | ------ | ------- |

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
