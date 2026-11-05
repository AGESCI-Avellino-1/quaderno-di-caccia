# TODO — manutenzione

Situazione delle [issue](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues) e delle
[segnalazioni di sicurezza](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/security/advisories)
su GitHub, aggiornata il 05/11/2026 (ultima versione: v1.14.0). Le cose ancora aperte del periodo di
sviluppo sono in [TODO_SVILUPPO.md](TODO_SVILUPPO.md).

## Aperte

| Issue                                                                    | Titolo                 | Tipo     | Impatto | Difficoltà | Status |
| ------------------------------------------------------------------------ | ---------------------- | -------- | ------- | ---------- | ------ |
| [#23](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/23) | Scheda incarichi       | Funzione | Medio   | Media      | VAL    |
| [#22](https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/issues/22) | Animali di squadriglia | Funzione | Medio   | Media      | VAL    |

Nessuna segnalazione di sicurezza aperta.

### Da verificare sul server (senza issue)

Tempi della build con `scripts/aggiorna.sh`, passo per passo: dove va il tempo. Sul Mac (04/11) le
immagini della schermata di avvio prendono circa 2,5 s su 8,4 di `npm run build`. Da guardare: le
immagini (si possono generare in un passo Docker a parte, rifatto solo se cambiano logo, nome del
gruppo o `scripts/avvio.ts`), `npm ci` rifatto a ogni versione perché cambia il numero in
`package.json` e `package-lock.json`, l'immagine del backend.

## Valutazioni

Valutazioni fatte leggendo le issue, il codice e l'allegato di #22: nulla è ancora stato sviluppato e le
decisioni non sono ancora nell'analisi. Le due issue sono indipendenti; conviene partire da #23, più piccola.

### #23 Scheda incarichi

**Fattibile.** Impatto abbassato rispetto alla prima stima: un incarico nuovo non deve toccare quelli esistenti.

**Situazione.** I ruoli sono un elenco fisso nel codice (`RuoloIncarico`, 134 punti in 19 file), ma i permessi
guardano solo ruoli precisi: un incarico sconosciuto non dà nessun permesso. La PWA riceve già dall'API i ruoli
assegnabili e, per il PDF dell'organigramma, se sono educativi. Oggi «educativo» serve solo come scelta rapida di
quel PDF (DEC-318), con i non educativi scritti nel codice (`NON_EDUCATIVI`).

**Cose da fare.**

1. Modello degli incarichi definiti dal gruppo: nome, educativo o no, attivo o no. Uno già usato si disattiva e
   non si cancella, perché lo storico deve restare leggibile.
2. `Incarico` collegato al nuovo modello senza cambiare i ruoli esistenti; `ruolo` e `get_ruolo_display` restano
   l'unico punto di lettura, così le altre letture (43 tra fascicolo, percorso, email) non cambiano.
3. Controlli di `Incarico.clean`, `policy.puo_nominare` e `puo_definire_incarichi`, con i test di ogni ruolo.
4. Pagina dell'elenco per i capigruppo, scelta nell'assegnazione, organigramma e relativo PDF.
5. Fascicolo del capo, esportazione e trasferimento: portano il nome dell'incarico. Manuale e dati di prova.

**Da decidere.**

- Se i capigruppo possono cambiare anche «educativo» degli incarichi esistenti, oggi fissato da DEC-318.
- Se «educativo» serve anche ad altro, oltre al PDF.

**Deciso (maintainer, 05/11).** «Incarico» e «ruolo» sono la stessa cosa: un solo elenco. Gli incarichi nuovi non danno
nessun permesso, come quelli di squadriglia (DEC-321). Chi crea l'incarico sceglie se è di gruppo o
di unità, e se è di servizio o
aggiuntivo. Li ricevono solo i capi.
Un incarico di servizio di gruppo funziona come un servizio di supporto (DEC-293): esclude l'unità e gli altri
supporti e si chiude da solo quando il capo viene assegnato a un'unità. Uno di unità conta come lo staff per i
servizi: esclude i supporti e li chiude, ma senza i permessi dello staff.
Li definiscono e li assegnano solo i capigruppo.

### #22 Animali di squadriglia

**Fattibile.**

**L'allegato.** 93 animali (81 generali, 12 nautici), con PNG, SVG, un unico file di simboli e un CSV. Simboli e
righe del CSV corrispondono uno a uno, senza doppioni e senza script. Limiti trovati:

- `animali.svg` pesa 2,07 MB (769 KB compresso) e supera di poco il limite di 2 MB della cache della PWA, che
  lo salterebbe. Comunque peserebbe su ogni telefono: meglio i 93 SVG singoli (11-223 KB), scaricati quando servono.
- I colori sono solo nomi (24 diversi), mentre il simbolo vuole un codice come `#0a3d91`: la tabella va scritta.
- 11 animali hanno un colore solo, 13 non hanno il richiamo; 15 note parlano della fonte e non vanno mostrate.

**Situazione.** `Squadriglia.nome` è testo libero, unico nel reparto, e le altre API lo restituiscono come testo
(eventi, Progressione, turni). I nomi vecchi possono non coincidere: i dati di prova hanno «Pantere» e «Volpi», il
CSV «Pantera» e «Volpe».

**Cose da fare.**

1. Catalogo in `backend/data/cataloghi/` e modello degli animali, con permessi e test di ogni ruolo.
2. `Squadriglia.animale` facoltativo, con `nome` che resta e prende il nome dell'animale: le letture non cambiano.
3. Migrazione: si collegano i nomi uguali; gli altri restano e la pagina del reparto chiede di scegliere.
4. Scelta dell'animale alla creazione al posto del testo, pagina dell'elenco, tabella dei colori.
5. Componente con l'immagine e i campi nuovi nelle API, vicino al nome della squadriglia. Da provare offline.
6. `dati_di_prova`, schermate e manuale.

**Attenzione alla sicurezza.** Un SVG caricato da un utente può contenere script e nginx non ha una
Content-Security-Policy. La proposta è accettare solo PNG e JPEG, ricodificati con Pillow come le foto.

**Da decidere.**

- Di chi sono le immagini e se possono stare in un repository pubblico con licenza MIT.
- Se l'elenco è unico per il gruppo o per ogni reparto: la issue parla di unità, ma con due reparti gli animali
  aggiunti andrebbero rifatti.
- Se anche i capigruppo lo modificano: DEC-112 fa gestire loro le squadriglie, la issue dice solo lo staff.
- Se il nome si può ancora scrivere a mano e come si mostrano i nomi al plurale.
- Se i genitori vedono elenco e immagine, se l'elenco serve offline e cosa si mostra oltre all'immagine.
- Se i nautici si offrono a tutti: oggi l'unità non dice se è nautica.

## Chiuse

| Issue | Titolo | Release |
| ----- | ------ | ------- |
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
