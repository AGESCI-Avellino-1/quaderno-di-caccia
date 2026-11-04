"""The minutes as a PDF on the group's letterhead (DEC-322, DEC-324)."""

import io
from html.parser import HTMLParser
from xml.sax.saxutils import escape

from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from apps.core.stampa import decora_pagina, intestazione
from apps.organizzazione.models import Gruppo

from .models import TipoVerbale, Verbale

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


def _firme(verbale: Verbale, tipo: str) -> list:
    """The space to sign: never for the meetings with the ragazzi, which are informal
    (DEC-324)."""
    if tipo == TipoVerbale.ASSEMBLEA:
        presidente = verbale.cariche.get("presidente", {}).get("nome", "")
        righe = [f"Il presidente: {presidente}"] + [
            f"Il segretario: {s['nome']}" for s in verbale.cariche.get("segretari", [])
        ]
    elif tipo in (TipoVerbale.COCA, TipoVerbale.GENITORI):
        righe = [f"Chi ha scritto il verbale: {verbale.autore_nome}"]
    else:
        return []
    elementi: list = [Spacer(1, 4 * mm)]
    for riga in righe:
        tabella = Table(
            [[Paragraph(escape(riga), CELLA)], [""], [""]],
            colWidths=[LARGHEZZA * 0.6],
            rowHeights=[6 * mm, 10 * mm, 2 * mm],
            hAlign="LEFT",
        )
        tabella.setStyle(TableStyle([("LINEBELOW", (0, 1), (0, 1), 0.5, "#000000")]))
        elementi += [Spacer(1, 4 * mm), tabella]
    return elementi


def _intestazione_assemblea(verbale: Verbale, tipo: str) -> list:
    if tipo != TipoVerbale.ASSEMBLEA:
        return []
    presidente = verbale.cariche.get("presidente", {}).get("nome", "")
    segretari = ", ".join(s["nome"] for s in verbale.cariche.get("segretari", []))
    return [
        Paragraph(f"<b>Presidente:</b> {escape(presidente)}", TESTO),
        Paragraph(f"<b>Segretari:</b> {escape(segretari)}", TESTO),
    ]


def _presenti(verbale: Verbale, tipo: str) -> list:
    """Who was there; at the assembly with who may vote, no child named (DEC-326, DEC-328)."""
    if not verbale.presenti:
        return []
    assemblea = tipo == TipoVerbale.ASSEMBLEA
    testata = ["Presente", "Qualità", "Diritto di voto"] if assemblea else ["Presente"]
    righe = [[Paragraph(f"<b>{t}</b>", CELLA) for t in testata]]
    for p in verbale.presenti:
        riga = [Paragraph(escape(p["nome"]), CELLA)]
        if assemblea:
            riga += [
                Paragraph(escape(p.get("qualita", "")), CELLA),
                Paragraph("Sì" if p.get("voto") else "No", CELLA),
            ]
        righe.append(riga)
    larghezze = [LARGHEZZA * 0.45, LARGHEZZA * 0.35, LARGHEZZA * 0.2] if assemblea else [LARGHEZZA]
    tabella = Table(righe, colWidths=larghezze, repeatRows=1)
    tabella.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, -1), 0.25, "#cccccc"),
                ("LINEBELOW", (0, 0), (-1, 0), 0.75, "#462d7b"),
            ]
        )
    )
    return [Spacer(1, 5 * mm), tabella]


def pdf(verbale: Verbale, tipo: str) -> bytes:
    uscita = io.BytesIO()
    documento = SimpleDocTemplate(
        uscita,
        pagesize=A4,
        leftMargin=MARGINE,
        rightMargin=MARGINE,
        topMargin=14 * mm,
        bottomMargin=16 * mm,
        title=f"Verbale della riunione del {_giorno(verbale)}",
    )
    gruppo = Gruppo.objects.first()
    evento = verbale.evento
    elementi = [
        intestazione(gruppo, LARGHEZZA),
        Spacer(1, 4 * mm),
        Paragraph("Verbale della riunione", TITOLO),
        Paragraph(escape(f"{evento.titolo} – {_giorno(verbale)}"), SOTTOTITOLO),
        Spacer(1, 5 * mm),
        *_intestazione_assemblea(verbale, tipo),
        *flowable_del_testo(verbale.testo),
        *_presenti(verbale, tipo),
        *_firme(verbale, tipo),
    ]
    pagina = decora_pagina(gruppo, MARGINE)
    documento.build(elementi, onFirstPage=pagina, onLaterPages=pagina)
    return uscita.getvalue()


def _giorno(verbale: Verbale) -> str:
    return f"{timezone.localtime(verbale.evento.inizio):%d/%m/%Y}"
