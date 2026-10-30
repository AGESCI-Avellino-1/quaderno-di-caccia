# Progressione Personale: specifica di dominio

> Versione 1.0 del 21 ottobre 2026, convertita da Word il 30 ottobre 2026. È il riferimento della fase 4 (DEC-56): il codice ne cita le sezioni (§17.5) e le regole (V04). Le decisioni che la precisano o la modificano sono nell'[analisi](analisi-requisiti.md) (DEC-56…DEC-74, DEC-171…DEC-190). Tutti gli esempi sono fittizi.


## 1 Scopo e criterio di modellazione

L’applicazione deve documentare e accompagnare il percorso personale di ciascun ragazzo e ragazza attraverso L/C, E/G e R/S, mantenendo la continuità della storia educativa fino alla Partenza. Il centro del modello è la persona: esperienze, impegni, verifiche, relazioni, competenze e scelte costituiscono il suo cammino. Le appartenenze alle unità e gli strumenti delle branche cambiano nel tempo.

La progressione personale non coincide con il completamento di una lista di attività. Il software deve aiutare ragazzo, ragazza e capi a ricordare, progettare e rileggere il percorso, lasciando alle persone e alle comunità previste dal metodo il riconoscimento della crescita. La Partenza è l’orizzonte dell’intero itinerario; non è un premio calcolato dall’app né un esito obbligatorio per chiunque abbia frequentato le tre branche.

Il documento è destinato a chi progetta il prodotto, il modello dati e i flussi applicativi, insieme ai capi che ne verificano la coerenza metodologica. Comprende tipi, schema logico, macchine a stati, eventi di dominio e requisiti di storicizzazione. Non impone un database fisico, un linguaggio di programmazione o una procedura associativa di approvazione del software.

### 1.1 Fonte e convenzioni

Fonte: *Regolamento metodologico – Associazione Guide e Scouts Cattolici Italiani*, file fornito “Regolamento-metodologico-agesci-2026.pdf”, pagine 49–78, integrate con gli allegati finali alle pp. 78–81. Le pp. 82–88 sono state consultate per verificare gli indici e i riferimenti. Le pagine fisiche del PDF corrispondono alla numerazione stampata per l’intervallo esaminato.

I riferimenti sono qualificati con **Interbranca**, **L/C**, **E/G** o **R/S**, perché lo stesso numero di articolo identifica testi diversi nelle colonne parallele. Per esempio, “E/G art. 38” riguarda il brevetto di competenza, mentre “L/C art. 38” riguarda il gioco delle prede e dei voli.

Nel testo:

- **Fonte** indica una sintesi del regolamento, accompagnata dal riferimento.

- **Modello proposto** indica una scelta di progettazione dell’app, dedotta dal metodo ma non prescritta dal regolamento.

- **Da definire** indica una decisione di prodotto o un’integrazione documentale necessaria.

L’intervallo comprende il Capo V sulla progressione personale, il Capo VI sulla figura del capo e gli allegati finali rilevanti. Da p. 72 l’intestazione del file riporta “aggiornato al Consiglio generale 2024”, mentre le pagine precedenti riportano 2026. Questa difformità va mantenuta nella provenienza della fonte, senza attribuirle autonomamente un significato normativo. I cataloghi di specialità, brevetti e tipi di evento sono riportati nelle appendici di questo documento, con la numerazione effettiva degli allegati.

## 2 Principi comuni alle tre branche

### 2.1 Unitarietà e gradualità

**Fonte.** La progressione personale cura lo sviluppo graduale e globale della persona attraverso l’identificazione e la realizzazione delle proprie potenzialità. Si vive nelle occasioni offerte dall’esperienza scout e nella comunità, con lo spirito del gioco, dell’avventura e del servizio. È unitaria perché orientata alla Partenza e procede a spirale: esperienze analoghe vengono rilette a livelli diversi di maturazione. Scoperta, competenza e responsabilità sono momenti complementari presenti in ogni branca. La Promessa si colloca nella scoperta e non costituisce una fase preliminare separata. \[Interbranca artt. 28–30, pp. 49–50\]

**Modello proposto.** Conservare una sola identità personale e più periodi di percorso. Ogni periodo di branca mantiene la propria scansione. Non creare una sequenza unica di nove “livelli” che trasformi le tre branche in una graduatoria. Separare il momento prevalente vissuto dalla persona dalle dimensioni pedagogiche presenti nelle singole esperienze.

### 2.2 Globalità e vita quotidiana

**Fonte.** La crescita riguarda tutte le dimensioni della vita e si attua secondo i quattro punti di B.-P.: formazione del carattere, salute e forza fisica, abilità manuale, servizio del prossimo. Le capacità maturate si esprimono anche fuori dallo scautismo. \[Interbranca art. 32, p. 50; E/G art. 31, p. 51\]

**Modello proposto.** Un obiettivo o un’esperienza può riguardare più ambiti di vita e più dimensioni educative. Utilizzare associazioni molti-a-molti, non un unico campo obbligatorio. Gli ambiti possono comprendere scautismo, famiglia, scuola, studio, lavoro, amicizie, sport, parrocchia e territorio. I quattro punti aiutano la lettura educativa dei capi; non diventano voti o percentuali di maturità.

Le quattro dimensioni relazionali R/S sono una classificazione specifica: sé, Dio, altro, mondo. Non vanno equiparate automaticamente, una per una, ai quattro punti di B.-P.

### 2.3 Protagonismo e relazione educativa

**Fonte.** Il capo ascolta, conosce, stimola e accompagna; non si sostituisce al ragazzo nelle scelte. L’autonomia cresce nelle tre branche. La comunità è luogo di confronto e crescita, non semplice scenario. La Comunità capi garantisce unitarietà e coerenza. \[Interbranca artt. 34–35, pp. 69–71; art. 40, p. 75\]

**Modello proposto.** Distinguere sempre chi formula un contenuto, chi lo inserisce materialmente nell’app, chi lo condivide e chi ne riconosce l’esito. Un capo può trascrivere una preda formulata da un bambino senza diventarne l’autore educativo. L’uso personale dell’app da parte dei minori non è un presupposto del modello.

### 2.4 Verifica come rilettura

**Fonte.** La verifica rilegge motivazioni, sforzo e risultati, confronta il percorso con gli obiettivi e orienta le scelte successive. In R/S un obiettivo non raggiunto può suggerire una revisione del cammino, senza essere interpretato come fallimento. \[Interbranca art. 33, p. 67; R/S art. 41, p. 72\]

**Modello proposto.** Conservare più verifiche sullo stesso impegno, con autovalutazione, contributi dei capi e della comunità. Consentire riformulazioni e nuovi tentativi senza cancellare la storia. Distinguere la verifica di un impegno dal riconoscimento di una tappa, specialità o brevetto.

## 3 Confronto fra le branche

| Aspetto | L/C | E/G | R/S |
|----|----|----|----|
| Percorso | Pista del lupetto o sentiero della coccinella | Sentiero | Progressione personale lungo la strada |
| Scansione | Momenti di scoperta, competenza, responsabilità | Tappe di scoperta, competenza, responsabilità | Passi di scoperta, competenza, responsabilità |
| Progettazione personale | Prede e voli; prove di specialità e altri strumenti | Impegni; mete introdotte gradualmente | Punto della strada, obiettivi e programma di impegni |
| Contesto | Branco o cerchio | Reparto, squadriglia, Alta squadriglia | Comunità R/S, noviziato, clan/fuoco |
| Verifica | Bambino e capi, con modalità adeguate e contributo comunitario | Autovalutazione, capi e comunità pertinenti; Consiglio della Legge | Rover o scolta, capi, assistente ecclesiastico e comunità, con riservatezza |
| Distintivo di progressione | Dopo conclusione e verifica delle prede o dei voli | All’inizio del cammino nella tappa | Nessun sistema di distintivi dei passi definito nelle pagine esaminate |
| Snodo caratteristico | Conquista delle prede o dei voli | Riconoscimenti nel Consiglio della Legge | Firma della Carta di clan e maturazione delle scelte della Partenza |

Riferimenti principali: L/C artt. 35–44, pp. 51–61 e 67; E/G artt. 31–43, pp. 51–68; R/S artt. 33–39, pp. 51–61.

## 4 Progressione personale in L C

### 4.1 Ingresso e momenti del percorso

**Fonte.** La progressione inizia dal primo ingresso in branco o cerchio. Si realizza con esperienze concrete, impegno a fare del proprio meglio, verifica in tutti gli ambiti di vita e relazioni nel clima di famiglia felice. Gli obiettivi educativi sono proporzionati all’età, alla crescita e alla personalità. \[L/C art. 35, pp. 51–52\]

| Momento | Caratterizzazione | Giungla | Bosco |
|----|----|----|----|
| Scoperta | Conoscere sé, comunità e regole; scegliere la Promessa; iniziare gli impegni personali | In caccia con Baloo per diventare lupo della legge | In volo nel prato per diventare coccinella del prato; filo d’erba |
| Competenza | Coltivare talenti, aprirsi agli altri e contribuire consapevolmente alla comunità | In caccia con Bagheera per diventare lupo della rupe | In volo nel bosco per diventare coccinella del bosco; mughetto |
| Responsabilità | Individuare occasioni, formulare proposte e mettere le capacità a disposizione degli altri | In caccia con Akela per diventare lupo anziano | In volo sulla montagna per diventare coccinella della montagna; genziana |

Fonte: L/C artt. 36 e 38, pp. 52–56. Le denominazioni del riconoscimento non devono essere usate per far apparire già conquistato ciò verso cui il bambino sta camminando.

### 4.2 Gioco delle prede e dei voli

**Fonte.** Le prede e i voli sono impegni personali, concreti e verificabili, individuati dal bambino con un protagonismo crescente nella relazione con i capi. Il numero è deciso insieme: una o più prede o voli, secondo capacità, interessi e tempi personali e della stagione. Non esiste una quantità fissa valida per tutti. \[L/C art. 38, pp. 54–55\]

La stagione di caccia o di volo:

- è un tempo comune dell’unità, distinto dal singolo impegno;

- inizia dopo che la comunità si è arricchita delle Promesse dei cuccioli e delle cocci, con un lancio festoso;

- dura circa tre o quattro mesi;

- si conclude quando tutti hanno conquistato prede e voli e comunque prima delle vacanze di branco o cerchio.

Il gioco impegna i bambini nei primi tre anni di permanenza. Nelle unità quadriennali l’ultimo anno continua il momento della responsabilità con altri strumenti della pista o del sentiero. \[L/C art. 38, pp. 54–55\]

Il bambino verifica la conquista con i vecchi lupi o le coccinelle anziane. Le difficoltà diventano occasioni di accompagnamento e individuazione di nuovi obiettivi, creando condizioni perché ciascuno conquisti la propria preda o il proprio volo. Il distintivo viene consegnato subito dopo conclusione e verifica. \[L/C art. 38, pp. 56–57\]

**Modello proposto.** Entità separate per stagione, partecipazione personale alla stagione, preda/volo, verifiche e riconoscimento. Il momento vissuto, il riconoscimento conquistato e la data di consegna del distintivo sono informazioni distinte. Il termine della stagione non deve dichiarare automaticamente conquistate le prede ancora da verificare.

### 4.3 Specialità e altri strumenti

**Fonte.** Il bambino sceglie le specialità di interesse e concorda con il capo le prove per diventare competente; le capacità acquisite possono essere messe a disposizione della comunità. Il regolamento non stabilisce qui un elenco uniforme di prove obbligatorie. \[L/C art. 41, pp. 59–60\]

Gli strumenti comprendono anche consiglio degli anziani, Consiglio della rupe e della grande quercia, Buona Azione, Piccole Orme e altre esperienze individuali. I filoni di attività sono uno strumento dei capi: formazione cristiana, natura e vita all’aperto, formazione fisica, allenamento dei sensi, abilità manuale, espressione, formazione sociale. \[L/C artt. 37 e 40, pp. 53 e 57–59\]

**Modello proposto.** Una specialità L/C ha un percorso personale con prove concordate, esperienze e verifiche. Non va confusa con una preda: una stessa esperienza può contribuire a entrambi i percorsi. I filoni possono classificare le proposte educative senza diventare sette caselle obbligatorie per ogni bambino.

### 4.4 Eventi individuali e Piccole Orme

**Fonte.** Voli, cacce e campetti individuali integrano il percorso personale e favoriscono incontro, confronto, competenze e restituzione alla comunità. Le Piccole Orme sono rivolte a chi vive la responsabilità, si possono vivere una sola volta, durano almeno tre giorni e vanno collocate in tempo utile per un successivo periodo significativo nella propria unità. La partecipazione può avvenire anche in una regione diversa da quella di censimento. \[L/C artt. 42–43, pp. 60–61\]

**Modello proposto.** La partecipazione registra preparazione, obiettivi, esperienza, verifica e restituzione. Il controllo “una sola volta” riguarda l’intera storia della persona, anche dopo un trasferimento. Una richiesta o prenotazione annullata non equivale a partecipazione vissuta. La significatività del tempo residuo nell’unità richiede una valutazione educativa, non un numero di giorni inventato dal software.

### 4.5 Ingressi successivi e verifica

**Fonte.** Chi entra dopo gli otto anni vive scoperta e Promessa; nella stagione attraversa un primo breve momento di scoperta e prosegue nel momento adeguato alla maturazione. La verifica considera sforzo, difficoltà e progressi, rispettando sensibilità, gioia e gioco. \[L/C art. 39, p. 57; art. 44, p. 67\]

**Modello proposto.** Consentire un percorso iniziale abbreviato e un collocamento motivato nel momento opportuno. Non creare conquiste fittizie di distintivi o stagioni mai vissute per soddisfare una sequenza informatica.

## 5 Progressione personale in E G

### 5.1 Sentiero e tre tappe

**Fonte.** Il sentiero inizia con l’ingresso in reparto e accompagna tutta la permanenza. Ragazzo e ragazza ne sono protagonisti; staff e comunità contribuiscono alla crescita. La dinamica è assumere un impegno, viverlo e verificarlo con la comunità. \[E/G art. 31, pp. 51–52\]

Le tappe non corrispondono automaticamente agli anni in reparto. Ciascuna contiene aspetti di scoperta, competenza e responsabilità, con una prevalenza specifica. Il distintivo viene consegnato all’inizio della tappa. Il riconoscimento nel Consiglio della Legge delle mete raggiunte o dei cambiamenti realizzati attraverso gli impegni comporta il passaggio alla tappa successiva. \[E/G art. 34, pp. 54–55\]

| Tappa | Elementi da documentare |
|----|----|
| Scoperta | Accoglienza, conoscenza delle regole, Promessa, prime responsabilità, incarichi, posti d’azione, interessi e specialità |
| Competenza | Autonomia, ruoli nelle imprese, approfondimento dei talenti, percorso verso il brevetto, capacità messe a disposizione degli altri |
| Responsabilità | Coerenza delle scelte, cura di persone e relazioni, competenze mantenute e trasmesse, ruoli di cogestione e responsabilità anche fuori dal reparto |

Fonti: E/G artt. 35, 37 e 39, pp. 55–61 e 63–66.

**Modello proposto.** Ogni tappa ha data di ingresso e, quando riconosciuta, data di conclusione. La consegna del distintivo non ne determina il completamento. La conclusione della responsabilità è un evento distinto dall’uscita dal reparto: il sentiero continua fino al passaggio. \[E/G art. 40, p. 66\]

### 5.2 Impegni e mete

**Fonte.** Gli impegni sono concreti, verificabili, condivisi nella comunità, limitati nel tempo e orientati alla tappa. Possono nascere da posti d’azione nelle imprese, specialità, incarichi di squadriglia, buone azioni e altre occasioni anche esterne al reparto. Il loro numero non è definibile a priori. \[E/G art. 32, pp. 52–53\]

La meta è una prospettiva di cambiamento individuata dall’E/G nel confronto con i capi e con quanto emerso nei Consigli della Legge. È impegnativa ma proporzionata, verificabile e collegata alla vita quotidiana. Viene introdotta quando il ragazzo è in grado di formularla: prima si utilizzano solo gli impegni. Numero, contenuti e durata sono personalizzati; è utile che alcune mete riguardino ambienti esterni. Le mete particolarmente delicate fanno eccezione alla visualizzazione comunitaria. \[E/G art. 33, pp. 53–54\]

**Modello proposto.** Distinguere “meta” e “impegno” anche se condividono campi di base. Consentire un impegno senza meta e, quando utile, collegamenti a più mete. Il completamento degli impegni non chiude automaticamente una meta: occorre rileggere il cambiamento prodotto.

### 5.3 Specialità individuali

**Fonte.** Le specialità consentono di scoprire e sviluppare capacità e di assumere un ruolo nella comunità. Il percorso utilizza la carta di specialità ed è accompagnato da un maestro o una maestra: E/G competente, capo oppure adulto esterno con capacità tecniche adeguate. Il Consiglio della Legge riconosce la conquista e viene assegnato il distintivo. I Campi di specialità possono contribuire al percorso. \[E/G art. 36, pp. 58–59\]

Le competenze L/C vengono valorizzate, ma un’eventuale riconferma passa attraverso il fare nelle imprese di squadriglia o reparto. Non esiste una conversione automatica delle specialità fra branche. \[E/G art. 36, p. 59\]

**Modello proposto.** Catalogo E/G separato dal catalogo L/C; collegamento di continuità tra percorsi, senza equivalenza di riconoscimento. Registrare carta, accompagnatore, attività e riconoscimento. L’accompagnatore esterno può essere rappresentato senza attribuirgli un account con accesso alla scheda personale.

### 5.4 Brevetto di competenza

**Fonte.** Il brevetto è un percorso personale e specifico, progettato con i capi e il maestro o la maestra di competenza. È un esempio concreto di meta. Ogni E/G dovrà impegnarsi a conseguire almeno un brevetto, mettendolo a disposizione di squadriglia e reparto. Il percorso non è schematizzabile genericamente a priori. \[E/G art. 38, pp. 61–63\]

Per la conquista il testo richiede:

1.  specialità ritenute idonee dall’E/G;

2.  approfondimento nelle imprese e nella vita di squadriglia e reparto, con capacità effettiva, affidabilità tecnica elevata e ruoli di responsabilità;

3.  partecipazione a un’occasione di confronto sulla competenza, interna o esterna all’Associazione;

4.  sperimentazione nel Consiglio d’impresa e come maestro o maestra di specialità.

Il maestro di competenza è preferibilmente un E/G con brevetto uguale o affine, altrimenti una persona esperta. La carta di competenza sostiene la progettazione; il Consiglio della Legge riconosce la conquista, cui corrisponde il distintivo. \[E/G art. 38, pp. 62–63\]

**Modello proposto.** Collegare al brevetto specialità, esperienze, ruoli, occasione di confronto, carta e verifiche. Non introdurre un minimo fisso di specialità, assente nel testo esaminato. Un campo specifico non è l’unica forma ammessa di confronto. Il requisito di almeno un brevetto è un orientamento esplicito da rendere visibile ai capi; non autorizza il software a bloccare automaticamente il passaggio di branca o ad attribuire un brevetto.

### 5.5 Sedi della verifica

| Oggetto | Sede prevista dalla fonte |
|----|----|
| Posti d’azione nelle imprese | Consiglio di squadriglia, Consiglio della Legge o Alta squadriglia |
| Specialità | Consiglio della Legge, possibilmente dopo verifica con maestro e Consiglio di squadriglia |
| Incarichi di squadriglia | Consiglio di squadriglia |
| Altre occasioni concrete, interne o esterne | Consiglio della Legge |
| Mete, cammino di tappa, specialità e brevetti | Consiglio della Legge come momento privilegiato di verifica e riconoscimento |

Fonte: E/G artt. 42–43, pp. 67–68.

**Modello proposto.** Registrare il tipo di sede, la comunità concreta, la data, l’autovalutazione, i contributi e l’esito. Il capo che inserisce l’esito non sostituisce il soggetto o la sede metodologica del riconoscimento. La verifica non è un voto di maggioranza digitale.

### 5.6 Inserimenti in età superiore

**Fonte.** Chi entra più tardi comincia nella scoperta, conosce e accetta le regole pronunciando la Promessa e prosegue nella tappa adeguata alla maturazione. Il periodo iniziale, anche breve, permette al capo di conoscerlo. Il cammino verso la Promessa dura solitamente due o tre mesi. \[E/G artt. 35 e 41, pp. 56 e 66\]

**Modello proposto.** Il tempo usuale è un promemoria, non una scadenza automatica. Il collocamento successivo alla Promessa deve essere registrabile senza fabbricare un percorso storico nelle tappe eventualmente non frequentate come periodi distinti.

## 6 Progressione personale in R S

### 6.1 Passi e articolazione della comunità

**Fonte.** Il percorso R/S sintetizza esperienze scout e di vita, sviluppa progettualità, relazioni e capacità di scelta, con la Partenza come orizzonte. Si articola in passi di scoperta, competenza e responsabilità. \[R/S art. 33, pp. 51–53\]

| Passo | Inizio e snodi | Aspetti da accompagnare |
|----|----|----|
| Scoperta | Ingresso in Comunità R/S; conclusione con firma della Carta di clan nei primi mesi di clan/fuoco | Conoscenza di sé e della proposta, confronto, disponibilità al cambiamento |
| Competenza | Adesione consapevole espressa con la firma della Carta di clan | Uso di conoscenze e abilità nella quotidianità e nel servizio, autonomia, relazioni autentiche |
| Responsabilità | Confronto esplicito e approfondito sulle scelte della Partenza, condiviso con il clan/fuoco | Progetto di vita, servizio continuativo, cittadinanza, scelte autonome e consapevoli |

Fonti: R/S artt. 34–36, pp. 53–56.

La guida o l’esploratore che arriva dal reparto, oppure il giovane sedicenne proveniente dall’esterno, vive la prima parte della scoperta nell’anno di noviziato. Chi arriva in età maggiore vive i passi di scoperta nel clan/fuoco. Il nuovo ingresso dall’esterno incontra la Promessa in questa fase. \[R/S art. 34, pp. 53–54\]

**Modello proposto.** Noviziato e clan/fuoco sono articolazioni dell’appartenenza, mentre scoperta, competenza e responsabilità sono passi della progressione: servono due informazioni separate. Entrare in clan/fuoco non significa automaticamente essere già nei passi di competenza.

### 6.2 Tempi della responsabilità

**Fonte.** All’inizio del terzo anno di clan/fuoco, i rover e le scolte che mostrano autonomia, protagonismo e capacità di portare fuori dallo scautismo le esperienze maturate vengono orientati verso scelte consapevoli. La Route Orientamento Scelte di Servizio è indicata come opportuna e utile in questo momento. I passi di responsabilità si concludono solitamente fra la fine del terzo e l’inizio del quarto anno di clan/fuoco. \[R/S art. 36, pp. 55–56\]

**Modello proposto.** Conservare date e periodi reali di appartenenza al clan/fuoco per contestualizzare gli orientamenti temporali. Non utilizzare il solo numero di anni complessivi in R/S. Non trasformare la ROSS in un requisito automatico per la Partenza: questo obbligo non è formulato nelle pagine esaminate.

### 6.3 Punto della strada

**Fonte.** È il principale strumento di progettazione, programmazione e verifica. Rilegge esperienze e competenze, riconosce obiettivi raggiunti e ne definisce di nuovi, con la Parola di Dio come riferimento. \[R/S art. 39, pp. 59–61\]

| Fase | Contenuto | Rappresentazione applicativa proposta |
|----|----|----|
| Coscienza | Rileggere il cammino e il modo di essere nelle relazioni | Sintesi personale e riferimenti alle esperienze |
| Confronto | Confrontarsi con Promessa, Legge, Parola di Dio e Carta di clan, con comunità e capi | Riferimenti e contributi condivisi, separati dalle parti riservate |
| Progetto | Fissare o ricalibrare gli obiettivi personali | Obiettivi nuovi o revisioni degli esistenti |
| Programma | Definire impegni concreti e verificabili | Azioni, tempi e occasioni di verifica |

Gli obiettivi sono semplici, concreti, limitati nel tempo e tengono conto delle relazioni con sé, Dio, altri e mondo. Vengono condivisi con la comunità rispettando la riservatezza delle situazioni affrontate con capi e assistente ecclesiastico. Il Punto della strada può essere proposto in due o tre momenti dell’anno, anche in noviziato; eventi e passaggi di vita possono offrire ulteriori occasioni di verifica. I capi aiutano senza sostituirsi alle scelte. \[R/S art. 39, pp. 60–61\]

**Modello proposto.** Un Punto della strada è un contenitore datato, ripetibile, collegato a obiettivi, impegni e verifiche. Le quattro fasi non sono nuovi livelli della progressione e non richiedono obbligatoriamente quattro schermate. Consentire revisioni degli obiettivi fra un Punto della strada e l’altro; mantenere la storia della formulazione precedente.

Non imporre quattro obiettivi, uno per relazione: il testo chiede attenzione alle quattro dimensioni, non una cardinalità uniforme. Un obiettivo può interessare più dimensioni.

### 6.4 Eventi individuali

**Fonte.** Gli EPPPI sono scelti da rover o scolta insieme ai capi in relazione ai passi vissuti e agli obiettivi del Punto della strada. La preparazione e la rielaborazione dopo l’evento, con restituzione alla comunità, sono parte essenziale della loro efficacia educativa. \[R/S art. 38, pp. 58–59\]

L’Allegato 1 R/S, pp. 78–81, distingue laboratori/botteghe/workshop, campi di specializzazione, campi Ora et Labora, Route dello spirito, cantieri, ROSS ed eventi per Partenti. L’Appendice B riporta finalità e collocazione preferenziale nei passi.

**Modello proposto.** Distinguere tipo di evento, edizione concreta e partecipazione personale. Collegare la partecipazione agli obiettivi e conservare preparazione, restituzione e successive verifiche. Le indicazioni di collocazione sono preferenze educative, salvo eventuali requisiti espliciti da acquisire da fonti complete.

### 6.5 Partenza e altre conclusioni

**Fonte.** Tra i venti e i ventuno anni rover e scolte chiedono ai capi e all’assistente ecclesiastico il riconoscimento della capacità di scelte autonome e consapevoli e della responsabilità verso sé e gli altri. La Partenza esprime scelte di fede, servizio e impegno politico, vissute nella quotidianità secondo Promessa e Legge. Le scelte e il futuro impegno di servizio vengono esplicitati e condivisi con la comunità; la cerimonia coinvolge l’intera Comunità R/S. Chi compie scelte diverse lascia il clan/fuoco con un saluto fraterno secondo le modalità della comunità. \[R/S art. 37, pp. 56–58\]

**Modello proposto.** Registrare un percorso di discernimento e un evento conclusivo di Partenza con richiesta, riconoscimento, scelte esplicitate, impegno futuro di servizio e cerimonia. Separare le date quando non coincidono. Conservare soltanto la sintesi necessaria e condivisibile, non il contenuto di colloqui spirituali riservati.

Prevedere anche una conclusione con saluto fraterno per scelte diverse, distinta da trasferimento, interruzione o uscita amministrativa. Non usare “bocciato”, “fallito” o un punteggio insufficiente. La Partenza chiude l’iter educativo proposto, non la crescita della persona; l’app non deve assimilare la conclusione a cancellazione della storia.

## 7 Passaggi e continuità del percorso

**Fonte.** Il passaggio riconosce il percorso compiuto, introduce una nuova esperienza e invita a donare le capacità acquisite. Deve evitare la svalutazione dell’esperienza precedente. La Comunità capi condivide le scelte sulle età dei passaggi considerando comunità, esperienze, caratteristiche personali, unità, Gruppo e contesto. \[Interbranca artt. 31 e 37, pp. 50 e 73\]

**Modello proposto.** Un passaggio collega il periodo in uscita e quello in ingresso, senza sovrascriverli. Registra preparazione, data, eventuale cerimonia, partecipanti alla continuità educativa e una sintesi destinata ai nuovi capi. L’identità della persona e i riconoscimenti restano invariati.

Il passaggio non converte automaticamente tappe o specialità. La nuova branca avvia i propri strumenti, valorizzando il cammino precedente. L’app deve consentire anche ingresso diretto in E/G o R/S, trasferimento fra gruppi o unità, interruzione e rientro: sono esigenze di prodotto, non una disciplina ricostruita dagli articoli.

La completezza storica deve essere esplicita. Un dato non conosciuto si registra come non documentato, senza dichiarare che l’esperienza non è mai avvenuta. Per dati importati usare date approssimative o precisione “anno” quando non esiste una data esatta; non inventare il primo gennaio.

## 8 Modello concettuale dei dati

### 8.1 Entità principali

Tutte le entità della tabella sono una proposta tecnica. La terminologia visibile all’utente deve restare quella della branca.

| Entità | Responsabilità e campi essenziali |
|----|----|
| Persona | Identificativo stabile; dati anagrafici minimi; eventuale collegamento a un account |
| Gruppo e comunità | Identità, tipo, denominazione, branca, relazioni con reparto, squadriglia, noviziato o clan/fuoco |
| Appartenenza | Persona, comunità, ruolo, inizio e fine, provenienza; storico delle assegnazioni |
| Periodo di branca | Persona, branca, inizio/fine, motivo di ingresso e uscita, versione del metodo |
| Periodo di progressione | Periodo di branca, momento/tappa/passo, date, motivazione del collocamento, verifica di riferimento |
| Obiettivo | Tipo specifico di branca, formulazione, autore, ambiti/dimensioni, orizzonte temporale, visibilità |
| Impegno | Tipo specifico, descrizione concreta, tempi, criterio di verifica, contesto comunitario, stato |
| Esperienza | Titolo, date, contesto scout o esterno, comunità, partecipanti e ruoli; legami agli impegni |
| Verifica | Oggetto o oggetti verificati, data, sede, autovalutazione, contributi, sforzo, difficoltà, esito e passi successivi |
| Riconoscimento | Tipo, persona, data, riferimento a verifica e sede metodologica; eventuale cerimonia e distintivo |
| Percorso di competenza | Persona, specialità o brevetto, carta/progetto, accompagnatori, attività, verifiche e riconoscimento |
| Evento e partecipazione | Tipo ed edizione dell’evento; iscrizione, partecipazione effettiva, obiettivi, preparazione e restituzione |
| Passaggio | Origine e destinazione, date, sintesi condivisibile, confronto tra capi e cerimonia |
| Conclusione R/S | Tipo di conclusione, percorso di discernimento, richiesta e riconoscimento se Partenza, cerimonia |
| Fonte metodologica | Documento, edizione dichiarata, pagina, branca, articolo, comma, regola e natura del vincolo |

L’appartenenza alla comunità e il periodo di branca non sono equivalenti. Si può cambiare reparto restando E/G, oppure passare da noviziato a clan/fuoco senza cambiare branca. Le specialità di squadriglia hanno come titolare la squadriglia, non ciascuno dei suoi componenti. Prevedere un percorso collettivo distinto, con partecipazioni personali, incarichi e impegni collegati: il conseguimento collettivo non attribuisce una specialità individuale a ogni partecipante. Il catalogo è in Appendice A; le regole operative di conquista richiedono l’art. 18 E/G, esterno al segmento centrale analizzato.

Un incarico non coincide con una tappa: essere capo squadriglia non basta a dimostrare automaticamente il completamento della responsabilità.

### 8.2 Estensioni specifiche

| Estensione | Dati specifici |
|----|----|
| Stagione L/C | Unità, caccia/volo, anno, lancio, inizio/fine previsti ed effettivi, riferimento alle vacanze |
| Partecipazione alla stagione | Persona, momento vissuto, prede/voli, verifiche e conquista |
| Carta di specialità o competenza E/G | Tipo di percorso, versione del progetto, maestro, attività concordate e riferimenti alle esperienze |
| Punto della strada R/S | Data o periodo, quattro fasi, dimensioni relazionali, obiettivi definiti/ricalibrati, impegni |
| Firma della Carta di clan | Persona, data, versione della Carta sottoscritta, cerimonia |
| Ruolo nell’esperienza | Persona, esperienza, ruolo, intervallo; distinto da un incarico continuativo nell’unità |
| Consegna di un segno | Persona, tipo di distintivo o segno, data; legame a Promessa, ingresso in tappa o conquista |

La Carta di clan va versionata: la firma di una persona deve riferirsi al testo effettivamente sottoscritto. La revisione della Carta non genera retroattivamente una nuova firma.

### 8.3 Relazioni e cardinalità

- Una persona può avere più periodi di branca e molte appartenenze storiche.

- Un periodo di branca contiene più periodi di progressione e più oggetti personali.

- Un obiettivo può avere più impegni; un impegno può esistere senza obiettivo esplicito e può contribuire a più obiettivi.

- Un’esperienza può coinvolgere molte persone e molti impegni; lo stesso impegno può realizzarsi attraverso più esperienze.

- Un oggetto personale può ricevere più verifiche. Una sessione comunitaria può contenere verifiche di più persone, conservandone separati gli accessi.

- Un percorso di specialità o brevetto può avere più accompagnatori nel tempo.

- Una partecipazione individuale collega una persona a un’edizione di evento e può contribuire a più obiettivi.

- Una conquista o un passaggio deve essere collegabile alle verifiche che lo motivano; la data di registrazione non sostituisce quella dell’evento.

È consigliabile usare un archivio transazionale con storico delle revisioni e registro delle azioni. Non è necessario imporre un’architettura di event sourcing: la timeline può derivare dagli eventi educativi e dai record storicizzati.

### 8.4 Classificazioni separate

Mantenere distinti questi cataloghi:

1.  punti di B.-P.;

2.  filoni L/C;

3.  dimensioni relazionali R/S;

4.  ambiti di vita;

5.  momenti, tappe e passi per branca;

6.  tipi di strumento e riconoscimento;

7.  specialità L/C, specialità E/G, brevetti E/G ed eventi.

Codici tecnici stabili e denominazioni visualizzate devono essere separati. Il catalogo può offrire nomi declinati al maschile o al femminile senza moltiplicare l’identità della specialità, possibilità esplicitata nell’allegato E/G a p. 78.

## 9 Stati e flussi applicativi

### 9.1 Ciclo degli impegni

**Modello proposto.** Stati operativi possibili: bozza, concordato, in corso, da verificare, concluso, interrotto. La riformulazione crea una nuova revisione collegata, senza cancellare la formulazione precedente.

“Concluso” significa che quel ciclo di lavoro è stato chiuso. L’esito della verifica è separato: raggiunto, parzialmente raggiunto, da riformulare o altro esito motivato. Nessuno di questi esiti deve far avanzare automaticamente nella progressione.

Per prede/voli, specialità e brevetti il riconoscimento della conquista rimane esplicito. Per una meta E/G o un obiettivo R/S la verifica valuta il cambiamento e non soltanto le attività eseguite. Una data oltrepassata genera al massimo un invito alla rilettura.

### 9.2 Flusso L C

1.  Registrare ingresso e appartenenza, avviando la progressione dalla prima esperienza.

2.  Registrare la Promessa quando vissuta, senza considerarla l’inizio della progressione.

3.  Aprire la stagione dell’unità e associarvi i bambini.

4.  Concordare prede o voli personali, momento e riferimenti simbolici.

5.  Collegare esperienze e verifiche; riformulare quando necessario.

6.  Registrare la conquista dopo la verifica e la consegna del distintivo.

7.  Proseguire con gli altri strumenti e preparare il passaggio, mantenendo distinta la conclusione della stagione.

### 9.3 Flusso E G

1.  Registrare ingresso, tappa e consegna del distintivo di tappa.

2.  Documentare la Promessa nel percorso della scoperta.

3.  Assumere impegni e introdurre mete quando appropriato.

4.  Collegare imprese, incarichi, specialità e percorsi di brevetto.

5.  Verificare nelle sedi pertinenti.

6.  Registrare riconoscimento della conclusione di tappa e avvio della successiva.

7.  Dopo la responsabilità continuare a documentare il sentiero fino all’effettivo passaggio.

### 9.4 Flusso R S

1.  Registrare ingresso in Comunità R/S, articolazione e passi di scoperta.

2.  Avviare Punti della strada, obiettivi e programma.

3.  Registrare firma della Carta di clan e passaggio ai passi di competenza.

4.  Collegare servizi, esperienze, EPPPI e verifiche.

5.  Avviare i passi di responsabilità sulla base del percorso educativo.

6.  Accompagnare il discernimento sulle scelte della Partenza.

7.  Registrare la conclusione appropriata senza equiparare ogni uscita alla Partenza.

## 10 Regole di validazione e automazioni

Le regole seguenti distinguono dato verificabile e giudizio educativo. Un controllo tecnico deve impedire incoerenze strutturali, non decidere la maturazione di una persona.

| ID | Regola di dominio | Comportamento proposto |
|----|----|----|
| V01 | La progressione parte dall’ingresso | Consentire esperienze e impegni precedenti alla Promessa |
| V02 | La Promessa è nella scoperta | Registrarla come evento, non come quarta fase |
| V03 | Numero personale di prede, voli e impegni | Nessun minimo uniforme; indicazioni contestuali |
| V04 | Stagione L/C di circa 3–4 mesi e prima delle vacanze | Avvisi su pianificazione e incongruenze; mai chiusura automatica delle conquiste |
| V05 | Distintivo L/C dopo verifica | Richiedere il riferimento alla conquista per nuove registrazioni; ammettere storia importata incompleta esplicita |
| V06 | Distintivo E/G all’inizio | Separare consegna, ingresso in tappa e conclusione |
| V07 | Mete E/G introdotte gradualmente | Consentire impegni senza meta |
| V08 | Nessun avanzamento E/G per anzianità | Richiedere una decisione educativa registrata |
| V09 | Brevetto con percorso personale e condizioni dell’art. 38 | Mostrare le condizioni e le esperienze collegate; riconoscimento umano |
| V10 | Almeno un brevetto nel percorso E/G | Promemoria di progettazione ai capi; nessuna attribuzione o blocco di passaggio automatici |
| V11 | Piccole Orme una sola volta, in responsabilità, almeno 3 giorni | Segnalare duplicati e dati incompatibili nelle registrazioni ordinarie; gestire rettifiche storiche senza inventare conformità |
| V12 | Firma della Carta di clan e passi di competenza | Collegare gli eventi; ingresso in clan/fuoco da solo insufficiente |
| V13 | Punto della strada ripetibile e quattro dimensioni | Promemoria configurabili; nessun obbligo di quattro obiettivi o sole tre verifiche annue |
| V14 | Tempi R/S orientano il discernimento | Evidenziare età e anni nel clan/fuoco; nessuna Partenza automatica |
| V15 | Riservatezza delle mete e situazioni delicate | Separare contenuto riservato e sintesi comunitaria |
| V16 | Conclusione responsabilità E/G diversa da uscita | Consentire sentiero attivo dopo la conclusione della tappa |
| V17 | Competenze L/C valorizzate in E/G attraverso il fare | Collegare i percorsi senza conversione automatica |
| V18 | Continuità della storia | Trasferimenti e passaggi non creano una nuova persona né cancellano il passato |
| V19 | Specialità di squadriglia distinta da specialità personale | Titolare collettivo e contributi individuali separati; nessuna attribuzione automatica ai membri |
| V20 | Promessa e fazzolettone non si ritirano come sanzione | Nessuna funzione di revoca punitiva; consentire soltanto rettifiche di errori di registrazione tracciate |

V20 deriva dall’art. 39 Interbranca, pp. 73–74: i segni personali della Promessa e dell’appartenenza non devono essere tolti al ragazzo. Non va estesa per analogia a regole non presenti su qualsiasi altro riconoscimento.

Per V11 il sistema deve distinguere evento pianificato, iscrizione annullata e partecipazione effettiva. Le registrazioni pregresse problematiche richiedono un’anomalia visibile e una rettifica tracciata: non una deroga metodologica attribuita dall’app.

Sono utili automazioni di promemoria, ricerca di dati mancanti, composizione della timeline e preparazione di sintesi. Sono da escludere punteggi di fede, maturità o “prontezza alla Partenza”, classifiche fra ragazzi, percentuali complessive di crescita e riconoscimenti assegnati solo contando presenze o attività.

## 11 Ruoli e visibilità

### 11.1 Attori educativi e utenti

**Fonte.** Lo staff condivide la responsabilità educativa; in R/S maestri dei novizi, capi clan/fuoco e assistente ecclesiastico condividono quella di tutti gli R/S. La Comunità capi garantisce coerenza; la famiglia e gli altri ambiti di vita contribuiscono alla conoscenza della persona. \[Interbranca artt. 40–41 e articoli di branca, pp. 75–77\]

**Modello proposto.** Non dedurre da queste responsabilità un accesso digitale indiscriminato. Un attore del processo può non essere utente dell’app. Un genitore non riceve automaticamente accesso a ogni riflessione; un membro della Comunità capi non ottiene automaticamente tutte le note dei singoli.

| Ruolo applicativo proposto | Ambito di accesso |
|----|----|
| Ragazzo o ragazza con account | Propri contenuti e parti condivise; esperienza adeguata all’età |
| Capo assegnato alla persona o unità | Strumenti necessari all’accompagnamento e registrazione delle verifiche |
| Staff | Contenuti educativi condivisi con lo staff; nessun accesso automatico a ogni nota personale |
| Comunità o squadriglia | Impegni e sintesi deliberatamente condivisi con quella comunità |
| Maestro di specialità o competenza | Solo il percorso affidato e le informazioni necessarie |
| Capi del passaggio | Sintesi di continuità e dati selezionati secondo una politica esplicita |
| Amministratore tecnico | Gestione del servizio; accesso ai contenuti educativi limitato per quanto tecnicamente possibile |

### 11.2 Contenuti riservati e continuità

**Fonte.** Le mete E/G particolarmente delicate sono escluse dalla normale visualizzazione; in R/S alcune situazioni sono affrontate riservatamente con capi e assistente ecclesiastico. \[E/G art. 33, p. 54; R/S art. 39, p. 61\]

**Modello proposto.** Visibilità per singolo oggetto: personale, condiviso con persone specifiche, staff, comunità. Separare note riservate, voce del ragazzo e sintesi condivisibile; una casella generica “privato” sull’intera scheda non basta.

Una vista comunitaria deve includere soltanto la sintesi autorizzata. Anche notifiche, ricerca, allegati ed esportazioni devono rispettare gli stessi limiti. Al trasferimento, riesaminare gli accessi; le note riservate non passano automaticamente ai nuovi capi.

Da definire prima dell’uso reale: destinatari dell’app, gestione degli account dei minori, autorizzazioni, conservazione, cancellazione, esportazione e trattamento dei dati delicati. Sono requisiti di progettazione da verificare con i responsabili dell’associazione; questo documento non attesta conformità giuridica.

## 12 Funzioni e viste della prima versione

### 12.1 Funzioni prioritarie

1.  Identità unica e storico di gruppi, unità, branche e comunità.

2.  Scheda personale con momento/tappa/passo e timeline.

3.  Impegni, obiettivi, esperienze, verifiche e revisioni.

4.  Stagioni L/C, prede/voli, specialità e Piccole Orme.

5.  Sentiero E/G, mete, carte, specialità, brevetti e sedi di verifica.

6.  Punti della strada R/S, Carta di clan, EPPPI e percorso verso la Partenza.

7.  Passaggi con sintesi di continuità.

8.  Permessi, esportazioni selettive e storico delle modifiche.

9.  Cataloghi versionati e collegamenti alle fonti metodologiche.

Per la prima versione si propone un utilizzo assistito dai capi, con eventuale accesso diretto dei ragazzi da decidere successivamente. Il modello conserva comunque la loro paternità delle scelte. Non sono necessari classifiche, social feed, rilevazione delle presenze o gestione amministrativa dei censimenti per realizzare il nucleo della progressione.

### 12.2 Viste utili

**Scheda personale.** Mostra il percorso attuale, impegni, prossime verifiche, competenze e storia. Distingue riconoscimenti conquistati da strumenti in corso.

**Vista di unità.** Supporta la preparazione delle attività e delle verifiche; evidenzia chi ha impegni da rileggere e quali occasioni possono essere utili, senza ordinare i ragazzi per “livello”.

**Vista di continuità.** Raccoglie esperienze significative, competenze, interessi, voce del ragazzo e obiettivi condivisibili per il passaggio. L’intera scheda riservata non diventa un allegato automatico.

**Vista dei percorsi di competenza.** Collega specialità, brevetti, maestri, ruoli ed esperienze, facilitando la messa a disposizione delle capacità nella comunità.

**Vista R/S.** Consente di rileggere i Punti della strada nel tempo e i collegamenti tra obiettivi, servizio, esperienze ed eventi individuali.

## 13 Casi di prova per la coerenza del modello

Tutti gli esempi sono fittizi e servono a verificare requisiti applicativi.

| Caso | Risultato atteso |
|----|----|
| Una coccinella prende un impegno prima della Promessa | L’impegno è registrabile: la progressione è già iniziata |
| Un bambino concorda due prede e un altro una | Entrambi i percorsi sono validi; nessuna quota uniforme |
| Una preda richiede riformulazione alla fine della stagione | Si conserva la verifica e il percorso successivo; nessuna conquista automatica |
| Un lupetto è nel quarto anno di unità quadriennale | Continua la responsabilità con altri strumenti, senza una quarta fase di distintivo |
| Un bambino già partecipante alle Piccole Orme cambia Gruppo | La partecipazione precedente rimane visibile al controllo di unicità |
| Un E/G ha impegni ma non è ancora pronto a formulare mete | Il sentiero è rappresentabile senza meta fittizia |
| Viene consegnato il distintivo della competenza E/G | Inizia la tappa; non risulta completata |
| Un E/G conclude la responsabilità a febbraio e passa a ottobre | Il sentiero resta attivo fino a ottobre |
| Una specialità L/C viene valorizzata in reparto | Si collega la storia; il riconoscimento E/G richiede il nuovo percorso concreto |
| Un brevetto ha specialità pertinenti e confronto esterno | Il confronto non viene respinto solo perché non è un campo associativo |
| Un nuovo E/G entra in età superiore a quella usuale | Dopo scoperta e Promessa può essere collocato nella tappa adeguata senza storia inventata |
| Una scolta entra in clan/fuoco ma non ha firmato la Carta | Può essere ancora nei passi di scoperta |
| Un obiettivo R/S riguarda contemporaneamente sé e gli altri | Sono ammesse più dimensioni relazionali |
| Un Punto della strada contiene una situazione riservata | La comunità vede soltanto la sintesi condivisa |
| Un rover compie ventuno anni | Non riceve automaticamente la Partenza |
| Una scolta sceglie di lasciare con saluto fraterno | La conclusione è distinta dalla Partenza e non è un fallimento |
| Un capo cambia unità | La titolarità storica dei contributi rimane; gli accessi correnti vengono riesaminati |
| Si importa una specialità con anno noto e giorno ignoto | Si registra la precisione annuale, senza inventare una data esatta |

## 14 Decisioni necessarie prima dell’implementazione

### 14.1 Cataloghi acquisiti e riferimenti da verificare

Gli allegati sono stati integrati: 40 specialità L/C, 65 specialità individuali E/G, 12 specialità di squadriglia e 15 brevetti di competenza E/G. I cataloghi completi sono in Appendice A; gli eventi sono in Appendice B. Le indicazioni numeriche degli allegati nei testi e nei titoli finali non sono sempre allineate: per esempio l’art. 36 E/G rimanda all’Allegato 3 per le specialità individuali, mentre il catalogo effettivo è intitolato Allegato 2. Il modello della fonte deve quindi collegare anche titolo, branca e pagina, non solo “Allegato N”.

Eventuali dettagli di strumenti citati ma non descritti integralmente nel segmento, come forme specifiche dei consigli, carte e altri strumenti di branca, richiedono le sezioni pertinenti. Non vanno colmati importando a memoria prassi di Gruppo come se fossero prescrizioni nazionali.

### 14.2 Scelte di prodotto

Prima di tradurre il modello in schema fisico e interfacce occorre decidere:

- se l’app serve un Gruppo o più livelli associativi;

- se ragazzi e ragazze accedono direttamente e da quale fase;

- come gestire appartenenze, identificativi e trasferimenti;

- quali note conservare e quali mantenere fuori dall’app;

- quali dati vengono condivisi nel passaggio;

- come caricare, verificare e aggiornare i cataloghi metodologici;

- quali esportazioni servono per confronto educativo, continuità e disponibilità personale della storia.

La configurazione locale può riguardare cerimonie, linguaggio visuale, calendari e modalità organizzative. Non deve riscrivere silenziosamente le regole metodologiche o trasformare tradizioni locali in obblighi per tutti.

## 15 Mappa dei riferimenti

| Area | Riferimenti nelle pagine esaminate |
|----|----|
| Definizione, unitarietà, gradualità, passaggi e globalità | Interbranca artt. 28–32, pp. 49–50 |
| Pista e sentiero L/C, momenti e strumenti | L/C artt. 35–37, pp. 51–53 |
| Prede, voli e distintivi L/C | L/C art. 38, pp. 54–57; allegato a p. 78 |
| Inserimento, filoni e specialità L/C | L/C artt. 39–41, pp. 57–60 |
| Eventi L/C e Piccole Orme | L/C artt. 42–43, pp. 60–61 |
| Verifica e relazioni L/C | L/C artt. 44–46, pp. 67, 69 e 72 |
| Sentiero, impegni, mete e tappe E/G | E/G artt. 31–34, pp. 51–55 |
| Scoperta e specialità E/G | E/G artt. 35–36, pp. 55–59 |
| Competenza e brevetti E/G | E/G artt. 37–38, pp. 59–63 |
| Responsabilità, conclusione e inserimento E/G | E/G artt. 39–41, pp. 63–66 |
| Verifiche e comunità E/G | E/G artt. 42–45, pp. 67–70 e 72 |
| Progressione R/S e dimensioni relazionali | R/S art. 33, pp. 51–53 |
| Passi R/S | R/S artt. 34–36, pp. 53–56 |
| Partenza | R/S art. 37, pp. 56–58 |
| EPPPI e Punto della strada | R/S artt. 38–39, pp. 58–61; Allegato 1, pp. 78–81 |
| Relazioni e comunità R/S | R/S artt. 40–41, pp. 69–70 e 72 |
| Verifica comune e relazioni educative | Interbranca artt. 33–35, pp. 67 e 69–71 |
| Esperienza, archi di età, cerimonie, Promessa | Interbranca artt. 36–39, pp. 72–74 |
| Capi e staff delle tre branche | Interbranca artt. 40–41 e articoli di branca, pp. 75–77 |

La traduzione in requisiti deve mantenere questa tracciabilità: ogni regola implementata indica se proviene dalla fonte, da una deduzione progettuale o da una decisione locale. Questo consente di aggiornare l’app senza alterare retroattivamente il significato del cammino già documentato.

## 16 Specifica tecnica del modello

Questa sezione è una proposta implementativa, distinta dalle prescrizioni del regolamento. Le macchine a stati descrivono operazioni dell’app e registrazioni di decisioni educative; non misurano la maturazione né la sostituiscono. Gli stati operativi qui definiti precisano e rendono coerenti i flussi del capitolo 9.

### 16.1 Tipi di base

| Tipo | Rappresentazione proposta | Regole |
|----|----|----|
| Identificativo | UUID opaco | Stabile, mai derivato da nome, sesso, unità o numero di tessera |
| Data civile | YYYY-MM-DD | Per ingresso, Promessa, verifica, cerimonia; non convertirla in timestamp UTC |
| Istante di registrazione | Timestamp UTC | Per audit, concorrenza e sincronizzazione; visualizzazione nel fuso scelto |
| Data storica parziale | Valore con precisione giorno, mese, anno o sconosciuta | Distinta da una data esatta; nessun giorno fittizio |
| Intervallo | Inizio incluso, fine esclusa | Fine nulla se aperto; una transizione alla stessa data non crea sovrapposizione |
| Testo | Stringa Unicode con limiti configurati | Nessun HTML arbitrario; conservare la formulazione originale nelle revisioni |
| Stato | Enumerazione per singolo aggregato | Non usare una sola enumerazione per impegni, tappe, eventi e riconoscimenti |
| Versione | Intero crescente per aggregato | Usato per controllo di concorrenza ottimistico |
| Provenienza | Diretta, importata, ricostruita | Con autore, fonte e qualità documentale, senza giudizi sulla persona |
| Visibilità | Politica più destinatari espliciti | Mai derivata soltanto dalla branca o dal nome del ruolo |

Una data parziale non va usata per ordinare con certezza eventi avvenuti nello stesso anno. Le viste devono mostrare il livello di precisione e distinguere ordine noto da ordine solo plausibile.

### 16.2 Enumerazioni di dominio

I codici seguenti sono proposti, non ufficiali AGESCI. I nomi visualizzati restano quelli italiani delle branche.

| Tipo | Valori proposti |
|----|----|
| Branch | LC, EG, RS |
| EducationalPhase | DISCOVERY, COMPETENCE, RESPONSIBILITY |
| LCEnvironment | GIUNGLA, BOSCO |
| CommunityKind | BRANCO, CERCHIO, REPARTO, SQUADRIGLIA, ALTA_SQUADRIGLIA, COMUNITA_RS, NOVIZIATO, CLAN_FUOCO, COMUNITA_CAPI |
| ObjectiveKind | INTENTO_EDUCATIVO_LC, META_EG, OBIETTIVO_RS |
| CommitmentKind | PREDA, VOLO, IMPEGNO_EG, IMPEGNO_RS, PROVA_SPECIALITA |
| CompetencePathKind | SPECIALITA_LC, SPECIALITA_EG, BREVETTO_EG, SPECIALITA_SQUADRIGLIA |
| ScopeOwner | PERSON, COMMUNITY |
| AssessmentOutcome | REACHED, PARTIAL, REFORMULATE, NOT_EVALUABLE |
| ReviewVenueKind | COLLOQUIO, CONSIGLIO_SQUADRIGLIA, CONSIGLIO_LEGGE, ALTA_SQUADRIGLIA, COMUNITA_RS, ALTRO |
| ClosureKind | PARTENZA, SALUTO_FRATERNO, INTERRUZIONE, TRASFERIMENTO |
| RecordOrigin | DIRECT, IMPORTED, RECONSTRUCTED |
| AccessScope | PERSONAL, NAMED_PEOPLE, STAFF, COMMUNITY |
| RuleEffect | INTEGRITY_ERROR, METHOD_WARNING, INFORMATION |

“INTENTO_EDUCATIVO_LC” è un dato di progettazione educativa dei capi, da distinguere dalle prede o dai voli formulati dal bambino. Non deve apparire automaticamente come un suo obiettivo esplicito. “ALTRO” richiede una descrizione e non può aggirare una sede richiesta per un riconoscimento.

CommunityKind non è un elenco esaustivo dell’organizzazione associativa. Se si includono sestiglie o altri contesti, aggiungere tipi senza dedurre da essi nuove fasi della progressione.

### 16.3 Schema logico essenziale

Convenzioni: PK identifica una chiave primaria; FK un riferimento; un campo indicato come facoltativo può essere nullo. Gli oggetti che contengono testo riservato richiedono una propria politica di accesso.

| Relazione | Campi principali |
|----|----|
| person | id PK, nome visualizzato, data nascita con precisione, stato anagrafico |
| community | id PK, group_id FK, kind, parent_id FK facoltativo, denominazione |
| membership | id PK, person_id FK, community_id FK, ruolo, intervallo |
| branch_period | id PK, person_id FK, branch, intervallo, entry_reason, exit_reason, method_version_id FK |
| phase_period | id PK, branch_period_id FK, phase, intervallo, entry_basis, completion_id FK facoltativo |
| objective | id PK, branch_period_id FK, kind, current_revision_id FK, lifecycle, access_policy_id FK |
| commitment | id PK, branch_period_id FK, kind, current_revision_id FK, status, assunzione, termine previsto |
| objective_commitment | objective_id FK, commitment_id FK, motivazione del collegamento |
| experience | id PK, comunità facoltativa, tipo, titolo, intervallo, contesto scout o esterno |
| experience_participation | id PK, experience_id FK, person_id FK, ruolo, intervallo |
| commitment_experience | commitment_id FK, experience_id FK, contributo personale |
| review_session | id PK, data, venue_kind, community_id FK facoltativo, responsabile registrazione |
| review_item | id PK, session_id FK, person_id FK, oggetto verificato, outcome, testo e access_policy_id FK |
| recognition | id PK, person_id o community_id, kind, catalog_version_id FK facoltativo, data, review_item_id FK facoltativo |
| competence_path | id PK, owner_type, person_id o community_id, catalog_version_id FK, stato, progetto |
| path_mentor | path_id FK, person_id o external_contact_id FK, ruolo, intervallo |
| season_lc | id PK, community_id FK, tipo, date previste ed effettive, stato |
| season_participation | id PK, season_id FK, person_id FK, phase_period_id FK |
| point_of_road | id PK, branch_period_id FK, periodo, stato, sintesi delle quattro fasi, access_policy_id FK |
| event_participation | id PK, event_edition_id FK, person_id FK, stato, preparazione, restituzione |
| transition | id PK, person_id FK, origine FK, destinazione FK, data, motivazione, review_id FK facoltativo |
| closing_process_rs | id PK, branch_period_id FK, stato, closure_kind facoltativo, richiesta, riconoscimento, cerimonia |
| content_revision | id PK, entity_id, numero, contenuto, autore educativo, inserito_da, validità, recorded_at |
| domain_event | id PK, aggregate_id, aggregate_version, event_type, occurred_at, recorded_at, actor_id, payload_version |
| access_policy | id PK, scope, destinatari, validità e regole di trasferimento |

Per specialità collettive utilizzare un titolare esclusivo: esattamente uno fra person_id e community_id. Nel database introdurre un vincolo CHECK coerente con owner_type. Per gli altri riconoscimenti il tipo determina il titolare ammesso.

I riferimenti generici “oggetto verificato” ed “entity_id” descrivono una generalizzazione concettuale. In un database relazionale vanno realizzati con un supertipo referenziabile oppure con tabelle di collegamento specifiche; una coppia libera “nome tabella + id” senza integrità referenziale non è sufficiente.

Aggiungere tabelle di collegamento per dimensioni educative, ambiti, obiettivi dei Punti della strada, specialità collegate a brevetti e partecipazioni a percorsi collettivi. Separare le versioni del catalogo dalle istanze di percorso delle persone.

### 16.4 Dati obbligatori progressivi

Una bozza richiede soltanto titolare, tipo e formulazione iniziale. Un impegno concordato richiede formulazione concreta, criterio di verifica, comunità o contesto, attribuzione della scelta e riferimento temporale; per E/G e R/S deve essere espresso un limite temporale. In L/C il riferimento può essere la stagione insieme a un tempo personale concordato.

Una verifica registrata richiede data o precisione storica dichiarata, oggetto, sede, contributo della persona oppure indicazione che non è documentato, esito e registrante. Un riconoscimento corrente richiede le informazioni della sede metodologica; un riconoscimento importato può avere evidenza incompleta, resa esplicita.

Non inventare obbligatorietà documentali attribuendole al regolamento: firme digitali, fotografie, allegati e approvazioni in app non sono richiesti dal testo analizzato.

## 17 Macchine a stati

### 17.1 Contratto comune delle transizioni

Ogni comando di transizione contiene identificativo dell’oggetto, versione attesa, chiave di idempotenza, data educativa, eventuale motivazione e riferimenti alle verifiche. Il server controlla autorizzazione, stato di origine, integrità dei riferimenti e condizioni applicabili; quindi aggiorna stato e storico nella stessa transazione.

La transizione produce un evento esplicito. Una semplice modifica al testo non deve simulare un passaggio educativo. Le notifiche partono dopo il commit e rispettano la visibilità dell’oggetto.

### 17.2 Impegno personale

| Origine | Comando e destinazione | Condizioni ed effetti |
|----|----|----|
| DRAFT | Concorda → AGREED | Formulazione, titolare, criterio e tempi coerenti; registrare chi ha formulato e condiviso |
| AGREED | Avvia → ACTIVE | Data di avvio; non richiede una presenza o fotografia |
| ACTIVE | Proponi verifica → READY_FOR_REVIEW | Esperienze o resoconto disponibili; la richiesta non certifica il risultato |
| READY_FOR_REVIEW | Prosegui → ACTIVE | Verifica intermedia o richiesta di ulteriore esperienza |
| READY_FOR_REVIEW | Concludi → CLOSED | Verifica registrata e relativo esito, senza automatismi su tappe |
| DRAFT, AGREED, ACTIVE, READY_FOR_REVIEW | Interrompi → STOPPED | Motivazione e conservazione del lavoro già svolto |
| AGREED, ACTIVE, READY_FOR_REVIEW | Riformula → stesso stato o AGREED | Nuova revisione; se cambia l’accordo, riportare ad AGREED |
| CLOSED, STOPPED | Riprendi come nuovo impegno | Nuova istanza collegata alla precedente; la chiusura storica resta |

Non riaprire silenziosamente un impegno concluso: una nuova esperienza può motivare un nuovo ciclo. Un errore materiale nella chiusura segue invece il flusso di rettifica, non quello educativo.

### 17.3 Obiettivo e meta

Stati: DRAFT, ACTIVE, REVIEWED, CLOSED, SUPERSEDED.

DRAFT → ACTIVE registra la formulazione condivisa. ACTIVE → REVIEWED registra una verifica. Da REVIEWED si può tornare ACTIVE, mantenendo lo stesso obiettivo; si può passare CLOSED, quando il ciclo è concluso; oppure SUPERSEDED, collegando un obiettivo riformulato. Una revisione del solo testo mantiene l’identità, mentre un cambiamento sostanziale di finalità crea un successore.

L’esito educativo è distinto dallo stato: CLOSED non significa necessariamente “raggiunto”. Il sistema conserva data, esito e ragione della chiusura. Le mete E/G si collegano alle verifiche nel Consiglio della Legge; gli obiettivi R/S alla loro storia nei Punti della strada.

### 17.4 Percorso di specialità o brevetto

| Origine | Comando e destinazione | Condizioni ed effetti |
|----|----|----|
| PROPOSED | Concorda progetto → IN_PROGRESS | Voce di catalogo corretta, titolare e progetto personale o collettivo |
| IN_PROGRESS | Richiedi verifica → TO_REVIEW | Collegamenti alle esperienze; accompagnatori quando previsti |
| TO_REVIEW | Prosegui → IN_PROGRESS | Osservazioni e indicazioni della verifica |
| TO_REVIEW | Riconosci → RECOGNIZED | Verifica e sede appropriate; creazione del riconoscimento |
| PROPOSED, IN_PROGRESS, TO_REVIEW | Interrompi → STOPPED | Ragione documentata; nessun riconoscimento attribuito |
| RECOGNIZED | Registra utilizzo della competenza → RECOGNIZED | Nuove esperienze e ruoli, senza azzerare la conquista |

Per E/G specialità e brevetti il riconoscimento richiama il Consiglio della Legge. Per L/C la fonte descrive prove concordate e verifica con i capi: non importare automaticamente la procedura E/G. Per la specialità di squadriglia il titolare è collettivo e le condizioni specifiche vanno completate con l’art. 18 E/G.

La consegna del distintivo è un evento collegato, con data propria; non serve uno stato unico “distintivo consegnato” che sostituisca il riconoscimento.

### 17.5 Stagione L C e conquista

La stagione di unità segue PLANNED → OPEN → CLOSED. L’apertura registra il lancio e il riferimento al percorso di accoglienza e Promesse; la chiusura registra il termine effettivo. Una stagione può essere annullata prima dell’avvio con stato CANCELLED.

La partecipazione personale registra separatamente prede o voli e riconoscimento del momento. Una chiusura di stagione con percorsi non conclusi produce un’anomalia da rileggere con i capi, mai riconoscimenti automatici. L’interfaccia deve favorire la revisione durante la stagione, prima delle vacanze.

Il momento L/C prevalente è conservato come periodo, mentre la conquista del relativo distintivo è un riconoscimento. Non derivare il momento attuale soltanto dall’ultimo distintivo posseduto, soprattutto nei nuovi ingressi e nei percorsi abbreviati.

### 17.6 Tappe E G e passaggi di momento L C

Per le tappe E/G, la macchina educativa ordinaria è DISCOVERY → COMPETENCE → RESPONSIBILITY. Ogni freccia è una decisione riconosciuta nel contesto previsto dal metodo, registrata tramite un comando e una verifica. La conclusione di RESPONSIBILITY genera phase_completed ma non chiude branch_period.

Per L/C i tre momenti hanno lo stesso ordine pedagogico, ma la conquista del distintivo e il passaggio al successivo momento restano dati distinguibili. La progressione del bambino non va ridotta all’apertura o chiusura della stagione.

Il comando PlaceAfterLateEntry gestisce un ingresso in età superiore: richiede evidenza del primo percorso di scoperta, Promessa secondo quanto previsto dalla branca, collocamento educativo e motivazione. Può assegnare il momento o la tappa adeguata senza creare periodi o riconoscimenti intermedi mai vissuti. Questo comando non è una scorciatoia ordinaria per saltare tappe.

Sono da evitare transizioni di “retrocessione” punitive. Correggere un errore di registrazione è un’operazione amministrativa tracciata, distinta dal cambiare retroattivamente il valore del cammino educativo.

### 17.7 Passi R S e Punto della strada

Per i passi R/S:

- DISCOVERY → COMPETENCE richiede la firma della Carta di clan come snodo educativo, collegata alla versione del testo;

- COMPETENCE → RESPONSIBILITY registra l’avvio del confronto esplicito sulle scelte della Partenza, condiviso con il clan/fuoco;

- RESPONSIBILITY non passa automaticamente a un presunto livello “PARTENZA”: il procedimento conclusivo è separato.

La firma e l’avvio della competenza devono essere registrati atomicamente quando il dato è corrente e completo. Per una storia importata, una data ignota resta ignota: si può conoscere il passo attuale senza inventare il giorno della firma.

Il Punto della strada ha stati operativi DRAFT, IN_PROGRESS, SHARED, CLOSED. Le quattro fasi coscienza, confronto, progetto e programma sono componenti del contenuto. SHARED significa che una sintesi è stata condivisa con destinatari espliciti; non che tutte le note siano diventate accessibili alla comunità. CLOSED significa che quel momento di rilettura è concluso, mentre obiettivi e impegni possono continuare.

### 17.8 Partecipazione a un evento

Stati proposti: PROPOSED → AGREED → REGISTERED → ATTENDED → REVIEWED. Sono possibili CANCELLED prima della partecipazione e NOT_ATTENDED dopo la data dell’evento, se la persona non ha partecipato. Se un evento non prevede iscrizione, AGREED può passare direttamente ad ATTENDED.

La verifica di restituzione completa il ciclo applicativo, non assegna automaticamente competenze o riconoscimenti. Una partecipazione parziale va registrata con durata e nota; per Piccole Orme richiede una valutazione esplicita su come rappresentare l’esperienza, senza far decidere al conteggio automatico se la regola della singola partecipazione sia stata soddisfatta. Questa casistica non è disciplinata nel dettaglio dalle pagine esaminate.

### 17.9 Passaggio fra branche

| Origine | Comando e destinazione | Effetto |
|----|----|----|
| PLANNED | Concorda → AGREED | Origine, destinazione e sintesi educativa condivisibile |
| AGREED | Esegui → EXECUTED | Chiusura del periodo precedente e apertura del successivo nella stessa transazione |
| PLANNED, AGREED | Annulla → CANCELLED | Nessuna modifica alle appartenenze effettive |
| EXECUTED | Rettifica | Evento compensativo e aggiornamento delle proiezioni; mai cancellazione silenziosa |

La cerimonia può avere una data diversa dalla decorrenza amministrativa: registrarle separatamente. Il trasferimento in un’altra unità della stessa branca modifica l’appartenenza, senza creare automaticamente un passaggio di branca.

### 17.10 Conclusione del percorso R S

Stati del discernimento: OPEN → REQUESTED → RECOGNIZED → CELEBRATED → CLOSED. Questa sequenza è una rappresentazione tecnica della Partenza, non una serie di nuovi riti o obblighi formali introdotti nell’associazione.

REQUESTED registra la richiesta del rover o della scolta. RECOGNIZED registra il riconoscimento da parte dei capi e dell’assistente ecclesiastico. CELEBRATED registra la cerimonia con la Comunità R/S. CLOSED chiude il periodo educativo alla data concordata. Se questi momenti coincidono, un solo comando può registrarli nella stessa transazione, senza costringere a quattro operazioni manuali.

Prima del riconoscimento è possibile tornare a OPEN per continuare il discernimento, conservando la richiesta precedente. La conclusione con saluto fraterno segue un ramo distinto, concordato con la persona e la comunità, e imposta closure_kind = SALUTO_FRATERNO. Interruzione e trasferimento sono uscite diverse: non devono essere riclassificati come “Partenza negata”.

Le decisioni già riconosciute non vengono revocate dall’app per valutazioni successive. Errori fattuali, duplicati e date scorrette seguono il flusso di rettifica con motivazione.

## 18 Storicizzazione e consistenza

### 18.1 Due tempi distinti

Ogni evento educativo deve distinguere quando è accaduto e quando è stato registrato. Esempio: una specialità conseguita il 12 giugno e inserita il 20 settembre conserva entrambe le date. Una rettifica del 25 settembre aggiunge un nuovo fatto di registrazione senza far apparire che la correzione esistesse a giugno.

Per contenuti revisionabili conservare valid_from e valid_to, oltre a recorded_at. Per dati particolarmente rilevanti può essere utile una gestione bitemporale completa; non è indispensabile applicarla a ogni tabella nella prima versione.

La timeline ordinaria usa il tempo educativo. L’audit usa il tempo di registrazione. Una vista “come conosciuto al giorno X” deve distinguersi da “percorso effettivo al giorno X”.

### 18.2 Eventi di dominio

| Evento proposto | Contenuto essenziale |
|----|----|
| BranchPeriodOpened / Closed | Persona, branca, periodo, ragione e data |
| PhaseEntered / PhaseCompleted | Momento o tappa, base educativa e verifica collegata |
| PromiseMade | Persona, contesto, data e tipo di Promessa |
| CommitmentAgreed / Revised | Impegno, revisione, autore educativo e tempi |
| ExperienceLinked | Collegamento esplicito fra esperienza e percorso |
| ReviewRecorded | Verifica, oggetti, sede, esito e riferimenti di accesso |
| RecognitionGranted | Tipo, titolare, data, catalogo e versione |
| InsigniaDelivered | Segno, persona, data e evento educativo collegato |
| ClanCharterSigned | Persona, versione della Carta e data |
| PointOfRoadClosed | Punto della strada e riferimenti a obiettivi e impegni |
| EventAttended / Reviewed | Edizione, persona, partecipazione e restituzione |
| BranchTransitionExecuted | Periodi origine/destinazione, data e sintesi autorizzata |
| DepartureRecognized / Celebrated | Percorso conclusivo, date, soggetti e riferimenti |
| RecordCorrected / Superseded | Record precedente, correzione, motivazione e autore |

Non duplicare nei payload dell’audit tutte le note personali. Conservare riferimenti e versioni; un registro append-only pieno di contenuti delicati renderebbe più complessa la gestione della loro visibilità e rimozione. La stabilità dello storico non impone conservazione perpetua indiscriminata dei contenuti.

### 18.3 Invarianti tecnici

1.  Una persona mantiene lo stesso identificativo nei trasferimenti.

2.  Nella proposta standard esiste un solo periodo di branca effettivo attivo per persona; le attività preparatorie interbranca non ne aprono un secondo. Le importazioni conflittuali vengono segnalate e risolte.

3.  Un periodo di progressione appartiene a un periodo di branca compatibile; nell’ordinario non si sovrappone a un altro periodo prevalente.

4.  Tutte le associazioni personali devono riferirsi alla stessa persona, salvo oggetti dichiaratamente collettivi.

5.  Per un oggetto collettivo il titolare è una comunità; le partecipazioni sono separate.

6.  Date di fine precedenti all’inizio sono respinte; date parziali richiedono controlli compatibili con la loro precisione.

7.  Lo stato corrente è coerente con l’ultima versione accettata; non è aggiornabile liberamente da un campo generico dell’interfaccia.

8.  Una voce di catalogo referenziata non viene eliminata fisicamente: si può ritirare dalle nuove scelte e mantenere nello storico.

9.  Una transizione riconosciuta non viene generata da una modifica anagrafica, dal compleanno o dal conteggio delle presenze.

10. Le concessioni di accesso non si ereditano automaticamente da tutte le comunità collegate.

I vincoli 2 e 3 sono scelte strutturali proposte, da confermare in base al funzionamento dell’app. Non rappresentano nuove norme associative.

### 18.4 Rettifiche e dati pregressi

Distinguere quattro operazioni:

- correzione materiale, come una data o un errore di trascrizione;

- revisione educativa, come la riformulazione di un impegno;

- importazione storica, con informazioni incomplete;

- rimozione o limitazione di contenuti secondo le politiche definite.

Una rettifica richiede identificativo del record corretto, motivo, autore, versione attesa e nuovi valori. Il vecchio record resta collegato per la tracciabilità, con visibilità appropriata. Le proiezioni correnti devono escludere i record superati dai conteggi ordinari.

L’importazione non deve passare artificialmente per tutti gli stati correnti. Un comando dedicato registra direttamente un fatto storico, con provenienza, precisione della data e grado di documentazione. Un riconoscimento senza verbale storico non va trasformato in un riconoscimento inesistente; va rappresentato come documentato parzialmente.

### 18.5 Concorrenza e sincronizzazione

Ogni aggregato usa una versione crescente. Se due capi aggiornano lo stesso impegno partendo dalla versione 4, il primo aggiornamento produce la 5; il secondo riceve un conflitto e deve confrontare le modifiche. Non applicare “vince l’ultimo” a verifiche, riconoscimenti e passaggi.

La chiave di idempotenza impedisce che un doppio invio crei due Promesse, firme, partecipazioni o riconoscimenti. Non usare nome e data come unica chiave di deduplicazione: persone ed eventi diversi possono condividerli.

Per il funzionamento offline, le bozze possono essere locali e sincronizzabili. Le transizioni con effetti su periodi, riconoscimenti e accessi richiedono controllo sul server. Lo stato “in attesa di sincronizzazione” è tecnico e non deve essere confuso con “conquista in attesa di verifica”.

## 19 Contratti applicativi e criteri di accettazione

### 19.1 Comandi applicativi

In un’API orientata alle risorse, i comandi significativi possono essere esposti come operazioni specifiche invece di un generico aggiornamento del campo stato.

| Comando | Input caratteristico | Risultato |
|----|----|----|
| AgreeCommitment | Impegno, revisione, tempi, autore e contesto | Stato concordato e nuova versione |
| RecordReview | Sede, oggetti, contributi, esito e visibilità | Verifica storicizzata |
| RecognizeCompetence | Percorso, verifica, data | Riconoscimento, evento e percorso aggiornato |
| EnterPhase | Periodo, fase destinazione, verifica o collocamento motivato | Nuovo periodo di progressione |
| SignClanCharter | Persona, versione della Carta, data | Firma e avvio della competenza quando applicabile |
| ExecuteBranchTransition | Origine, destinazione, date e sintesi | Chiusura e apertura atomiche |
| RecognizeDeparture | Percorso R/S, richiesta, riconoscimento, soggetti e data | Evento di Partenza riconosciuta |
| CorrectHistoricalRecord | Record, versione, correzione e motivo | Revisione compensativa tracciata |

Ogni risposta distingue errore di integrità, avviso metodologico e informazione. Esempio: una data impossibile è un errore; un impegno oltre il termine pianificato è un invito alla verifica; un ragazzo senza brevetto richiede attenzione educativa, non l’attribuzione automatica di un esito negativo.

### 19.2 Interrogazioni necessarie

Il modello deve rispondere almeno a queste domande:

- Qual è il percorso attuale e quali dati lo sostengono?

- Quali impegni richiedono una verifica e in quale sede?

- Come è cambiata una meta e quali esperienze hanno motivato il cambiamento?

- Quali competenze sono riconosciute e quando sono state utilizzate per gli altri?

- Qual era l’appartenenza della persona al momento di un’esperienza?

- Quale testo della Carta di clan è stato firmato?

- La persona ha già partecipato alle Piccole Orme, anche in un altro Gruppo?

- Cosa è condivisibile con i nuovi capi e cosa deve restare riservato?

- Quali dati storici sono incompleti, rettificati o derivano da importazione?

- Quale regola metodologica e quale sua versione hanno orientato una registrazione?

### 19.3 Criteri tecnici aggiuntivi di accettazione

| Scenario | Criterio verificabile |
|----|----|
| Due invii dello stesso riconoscimento | Un solo effetto, grazie all’idempotenza |
| Aggiornamenti concorrenti | Conflitto esplicito, nessuna perdita silenziosa |
| Rettifica di una data | Timeline aggiornata e audit della correzione conservato |
| Passaggio interrotto durante il salvataggio | Nessuna situazione con origine chiusa e destinazione assente |
| Cambio del nome di una specialità nel catalogo | Il riconoscimento storico conserva versione e denominazione pertinenti |
| Trasferimento con note riservate | Nessun trasferimento implicito delle autorizzazioni |
| Esportazione comunitaria | Assenza di note, allegati e titoli non autorizzati |
| Importazione di una tappa senza data esatta | Precisione dichiarata; nessuna falsa data puntuale |
| Specialità di squadriglia conseguita | Nessuna duplicazione in specialità personali dei membri |
| Rettifica di una partecipazione Piccole Orme duplicata | Conteggio sui fatti effettivi correnti, storico del duplicato mantenuto |
| Firma della Carta inserita due volte | Nessuna doppia apertura dei passi di competenza |
| Conclusione della responsabilità E/G | Possibilità di ulteriori impegni nello stesso periodo di branca |
| Compleanno o cambio di anno scout | Nessuna transizione educativa automatica |

Questi criteri possono diventare test di dominio e di autorizzazione. Le valutazioni educative restano esempi da confrontare con i capi, non aspettative numeriche da automatizzare.

## Appendice A Cataloghi L C ed E G

I nomi seguenti sono trascritti dai cataloghi del PDF. I codici sono identificativi tecnici proposti per questo documento, non codici ufficiali AGESCI. I codici non devono essere rigenerati a ogni riordinamento e non devono essere riutilizzati per voci diverse. La declinazione del nome può essere adattata alla persona, come previsto negli allegati L/C ed E/G, mantenendo un’identità di catalogo stabile.

### A1 Momenti e riconoscimenti L C

Fonte: Allegato 2 L/C, p. 78; L/C art. 38, pp. 54–57.

| Codice proposto | Momento | Riconoscimento in Giungla | Riconoscimento in Bosco |
|----|----|----|----|
| LC01 | Scoperta | Lupo della legge | Coccinella del prato |
| LC02 | Competenza | Lupo della rupe | Coccinella del bosco |
| LC03 | Responsabilità | Lupo anziano | Coccinella della montagna |

La Promessa dispone di un distintivo proprio descritto nell’Allegato 1 L/C, p. 78; non è una quarta tappa. L’app deve distinguere il momento in corso dal riconoscimento conseguito. Gli asset grafici degli emblemi sono risorse del catalogo, non i suoi identificativi.

### A2 Tappe E G

Fonte: Allegato 1 E/G, p. 78.

| Codice proposto | Tappa          | Momento della consegna del distintivo |
|-----------------|----------------|---------------------------------------|
| EG01            | Scoperta       | Inizio del cammino nella tappa        |
| EG02            | Competenza     | Inizio del cammino nella tappa        |
| EG03            | Responsabilità | Inizio del cammino nella tappa        |

Il distintivo si compone di tre parti, una per tappa. La rappresentazione delle parti non modifica la distinzione tra avvio e conclusione del percorso.

### A3 Specialità L C

Fonte: Allegato 3 L/C, p. 79. Totale: 40 voci.

| Codice proposto | Denominazione nella fonte |
|-----------------|---------------------------|
| LCSP001         | Amico degli animali       |
| LCSP002         | Amico degli anziani       |
| LCSP003         | Amico del mare            |
| LCSP004         | Amico della natura        |
| LCSP005         | Amico di Aronne           |
| LCSP006         | Amico di Samuele          |
| LCSP007         | Amico di San Francesco    |
| LCSP008         | Artigiano                 |
| LCSP009         | Astronomo                 |
| LCSP010         | Atleta                    |
| LCSP011         | Attore                    |
| LCSP012         | Botanico                  |
| LCSP013         | Canterino                 |
| LCSP014         | Cercatore di tracce       |
| LCSP015         | Cittadino del mondo       |
| LCSP016         | Collezionista             |
| LCSP017         | Cuoco                     |
| LCSP018         | Disegnatore               |
| LCSP019         | Folclorista               |
| LCSP020         | Fotografo                 |
| LCSP021         | Giardiniere               |
| LCSP022         | Giocatore di squadra      |
| LCSP023         | Giocattolaio              |
| LCSP024         | Giornalista               |
| LCSP025         | Guida                     |
| LCSP026         | Infermiere                |
| LCSP027         | Kim                       |
| LCSP028         | Maestro dei giochi        |
| LCSP029         | Maestro del bosco         |
| LCSP030         | Maestro della salute      |
| LCSP031         | Maestro di danze          |
| LCSP032         | Mani abili                |
| LCSP033         | Massaio                   |
| LCSP034         | Meteorologo               |
| LCSP035         | Montanaro                 |
| LCSP036         | Musicista                 |
| LCSP037         | Ripara-Ricicla            |
| LCSP038         | Sarto                     |
| LCSP039         | Scaccia pericoli          |
| LCSP040         | Scrittore                 |

### A4 Specialità individuali E G

Fonte: Allegato 2 E/G, pp. 78–79. Totale: 65 voci. Si mantiene anche la forma “Lavoratore/ce in cuoio” riportata nella fonte; le denominazioni di interfaccia possono essere declinate senza alterare l’identità della voce.

| Codice proposto | Denominazione nella fonte |
|-----------------|---------------------------|
| EGSP001         | Allevatore                |
| EGSP002         | Alpinista                 |
| EGSP003         | Amico degli animali       |
| EGSP004         | Amico del quartiere       |
| EGSP005         | Archeologo                |
| EGSP006         | Artigiano                 |
| EGSP007         | Artista di strada         |
| EGSP008         | Astronomo                 |
| EGSP009         | Atleta                    |
| EGSP010         | Attore                    |
| EGSP011         | Battelliere               |
| EGSP012         | Boscaiolo                 |
| EGSP013         | Botanico                  |
| EGSP014         | Campeggiatore             |
| EGSP015         | Canoista                  |
| EGSP016         | Cantante                  |
| EGSP017         | Carpentiere navale        |
| EGSP018         | Ciclista                  |
| EGSP019         | Collezionista             |
| EGSP020         | Coltivatore               |
| EGSP021         | Corrispondente            |
| EGSP022         | Corrispondente radio      |
| EGSP023         | Cuoco                     |
| EGSP024         | Danzatore                 |
| EGSP025         | Disegnatore               |
| EGSP026         | Elettricista              |
| EGSP027         | Elettronico               |
| EGSP028         | Esperto del computer      |
| EGSP029         | Europeista                |
| EGSP030         | Falegname                 |
| EGSP031         | Fa tutto                  |
| EGSP032         | Folclorista               |
| EGSP033         | Fotografo                 |
| EGSP034         | Geologo                   |
| EGSP035         | Giardiniere               |
| EGSP036         | Giocattolaio              |
| EGSP037         | Grafico                   |
| EGSP038         | Guida                     |
| EGSP039         | Guida marina              |
| EGSP040         | Hebertista                |
| EGSP041         | Idraulico                 |
| EGSP042         | Infermiere                |
| EGSP043         | Interprete                |
| EGSP044         | Lavoratore/ce in cuoio    |
| EGSP045         | Maestro dei giochi        |
| EGSP046         | Maestro dei nodi          |
| EGSP047         | Meccanico                 |
| EGSP048         | Modellista                |
| EGSP049         | Muratore                  |
| EGSP050         | Musicista                 |
| EGSP051         | Nuotatore                 |
| EGSP052         | Osservatore               |
| EGSP053         | Osservatore meteo         |
| EGSP054         | Pescatore                 |
| EGSP055         | Pompiere                  |
| EGSP056         | Redattore                 |
| EGSP057         | Regista                   |
| EGSP058         | Sarto                     |
| EGSP059         | Scenografo                |
| EGSP060         | Segnalatore               |
| EGSP061         | Servizio della Parola     |
| EGSP062         | Servizio liturgico        |
| EGSP063         | Servizio missionario      |
| EGSP064         | Topografo                 |
| EGSP065         | Velista                   |

### A5 Specialità di squadriglia

Fonte: Allegato 3 E/G, p. 79. Totale: 12 voci. Il titolare del percorso è la squadriglia; per ciascun ragazzo si documenta il contributo personale.

| Codice proposto | Denominazione nella fonte |
|-----------------|---------------------------|
| EGSQ001         | Alpinismo                 |
| EGSQ002         | Artigianato               |
| EGSQ003         | Campismo                  |
| EGSQ004         | Civitas                   |
| EGSQ005         | Esplorazione              |
| EGSQ006         | Espressione               |
| EGSQ007         | Giornalismo               |
| EGSQ008         | Internazionale            |
| EGSQ009         | Natura                    |
| EGSQ010         | Nautica                   |
| EGSQ011         | Olimpia                   |
| EGSQ012         | Pronto Intervento         |

### A6 Brevetti di competenza E G

Fonte: Allegato 4 E/G, pp. 79–80. Totale: 15 voci.

| Codice proposto | Denominazione nella fonte |
|-----------------|---------------------------|
| EGBR001         | Animatore sportivo        |
| EGBR002         | Artista                   |
| EGBR003         | Cittadino del mondo       |
| EGBR004         | Esploratore delle acque   |
| EGBR005         | Giornalista               |
| EGBR006         | Grafico multimediale      |
| EGBR007         | Guida alpina              |
| EGBR008         | Liturgista                |
| EGBR009         | Maestro delle tecnologie  |
| EGBR010         | Mani Abili                |
| EGBR011         | Naturalista               |
| EGBR012         | Pioniere                  |
| EGBR013         | Sherpa                    |
| EGBR014         | Soccorritore              |
| EGBR015         | Trappeur                  |

### A7 Struttura proposta del catalogo

Ogni voce richiede almeno identificativo stabile, branca, tipo, titolare personale o collettivo, denominazione della fonte, eventuali forme visualizzate, riferimento documentale e versione. Per i momenti e le tappe servono anche ordine pedagogico e regola di consegna del segno.

Un percorso individuale fa riferimento alla voce e alla sua versione, senza duplicare il catalogo. Ogni nuova edizione mantiene la provenienza e i nomi precedenti: un cambiamento di denominazione non deve modificare il testo del riconoscimento storico già registrato.

Le identiche denominazioni in cataloghi diversi non implicano equivalenza: “Artigiano” L/C e “Artigiano” E/G sono voci diverse; “Giornalista” L/C è una specialità, mentre “Giornalista” E/G è qui un brevetto. La relazione fra specialità e brevetti è definita nel progetto personale, non con una tabella universale di prerequisiti che la fonte non fornisce.

## Appendice B Eventi individuali e approfondimenti della competenza

### B1 Eventi E G

Fonte: Allegato 5 E/G, pp. 80–81.

| Tipo | Collocazione e organizzazione | Finalità e dati da collegare |
|----|----|----|
| Campi di specialità | Eventi regionali, fra scoperta e competenza | Conoscenza e approfondimento di singole specialità; collegare percorso e restituzione |
| Corsi di avviamento alla nautica | Settore Nautico, stessa fascia e finalità dei campi di specialità | Esperienze nautiche collegate agli interessi e al percorso personale |
| Campi di competenza | Eventi nazionali, Settore Competenze e Settore Nautico in accordo con Branca E/G; come impegno verso il brevetto | Approfondimento tecnico elevato, servizio e capacità di animare squadriglia e reparto |

L’allegato descrive i destinatari dei campi di competenza come ragazzi “in cammino verso la tappa della competenza”. Questa formulazione va conservata come indicazione della fonte e letta insieme al percorso verso il brevetto; non va trasformata senza confronto metodologico in un filtro rigido che escluda chi è già nella tappa.

### B2 Eventi R S

Fonte: Allegato 1 R/S, pp. 78–81. Le collocazioni sono indicazioni preferenziali nel percorso, da leggere insieme all’art. 38 R/S.

| Tipo | Passi indicati | Finalità prevalente |
|----|----|----|
| Laboratori, botteghe e workshop | Scoperta, competenza, responsabilità | Approfondire temi tecnici, servizio o impegno personale con esperti; durata solitamente di un fine settimana |
| Campi di specializzazione | Scoperta e competenza | Acquisire tecniche e manualità, riflettere sul fare e mettere le abilità al servizio |
| Campi Ora et Labora | Scoperta e competenza | Lavoro manuale, preghiera, condivisione e riflessione personale |
| Route dello spirito | Competenza e responsabilità | Crescita nella fede, conoscenza della Bibbia e della liturgia, con un esperto |
| Cantieri | Competenza e responsabilità | Motivazioni al servizio e sua dimensione politica nel territorio, condivisione e cammino di fede |
| ROSS | Inizio dei passi di responsabilità | Sintesi del cammino, discernimento vocazionale e orientamento al servizio in relazione alle tre scelte della Partenza |
| Eventi per Partenti | Responsabilità, verso la fine del cammino | Sintesi e verifica delle scelte di fede, impegno politico e servizio, confronto con coetanei e testimoni |

Ogni partecipazione resta collegata agli obiettivi personali. La presenza a un evento non dimostra da sola la maturazione di una scelta e non sostituisce la verifica con la comunità. La fonte usa per la ROSS formulazioni del nome lievemente differenti nel testo e nell’allegato: il catalogo può mantenere “ROSS” come sigla e registrare le denominazioni come varianti della stessa tipologia.

### B3 Elementi finali non trattati come progressione

L’Allegato 6 E/G, p. 81, propone nomi di squadriglia: riguarda la denominazione delle comunità, non specialità, brevetti o tappe. Non va inserito nel catalogo dei riconoscimenti. Gli indici finali, pp. 82–88, sono stati utilizzati per il controllo della struttura e dei rimandi.
