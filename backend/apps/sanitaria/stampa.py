"""The group's medical form ("Scheda sanitaria personale", DEC-289), filled in from the
app, on the group's letterhead (DEC-192): the same sections as the paper model, the
parents with their phones for a minor, the emergency contact of an event when there is
one (DEC-53), "Altre informazioni" for the data the model lacks, the declaration and
consent of the settings, the signatures. An adult signs their own form.

Generated on request, never stored.
"""

import io
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from apps.anagrafica.models import Appartenenza, Persona, RelazioneTutela
from apps.core.stampa import INDACO, decora_pagina, intestazione
from apps.organizzazione.models import Gruppo

from .models import CAMPO_DEL_TIPO, Gravita, InformazioniSanitarie, ReperibilitaEvento
from .testi import testi

LARGHEZZA = A4[0] - 36 * mm
TESTO = ParagraphStyle("testo", fontName="Helvetica", fontSize=9.5, leading=12.5)
PICCOLO = ParagraphStyle("piccolo", parent=TESTO, fontSize=8, leading=10)
GRASSETTO = ParagraphStyle("grassetto", parent=TESTO, fontName="Helvetica-Bold")
TITOLO = ParagraphStyle(
    "titolo", parent=TESTO, fontName="Helvetica-Bold", fontSize=14, leading=18, alignment=1
)
SOTTOTITOLO = ParagraphStyle("sottotitolo", parent=TESTO, fontSize=8.5, alignment=1)
SEZIONE = ParagraphStyle(
    "sezione",
    parent=TESTO,
    fontName="Helvetica-Bold",
    fontSize=10.5,
    leading=14,
    spaceBefore=7,
    spaceAfter=3,
    textColor=INDACO,
)

# Short words on paper; the app explains "grave" as a risk for life.
GRAVITA = {Gravita.LIEVE: "lieve", Gravita.MODERATA: "moderata", Gravita.GRAVE: "grave"}
# Helvetica has no ballot boxes: [X] and [  ] print everywhere.
SI, NO, VUOTO = "[X]", "[X]", "[&nbsp;&nbsp;]"
ANAMNESI = (
    (
        "patologie",
        "Soffre o ha sofferto di patologie rilevanti? (es. asma, epilessia, diabete, problemi "
        "cardiaci, convulsioni febbrili…)",
    ),
    ("interventi", "Ha subito interventi chirurgici o traumi recenti?"),
    (
        "disturbi_sonno",
        "Soffre di disturbi del sonno? (es. sonnambulismo, incubi frequenti, enuresi notturna)",
    ),
    ("occhiali", "Porta occhiali da vista, lenti a contatto o apparecchi ortodontici mobili?"),
)
TIPI = (
    ("FARMACI", "Allergie a farmaci (es. antibiotici)"),
    ("ALIMENTARE", "Allergie alimentari"),
    ("INTOLLERANZA", "Intolleranze alimentari (es. celiachia, lattosio)"),
    ("INSETTI", "Allergie a punture d'insetto (api, vespe)"),
    ("AMBIENTALE", "Allergie ambientali (polline, polvere, ecc.)"),
)


def _e(valore) -> str:
    return escape(str(valore)) if valore not in (None, "") else ""


def _linea(valore) -> str:
    """The value, or a line to write on by hand."""
    return f"<b>{_e(valore)}</b>" if valore not in (None, "") else "______________________"


def _no_si(valore, dettaglio: str = "") -> str:
    no = NO if valore is False else VUOTO
    si = SI if valore else VUOTO
    testo = f"{no} NO &nbsp;&nbsp; {si} SÌ"
    if valore:
        testo += f" → <b>{_e(dettaglio)}</b>"
    elif valore is None:
        testo += " → ______________________"
    return testo


def _tabella(righe, larghezze, intestazione_righe: int = 1) -> Table:
    tabella = Table(righe, colWidths=larghezze, repeatRows=intestazione_righe)
    tabella.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.4, "#999999"),
                ("BACKGROUND", (0, 0), (-1, intestazione_righe - 1), "#e9e4f2"),
            ]
        )
    )
    return tabella


def _due_colonne(righe) -> Table:
    tabella = Table(righe, colWidths=[LARGHEZZA * 0.38, LARGHEZZA * 0.62])
    tabella.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (1, 0), (1, -1), 0.3, "#bbbbbb"),
            ]
        )
    )
    return tabella


def _unita(persona: Persona) -> str:
    appartenenza = (
        Appartenenza.objects.attive().filter(persona=persona).select_related("unita").first()
    )
    return str(appartenenza.unita) if appartenenza else ""


def _scheda(persona: Persona, recapito: tuple[str, str] | None, gruppo) -> list:
    info = (
        InformazioniSanitarie.objects.filter(persona=persona)
        .prefetch_related("allergie", "farmaci")
        .first()
    )
    minore = persona.e_minorenne()
    nascita = f"{persona.data_nascita:%d/%m/%Y}" if persona.data_nascita else ""
    nome_gruppo = (
        (gruppo.denominazione_sociale or f"AGESCI {gruppo.denominazione}") if gruppo else ""
    )
    elementi = [
        Paragraph("SCHEDA SANITARIA PERSONALE", TITOLO),
        Paragraph(
            (
                "Da compilare a cura dei genitori o tutori legali e consegnare ai capi unità."
                if minore
                else "Da compilare e firmare a cura dell'interessato/a e consegnare ai capi unità."
            ),
            SOTTOTITOLO,
        ),
        Paragraph("1. DATI ANAGRAFICI" + (" DEL/LA RAGAZZO/A" if minore else ""), SEZIONE),
        _due_colonne(
            [
                [Paragraph("Cognome", GRASSETTO), Paragraph(_linea(persona.cognome), TESTO)],
                [Paragraph("Nome", GRASSETTO), Paragraph(_linea(persona.nome), TESTO)],
                [
                    Paragraph("Luogo e data di nascita", GRASSETTO),
                    Paragraph(
                        _linea(" ".join(x for x in (persona.luogo_nascita, nascita) if x)), TESTO
                    ),
                ],
                [
                    Paragraph("Codice fiscale", GRASSETTO),
                    Paragraph(_linea(persona.codice_fiscale), TESTO),
                ],
                [
                    Paragraph("Gruppo scout e unità", GRASSETTO),
                    Paragraph(
                        _linea(", ".join(x for x in (nome_gruppo, _unita(persona)) if x)), TESTO
                    ),
                ],
            ]
        ),
        Paragraph("2. CONTATTI DI EMERGENZA", SEZIONE),
    ]
    contatti = []
    if minore:
        tutele = list(
            RelazioneTutela.objects.filter(minore=persona)
            .select_related("tutore")
            .order_by("-responsabilita_genitoriale", "pk")[:2]
        )
        for n in range(2):
            t = tutele[n].tutore if n < len(tutele) else None
            contatti += [
                [
                    Paragraph(f"Genitore {n + 1} (nome e cognome)", GRASSETTO),
                    Paragraph(_linea(f"{t.nome} {t.cognome}" if t else ""), TESTO),
                ],
                [
                    Paragraph("Cellulare · Fisso o lavoro", GRASSETTO),
                    Paragraph(
                        f"{_linea(t.cellulare if t else '')} · "
                        f"{_linea(t.telefono_fisso if t else '')}",
                        TESTO,
                    ),
                ],
            ]
    nome_rep, tel_rep = recapito or (
        (info.reperibilita_nome, info.reperibilita_telefono) if info else ("", "")
    )
    contatti += [
        [
            Paragraph(
                "Contatto di fiducia" + (" per questo evento" if recapito else ""), GRASSETTO
            ),
            Paragraph(f"{_linea(nome_rep)} · tel. {_linea(tel_rep)}", TESTO),
        ],
        [
            Paragraph("Medico di medicina generale / pediatra", GRASSETTO),
            Paragraph(
                f"{_linea(info.medico_curante if info else '')} · tel. "
                f"{_linea(info.medico_telefono if info else '')}",
                TESTO,
            ),
        ],
    ]
    elementi.append(_due_colonne(contatti))

    elementi.append(Paragraph("3. STATO DI SALUTE E ANAMNESI", SEZIONE))
    for n, (campo, domanda) in enumerate(ANAMNESI, start=1):
        valore = getattr(info, campo) if info else None
        dettaglio = getattr(info, f"{campo}_dettaglio") if info else ""
        elementi += [
            Paragraph(f"{n}. {escape(domanda)}", GRASSETTO),
            Paragraph(_no_si(valore, dettaglio), TESTO),
        ]

    elementi.append(Paragraph("4. ALLERGIE, INTOLLERANZE E REGIMI ALIMENTARI", SEZIONE))
    righe = [
        [
            Paragraph("TIPO DI ALLERGIA / INTOLLERANZA", GRASSETTO),
            Paragraph("NO", GRASSETTO),
            Paragraph("SÌ", GRASSETTO),
            Paragraph("SOSTANZA, GRAVITÀ E REAZIONE", GRASSETTO),
        ]
    ]
    for tipo, nome in TIPI:
        valore = getattr(info, CAMPO_DEL_TIPO[tipo]) if info else None
        voci = [a for a in info.allergie.all() if a.tipo == tipo] if info else []
        if info and info.nessuna_allergia and valore is None:
            valore = False
        dettaglio = "; ".join(
            f"{a.sostanza} ({GRAVITA.get(a.gravita, a.gravita)})"
            + (f": {a.reazione}" if a.reazione else "")
            + (f". Cosa fare: {a.cosa_fare}" if a.cosa_fare else "")
            for a in voci
        )
        righe.append(
            [
                Paragraph(escape(nome), TESTO),
                Paragraph(NO if valore is False else VUOTO, TESTO),
                Paragraph(SI if valore or voci else VUOTO, TESTO),
                Paragraph(_e(dettaglio), TESTO),
            ]
        )
    elementi.append(
        _tabella(righe, [LARGHEZZA * 0.36, LARGHEZZA * 0.08, LARGHEZZA * 0.08, LARGHEZZA * 0.48])
    )
    elementi += [
        Spacer(1, 2 * mm),
        Paragraph(
            "In caso di allergia grave, è necessario l'uso di farmaci salvavita (es. adrenalina "
            "autoiniettabile)?",
            GRASSETTO,
        ),
        Paragraph(_no_si(info.farmaco_salvavita if info else None).split(" → ")[0], TESTO),
        Paragraph(
            "<i>Il farmaco deve essere consegnato direttamente ai capi prima della partenza, con "
            "precise istruzioni scritte.</i>",
            PICCOLO,
        ),
        Paragraph(
            "Segue regimi alimentari particolari per motivi etici, personali o religiosi?",
            GRASSETTO,
        ),
        Paragraph(
            _no_si(
                bool(info.esigenze_alimentari) if info else None,
                info.esigenze_alimentari if info else "",
            ),
            TESTO,
        ),
    ]

    elementi.append(Paragraph("5. TERAPIE FARMACOLOGICHE IN CORSO", SEZIONE))
    farmaci = list(info.farmaci.all()) if info else []
    prende = True if farmaci else (False if info and info.nessun_farmaco else None)
    elementi.append(
        Paragraph(
            "Deve assumere regolarmente farmaci durante le attività o il campo? "
            + _no_si(prende, "vedi tabella").split(" → ")[0],
            TESTO,
        )
    )
    if farmaci or prende is None:
        righe = [
            [
                Paragraph("NOME DEL FARMACO", GRASSETTO),
                Paragraph("DOSAGGIO / POSOLOGIA", GRASSETTO),
                Paragraph("ORARIO DI ASSUNZIONE", GRASSETTO),
                Paragraph("NOTE / CONSERVAZIONE", GRASSETTO),
            ]
        ]
        for f in farmaci:
            note = "; ".join(
                x for x in (f.note, "lo prende da solo" if f.autonomo else "glielo dà un capo") if x
            )
            righe.append(
                [
                    Paragraph(_e(f.nome), TESTO),
                    Paragraph(_e(f.posologia), TESTO),
                    Paragraph(_e(f.orari), TESTO),
                    Paragraph(_e(note), TESTO),
                ]
            )
        if not farmaci:
            righe += [[""] * 4, [""] * 4]
        elementi.append(_tabella(righe, [LARGHEZZA * 0.25] * 4))
    elementi.append(
        Paragraph(
            "<i>I farmaci vanno consegnati ai capi all'inizio dell'attività nella confezione "
            "originale, con il nome, e accompagnati da prescrizione medica.</i>",
            PICCOLO,
        )
    )

    elementi.append(Paragraph("6. COPERTURA VACCINALE ANTITETANICA", SEZIONE))
    data = info.antitetanica_data if info else None
    elementi.append(
        Paragraph(
            "L'ultima vaccinazione o richiamo contro il tetano è stata effettuata in data: "
            + (f"<b>{data:%d/%m/%Y}</b>" if data else "______________"),
            TESTO,
        )
    )

    elementi.append(Paragraph("7. ALTRE INFORMAZIONI", SEZIONE))
    elementi.append(
        _due_colonne(
            [
                [
                    Paragraph("Numero di tessera sanitaria", GRASSETTO),
                    Paragraph(_linea(info.tessera_sanitaria if info else ""), TESTO),
                ],
                [
                    Paragraph("Gruppo sanguigno", GRASSETTO),
                    Paragraph(_linea(info.gruppo_sanguigno if info else ""), TESTO),
                ],
                [
                    Paragraph("Altre vaccinazioni", GRASSETTO),
                    Paragraph(_linea(info.altre_vaccinazioni if info else ""), TESTO),
                ],
                [
                    Paragraph("Altre note sanitarie", GRASSETTO),
                    Paragraph(_linea(info.note_sanitarie if info else ""), TESTO),
                ],
            ]
        )
    )

    banco = info.farmaci_da_banco if info else None
    dichiarazione, consenso = testi()
    if minore:
        # One line for each parent with parental responsibility, at least one (DEC-51).
        quanti = RelazioneTutela.objects.filter(
            minore=persona, responsabilita_genitoriale=True
        ).count()
        firmatari = ["Firma leggibile del genitore / tutore"] * min(max(quanti, 1), 2)
    else:
        firmatari = ["Firma dell'interessato/a"]
    firme = Table(
        [["Luogo e data", firmatari[0]], ["", ""]]
        + ([["", firmatari[1]], ["", ""]] if len(firmatari) > 1 else []),
        colWidths=[LARGHEZZA * 0.45, LARGHEZZA * 0.55],
        rowHeights=[5 * mm, 9 * mm] * len(firmatari),
    )
    stile = [("FONTSIZE", (0, 0), (-1, -1), 9)]
    for n in range(1, 2 * len(firmatari), 2):
        stile.append(("LINEBELOW", (1, n), (1, n), 0.5, "black"))
    stile.append(("LINEBELOW", (0, 1), (0, 1), 0.5, "black"))
    firme.setStyle(TableStyle(stile))
    elementi.append(
        KeepTogether(
            [
                Paragraph("8. AUTORIZZAZIONI E CONSENSI (FIRME)", SEZIONE),
                Paragraph("Autorizzazione alla somministrazione di farmaci da banco:", GRASSETTO),
                Paragraph(
                    "In caso di piccoli malesseri (es. mal di testa, leggera febbre, dolore "
                    "addominale, punture di insetto), i capi unità sono autorizzati a somministrare "
                    "farmaci di primo soccorso (es. paracetamolo, ibuprofene, antistaminici "
                    "topici), previa consultazione telefonica ove possibile?",
                    TESTO,
                ),
                Paragraph(
                    f"{SI if banco else VUOTO} SÌ, autorizzo &nbsp;&nbsp; "
                    f"{NO if banco is False else VUOTO} NO, non autorizzo",
                    TESTO,
                ),
                Spacer(1, 2 * mm),
                Paragraph("Consenso al trattamento dei dati:", GRASSETTO),
                Paragraph(escape(dichiarazione), TESTO),
                Paragraph(escape(consenso), TESTO),
                Spacer(1, 3 * mm),
                firme,
                Spacer(1, 4 * mm),
                _allegati(minore),
            ]
        )
    )
    return elementi


def _allegati(minore: bool) -> Table:
    righe = [
        Paragraph("Documenti da allegare alla presente scheda:", GRASSETTO),
        Paragraph(
            "• Fotocopia della tessera sanitaria o del codice fiscale"
            + (" del/la ragazzo/a." if minore else "."),
            TESTO,
        ),
        Paragraph(
            "• Fotocopia del documento d'identità in corso di validità"
            + (" del/la ragazzo/a e del genitore firmatario." if minore else "."),
            TESTO,
        ),
    ]
    riquadro = Table([[righe]], colWidths=[LARGHEZZA])
    riquadro.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.6, "#e0a800"),
                ("BACKGROUND", (0, 0), (-1, -1), "#fff8e1"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return riquadro


def pdf(persone: list[Persona], evento=None) -> bytes:
    """One form per person; for an event, its emergency contacts (DEC-53)."""
    gruppo = Gruppo.objects.first()
    recapiti = {}
    if evento is not None:
        recapiti = {
            r.persona_id: (r.nome, r.telefono)
            for r in ReperibilitaEvento.objects.filter(evento=evento, persona__in=persone)
        }
    uscita = io.BytesIO()
    pie_di_pagina = decora_pagina(gruppo)
    documento = SimpleDocTemplate(
        uscita,
        pagesize=A4,
        title="Scheda sanitaria personale",
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=14 * mm,
        bottomMargin=18 * mm,
    )
    elementi = []
    for n, persona in enumerate(persone):
        if n:
            elementi.append(PageBreak())
        elementi += [intestazione(gruppo, LARGHEZZA), Spacer(1, 4 * mm)]
        elementi += _scheda(persona, recapiti.get(persona.pk), gruppo)
    documento.build(elementi, onFirstPage=pie_di_pagina, onLaterPages=pie_di_pagina)
    return uscita.getvalue()
