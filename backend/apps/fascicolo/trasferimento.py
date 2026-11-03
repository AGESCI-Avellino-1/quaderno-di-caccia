"""Moving a file to another group that uses QdC (DEC-46, DEC-213): the Progressione
Personale, the notes that are not reserved (shared with the ragazzo or the parents),
the scout path (DEC-287), for a capo the years of service and the training. Never attendance, health data,
rules on the relationship with the minor, photos or private mete and Punto della Strada
parts. The registry travels with BuonaStrada: the person is matched by codice fiscale.

A JSON file with a format name and version, exported and imported by a capogruppo."""

import io
import json
import zipfile
from datetime import date

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.anagrafica.models import Persona
from apps.organizzazione.models import Gruppo

FORMATO = "qdc-fascicolo"
# 2 adds the scout path; files of version 1 are still read.
VERSIONE = 2
VERSIONI_LETTE = {1, 2}
# Inside the archive ZIP (DEC-215).
FILE_ARCHIVIO = "reimportazione.json"


def leggi(contenuto: bytes) -> dict:
    """The JSON of an exchange, or the archive ZIP that holds one (DEC-215)."""
    try:
        if contenuto[:2] == b"PK":
            with zipfile.ZipFile(io.BytesIO(contenuto)) as archivio:
                contenuto = archivio.read(FILE_ARCHIVIO)
        dati = json.loads(contenuto.decode("utf-8"))
    except (KeyError, zipfile.BadZipFile, UnicodeDecodeError, ValueError) as errore:
        raise ValidationError("Non è un fascicolo esportato dal Quaderno di Caccia.") from errore
    if not isinstance(dati, dict):
        raise ValidationError("Non è un fascicolo esportato dal Quaderno di Caccia.")
    return dati


def _riunisci(persona: Persona, dati: dict) -> bool:
    """Coming back after the archiving (DEC-215): the record with the name and the years
    that stayed here joins the person BuonaStrada brought back, access log included.
    True when the years in the group came back that way."""
    from apps.anagrafica.models import Appartenenza, AppartenenzaSquadriglia
    from apps.archivio.models import Archiviazione
    from apps.organizzazione.models import Incarico
    from apps.permessi.models import AccessoDatoSensibile

    rimasto_id = (dati.get("archivio") or {}).get("persona_id")
    rimasto = Persona.objects.filter(pk=rimasto_id, archiviazioni__isnull=False).first()
    if rimasto is None:
        return False
    from apps.organizzazione.servizi import ripristina_unita_di

    if rimasto.pk != persona.pk:  # else already joined by the BuonaStrada import (DEC-217)
        for modello in (Appartenenza, AppartenenzaSquadriglia, Incarico, AccessoDatoSensibile):
            modello.objects.filter(persona=rimasto).update(persona=persona)
        Archiviazione.objects.filter(persona=rimasto).update(persona=persona)
        rimasto.delete()
    # The archived units of their years come back, closed (DEC-275).
    ripristina_unita_di(persona)
    return True


def _d(valore) -> str | None:
    return valore.isoformat() if valore else None


def esporta(persona: Persona) -> dict:
    from apps.anagrafica import percorso as percorso_scout
    from apps.fascicolo import capi
    from apps.note.models import Nota
    from apps.permessi import policy
    from apps.progressione.models import PeriodoBranca

    gruppo = Gruppo.objects.first()
    periodi = []
    for p in PeriodoBranca.objects.filter(persona=persona).prefetch_related(
        "tappe__distintivo", "mete", "impegni", "competenze", "punti_strada"
    ):
        periodi.append(
            {
                "branca": p.branca,
                "data_inizio": _d(p.data_inizio),
                "precisione_inizio": p.precisione_inizio,
                "data_fine": _d(p.data_fine),
                "motivo_fine": p.motivo_fine,
                "promessa": (
                    {"data": _d(p.promessa.data), "precisione": p.promessa.precisione}
                    if hasattr(p, "promessa")
                    else None
                ),
                "firma_carta": (
                    {"data": _d(p.firma_carta.data), "precisione": p.firma_carta.precisione}
                    if hasattr(p, "firma_carta")
                    else None
                ),
                "conclusione": (
                    {
                        "tipo": p.conclusione.tipo,
                        "data": _d(p.conclusione.data),
                        "precisione": p.conclusione.precisione,
                        "nota": p.conclusione.nota,
                    }
                    if hasattr(p, "conclusione")
                    else None
                ),
                "tappe": [
                    {
                        "fase": t.fase,
                        "data_inizio": _d(t.data_inizio),
                        "precisione_inizio": t.precisione_inizio,
                        "collocamento": t.collocamento,
                        "motivazione": t.motivazione,
                        "completata_il": _d(t.completata_il),
                        "precisione_completata": t.precisione_completata,
                        "data_fine": _d(t.data_fine),
                        "distintivo": (
                            {"data": _d(t.distintivo.data), "precisione": t.distintivo.precisione}
                            if hasattr(t, "distintivo")
                            else None
                        ),
                    }
                    for t in p.tappe.all()
                ],
                # A private meta stays in the group (DEC-173).
                "mete": [_percorso(m) for m in p.mete.all() if not m.riservata],
                "impegni": [
                    _percorso(i) | {"criterio_verifica": i.criterio_verifica}
                    for i in p.impegni.all()
                ],
                "competenze": [
                    {
                        "tipo": c.tipo,
                        "codice": c.codice,
                        "nome": c.nome,
                        "versione_catalogo": c.versione_catalogo,
                        "stato": c.stato,
                        "carta": c.carta,
                        "maestro": c.maestro,
                        "confronto": c.confronto,
                        "riconosciuto_il": _d(c.riconosciuto_il),
                        "precisione_riconosciuto": c.precisione_riconosciuto,
                        "distintivo_il": _d(c.distintivo_il),
                        "precisione_distintivo": c.precisione_distintivo,
                    }
                    for c in p.competenze.all()
                ],
                # Only the shared summary and the service (DEC-180, DEC-188).
                "punti_strada": [
                    {"data": _d(ps.data), "sintesi": ps.sintesi, "servizio": ps.servizio}
                    for ps in p.punti_strada.all()
                ],
            }
        )
    note = [
        {
            "tipo": n.tipo,
            "testo": n.testo,
            "scritta_il": _d(timezone.localdate(n.creato_il)),
            "visibile_ragazzo": n.visibile_ragazzo,
            "visibile_genitori": n.visibile_genitori,
        }
        for n in Nota.objects.filter(persona=persona)
        if n.visibile_ragazzo or n.visibile_genitori
    ]
    capo = None
    if policy.e_capo_persona(persona):
        dati = capi.fascicolo(persona)
        capo = {
            "anni": [
                {"anno": a["anno"], "ruoli": a["ruoli"] + [r["testo"] for r in a["ricostruiti"]]}
                for a in dati["anni"]
                if a["ruoli"] or a["ricostruiti"]
            ],
            "formazione": [
                {k: (_d(v) if isinstance(v, date) else v) for k, v in f.items() if k != "id"}
                for f in dati["formazione"]
            ],
        }
    return {
        "formato": FORMATO,
        "versione": VERSIONE,
        "gruppo": gruppo.denominazione if gruppo else "",
        "esportato_il": timezone.localdate().isoformat(),
        "persona": {
            "nome": persona.nome,
            "cognome": persona.cognome,
            "codice_fiscale": persona.codice_fiscale,
            "data_nascita": _d(persona.data_nascita),
        },
        "progressione": periodi,
        # Every period, in this group's units and outside them (DEC-287). `gruppo` empty:
        # this group; `nelle_unita`: from the app's memberships, which an archived person
        # keeps here (DEC-215).
        "percorso": [
            {
                "gruppo": x["gruppo"],
                "unita": x["unita"],
                "ruolo": x["ruolo"],
                "anno_inizio": x["anno_inizio"],
                "anno_fine": x["anno_fine"],
                "fonte": x["fonte"],
                "nelle_unita": x["id"] is None,
            }
            for x in percorso_scout.periodi(persona)
        ],
        "note": note,
        "capo": capo,
    }


def _percorso(o) -> dict:
    return {
        "testo": o.testo,
        "stato": o.stato,
        "termine": _d(o.termine),
        "verificato_il": _d(o.verificato_il),
        "sede": o.sede,
        "sede_descrizione": o.sede_descrizione,
        "interrotto_il": _d(o.interrotto_il),
        "motivo_interruzione": o.motivo_interruzione,
    }


def _nome_gruppo(nome: str) -> str:
    """For comparing group names: "AGESCI Avellino 1" and "AVELLINO 1" are the same."""
    nome = " ".join(nome.split()).casefold()
    return nome.removeprefix("agesci ").strip()


def _importa_percorso(persona: Persona, dati: dict, esportato: date, utente) -> int:
    """The scout path of the file (DEC-213, DEC-287). From another group, its years
    become years "in another group" with its name; back from the archive, the years in
    this group's units are already here with the record (DEC-215). A period already
    here (same group, years and role, for instance from BuonaStrada) is skipped, as is
    one in the group receiving the file (maintainer, 03/11)."""
    from apps.anagrafica.models import PeriodoPercorso
    from apps.core.anno import AnnoAssociativo
    from apps.core.models import FonteDato
    from apps.impostazioni.models import Impostazioni

    archivio = bool(dati.get("archivio"))
    loro = (dati.get("gruppo") or "").strip() or "Altro gruppo"
    nostri = {_nome_gruppo(Impostazioni.carica().nome_del_gruppo())}
    if gruppo := Gruppo.objects.first():
        nostri.add(_nome_gruppo(gruppo.denominazione))
    ultimo = AnnoAssociativo.da_data(esportato).anno_fine
    presenti = {
        (_nome_gruppo(p.gruppo), p.anno_inizio, p.anno_fine, p.ruolo)
        for p in PeriodoPercorso.objects.filter(persona=persona)
    }
    aggiunti = 0
    for x in dati.get("percorso", []):
        if archivio and x.get("nelle_unita"):
            continue
        gruppo = (x.get("gruppo") or "").strip()
        if not archivio and not gruppo:
            gruppo = loro
        if gruppo and _nome_gruppo(gruppo) in nostri:
            continue  # years in this group: its own units have them
        periodo = PeriodoPercorso(
            persona=persona,
            gruppo=gruppo[:160],
            unita=x["unita"][:160],
            ruolo=x["ruolo"],
            anno_inizio=x["anno_inizio"],
            anno_fine=x["anno_fine"] or ultimo,
            fonte=x.get("fonte") or FonteDato.BUONASTRADA,
            registrato_da=utente,
        )
        chiave = (
            _nome_gruppo(periodo.gruppo),
            periodo.anno_inizio,
            periodo.anno_fine,
            periodo.ruolo,
        )
        if chiave in presenti:
            continue
        periodo.full_clean()
        periodo.save()
        presenti.add(chiave)
        aggiunti += 1
    return aggiunti


def _g(valore: str | None) -> date | None:
    return date.fromisoformat(valore) if valore else None


@transaction.atomic
def importa(dati: dict, utente) -> dict:
    """Into the person with the same codice fiscale, who must already be in this group's
    registry (BuonaStrada moves the membership). The periods keep where they come from;
    an open period stays open only if the person has none here (DEC-213)."""
    from apps.buonacaccia.models import TipoCampoFormazione
    from apps.fascicolo.models import Formazione, RuoloPassato, ServizioPassato
    from apps.note.models import Nota
    from apps.progressione.models import (
        Conclusione,
        ConsegnaDistintivo,
        FirmaCarta,
        Impegno,
        Obiettivo,
        PercorsoCompetenza,
        PeriodoBranca,
        Promessa,
        PuntoStrada,
        Tappa,
    )

    if dati.get("formato") != FORMATO or dati.get("versione") not in VERSIONI_LETTE:
        raise ValidationError("Non è un fascicolo esportato dal Quaderno di Caccia.")
    cf = (dati.get("persona") or {}).get("codice_fiscale") or ""
    persona = Persona.objects.filter(codice_fiscale=cf).first() if cf else None
    if persona is None:
        raise ValidationError(
            "La persona non c'è ancora nell'anagrafica del gruppo: importa prima i dati di "
            "BuonaStrada."
        )
    provenienza = (dati.get("gruppo") or "altro gruppo")[:120]
    esportato = _g(dati.get("esportato_il")) or timezone.localdate()
    if dati.get("archivio"):
        provenienza = f"Archivio del {esportato:%d/%m/%Y}"[:120]
    if PeriodoBranca.objects.filter(persona=persona, provenienza=provenienza).exists():
        raise ValidationError("Questo fascicolo è già stato importato.")
    riunito = _riunisci(persona, dati) if dati.get("archivio") else False
    aperto_qui = PeriodoBranca.objects.filter(persona=persona, data_fine__isnull=True).exists()
    conteggio = {"periodi": 0, "note": 0, "anni_di_servizio": 0, "formazione": 0, "percorso": 0}
    try:
        for p in dati.get("progressione", []):
            fine = _g(p.get("data_fine"))
            motivo = p.get("motivo_fine", "")
            if fine is None and aperto_qui:
                fine, motivo = esportato, f"Trasferimento da {provenienza}"
            periodo = PeriodoBranca.objects.create(
                persona=persona,
                branca=p["branca"],
                data_inizio=_g(p["data_inizio"]),
                precisione_inizio=p.get("precisione_inizio", "GIORNO"),
                data_fine=fine,
                motivo_fine=motivo,
                registrato_da=utente,
                provenienza=provenienza,
            )
            conteggio["periodi"] += 1
            if p.get("promessa"):
                Promessa.objects.create(
                    periodo=periodo,
                    data=_g(p["promessa"]["data"]),
                    precisione=p["promessa"]["precisione"],
                    registrata_da=utente,
                )
            if p.get("firma_carta"):
                FirmaCarta.objects.create(
                    periodo=periodo,
                    data=_g(p["firma_carta"]["data"]),
                    precisione=p["firma_carta"]["precisione"],
                    registrata_da=utente,
                )
            if p.get("conclusione"):
                c = p["conclusione"]
                Conclusione.objects.create(
                    periodo=periodo,
                    tipo=c["tipo"],
                    data=_g(c["data"]),
                    precisione=c["precisione"],
                    nota=c.get("nota", ""),
                    registrata_da=utente,
                )
            for t in p.get("tappe", []):
                tappa = Tappa.objects.create(
                    periodo=periodo,
                    fase=t["fase"],
                    data_inizio=_g(t["data_inizio"]),
                    precisione_inizio=t.get("precisione_inizio", "GIORNO"),
                    collocamento=t.get("collocamento", False),
                    motivazione=t.get("motivazione", ""),
                    completata_il=_g(t.get("completata_il")),
                    precisione_completata=t.get("precisione_completata", "GIORNO"),
                    data_fine=_g(t.get("data_fine")) or (fine if periodo.data_fine else None),
                    registrata_da=utente,
                )
                if t.get("distintivo"):
                    ConsegnaDistintivo.objects.create(
                        tappa=tappa,
                        data=_g(t["distintivo"]["data"]),
                        precisione=t["distintivo"]["precisione"],
                        registrata_da=utente,
                    )
            for modello, chiave in ((Obiettivo, "mete"), (Impegno, "impegni")):
                for o in p.get(chiave, []):
                    modello.objects.create(
                        periodo=periodo,
                        testo=o["testo"],
                        stato=o["stato"],
                        termine=_g(o.get("termine")),
                        verificato_il=_g(o.get("verificato_il")),
                        sede=o.get("sede", ""),
                        sede_descrizione=o.get("sede_descrizione", ""),
                        interrotto_il=_g(o.get("interrotto_il")),
                        motivo_interruzione=o.get("motivo_interruzione", ""),
                        creato_da=utente,
                        **(
                            {"criterio_verifica": o.get("criterio_verifica", "")}
                            if modello is Impegno
                            else {}
                        ),
                    )
            for c in p.get("competenze", []):
                PercorsoCompetenza.objects.create(
                    periodo=periodo,
                    tipo=c["tipo"],
                    codice=c["codice"],
                    nome=c["nome"],
                    versione_catalogo=c.get("versione_catalogo", ""),
                    stato=c["stato"],
                    carta=c.get("carta", ""),
                    maestro=c.get("maestro", ""),
                    confronto=c.get("confronto", ""),
                    riconosciuto_il=_g(c.get("riconosciuto_il")),
                    precisione_riconosciuto=c.get("precisione_riconosciuto", "GIORNO"),
                    distintivo_il=_g(c.get("distintivo_il")),
                    precisione_distintivo=c.get("precisione_distintivo", "GIORNO"),
                    storico=True,
                    creato_da=utente,
                )
            for ps in p.get("punti_strada", []):
                PuntoStrada.objects.create(
                    periodo=periodo,
                    data=_g(ps["data"]),
                    sintesi=ps.get("sintesi", ""),
                    servizio=ps.get("servizio", ""),
                    creato_da=utente,
                )
        for n in dati.get("note", []):
            Nota.objects.create(
                persona=persona,
                tipo=n["tipo"],
                testo=n["testo"],
                visibile_ragazzo=n.get("visibile_ragazzo", False),
                visibile_genitori=n.get("visibile_genitori", False),
                provenienza=provenienza,
            )
            conteggio["note"] += 1
        conteggio["percorso"] = _importa_percorso(persona, dati, esportato, utente)
        capo = dati.get("capo") or {}
        # Back from the archive here: the roles of those years came back with the
        # record, they are not rebuilt again.
        for a in [] if riunito else capo.get("anni", []):
            ServizioPassato.objects.create(
                persona=persona,
                anno=a["anno"],
                ruolo=RuoloPassato.ALTRO,
                unita_testo=provenienza,
                note="; ".join(a.get("ruoli", []))[:300] or "Servizio",
                registrato_da=utente,
            )
            conteggio["anni_di_servizio"] += 1
        for f in capo.get("formazione", []):
            if f.get("tipo") not in TipoCampoFormazione.values:
                continue
            Formazione.objects.create(
                persona=persona,
                tipo=f["tipo"],
                specifica=(f.get("specifica") or "")[:160],
                data=_g(f["data"]),
                precisione=f.get("precisione", "GIORNO"),
                luogo=(f.get("luogo") or "")[:120],
                note=(f.get("note") or "")[:300],
                registrata_da=utente,
            )
            conteggio["formazione"] += 1
    except (KeyError, TypeError, ValueError) as errore:
        raise ValidationError(
            "Il file è incompleto o danneggiato: niente è stato importato."
        ) from errore
    return {"persona_id": persona.pk, "persona": f"{persona.nome} {persona.cognome}", **conteggio}
