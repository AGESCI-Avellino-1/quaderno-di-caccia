"""The attendance sheet to print and fill in by hand (DEC-78). Generated on request."""

import io
from xml.sax.saxutils import escape

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle

from .models import Evento, StatoPartecipazione


def foglio(evento: Evento) -> bytes:
    stili = getSampleStyleSheet()
    uscita = io.BytesIO()
    documento = SimpleDocTemplate(
        uscita,
        pagesize=A4,
        title=f"Presenze: {evento.titolo}",
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )
    inizio = timezone.localtime(evento.inizio)
    righe = [["Socio", "Presente", "Assente", "Giustificato"]]
    for p in evento.partecipazioni.select_related("persona").order_by(
        "persona__cognome", "persona__nome"
    ):
        if p.stato == StatoPartecipazione.NON_INVITATO:
            continue
        nota = (
            " (ha detto che non partecipa)" if p.stato == StatoPartecipazione.NON_PARTECIPA else ""
        )
        righe.append([f"{p.persona.cognome} {p.persona.nome}{nota}", "", "", ""])
    tabella = Table(righe, colWidths=[100 * mm, 25 * mm, 25 * mm, 30 * mm], repeatRows=1)
    tabella.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.whitesmoke]),
                ("TOPPADDING", (0, 1), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
            ]
        )
    )
    documento.build(
        [
            Paragraph(escape(evento.titolo), stili["Title"]),
            Paragraph(
                f"{inizio.strftime('%d/%m/%Y %H:%M')} · {escape(evento.luogo or '')}",
                stili["BodyText"],
            ),
            tabella,
            Paragraph("Segna una X; poi riporta le presenze nell'app.", stili["BodyText"]),
        ]
    )
    return uscita.getvalue()
