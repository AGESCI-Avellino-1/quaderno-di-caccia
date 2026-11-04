# TODO — manutenzione

Situazione delle [issue](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues) e delle
[segnalazioni di sicurezza](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/security/advisories)
su GitHub, aggiornata il 04/11/2026 (ultima versione: v1.12.0). Le cose ancora aperte del periodo di
sviluppo sono in [TODO_SVILUPPO.md](TODO_SVILUPPO.md).

## Aperte

| Issue                                                                  | Titolo            | Tipo     | Impatto | Difficoltà | Status |
| ---------------------------------------------------------------------- | ----------------- | -------- | ------- | ---------- | ------ |
| [#13](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/13) | Verbali           | Funzione | Medio   | Alta       |        |
| [#12](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/12) | Errore in pdf PWA | Errore   | Basso   | Media      |        |

Nessuna segnalazione di sicurezza aperta.

### Note di prima valutazione

Stime fatte leggendo la issue e il codice, senza riprodurre nulla né decidere la soluzione.

- **#13 Verbali.** Impatto medio: è soprattutto codice nuovo, ma tocca permessi, riunioni,
  incarichi di squadriglia ed esportazione e cancellazione dei dati. Difficoltà alta: l'analisi non
  copre i verbali, quindi servono nuove decisioni (chi legge ogni tipo di verbale, come funziona
  l'assemblea dei soci con i genitori in rappresentanza dei minorenni). Esistono già l'editor
  (`EditorTesto.vue`), la pulizia dell'HTML (`impostazioni/html.py`) e la carta intestata
  (`core/stampa.py`); da verificare come passare dal testo dell'editor al PDF. Il file degli
  incarichi di squadriglia è sul computer del maintainer (`ignored/Incarichi di Squadriglia.pdf`) ed
  elenca: cassiere, cicala, cronista, guardiano dell'angolo, guardiano dello stile, guardiano del
  tempo, infermiere, liturgista, magazziniere (con eventuale aiuto), mercurio. Oggi l'app ha solo
  capo e vice capo squadriglia, uno per squadriglia. Deciso dal maintainer il 04/11/2026: un incarico
  può avere più persone e una persona può averne più di uno; chi scrive il verbale di squadriglia,
  anche se il cronista gira a rotazione, lo decide il capo squadriglia; l'infermiere è solo un ruolo
  e non vede nessun dato in più di prima.
- **#12 Errore in pdf PWA.** Impatto basso: riguarda solo come il frontend apre i file, non i dati
  né i permessi, anche se i punti da cambiare sono molti (i PDF e gli allegati si aprono con link
  diretti, sparsi in più pagine). Difficoltà media: il comportamento si può verificare solo su un
  iPhone vero, con la PWA installata.

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

| Status | Significato                                                                         |
| ------ | ----------------------------------------------------------------------------------- |
| vuoto  | Appena scaricata da GitHub                                                          |
| VAL    | Valutate complessità, fattibilità e cose da fare; implementazione non ancora avviata |
| WIP    | Da sviluppare, ci stiamo lavorando                                                  |
| VER    | Sviluppo completato, in attesa dell'ok del maintainer                               |
| CLSD   | Chiusa con la soluzione: passa alla tabella «Chiuse», con la release                |
| NO     | Non fattibile o si decide di non procedere: passa alla tabella «Non fatte»          |

- **Chiusura con soluzione:** dopo lo sviluppo la issue passa a VER. Quando il maintainer dà l'ok e
  la release è pubblicata, si chiude su GitHub indicando la release nel commento di chiusura.
- **Non si procede:** la issue passa a NO e si chiude su GitHub.
- **Segnalazioni di sicurezza non ancora pubbliche:** questo file è pubblico, quindi finché la
  segnalazione non è pubblicata si scrive solo il suo codice GHSA, senza titolo né valutazioni. I
  dettagli delle segnalazioni attive stanno in `TODO_security.md`, che resta sul computer del
  maintainer e non va su GitHub.
