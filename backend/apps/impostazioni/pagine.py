"""Privacy policy and terms (DEC-266): public pages with a default text the group can
change. The defaults follow the analysis (DEC-98 controller and delegates, DEC-101 access
log, DEC-102 rights, DEC-103 data in the EU, DEC-263 waiting list); the group checks them
with whoever handles privacy before publishing a version of its own.
"""

import re
from dataclasses import dataclass
from html import escape

from . import segnaposto as sp

EMAIL_GRUPPO = "Email gruppo"
SEGNAPOSTO_PAGINE = (*sp.DEL_TITOLO[:-1], EMAIL_GRUPPO)


@dataclass(frozen=True)
class Pagina:
    chiave: str
    titolo: str
    campo: str
    campo_data: str
    base: str


PRIVACY_BASE = """<h2>Chi tratta i dati</h2>
<p>[Nome sito] è l'app di [Gruppo] per la vita del gruppo: anagrafica dei soci e delle famiglie, progressione personale, eventi e presenze, quote e cassa, scheda sanitaria.</p>
<p>Titolare del trattamento è l'Associazione Guide e Scouts Cattolici Italiani (AGESCI) APS, secondo la sua informativa unificata per i soci. I capigruppo di [Gruppo] sono delegati al trattamento; gli altri capi trattano i dati su loro delega e solo per quello che serve al loro servizio.</p>
<h2>Quali dati e perché</h2>
<ul><li>Dati anagrafici e di contatto dei soci e dei genitori, per la vita associativa e per comunicare con le famiglie.</li><li>Dati sulla salute (farmaci, allergie, intolleranze, scheda medica), solo per la sicurezza durante le attività: li vedono i capi che ne hanno bisogno, ogni lettura resta in un registro.</li><li>Progressione personale, presenze, note dei capi, per accompagnare il cammino di ciascuno.</li><li>Quote e pagamenti, per la gestione economica del gruppo.</li><li>Lista d'attesa: i dati di chi vuole entrare nel gruppo, solo per contattarlo; chi esce dalla lista non lascia dati.</li></ul>
<h2>Dove e per quanto</h2>
<p>I dati restano in server nell'Unione Europea. Chi lascia il gruppo viene archiviato dopo due anni e i suoi dati vengono tolti dall'app. Sul telefono l'app conserva una copia cifrata, protetta dal PIN, per usarla anche senza rete; si cancella da sola se il telefono non si collega per troppo tempo o se il dispositivo viene revocato.</p>
<h2>Cookie</h2>
<p>L'app usa solo cookie tecnici, necessari per funzionare (l'accesso e la protezione dei moduli): nessun cookie di statistica o pubblicità, nessun dato ceduto a terzi.</p>
<h2>I tuoi diritti</h2>
<p>Puoi chiedere di vedere, correggere, ricevere in copia o cancellare i tuoi dati e quelli dei tuoi figli minorenni, e opporti alle email che non sono necessarie (le scegli nella pagina Privacy). Rivolgiti ai capigruppo ([Email gruppo]). Le richieste vengono gestite con l'ufficio privacy nazionale dell'AGESCI.</p>
<p><small>Anno scout [Anno].</small></p>"""

TERMINI_BASE = """<h2>A chi è rivolta</h2>
<p>[Nome sito] è l'app di [Gruppo], riservata ai soci, ai loro genitori e ai capi del gruppo. Chi è in lista d'attesa la usa solo per i propri dati in lista.</p>
<h2>L'account</h2>
<p>L'account è personale: non va condiviso. Ognuno vede solo quello che il suo ruolo gli permette. Se perdi il telefono, revocalo dalla pagina Password e sicurezza o chiedi ai capigruppo di farlo.</p>
<h2>Cosa si può fare</h2>
<ul><li>Usare i dati degli altri solo per la vita del gruppo, mai per altri scopi.</li><li>Pubblicare avvisi, foto e documenti solo se legati alle attività e nel rispetto delle persone.</li><li>I pagamenti non avvengono dentro l'app: l'app indica come pagare e registra le ricevute.</li></ul>
<h2>Il servizio</h2>
<p>L'app è gestita da volontari del gruppo e offerta senza garanzia di disponibilità continua. Le informazioni ufficiali sui soci restano quelle dell'associazione (BuonaStrada).</p>
<h2>Modifiche e contatti</h2>
<p>Questi termini possono cambiare; la versione in vigore è sempre in questa pagina. Per domande rivolgiti ai capigruppo ([Email gruppo]).</p>"""

PAGINE = {
    "privacy": Pagina(
        "privacy", "Privacy policy", "privacy", "privacy_aggiornata_il", PRIVACY_BASE
    ),
    "termini": Pagina(
        "termini", "Termini e condizioni", "termini", "termini_aggiornati_il", TERMINI_BASE
    ),
}


def valori() -> dict[str, str]:
    from apps.core.anno import AnnoAssociativo
    from apps.organizzazione.models import Gruppo

    from .models import Impostazioni

    imp = Impostazioni.carica()
    gruppo = imp.nome_del_gruppo()
    # Without the group's address (letterhead), a phrase that reads well in its place.
    email = getattr(Gruppo.objects.first(), "email", "") or "anche tramite i capi della tua unità"
    return {
        sp.NOME_SITO: imp.nome_sito,
        sp.SIGLA_SITO: imp.sigla_sito or imp.nome_sito,
        sp.GRUPPO: gruppo,
        sp.SIGLA_GRUPPO: imp.sigla_gruppo or gruppo,
        sp.ANNO: AnnoAssociativo.corrente().etichetta,
        EMAIL_GRUPPO: email,
    }


_TAG = re.compile(r"(<[^>]*>)")


def riempi(html: str, valori_: dict[str, str]) -> str:
    """Placeholders only in the text between tags, values escaped."""
    noti = {k.casefold(): v for k, v in valori_.items()}

    def sostituisci(m: re.Match) -> str:
        valore = noti.get(m.group(1).strip().casefold())
        return m.group(0) if valore is None else escape(valore)

    return "".join(
        p if p.startswith("<") else sp.SEGNAPOSTO.sub(sostituisci, p) for p in _TAG.split(html)
    )
