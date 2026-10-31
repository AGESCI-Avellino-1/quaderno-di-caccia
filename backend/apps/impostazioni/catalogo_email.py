"""Every email the platform sends, with its default text (DEC-250).

The default texts are the ones the app sent before the templates existed. Indispensable
placeholders are what makes the email useful: links, codes, dates to respect, the data
or the text being communicated. A new email = a new entry here, then `email.messaggio()`
where it is sent.
"""

from .email import Segnaposto, TipoEmail


def _link(descrizione: str, esempio: str = "https://qdc.avellino1.it/…") -> Segnaposto:
    return Segnaposto("Link", descrizione, esempio, indispensabile=True, link=True)


PERSONA = Segnaposto("Persona", "nome e cognome della persona", "Giulia Rossi")
NOME = Segnaposto("Nome", "il nome della persona", "Giulia")
UNITA = Segnaposto("Unità", "l'unità", "Reparto Antares (N1)")
EVENTO = Segnaposto("Evento", "il titolo dell'evento", "Uscita di reparto")
RAGAZZO = Segnaposto("Ragazzo", "nome e cognome del ragazzo", "Giulia Rossi")
MOTIVO = Segnaposto("Motivo", "il motivo scritto dal capo", "Il reparto è al completo.", True)


def _scadenza(descrizione: str) -> Segnaposto:
    return Segnaposto("Scadenza", descrizione, "15/11/2026", indispensabile=True)


def _elenco(descrizione: str, esempio: str) -> Segnaposto:
    return Segnaposto("Elenco", descrizione, esempio, indispensabile=True)


_TIPI = [
    # --- Account and access ----------------------------------------------------------
    TipoEmail(
        "codice_accesso",
        "Codice di accesso",
        "A chi chiede di entrare con un codice via email.",
        "[Nome sito]: codice di accesso",
        "<p>Ciao,</p><p>il tuo codice di accesso è qui sotto: inseriscilo nella pagina "
        "dell'app che hai aperto.</p><p><strong>[Codice]</strong></p><p>Se non hai chiesto "
        "tu di entrare, ignora questa email.</p><p>[Nome sito]</p>",
        (Segnaposto("Codice", "il codice da inserire", "ABCD-EFGH", indispensabile=True),),
    ),
    TipoEmail(
        "invito",
        "Invito",
        "A chi viene invitato a creare il suo account, quando un capo lo invita.",
        "Invito al [Nome sito]",
        "<p>Ciao,</p><p>sei stato invitato a creare l'account del [Nome sito] ([Sigla sito]) "
        "per [Persona].</p><p>Apri questo link per completare l'iscrizione:<br>[Link]</p>"
        "<p>Il link vale fino al [Scadenza] e si può usare una sola volta.<br>Se non "
        "aspettavi questo messaggio puoi ignorarlo.</p>",
        (
            PERSONA,
            _link("il link per creare l'account"),
            _scadenza("fino a quando vale il link"),
        ),
    ),
    TipoEmail(
        "reimposta_password",
        "Nuova password",
        "A chi chiede di reimpostare la password.",
        "[Nome sito]: nuova password",
        "<p>Ciao,</p><p>hai chiesto di reimpostare la password del tuo account. Se non "
        "l'hai chiesto tu, ignora questa email; altrimenti apri il link qui sotto per "
        "sceglierne una nuova.</p><p>[Link]</p><p>[Nome sito]</p>",
        (_link("il link per scegliere la nuova password"),),
    ),
    TipoEmail(
        "verifica_email_registrazione",
        "Conferma dell'email alla registrazione",
        "A chi si registra con un codice di iscrizione, per confermare l'indirizzo.",
        "[Nome sito]: conferma il tuo indirizzo email",
        "<p>Ciao,</p><p>questo indirizzo è stato indicato per un account del [Nome sito]."
        "</p><p>Per confermarlo apri questo link:<br>[Link]</p><p>Se non aspettavi questo "
        "messaggio puoi ignorarlo.</p><p>[Nome sito]</p>",
        (_link("il link per confermare l'indirizzo"),),
    ),
    TipoEmail(
        "verifica_email",
        "Conferma dell'email",
        "A chi entra con un indirizzo non ancora confermato, o chiede di nuovo la conferma.",
        "[Nome sito]: conferma il tuo indirizzo email",
        "<p>Ciao,</p><p>questo indirizzo è stato indicato per un account del [Nome sito]."
        "</p><p>Per confermarlo apri questo link:<br>[Link]</p><p>Se non aspettavi questo "
        "messaggio puoi ignorarlo.</p><p>[Nome sito]</p>",
        (_link("il link per confermare l'indirizzo"),),
    ),
    TipoEmail(
        "account_esistente",
        "Account già esistente",
        "A chi prova a registrarsi con un indirizzo che ha già un account.",
        "[Nome sito]: l'account esiste già",
        "<p>Ciao,</p><p>qualcuno (forse tu) ha provato a registrarsi con l'indirizzo "
        "[Email], che ha già un account del [Nome sito].</p><p>Se hai dimenticato la "
        "password, scegline una nuova da qui:<br>[Link]</p><p>Se non sei stato tu, ignora "
        "questa email.</p>",
        (
            Segnaposto("Email", "l'indirizzo usato", "giulia.rossi@example.org"),
            _link("il link per scegliere una nuova password"),
        ),
    ),
    TipoEmail(
        "account_sconosciuto",
        "Account sconosciuto",
        "A chi prova a entrare o a reimpostare la password con un indirizzo senza account.",
        "[Nome sito]: nessun account con questo indirizzo",
        "<p>Ciao,</p><p>qualcuno (forse tu) ha provato a entrare nel [Nome sito] con "
        "l'indirizzo [Email], ma non c'è nessun account con questo indirizzo.</p><p>Per "
        "avere un account serve un invito dei capi o un codice di iscrizione: chiedilo ai "
        "capi del gruppo. Se non sei stato tu, ignora questa email.</p>",
        (Segnaposto("Email", "l'indirizzo usato", "giulia.rossi@example.org"),),
    ),
    # --- Joining from the app ------------------------------------------------------------
    TipoEmail(
        "nuova_richiesta_iscrizione",
        "Nuova richiesta di iscrizione",
        "Ai capigruppo e allo staff dell'unità, ogni giorno, per le richieste nuove.",
        "[Nome sito]: nuova richiesta di iscrizione",
        "<p>Ciao,</p><p>c'è una nuova richiesta di iscrizione a [Unità].</p><p>La trovi "
        "qui:<br>[Link]</p>",
        (UNITA, _link("la pagina delle richieste")),
        facoltativa=True,
    ),
    TipoEmail(
        "iscrizione_accolta",
        "Iscrizione accolta",
        "A chi ha chiesto l'iscrizione, quando un capo la accoglie.",
        "[Nome sito]: iscrizione accolta",
        "<p>Ciao,</p><p>l'iscrizione di [Nome] a [Unità] è stata accolta.</p><p>Entro il "
        "[Scadenza] completa i dati e carica i moduli firmati dall'app:<br>[Link]</p>",
        (NOME, UNITA, _scadenza("entro quando completare"), _link("la pagina dell'iscrizione")),
    ),
    TipoEmail(
        "iscrizione_rifiutata",
        "Iscrizione non accolta",
        "A chi ha chiesto l'iscrizione, quando un capo non la accoglie.",
        "[Nome sito]: iscrizione non accolta",
        "<p>Ciao,</p><p>l'iscrizione di [Nome] a [Unità] non è stata accolta:<br>[Motivo]"
        "</p><p>Per chiarimenti rivolgiti ai capi dell'unità.</p>",
        (NOME, UNITA, MOTIVO),
    ),
    TipoEmail(
        "iscrizione_da_completare",
        "Iscrizione da completare",
        "Alla famiglia, una settimana prima del termine per completare l'iscrizione.",
        "[Nome sito]: completa l'iscrizione",
        "<p>Ciao,</p><p>entro il [Scadenza] vanno completati i dati e i moduli "
        "dell'iscrizione di [Nome]:<br>[Link]</p>",
        (NOME, _scadenza("il termine"), _link("la pagina dell'iscrizione")),
    ),
    TipoEmail(
        "iscrizione_sospesa",
        "Iscrizione sospesa",
        "Alla famiglia, quando il termine per completare l'iscrizione è passato.",
        "[Nome sito]: iscrizione sospesa",
        "<p>Ciao,</p><p>il [Scadenza] è scaduto il termine per completare l'iscrizione di "
        "[Nome]. Fino a quando non la completi, nell'app vedi solo l'iscrizione e non la "
        "sua scheda:<br>[Link]</p>",
        (NOME, _scadenza("il termine passato"), _link("la pagina dell'iscrizione")),
    ),
    # --- Waiting list (DEC-256…DEC-263) -------------------------------------------------------
    TipoEmail(
        "attesa_conferma",
        "Lista d'attesa: conferma",
        "A chi si mette in lista d'attesa, o viene messo in lista da un capo.",
        "[Nome sito]: siete in lista d'attesa",
        "<p>Ciao,</p><p>[Ragazzo] è in lista d'attesa per entrare in [Gruppo].</p><p>Potrà "
        "essere contattato [Quando]: i capi chiamano a inizio anno, secondo i posti nelle "
        "unità, non secondo l'ordine di arrivo.</p><p>Da questo link puoi correggere i dati o "
        "uscire dalla lista:<br>[Link]</p><p>Conserva questa email; se la perdi, il link si "
        "richiede di nuovo dal sito.</p>",
        (
            RAGAZZO,
            Segnaposto(
                "Quando",
                "da quando può essere contattato",
                "dall'anno scout 2027/28",
                indispensabile=True,
            ),
            _link("il link personale per correggere o uscire"),
        ),
    ),
    TipoEmail(
        "attesa_link",
        "Lista d'attesa: il link personale",
        "A chi chiede di nuovo il link per correggere i dati o uscire dalla lista.",
        "[Nome sito]: il tuo link per la lista d'attesa",
        "<p>Ciao,</p><p>ecco il link per correggere i dati di [Ragazzo] in lista d'attesa o "
        "per uscire dalla lista:<br>[Link]</p><p>Se non l'hai chiesto tu, ignora questa "
        "email.</p>",
        (RAGAZZO, _link("il link personale per correggere o uscire")),
    ),
    TipoEmail(
        "attesa_interesse",
        "Lista d'attesa: confermi l'interesse?",
        "Dopo due anni in lista senza essere contattati, e di nuovo dopo 15 giorni.",
        "[Nome sito]: vuoi restare in lista d'attesa?",
        "<p>Ciao,</p><p>[Ragazzo] è in lista d'attesa per entrare in [Gruppo] da due anni. "
        "Se volete restare in lista, confermatelo da qui entro 30 giorni:<br>[Link]</p><p>Senza "
        "conferma, dopo 30 giorni l'iscrizione alla lista si cancella.</p>",
        (RAGAZZO, _link("il link personale per confermare")),
    ),
    TipoEmail(
        "attesa_uscita",
        "Lista d'attesa: uscita",
        "Quando, dopo la domanda dei due anni, nessuno ha confermato entro 30 giorni.",
        "[Nome sito]: uscita dalla lista d'attesa",
        "<p>Ciao,</p><p>non avendo ricevuto conferma, [Ragazzo] non è più in lista d'attesa "
        "per [Gruppo] e i suoi dati sono stati cancellati.</p><p>Se volete, potete rimettervi "
        "in lista dal sito.</p>",
        (RAGAZZO,),
    ),
    TipoEmail(
        "attesa_iscrizione",
        "Lista d'attesa: iscrizione",
        "Alla famiglia (o al maggiorenne) quando i capi lo iscrivono in un'unità.",
        "[Nome sito]: l'iscrizione di [Ragazzo]",
        "<p>Ciao,</p><p>[Ragazzo] può entrare in [Unità]!</p><p>Per l'iscrizione apri questo "
        "link entro il [Scadenza]: troverai già i dati della lista d'attesa, da completare "
        "con quelli che servono all'associazione.<br>[Link]</p>",
        (
            RAGAZZO,
            UNITA,
            _link("il link per l'iscrizione"),
            _scadenza("fino a quando vale il link"),
        ),
    ),
    # --- Events ----------------------------------------------------------------------------
    TipoEmail(
        "evento_nuovo",
        "Nuovo evento",
        "Alle famiglie e ai soci maggiorenni invitati, quando un capo crea un evento.",
        "[Evento]",
        "<p>Ciao,</p><p>nuovo evento: [Evento]<br>[Quando]<br>[Dettagli]</p><p>I dettagli "
        "nell'app:<br>[Link]</p>",
        (
            EVENTO,
            Segnaposto("Quando", "data e orari", "sabato 7/11/2026, dalle 16:00 alle 19:00", True),
            Segnaposto("Dettagli", "luogo e quota, se ci sono", "Luogo: Parrocchia"),
            _link("la pagina dell'evento"),
        ),
        facoltativa=True,
    ),
    TipoEmail(
        "evento_modificato",
        "Evento cambiato",
        "Agli invitati, quando cambiano data, orari o luogo di un evento.",
        "Cambiato: [Evento]",
        "<p>Ciao,</p><p>è cambiato l'evento [Evento]: ora è [Quando].</p><p>I dettagli "
        "nell'app:<br>[Link]</p>",
        (
            EVENTO,
            Segnaposto(
                "Quando",
                "data, orari e luogo",
                "07/11/2026, dalle 16:00 alle 19:00, a Mercogliano",
                True,
            ),
            _link("la pagina dell'evento"),
        ),
        facoltativa=True,
    ),
    TipoEmail(
        "evento_annullato",
        "Evento annullato",
        "Agli invitati, quando un evento è annullato.",
        "Annullato: [Evento]",
        "<p>Ciao,</p><p>l'evento [Evento] ([Quando]) è annullato: [Motivo]</p><p>I dettagli "
        "nell'app:<br>[Link]</p>",
        (
            EVENTO,
            Segnaposto("Quando", "data e orari", "07/11/2026, dalle 16:00 alle 19:00"),
            MOTIVO,
            _link("la pagina dell'evento"),
        ),
        facoltativa=True,
    ),
    # --- Fees ------------------------------------------------------------------------------
    TipoEmail(
        "ricevuta",
        "Ricevuta di un pagamento",
        "A chi ha pagato (ai genitori, per i minorenni), con la ricevuta in allegato.",
        "Ricevuta n. [Numero]",
        "<p>Ciao,</p><p>in allegato la ricevuta del pagamento di [Importo] del [Data]. Non è "
        "una ricevuta fiscale.</p><p>La trovi anche nell'app, alla pagina Quote.</p>",
        (
            Segnaposto("Numero", "il numero della ricevuta", "12/2026", True),
            Segnaposto("Importo", "l'importo pagato", "35,00 €", True),
            Segnaposto("Data", "la data del pagamento", "31/10/2026", True),
        ),
    ),
    TipoEmail(
        "promemoria_quote",
        "Quote in scadenza",
        "Alle famiglie, una settimana prima della scadenza delle quote non pagate.",
        "Quote in scadenza",
        "<p>Ciao,</p><p>ti ricordiamo le quote in scadenza:<br>[Elenco]</p><p>I dettagli e "
        "come pagare nell'app:<br>[Link]</p>",
        (
            _elenco(
                "le quote, una per riga",
                "- Giulia: Quota di gruppo, 35,00 € entro il 15/11/2026",
            ),
            _link("la pagina delle quote"),
        ),
        facoltativa=True,
    ),
    TipoEmail(
        "pagamento_non_confermato",
        "Pagamento non confermato",
        "A chi ha segnalato un pagamento con PayPal o con bonifico, quando un capo non lo "
        "trova o non lo conferma.",
        "[Nome sito]: pagamento non confermato",
        "<p>Ciao,</p><p>il pagamento di [Importo] che hai segnalato il [Data] non è stato "
        "confermato:<br>[Motivo]</p><p>Le quote restano da pagare; trovi tutto qui:<br>[Link]"
        "</p><p>Per chiarimenti rivolgiti ai capi.</p>",
        (
            Segnaposto("Importo", "l'importo segnalato", "37,00 €", True),
            Segnaposto("Data", "il giorno del pagamento", "31/10/2026"),
            MOTIVO,
            _link("la pagina delle quote"),
        ),
    ),
    # --- Notice board ----------------------------------------------------------------------
    TipoEmail(
        "avviso_bacheca",
        "Avviso della bacheca",
        "A chi legge un avviso, quando chi lo pubblica lo manda anche per email.",
        "[Titolo]",
        "<p>Ciao,</p><p>[Titolo]</p><p>[Testo]</p><p>Nella bacheca dell'app:<br>[Link]</p>",
        (
            Segnaposto("Titolo", "il titolo dell'avviso", "Riunione dei genitori", True),
            Segnaposto("Testo", "il testo dell'avviso", "Venerdì alle 20:30 in sede.", True),
            _link("la bacheca"),
        ),
        facoltativa=True,
    ),
    # --- Events on BuonaCaccia (always sent, DEC-168) --------------------------------------
    TipoEmail(
        "buonacaccia_iscrizione",
        "Iscrizione a un evento BuonaCaccia",
        "Alla famiglia, quando lo staff registra l'esito dell'iscrizione su BuonaCaccia.",
        "Iscrizione a [Evento]",
        "<p>Ciao,</p><p>[Nome] è iscritto su BuonaCaccia all'evento [Evento] ([Data]): "
        "[Stato].</p><p>[Cosa serve]</p><p>I dettagli nell'app:<br>[Link]</p>",
        (
            NOME,
            EVENTO,
            Segnaposto("Data", "il giorno di inizio", "14/11/2026"),
            Segnaposto("Stato", "l'esito: ammesso, in lista d'attesa…", "ammesso", True),
            Segnaposto(
                "Cosa serve",
                "quello che serve dalla famiglia, se serve qualcosa",
                "Ci serve:\n- le risposte alla scheda dell'evento, nell'app",
            ),
            _link("la pagina dell'evento"),
        ),
    ),
    TipoEmail(
        "liberatoria_da_firmare",
        "Liberatoria da firmare",
        "Alla famiglia, quando la liberatoria di un evento BuonaCaccia è nell'app.",
        "Liberatoria per [Evento]",
        "<p>Ciao,</p><p>nell'app c'è la liberatoria di [Nome] per [Evento]: scaricala, "
        "completala, firmala e caricala di nuovo nell'app entro il [Scadenza].</p><p>[Link]"
        "</p>",
        (NOME, EVENTO, _scadenza("entro quando caricarla"), _link("la pagina dell'evento")),
    ),
    TipoEmail(
        "liberatoria_rigettata",
        "Liberatoria da rifare",
        "Alla famiglia, quando la segreteria rigetta una liberatoria.",
        "Liberatoria da rifare: [Evento]",
        "<p>Ciao,</p><p>la segreteria ha rigettato la liberatoria di [Nome] per [Evento]: "
        "[Motivo]</p><p>Serve una liberatoria nuova: [Link]</p>",
        (NOME, EVENTO, MOTIVO, _link("la pagina dell'evento")),
    ),
    TipoEmail(
        "promemoria_liberatoria",
        "Promemoria della liberatoria",
        "Alla famiglia, due giorni prima e il giorno della scadenza, se manca ancora qualcosa.",
        "Promemoria: liberatoria per un evento",
        "<p>Ciao,</p><p>[Elenco]</p>",
        (
            _elenco(
                "per ogni iscrizione, cosa serve e il link",
                "Per Giulia (Campetto, https://qdc.avellino1.it/eventi/5) ci serve:\n"
                "- la liberatoria firmata dai genitori",
            ),
        ),
    ),
    TipoEmail(
        "buonacaccia_scadenze",
        "Scadenze su BuonaCaccia",
        "Allo staff, due giorni prima e il giorno delle scadenze delle iscrizioni.",
        "Scadenze su BuonaCaccia",
        "<p>Ciao,</p><p>scadenze vicine delle iscrizioni su BuonaCaccia:<br>[Elenco]</p>"
        "<p>Nell'app: [Link]</p>",
        (
            _elenco(
                "le scadenze, una per riga",
                "- Rossi Giulia, Campetto: entro il 15/11/2026 su BuonaCaccia resta da "
                "pagare la quota",
            ),
            _link("la pagina degli eventi su BuonaCaccia"),
        ),
    ),
    # --- At 18 (DEC-26) --------------------------------------------------------------------
    TipoEmail(
        "maggiore_eta_mese_prima",
        "Tra un mese compi 18 anni",
        "Al socio, un mese prima dei 18 anni.",
        "Tra un mese compi 18 anni",
        "<p>Ciao [Nome],</p><p>[Quando] compi 18 anni. Da quel giorno decidi tu cosa "
        "possono vedere i tuoi genitori nel [Nome sito]: contatti, farmaci e allergie, la "
        "tua scheda.<br>Finché non scegli, continuano a vedere tutto.</p><p>Scegli qui "
        "(serve il tuo account; se non l'hai, chiedilo ai tuoi capi):<br>[Link]</p>",
        (
            NOME,
            Segnaposto("Quando", "il giorno del compleanno", "il 30/11/2026", True),
            _link("la pagina dove scegliere"),
        ),
        facoltativa=True,
    ),
    TipoEmail(
        "maggiore_eta",
        "Compi 18 anni",
        "Al socio, il giorno dei 18 anni.",
        "Compi 18 anni: cosa vedono i tuoi genitori",
        "<p>Ciao [Nome],</p><p>[Quando] compi 18 anni. Da quel giorno decidi tu cosa "
        "possono vedere i tuoi genitori nel [Nome sito]: contatti, farmaci e allergie, la "
        "tua scheda.<br>Finché non scegli, continuano a vedere tutto.</p><p>Scegli qui "
        "(serve il tuo account; se non l'hai, chiedilo ai tuoi capi):<br>[Link]</p>",
        (
            NOME,
            Segnaposto("Quando", "il giorno del compleanno", "oggi", True),
            _link("la pagina dove scegliere"),
        ),
        facoltativa=True,
    ),
    TipoEmail(
        "maggiore_eta_genitori",
        "Un figlio compie 18 anni",
        "Ai genitori, un mese prima e il giorno dei 18 anni del figlio.",
        "[Nome] compie 18 anni",
        "<p>Gentile genitore,</p><p>[Quando] [Nome] compie 18 anni. Da quel giorno sarà "
        "[Nome] a decidere cosa resta visibile a voi nel [Nome sito]. Finché non sceglie, "
        "continuate a vedere tutto come ora.</p>",
        (NOME, Segnaposto("Quando", "il giorno del compleanno", "il 30/11/2026", True)),
        facoltativa=True,
    ),
    # --- Summaries for the capigruppo --------------------------------------------------------
    TipoEmail(
        "correzioni_da_inoltrare",
        "Correzioni da inoltrare",
        "Ai capigruppo, ogni giorno, quando ci sono correzioni nuove ai dati di BuonaStrada.",
        "Correzioni da inoltrare alla segreteria",
        "<p>Ciao,</p><p>nel [Nome sito] ci sono [Nuove] nuove correzioni ai dati di "
        "BuonaStrada ([Da inoltrare] in tutto da inoltrare alla segreteria).</p><p>Le trovi "
        "qui:<br>[Link]</p><p>Dopo averle inoltrate, segnalale come inoltrate nell'app.</p>",
        (
            Segnaposto("Nuove", "quante sono le correzioni nuove", "2", True),
            Segnaposto("Da inoltrare", "quante sono in tutto da inoltrare", "3"),
            _link("la pagina delle correzioni"),
        ),
        facoltativa=True,
    ),
    TipoEmail(
        "promemoria_fine_anno",
        "Fine anno e archivio",
        "Ai capigruppo: l'anno da chiudere e chi è da archiviare.",
        "Fine anno e archivio nel [Nome sito]",
        "<p>Ciao,</p><p>[Elenco]</p><p>Trovi tutto qui:<br>[Link]</p>",
        (
            _elenco(
                "cosa c'è da fare, una cosa per riga",
                "- l'anno associativo 2025/26 è finito ma è ancora aperto: chiudilo quando "
                "rendiconto e verifiche sono fatti.",
            ),
            _link("la pagina del gruppo"),
        ),
        facoltativa=True,
    ),
]

TIPI: dict[str, TipoEmail] = {t.chiave: t for t in _TIPI}
