"""The description at the top of «La mia tribù» (DEC-416): the group's text from the
settings, or the base one, written for Avellino 1 (the default installation)."""

from apps.impostazioni.models import Impostazioni

DESCRIZIONE_BASE = (
    "Attorno al fuoco della nostra tribù Cherokee, sotto lo sguardo di Recchia Mozza, ogni "
    "guerriero porta il nome che il Grande Spirito gli ha donato nella notte del fuoco: lo "
    "spirito animale che lo protegge e lo sostiene nelle difficoltà.\n\n"
    "Rosso come il coraggio, marrone come la forza, bianco come la purezza: sono i colori "
    "della tribù. Qui trovi i fratelli e le sorelle che li portano con te. Il tuo nome di "
    "totem è un segreto della tribù: non rivelarlo a chi non ne fa parte. Porta il tuo nome "
    "con orgoglio e valore, e custodisci ciò che accade attorno al fuoco."
)
LUNGHEZZA_DESCRIZIONE = 2000


def descrizione(imp: Impostazioni) -> str:
    return imp.descrizione_tribu or DESCRIZIONE_BASE


def in_paragrafi(testo: str) -> str:
    """Paragraphs split by an empty line, each on one line, as the flyer's text."""
    return "\n\n".join(
        " ".join(c.split()) for c in testo.replace("\r\n", "\n").split("\n\n") if c.strip()
    )
