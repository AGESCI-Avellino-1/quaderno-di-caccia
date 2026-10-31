# Cataloghi ufficiali

Dati di riferimento trascritti dai documenti AGESCI, da caricare nei modelli delle fasi
successive (quote e cassa, Progressione Personale). I codici (`LCSP001`, `EGBR015`, …)
sono identificativi tecnici di QdC, **non** codici ufficiali AGESCI: non vanno mai
riassegnati a voci diverse.

| File | Contenuto | Fonte | Fase |
| --- | --- | --- | --- |
| `modello_d_2024_2025.json` | Voci ministeriali e voci scout del Modello D (rendiconto di cassa); `selezionabile: false` = righe grigie | Vademecum AGESCI "Bilancio di Gruppo 2024–2025" | 2 — Quote e cassa (DEC-87) |
| `specialita_lc.json` | 40 specialità L/C | Regolamento metodologico 2026, Allegato 3 L/C | 4 — PP |
| `specialita_eg.json` | 65 specialità individuali E/G | Regolamento metodologico 2026, Allegato 2 E/G | 4 — PP |
| `specialita_squadriglia.json` | 12 specialità di squadriglia | Regolamento metodologico 2026, Allegato 3 E/G | 4 — PP (DEC-64) |
| `brevetti_eg.json` | 15 brevetti di competenza | Regolamento metodologico 2026, Allegato 4 E/G | 4 — PP |
| `comuni_istat.json` | 7.896 comuni italiani: nome, sigla della provincia, codice catastale (Belfiore), per proporre il codice fiscale | ISTAT, «Elenco dei comuni italiani», CC BY 4.0, scaricato il 31/10/2026 da istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.csv | calcolo del codice fiscale |

Regole (DEC-63, DEC-87):

- le voci non si cancellano mai: si ritirano e restano nello storico;
- ogni conquista o movimento conserva il nome della voce al momento della registrazione;
- il Modello D vale per anno di bilancio: un nuovo vademecum diventa un nuovo file.

`tests/test_cataloghi.py` verifica i conteggi: se un file cambia, il test va aggiornato
consapevolmente.

`comuni_istat.json` si aggiorna scaricando di nuovo l'elenco ISTAT (colonne «Denominazione
in italiano», «Sigla automobilistica», «Codice Catastale del comune»). Contiene solo i
comuni esistenti: per chi è nato in un comune poi soppresso o all'estero il codice
fiscale si scrive a mano.
