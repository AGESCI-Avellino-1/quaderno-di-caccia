"""The waiting list flyer (DEC-304): an A4 PDF with the group's letterhead, a short text,
the QR code and the link of the public waiting list. Never stored; the link is the same
for everybody and says nothing about who shares it."""

import io
from xml.sax.saxutils import escape

from django.conf import settings
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from apps.core.stampa import INDACO, decora_pagina, intestazione
from apps.impostazioni import segnaposto
from apps.impostazioni.models import Impostazioni
from apps.organizzazione.models import Gruppo

TESTO_BASE = (
    "Vuoi entrare in [Gruppo]? Inquadra il codice con il telefono e mettiti in lista "
    "d'attesa: non serve un account.\n\n"
    "I capi chiamano a inizio anno scout, secondo l'età e i posti nelle unità."
)
SEGNAPOSTO = (segnaposto.GRUPPO, segnaposto.SIGLA_GRUPPO)
LUNGHEZZA_MASSIMA = 1000

MARGINE = 18 * mm
LARGHEZZA = A4[0] - 2 * MARGINE
LATO_QR = 95 * mm

TITOLO = ParagraphStyle(
    "titolo",
    fontName="Helvetica-Bold",
    fontSize=30,
    leading=36,
    alignment=1,
    textColor=HexColor(INDACO),
)
GRUPPO = ParagraphStyle("gruppo", fontName="Helvetica-Bold", fontSize=16, leading=20, alignment=1)
TESTO = ParagraphStyle(
    "testo", fontName="Helvetica", fontSize=14, leading=19, alignment=1, spaceAfter=8
)
LINK = ParagraphStyle("link", fontName="Helvetica", fontSize=12, leading=15, alignment=1)


def indirizzo() -> str:
    """The public waiting list page (DEC-256), as the PWA links it."""
    return f"{settings.FRONTEND_URL}/lista-attesa"


def testo(imp: Impostazioni) -> str:
    """The group's text, or the base one."""
    return imp.volantino_attesa or TESTO_BASE


def compila(testo_: str, imp: Impostazioni) -> str:
    """The placeholders filled in (compared ignoring case, as the PWA does)."""
    valori = {
        segnaposto.GRUPPO.casefold(): imp.nome_del_gruppo(),
        segnaposto.SIGLA_GRUPPO.casefold(): imp.sigla_gruppo,
    }
    return segnaposto.SEGNAPOSTO.sub(
        lambda m: valori.get(m.group(1).strip().casefold(), m.group(0)), testo_
    )


def _qr(valore: str) -> Drawing:
    codice = QrCodeWidget(valore, barLevel="M", barBorder=2)
    x0, y0, x1, y1 = codice.getBounds()
    disegno = Drawing(
        LATO_QR,
        LATO_QR,
        transform=[LATO_QR / (x1 - x0), 0, 0, LATO_QR / (y1 - y0), 0, 0],
    )
    disegno.add(codice)
    disegno.hAlign = "CENTER"
    return disegno


def pdf() -> bytes:
    imp = Impostazioni.carica()
    gruppo = Gruppo.objects.first()
    link = indirizzo()
    uscita = io.BytesIO()
    documento = SimpleDocTemplate(
        uscita,
        pagesize=A4,
        title="Lista d'attesa",
        leftMargin=MARGINE,
        rightMargin=MARGINE,
        topMargin=14 * mm,
        bottomMargin=18 * mm,
    )
    elementi = [
        intestazione(gruppo, LARGHEZZA),
        Spacer(1, 14 * mm),
        Paragraph("Lista d'attesa", TITOLO),
        Paragraph(escape(imp.nome_del_gruppo()), GRUPPO),
        Spacer(1, 8 * mm),
    ]
    for capoverso in compila(testo(imp), imp).split("\n\n"):
        righe = [escape(r.strip()) for r in capoverso.splitlines() if r.strip()]
        if righe:
            elementi.append(Paragraph("<br/>".join(righe), TESTO))
    elementi += [Spacer(1, 6 * mm), _qr(link), Spacer(1, 4 * mm), Paragraph(escape(link), LINK)]
    decora = decora_pagina(gruppo, MARGINE)
    documento.build(elementi, onFirstPage=decora, onLaterPages=decora)
    return uscita.getvalue()
