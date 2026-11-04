# TODO — manutenzione

Situazione delle [issue](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues) e delle
[segnalazioni di sicurezza](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/security/advisories)
su GitHub, aggiornata il 04/11/2026 (ultima versione: v1.12.0). Le cose ancora aperte del periodo di
sviluppo sono in [TODO_SVILUPPO.md](TODO_SVILUPPO.md).

## Aperte

| Issue                                                                    | Titolo            | Tipo     | Impatto | Difficoltà | Status |
| ------------------------------------------------------------------------ | ----------------- | -------- | ------- | ---------- | ------ |
| [#13](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/13) | Verbali           | Funzione | Medio   | Alta       | VAL    |
| [#12](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/12) | Errore in pdf PWA | Errore   | Basso   | Media      | VAL    |

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

**Deciso dal maintainer il 04/11/2026** (da riportare nell'analisi prima dello sviluppo):

- **Incarichi di squadriglia:** cassiere, cicala, cronista, guardiano dell'angolo, guardiano dello
  stile, guardiano del tempo, infermiere, liturgista, magazziniere, aiuto magazziniere, mercurio
  (elenco in `ignored/Incarichi di Squadriglia.pdf`). Un incarico può avere più persone e una persona
  può averne più di uno; non danno permessi, nemmeno l'infermiere. Li assegnano il capo squadriglia e
  lo staff del reparto (un capogruppo solo se è in quello staff); il vice no, salvo abilitazione. Li
  vedono la squadriglia, i suoi genitori e i capi.
- **Chi legge il verbale:** Co.Ca. solo i capi; squadriglia i membri, i loro genitori e i capi; Alta
  Squadriglia, Consiglio Capi e Con.Ca.Vi. gli invitati e i capi; riunioni dei genitori e assemblea
  gli invitati e i capi.
- **Chi scrive:** riunione per riunione chi ne ha il potere indica una persona tra gli invitati o un
  capo, e può sempre scrivere e correggere: capo squadriglia e staff per la squadriglia; lo staff per
  Alta Squadriglia, Consiglio Capi e Con.Ca.Vi.; i capigruppo per Co.Ca. e assemblea; per le riunioni
  dei genitori i capigruppo e, se di una sola unità, anche il suo staff. Il cronista è proposto per
  primo, ma serve sempre la scelta del capo squadriglia.
- **Stati:** bozza (la vedono chi scrive, chi l'ha indicato e i capi) e definitivo (lo leggono gli
  aventi diritto, con il PDF). Lo rende definitivo e lo riapre, con un motivo, chi può indicare chi
  scrive; l'anno chiuso lo blocca. Niente approvazione alla riunione successiva.
- **Firme nel PDF:** presidente e segretari per l'assemblea, chi ha scritto per Co.Ca. e riunioni dei
  genitori; nessuna per le riunioni con i ragazzi, che sono informali.
- **Riunioni dei genitori:** di gruppo o di una o più unità, create dallo staff o dai capigruppo. Sono
  invitati i genitori e i tutori, e i capi dello staff (per il gruppo tutta la Co.Ca.). Un figlio
  maggiorenne non partecipa, ma può scegliere di partecipare al posto dei genitori. Presenze segnate
  dallo staff (per il gruppo da qualunque capo), senza effetto su quelle dei figli; nessuna assenza da
  comunicare.
- **Assemblea dei soci:** convocata dai capigruppo. Invitati: capi e R/S maggiorenni e genitori e tutori
  dei minorenni, con diritto di voto; genitori di maggiorenni senza figli minorenni, senza voto, che
  leggono comunque il verbale. Il voto si conta per socio: ogni minorenne vale un voto, espresso da uno
  solo dei genitori; un genitore socio vota anche per sé. Le votazioni, le deleghe e il numero legale
  restano fuori dall'app: al massimo si scrivono nel verbale. Presidente uno, socio maggiorenne o
  genitore; segretari uno o più; si scelgono tra i presenti. Presenze segnate dai capigruppo o da una
  persona indicata. Il PDF elenca i presenti con il diritto di voto, copiati nel verbale definitivo.
- **Email:** per riunioni dei genitori e assemblea anche alla convocazione e all'aggiunta di allegati,
  con i file allegati fino a una certa dimensione (sopra, titolo e link); gli allegati restano
  disponibili nell'app.
- **Conservazione:** i verbali restano senza scadenza. Per assemblea e Co.Ca. (Terzo Settore) nomi e
  presenti restano per 5 anni anche se una persona viene cancellata o archiviata; dopo, e subito per gli
  altri tipi, il nome scelto dall'elenco si toglie. Il testo libero non cambia da solo: la cancellazione
  segnala i verbali col nome e decide il capogruppo.
- **Riservatezza:** il testo non entra mai nel registro delle modifiche; le letture e i PDF scaricati si
  registrano solo per la Co.Ca.
- **Limiti:** solo online, nessuna lettura o scrittura offline; niente immagini nel testo; nessun verbale
  per Consiglio degli Anziani e riunioni ordinarie di unità.
- **Allegati al verbale:** PDF, immagini, Word, Excel, PowerPoint, audio e video, con le regole di lettura
  del verbale, fuori dal PDF, caricati sul Drive del gruppo; se possibile, ZIP con verbale e allegati su
  richiesta.
- **Obbligo e promemoria:** l'assemblea deve avere il verbale; Co.Ca. e riunioni dei genitori mandano un
  promemoria, salvo che si indichi, anche dopo la riunione, che non c'è verbale; gli altri tipi sono
  facoltativi e senza promemoria.
- **Ordine:** incarichi, verbali per le riunioni esistenti, riunioni dei genitori, assemblea; una sola
  versione alla fine di tutti i blocchi.

**Ancora da decidere:** promemoria (quando e a chi), Drive (installazioni senza Drive, limiti, accesso alla
cartella), se la #12 esce prima con una sua versione.

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

- **Chiusura con soluzione:** dopo lo sviluppo la issue passa a VER. Quando il maintainer dà l'ok e
  la release è pubblicata, si chiude su GitHub indicando la release nel commento di chiusura.
- **Non si procede:** la issue passa a NO e si chiude su GitHub.
- **Segnalazioni di sicurezza non ancora pubbliche:** questo file è pubblico, quindi finché la
  segnalazione non è pubblicata si scrive solo il suo codice GHSA, senza titolo né valutazioni. I
  dettagli delle segnalazioni attive stanno in `TODO_security.md`, che resta sul computer del
  maintainer e non va su GitHub.
