"""The list of the group's roles as PDF, for the capigruppo (DEC-284): never stored.

The capigruppo choose the kinds of role and how to group the capi: by unit (each role in
its unit, the group's roles in the Co.Ca.; a capo in every section of their roles) or by
role. Each capo: codice socio, name, surname, training level
(today's: the app keeps no history of it). Roles in force today, or at the end of a past
associative year.
"""

import io
from dataclasses import dataclass, field
from datetime import date
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from apps.anagrafica.models import Persona
from apps.core.anno import AnnoAssociativo
from apps.core.stampa import decora_pagina, intestazione

from .models import (
    INCARICHI_DI_SERVIZIO,
    Branca,
    Gruppo,
    Incarico,
    RuoloIncarico,
    TipoUnita,
    Unita,
)

# The roles of the capi that can go in the list, in the order of the sections.
RUOLI_ELENCO = (
    RuoloIncarico.CAPOGRUPPO,
    RuoloIncarico.AE_GRUPPO,
    RuoloIncarico.CAPO_UNITA,
    RuoloIncarico.STAFF,
    RuoloIncarico.AE_UNITA,
    RuoloIncarico.SUPPORTO_GRUPPO,
    RuoloIncarico.SUPPORTO_EDUCATIVO,
    # Only in a year when someone held it (DEC-293).
    RuoloIncarico.A_DISPOSIZIONE,
    RuoloIncarico.TESORIERE_GRUPPO,
    RuoloIncarico.TESORIERE_UNITA,
    RuoloIncarico.AMMINISTRATORE,
)
# A capo with additional roles only (a treasurer serving no unit) shows this next to the
# name, in the PDF only: nothing is recorded (maintainer, 03/11).
SENZA_SERVIZIO = RuoloIncarico.SUPPORTO_GRUPPO.label
# The sections by unit: the Co.Ca. first, then L/C, E/G, R/S, each by code (maintainer,
# 03/11).
ORDINE_BRANCHE = [Branca.LC, Branca.EG, Branca.RS]


@dataclass
class Riga:
    persona: Persona
    incarichi: list[str] = field(default_factory=list)


@dataclass
class Sezione:
    titolo: str
    righe: list[Riga]


def giorno_di_riferimento(anno: int | None, oggi: date | None = None) -> date:
    """Today, or the last day of a past associative year (its roles at its end)."""
    oggi = oggi or date.today()
    if anno is None or AnnoAssociativo(anno).contiene(oggi):
        return oggi
    return AnnoAssociativo(anno).fine


def _ordine_unita(unita: Unita) -> tuple:
    branca = unita.branca
    posto = ORDINE_BRANCHE.index(branca) if branca in ORDINE_BRANCHE else len(ORDINE_BRANCHE)
    # A unit with no BuonaStrada code yet goes after the coded ones of its branch.
    return (posto, not unita.codice_unita, unita.codice_unita, unita.progressivo or 0, unita.nome)


def _ordine_persona(persona: Persona) -> tuple:
    return (persona.cognome.lower(), persona.nome.lower(), persona.pk)


def _etichetta(incarico: Incarico, sezione: Unita | None = None) -> str:
    """The role, with its unit when it is not the section's own."""
    testo = incarico.get_ruolo_display()
    if incarico.unita_id and incarico.unita_id != getattr(sezione, "pk", None):
        testo += f" – {incarico.unita}"
    return testo


def sezioni(ruoli: set[str], raggruppa: str, giorno: date) -> list[Sezione]:
    scelti = [r for r in RUOLI_ELENCO if r in ruoli]
    incarichi = list(
        Incarico.objects.attivi(giorno)
        .filter(ruolo__in=RUOLI_ELENCO, persona__isnull=False)
        .select_related("persona", "unita")
    )
    if raggruppa == "incarico":
        return _per_incarico(scelti, incarichi)
    return _per_unita(set(scelti), incarichi)


def _per_incarico(scelti: list[str], incarichi: list[Incarico]) -> list[Sezione]:
    risultato = []
    for ruolo in scelti:
        del_ruolo = sorted(
            (i for i in incarichi if i.ruolo == ruolo),
            key=lambda i: (
                _ordine_unita(i.unita) if i.unita_id else (),
                _ordine_persona(i.persona),
            ),
        )
        righe = [Riga(i.persona, [str(i.unita)] if i.unita_id else []) for i in del_ruolo]
        risultato.append(Sezione(RuoloIncarico(ruolo).label, righe))
    return [s for s in risultato if s.righe]


def _per_unita(scelti: set[str], incarichi: list[Incarico]) -> list[Sezione]:
    """Every role in its section: a unit's roles in that unit, the group's in the Co.Ca. A
    capo shows in every section where they hold a chosen role, with that section's roles
    only next to the name, even if that lists them more than once (maintainer, 03/11)."""
    per_persona: dict[int, list[Incarico]] = {}
    for incarico in sorted(incarichi, key=lambda i: RUOLI_ELENCO.index(i.ruolo)):
        per_persona.setdefault(incarico.persona_id, []).append(incarico)

    righe_di: dict[object, list[Riga]] = {}
    coca = "coca"
    unita_di: dict[int, Unita] = {}
    for propri in per_persona.values():
        scelti_propri = [i for i in propri if i.ruolo in scelti]
        if not scelti_propri:
            continue
        persona = propri[0].persona
        per_sezione: dict[object, list[str]] = {}
        for i in scelti_propri:
            if i.unita_id:
                unita_di[i.unita_id] = i.unita
                per_sezione.setdefault(i.unita_id, []).append(_etichetta(i, i.unita))
            else:
                per_sezione.setdefault(coca, []).append(_etichetta(i))
        # No service at all (e.g. a unit treasurer only): in the Co.Ca. too (DEC-284).
        if not any(i.ruolo in INCARICHI_DI_SERVIZIO | {RuoloIncarico.CAPOGRUPPO} for i in propri):
            per_sezione.setdefault(coca, []).insert(0, SENZA_SERVIZIO)
        for sezione, etichette in per_sezione.items():
            righe_di.setdefault(sezione, []).append(Riga(persona, etichette))

    risultato = [
        Sezione(str(unita_di[u]), sorted(righe_di[u], key=lambda r: _ordine_persona(r.persona)))
        for u in sorted(
            (k for k in righe_di if k != coca), key=lambda k: _ordine_unita(unita_di[k])
        )
    ]
    if coca in righe_di:
        coca_unita = Unita.objects.filter(tipo=TipoUnita.COMUNITA_CAPI).first()
        risultato.insert(
            0,
            Sezione(
                str(coca_unita) if coca_unita else "Comunità Capi",
                sorted(righe_di[coca], key=lambda r: _ordine_persona(r.persona)),
            ),
        )
    return risultato


LARGHEZZA = A4[0] - 36 * mm
TESTO = ParagraphStyle("testo", fontName="Helvetica", fontSize=9, leading=11.5)
TESTATA = ParagraphStyle("testata", parent=TESTO, fontName="Helvetica-Bold")
TITOLO = ParagraphStyle("titolo", parent=TESTO, fontName="Helvetica-Bold", fontSize=14, leading=18)
SEZIONE = ParagraphStyle(
    "sezione", parent=TESTO, fontName="Helvetica-Bold", fontSize=11, leading=14, spaceBefore=8
)
COLONNE = [24 * mm, 36 * mm, 36 * mm, 20 * mm]


def pdf(sezioni_: list[Sezione], giorno: date, raggruppa: str) -> bytes:
    gruppo = Gruppo.objects.first()
    uscita = io.BytesIO()
    documento = SimpleDocTemplate(
        uscita,
        pagesize=A4,
        title="Incarichi del gruppo",
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=14 * mm,
        bottomMargin=18 * mm,
    )
    anno = AnnoAssociativo.da_data(giorno)
    quando = (
        f"al {giorno:%d/%m/%Y}"
        if giorno != anno.fine
        else f"alla fine dell'anno associativo {anno.etichetta}"
    )
    elementi = [
        intestazione(gruppo, LARGHEZZA),
        Spacer(1, 4 * mm),
        Paragraph("Incarichi del gruppo", TITOLO),
        Paragraph(escape(f"Incarichi in corso {quando}"), TESTO),
    ]
    ultima = "Incarichi" if raggruppa == "unita" else "Unità"
    for sezione in sezioni_:
        elementi.append(Paragraph(escape(sezione.titolo), SEZIONE))
        righe = [
            [
                Paragraph(t, TESTATA)
                for t in ("Codice socio", "Cognome", "Nome", "Livello Fo.Ca.", ultima)
            ]
        ]
        for riga in sezione.righe:
            p = riga.persona
            livello = "" if p.livello_formazione is None else str(p.livello_formazione)
            righe.append(
                [
                    Paragraph(escape(p.codice_socio or ""), TESTO),
                    Paragraph(escape(p.cognome), TESTO),
                    Paragraph(escape(p.nome), TESTO),
                    Paragraph(escape(livello), TESTO),
                    Paragraph(escape(", ".join(riga.incarichi)), TESTO),
                ]
            )
        tabella = Table(righe, colWidths=[*COLONNE, LARGHEZZA - sum(COLONNE)], repeatRows=1)
        tabella.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.25, "#cccccc"),
                    ("LINEBELOW", (0, 0), (-1, 0), 0.75, "#462d7b"),
                ]
            )
        )
        elementi.append(tabella)
    if not sezioni_:
        elementi.append(Spacer(1, 4 * mm))
        elementi.append(Paragraph("Nessun incarico di quelli scelti.", TESTO))
    pagina = decora_pagina(gruppo)
    documento.build(elementi, onFirstPage=pagina, onLaterPages=pagina)
    return uscita.getvalue()
