"""The scout path of a member (DEC-287): the periods in the app's units, from BuonaStrada
or the app, and those outside them (`PeriodoPercorso`: other groups, years rebuilt by
hand), one per line with unit and years, and the year of joining the group."""

from datetime import timedelta

from apps.core.anno import AnnoAssociativo
from apps.core.models import FonteDato

from .models import Appartenenza, PeriodoPercorso, Persona, RuoloAppartenenza


def _etichetta(anno: int) -> str:
    return AnnoAssociativo(anno).etichetta


def _unita_testo(tipo: str, codice: str) -> str:
    return f"{tipo} ({codice})" if codice else tipo


def _periodi_nelle_unita(persona: Persona) -> list[dict]:
    """The app's memberships, contiguous ones in the same unit joined in one line."""
    righe: list[dict] = []
    appartenenze = (
        Appartenenza.objects.filter(persona=persona)
        .select_related("unita")
        .order_by("unita_id", "data_inizio")
    )
    for a in appartenenze:
        ultima = righe[-1] if righe else None
        if (
            ultima is not None
            and ultima["unita_id"] == a.unita_id
            and ultima["data_fine"] is not None
            and a.data_inizio <= ultima["data_fine"]
        ):
            ultima["data_fine"] = (
                None if a.data_fine is None else max(a.data_fine, ultima["data_fine"])
            )
            ultima["ricostruito"] &= a.fonte == FonteDato.RICOSTRUITO
            continue
        righe.append(
            {
                "unita_id": a.unita_id,
                "unita": str(a.unita),
                "ruolo": a.ruolo,
                "data_inizio": a.data_inizio,
                "data_fine": a.data_fine,
                "ricostruito": a.fonte == FonteDato.RICOSTRUITO,
            }
        )
    risultato = []
    for r in righe:
        dal = AnnoAssociativo.da_data(r["data_inizio"]).anno_fine
        al = (
            AnnoAssociativo.da_data(r["data_fine"] - timedelta(days=1)).anno_fine
            if r["data_fine"]
            else None
        )
        risultato.append(
            {
                "id": None,
                "gruppo": "",
                "unita": r["unita"],
                "ruolo": r["ruolo"],
                "anno_inizio": dal,
                "anno_fine": al,
                "fonte": FonteDato.RICOSTRUITO if r["ricostruito"] else FonteDato.BUONASTRADA,
            }
        )
    return risultato


def percorso(persona: Persona) -> dict:
    from apps.impostazioni.models import Impostazioni

    nostro = Impostazioni.carica().nome_del_gruppo()
    periodi = _periodi_nelle_unita(persona) + [
        {
            "id": p.pk,
            "gruppo": p.gruppo,
            "unita": p.unita,
            "ruolo": p.ruolo,
            "anno_inizio": p.anno_inizio,
            "anno_fine": p.anno_fine,
            "fonte": p.fonte,
        }
        for p in PeriodoPercorso.objects.filter(persona=persona)
    ]
    periodi.sort(key=lambda p: (p["anno_inizio"], p["anno_fine"] or 9999))
    nel_gruppo = [p["anno_inizio"] for p in periodi if not p["gruppo"]]
    return {
        "anno_ingresso": _etichetta(min(nel_gruppo)) if nel_gruppo else "",
        "periodi": [
            {
                "id": p["id"],
                "gruppo": p["gruppo"] or nostro,
                "altro_gruppo": bool(p["gruppo"]),
                "unita": p["unita"],
                "ruolo": p["ruolo"],
                "ruolo_nome": RuoloAppartenenza(p["ruolo"]).label,
                "anni": (
                    _etichetta(p["anno_inizio"])
                    if p["anno_fine"] == p["anno_inizio"]
                    else f"{_etichetta(p['anno_inizio'])}–"
                    + (_etichetta(p["anno_fine"]) if p["anno_fine"] else "oggi")
                ),
                "ricostruito": p["fonte"] == FonteDato.RICOSTRUITO,
                # Only what was rebuilt by hand can be removed here.
                "rimovibile": p["id"] is not None and p["fonte"] == FonteDato.RICOSTRUITO,
            }
            for p in periodi
        ],
    }


def registra_altri_gruppi(persona: Persona, righe) -> list[str]:
    """The years of a member in other groups from the export (DEC-287), as text: one
    period per run of consecutive years in the same group and unit. Run again, a period
    already there grows instead of doubling. Returns what was added, for the summary."""
    from apps.importazione.servizi import STATI_ATTIVI

    righe = sorted((x for x in righe if x.stato in STATI_ATTIVI), key=lambda x: x.anno_scout)
    periodi: list[list] = []
    for riga in righe:
        chiave = (riga.gruppo.ordinale, riga.tipo_unita_testo, riga.codice_unita, riga.progressivo)
        ultimo = periodi[-1] if periodi else None
        if ultimo and ultimo[0] == chiave and riga.anno_scout == ultimo[-1].anno_scout + 1:
            ultimo.append(riga)
        else:
            periodi.append([chiave, riga])
    aggiunti = []
    for _chiave, *anni in periodi:
        prima = anni[0]
        gruppo = prima.gruppo.denominazione or prima.gruppo.ordinale
        gruppo = (
            f"AGESCI {gruppo.title()}"
            if gruppo and not gruppo.upper().startswith("AGESCI")
            else gruppo
        )
        tipo = prima.tipo_unita.label if prima.tipo_unita else prima.tipo_unita_testo.title()
        codice = f"{prima.codice_unita}{prima.progressivo or ''}"
        ruolo = (
            RuoloAppartenenza.CAPO
            if prima.tipo_unita_testo.upper().startswith("COMUNIT")
            else RuoloAppartenenza.RAGAZZO
        )
        periodo, creato = PeriodoPercorso.objects.get_or_create(
            persona=persona,
            gruppo=gruppo,
            unita=_unita_testo(tipo, codice),
            anno_inizio=prima.anno_scout,
            fonte=FonteDato.BUONASTRADA,
            defaults={"ruolo": ruolo, "anno_fine": anni[-1].anno_scout},
        )
        if not creato and periodo.anno_fine < anni[-1].anno_scout:
            periodo.anno_fine = anni[-1].anno_scout
            periodo.save(update_fields=["anno_fine", "aggiornato_il"])
        if creato:
            aggiunti.append(
                f"{persona} — {gruppo}, {periodo.unita}, {_etichetta(periodo.anno_inizio)}"
                f"–{_etichetta(periodo.anno_fine)}"
            )
    return aggiunti
