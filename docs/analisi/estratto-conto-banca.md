# Estratto conto bancario: note per la fase 6

Note raccolte il 29/10/2026 su un export reale dei movimenti. **Realizzato il 30/10/2026**
(fase 6, blocco 2): le decisioni sono DEC-221…DEC-224 nell'analisi, il codice in
`backend/apps/banca`. Qui non ci sono dati reali: solo la struttura del file.

Verificato sul file vero: la carta di un'unità compare come `CARTA N. ####` nei prelievi e
`CARTA ####` nei pagamenti POS (le ultime quattro cifre); l'ordinante di un bonifico
ricevuto si legge da `ORD.:` o `MITT.:`.

- **Esempio:** `ignored/Movimenti_Conto_27102026.xlsx`, un export dell'AGESCI Zona
  Hirpinia dalla stessa banca del gruppo. La cartella è esclusa da git e il file non va
  mai copiato nei test: per i test serve un file sintetico con la stessa struttura.
- **Richiesta del maintainer:** importare i movimenti e collegarli, dove possibile, a
  quote e altri versamenti dei soci.

## Struttura del file (XLSX, un foglio "Lista Movimenti")

| Righe | Contenuto |
| --- | --- |
| 1–5 | vuote (logo) |
| 6 (col. F) | avvertenza della banca |
| 7–23 (col. C etichetta, col. D valore, col. E importo) | `Intestatario conto:`, `Numero conto:`, `Filiale:`, `Saldo contabile iniziale al:` (data `gg.mm.aaaa` + importo), `Saldo contabile finale al:`, `Saldo disponibile  al (escluso Fido):` (due spazi), `Importo Fido:`, `Entrate/Uscite:`, `Ricerca Per:`, `Importo:`, `Tipologia movimenti selezionata:`, `Controvalore in:`, `I movimenti selezionati sono:` |
| 26 (col. D) | titolo della sezione `Operazioni contabilizzate` |
| 28 | intestazione: `Data contabile`, `Data valuta`, `Descrizione`, `Accrediti`, `Addebiti`, `Descrizione estesa`, `Effettuata tramite:` |
| 29 | `Saldo contabile iniziale in Euro`, importo in `Addebiti` |
| 30… | un movimento per riga, dal più recente |
| penultima della sezione | `Saldo contabile finale in Euro` |
| dopo | sezione `Operazioni non contabilizzate`, con intestazione `Data`, `Descrizione`, `Accrediti`, `Addebiti`, `Descrizione estesa` (vuota nell'esempio) |

Dettagli per il parser:

- le date dei movimenti sono celle data (datetime); le date dell'intestazione sono testo
  `gg.mm.aaaa`;
- gli importi sono numeri: accrediti positivi, **addebiti negativi**, nella colonna
  della loro parte (l'altra colonna è vuota);
- la colonna `Effettuata tramite:` è vuota nell'esempio;
- le righe si individuano dall'intestazione, non dal numero di riga: la parte iniziale
  può cambiare;
- un movimento si riconosce, per non importarlo due volte, da data contabile, importo e
  descrizione estesa (che contiene un codice dell'operazione).
- La coppia saldo iniziale e saldo finale serve per verificare l'importazione: il saldo
  iniziale più i movimenti deve dare il saldo finale. Può anche diventare una verifica
  di cassa del conto.

## Tipi di operazione (colonna `Descrizione`, testi della banca)

| Descrizione | Verso | Possibile trattamento (da decidere) |
| --- | --- | --- |
| ACCREDITO BEU CON CONTABILE | entrata | bonifico ricevuto: da abbinare a pagamenti di quote o ad altre entrate |
| BONIFICO ISTANTANEO DA VOI DISPOSTO | uscita | pagamento a fornitori o rimborsi |
| COSTO BONIFICO ISTANTANEO DA VOI DISPOSTO | uscita | spese bancarie (uscite A.2, "Oneri e servizi bancari") |
| DISPOSIZIONE DI BONIFICO | uscita | come sopra |
| COMMISSIONE DISPOSIZIONE DI BONIFICO | uscita | spese bancarie |
| CANONE MENSILE BASE E SERVIZI AGGIUNTIVI | uscita | spese bancarie |
| PRELIEVO CARTA DEBITO SU BANCHE DEL GRUPPO | uscita | giroconto dal conto alla cassa contanti di un'unità (DEC-88) |
| PAGAMENTO POS | uscita | spesa con la carta di un'unità |
| PAGAMENTO BOLLETTA CBILL | uscita | utenze o tributi |
| COMMISSIONE PAGAMENTO CBILL / PAGOPA | uscita | spese bancarie |

## Descrizione estesa di un bonifico ricevuto

Contiene dati personali (chi ha pagato, la causale): nessun log, nessun test con dati
reali. Gli elementi fissi, nell'ordine:

```
COD.DISP.: <codice> CASH <causale e riferimenti> Bonifico a Vostro favore disposto da:
MITT.: <ordinante> BENEF.: <beneficiario> BIC. <…> ORD.: <ordinante>
```

Il testo tra `CASH` e `Bonifico a Vostro favore` sembra essere la causale scritta da chi
paga; `MITT.:` e `ORD.:` indicano l'ordinante. Va confermato su più esempi, compresi i
bonifici fatti dalle famiglie del gruppo.

## Spunti per l'abbinamento con le quote (da discutere)

- **Proposte, mai abbinamenti automatici.** Il tesoriere conferma ogni abbinamento; un
  accredito si può dividere su più quote, come un pagamento (fase 2).
- **Criteri candidati:**
  - importo uguale al residuo di una quota o alla somma delle quote aperte di una
    famiglia;
  - ordinante simile al nome di un genitore o di un socio;
  - causale con il nome del socio, il codice socio o il mese della quota.
- **Pagamento già registrato a mano.** Il tesoriere potrebbe aver già registrato in
  QdC il bonifico (pagamento di fase 2 con metodo "bonifico"). In quel caso
  l'importazione deve proporre di **collegare** l'accredito al movimento esistente,
  non crearne un secondo.
- **Uscite.** Le uscite (canoni, commissioni) potrebbero avere una voce del Modello D
  proposta per tipo di operazione. I prelievi con la carta di unità diventano
  giroconti verso la cassa contanti di quell'unità.
- **Unità del movimento.** Per i pagamenti con carta di unità (DEC-85) bisogna capire
  dal file quale carta è stata usata: nell'esempio non c'è un campo dedicato, forse è
  nella descrizione estesa.
