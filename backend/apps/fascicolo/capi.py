"""The capi's file (DEC-47, DEC-134, DEC-206…DEC-208): years of service with units and
roles, the BuonaStrada data (training level, year in the Co.Ca., appointment), training
entered by hand and the camps recorded as BuonaCaccia events."""

from datetime import date, timedelta

from django.utils import timezone

from apps.anagrafica.models import Appartenenza, Persona, RuoloAppartenenza
from apps.core.anno import AnnoAssociativo
from apps.organizzazione.models import RUOLI_DI_SQUADRIGLIA, Incarico, RuoloIncarico

from .models import Formazione, ServizioPassato

# Roles of the ragazzi, not of a capo's service.
DEI_RAGAZZI = {*RUOLI_DI_SQUADRIGLIA, RuoloIncarico.CONSIGLIO_ANZIANI}


def _anni(dal: date, al: date | None) -> range:
    """The associative years a period touches (its end is exclusive)."""
    fine = (al - timedelta(days=1)) if al else timezone.localdate()
    return range(
        AnnoAssociativo.da_data(dal).anno_fine, AnnoAssociativo.da_data(fine).anno_fine + 1
    )


def anni_di_servizio(persona: Persona) -> list[dict]:
    """Per associative year, newest first: roles from the app, or rebuilt by hand."""
    anni: dict[int, dict] = {}

    def anno(n: int) -> dict:
        return anni.setdefault(
            n,
            {
                "anno": n,
                "etichetta": AnnoAssociativo(n).etichetta,
                "ruoli": [],
                "in_coca": False,
                "ricostruiti": [],
            },
        )

    for a in Appartenenza.objects.filter(persona=persona, ruolo=RuoloAppartenenza.CAPO):
        for n in _anni(a.data_inizio, a.data_fine):
            anno(n)["in_coca"] = True
    for i in (
        Incarico.objects.filter(persona=persona)
        .exclude(ruolo__in=DEI_RAGAZZI)
        .select_related("unita", "gruppo")
    ):
        dove = f", {i.unita}" if i.unita_id else ""
        for n in _anni(i.data_inizio, i.data_fine):
            testo = f"{i.get_ruolo_display()}{dove}"
            if testo not in anno(n)["ruoli"]:
                anno(n)["ruoli"].append(testo)
    for s in ServizioPassato.objects.filter(persona=persona).select_related("unita"):
        dove = str(s.unita) if s.unita_id else s.unita_testo
        anno(s.anno)["ricostruiti"].append(
            {
                "id": s.pk,
                "testo": ", ".join(x for x in (s.get_ruolo_display(), dove, s.note) if x),
            }
        )
    return [anni[n] for n in sorted(anni, reverse=True)]


def formazione(persona: Persona) -> list[dict]:
    """Entered by hand, and the capi training camps recorded as BuonaCaccia events
    (DEC-164), newest first."""
    from apps.eventi.models import StatoPartecipazione

    voci = [
        {
            "id": f.pk,
            "tipo": f.tipo,
            "tipo_nome": f.get_tipo_display(),
            "specifica": f.specifica,
            "data": f.data,
            "precisione": f.precisione,
            "luogo": f.luogo,
            "note": f.note,
            "da_buonacaccia": False,
        }
        for f in Formazione.objects.filter(persona=persona)
    ]
    for p in persona.partecipazioni.filter(
        evento__buonacaccia__formazione_capi=True, stato=StatoPartecipazione.INVITATO
    ).select_related("evento__buonacaccia"):
        evento = p.evento
        dettagli = evento.buonacaccia
        voci.append(
            {
                "id": None,
                "tipo": dettagli.tipo_campo,
                "tipo_nome": dettagli.get_tipo_campo_display(),
                "specifica": dettagli.specifica or evento.titolo,
                "data": timezone.localdate(evento.inizio),
                "precisione": "GIORNO",
                "luogo": evento.luogo,
                "note": "",
                "da_buonacaccia": True,
            }
        )
    return sorted(voci, key=lambda v: v["data"], reverse=True)


def fascicolo(persona: Persona) -> dict:
    anni = anni_di_servizio(persona)
    return {
        "persona_id": persona.pk,
        "persona": f"{persona.nome} {persona.cognome}",
        "livello_formazione": persona.livello_formazione,
        "anno_ingresso_coca": persona.anno_ingresso_coca,
        "numero_nomina": persona.numero_nomina,
        "data_nomina": persona.data_nomina,
        "anni_di_servizio": sum(1 for a in anni if a["ruoli"] or a["ricostruiti"]),
        "anni": anni,
        "formazione": formazione(persona),
    }
