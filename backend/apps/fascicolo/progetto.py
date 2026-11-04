"""The capo's project (DEC-335): written only by the capo, as text with the editor or as a
PDF. Every save is a new version with its date: the latest is in force, the others stay."""

import io
import uuid
from xml.sax.saxutils import escape

from django.core.exceptions import ValidationError
from django.db import transaction
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from apps.anagrafica.models import Persona
from apps.core.file_caricati import (
    DOCUMENTI,
    controlla_file,
    estensione,
    togli_file_dopo,
)
from apps.core.testo_pdf import MARGINE, SOTTOTITOLO, TITOLO, flowable_del_testo
from apps.impostazioni.html import pulisci

from .models import ProgettoCapo

ERRORE_TIPO = "Il progetto si carica come PDF."


@transaction.atomic
def nuova_versione(persona: Persona, file, testo: str) -> ProgettoCapo:
    pulito = pulisci(testo or "", immagini=False)
    if bool(file) == bool(pulito):
        raise ValidationError("Scrivi il testo oppure carica il PDF.")
    versione = ProgettoCapo(persona=persona, testo=pulito)
    if file:
        nome, _ = controlla_file(file, {".pdf": DOCUMENTI[".pdf"]}, ERRORE_TIPO)
        versione.file.save(f"{uuid.uuid4().hex}{estensione(nome)}", file, save=False)
        versione.nome_file = nome
        versione.dimensione = file.size
    versione.save()
    return versione


@transaction.atomic
def elimina(versione: ProgettoCapo) -> None:
    togli_file_dopo(versione.file)
    versione.delete()


def pdf_del_testo(versione: ProgettoCapo) -> bytes:
    """On a plain sheet, no letterhead: it is a personal document, not an act of the group."""
    uscita = io.BytesIO()
    documento = SimpleDocTemplate(
        uscita,
        pagesize=A4,
        leftMargin=MARGINE,
        rightMargin=MARGINE,
        topMargin=18 * mm,
        bottomMargin=16 * mm,
        title="Progetto del capo",
    )
    persona = versione.persona
    documento.build(
        [
            Paragraph("Progetto del capo", TITOLO),
            Paragraph(
                escape(f"{persona.nome} {persona.cognome} – {versione.creato_il:%d/%m/%Y}"),
                SOTTOTITOLO,
            ),
            Spacer(1, 5 * mm),
            *flowable_del_testo(versione.testo),
        ]
    )
    return uscita.getvalue()
