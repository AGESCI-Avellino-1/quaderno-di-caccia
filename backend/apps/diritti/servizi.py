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
from apps.anagrafica.servizi import come_testo
from apps.dispositivi.models import Dispositivo
from apps.organizzazione.models import Incarico
from apps.permessi.models import AccessoDatoSensibile
from apps.sanitaria.models import InformazioniSanitarie

from .models import RichiestaDiritti


def _periodo(oggetto) -> dict:
    return {"dal": come_testo(oggetto.data_inizio), "al": come_testo(oggetto.data_fine)}


def fascicolo(persona: Persona) -> dict:
    """Everything the app holds about `persona`, in plain words where it helps."""
    utente = persona.utente
    sanitarie = InformazioniSanitarie.objects.filter(persona=persona).first()
    visibilita = VisibilitaGenitori.objects.filter(persona=persona).first()
    return {
        "generato_il": timezone.now().isoformat(),
        "anagrafica": {
            ETICHETTE_CAMPI[campo]: come_testo(getattr(persona, campo))
            for campo in CAMPI_BUONASTRADA
        }
        | {"Codice socio": persona.codice_socio or ""},
        "account": (
            {
                "Email di accesso": utente.email,
                "Creato il": come_testo(utente.date_joined.date()),
                "Ultimo accesso": come_testo(utente.last_login and utente.last_login.date()),
                "Dispositivi": [
                    {
                        "nome": d.nome,
                        "ultimo_contatto": come_testo(d.ultimo_contatto.date()),
                        "scollegato_il": come_testo(d.revocato_il and d.revocato_il.date()),
                    }
                    for d in Dispositivo.objects.filter(utente=utente)
                ],
            }
            if utente
            else None
        ),
        "genitori_e_tutori": [
            {"nome": f"{r.tutore.nome} {r.tutore.cognome}", "relazione": r.get_tipo_display()}
            for r in RelazioneTutela.objects.filter(minore=persona).select_related("tutore")
        ],
        "figli_o_tutelati": [
            {"nome": f"{r.minore.nome} {r.minore.cognome}", "relazione": r.get_tipo_display()}
            for r in RelazioneTutela.objects.filter(tutore=persona).select_related("minore")
        ],
        "unita": [
            {"unita": str(a.unita), "ruolo": a.get_ruolo_display()} | _periodo(a)
            for a in Appartenenza.objects.filter(persona=persona).select_related("unita")
        ],
        "squadriglie": [
            {"squadriglia": str(a.squadriglia)} | _periodo(a)
            for a in persona.appartenenze_squadriglia.select_related("squadriglia")
        ],
        "incarichi": [
            {"incarico": i.get_ruolo_display(), "dove": str(i.unita or i.squadriglia or i.gruppo)}
            | _periodo(i)
            for i in Incarico.objects.filter(persona=persona).select_related(
                "unita", "squadriglia", "gruppo"
            )
        ],
        "telefono_in_squadriglia": {
            "Numero di un genitore scelto": (
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
                        "tipo": a.get_tipo_display(),
                        "sostanza": a.sostanza,
                        "gravità": a.get_gravita_display(),
                        "reazione": a.reazione,
                        "cosa fare": a.cosa_fare,
                    }
                    for a in sanitarie.allergie.all()
                ],
                "Farmaci": [
                    {
                        "nome": f.nome,
                        "posologia": f.posologia,
                        "orari": f.orari,
                        "lo prende da solo": f.autonomo,
                        "note": f.note,
                    }
                    for f in sanitarie.farmaci.all()
                ],
                "Inserite da": sanitarie.get_inserite_da_display(),
                "Aggiornate il": come_testo(sanitarie.aggiornato_il.date()),
            }
            if sanitarie
            else None
        ),
        "eccezioni_squadriglia": [
            {
                "reparto": str(d.reparto),
                "squadriglie": d.get_sesso_squadriglia_display(),
                "decisa_il": come_testo(d.data_decisione),
                "motivazione": d.motivazione,
                "revocata_il": come_testo(d.revocata_il),
            }
            for d in DerogaSquadriglia.objects.filter(persona=persona).select_related("reparto")
        ],
        "visibilita_ai_genitori": (
            {
                "Contatti e indirizzo": visibilita.contatti,
                "Farmaci, allergie e alimentazione": visibilita.sanitarie,
                "Scheda e attività": visibilita.scheda,
                "Scelta il": come_testo(visibilita.decisa_il and visibilita.decisa_il.date()),
            }
            if visibilita and visibilita.decisa_il
            else None
        ),
        "correzioni_ai_dati": [
            {
                "dato": ETICHETTE_CAMPI.get(c.campo, c.campo),
                "prima": c.valore_precedente,
                "dopo": c.valore_corretto,
                "stato": c.get_stato_display(),
                "il": come_testo(c.creato_il.date()),
            }
            for c in CorrezioneAnagrafica.objects.filter(persona=persona)
        ],
        "inviti": [
            {
                "email": i.email,
                "creato_il": come_testo(i.creato_il.date()),
                "usato_il": come_testo(i.usato_il and i.usato_il.date()),
            }
            for i in Invito.objects.filter(persona=persona)
        ],
        "accessi_ai_dati_delicati": [
            {
                "quando": a.creato_il.isoformat(),
                "chi": a.utente.email if a.utente else "",
                "cosa": a.get_categoria_display(),
                "azione": a.get_azione_display(),
            }
            for a in AccessoDatoSensibile.objects.filter(persona=persona).select_related("utente")
        ],
        "richieste_dei_diritti": [
            {
                "tipo": r.get_tipo_display(),
                "ricevuta_il": come_testo(r.ricevuta_il),
                "evasa_il": come_testo(r.evasa_il),
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
