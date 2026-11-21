"""The totem ceremony as a PDF for the capi (DEC-416): a plain sheet, never stored."""

import io

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from apps.core.testo_pdf import MARGINE, TITOLO, flowable_del_testo

TITOLO_CERIMONIA = "Cerimonia del totem"


def pdf_cerimonia(html: str) -> bytes:
    uscita = io.BytesIO()
    documento = SimpleDocTemplate(
        uscita,
        pagesize=A4,
        leftMargin=MARGINE,
        rightMargin=MARGINE,
        topMargin=18 * mm,
        bottomMargin=16 * mm,
        title=TITOLO_CERIMONIA,
    )
    documento.build(
        [Paragraph(TITOLO_CERIMONIA, TITOLO), Spacer(1, 5 * mm), *flowable_del_testo(html)]
    )
    return uscita.getvalue()
