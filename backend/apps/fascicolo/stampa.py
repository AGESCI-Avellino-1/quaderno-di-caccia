"""The file of a year, or a passage report, as PDF (DEC-203, DEC-204): never stored."""

import io
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from apps.core.stampa import decora_pagina, intestazione
from apps.organizzazione.models import Gruppo

LARGHEZZA = A4[0] - 36 * mm
TESTO = ParagraphStyle("testo", fontName="Helvetica", fontSize=9.5, leading=12.5)
ETICHETTA = ParagraphStyle("etichetta", parent=TESTO, fontName="Helvetica-Bold")
TITOLO = ParagraphStyle("titolo", parent=TESTO, fontName="Helvetica-Bold", fontSize=14, leading=18)
SEZIONE = ParagraphStyle(
    "sezione", parent=TESTO, fontName="Helvetica-Bold", fontSize=11, leading=14, spaceBefore=8
)


def pdf(dati: dict, foto=None) -> bytes:
    gruppo = Gruppo.objects.first()
    uscita = io.BytesIO()
    documento = SimpleDocTemplate(
        uscita,
        pagesize=A4,
        title="Fascicolo personale",
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=14 * mm,
        bottomMargin=18 * mm,
    )
    titolo = [
        Paragraph(escape(dati["persona"]), TITOLO),
        Paragraph(f"Fascicolo personale · {escape(dati['etichetta'])}", TESTO),
    ]
    if foto is not None:
        testata = Table(
            [[titolo, Image(foto, width=25 * mm, height=25 * mm, kind="proportional")]],
            colWidths=[LARGHEZZA - 30 * mm, 30 * mm],
        )
        testata.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
        elementi = [intestazione(gruppo, LARGHEZZA), Spacer(1, 4 * mm), testata]
    else:
        elementi = [intestazione(gruppo, LARGHEZZA), Spacer(1, 4 * mm), *titolo]
    for sezione in dati["sezioni"]:
        elementi.append(Paragraph(escape(sezione["titolo"]), SEZIONE))
        if not sezione["voci"]:
            elementi.append(Paragraph(escape(sezione["vuota"] or "—"), TESTO))
            continue
        righe = [
            [Paragraph(escape(v["etichetta"]), ETICHETTA), Paragraph(escape(v["valore"]), TESTO)]
            for v in sezione["voci"]
        ]
        tabella = Table(righe, colWidths=[55 * mm, LARGHEZZA - 55 * mm])
        tabella.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.25, "#cccccc"),
                ]
            )
        )
        elementi.append(tabella)
    pagina = decora_pagina(gruppo)
    documento.build(elementi, onFirstPage=pagina, onLaterPages=pagina)
    return uscita.getvalue()
