"""The group's letterhead on every print (DEC-192): logo, name and the data the AGESCI
forms carry (codice fiscale, seat, phones, emails, website, RUNTS entry)."""

from xml.sax.saxutils import escape

from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, Table, TableStyle

DESTRA = ParagraphStyle("intestazione", fontName="Helvetica", fontSize=8, leading=10, alignment=2)


def righe_intestazione(gruppo) -> list[str]:
    if gruppo is None:
        return []
    righe = [
        f"<b>{escape(gruppo.denominazione_sociale or 'AGESCI Gruppo ' + gruppo.denominazione)}</b>"
    ]
    if gruppo.codice_fiscale:
        righe.append(f"Codice fiscale: {escape(gruppo.codice_fiscale)}")
    sede = ", ".join(
        x
        for x in (
            gruppo.sede_indirizzo,
            " ".join(
                y
                for y in (
                    gruppo.sede_cap,
                    gruppo.sede_comune,
                    f"({gruppo.sede_provincia})" if gruppo.sede_provincia else "",
                )
                if y
            ),
        )
        if x
    )
    if sede:
        righe.append(escape(sede))
    telefoni = " – ".join(
        x
        for x in (
            f"tel. {gruppo.telefono}" if gruppo.telefono else "",
            f"cell. {gruppo.cellulare}" if gruppo.cellulare else "",
        )
        if x
    )
    if telefoni:
        righe.append(escape(telefoni))
    email = " – ".join(x for x in (gruppo.email, gruppo.pec) if x)
    if email:
        righe.append(escape(email))
    if gruppo.sito:
        righe.append(escape(gruppo.sito))
    return righe


def piede(gruppo) -> str:
    """The RUNTS line at the foot of the AGESCI forms."""
    if gruppo is None or not gruppo.runts_repertorio:
        return "WAGGGS / WOSM Member"
    data = f" del {gruppo.runts_data:%d/%m/%Y}" if gruppo.runts_data else ""
    return (
        "Iscritta al Registro Unico Nazionale del Terzo Settore – repertorio n. "
        f"{gruppo.runts_repertorio}{data} – WAGGGS / WOSM Member"
    )


def intestazione(gruppo, larghezza: float) -> Table:
    """Logo on the left (if any), the group's data on the right."""
    logo = ""
    if gruppo is not None and gruppo.logo:
        try:
            logo = Image(gruppo.logo.path, width=22 * mm, height=22 * mm, kind="proportional")
        except OSError:
            logo = ""
    testo = [Paragraph(riga, DESTRA) for riga in righe_intestazione(gruppo)]
    tabella = Table([[logo, testo]], colWidths=[26 * mm, larghezza - 26 * mm])
    tabella.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return tabella


# The band at the top of the group's letterhead paper: indigo, then gold after a point
# (colours of the AGESCI palette, frontend/src/theme/_palette.scss).
INDACO = "#462d7b"
ORO = "#ffcc1e"


def decora_pagina(gruppo, margine: float = 18 * mm):
    """A reportlab page callback: the band on top and the RUNTS line at the foot."""
    from reportlab.lib.colors import HexColor

    def disegna(canvas, documento):
        larghezza, altezza = documento.pagesize
        y, h = altezza - 9 * mm, 2.2 * mm
        punta = margine + (larghezza - 2 * margine) * 0.62
        canvas.saveState()
        canvas.setFillColor(HexColor(ORO))
        canvas.rect(punta, y, larghezza - margine - punta, h, stroke=0, fill=1)
        canvas.setFillColor(HexColor(INDACO))
        percorso = canvas.beginPath()
        percorso.moveTo(margine, y)
        percorso.lineTo(punta, y)
        percorso.lineTo(punta + h / 2, y + h / 2)
        percorso.lineTo(punta, y + h)
        percorso.lineTo(margine, y + h)
        percorso.close()
        canvas.drawPath(percorso, stroke=0, fill=1)
        canvas.setFillColor(HexColor("#000000"))
        canvas.setFont("Helvetica", 7)
        canvas.drawString(margine, 10 * mm, piede(gruppo))
        canvas.drawRightString(larghezza - margine, 10 * mm, f"Pag. {documento.page}")
        canvas.restoreState()

    return disegna
