"""Full export and erasure of a person's data (DEC-102, DEC-136).

Export: everything the app holds about a person, as JSON (portability) that the PWA
also shows as a printable page. Erasure: the data that exist only in the app go; an
ex member is also anonymised, keeping only the periods in units for statistics.
BuonaStrada stays with the national office.
"""

from auditlog.context import disable_auditlog
from auditlog.models import LogEntry
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Invito
from apps.anagrafica.models import (
    CAMPI_BUONASTRADA,
    ETICHETTE_CAMPI,
    Appartenenza,
    CorrezioneAnagrafica,
    DerogaSquadriglia,
    Persona,
    PreferenzeEmail,
    RelazioneTutela,
    VisibilitaGenitori,
)
from apps.anagrafica.servizi import come_testo, telefono_in_squadriglia
from apps.buonacaccia.models import IscrizioneBuonaCaccia, QuotaFormazione
from apps.dispositivi.models import Dispositivo
from apps.iscrizioni.models import RichiestaIscrizione
from apps.organizzazione.models import Incarico
from apps.permessi.models import AccessoDatoSensibile
from apps.quote.models import Quota
from apps.sanitaria.models import InformazioniSanitarie, ReperibilitaEvento

from .models import RichiestaDiritti


def _periodo(oggetto) -> dict:
    return {"Dal": come_testo(oggetto.data_inizio), "Al": come_testo(oggetto.data_fine)}


def _valore(persona: Persona, campo: str):
    """A registry value for people: labels for codes, yes/no stays a boolean."""
    field = Persona._meta.get_field(campo)
    valore = getattr(persona, campo)
    if field.choices and valore:
        return getattr(persona, f"get_{campo}_display")()
    if isinstance(valore, bool):
        return valore
    return come_testo(valore)


def _giorno(momento) -> str:
    return come_testo(momento and momento.date())


def _telefono(persona: Persona) -> str:
    numero, genitore = telefono_in_squadriglia(persona)
    if not numero:
        return ""
    return f"{numero} (di {genitore.nome} {genitore.cognome})" if genitore else numero


def fascicolo(persona: Persona) -> dict:
    """Everything the app holds about `persona`, in plain words where it helps."""
    utente = persona.utente
    sanitarie = InformazioniSanitarie.objects.filter(persona=persona).first()
    visibilita = VisibilitaGenitori.objects.filter(persona=persona).first()
    return {
        "generato_il": timezone.now().isoformat(),
        "anagrafica": {
            ETICHETTE_CAMPI[campo]: _valore(persona, campo) for campo in CAMPI_BUONASTRADA
        }
        | {"Codice socio": persona.codice_socio or ""},
        "account": (
            {
                "Email di accesso": utente.email,
                "Creato il": _giorno(utente.date_joined),
                "Ultimo accesso": _giorno(utente.last_login),
                "Dispositivi": [
                    {
                        "Nome": d.nome,
                        "Ultimo contatto": _giorno(d.ultimo_contatto),
                        "Scollegato il": _giorno(d.revocato_il),
                    }
                    for d in Dispositivo.objects.filter(utente=utente)
                ],
            }
            if utente
            else None
        ),
        "genitori_e_tutori": [
            {"Nome": f"{r.tutore.nome} {r.tutore.cognome}", "Relazione": r.get_tipo_display()}
            for r in RelazioneTutela.objects.filter(minore=persona).select_related("tutore")
        ],
        "figli_o_tutelati": [
            {"Nome": f"{r.minore.nome} {r.minore.cognome}", "Relazione": r.get_tipo_display()}
            for r in RelazioneTutela.objects.filter(tutore=persona).select_related("minore")
        ],
        "unita": [
            {"Unità": str(a.unita), "Ruolo": a.get_ruolo_display()} | _periodo(a)
            for a in Appartenenza.objects.filter(persona=persona).select_related("unita")
        ],
        "squadriglie": [
            {"Squadriglia": str(a.squadriglia)} | _periodo(a)
            for a in persona.appartenenze_squadriglia.select_related("squadriglia")
        ],
        "incarichi": [
            {"Incarico": i.get_ruolo_display(), "Dove": str(i.unita or i.squadriglia or i.gruppo)}
            | _periodo(i)
            for i in Incarico.objects.filter(persona=persona).select_related(
                "unita", "squadriglia", "gruppo"
            )
        ],
        "telefono_in_squadriglia": {
            "Numero mostrato": _telefono(persona),
            "Numero di un genitore scelto per lui o lei": (
                str(persona.telefono_squadriglia_da) if persona.telefono_squadriglia_da else ""
            ),
            "Nascosto agli altri ragazzi": persona.telefono_squadriglia_nascosto,
            "Il suo numero vale per i figli senza cellulare": persona.telefono_per_i_figli,
        },
        "informazioni_sanitarie": (
            {
                "Nessuna allergia": sanitarie.nessuna_allergia,
                "Nessun farmaco": sanitarie.nessun_farmaco,
                "Esigenze alimentari": sanitarie.esigenze_alimentari,
                "Allergie e intolleranze": [
                    {
                        "Tipo": a.get_tipo_display(),
                        "Sostanza": a.sostanza,
                        "Gravità": a.get_gravita_display(),
                        "Reazione": a.reazione,
                        "Cosa fare": a.cosa_fare,
                    }
                    for a in sanitarie.allergie.all()
                ],
                "Farmaci": [
                    {
                        "Nome": f.nome,
                        "Posologia": f.posologia,
                        "Orari": f.orari,
                        "Lo prende da solo": f.autonomo,
                        "Note": f.note,
                    }
                    for f in sanitarie.farmaci.all()
                ],
                "Tessera sanitaria": sanitarie.tessera_sanitaria,
                "Reperibilità per emergenze": " ".join(
                    x for x in (sanitarie.reperibilita_nome, sanitarie.reperibilita_telefono) if x
                ),
                "Vaccinazione antitetanica": {True: "sì", False: "no"}.get(
                    sanitarie.antitetanica, "non indicata"
                ),
                "Ulteriori note sanitarie": sanitarie.note_sanitarie,
                "Gruppo sanguigno": sanitarie.gruppo_sanguigno,
                "Medico curante": sanitarie.medico_curante,
                "Altre vaccinazioni": sanitarie.altre_vaccinazioni,
                "Modulo firmato il": come_testo(sanitarie.firmata_il),
                "Prescrizione consegnata il": come_testo(sanitarie.prescrizione_consegnata_il),
                "Inserite da": sanitarie.get_inserite_da_display(),
                "Aggiornate il": _giorno(sanitarie.aggiornato_il),
            }
            if sanitarie
            else None
        ),
        "reperibilita_per_evento": [
            {"Evento": r.evento.titolo, "Chi": r.nome, "Telefono": r.telefono}
            for r in ReperibilitaEvento.objects.filter(persona=persona).select_related("evento")
        ],
        "eccezioni_squadriglia": [
            {
                "Reparto": str(d.reparto),
                "Squadriglie": d.get_sesso_squadriglia_display(),
                "Decisa il": come_testo(d.data_decisione),
                "Motivazione": d.motivazione,
                "Revocata il": come_testo(d.revocata_il),
            }
            for d in DerogaSquadriglia.objects.filter(persona=persona).select_related("reparto")
        ],
        "visibilita_ai_genitori": (
            {
                "Contatti e indirizzo": visibilita.contatti,
                "Farmaci, allergie e alimentazione": visibilita.sanitarie,
                "Scheda e attività": visibilita.scheda,
                "Quote e pagamenti": visibilita.quote,
                "Scelta il": _giorno(visibilita.decisa_il),
            }
            if visibilita and visibilita.decisa_il
            else None
        ),
        # Payments are accounting records: exported here, kept by an erasure.
        "quote": [
            {
                "Quota": q.descrizione,
                "Scadenza": come_testo(q.scadenza),
                "Importo": str(q.importo),
                "Sconto famiglia": str(q.sconto),
                "Agevolazione": str(q.agevolata),
                "Pagato": str(q.pagato),
                "Annullata": bool(q.annullata_il),
            }
            for q in Quota.objects.filter(persona=persona).select_related("tipo", "agevolazione")
        ],
        "email_scelte": (
            {
                "Eventi": p.eventi,
                "Promemoria delle quote": p.promemoria_quote,
                "Avvisi dei 18 anni": p.maggiore_eta,
                "Riepiloghi per i capi": p.riepiloghi,
            }
            if (p := PreferenzeEmail.objects.filter(persona=persona).first())
            else None
        ),
        "correzioni_ai_dati": [
            {
                "Dato": ETICHETTE_CAMPI.get(c.campo, c.campo),
                "Prima": c.valore_precedente,
                "Dopo": c.valore_corretto,
                "Stato": c.get_stato_display(),
                "Il": _giorno(c.creato_il),
            }
            for c in CorrezioneAnagrafica.objects.filter(persona=persona)
        ],
        "inviti": [
            {
                "Email": i.email,
                "Creato il": _giorno(i.creato_il),
                "Usato il": _giorno(i.usato_il),
            }
            for i in Invito.objects.filter(persona=persona)
        ],
        "accessi_ai_dati_delicati": [
            {
                "Quando": a.creato_il.isoformat(),
                "Chi": a.utente.email if a.utente else "",
                "Cosa": a.get_categoria_display(),
                "Azione": a.get_azione_display(),
            }
            for a in AccessoDatoSensibile.objects.filter(persona=persona).select_related("utente")
        ],
        "iscrizioni_dall_app": [
            {
                "Unità": str(r.unita),
                "Stato": r.get_stato_display(),
                "Richiesta il": _giorno(r.creato_il),
                "Moduli firmati": ", ".join(a.nome_file for a in r.allegati.all()),
            }
            for r in RichiestaIscrizione.objects.filter(persona=persona).select_related("unita")
        ],
        "eventi_buonacaccia": [_iscrizione_buonacaccia(i) for i in _iscrizioni_bc(persona)],
        **_progressione(persona),
        "campi_di_formazione": [
            {
                "Evento": q.partecipazione.evento.titolo,
                "Dal": _giorno(q.partecipazione.evento.inizio),
                "Quota versata": str(q.importo),
            }
            for q in QuotaFormazione.objects.filter(partecipazione__persona=persona).select_related(
                "partecipazione__evento"
            )
        ],
        "richieste_dei_diritti": [
            {
                "Tipo": r.get_tipo_display(),
                "Ricevuta il": come_testo(r.ricevuta_il),
                "Chiusa il": come_testo(r.evasa_il),
            }
            for r in RichiestaDiritti.objects.filter(persona=persona)
        ],
    }


def _quando(data, precisione=None) -> str:
    from apps.core.date_parziali import DataParziale

    if data is None:
        return ""
    return str(DataParziale(data, precisione)) if precisione else data.isoformat()


def _progressione(persona: Persona) -> dict:
    """The Progressione Personale, private mete and the private part of the Punti della
    Strada included: it is all about the person."""
    from apps.progressione.models import PassaggioPersona, PeriodoBranca, PostoAzione

    periodi = list(
        PeriodoBranca.objects.filter(persona=persona).prefetch_related(
            "tappe", "mete", "impegni", "competenze", "punti_strada"
        )
    )
    percorso = []
    for periodo in periodi:
        voce = {
            "Branca": periodo.get_branca_display(),
            "Dal": _quando(periodo.data_inizio, periodo.precisione_inizio),
            "Al": _quando(periodo.data_fine),
            "Come si è chiuso": periodo.motivo_fine,
            "Promessa": (
                _quando(periodo.promessa.data, periodo.promessa.precisione)
                if hasattr(periodo, "promessa")
                else ""
            ),
            "Firma della Carta di clan": (
                _quando(periodo.firma_carta.data, periodo.firma_carta.precisione)
                if hasattr(periodo, "firma_carta")
                else ""
            ),
            "Conclusione": (
                f"{periodo.conclusione.get_tipo_display()} "
                f"{_quando(periodo.conclusione.data, periodo.conclusione.precisione)}"
                if hasattr(periodo, "conclusione")
                else ""
            ),
            "Tappe o passi": "; ".join(
                f"{t.get_fase_display()} dal {_quando(t.data_inizio, t.precisione_inizio)}"
                + (
                    f", riconosciuta {_quando(t.completata_il, t.precisione_completata)}"
                    if t.completata_il
                    else ""
                )
                for t in periodo.tappe.all()
            ),
        }
        percorso.append(voce)
    return {
        "progressione_personale": percorso,
        "mete_e_impegni": [
            {
                "Tipo": tipo if periodo.branca != "RS" or tipo != "Meta" else "Obiettivo",
                "Testo": v.testo,
                "Riservata": "sì" if getattr(v, "riservata", False) else "",
                "Stato": v.get_stato_display(),
                "Verificato il": _quando(v.verificato_il),
                "Interrotto": v.motivo_interruzione,
            }
            for periodo in periodi
            for tipo, righe in (("Meta", periodo.mete.all()), ("Impegno", periodo.impegni.all()))
            for v in righe
        ],
        "punti_della_strada": [
            {
                "Data": _quando(ps.data),
                "Sintesi": ps.sintesi,
                "Servizio": ps.servizio,
                "Parte riservata": ps.riservato,
                "La mia rilettura": ps.voce,
            }
            for periodo in periodi
            for ps in periodo.punti_strada.all()
        ],
        "specialita_e_brevetti": [
            {
                "Tipo": c.get_tipo_display(),
                "Nome": c.nome,
                "Stato": c.get_stato_display(),
                "Carta": c.carta,
                "Maestro": c.maestro,
                "Conquistata": _quando(c.riconosciuto_il, c.precisione_riconosciuto),
                "Distintivo": _quando(c.distintivo_il, c.precisione_distintivo),
            }
            for periodo in periodi
            for c in periodo.competenze.all()
        ],
        "posti_d_azione": [
            {
                "Impresa": p.impresa.titolo,
                "Ruolo": p.ruolo,
                "Verificato il": _quando(p.verificato_il),
            }
            for p in PostoAzione.objects.filter(persona=persona).select_related("impresa")
        ],
        "passaggi_di_branca": [
            {
                "Da": str(r.passaggio.unita_origine),
                "A": str(r.passaggio.unita_destinazione),
                "Dal": _quando(r.passaggio.data),
                "Stato": (
                    "annullato dopo l'esecuzione"
                    if r.rettificata_il
                    else r.passaggio.get_stato_display()
                ),
                "Sintesi per i nuovi capi": r.sintesi,
            }
            for r in PassaggioPersona.objects.filter(persona=persona).select_related(
                "passaggio__unita_origine", "passaggio__unita_destinazione"
            )
        ],
    }


def _cancella_progressione(persona: Persona) -> None:
    """All of it is app-only: periods with tappe, Promessa, mete, impegni, specialità and
    brevetti, places in the imprese, the summaries written at the passages. Patrol
    specialità and imprese belong to the patrol and stay."""
    from apps.progressione.models import PassaggioPersona, PeriodoBranca, PostoAzione

    periodi = list(PeriodoBranca.objects.filter(persona=persona))
    figli = []
    for periodo in periodi:
        for relazione in periodo._meta.related_objects:
            if relazione.related_model is PassaggioPersona:
                continue
            accessor = relazione.get_accessor_name()
            if relazione.one_to_one:
                oggetto = getattr(periodo, accessor, None) if hasattr(periodo, accessor) else None
                figli += [oggetto] if oggetto is not None else []
            else:
                figli += list(getattr(periodo, accessor).all())
        for tappa in periodo.tappe.all():
            if hasattr(tappa, "distintivo"):
                figli.append(tappa.distintivo)
    posti = list(PostoAzione.objects.filter(persona=persona))
    passaggi = list(PassaggioPersona.objects.filter(persona=persona))
    _cancella_storico([*figli, *periodi, *posti, *passaggi])
    for oggetto in [*posti, *passaggi]:
        oggetto.delete()
    for periodo in periodi:
        periodo.delete()


def _iscrizioni_bc(persona: Persona):
    return IscrizioneBuonaCaccia.objects.filter(partecipazione__persona=persona).select_related(
        "partecipazione__evento"
    )


def _iscrizione_buonacaccia(i: IscrizioneBuonaCaccia) -> dict:
    """A registration on BuonaCaccia: the answers with their questions, the staff's
    presentation too (it is about the person)."""
    from apps.buonacaccia.servizi import riepilogo

    return {
        "Evento": i.partecipazione.evento.titolo,
        "Dal": _giorno(i.partecipazione.evento.inizio),
        "Iscritto il": come_testo(i.iscritto_il),
        "Stato": i.get_stato_display(),
        "Liberatoria ricevuta il": come_testo(i.liberatoria_ricevuta_il),
        "Esito della liberatoria": i.get_esito_liberatoria_display(),
        "Risposte": "; ".join(
            f"{r['domanda']}: {r['risposta']}" for r in riepilogo(i) if r["risposta"]
        ),
        "Presentazione dello staff": i.presentazione,
    }


def resta_in_anagrafica(persona: Persona) -> str | None:
    """Why the registry data of `persona` must stay (None: they can be anonymised)."""
    if Appartenenza.objects.attive().filter(persona=persona).exists():
        return "È ancora socio: i dati anagrafici arrivano da BuonaStrada."
    tutelati_attivi = Appartenenza.objects.attive().filter(persona__tutori__tutore=persona)
    if tutelati_attivi.exists():
        return "È genitore o tutore di un socio: i suoi recapiti servono per il figlio."
    return None


def anteprima_cancellazione(persona: Persona) -> dict:
    motivo = resta_in_anagrafica(persona)
    voci = [
        "Farmaci, allergie, intolleranze ed esigenze alimentari",
        "Eccezioni sulla squadriglia",
        "Scelte sul telefono in squadriglia e su cosa vedono i genitori",
        "Correzioni ai dati di BuonaStrada",
        "Account, dispositivi e inviti",
        "Iscrizioni dall'app e moduli firmati caricati",
        "Iscrizioni agli eventi su BuonaCaccia: liberatorie, risposte, foto e presentazione "
        "(le quote restano)",
        "Progressione personale: tappe e passi, Promessa, Carta di clan, mete, obiettivi e "
        "impegni, Punti della Strada, specialità e brevetti, posti d'azione nelle imprese, "
        "sintesi dei passaggi di branca",
        "Storico delle modifiche di questi dati",
    ]
    if motivo is None:
        voci.append(
            "Nome, codice fiscale, contatti e gli altri dati anagrafici (restano solo "
            "i periodi nelle unità, senza nome)"
        )
    return {"anonimizza": motivo is None, "motivo_anagrafica": motivo, "voci": voci}


def _cancella_storico(oggetti) -> None:
    for oggetto in oggetti:
        LogEntry.objects.get_for_object(oggetto).delete()


@transaction.atomic
def cancella(persona: Persona) -> dict:
    """Erase the app-only data of `persona`; anonymise an ex member. Returns what was
    done (the preview). The audit history of the erased data goes too: it holds their
    values. The access log stays (accountability), pointing to the anonymised record."""
    esito = anteprima_cancellazione(persona)
    with disable_auditlog():
        sanitarie = InformazioniSanitarie.objects.filter(persona=persona).first()
        if sanitarie is not None:
            _cancella_storico([*sanitarie.allergie.all(), *sanitarie.farmaci.all(), sanitarie])
            sanitarie.delete()
        reperibilita = list(ReperibilitaEvento.objects.filter(persona=persona))
        _cancella_storico(reperibilita)
        for r in reperibilita:
            r.delete()
        for modello in (
            DerogaSquadriglia,
            CorrezioneAnagrafica,
            VisibilitaGenitori,
            PreferenzeEmail,
            Invito,
        ):
            oggetti = list(modello.objects.filter(persona=persona))
            _cancella_storico(oggetti)
            for oggetto in oggetti:
                oggetto.delete()
        for iscrizione in _iscrizioni_bc(persona):
            from apps.buonacaccia.servizi import elimina

            _cancella_storico([iscrizione])
            elimina(iscrizione)
        _cancella_progressione(persona)
        iscrizioni = list(RichiestaIscrizione.objects.filter(persona=persona))
        for richiesta in iscrizioni:
            allegati = list(richiesta.allegati.all())
            _cancella_storico([*allegati, richiesta])
            for allegato in allegati:
                allegato.file.delete(save=False)
            richiesta.delete()
        if persona.utente_id:
            utente = persona.utente
            persona.utente = None
            persona.save(update_fields=["utente"])
            _cancella_storico([utente])
            utente.delete()  # devices and sessions go with it
        persona.telefono_squadriglia_da = None
        persona.telefono_squadriglia_nascosto = False
        persona.telefono_per_i_figli = False
        if esito["anonimizza"]:
            for campo in CAMPI_BUONASTRADA:
                field = Persona._meta.get_field(campo)
                setattr(persona, campo, None if field.null else "")
            persona.nome = "Persona"
            persona.cognome = f"cancellata n. {persona.pk}"
            persona.codice_socio = None
            tutele = list(RelazioneTutela.objects.filter(tutore=persona)) + list(
                RelazioneTutela.objects.filter(minore=persona)
            )
            # Their history names the person: it goes; the periods themselves stay.
            _cancella_storico(
                [
                    persona,
                    *tutele,
                    *Appartenenza.objects.filter(persona=persona),
                    *persona.appartenenze_squadriglia.all(),
                    *Incarico.objects.filter(persona=persona),
                ]
            )
            for tutela in tutele:
                tutela.delete()
        persona.save()
    return esito
