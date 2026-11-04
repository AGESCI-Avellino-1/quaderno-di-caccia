"""The editor's HTML as reportlab flowables, for every print made from a text (DEC-322)."""

from html.parser import HTMLParser
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import ListFlowable, ListItem, Paragraph, Spacer, Table, TableStyle

MARGINE = 18 * mm
LARGHEZZA = A4[0] - 2 * MARGINE
TITOLO = ParagraphStyle("titolo", fontName="Helvetica-Bold", fontSize=14, leading=18, spaceAfter=2)
SOTTOTITOLO = ParagraphStyle("sottotitolo", fontName="Helvetica", fontSize=9, leading=12)
TESTO = ParagraphStyle("testo", fontName="Helvetica", fontSize=10, leading=14, spaceAfter=6)
CELLA = ParagraphStyle("cella", fontName="Helvetica", fontSize=9, leading=12)
STILI_TITOLO = {
    "h2": ParagraphStyle(
        "h2", fontName="Helvetica-Bold", fontSize=12, leading=16, spaceBefore=6, spaceAfter=4
    ),
    "h3": ParagraphStyle(
        "h3", fontName="Helvetica-Bold", fontSize=10.5, leading=14, spaceBefore=4, spaceAfter=3
    ),
}
ALLINEAMENTI = {"left": 0, "center": 1, "right": 2}
# What the editor's inline marks become in reportlab's own markup.
SEGNI = {"strong": "b", "b": "b", "em": "i", "i": "i", "u": "u", "s": "strike"}


class _Lettore(HTMLParser):
    """Turns the HTML the server cleaned (`impostazioni.html.pulisci`) into flowables. It
    handles what that whitelist lets through; anything else is only its text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.elementi: list = []
        self._testo: list[str] = []
        self._blocco = "p"
        self._allineamento = 0
        self._liste: list[dict] = []
        self._tabella: list[list] | None = None
        self._riga: list | None = None
        self._cella = False

    def _stile(self) -> ParagraphStyle:
        base = STILI_TITOLO.get(self._blocco, TESTO)
        return ParagraphStyle(
            f"{base.name}-{self._allineamento}", base, alignment=self._allineamento
        )

    def _chiudi_testo(self) -> Paragraph | None:
        markup = "".join(self._testo).strip()
        self._testo = []
        return Paragraph(markup, self._stile()) if markup else None

    def _aggiungi_paragrafo(self) -> None:
        paragrafo = self._chiudi_testo()
        if paragrafo is not None:
            self.elementi.append(paragrafo)

    def handle_starttag(self, tag: str, attrs: list) -> None:
        attributi = dict(attrs)
        if tag in SEGNI:
            self._testo.append(f"<{SEGNI[tag]}>")
        elif tag == "br":
            self._testo.append("<br/>")
        elif tag == "a":
            self._testo.append(f'<a href="{escape(attributi.get("href") or "")}"><u>')
        elif tag in ("p", "h2", "h3"):
            if self._cella or self._liste:
                return
            self._aggiungi_paragrafo()
            self._blocco = tag
            stile = (attributi.get("style") or "").replace("text-align:", "").strip()
            self._allineamento = ALLINEAMENTI.get(stile, 0)
        elif tag in ("ul", "ol"):
            if not self._liste:
                self._aggiungi_paragrafo()
            self._liste.append({"tipo": tag, "voci": []})
        elif tag == "li":
            self._blocco, self._allineamento = "p", 0
            self._testo = []
        elif tag == "table":
            self._aggiungi_paragrafo()
            self._tabella = []
        elif tag == "tr" and self._tabella is not None:
            self._riga = []
        elif tag in ("td", "th"):
            self._cella = True
            self._testo = ["<b>"] if tag == "th" else []

    def handle_endtag(self, tag: str) -> None:
        if tag in SEGNI:
            self._testo.append(f"</{SEGNI[tag]}>")
        elif tag == "a":
            self._testo.append("</u></a>")
        elif tag in ("p", "h2", "h3"):
            if not (self._cella or self._liste):
                self._aggiungi_paragrafo()
                self._blocco = "p"
        elif tag == "li" and self._liste:
            paragrafo = self._chiudi_testo()
            if paragrafo is not None:
                self._liste[-1]["voci"].append(ListItem(paragrafo, leftIndent=12))
        elif tag in ("ul", "ol") and self._liste:
            lista = self._liste.pop()
            piatta = ListFlowable(
                lista["voci"],
                bulletType="1" if lista["tipo"] == "ol" else "bullet",
                start=None if lista["tipo"] == "ol" else "•",
                leftIndent=14,
            )
            if self._liste:
                self._liste[-1]["voci"].append(ListItem(piatta, leftIndent=12))
            else:
                self.elementi.append(piatta)
        elif tag in ("td", "th") and self._riga is not None:
            if tag == "th":
                self._testo.append("</b>")
            markup = "".join(self._testo).strip()
            self._riga.append(Paragraph(markup, CELLA) if markup != "<b></b>" else "")
            self._testo, self._cella = [], False
        elif tag == "tr" and self._tabella is not None and self._riga is not None:
            self._tabella.append(self._riga)
            self._riga = None
        elif tag == "table" and self._tabella is not None:
            self.elementi.append(self._chiudi_tabella())
            self._tabella = None

    def _chiudi_tabella(self):
        colonne = max((len(r) for r in self._tabella), default=0)
        if not colonne:
            return Spacer(1, 0)
        righe = [r + [""] * (colonne - len(r)) for r in self._tabella]
        tabella = Table(righe, colWidths=[LARGHEZZA / colonne] * colonne, repeatRows=0)
        tabella.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.25, "#999999"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        return tabella

    def handle_data(self, data: str) -> None:
        self._testo.append(escape(data))

    def close(self) -> None:
        super().close()
        self._aggiungi_paragrafo()


def flowable_del_testo(html: str) -> list:
    lettore = _Lettore()
    lettore.feed(html)
    lettore.close()
    return lettore.elementi
