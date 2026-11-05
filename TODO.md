# TODO — manutenzione

Situazione delle [issue](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues) e delle
[segnalazioni di sicurezza](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/security/advisories)
su GitHub, aggiornata il 05/11/2026 (ultima versione: v1.15.0). Le cose ancora aperte del periodo di
sviluppo sono in [TODO_SVILUPPO.md](TODO_SVILUPPO.md).

## Aperte

| Issue                                                                    | Titolo                 | Tipo     | Impatto | Difficoltà | Status |
| ------------------------------------------------------------------------ | ---------------------- | -------- | ------- | ---------- | ------ |
| [#25](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/25) | Criteri di ammissione dell'anno | Funzione | Basso   | Media      | VAL    |

Nessuna segnalazione di sicurezza aperta.

### Da verificare sul server (senza issue)

Tempi della build con `scripts/aggiorna.sh`, passo per passo: dove va il tempo. Sul Mac (04/11) le
immagini della schermata di avvio prendono circa 2,5 s su 8,4 di `npm run build`. Da guardare: le
immagini (si possono generare in un passo Docker a parte, rifatto solo se cambiano logo, nome del
gruppo o `scripts/avvio.ts`), `npm ci` rifatto a ogni versione perché cambia il numero in
`package.json` e `package-lock.json`, l'immagine del backend.

## Valutazioni

Nulla è ancora stato sviluppato.

### #25 Criteri di ammissione dell'anno

**Fattibile.** Il modello è il Progetto Educativo di Gruppo (DEC-343, DEC-344), che ha già versioni, Download, pagina
pubblica e scaricamento senza account con un limite alle richieste.

**Situazione.** Il rifiuto di una richiesta di iscrizione chiede già un motivo e lo manda via email (`iscrizioni.servizi.rifiuta`),
ma senza scadenza né legame coi criteri. La lista d'attesa è pubblica (`ListaAttesaView.vue`). Le unità hanno età minima e
massima (DEC-260), non un numero massimo di soci.

**Norme.** Il Codice del Terzo settore chiede requisiti di ammissione con criteri non discriminatori (art. 21), letto su fonti
secondarie. Il rigetto va motivato e comunicato entro sessanta giorni: lo prevede lo Statuto (maintainer, 05/11).

**Cose da fare.**

1. Documento per anno associativo con le sue versioni, data di inizio, riferimento al verbale della Co.Ca., testo pulito sul
   server come per le email (`html.pulisci`), PDF sulla carta intestata e permessi in `policy.py`.
2. Voce in Download e collegamento nella pagina pubblica della lista d'attesa, con scaricamento senza account.
3. Promemoria annuale, con `promemoria_fine_anno` o accanto a esso.
4. Test di ogni ruolo, manuale e dati di prova.

**Da decidere.**

- Cosa si mostra se per l'anno in corso non c'è ancora.
- Se servono anche il numero massimo per unità, con un avviso all'approvazione, e la scadenza dei sessanta giorni sul rifiuto.
- Se l'app prepara anche la lettera alla Zona.

**Deciso (maintainer, 05/11).** Nel testo nessuna esclusione per diagnosi: la Co.Ca. valuta caso per caso e motiva l'esito. Il
documento si compila nell'app sulla carta intestata, partendo dal testo del modello, modificabile con l'editor di testo
(`EditorTesto.vue`). Se il testo cambia si indica da quando vale la nuova versione: le altre versioni dello stesso anno
restano visibili, ognuna con la data fino a cui è valida.
Lo compilano i capigruppo. Lo vedono tutti in Download e, senza account, dalla lista d'attesa, con tutte le versioni dell'anno.

## Chiuse

| Issue | Titolo | Release |
| ----- | ------ | ------- |
| [#23](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/23) | Scheda incarichi | [v1.15.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.15.0) |
| [#22](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/22) | Animali di squadriglia | [v1.15.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.15.0) |
| [#21](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/21) | Notifiche push sull'app installata | [v1.14.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.14.0) |
| [#20](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/20) | Modelli di convocazione e verbali del gruppo su carta intestata | [v1.14.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.14.0) |
| [#19](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/19) | Download: documenti del gruppo scaricabili in app | [v1.14.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.14.0) |
| [#18](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/18) | Progetto Educativo di Gruppo (PEG): caricamento e storico delle versioni | [v1.14.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.14.0) |
| [#17](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/17) | Progetto del capo: inserimento e consultazione da parte della Co.Ca. | [v1.14.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.14.0) |
| [#16](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/16) | Calendario: voce «Tutti i miei eventi» come selezione predefinita | [v1.14.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.14.0) |
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
