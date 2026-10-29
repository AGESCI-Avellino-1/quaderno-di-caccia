"""Non-fiscal receipt as PDF, made out by the group (DEC-84). Generated on request,
never stored: the payment record is the source."""

import io
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from apps.organizzazione.models import Gruppo

from .models import Pagamento


def _euro(valore) -> str:
    return f"{valore:.2f} €".replace(".", ",")


def pdf(pagamento: Pagamento) -> bytes:
    stili = getSampleStyleSheet()
    testo = stili["BodyText"]
    gruppo = Gruppo.objects.first()
    intestazione = []
    if gruppo is not None:
        intestazione.append(
            f"<b>{escape(gruppo.denominazione_sociale or 'AGESCI ' + gruppo.denominazione)}</b>"
        )
        if gruppo.codice_fiscale:
            intestazione.append(f"Codice fiscale {escape(gruppo.codice_fiscale)}")
    uscita = io.BytesIO()
    documento = SimpleDocTemplate(
        uscita,
        pagesize=A4,
        title=f"Ricevuta {pagamento.numero}",
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )
    elementi = [Paragraph(riga, testo) for riga in intestazione]
    elementi += [
        Spacer(1, 8 * mm),
        Paragraph(f"Ricevuta n. {pagamento.numero}", stili["Title"]),
    ]
    if pagamento.annullato_il:
        elementi.append(
            Paragraph(
                f"<b>ANNULLATA</b> il {pagamento.annullato_il.strftime('%d/%m/%Y')}: "
                f"{escape(pagamento.motivo_annullamento)}",
                testo,
            )
        )
    elementi += [
        Paragraph(
            f"Ricevuti da <b>{escape(pagamento.versato_da)}</b> il "
            f"{pagamento.data.strftime('%d/%m/%Y')}, {pagamento.get_metodo_display().lower()}, "
            f"<b>{_euro(pagamento.importo)}</b> per:",
            testo,
        ),
        Spacer(1, 4 * mm),
    ]
    righe = [["Socio", "Quota", "Importo"]]
    for riga in pagamento.righe.select_related("quota__tipo", "quota__persona"):
        persona = riga.quota.persona
        righe.append(
            [
                Paragraph(escape(f"{persona.nome} {persona.cognome}"), testo),
                Paragraph(escape(riga.quota.descrizione), testo),
                _euro(riga.importo),
            ]
        )
    righe.append(["", "Totale", _euro(pagamento.importo)])
    tabella = Table(righe, colWidths=[55 * mm, 85 * mm, 30 * mm])
    tabella.setStyle(
        TableStyle(
            [
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.black),
                ("LINEABOVE", (0, -1), (-1, -1), 0.5, colors.black),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("ALIGN", (2, 0), (2, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    elementi += [
        tabella,
        Spacer(1, 8 * mm),
        Paragraph("Ricevuta non fiscale.", testo),
    ]
    if pagamento.note:
        elementi.append(Paragraph(f"Note: {escape(pagamento.note)}", testo))
    documento.build(elementi)
    return uscita.getvalue()
