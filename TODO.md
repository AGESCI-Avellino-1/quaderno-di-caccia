# TODO — manutenzione

Situazione delle [issue](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues) e delle
[segnalazioni di sicurezza](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/security/advisories)
su GitHub, aggiornata il 06/11/2026 (ultima versione: v1.19.1). Le cose ancora aperte del periodo di
sviluppo sono in [TODO_SVILUPPO.md](TODO_SVILUPPO.md).

## Aperte

| Issue                                                                    | Titolo                                                       | Tipo           | Impatto | Difficoltà | Status |
| ------------------------------------------------------------------------ | ------------------------------------------------------------ | -------------- | ------- | ---------- | ------ |
| [#35](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/35) | Manuale d'uso online non personalizzato (DEC-371)            | Documentazione | Basso   | Media      | VAL    |
| [#34](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/34) | Barra fuori schermo su iPhone e foto che resta (DEC-370)     | Bug            | Medio   | Media      | VER    |
| [#33](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/33) | Guida di installazione: i menu di Google Cloud sono cambiati | Documentazione | Basso   | Bassa      | VER    |

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

| Issue | Titolo | Release |
| ----- | ------ | ------- |
| [#32](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/32) | Versione dell'app nel piè di pagina (DEC-369) | [v1.19.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.19.0) |
| [#30](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/30) | Assemblea: il punto Regolamento parte non spuntato (DEC-368) | [v1.18.1](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.18.1) |
| [#29](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/29) | Località: nome facoltativo e numero civico (DEC-366, DEC-367) | [v1.18.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.18.0) |
| [#28](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/28) | Azienda nel file dei contatti (DEC-361) | [v1.17.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.17.0) |
| [#27](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/27) | Ricerca degli indirizzi per le località (DEC-360) | [v1.17.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.17.0) |
| [#26](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/26) | Ordine del giorno in riunione (DEC-362…DEC-365) | [v1.17.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.17.0) |
| [#25](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/25) | Criteri di ammissione dell'anno | [v1.16.0](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/v1.16.0) |
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
| [#31](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/31) | Gestione casse | Già possibile: cassa comune di due unità collegate (DEC-288); banca e PayPal sono già del gruppo |

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
