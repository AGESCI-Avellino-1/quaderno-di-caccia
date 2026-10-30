"""The AGESCI form "Consenso al trattamento dei dati sanitari", minor or adult member,
filled in from the app (DEC-51): the signers of a minor come from the parents'
records, the emergency contact may be the one given for an event (DEC-53); below, the
optional fields with their own consent line and signatures (DEC-49, DEC-51, DEC-194).

Generated on request, never stored. The text of the declarations is the AGESCI one.
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

from apps.anagrafica.models import Persona, RelazioneTutela
from apps.core.stampa import decora_pagina, intestazione
from apps.organizzazione.models import Gruppo

from .models import Gravita, InformazioniSanitarie, ReperibilitaEvento

LARGHEZZA = A4[0] - 36 * mm
TESTO = ParagraphStyle("testo", fontName="Helvetica", fontSize=9.5, leading=12.5)
PICCOLO = ParagraphStyle("piccolo", parent=TESTO, fontSize=8, leading=10)
TITOLO = ParagraphStyle(
    "titolo", parent=TESTO, fontName="Helvetica-Bold", fontSize=12, leading=15, alignment=1
)
SOTTOTITOLO = ParagraphStyle("sottotitolo", parent=TESTO, fontSize=8.5, alignment=1)
CENTRO = ParagraphStyle("centro", parent=TESTO, fontName="Helvetica-Bold", alignment=1)

AUTORIZZA = (
    "il trattamento dei dati personali, ivi compresi i dati appartenenti alle categorie "
    "particolari censite all’art.9 del Regolamento Europeo 679/2016 (quali, ad esempio, i dati "
    "sanitari), di seguito riportati, ai sensi del Regolamento stesso e del decreto attuativo "
    "10/08/2018, n. 101, in accordo con l’informativa fornitami dalla rete associativa "
    "nazionale “Associazione Guide e Scouts Cattolici Italiani (AGESCI) APS”"
)
DICHIARA_MINORE = (
    "che i dati sanitari sottoindicati sono aggiornati alla data di sottoscrizione del presente "
    "documento, veritieri, completi e compatibili con le attività associative, di cui all’art. 2 "
    "dello Statuto dell’AGESCI. In caso di variazione dei dati sotto riportati gli stessi saranno "
    "prontamente aggiornati e trasmessi alla Comunità capi del Gruppo per il quale è stata "
    "richiesta l’ammissione in qualità di socio."
)
DICHIARA_ADULTO = (
    "che i dati sanitari sotto indicati sono aggiornati alla data di sottoscrizione del presente "
    "documento, veritieri, completi e compatibili con le attività associative, di cui all’art. 2 "
    "dello Statuto dell’AGESCI. In caso di variazione dei dati sotto riportati gli stessi saranno "
    "prontamente aggiornati e trasmessi alla Comunità capi del Gruppo per il quale ho richiesto "
    "l’ammissione in qualità di socio."
)
NOTA_MINORE = (
    "Compilare e firmare dagli esercenti la responsabilità genitoriale indicando tra parentesi il "
    "ruolo, anche in caso di separazione/divorzio (art. 155 C.C., modificato dalla legge "
    "08.02.2006, n. 54), indicando altresì eventuali regole che devono essere conosciute dai soci "
    "adulti in relazione al rapporto con il minore, da considerarsi valide fino a nuove "
    "indicazioni scritte."
)
# DEC-194: the consent line of the optional section.
CONSENSO_FACOLTATIVI = (
    "Acconsento/acconsentiamo al trattamento dei dati facoltativi sopra indicati, utili in caso "
    "di emergenza, alle stesse condizioni dell’informativa AGESCI."
)


def _e(valore) -> str:
    return escape(str(valore)) if valore not in (None, "") else "______________"


def _riga(etichetta: str, valore) -> Paragraph:
    return Paragraph(f"{etichetta} <b>{_e(valore)}</b>", TESTO)


def _sottoscrittore(p: Persona) -> list:
    nascita = f"{p.data_nascita:%d/%m/%Y}" if p.data_nascita else None
    return [
        _riga("Il/la sottoscritto/a", f"{p.cognome} {p.nome}"),
        Paragraph(
            f"sesso <b>{_e(p.sesso)}</b>, nato/a a <b>{_e(p.luogo_nascita)}</b> "
            f"il <b>{_e(nascita)}</b>",
            TESTO,
        ),
        _riga("codice fiscale", p.codice_fiscale),
        _riga("residente in", f"{p.indirizzo or '______'} n. {p.civico or '__'}"),
        _riga("a", f"{p.comune or '______'} CAP {p.cap or '_____'} ({p.provincia or '__'})"),
        _riga("e-mail", f"{p.email or '______'} · cell. {p.cellulare or '______'}"),
        Spacer(1, 2 * mm),
    ]


def _firme(ruoli: list[str]) -> Table:
    righe = [["", ""]]
    for ruolo in ruoli:
        righe.append(["", f"({ruolo})"])
        righe.append([Paragraph("<i>(firma)</i>", PICCOLO), Paragraph("<i>(ruolo)</i>", PICCOLO)])
    tabella = Table(righe, colWidths=[LARGHEZZA * 0.5, LARGHEZZA * 0.5], rowHeights=None)
    stile = [("TOPPADDING", (0, 0), (-1, -1), 6)]
    for n in range(1, len(righe), 2):
        stile.append(("LINEBELOW", (0, n), (0, n), 0.5, "black"))
        stile.append(("LINEBELOW", (1, n), (1, n), 0.5, "black"))
    tabella.setStyle(TableStyle(stile))
    return tabella


def _data_luogo() -> Paragraph:
    return Paragraph("Data ______________ &nbsp;&nbsp; Luogo ________________________", TESTO)


# Short words on paper; the app explains "grave" as a risk for life.
GRAVITA = {Gravita.LIEVE: "lieve", Gravita.MODERATA: "moderata", Gravita.GRAVE: "grave"}

# Helvetica has no ballot boxes: [X] and [  ] print everywhere.


def _gravita(g: str) -> str:
    return GRAVITA.get(g, g)


def _scheda(
    persona: Persona, info: InformazioniSanitarie | None, recapito: tuple[str, str] | None
) -> list:
    nascita = f"{persona.data_nascita:%d/%m/%Y}" if persona.data_nascita else None
    nome_rep, tel_rep = recapito or (
        (info.reperibilita_nome, info.reperibilita_telefono) if info else ("", "")
    )
    antitetanica = (
        "SI [X] &nbsp; NO [&nbsp;&nbsp;]"
        if info and info.antitetanica
        else (
            "SI [&nbsp;&nbsp;] &nbsp; NO [X]"
            if info and info.antitetanica is False
            else "SI [&nbsp;&nbsp;] &nbsp; NO [&nbsp;&nbsp;]"
        )
    )
    if info and info.allergie.exists():
        allergie = "; ".join(
            f"{a.get_tipo_display()}: {a.sostanza} (reazione {_gravita(a.gravita)})"
            + (f": {a.reazione}" if a.reazione else "")
            for a in info.allergie.all()
        )
    elif info and info.nessuna_allergia:
        allergie = "Nessuna allergia o intolleranza"
    else:
        allergie = ""
    if info and info.farmaci.exists():
        farmaci = "; ".join(
            f"{f.nome}, {f.posologia}"
            + (f", {f.orari}" if f.orari else "")
            + (", in autonomia" if f.autonomo else ", non in autonomia")
            for f in info.farmaci.all()
        )
    elif info and info.nessun_farmaco:
        farmaci = "Nessun farmaco"
    else:
        farmaci = ""
    elementi = [
        Paragraph("SCHEDA SANITARIA", TITOLO),
        Spacer(1, 2 * mm),
        _riga("Cognome", f"{persona.cognome} · Nome {persona.nome}"),
        _riga("nato/a", f"{persona.luogo_nascita or '______'} il {nascita or '__/__/____'}"),
        _riga(
            "Codice fiscale",
            f"{persona.codice_fiscale or '______'} · Nr. Tessera sanitaria "
            f"{(info.tessera_sanitaria if info else '') or '______'}",
        ),
        _riga(
            "Reperibilità per emergenze",
            f"{nome_rep or '______'} · {tel_rep or '______'}"
            + (" (per questo evento)" if recapito else ""),
        ),
        Paragraph(f"vaccinazione antitetanica &nbsp; {antitetanica}", TESTO),
        Spacer(1, 2 * mm),
        Paragraph(
            "Effettive allergie e/o intolleranze a cibi, medicinali o altro (indicare il grado "
            "di reazione):",
            TESTO,
        ),
        Paragraph(f"<b>{_e(allergie)}</b>", TESTO),
        Spacer(1, 2 * mm),
        Paragraph(
            "In caso di profilassi in corso, specificare nome del farmaco, la posologia, gli "
            "orari e l’indicazione dell’autonomia"
            + (" del bambino" if persona.e_minorenne() else "")
            + " nella somministrazione, allegando prescrizione medica:",
            TESTO,
        ),
        Paragraph(f"<b>{_e(farmaci)}</b>", TESTO),
        Spacer(1, 2 * mm),
        _riga("Ulteriori note sanitarie di rilievo:", info.note_sanitarie if info else ""),
        Spacer(1, 4 * mm),
    ]
    return elementi


def _facoltativi(info: InformazioniSanitarie | None, ruoli: list[str]) -> list:
    return [
        Spacer(1, 6 * mm),
        Paragraph("DATI FACOLTATIVI", CENTRO),
        _riga("Gruppo sanguigno", info.gruppo_sanguigno if info else ""),
        _riga("Medico curante", info.medico_curante if info else ""),
        _riga("Altre vaccinazioni", info.altre_vaccinazioni if info else ""),
        Spacer(1, 2 * mm),
        Paragraph(CONSENSO_FACOLTATIVI, TESTO),
        Spacer(1, 2 * mm),
        _data_luogo(),
        _firme(ruoli),
    ]


def _modulo(persona: Persona, recapito: tuple[str, str] | None) -> list:
    info = (
        InformazioniSanitarie.objects.filter(persona=persona)
        .prefetch_related("allergie", "farmaci")
        .first()
    )
    if not persona.e_minorenne():
        return [
            Paragraph("CONSENSO AL TRATTAMENTO DEI DATI SANITARI – SOCIO MAGGIORENNE", TITOLO),
            Paragraph(
                "(indispensabile per la partecipazione alle attività associative)", SOTTOTITOLO
            ),
            Spacer(1, 4 * mm),
            *_sottoscrittore(persona),
            Paragraph("AUTORIZZA", CENTRO),
            Paragraph(AUTORIZZA + " e", TESTO),
            Paragraph("DICHIARA", CENTRO),
            Paragraph(DICHIARA_ADULTO, TESTO),
            Spacer(1, 4 * mm),
            *_scheda(persona, info, recapito),
            _data_luogo(),
            Paragraph("In fede", TESTO),
            _firme(["interessato/a"]),
            *_facoltativi(info, ["interessato/a"]),
        ]
    tutele = list(
        RelazioneTutela.objects.filter(minore=persona, responsabilita_genitoriale=True)
        .select_related("tutore")
        .order_by("pk")[:2]
    )
    ruoli = [t.get_tipo_display().lower() for t in tutele] or ["genitore", "genitore"]
    entrambi = len(tutele) == 2
    elementi = [
        Paragraph("CONSENSO AL TRATTAMENTO DEI DATI SANITARI – SOCIO MINORENNE", TITOLO),
        Paragraph("(indispensabile per la partecipazione alle attività associative)", SOTTOTITOLO),
        Spacer(1, 3 * mm),
        Paragraph(
            "sottoscrivo/sottoscriviamo tale consenso in qualità di "
            "<i>(compilare i soli campi relativi all’opzione scelta)</i>:",
            TESTO,
        ),
        Paragraph(
            f"{'[X]' if entrambi else '[&nbsp;&nbsp;]'} <b>Esercenti la responsabilità genitoriale</b> "
            "(entrambi esercenti la responsabilità genitoriale)",
            TESTO,
        ),
    ]
    if entrambi:
        for t in tutele:
            elementi += _sottoscrittore(t.tutore)
    elementi.append(
        Paragraph(
            f"{'[X]' if len(tutele) == 1 else '[&nbsp;&nbsp;]'} <b>unico genitore o tutore</b> "
            "(esercente la responsabilità genitoriale)",
            TESTO,
        )
    )
    if len(tutele) == 1:
        elementi += _sottoscrittore(tutele[0].tutore)
    elementi += [
        Paragraph("AUTORIZZA/AUTORIZZANO", CENTRO),
        Paragraph(AUTORIZZA, TESTO),
        Paragraph("DICHIARA/DICHIARANO", CENTRO),
        Paragraph(DICHIARA_MINORE, TESTO),
        PageBreak(),
        *_scheda(persona, info, recapito),
        KeepTogether([_data_luogo(), Paragraph("In fede", TESTO), _firme(ruoli)]),
        Paragraph(f"<i>{NOTA_MINORE}</i>", PICCOLO),
        *_facoltativi(info, ruoli),
    ]
    return elementi


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
        title="Scheda dati sanitari",
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
        elementi += _modulo(persona, recapiti.get(persona.pk))
    documento.build(elementi, onFirstPage=pie_di_pagina, onLaterPages=pie_di_pagina)
    return uscita.getvalue()
