"""The texts of the AGESCI templates (DEC-336…DEC-340): the assembly's convocation and minutes,
the separate minutes of the budget, the Co.Ca.'s on Capi Gruppo, legal representative and seat.

The texts are fixed: changing a template is a new development (DEC-336). The app asks for the
data, shows the result and tells what is missing. `mancanti_*` give the list that stops the
sending or the definitive; `testo_*` give the HTML, the same one the PDF is made from. What
is typed goes through `_e`: it ends up in HTML shown with v-html and in reportlab's markup.
"""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from html import escape

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.anagrafica.models import Appartenenza, Persona, RuoloAppartenenza
from apps.core.anno import AnnoAssociativo
from apps.core.codice_fiscale import cerca_comuni
from apps.eventi.models import Evento
from apps.organizzazione.models import Gruppo, Incarico, RuoloIncarico, TipoUnita

from .models import Verbale

REGOLAMENTO = "REGOLAMENTO"
ELEZIONE = "ELEZIONE"
BILANCIO = "BILANCIO"
QUOTA = "QUOTA"
VARIE = "VARIE"
PUNTI = (REGOLAMENTO, ELEZIONE, BILANCIO, QUOTA, VARIE)
# What the assembly votes on.
DELIBERE = {
    REGOLAMENTO: "Regolamento",
    ELEZIONE: "elezione dell'organo",
    BILANCIO: "bilancio",
    QUOTA: "quota associativa",
}
VUOTO = "…"


def _e(valore) -> str:
    testo = str(valore or "").strip()
    return escape(testo) if testo else VUOTO


def _anno(fine: int | None) -> str:
    return f"{fine - 1}/{fine}" if fine else VUOTO


def _giorno(valore: date | None) -> str:
    return f"{valore:%d/%m/%Y}" if valore else VUOTO


def _giorno_riunione(evento: Evento) -> date:
    return timezone.localdate(evento.inizio)


def _nome(persona: Persona) -> str:
    return f"{persona.nome} {persona.cognome}"


def _gruppo() -> Gruppo | None:
    return Gruppo.objects.first()


def _intestatario(gruppo: Gruppo | None) -> str:
    """Written as in the templates: «AGESCI Gruppo X (codice fiscale Y)»."""
    if gruppo is None:
        return f"{VUOTO} (codice fiscale {VUOTO})"
    nome = gruppo.denominazione_sociale or f"AGESCI Gruppo {gruppo.denominazione}"
    return f"{_e(nome)} (codice fiscale {_e(gruppo.codice_fiscale)})"


def _mancanti_gruppo() -> list[str]:
    gruppo = _gruppo()
    return [] if gruppo and gruppo.codice_fiscale else ["codice fiscale del gruppo"]


def _elenco(punti: list[str], tag: str = "ol") -> str:
    voci = "".join(f"<li>{p}</li>" for p in punti)
    return f"<{tag}>{voci}</{tag}>"


def _indirizzo(dove: dict) -> str:
    """«Via Roma, n. 1, 83100 Avellino (AV)»."""
    return (
        f"{_e(dove.get('via'))}, n. {_e(dove.get('civico'))}, {_e(dove.get('cap'))} "
        f"{_e(dove.get('citta'))} ({_e(dove.get('provincia'))})"
    )


CAMPI_LUOGO = {
    "via": "via",
    "civico": "numero civico",
    "cap": "CAP",
    "citta": "città",
    "provincia": "provincia",
}


def _mancanti_luogo(dove: dict, prefisso: str) -> list[str]:
    return [
        f"{prefisso}: {n}" for c, n in CAMPI_LUOGO.items() if not str(dove.get(c) or "").strip()
    ]


# --- Convocation of the assembly (DEC-337) --------------------------------------------------


def _datetime(valore: str | None) -> datetime | None:
    if not valore:
        return None
    momento = parse_datetime(valore)
    if momento is not None and timezone.is_naive(momento):
        momento = timezone.make_aware(momento)
    return momento


def predefinita_convocazione(evento: Evento) -> dict:
    """What the form proposes: every point of the template, to be taken off when not needed
    (DEC-364), the last closed year for the budget, the year in course for election and fee,
    the place of the previous assembly held in the same place."""
    giorno = _giorno_riunione(evento)
    anno = AnnoAssociativo.da_data(giorno)
    luogo = {
        "presso": evento.luogo,
        "via": "",
        "civico": "",
        "cap": "",
        "citta": "",
        "provincia": "",
    }
    precedenti = (
        Verbale.objects.filter(evento__cerchia=evento.cerchia)
        .exclude(evento=evento)
        .exclude(dati={})
        .order_by("-evento__inizio")
    )
    for precedente in precedenti:
        stesso = precedente.dati.get("convocazione", {}).get("luogo", {})
        if stesso.get("presso") == evento.luogo and evento.luogo:
            luogo = stesso
            break
    return {
        "punti": list(PUNTI),
        "prima_il": None,
        "anno_bilancio": anno.precedente().anno_fine,
        "anno_elezione": anno.anno_fine,
        "luogo": luogo,
    }


def dati_convocazione(verbale: Verbale) -> dict:
    return {**predefinita_convocazione(verbale.evento), **verbale.dati.get("convocazione", {})}


def prima_convocazione(evento: Evento, dati: dict) -> datetime:
    """By default midnight of the day: it exists for the quorum, like a condominium's."""
    scelta = _datetime(dati.get("prima_il"))
    if scelta is not None:
        return timezone.localtime(scelta)
    return timezone.localtime(evento.inizio).replace(hour=0, minute=0, second=0, microsecond=0)


def punti_convocazione(dati: dict) -> list[str]:
    voci = {
        REGOLAMENTO: "approvazione del Regolamento dell'Assemblea di Gruppo;",
        ELEZIONE: (
            "elezione dell'organo esecutivo e di amministrazione del livello di Gruppo per "
            f"l'anno scout {_anno(dati.get('anno_elezione'))};"
        ),
        BILANCIO: (
            f"approvazione del bilancio d'esercizio {_anno(dati.get('anno_bilancio'))}, chiuso al "
            f"30/09/{dati.get('anno_bilancio') or VUOTO};"
        ),
        QUOTA: (
            "definizione in merito alla quota associativa di Gruppo per l'anno scout "
            f"{_anno(dati.get('anno_elezione'))};"
        ),
        VARIE: "varie ed eventuali.",
    }
    return _chiudi_elenco([voci[p] for p in PUNTI if p in dati.get("punti", [])])


def _chiudi_elenco(punti: list[str]) -> list[str]:
    if punti:
        punti[-1] = punti[-1].rstrip(";.") + "."
    return punti


def mancanti_convocazione(verbale: Verbale) -> list[str]:
    dati = dati_convocazione(verbale)
    evento = verbale.evento
    mancanti = _mancanti_gruppo()
    if not dati.get("punti"):
        mancanti.append("almeno un punto dell'ordine del giorno")
    if not dati.get("anno_bilancio") and BILANCIO in dati.get("punti", []):
        mancanti.append("anno del bilancio")
    if not dati.get("anno_elezione") and {ELEZIONE, QUOTA} & set(dati.get("punti", [])):
        mancanti.append("anno di elezione e quota")
    luogo = dati.get("luogo", {})
    if not str(luogo.get("presso") or "").strip():
        mancanti.append("luogo: presso")
    mancanti += _mancanti_luogo(luogo, "luogo")
    if prima_convocazione(evento, dati) >= evento.inizio:
        mancanti.append("la prima convocazione deve essere prima dell'orario della riunione")
    return mancanti


def testo_convocazione(verbale: Verbale, inviata_il: date | None = None) -> str:
    dati = dati_convocazione(verbale)
    evento = verbale.evento
    prima = prima_convocazione(evento, dati)
    seconda = timezone.localtime(evento.inizio)
    luogo = dati.get("luogo", {})
    stesso = prima.date() == seconda.date()
    quando_seconda = "lo stesso giorno" if stesso else f"il giorno {_giorno(seconda.date())}"
    return "".join(
        [
            '<p style="text-align: right">Agli associati del Gruppo</p>',
            f"<p>Data {_giorno(inviata_il or timezone.localdate())}</p>",
            "<p><strong>Oggetto: Convocazione Assemblea di Gruppo</strong></p>",
            f"<p>Con la presente si comunica che l'Assemblea ordinaria dei soci di "
            f"{_intestatario(_gruppo())} è convocata presso {_e(luogo.get('presso'))} sita a "
            f"{_e(luogo.get('citta'))} in {_indirizzo(luogo)} in prima convocazione, il giorno "
            f"{_giorno(prima.date())} alle ore {prima:%H:%M} e, occorrendo, in seconda "
            f"convocazione {quando_seconda} presso il medesimo luogo alle ore {seconda:%H:%M}, "
            "per discutere e deliberare, ai sensi dello Statuto, sul seguente ordine del "
            "giorno:</p>",
            _elenco(punti_convocazione(dati)),
            '<p style="text-align: right">I Capi Gruppo</p>',
        ]
    )


# --- Minutes of the assembly (DEC-338) ------------------------------------------------------


def dati_verbale(verbale: Verbale) -> dict:
    predefiniti = {
        "ora_apertura": "",
        "ora_chiusura": "",
        "scrutatori": [],
        "voti": {},
        "risultato": "",
        "quota_gruppo": "",
        "quota_totale": "",
        "quota_modalita": "",
        "varie": "",
        "bilancio_separato": False,
    }
    return {**predefiniti, **verbale.dati.get("assemblea", {})}


def _numero_presenti(verbale: Verbale) -> int:
    """From the attendance; after two years only the copy is left (DEC-328)."""
    from .servizi import presenti_segnati

    return presenti_segnati(verbale.evento).count() or len(verbale.presenti)


def _voti_validi(voti: dict | None) -> bool:
    if not voti:
        return False
    return bool(voti.get("unanimita")) or (
        voti.get("favorevoli") is not None and voti.get("contrari") is not None
    )


def _esito(voti: dict | None, presenti: int) -> str:
    """Only for and against, or unanimity without numbers (DEC-338)."""
    voti = voti or {}
    if voti.get("unanimita"):
        return f"all'unanimità dei {presenti} presenti"
    return (
        f"con {_e(voti.get('favorevoli'))} voti favorevoli e {_e(voti.get('contrari'))} "
        f"contrari, su {presenti} presenti"
    )


def _importo(valore) -> str:
    try:
        return f"{Decimal(str(valore)):.2f}".replace(".", ",")
    except InvalidOperation:
        return VUOTO


def _persone(ids: list[int]) -> list[Persona]:
    return list(Persona.objects.filter(pk__in=ids or []).order_by("cognome", "nome"))


def _elenco_nomi(nomi: list[str]) -> str:
    return ", ".join(escape(n) for n in nomi) or VUOTO


def _cariche(verbale: Verbale) -> tuple[str, list[str]]:
    if verbale.cariche:
        return (
            verbale.cariche.get("presidente", {}).get("nome", ""),
            [s["nome"] for s in verbale.cariche.get("segretari", [])],
        )
    presidente = _nome(verbale.presidente) if verbale.presidente else ""
    segretari = (
        [_nome(s) for s in verbale.segretari.order_by("cognome", "nome")] if verbale.pk else []
    )
    return presidente, segretari


def _apertura(evento_luogo: dict, ora: str) -> str:
    dove = f"{_e(evento_luogo.get('presso'))}, {_indirizzo(evento_luogo)}"
    return f"In data odierna alle ore {_e(ora)} presso {dove}"


def _presidenza(verbale: Verbale) -> str:
    presidente, segretari = _cariche(verbale)
    chi = "Segretario" if len(segretari) <= 1 else "Segretari"
    verbi = "che, ringraziando accetta" if len(segretari) <= 1 else "che, ringraziando accettano"
    return (
        "<p>Assume la Presidenza, ai sensi dell'art. 6 del Regolamento dell'Assemblea di "
        f"Gruppo, {_e(presidente)} che, constatata e fatta constatare la regolarità della "
        "convocazione come da Regolamento e la presenza del quorum costitutivo, ai sensi "
        "dell'art. 4, dichiara l'Assemblea validamente costituita e atta ad assumere la "
        f"delibera di cui sopra, chiamando a fungere da {chi} {_elenco_nomi(segretari)}, "
        f"{verbi}.</p>"
    )


def _scrutatori(dati: dict, separato: bool = False) -> str:
    nomi = [_nome(p) for p in _persone(dati.get("scrutatori", []))]
    if len(nomi) == 1 and not separato:
        return f"<p>La Presidenza procede quindi con la nomina dello scrutatore nella persona di {_elenco_nomi(nomi)}.</p>"
    if separato:
        return f"<p>La Presidenza procede quindi con la nomina degli scrutatori in persona di {_elenco_nomi(nomi)}.</p>"
    return f"<p>La Presidenza procede quindi con la nomina degli scrutatori nelle persone di {_elenco_nomi(nomi)}.</p>"


def membri_coca(giorno: date) -> list[str]:
    """Every capo and assistente ecclesiastico of the Co.Ca., for the election (DEC-338)."""
    capi = Appartenenza.objects.attive(giorno).filter(
        ruolo=RuoloAppartenenza.CAPO, unita__tipo=TipoUnita.COMUNITA_CAPI
    )
    assistenti = Incarico.objects.attivi(giorno).filter(
        ruolo__in={RuoloIncarico.AE_GRUPPO, RuoloIncarico.AE_UNITA}
    )
    persone = Persona.objects.filter(pk__in=capi.values("persona_id")) | Persona.objects.filter(
        pk__in=assistenti.values("persona_id")
    )
    return [_nome(p) for p in persone.distinct().order_by("cognome", "nome")]


def mancanti_verbale(verbale: Verbale) -> list[str]:
    conv = dati_convocazione(verbale)
    dati = dati_verbale(verbale)
    punti = conv.get("punti", [])
    mancanti = _mancanti_gruppo()
    if not punti:
        mancanti.append("ordine del giorno (nella convocazione)")
    mancanti += _mancanti_luogo(conv.get("luogo", {}), "luogo")
    for campo, nome in (("ora_apertura", "ora di apertura"), ("ora_chiusura", "ora di chiusura")):
        if not dati.get(campo):
            mancanti.append(nome)
    if not dati.get("scrutatori"):
        mancanti.append("almeno uno scrutatore")
    voti = dati.get("voti", {})
    mancanti += [
        f"voti: {nome}"
        for punto, nome in DELIBERE.items()
        if punto in punti and not _voti_validi(voti.get(punto))
    ]
    if BILANCIO in punti and dati.get("risultato") in ("", None):
        mancanti.append("risultato di bilancio")
    if QUOTA in punti:
        for campo, nome in (
            ("quota_gruppo", "quota di gruppo"),
            ("quota_totale", "totale delle quote"),
            ("quota_modalita", "modalità e termini delle quote"),
        ):
            if dati.get(campo) in ("", None):
                mancanti.append(nome)
    return mancanti


def _luogo_e_data(evento: Evento, citta) -> str:
    return f"<p>Lì {_e(citta)}, {_giorno(_giorno_riunione(evento))}</p>"


def _testo_bilancio(anno: int | None, dati: dict, presenti: int, intro_nota: bool) -> list[str]:
    nota = (
        "costituito, ai sensi dello Statuto, dal solo rendiconto per cassa e redatto in "
        "conformità alle norme di legge. Attraverso anche la relativa nota, vengono pertanto"
        if intro_nota
        else "costituito dal solo rendiconto per cassa (ai sensi dello Statuto) e redatto in "
        "conformità alle norme di legge. Vengono pertanto"
    )
    return [
        "<p>La Presidenza dà la parola ai Capi Gruppo e agli altri membri della Comunità capi "
        "che procedono quindi alla presentazione del bilancio d'esercizio di Gruppo dell'anno "
        f"scout {_anno(anno)}, {nota} indicate le entrate e le uscite intervenute nel corso "
        "dell'esercizio, commentando le variazioni intervenute per le diverse sezioni rispetto "
        "all'esercizio precedente, e indicando che il risultato della gestione ammonta a euro "
        f"{_importo(dati.get('risultato'))}, e viene proposto che tale ammontare venga "
        "assorbito dal patrimonio netto contabile del Gruppo.</p>",
        "<p>Dopo ampia e dettagliata analisi l'Assemblea di Gruppo approva, ai sensi dell'art. "
        f"14 del Regolamento, {_esito(dati.get('voti', {}).get(BILANCIO), presenti)}, il "
        f"bilancio d'esercizio dell'anno scout {_anno(anno)}, chiuso al 30/09/{anno or VUOTO}, "
        "e la proposta di destinazione del risultato della gestione che emerge dal rendiconto "
        "stesso.</p>",
    ]


def testo_assemblea(verbale: Verbale) -> str:
    conv = dati_convocazione(verbale)
    dati = dati_verbale(verbale)
    evento = verbale.evento
    punti = conv.get("punti", [])
    luogo = conv.get("luogo", {})
    presenti = _numero_presenti(verbale)
    voti = dati.get("voti", {})
    elezione = conv.get("anno_elezione")
    voci_odg = {
        REGOLAMENTO: "approvazione del Regolamento dell'Assemblea di Gruppo;",
        ELEZIONE: (
            "elezione dell'organo esecutivo e di amministrazione del Gruppo per l'anno scout "
            f"{_anno(elezione)};"
        ),
        BILANCIO: (
            "approvazione del bilancio d'esercizio chiuso al "
            f"30/09/{conv.get('anno_bilancio') or VUOTO};"
        ),
        QUOTA: (
            "definizione in merito alla quota associativa di Gruppo per l'anno scout "
            f"{_anno(elezione)};"
        ),
        VARIE: "varie ed eventuali.",
    }
    parti = [
        f"<p>{_apertura(luogo, dati.get('ora_apertura'))} si è riunita in sessione ordinaria, ai "
        f"sensi dello Statuto, l'Assemblea di {_intestatario(_gruppo())}, per deliberare sul "
        "seguente ordine del giorno:</p>",
        _elenco(_chiudi_elenco([voci_odg[p] for p in PUNTI if p in punti])),
        _presidenza(verbale),
        _scrutatori(dati),
    ]
    if REGOLAMENTO in punti:
        parti.append(
            "<p>La Presidenza dà quindi la parola ai Capi Gruppo e agli altri membri della "
            "Comunità capi che presentano la proposta di Regolamento dell'Assemblea di Gruppo "
            "nel testo giunto con la convocazione che viene approvata ai sensi dell'art. 14 del "
            f"Regolamento, {_esito(voti.get(REGOLAMENTO), presenti)}.</p>"
        )
    if ELEZIONE in punti:
        membri = _elenco_nomi(membri_coca(_giorno_riunione(evento)))
        parti.append(
            "<p>La Presidenza dà quindi la parola ai Capi Gruppo che presentano la Comunità capi "
            "nel suo insieme (ovvero la totalità dei capi e degli assistenti ecclesiastici "
            "censiti nel Gruppo) la quale eserciterà le funzioni di organo esecutivo e di "
            "amministrazione del Gruppo. Si procede pertanto all'elezione dei membri di tale "
            "organo. Risulta pertanto eletta la Comunità capi nel suo insieme, avendo ottenuto "
            "un numero di voti corrispondenti almeno alla metà più uno dei presenti aventi "
            f"diritto al voto, {_esito(voti.get(ELEZIONE), presenti)}, composta da: {membri}.</p>"
        )
    if BILANCIO in punti:
        parti += _testo_bilancio(conv.get("anno_bilancio"), dati, presenti, intro_nota=True)
    if QUOTA in punti:
        decorrenza = f"01/10/{elezione - 1}" if elezione else VUOTO
        parti += [
            "<p>La Presidenza dà quindi la parola ai Capi Gruppo e agli altri membri della "
            "Comunità capi che presentano la proposta di quota associativa integrativa di Gruppo "
            f"per l'anno scout {_anno(elezione)}, pari a euro "
            f"{_importo(dati.get('quota_gruppo'))}. Viene specificato che tale quota non "
            "costituisce entrata commerciale e non ha rilevanza reddituale, ai sensi dell'art. "
            "148 del TUIR.</p>",
            "<p>Dopo ampia e dettagliata analisi l'Assemblea di Gruppo delibera, "
            f"{_esito(voti.get(QUOTA), presenti)}, per l'anno scout decorrente dal {decorrenza} "
            f"di fissare la quota associativa di Gruppo pari a euro "
            f"{_importo(dati.get('quota_gruppo'))}.</p>",
            "<p>A seguire l'Assemblea delibera che tale quota, unitamente alla quota associativa "
            "nazionale, a quella regionale (ove presente) e a quella di Zona (ove presente), per "
            f"un totale pari a euro {_importo(dati.get('quota_totale'))}, dovrà essere "
            f"corrisposta da ciascun socio del Gruppo {_e(dati.get('quota_modalita'))}. Si "
            "informa altresì l'Assemblea che l'entità della quota associativa di Gruppo verrà "
            "portata a conoscenza del Comitato di Zona.</p>",
        ]
    varie = str(dati.get("varie") or "").strip()
    ora_fine = _e(dati.get("ora_chiusura"))
    if varie and VARIE in punti:
        parti.append(f"<p>Varie ed eventuali: {escape(varie)}</p>")
        parti.append(
            "<p>Null'altro essendovi da deliberare e nessuno chiedendo ulteriormente la parola, "
            f"l'Assemblea di Gruppo viene chiusa alle ore {ora_fine}.</p>"
        )
    else:
        parti.append(
            "<p>Non risultando varie ed eventuali da trattare e null'altro essendovi da "
            "deliberare e nessuno chiedendo ulteriormente la parola, l'Assemblea di Gruppo viene "
            f"chiusa alle ore {ora_fine}.</p>"
        )
    parti.append(_luogo_e_data(evento, luogo.get("citta")))
    return "".join(parti)


# --- Separate minutes of the budget (DEC-339) -----------------------------------------------


def mancanti_bilancio(verbale: Verbale) -> list[str]:
    conv = dati_convocazione(verbale)
    dati = dati_verbale(verbale)
    mancanti = _mancanti_gruppo()
    if BILANCIO not in conv.get("punti", []):
        mancanti.append("il bilancio deve essere nell'ordine del giorno")
    mancanti += _mancanti_luogo(conv.get("luogo", {}), "luogo")
    if not conv.get("anno_bilancio"):
        mancanti.append("anno del bilancio")
    for campo, nome in (("ora_apertura", "ora di apertura"), ("ora_chiusura", "ora di chiusura")):
        if not dati.get(campo):
            mancanti.append(nome)
    if not dati.get("scrutatori"):
        mancanti.append("almeno uno scrutatore")
    if not _voti_validi(dati.get("voti", {}).get(BILANCIO)):
        mancanti.append("voti: bilancio")
    if dati.get("risultato") in ("", None):
        mancanti.append("risultato di bilancio")
    presidente, segretari = _cariche(verbale)
    if not presidente or not segretari:
        mancanti.append("presidente e segretario dell'assemblea")
    if not capigruppo_in_carica(_giorno_riunione(verbale.evento)):
        mancanti.append("i capigruppo in carica")
    return mancanti


def testo_bilancio(verbale: Verbale) -> str:
    conv = dati_convocazione(verbale)
    dati = dati_verbale(verbale)
    anno = conv.get("anno_bilancio")
    luogo = conv.get("luogo", {})
    parti = [
        f"<p>{_apertura(luogo, dati.get('ora_apertura'))} si è riunita in sessione ordinaria, ai "
        f"sensi dello Statuto, l'Assemblea di {_intestatario(_gruppo())}, per deliberare "
        f"sull'approvazione del bilancio d'esercizio dell'anno scout {_anno(anno)}, chiuso al "
        f"30/09/{anno or VUOTO}.</p>",
        _presidenza(verbale),
        _scrutatori(dati, separato=True),
        *_testo_bilancio(anno, dati, _numero_presenti(verbale), intro_nota=False),
        "<p>Null'altro essendovi da deliberare e nessuno chiedendo ulteriormente la parola, "
        f"l'Assemblea di Gruppo viene chiusa alle ore {_e(dati.get('ora_chiusura'))}.</p>",
        _luogo_e_data(verbale.evento, luogo.get("citta")),
    ]
    return "".join(parti)


def _capo_gruppo(persona: Persona) -> str:
    articolo = "La Capo Gruppo" if persona.sesso == "F" else "Il Capo Gruppo"
    return f"{articolo}: {_nome(persona)}"


def capigruppo_in_carica(giorno: date) -> list[Persona]:
    incarichi = Incarico.objects.attivi(giorno).filter(ruolo=RuoloIncarico.CAPOGRUPPO)
    return list(
        Persona.objects.filter(pk__in=incarichi.values("persona_id")).order_by("cognome", "nome")
    )


def firme_bilancio(verbale: Verbale) -> list[dict]:
    presidente, segretari = _cariche(verbale)
    return [
        {
            "intro": "",
            "righe": [f"Il Presidente: {presidente}", *(f"Il Segretario: {s}" for s in segretari)],
        },
        {
            "intro": (
                "Per dichiarazione di conformità del bilancio d'esercizio, costituito dal solo "
                "rendiconto per cassa."
            ),
            "righe": [
                _capo_gruppo(p) for p in capigruppo_in_carica(_giorno_riunione(verbale.evento))
            ],
        },
    ]


# --- Minutes of the Co.Ca. on Capi Gruppo, representative, seat (DEC-339) -------------------


def predefinita_capi_gruppo(evento: Evento) -> dict:
    return {
        "ora_apertura": "",
        "ora_chiusura": "",
        "luogo": {
            "presso": evento.luogo,
            "via": "",
            "civico": "",
            "cap": "",
            "citta": "",
            "provincia": "",
        },
        "capi_gruppo": [],
        "cambia_capi_gruppo": False,
        "rappresentante": None,
        "cambia_rappresentante": False,
        "sede": {"via": "", "civico": "", "cap": "", "citta": "", "provincia": ""},
        "cambia_sede": False,
        "varie": "",
    }


def dati_capi_gruppo(evento: Evento, salvati: dict) -> dict:
    return {**predefinita_capi_gruppo(evento), **salvati}


def _nascita(persona: Persona) -> str:
    """The card has the municipality alone: the province comes from the ISTAT list when the
    name leaves no doubt (born abroad: none)."""
    luogo = (persona.luogo_nascita or "").strip()
    if not luogo or luogo.endswith(")"):
        return escape(luogo)
    trovati = cerca_comuni(luogo)
    return escape(f"{luogo} ({trovati[0]['provincia']})" if len(trovati) == 1 else luogo)


def _residenza(persona: Persona) -> str:
    return (
        f"{escape(persona.indirizzo)}, n.{escape(persona.civico)}, {escape(persona.cap)} "
        f"{escape(persona.comune)} ({escape(persona.provincia)})"
    )


def _generalita(persona: Persona) -> str:
    """Name, codice fiscale, birth and residence, from the person's card."""
    nato = "nata" if persona.sesso == "F" else "nato"
    return (
        f"{escape(persona.cognome)} {escape(persona.nome)} (codice fiscale "
        f"{escape(persona.codice_fiscale or '')}), {nato} a {_nascita(persona)} il "
        f"{_giorno(persona.data_nascita)} e residente in {_residenza(persona)}"
    )


def _titolo_sig(persona: Persona) -> str:
    return "Sig.ra" if persona.sesso == "F" else "Sig."


def _mancanti_persona(persona: Persona) -> list[str]:
    campi = {
        "sesso": persona.sesso,
        "codice fiscale": persona.codice_fiscale,
        "data di nascita": persona.data_nascita,
        "luogo di nascita": persona.luogo_nascita,
        "indirizzo": persona.indirizzo,
        "numero civico": persona.civico,
        "CAP": persona.cap,
        "comune": persona.comune,
        "provincia": persona.provincia,
    }
    assenti = [nome for nome, valore in campi.items() if not valore]
    return [f"{_nome(persona)}: {nome}" for nome in assenti]


def _persone_capi_gruppo(evento: Evento, dati: dict) -> list[Persona]:
    if dati.get("cambia_capi_gruppo"):
        return _persone(dati.get("capi_gruppo", []))
    return capigruppo_in_carica(_giorno_riunione(evento))


def _rappresentante(dati: dict) -> Persona | None:
    if not dati.get("rappresentante"):
        return None
    return Persona.objects.filter(pk=dati["rappresentante"]).first()


def mancanti_capi_gruppo(evento: Evento, dati: dict) -> list[str]:
    mancanti = _mancanti_gruppo()
    if not (
        dati.get("cambia_capi_gruppo")
        or dati.get("cambia_rappresentante")
        or dati.get("cambia_sede")
    ):
        mancanti.append("almeno una parte tra Capi Gruppo, rappresentante legale e sede")
    for campo, nome in (("ora_apertura", "ora di apertura"), ("ora_chiusura", "ora di chiusura")):
        if not dati.get(campo):
            mancanti.append(nome)
    luogo = dati.get("luogo", {})
    if not str(luogo.get("presso") or "").strip():
        mancanti.append("luogo: presso")
    mancanti += _mancanti_luogo(luogo, "luogo")
    capi_gruppo = _persone_capi_gruppo(evento, dati)
    if dati.get("cambia_capi_gruppo"):
        if not capi_gruppo:
            mancanti.append("i Capi Gruppo da esprimere")
        for persona in capi_gruppo:
            mancanti += _mancanti_persona(persona)
    if dati.get("cambia_rappresentante"):
        rappresentante = _rappresentante(dati)
        if rappresentante is None:
            mancanti.append("il rappresentante legale")
        else:
            if rappresentante.pk not in {p.pk for p in capi_gruppo}:
                mancanti.append("il rappresentante legale va scelto tra i Capi Gruppo")
            if not dati.get("cambia_capi_gruppo"):
                mancanti += _mancanti_persona(rappresentante)
    if dati.get("cambia_sede"):
        mancanti += _mancanti_luogo(dati.get("sede", {}), "nuova sede")
    return mancanti


def testo_capi_gruppo(evento: Evento, dati: dict) -> str:
    gruppo = _intestatario(_gruppo())
    odg = []
    if dati.get("cambia_capi_gruppo"):
        odg.append("espressione dei Capi Gruppo;")
    if dati.get("cambia_rappresentante"):
        odg.append("variazione rappresentante legale delegato agli adempimenti fiscali;")
    if dati.get("cambia_sede"):
        odg.append("variazione sede legale;")
    odg.append("varie ed eventuali.")
    luogo = dati.get("luogo", {})
    parti = [
        f"<p>{_apertura(luogo, dati.get('ora_apertura'))} si è riunita, ai sensi dell'art. 30 "
        f"dello Statuto, la Comunità capi di {gruppo}, per deliberare sul seguente ordine del "
        "giorno:</p>",
        _elenco(odg),
    ]
    inoltre = ""
    if dati.get("cambia_capi_gruppo"):
        voci = [
            f"{_titolo_sig(p)} {_generalita(p)};" for p in _persone(dati.get("capi_gruppo", []))
        ]
        parti += [
            f"<p>La Comunità capi di {gruppo} esprime nei ruoli di Capi Gruppo, ai sensi degli "
            "artt. 26 e 30 dello Statuto:</p>",
            _elenco(_chiudi_elenco(voci)),
        ]
        inoltre = "inoltre "
    if dati.get("cambia_rappresentante"):
        rappresentante = _rappresentante(dati)
        if rappresentante is not None:
            articolo = "la" if rappresentante.sesso == "F" else "il"
            chi = f"{articolo} {_titolo_sig(rappresentante)} {_generalita(rappresentante)}"
        else:
            chi = VUOTO
        parti.append(
            f"<p>La Comunità capi di {gruppo} {inoltre}nomina, tra i Capi Gruppo, {chi}, ai sensi "
            f"dell'art. 26 dello Statuto, Rappresentante legale delegato agli adempimenti fiscali "
            f"di {gruppo} in parola con decorrenza immediata.</p>"
        )
        inoltre = "inoltre "
    if dati.get("cambia_sede"):
        parti.append(
            f"<p>La Comunità capi di {gruppo} {inoltre}delibera che la nuova sede legale di "
            f"{gruppo} sarà in {_indirizzo(dati.get('sede', {}))}.</p>"
        )
    varie = str(dati.get("varie") or "").strip()
    parti += [
        f"<p>Varie ed eventuali: {escape(varie)}</p>" if varie else "<p>Varie ed eventuali.</p>",
        "<p>Null'altro essendovi da deliberare e nessuno chiedendo ulteriormente la parola, la "
        f"riunione della Comunità capi viene chiusa alle ore {_e(dati.get('ora_chiusura'))}.</p>",
        _luogo_e_data(evento, luogo.get("citta")),
    ]
    return "".join(parti)


def firme_capi_gruppo(evento: Evento, dati: dict) -> list[dict]:
    from .servizi import presenti_segnati

    return [
        {
            "intro": "Firme dei presenti",
            "righe": [_nome(p) for p in presenti_segnati(evento)],
        },
        {"intro": "", "righe": [_capo_gruppo(p) for p in _persone_capi_gruppo(evento, dati)]},
    ]
