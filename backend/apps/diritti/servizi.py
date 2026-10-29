"""Full export and erasure of a person's data (DEC-102; maintainer, 2026-10-29).

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
    RelazioneTutela,
    VisibilitaGenitori,
)
from apps.anagrafica.servizi import come_testo, telefono_in_squadriglia
from apps.dispositivi.models import Dispositivo
from apps.iscrizioni.models import RichiestaIscrizione
from apps.organizzazione.models import Incarico
from apps.permessi.models import AccessoDatoSensibile
from apps.sanitaria.models import InformazioniSanitarie

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
                "Inserite da": sanitarie.get_inserite_da_display(),
                "Aggiornate il": _giorno(sanitarie.aggiornato_il),
            }
            if sanitarie
            else None
        ),
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
                "Scelta il": _giorno(visibilita.decisa_il),
            }
            if visibilita and visibilita.decisa_il
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
        "richieste_dei_diritti": [
            {
                "Tipo": r.get_tipo_display(),
                "Ricevuta il": come_testo(r.ricevuta_il),
                "Chiusa il": come_testo(r.evasa_il),
            }
            for r in RichiestaDiritti.objects.filter(persona=persona)
        ],
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
        for modello in (DerogaSquadriglia, CorrezioneAnagrafica, VisibilitaGenitori, Invito):
            oggetti = list(modello.objects.filter(persona=persona))
            _cancella_storico(oggetti)
            for oggetto in oggetti:
                oggetto.delete()
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
