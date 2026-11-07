"""The admission criteria of an associative year (DEC-355...DEC-359): the template's text, which
versions count on a day, the PDF, and the maximum of members of a unit."""

import io
from dataclasses import dataclass
from datetime import date, timedelta
from xml.sax.saxutils import escape

from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from apps.anagrafica.models import Appartenenza, RuoloAppartenenza
from apps.core.anno import AnnoAssociativo
from apps.core.stampa import decora_pagina, intestazione
from apps.core.testo_pdf import (
    CELLA,
    LARGHEZZA,
    MARGINE,
    SOTTOTITOLO,
    TITOLO,
    flowable_del_testo,
)
from apps.organizzazione.models import Gruppo, Unita, ordine_unita

from .models import MassimoUnita, VersioneCriteri

# Where a new year starts from, when the group has no criteria yet (DEC-355). Written from the
# documents of the groups; to be checked against the Statuto and the Regolamento. Its numbers
# are not here: the maxima are data, printed in their own table (DEC-358).
MODELLO = """<h2>Requisiti di ammissione per i soci giovani</h2>
<p>Il socio giovane, al momento della richiesta di ammissione all'Associazione, e se minorenne tramite gli esercenti la responsabilità genitoriale, dichiara:</p>
<ul>
<li><p>di aver letto e di rispettare lo Statuto e il Regolamento, accettandoli in ogni loro punto;</p></li>
<li><p>di avere un'età compresa tra gli 8 anni, da compiersi entro l'anno associativo in corso, e i 20/21 anni;</p></li>
<li><p>di aver ricevuto, letto e sottoscritto l'informativa sul trattamento dei dati personali.</p></li>
</ul>
<p>È tenuto alla compilazione e alla firma della richiesta di adesione, della scheda sanitaria e del modulo per il consenso al trattamento dei dati personali, e al pagamento annuale della quota associativa.</p>
<h2>Requisiti di ammissione per i soci adulti</h2>
<p>Il socio adulto, al momento della richiesta di ammissione all'Associazione, dichiara:</p>
<ul>
<li><p>di condividere e riconoscersi nella Promessa, nella Legge e nel Patto associativo;</p></li>
<li><p>di aver letto e di rispettare lo Statuto e il Regolamento, accettandoli in ogni loro punto;</p></li>
<li><p>di aver compiuto almeno diciotto anni di età;</p></li>
<li><p>di non avere condanne definitive o sanzioni interdittive risultanti dal certificato del Casellario giudiziale richiesto per chi opera con i minori;</p></li>
<li><p>di non aver riportato condanne penali per reati che comportano l'interdizione dai pubblici uffici;</p></li>
<li><p>di non avere atteggiamenti o comportamenti lesivi della persona, della sua libertà o della sua dignità, o incompatibili con le finalità dell'Associazione;</p></li>
<li><p>di non essere iscritto a enti od organizzazioni con finalità in contrasto con quelle dell'Associazione;</p></li>
<li><p>di aver ricevuto, letto e sottoscritto l'informativa sul trattamento dei dati personali.</p></li>
</ul>
<p>È tenuto alla compilazione e alla firma della richiesta di adesione, della scheda sanitaria e del modulo per il consenso al trattamento dei dati personali, e al pagamento annuale della quota associativa.</p>
<h2>Criteri di ammissione del gruppo</h2>
<p>La Comunità capi, in base al numero di capi in servizio e alla qualità della proposta educativa, stabilisce per ogni unità il numero massimo di soci giovani indicato in fondo a questo documento.</p>
<p>Nessuna richiesta viene esclusa per disabilità, stato di salute o diagnosi. Quando una richiesta presenta bisogni particolari, la Comunità capi valuta caso per caso, con la famiglia, le risorse disponibili e gli adattamenti possibili, e ne motiva l'esito.</p>
<p>Si valuta anche la data di presentazione della richiesta, in relazione alla possibilità di strutturare un percorso educativo adeguato e in linea con il Progetto Educativo di Gruppo e i programmi di unità.</p>
<p>Se le richieste superano il numero massimo stabilito, viene data precedenza considerando:</p>
<ol>
<li><p>la possibilità di compiere l'intero ciclo educativo scout;</p></li>
<li><p>le relazioni della progressione personale;</p></li>
<li><p>l'equilibrio numerico per genere;</p></li>
</ol>
<p>e, solo successivamente, la data della richiesta di ammissione.</p>
<p>Il rigetto di una richiesta è motivato e comunicato all'interessato entro sessanta giorni dalla richiesta.</p>
"""

# The Statuto's term for answering a request, counted from the request (DEC-359).
GIORNI_PER_DECIDERE = 60
# How long before the term who decides gets the reminder.
PREAVVISO_DECISIONE = 10


def valida_fino_al(versione: VersioneCriteri) -> date:
    """The day before the next version of that year, or the end of the year (DEC-356)."""
    successiva = (
        VersioneCriteri.objects.filter(anno=versione.anno, valida_dal__gt=versione.valida_dal)
        .order_by("valida_dal")
        .first()
    )
    if successiva is not None:
        return successiva.valida_dal - timedelta(days=1)
    return AnnoAssociativo(versione.anno).fine


def in_vigore(giorno: date | None = None) -> VersioneCriteri | None:
    """The version of the year of that day which counts on it; None before there is one."""
    giorno = giorno or timezone.localdate()
    return (
        VersioneCriteri.objects.filter(
            anno=AnnoAssociativo.da_data(giorno).anno_fine, valida_dal__lte=giorno
        )
        .order_by("-valida_dal")
        .first()
    )


@dataclass
class Pubblicati:
    """What everybody sees (DEC-357): the versions of a year, those already begun."""

    anno: int | None
    # The last year's, shown only as an outline while the new one is missing.
    traccia: bool
    versioni: list[VersioneCriteri]


def pubblicati(giorno: date | None = None) -> Pubblicati:
    giorno = giorno or timezone.localdate()
    corrente = AnnoAssociativo.da_data(giorno).anno_fine
    iniziate = VersioneCriteri.objects.filter(valida_dal__lte=giorno)
    if iniziate.filter(anno=corrente).exists():
        anno, traccia = corrente, False
    else:
        ultima = iniziate.filter(anno__lt=corrente).order_by("-anno").first()
        if ultima is None:
            return Pubblicati(None, False, [])
        anno, traccia = ultima.anno, True
    return Pubblicati(anno, traccia, list(iniziate.filter(anno=anno).order_by("-valida_dal")))


def soci_giovani(unita: Unita, giorno: date | None = None) -> int:
    return (
        Appartenenza.objects.attive(giorno or timezone.localdate())
        .filter(unita=unita, ruolo=RuoloAppartenenza.RAGAZZO)
        .count()
    )


def massimo_di(unita: Unita, giorno: date | None = None) -> int | None:
    """None: no maximum, or no criteria for the year yet: nothing to warn about (DEC-358)."""
    versione = in_vigore(giorno)
    if versione is None:
        return None
    voce = MassimoUnita.objects.filter(versione=versione, unita=unita).first()
    return voce.massimo if voce else None


def posti(unita: Unita) -> str:
    """«30 su 45», "" without a maximum."""
    massimo = massimo_di(unita)
    return "" if massimo is None else f"{soci_giovani(unita)} su {massimo}"


def _periodo(versione: VersioneCriteri) -> str:
    return (
        f"Validi dal {versione.valida_dal:%d/%m/%Y} al {valida_fino_al(versione):%d/%m/%Y}. "
        f"Deliberati con il verbale della Comunità capi n. {versione.verbale_numero} "
        f"del {versione.verbale_data:%d/%m/%Y}."
    )


def pdf(versione: VersioneCriteri) -> bytes:
    """On the letterhead, never stored. No names of who signs: it is public (DEC-355)."""
    gruppo = Gruppo.objects.first()
    uscita = io.BytesIO()
    documento = SimpleDocTemplate(
        uscita,
        pagesize=A4,
        leftMargin=MARGINE,
        rightMargin=MARGINE,
        topMargin=14 * mm,
        bottomMargin=16 * mm,
        title="Criteri di ammissione",
    )
    elementi = [
        intestazione(gruppo, LARGHEZZA),
        Spacer(1, 4 * mm),
        Paragraph(
            escape(
                f"Criteri di ammissione: anno associativo "
                f"{AnnoAssociativo(versione.anno).etichetta}"
            ),
            TITOLO,
        ),
        Paragraph(escape(_periodo(versione)), SOTTOTITOLO),
        Spacer(1, 5 * mm),
        *flowable_del_testo(versione.testo),
    ]
    massimi = list(versione.massimi.select_related("unita").order_by(*ordine_unita("unita__")))
    if massimi:
        righe = [
            [Paragraph("<b>Unità</b>", CELLA), Paragraph("<b>Soci giovani al massimo</b>", CELLA)]
        ]
        righe += [
            [Paragraph(escape(str(m.unita)), CELLA), Paragraph(str(m.massimo), CELLA)]
            for m in massimi
        ]
        tabella = Table(righe, colWidths=[LARGHEZZA * 0.7, LARGHEZZA * 0.3], repeatRows=1)
        tabella.setStyle(
            TableStyle(
                [
                    ("LINEBELOW", (0, 0), (-1, -1), 0.25, "#cccccc"),
                    ("LINEBELOW", (0, 0), (-1, 0), 0.75, "#462d7b"),
                ]
            )
        )
        elementi += [Spacer(1, 4 * mm), tabella]
    pagina = decora_pagina(gruppo, MARGINE)
    documento.build(elementi, onFirstPage=pagina, onLaterPages=pagina)
    return uscita.getvalue()
