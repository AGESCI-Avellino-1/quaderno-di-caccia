"""HTML of the email templates (DEC-250): what the editor may produce, and the plain-text
version derived from it.

The editor's HTML is cleaned on the server with nh3 (a whitelist): it reaches people's
mailboxes, so only simple formatting, tables, http(s)/mailto links and images from the
app's own store survive.
"""

import re
from html.parser import HTMLParser

import nh3

TAG = {"p", "br", "strong", "b", "em", "i", "u", "s", "ul", "ol", "li", "a", "h2", "h3"}
TAG |= {"table", "thead", "tbody", "tr", "th", "td", "img"}
ATTRIBUTI = {
    "a": {"href"},
    "img": {"src", "alt", "width"},
    "th": {"colspan", "rowspan"},
    "td": {"colspan", "rowspan"},
}
SCHEMI = {"http", "https", "mailto"}
# Images only from the app's own store (`ImmagineEmail`): never from elsewhere.
IMMAGINI = "/api/v1/immagini/"


def _filtra(tag: str, attributo: str, valore: str) -> str | None:
    if tag == "img" and attributo == "src" and not valore.startswith(IMMAGINI):
        return None
    if attributo in ("width", "colspan", "rowspan") and not valore.isdigit():
        return None
    return valore


def pulisci(html: str) -> str:
    pulito = nh3.clean(
        html,
        tags=TAG,
        attributes=ATTRIBUTI,
        attribute_filter=_filtra,
        url_schemes=SCHEMI,
        link_rel="noopener noreferrer",
    )
    # An image left without its source (from elsewhere) goes entirely.
    return re.sub(r"<img(?![^>]*\bsrc=)[^>]*>", "", pulito).strip()


# Between table cells while reading; `_righe_tabella` turns it into " | ".
CELLA = "\x1f"


def _righe_tabella(riga: str) -> str | None:
    """A table row: its cells joined by " | ", trailing empty ones dropped; None if the
    row is empty."""
    celle = [c.strip() for c in riga.split(CELLA)]
    while celle and not celle[-1]:
        celle.pop()
    return " | ".join(celle) if celle else None


class _Testo(HTMLParser):
    """Paragraphs and headings separated by a blank line, list items with "- " or
    "1. ", links as "text (address)" unless the text is the address."""

    BLOCCHI = {"p", "h2", "h3", "ul", "ol", "table"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parti: list[str] = []
        self.liste: list[list[int]] = []  # [counter] for ol, [] for ul
        self.link: str | None = None
        self.testo_link: list[str] = []
        # Inside a table cell paragraphs do not break the row; cells are "a | b".
        self.celle = 0
        self.prima_cella = True

    def _a_capo(self, righe: int) -> None:
        testo = "".join(self.parti).rstrip(" ")
        finali = len(testo) - len(testo.rstrip("\n"))
        if testo and finali < righe:
            self.parti.append("\n" * (righe - finali))

    def handle_starttag(self, tag, attrs):
        if tag in ("p", "h2", "h3") and self.celle:
            return
        if tag in ("p", "h2", "h3"):
            self._a_capo(1 if self.liste else 2)
        elif tag in ("ul", "ol"):
            self._a_capo(1 if self.liste else 2)
            self.liste.append([0] if tag == "ol" else [])
        elif tag == "li":
            self._a_capo(1)
            lista = self.liste[-1] if self.liste else []
            rientro = "   " * (len(self.liste) - 1)
            if lista:
                lista[0] += 1
                self.parti.append(f"{rientro}{lista[0]}. ")
            else:
                self.parti.append(f"{rientro}- ")
        elif tag == "br":
            self.parti.append("\n")
        elif tag == "table":
            self._a_capo(2)
        elif tag == "tr":
            self._a_capo(1)
            self.prima_cella = True
        elif tag in ("td", "th"):
            if not self.prima_cella:
                self.parti.append(CELLA)
            self.prima_cella = False
            self.celle += 1
        elif tag == "img":
            alt = (dict(attrs).get("alt") or "").strip()
            if alt:
                self.parti.append(f"[{alt}]")
        elif tag == "a":
            self.link = dict(attrs).get("href") or ""
            self.testo_link = []

    def handle_endtag(self, tag):
        if tag in ("ul", "ol") and self.liste:
            self.liste.pop()
            self._a_capo(1 if self.liste else 2)
        elif tag in ("td", "th"):
            self.celle = max(0, self.celle - 1)
        elif tag in ("p", "h2", "h3") and not self.celle:
            self._a_capo(1 if self.liste else 2)
        elif tag == "table":
            self._a_capo(2)
        elif tag == "a" and self.link is not None:
            testo = "".join(self.testo_link).strip()
            indirizzo = self.link.removeprefix("mailto:")
            self.parti.append(
                testo if not indirizzo or testo == indirizzo else f"{testo} ({indirizzo})"
            )
            self.link = None

    def handle_data(self, data):
        if not data.strip() and "\n" in data:
            return  # indentation between tags
        if self.link is not None:
            self.testo_link.append(data)
        else:
            self.parti.append(data)


def in_testo(html: str) -> str:
    """The plain-text version of an email, derived from its HTML."""
    lettore = _Testo()
    lettore.feed(html)
    lettore.close()
    righe = []
    for riga in "".join(lettore.parti).split("\n"):
        if CELLA in riga:
            riga = _righe_tabella(riga)
            if riga is None:
                continue
        righe.append(riga.rstrip())
    testo = "\n".join(righe).strip("\n")
    while "\n\n\n" in testo:
        testo = testo.replace("\n\n\n", "\n\n")
    return testo + "\n"
