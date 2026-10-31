# Manuali (fase 8): analisi

Bozza del 30/10/2026, da completare con il maintainer. Le decisioni prese hanno il loro
codice nell'analisi dei requisiti (DEC-230…DEC-239); l'indice è una proposta.

Aggiornata il 31/10/2026 con quello che è stato fatto mentre il manuale era in pausa:
navigazione con il menu laterale e il menu del profilo (DEC-241…DEC-244, DEC-251),
impostazioni del sito e dei pagamenti (DEC-245…DEC-248, DEC-253), modelli delle email
(DEC-249, DEC-250), pagamenti PayPal e bonifici segnalati dalla famiglia (DEC-254, DEC-255),
lista d'attesa (DEC-256…DEC-263), nuova richiesta di iscrizione (DEC-264), calcolo del
codice fiscale (DEC-265), privacy policy, termini e avviso sui cookie (DEC-266).

## Decisioni prese

| Codice | Decisione |
| --- | --- |
| DEC-230 | Due documenti separati: il **manuale d'uso** per l'Avellino 1 e la **guida di installazione** per i gruppi che adottano QdC. Il manuale d'uso ha la precedenza. |
| DEC-231 | Entrambi su Read the Docs, da `docs/` nel repository (Sphinx con pagine Markdown, come il tema AGESCI Campania), una versione per ogni release. Niente wiki di GitHub (disattivato): non ha versioni e non produce PDF. |
| DEC-232 | Il manuale d'uso è anche un **unico PDF** allegato a ogni release (indice per profilo); la guida di installazione solo online. |
| DEC-233 | Il manuale è diviso in **sezioni complete per profilo**: ognuna si legge da sola, anche ripetendo le parti comuni; tutti vedono tutto il manuale, ma ogni funzione dice chiaramente chi la può usare. Profili: genitore; ragazzo (L/C, E/G, capo squadriglia, R/S); capo e staff di unità; capogruppo, tesorieri e amministratore tecnico. |
| DEC-234 | Gli indirizzi della piattaforma nel manuale sono riferiti a `https://qdc.avellino1.it` (non ancora attivo). |
| DEC-235 | Gli screenshot vengono dall'ambiente di sviluppo con i dati di prova (persone inventate), prodotti da uno **script automatico** che entra come ogni profilo e rifà tutte le immagini; si rigenerano quando cambia l'interfaccia. Mai dati veri. |
| DEC-236 | Tono informale: il manuale dà del «tu». Gli esempi usano le persone di prova dell'ambiente di sviluppo. |
| DEC-237 | La parte «ragazzo» copre tutte le branche che possono avere un account: L/C (sotto i 14 anni con il consenso del genitore, DEC-24), E/G con il capo squadriglia, R/S. Chi può entrare nell'app ha il suo manuale. |
| DEC-238 | Guida passo passo: ogni funzione con i passi da fare, nell'ordine, e le immagini dei passi. |
| DEC-239 | Screenshot in due formati: telefono, dentro una cornice che lo fa sembrare un telefono, e computer. |

## Indice proposto

Ogni sezione si apre con «Chi sei, cosa puoi fare» e un riquadro «Non puoi» dove serve
(per esempio: il genitore non vede le note riservate ai capi).

### Parte 0 — Introduzione (comune, breve)

Cos'è il Quaderno di Caccia; come si apre (`qdc.avellino1.it`, installazione sul telefono
come app); l'avviso sui cookie, la privacy policy e i termini (piè di pagina); come ci si
muove: la Home a gruppi, il menu laterale (sul telefono dal pulsante in alto), il menu
del profilo sotto il proprio nome (Il mio profilo, Privacy, Password e sicurezza, Le mie
quote, Blocca l'app, Esci), il percorso in alto con la tenda; come leggere il manuale:
trova il tuo profilo.

### Parte 1 — Genitore

1. Primo accesso: invito o codice di iscrizione, password, accesso con codice via email,
   passkey, Google e Apple.
2. Proteggere il telefono: PIN, impronta, cosa succede se lo perdi (revoca), uso senza rete.
3. I tuoi figli: scheda, dati di BuonaStrada e come chiedere una correzione.
4. Lista d'attesa: mettere in lista un figlio senza account, l'email con il link per
   correggere i dati o uscire, la conferma dopo due anni.
5. Iscrivere un figlio dall'app: dati richiesti (sesso, responsabilità genitoriale, il
   pulsante «Calcola» del codice fiscale), conferma dell'email, moduli firmati, scadenze.
6. Scheda sanitaria: farmaci, allergie, intolleranze, alimentazione; la scheda completa e la
   firma su carta; reperibilità per un evento.
7. Foto del profilo (ritaglio sul telefono).
8. Eventi e calendario: inviti, assenze, link al calendario del telefono.
9. Iscrizioni a eventi BuonaCaccia: modulo, liberatoria, foto.
10. Quote: cosa pagare, come pagare (contanti o carta ai capi, bonifico, PayPal con i suoi
    costi), segnalare un bonifico o un pagamento PayPal e caricarne la ricevuta, quote «in
    verifica», sconti di famiglia, ricevute, pendenze degli anni precedenti.
11. Progressione Personale di tuo figlio: cosa vedi (e cosa no).
12. Telefoni di squadriglia: quale numero vedono gli altri.
13. Bacheca degli avvisi.
14. Figli maggiorenni: cosa scelgono di farti vedere.
15. Privacy: le email che si possono disattivare.
16. I tuoi diritti sui dati: la privacy policy, richiesta, esportazione, cancellazione.

### Parte 2 — Ragazzo

Sotto i 14 anni l'account c'è solo con il consenso del genitore (DEC-24); dai 14 basta
l'invito (DEC-117). Per lupetti e coccinelle il testo è più semplice e con le parole
dell'ambientazione (giungla o bosco), da scrivere con lo staff L/C.

1. Primo accesso e protezione del telefono (come per i genitori, con le differenze).
2. Lupetti e coccinelle: la tua pista o il tuo sentiero, il momento, le prede o i voli, le
   specialità, le Piccole Orme.
3. La tua scheda e la tua foto.
4. La Progressione: E/G (sentiero, mete e impegni, specialità e brevetti, imprese e posti
   d'azione), R/S (Carta di clan, obiettivi, Punto della Strada con la parte riservata).
5. Capo squadriglia: la squadriglia, i telefoni, le note sui tuoi squadriglieri, le
   imprese di squadriglia, il Consiglio d'impresa.
6. Rover e scolte: proporre una nuova versione della Carta di clan.
7. Eventi, bacheca; Privacy: le email e, da maggiorenne, cosa vedono i genitori.

### Parte 3 — Capo e staff di unità

1. Accesso, protezione del telefono, uso senza rete al campo.
2. L'unità: membri, squadriglie (composizione, eccezioni), incarichi, ambientazione L/C,
   età minima e massima dell'unità.
3. Persone: scheda, correzioni da mandare in BuonaStrada, inviti, foto, il codice fiscale
   calcolato.
4. Lista d'attesa: per età nell'anno in corso e nel successivo, unità consigliata,
   possibili doppioni, mettere in lista una famiglia, contattato o da contattare,
   iscrizione con il link personale alla famiglia; richieste di iscrizione da accogliere.
5. Al campo: farmaci, allergie, regole sul rapporto con il minore (cosa sono, chi le
   vede — vedi appunto in TODO), telefoni.
6. Scheda sanitaria: trascrizione, firme su carta, stampa per un evento.
7. Note di staff e del capo squadriglia: chi le legge.
8. Eventi e presenze, anche offline; eventi BuonaCaccia e iscrizioni dei ragazzi.
9. Progressione Personale per branca: L/C (stagioni, prede e voli, momenti), E/G, R/S
   (Carta di clan, Punto della Strada); passaggi tra branche e loro rettifica.
10. Fascicolo di un anno e report per i passaggi.
11. Il fascicolo del capo: anni di servizio e formazione.
12. Bacheca: pubblicare per la tua unità e per la Comunità capi.
13. Le mie spese: rimborsi.
14. Usare l'app al posto di un ragazzo o di un genitore (per aiutarli).

### Parte 4 — Capogruppo, tesorieri, amministratore tecnico

1. Capogruppo: importazione da BuonaStrada e differenze (i dati ufficiali del gruppo
   corretti nell'app restano); iscrizioni dall'app, moduli vuoti e lista per BuonaStrada;
   nomine e ruoli; Impostazioni (nome e sigla del sito e del gruppo, titoli, riga del piè
   di pagina, intestazione delle stampe e logo, modi di pagamento); modelli delle email e
   piè di pagina comune; privacy policy e termini; correzioni; dispositivi;
   registro degli accessi; diritti degli interessati; impersonazione; chiusura dell'anno,
   archivio e rientri, fascicolo per un altro gruppo; bacheca per tutto il gruppo; carte
   delle unità.
2. Tesoriere di gruppo e di unità: tipi di quota, emissione, agevolazioni, pagamenti e
   ricevute, pendenze; pagamenti da verificare (PayPal e bonifici segnalati dalle
   famiglie, l'accreditato e la trattenuta PayPal); prima nota, casse (anche il conto
   PayPal), verifiche, rendiconto Modello D; estratto conto della banca.
3. Amministratore tecnico: l'amministrazione Django, cosa non contiene (dati sanitari);
   la modalità di prova delle email con Mailpit.

### Appendice

Tabella «Chi può fare cosa» (funzione × profilo), generata dalle regole del codice dove
possibile, così non si disallinea.

## Da decidere

1. Account Read the Docs: deciso dal maintainer il 31/10/2026: lo stesso account usato per
   altri progetti, con **due progetti separati** (manuale d'uso e guida di installazione)
   dallo stesso repository, ognuno con la sua cartella Sphinx e il suo `.readthedocs.yaml`.
   Restano da scegliere i nomi dei due progetti.
2. Guida di installazione: indice proposto il 31/10/2026 (da rivedere con il maintainer),
   in `docs/installazione/`, per chi installa una copia per il suo gruppo: cos'è e cosa
   serve; installazione (Docker o Podman, reverse proxy e HTTPS, `.env`, posta); primo
   avvio (amministratore tecnico, importazione da BuonaStrada, primo capogruppo, prime
   impostazioni); lavori giornalieri (cron); archivio sul Drive e chiave per i rientri;
   accesso con Google e Apple; server di prova con Mailpit; backup; aggiornamenti; dati
   personali e sicurezza. Il ripristino da un backup va scritto dopo averlo provato.
