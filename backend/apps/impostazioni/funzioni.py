"""Features the group may switch off (DEC-421).

A feature listed here is off until a capogruppo or the technical administrator switches it on
in the settings. Off, it is as if it did not exist: its API answers 404, its menu entry, its
notifications and its email templates disappear. Its data stay in the database, hidden, and come
back as they were when it is switched on again.

A new feature of this kind = an entry in `_FUNZIONI`, `richiedi()` at the top of each of its
endpoints, its email types in `email`, its menu entry behind the profile's `funzioni`.
"""

from dataclasses import dataclass

from ninja.errors import HttpError

from .models import Impostazioni

BABBO_NATALE = "babbo_natale"


@dataclass(frozen=True)
class Funzione:
    chiave: str
    nome: str
    # What it does, for the settings page.
    descrizione: str
    # Its email types (`catalogo_email`): hidden from the templates while it is off.
    email: tuple[str, ...] = ()


_FUNZIONI = (
    Funzione(
        BABBO_NATALE,
        "Babbo Natale segreto",
        "Scambi di regali anonimi: lo staff e i capigruppo scelgono i partecipanti, l'app "
        "estrae a caso a chi ognuno fa il regalo e lo dice solo a lui.",
        ("babbo_natale_account", "babbo_natale_partecipante", "babbo_natale_genitori"),
    ),
)
FUNZIONI: dict[str, Funzione] = {f.chiave: f for f in _FUNZIONI}


def attive() -> set[str]:
    return {c for c in Impostazioni.carica().funzioni_attive if c in FUNZIONI}


def attiva(chiave: str) -> bool:
    return chiave in attive()


def richiedi(chiave: str) -> None:
    """At the top of every endpoint of a feature: off, it does not exist."""
    if not attiva(chiave):
        raise HttpError(404, "Pagina non trovata.")


def imposta(chiave: str, accesa: bool) -> None:
    if chiave not in FUNZIONI:
        raise KeyError(chiave)
    imp = Impostazioni.carica()
    scelte = [c for c in imp.funzioni_attive if c in FUNZIONI and c != chiave]
    if accesa:
        scelte.append(chiave)
    imp.funzioni_attive = sorted(scelte)
    imp.save(update_fields=["funzioni_attive", "aggiornato_il"])


def email_nascoste() -> set[str]:
    """The email types of the features switched off."""
    accese = attive()
    return {e for f in _FUNZIONI if f.chiave not in accese for e in f.email}
