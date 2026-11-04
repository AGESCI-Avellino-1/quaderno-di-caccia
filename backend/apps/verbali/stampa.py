"""The minutes as a PDF on the group's letterhead (DEC-322, DEC-324)."""

import io
from xml.sax.saxutils import escape

from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from apps.core.stampa import decora_pagina, intestazione
from apps.core.testo_pdf import (
    CELLA,
    LARGHEZZA,
    MARGINE,
    SOTTOTITOLO,
    TESTO,
    TITOLO,
    flowable_del_testo,
)
from apps.organizzazione.models import Gruppo

from .models import TipoVerbale, Verbale


def _spazi_firma(righe: list[str]) -> list:
    elementi: list = []
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
    return [Spacer(1, 4 * mm), *_spazi_firma(righe)]


def _intestazione_assemblea(verbale: Verbale, tipo: str) -> list:
    # With the template the text already names them.
    if tipo != TipoVerbale.ASSEMBLEA or verbale.da_modello:
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


def _documento(titolo: str, corpo: list, titolo_file: str) -> bytes:
    """On the group's letterhead, the one of every print (DEC-192, DEC-336)."""
    uscita = io.BytesIO()
    documento = SimpleDocTemplate(
        uscita,
        pagesize=A4,
        leftMargin=MARGINE,
        rightMargin=MARGINE,
        topMargin=14 * mm,
        bottomMargin=16 * mm,
        title=titolo_file,
    )
    gruppo = Gruppo.objects.first()
    elementi = [intestazione(gruppo, LARGHEZZA), Spacer(1, 4 * mm)]
    if titolo:
        elementi.append(Paragraph(escape(titolo), TITOLO))
    elementi += corpo
    pagina = decora_pagina(gruppo, MARGINE)
    documento.build(elementi, onFirstPage=pagina, onLaterPages=pagina)
    return uscita.getvalue()


def pdf(verbale: Verbale, tipo: str) -> bytes:
    evento = verbale.evento
    giorno = _giorno(evento)
    if verbale.da_modello:
        titolo = "Verbale Assemblea di Gruppo"
        apertura: list = [Spacer(1, 5 * mm)]
    else:
        titolo = "Verbale della riunione"
        apertura = [
            Paragraph(escape(f"{evento.titolo} – {giorno}"), SOTTOTITOLO),
            Spacer(1, 5 * mm),
        ]
    return _documento(
        titolo,
        [
            *apertura,
            *_intestazione_assemblea(verbale, tipo),
            *flowable_del_testo(verbale.testo),
            *_presenti(verbale, tipo),
            *_firme(verbale, tipo),
        ],
        f"Verbale della riunione del {giorno}",
    )


def pdf_convocazione(testo: str) -> bytes:
    return _documento("", flowable_del_testo(testo), "Convocazione Assemblea di Gruppo")


def pdf_collegato(collegato) -> bytes:
    corpo = [Spacer(1, 5 * mm), *flowable_del_testo(collegato.testo)]
    for blocco in collegato.firme:
        if blocco.get("intro"):
            corpo += [Spacer(1, 4 * mm), Paragraph(escape(blocco["intro"]), TESTO)]
        corpo += _spazi_firma(blocco.get("righe", []))
    return _documento(
        collegato.get_tipo_display(),
        corpo,
        f"{collegato.get_tipo_display()} del {_giorno(collegato.evento)}",
    )


def _giorno(evento) -> str:
    return f"{timezone.localtime(evento.inizio):%d/%m/%Y}"
