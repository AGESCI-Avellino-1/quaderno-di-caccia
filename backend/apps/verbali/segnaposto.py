"""The placeholders of the minutes written by hand (DEC-372): the data of the meeting and of the
group. A placeholder with no value disappears; `mancanti` tells who writes which ones."""

import re
from html import escape

from django.utils import timezone

from apps.eventi.models import Evento
from apps.organizzazione.models import Gruppo
from apps.quote.models import NOMI_MESI

DATA = "[Data]"
ORA_INIZIO = "[Ora di inizio]"
ORA_FINE = "[Ora di fine]"
DENOMINAZIONE = "[Denominazione gruppo]"
CODICE_FISCALE = "[Codice fiscale gruppo]"
PARTITA_IVA = "[Partita IVA gruppo]"
INDIRIZZO_COMPLETO = "[Indirizzo completo]"
INDIRIZZO = "[Indirizzo]"
LUOGO = "[Luogo]"

ELENCO = [
    DATA,
    ORA_INIZIO,
    ORA_FINE,
    DENOMINAZIONE,
    CODICE_FISCALE,
    PARTITA_IVA,
    INDIRIZZO_COMPLETO,
    INDIRIZZO,
    LUOGO,
]

NOMI = {
    DENOMINAZIONE: "la denominazione del gruppo",
    CODICE_FISCALE: "il codice fiscale del gruppo",
    PARTITA_IVA: "la partita IVA del gruppo",
    INDIRIZZO_COMPLETO: "l'indirizzo della riunione",
    INDIRIZZO: "l'indirizzo della riunione",
    LUOGO: "la città della riunione, che non si riconosce dall'indirizzo",
}

# The town follows the postcode: "Via Roma 1, 83100 Avellino (AV)".
_CITTA = re.compile(r"\b\d{5}\s+([^\W\d][^,(]*)")


def _indirizzi(evento: Evento) -> tuple[str, str]:
    """The long one and the short one; a place written by hand is both, as it is."""
    localita = evento.localita
    if localita is None:
        luogo = evento.luogo.strip()
        return luogo, luogo
    indirizzo = localita.indirizzo_completo.strip()
    return ", ".join(v for v in (localita.nome_visibile, indirizzo) if v), indirizzo


def _citta(indirizzo: str) -> str:
    trovata = _CITTA.search(indirizzo)
    return trovata[1].strip() if trovata else ""


def valori(evento: Evento) -> dict[str, str]:
    gruppo = Gruppo.objects.first()
    inizio = timezone.localtime(evento.inizio)
    completo, indirizzo = _indirizzi(evento)
    return {
        DATA: f"{inizio.day} {NOMI_MESI[inizio.month - 1]} {inizio.year}",
        ORA_INIZIO: f"{inizio:%H:%M}",
        ORA_FINE: f"{timezone.localtime(evento.fine):%H:%M}",
        DENOMINAZIONE: (gruppo.denominazione_sociale or gruppo.denominazione) if gruppo else "",
        CODICE_FISCALE: gruppo.codice_fiscale if gruppo else "",
        PARTITA_IVA: gruppo.partita_iva if gruppo else "",
        INDIRIZZO_COMPLETO: completo,
        INDIRIZZO: indirizzo,
        LUOGO: _citta(indirizzo),
    }


def sostituisci(testo: str, evento: Evento) -> str:
    """What is typed goes through `escape`: the text is shown with v-html and in the PDF."""
    for segnaposto, valore in valori(evento).items():
        testo = testo.replace(segnaposto, escape(valore))
    return testo


def mancanti(testo: str, evento: Evento) -> list[str]:
    """What the text asks for and the app does not have, once each."""
    nomi = [NOMI[s] for s, valore in valori(evento).items() if not valore and s in testo]
    return list(dict.fromkeys(nomi))
