"""An entry of the book as a PDF (DEC-437, the totem ceremony's since DEC-416): a plain sheet,
never stored."""

import io

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from apps.core.testo_pdf import MARGINE, TITOLO, flowable_del_testo


def pdf_voce(titolo: str, html: str) -> bytes:
    uscita = io.BytesIO()
    documento = SimpleDocTemplate(
        uscita,
        pagesize=A4,
        leftMargin=MARGINE,
        rightMargin=MARGINE,
        topMargin=18 * mm,
        bottomMargin=16 * mm,
        title=titolo,
    )
    documento.build([Paragraph(titolo, TITOLO), Spacer(1, 5 * mm), *flowable_del_testo(html)])
    return uscita.getvalue()
