"""The file of a ragazzo for an associative year (DEC-38, DEC-203) and the report for a
passage (DEC-41, DEC-204), as sections of labelled rows, the same for the page and the
PDF. Every section asks apps.permessi.policy who may read it: a parent reading the file
sees only what a parent sees."""

from collections import Counter
from datetime import date

from django.db.models import Q

from apps.anagrafica.models import CAMPI_CONSENSO, ETICHETTE_CAMPI, Appartenenza, Persona
from apps.core.anno import AnnoAssociativo
from apps.permessi import policy
from apps.permessi.models import Azione, Categoria, registra_accessi


def _sezione(titolo: str, voci: list[tuple[str, str]], vuota: str = "") -> dict:
    return {
        "titolo": titolo,
        "voci": [{"etichetta": e, "valore": v} for e, v in voci if v not in (None, "")],
        "vuota": vuota,
    }


def _g(giorno) -> str:
    return giorno.strftime("%d/%m/%Y") if giorno else ""


def _si_no(valore) -> str:
    return {True: "sì", False: "no"}.get(valore, "non indicato")


def presenze_per_anno(persona: Persona) -> list[dict]:
    """Totals per associative year: counted from the marks, or kept as totals after two
    years (DEC-78)."""
    from apps.eventi.models import Presenza, PresenzeAnnue, StatoPresenza

    anni: dict[int, Counter] = {}
    for p in Presenza.objects.filter(persona=persona).select_related("evento"):
        anno = AnnoAssociativo.da_data(p.evento.inizio.date()).anno_fine
        anni.setdefault(anno, Counter())[p.stato] += 1
    for t in PresenzeAnnue.objects.filter(persona=persona):
        conto = anni.setdefault(t.anno, Counter())
        conto[StatoPresenza.PRESENTE] += t.presenti
        conto[StatoPresenza.ASSENTE] += t.assenti
        conto[StatoPresenza.GIUSTIFICATO] += t.giustificati
    return [
        {
            "anno": anno,
            "etichetta": AnnoAssociativo(anno).etichetta,
            "presenti": c[StatoPresenza.PRESENTE],
            "assenti": c[StatoPresenza.ASSENTE],
            "giustificati": c[StatoPresenza.GIUSTIFICATO],
        }
        for anno, c in sorted(anni.items())
    ]


def _testo_presenze(riga: dict) -> str:
    return (
        f"{riga['presenti']} presenze, {riga['assenti']} assenze, "
        f"{riga['giustificati']} assenze giustificate"
    )


def _progressione(user, persona: Persona, dal: date, al: date) -> list[dict]:
    """What happened in the period: phases, Promessa, Carta, verified impegni and mete,
    conquered specialità and brevetti, posti d'azione, Punti della Strada, conclusion."""
    from apps.progressione.models import (
        Impegno,
        Obiettivo,
        PercorsoCompetenza,
        PeriodoBranca,
        PostoAzione,
        PuntoStrada,
        StatoCompetenza,
    )

    dentro = Q(data_inizio__lte=al) & (Q(data_fine__isnull=True) | Q(data_fine__gte=dal))
    voci = []
    for periodo in PeriodoBranca.objects.filter(dentro, persona=persona):
        voci.append(
            (
                f"Percorso {periodo.get_branca_display()}",
                f"dal {_g(periodo.data_inizio)}"
                + (
                    f" al {_g(periodo.data_fine)} ({periodo.motivo_fine})"
                    if periodo.data_fine
                    else ""
                ),
            )
        )
        if hasattr(periodo, "promessa") and dal <= periodo.promessa.data <= al:
            voci.append(("Promessa", _g(periodo.promessa.data)))
        if hasattr(periodo, "firma_carta") and dal <= periodo.firma_carta.data <= al:
            voci.append(("Carta di clan firmata", _g(periodo.firma_carta.data)))
        for t in periodo.tappe.all():
            if t.completata_il and dal <= t.completata_il <= al:
                voci.append((t.get_fase_display(), f"riconosciuta il {_g(t.completata_il)}"))
            elif dal <= t.data_inizio <= al:
                voci.append((t.get_fase_display(), f"iniziata il {_g(t.data_inizio)}"))
    mete = Obiettivo.objects.filter(periodo__persona=persona, verificato_il__range=(dal, al))
    if not policy.vede_mete_riservate(user, persona):
        mete = mete.filter(riservata=False)
    for m in mete:
        voci.append(("Meta o obiettivo raggiunto", f"{m.testo} ({_g(m.verificato_il)})"))
    for i in Impegno.objects.filter(periodo__persona=persona, verificato_il__range=(dal, al)):
        voci.append(("Impegno verificato", f"{i.testo} ({_g(i.verificato_il)})"))
    for c in PercorsoCompetenza.objects.filter(
        periodo__persona=persona,
        stato=StatoCompetenza.RICONOSCIUTO,
        riconosciuto_il__range=(dal, al),
    ):
        voci.append((c.get_tipo_display(), f"{c.nome}, conquistata il {_g(c.riconosciuto_il)}"))
    for p in PostoAzione.objects.filter(
        persona=persona, impresa__dal__range=(dal, al)
    ).select_related("impresa"):
        voci.append(("Posto d'azione", f"{p.ruolo} nell'impresa «{p.impresa.titolo}»"))
    for ps in PuntoStrada.objects.filter(periodo__persona=persona, data__range=(dal, al)):
        voci.append(("Punto della Strada", f"{_g(ps.data)}: {ps.sintesi}".rstrip(": ")))
    return voci


def fascicolo_anno(request, persona: Persona, anno: AnnoAssociativo) -> dict:
    """Every section the user may read, for the year (DEC-38): the reads of special
    data go into the access log (DEC-101)."""
    from apps.buonacaccia.models import IscrizioneBuonaCaccia
    from apps.note.models import RegoleRapporto
    from apps.sanitaria.models import InformazioniSanitarie
    from apps.sanitaria.stampa import GRAVITA

    user = request.auth
    dal, al = anno.inizio, anno.fine
    sezioni = []
    scheda = policy.puo_vedere_scheda(user, persona)

    if scheda:
        unita = Appartenenza.objects.filter(
            Q(data_fine__isnull=True) | Q(data_fine__gt=dal),
            persona=persona,
            data_inizio__lte=al,
        ).select_related("unita")
        voci = [
            ("Nome", f"{persona.nome} {persona.cognome}"),
            ("Nato/a il", _g(persona.data_nascita)),
            ("Codice socio", persona.codice_socio or ""),
            ("Unità nell'anno", ", ".join(str(a.unita) for a in unita)),
        ]
        if policy.puo_vedere_dati_sensibili(user, persona):
            voci += [
                ("Codice fiscale", persona.codice_fiscale or ""),
                (
                    "Indirizzo",
                    f"{persona.indirizzo} {persona.civico}, {persona.comune}".strip(" ,"),
                ),
                ("Email", persona.email),
                ("Cellulare", persona.cellulare),
            ]
            for t in persona.tutori.select_related("tutore"):
                tutore = t.tutore
                voci.append(
                    (
                        t.get_tipo_display(),
                        " · ".join(
                            x
                            for x in (
                                f"{tutore.nome} {tutore.cognome}",
                                tutore.cellulare,
                                tutore.email,
                            )
                            if x
                        ),
                    )
                )
        sezioni.append(_sezione("Anagrafica e famiglia", voci))

    regole = RegoleRapporto.objects.filter(persona=persona).first()
    if regole and policy.puo_vedere_regole_rapporto(user, persona):
        registra_accessi(request, [persona], Categoria.REGOLE_MINORE, Azione.LETTURA)
        sezioni.append(_sezione("Regole sul rapporto con il minore", [("Regole", regole.testo)]))

    if policy.puo_vedere_sanitarie(user, persona):
        info = InformazioniSanitarie.objects.filter(persona=persona).first()
        registra_accessi(request, [persona], Categoria.SANITARIE, Azione.LETTURA)
        voci = []
        if info:
            voci = [
                (
                    "Allergie e intolleranze",
                    (
                        "nessuna"
                        if info.nessuna_allergia
                        else "; ".join(
                            f"{a.sostanza} (reazione {GRAVITA.get(a.gravita, a.gravita)})"
                            for a in info.allergie.all()
                        )
                    ),
                ),
                (
                    "Farmaci",
                    (
                        "nessuno"
                        if info.nessun_farmaco
                        else "; ".join(f"{f.nome}, {f.posologia}" for f in info.farmaci.all())
                    ),
                ),
                ("Esigenze alimentari", info.esigenze_alimentari),
                ("Vaccinazione antitetanica", _si_no(info.antitetanica)),
                ("Note sanitarie", info.note_sanitarie),
                ("Modulo firmato il", _g(info.firmata_il)),
                ("Prescrizione consegnata il", _g(info.prescrizione_consegnata_il)),
            ]
        sezioni.append(_sezione("Scheda sanitaria", voci, "Non compilata."))

    if scheda:
        voci = [(ETICHETTE_CAMPI.get(c, c), _si_no(getattr(persona, c))) for c in CAMPI_CONSENSO]
        for i in IscrizioneBuonaCaccia.objects.filter(
            partecipazione__persona=persona, partecipazione__evento__inizio__date__range=(dal, al)
        ).select_related("partecipazione__evento"):
            esito = i.get_esito_liberatoria_display() or (
                f"ricevuta il {_g(i.liberatoria_ricevuta_il)}"
                if i.liberatoria_ricevuta_il
                else "non ancora ricevuta"
            )
            voci.append((f"Liberatoria: {i.partecipazione.evento.titolo}", esito))
        sezioni.append(_sezione("Autorizzazioni", voci))

    if policy.puo_vedere_progressione(user, persona):
        sezioni.append(
            _sezione(
                "Progressione Personale", _progressione(user, persona, dal, al), "Nulla nell'anno."
            )
        )

    if scheda:
        riga = next((r for r in presenze_per_anno(persona) if r["anno"] == anno.anno_fine), None)
        sezioni.append(
            _sezione("Presenze", [("Nell'anno", _testo_presenze(riga))] if riga else [], "Nessuna.")
        )

    if policy.puo_vedere_quote(user, persona):
        from apps.quote.models import Quota

        voci = [
            (
                q.descrizione,
                f"{q.dovuto:.2f} € dovuti, {q.pagato:.2f} € pagati".replace(".", ","),
            )
            for q in Quota.objects.filter(
                persona=persona, annullata_il__isnull=True, periodo__range=(dal, al)
            ).select_related("tipo")
        ]
        sezioni.append(_sezione("Quote", voci, "Nessuna quota."))

    if policy.e_capo_censito(user) and not policy.e_capo_in_attesa(user):
        from apps.iscrizioni.models import AllegatoIscrizione

        voci = [
            ("Modulo firmato", f"{a.nome_file}, caricato il {_g(a.creato_il)}")
            for a in AllegatoIscrizione.objects.filter(
                richiesta__persona=persona, creato_il__date__range=(dal, al)
            )
        ]
        sezioni.append(_sezione("Documenti", voci, "Nessun documento."))

    note = policy.note_visibili(user, persona).filter(creato_il__date__range=(dal, al))
    if note.exists() or policy.e_capo_censito(user):
        sezioni.append(
            _sezione(
                "Note",
                [(f"{n.get_tipo_display()} del {_g(n.creato_il)}", n.testo) for n in note],
                "Nessuna nota.",
            )
        )
    return {
        "persona_id": persona.pk,
        "persona": f"{persona.nome} {persona.cognome}",
        "anno": anno.anno_fine,
        "etichetta": anno.etichetta,
        "sezioni": sezioni,
        "foto": policy.puo_vedere_foto(user, persona) and persona.foto_profilo.exists(),
    }


def report_passaggio(request, riga) -> dict:
    """For the new capi (DEC-41, DEC-204): the way in the branch left, the summary
    written for them, the attendance of those years. No notes and no rules: what is
    reserved does not pass by itself (spec §11.2)."""
    persona = riga.persona
    passaggio = riga.passaggio
    periodo = riga.periodo_origine
    dal = periodo.data_inizio if periodo else passaggio.data
    al = passaggio.data
    sezioni = [
        _sezione(
            "Passaggio",
            [
                ("Da", str(passaggio.unita_origine)),
                ("A", str(passaggio.unita_destinazione)),
                ("Dal", _g(passaggio.data)),
                ("Sintesi per i nuovi capi", riga.sintesi),
            ],
        ),
        _sezione(
            "Percorso nella branca",
            _progressione(request.auth, persona, dal, al),
            "Nulla di registrato.",
        ),
        _sezione(
            "Presenze",
            [
                (r["etichetta"], _testo_presenze(r))
                for r in presenze_per_anno(persona)
                if AnnoAssociativo.da_data(dal).anno_fine
                <= r["anno"]
                <= AnnoAssociativo.da_data(al).anno_fine
            ],
            "Nessuna.",
        ),
    ]
    return {
        "persona_id": persona.pk,
        "persona": f"{persona.nome} {persona.cognome}",
        "anno": AnnoAssociativo.da_data(al).anno_fine,
        "etichetta": f"Passaggio del {_g(passaggio.data)}",
        "sezioni": sezioni,
        "foto": False,
    }
