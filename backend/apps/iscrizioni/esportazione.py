"""The list of registrations to enter in BuonaStrada as XLSX and PDF (DEC-127).
Personal data: generated on request for the capigruppo, never stored."""

import io
from datetime import date
from xml.sax.saxutils import escape

from openpyxl import Workbook
from openpyxl.styles import Font
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle

from .servizi import COLONNE

TITOLO = "Iscrizioni da inserire in BuonaStrada"


def xlsx(righe: list[list[str]]) -> bytes:
    libro = Workbook()
    foglio = libro.active
    foglio.title = "Iscrizioni"
    foglio.append(list(COLONNE))
    for cella in foglio[1]:
        cella.font = Font(bold=True)
    for riga in righe:
        foglio.append(riga)
    for colonna in foglio.columns:
        larghezza = max(len(str(c.value or "")) for c in colonna)
        foglio.column_dimensions[colonna[0].column_letter].width = min(larghezza + 2, 40)
    foglio.freeze_panes = "A2"
    uscita = io.BytesIO()
    libro.save(uscita)
    return uscita.getvalue()


def pdf(righe: list[list[str]]) -> bytes:
    """One block per member (20 columns do not fit a page width): label, value."""
    stili = getSampleStyleSheet()
    piccolo = stili["BodyText"].clone("piccolo", fontSize=8, leading=10)
    uscita = io.BytesIO()
    documento = SimpleDocTemplate(
        uscita,
        pagesize=landscape(A4),
        title=TITOLO,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )
    elementi = [
        Paragraph(TITOLO, stili["Title"]),
        Paragraph(f"Al {date.today().strftime('%d/%m/%Y')}", piccolo),
    ]
    if not righe:
        elementi.append(Paragraph("Nessuna iscrizione da inserire.", stili["BodyText"]))
    for riga in righe:
        dati = [
            [Paragraph(f"<b>{COLONNE[i]}</b>", piccolo), Paragraph(escape(riga[i]) or "—", piccolo)]
            for i in range(len(COLONNE))
        ]
        # Two label/value pairs per row, to keep each member on part of a page.
        coppie = [
            dati[i] + (dati[i + 1] if i + 1 < len(dati) else ["", ""])
            for i in range(0, len(dati), 2)
        ]
        tabella = Table(coppie, colWidths=[45 * mm, 85 * mm, 45 * mm, 85 * mm])
        tabella.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        elementi += [
            Paragraph(f"<b>{escape(riga[1])} {escape(riga[2])}</b>", stili["Heading3"]),
            tabella,
        ]
    documento.build(elementi)
    return uscita.getvalue()
