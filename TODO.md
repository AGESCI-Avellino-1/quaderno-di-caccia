# TODO — manutenzione

Situazione delle [issue](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues) e delle
[segnalazioni di sicurezza](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/security/advisories)
su GitHub, aggiornata il 14/11/2026 (ultima versione: v1.29.1). Le cose ancora aperte del periodo di
sviluppo sono in [TODO_SVILUPPO.md](TODO_SVILUPPO.md).

## Aperte

| Issue                                                                    | Titolo                                                                              | Tipo          | Impatto | Difficoltà | Status |
| ------------------------------------------------------------------------ | ----------------------------------------------------------------------------------- | ------------- | ------- | ---------- | ------ |
| [#73](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/73) | Squadriglia creata senza animale, lo sceglie il capo squadriglia (DEC-409)          | Miglioramento | Medio   | Media      | VER    |
| [#74](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/74) | Notifica: dopo lo sblocco si torna all'ultima pagina, non a quella della notifica   | Correzione    | Medio   | Media      | VER    |
| [#75](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/75) | Riorganizzazione delle squadriglie in bozza, applicata a mano dallo staff (DEC-410) | Miglioramento | Alto    | Alta       | VER    |
| [#76](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/76) | Informazioni: versione di iOS sbagliata da iOS 26 in poi                            | Correzione    | Basso   | Bassa      | VER    |

Nessuna segnalazione di sicurezza aperta.

### Da verificare sul server (senza issue)

Tempi della build con `scripts/aggiorna.sh`, passo per passo: dove va il tempo. Sul Mac (04/11) le
immagini della schermata di avvio prendono circa 2,5 s su 8,4 di `npm run build`. Da guardare: le
immagini (si possono generare in un passo Docker a parte, rifatto solo se cambiano logo, nome del
gruppo o `scripts/avvio.ts`), `npm ci` rifatto a ogni versione perché cambia il numero in
`package.json` e `package-lock.json`, l'immagine del backend.

### Visti e non toccati (senza issue)

Le altre pagine pubbliche (Progetto Educativo, calendario, codice fiscale) consumano lo stesso contatore per indirizzo della
lista d'attesa (20 iscrizioni l'ora): su una rete condivisa potrebbero farla rifiutare.

La lista d'attesa dice «non secondo l'ordine di arrivo», il modello dei criteri (`documenti/criteri.py`) considera la data della
richiesta per ultima: da tenere coerenti se si cambia uno dei due.

## Chiuse

| Issue                                                                    | Titolo                                                                        | Release                                                                                 |
| ------------------------------------------------------------------------ | ----------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| [#72](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/72) | Unità sempre con tipo, nome e codice (DEC-408)                                | [v1.29.1](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.29.1) |
| [#71](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/71) | Unità collegate in una pagina sola, turni del gruppo (DEC-405, DEC-406)       | [v1.29.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.29.0) |
| [#70](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/70) | Dalla progressione all'unità; «Indietro» nelle pagine di dettaglio (DEC-404)  | [v1.29.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.29.0) |
| [#69](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/69) | Squadriglie e unità: correzioni (raggruppa #68, #70, #71)                     | [v1.29.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.29.0) |
| [#68](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/68) | Squadriglie archiviate solo se vuote; storia per i ragazzi (DEC-403, DEC-407) | [v1.29.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.29.0) |
| [#65](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/65) | Riunioni: di staff e di staff congiunti, online o miste (DEC-401, DEC-402)    | [v1.28.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.28.0) |
| [#64](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/64) | Eventi: «Campo · · Località» per gli eventi su BuonaCaccia                    | [v1.27.1](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.27.1) |
| [#63](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/63) | Capo con codice provvisorio abilitato come censito                            | [v1.27.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.27.0) |
| [#62](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/62) | Formazione capi: livello 1 con il codice socio provvisorio                    | [v1.27.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.27.0) |
| [#61](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/61) | BuonaCaccia: tipi di evento e vincoli di iscrizione                           | [v1.27.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.27.0) |
| [#60](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/60) | Ricerca mentre si scrive: eventi su BuonaCaccia e altri campi                 | [v1.26.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.26.0) |
| [#59](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/59) | BuonaCaccia: registrare più iscrizioni insieme (DEC-396)                      | [v1.25.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.25.0) |
| [#58](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/58) | Scelta di una persona: campo con ricerca (DEC-395)                            | [v1.25.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.25.0) |
| [#57](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/57) | BuonaCaccia: senza quota non serve segnare il pagamento (DEC-394)             | [v1.24.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.24.0) |
| [#56](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/56) | Testi: socio, Ragazzo/a e ragazzi/e al posto di ragazzo (DEC-393)             | [v1.24.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.24.0) |
| [#55](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/55) | BuonaCaccia: la data reale dei passi di un'iscrizione (DEC-392)               | [v1.24.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.24.0) |
| [#54](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/54) | BuonaCaccia: orario facoltativo e modifica dell'evento (DEC-391)              | [v1.24.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.24.0) |
| [#53](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/53) | BuonaCaccia: «Scaduta, manca la scheda» senza scheda                          | [v1.24.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.24.0) |
| [#52](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/52) | Eventi: pulsante Nuovo evento su BuonaCaccia (DEC-390)                        | [v1.24.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.24.0) |
| [#51](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/51) | Eventi su BuonaCaccia: link allo stato e link all'evento (DEC-389)            | [v1.24.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.24.0) |
| [#50](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/50) | Passkey: su iPhone non si crea se ne esiste già una sincronizzata (DEC-388)   | [v1.23.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.23.0) |
| [#49](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/49) | Pagina Informazioni, con i dati tecnici da copiare (DEC-387)                  | [v1.23.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.23.0) |
| [#48](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/48) | Avvisi esistenti solo a chi può agire (DEC-385)                               | [v1.22.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.22.0) |
| [#47](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/47) | Organigramma: incarichi di unità e capi in più unità (DEC-384)                | [v1.22.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.22.0) |
| [#46](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/46) | Menu: pagine dei gruppi e nuova disposizione delle voci (DEC-382, DEC-383)    | [v1.22.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.22.0) |
| [#45](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/45) | Progressione delle altre unità in sola lettura per i capi (DEC-381)           | [v1.22.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.22.0) |
| [#44](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/44) | Versione sul server nel piè di pagina e pulsante Aggiorna (DEC-380)           | [v1.22.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.22.0) |
| [#43](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/43) | Spese da rimborsare: voce, contatore e notifica (DEC-379, DEC-386)            | [v1.22.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.22.0) |
| [#42](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/42) | Unità in ordine di branca, ovunque compaiono (DEC-378)                        | [v1.22.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.22.0) |
| [#35](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/35) | Manuale d'uso online non personalizzato (DEC-371)                             | [v1.20.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.20.0) |
| [#39](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/39) | Notifiche: invio di prova, amministratori tecnici (DEC-377)                   | [v1.21.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.21.0) |
| [#38](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/38) | Verbali: nome del file PDF con titolo e data (DEC-376)                        | [v1.20.1](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.20.1) |
| [#37](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/37) | App installata su macOS: i file non si scaricano (DEC-375)                    | [v1.20.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.20.0) |
| [#36](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/36) | Verbali: segnaposto e anteprima (DEC-372…DEC-374)                             | [v1.20.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.20.0) |
| [#34](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/34) | Barra fuori schermo su iPhone e foto che resta (DEC-370)                      | [v1.19.1](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.19.1) |
| [#33](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/33) | Guida di installazione: i menu di Google Cloud sono cambiati                  | [v1.19.1](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.19.1) |
| [#32](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/32) | Versione dell'app nel piè di pagina (DEC-369)                                 | [v1.19.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.19.0) |
| [#30](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/30) | Assemblea: il punto Regolamento parte non spuntato (DEC-368)                  | [v1.18.1](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.18.1) |
| [#29](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/29) | Località: nome facoltativo e numero civico (DEC-366, DEC-367)                 | [v1.18.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.18.0) |
| [#28](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/28) | Azienda nel file dei contatti (DEC-361)                                       | [v1.17.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.17.0) |
| [#27](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/27) | Ricerca degli indirizzi per le località (DEC-360)                             | [v1.17.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.17.0) |
| [#26](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/26) | Ordine del giorno in riunione (DEC-362…DEC-365)                               | [v1.17.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.17.0) |
| [#25](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/25) | Criteri di ammissione dell'anno                                               | [v1.16.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.16.0) |
| [#23](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/23) | Scheda incarichi                                                              | [v1.15.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.15.0) |
| [#22](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/22) | Animali di squadriglia                                                        | [v1.15.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.15.0) |
| [#21](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/21) | Notifiche push sull'app installata                                            | [v1.14.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.14.0) |
| [#20](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/20) | Modelli di convocazione e verbali del gruppo su carta intestata               | [v1.14.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.14.0) |
| [#19](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/19) | Download: documenti del gruppo scaricabili in app                             | [v1.14.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.14.0) |
| [#18](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/18) | Progetto Educativo di Gruppo (PEG): caricamento e storico delle versioni      | [v1.14.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.14.0) |
| [#17](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/17) | Progetto del capo: inserimento e consultazione da parte della Co.Ca.          | [v1.14.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.14.0) |
| [#16](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/16) | Calendario: voce «Tutti i miei eventi» come selezione predefinita             | [v1.14.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.14.0) |
| [#15](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/15) | Schermata di avvio: durata minima configurabile (DEC-333)                     | [v1.13.1](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.13.1) |
| [#14](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/14) | Schermata di avvio                                                            | [v1.13.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.13.0) |
| [#13](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/13) | Verbali                                                                       | [v1.13.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.13.0) |
| [#12](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/12) | Errore in pdf PWA                                                             | [v1.12.1](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.12.1) |

## Non fatte

| Issue                                                                    | Titolo                         | Motivo                                                                                           |
| ------------------------------------------------------------------------ | ------------------------------ | ------------------------------------------------------------------------------------------------ |
| [#40](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/40) | Tutte le email arrivano doppie | Non era un problema dell'app: due indirizzi, con un inoltro verso la stessa casella              |
| [#41](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/41) | Le notifiche push non arrivano | Non era un problema: le notifiche arrivano                                                       |
| [#31](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/31) | Gestione casse                 | Già possibile: cassa comune di due unità collegate (DEC-288); banca e PayPal sono già del gruppo |

## Come si usa

Questo file si aggiorna su richiesta, leggendo la situazione su GitHub. Una richiesta nata fuori da
GitHub diventa prima una issue.

**Impatto** è il rischio di fare danni al codice esistente implementando la soluzione: quanto può
rompersi quello che oggi funziona.
**Difficoltà** è quanto è lungo e complicato realizzare la soluzione, a prescindere da quel rischio.
Le due cose sono indipendenti: spostare una decina di voci di menu può essere facile e toccare poco;
cambiare una riga in un punto da cui dipende tutta l'app è facile, ma ha un impatto alto.
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
