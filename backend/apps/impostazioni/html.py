"""HTML of the email templates (DEC-250): what the editor may produce, and the plain-text
version derived from it.

The editor's HTML is cleaned on the server with nh3 (a whitelist): it reaches people's
mailboxes, so only simple formatting and http(s)/mailto links survive.
"""

from html.parser import HTMLParser

import nh3

TAG = {"p", "br", "strong", "b", "em", "i", "u", "s", "ul", "ol", "li", "a", "h2", "h3"}
ATTRIBUTI = {"a": {"href"}}
SCHEMI = {"http", "https", "mailto"}


def pulisci(html: str) -> str:
    return nh3.clean(
        html,
        tags=TAG,
        attributes=ATTRIBUTI,
        url_schemes=SCHEMI,
        link_rel="noopener noreferrer",
    ).strip()


class _Testo(HTMLParser):
    """Paragraphs and headings separated by a blank line, list items with "- " or
    "1. ", links as "text (address)" unless the text is the address."""

    BLOCCHI = {"p", "h2", "h3", "ul", "ol"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parti: list[str] = []
        self.liste: list[list[int]] = []  # [counter] for ol, [] for ul
        self.link: str | None = None
        self.testo_link: list[str] = []

    def _a_capo(self, righe: int) -> None:
        testo = "".join(self.parti).rstrip(" ")
        finali = len(testo) - len(testo.rstrip("\n"))
        if testo and finali < righe:
            self.parti.append("\n" * (righe - finali))

    def handle_starttag(self, tag, attrs):
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
        elif tag == "a":
            self.link = dict(attrs).get("href") or ""
            self.testo_link = []

    def handle_endtag(self, tag):
        if tag in ("ul", "ol") and self.liste:
            self.liste.pop()
            self._a_capo(1 if self.liste else 2)
        elif tag in ("p", "h2", "h3"):
            self._a_capo(1 if self.liste else 2)
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
    righe = "".join(lettore.parti).split("\n")
    testo = "\n".join(r.rstrip() for r in righe).strip("\n")
    while "\n\n\n" in testo:
        testo = testo.replace("\n\n\n", "\n\n")
    return testo + "\n"
