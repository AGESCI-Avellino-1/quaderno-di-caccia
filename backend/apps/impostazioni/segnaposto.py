"""Placeholders such as [Gruppo] in the texts the group writes (DEC-246, DEC-247).

The server only checks them: the PWA fills them in, because [Pagina corrente] is known
only there.
"""

import re

SEGNAPOSTO = re.compile(r"\[([^\[\]]+)\]")

# Title and footer (DEC-246, DEC-247).
NOME_SITO = "Nome sito"
SIGLA_SITO = "Sigla sito"
GRUPPO = "Gruppo"
SIGLA_GRUPPO = "Sigla gruppo"
ANNO = "Anno"
PAGINA_CORRENTE = "Pagina corrente"
# The version of the app open on the device (DEC-369): the server does not know it.
RELEASE = "Release"
# The version installed on the server (DEC-380); the PWA fills it in, with the others.
RELEASE_SERVER = "Release server"
# What the server can fill in by itself.
DEL_SITO = (NOME_SITO, SIGLA_SITO, GRUPPO, SIGLA_GRUPPO, ANNO)
DEL_TITOLO = (*DEL_SITO, RELEASE, RELEASE_SERVER, PAGINA_CORRENTE)


def usati(testo: str) -> list[str]:
    return [m.group(1).strip() for m in SEGNAPOSTO.finditer(testo)]


def sconosciuti(testo: str, ammessi: tuple[str, ...]) -> list[str]:
    """Placeholders not in `ammessi` (compared ignoring case), in order, once each."""
    noti = {a.casefold() for a in ammessi}
    trovati: list[str] = []
    for nome in usati(testo):
        if nome.casefold() not in noti and nome not in trovati:
            trovati.append(nome)
    return trovati
