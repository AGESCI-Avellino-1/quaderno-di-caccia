"""Registration requests: creation, approval, rejection (maintainer, 2026-10-29)."""

from dataclasses import dataclass
from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.anagrafica.models import (
    Appartenenza,
    Persona,
    RelazioneTutela,
    RuoloAppartenenza,
    TipoTutela,
)
from apps.anagrafica.servizi import nuovo_codice_provvisorio
from apps.core.anno import eta_in_data
from apps.core.models import FonteDato
from apps.organizzazione.models import TipoUnita

from .models import CodiceIscrizione, RichiestaIscrizione, StatoIscrizione

# The request of someone without an account yet waits here until sign-up.
CHIAVE_SESSIONE_ISCRIZIONE = "qdc_iscrizione"


@dataclass
class DatiIscrizione:
    nome: str
    cognome: str
    data_nascita: date
    codice_fiscale: str
    email: str = ""
    genitore_nome: str = ""
    genitore_cognome: str = ""
    genitore_codice_fiscale: str = ""

    def pulisci(self) -> DatiIscrizione:
        return DatiIscrizione(
            nome=self.nome.strip(),
            cognome=self.cognome.strip(),
            data_nascita=self.data_nascita,
            codice_fiscale=self.codice_fiscale.strip().upper(),
            email=self.email.strip().lower(),
            genitore_nome=self.genitore_nome.strip(),
            genitore_cognome=self.genitore_cognome.strip(),
            genitore_codice_fiscale=self.genitore_codice_fiscale.strip().upper(),
        )


def prepara(codice: CodiceIscrizione, dati: DatiIscrizione) -> RichiestaIscrizione:
    """A validated, unsaved request (ValidationError otherwise)."""
    if not codice.valido:
        raise ValidationError("Il codice di iscrizione non è più valido.")
    richiesta = RichiestaIscrizione(codice=codice, unita=codice.unita, **vars(dati.pulisci()))
    richiesta.full_clean(exclude=["utente", "persona"])
    gia = Appartenenza.objects.attive().filter(
        unita=codice.unita, persona__codice_fiscale=richiesta.codice_fiscale
    )
    if gia.exists():
        raise ValidationError("Questa persona fa già parte dell'unità.")
    return richiesta


@transaction.atomic
def crea_richiesta(codice: CodiceIscrizione, dati: DatiIscrizione, utente) -> RichiestaIscrizione:
    codice = CodiceIscrizione.objects.select_for_update().get(pk=codice.pk)
    # An adult joins with their own account: its address is theirs. A child never gets
    # the parent's address (every account has its own email).
    minore = eta_in_data(dati.data_nascita, timezone.localdate()) < 18
    if not minore:
        dati = DatiIscrizione(**{**vars(dati), "email": utente.email})
    richiesta = prepara(codice, dati)
    richiesta.utente = utente
    richiesta.save()
    CodiceIscrizione.objects.filter(pk=codice.pk).update(usi=F("usi") + 1)
    return richiesta


def _persona(nome: str, cognome: str, codice_fiscale: str, **altri) -> Persona:
    """The person with this codice fiscale if the app has them (an ex member, a parent
    of another member), else a new one."""
    persona = Persona.objects.filter(codice_fiscale=codice_fiscale).first()
    if persona is None:
        persona = Persona.objects.create(
            nome=nome, cognome=cognome, codice_fiscale=codice_fiscale, **altri
        )
    return persona


@transaction.atomic
def approva(richiesta: RichiestaIscrizione, utente, scadenza: date) -> Persona:
    """The member enters the unit with a provisional codice socio; the family completes
    the data and the forms by `scadenza`."""
    if richiesta.stato != StatoIscrizione.IN_ATTESA:
        raise ValidationError("Questa richiesta è già stata decisa.")
    if scadenza < date.today():
        raise ValidationError("La scadenza per completare non può essere nel passato.")
    socio = _persona(
        richiesta.nome,
        richiesta.cognome,
        richiesta.codice_fiscale,
        data_nascita=richiesta.data_nascita,
        email=richiesta.email,
    )
    if not socio.codice_socio:
        socio.codice_socio = nuovo_codice_provvisorio()
        socio.save(update_fields=["codice_socio", "aggiornato_il"])
    account = richiesta.utente
    if richiesta.per_minore:
        genitore = _persona(
            richiesta.genitore_nome,
            richiesta.genitore_cognome,
            richiesta.genitore_codice_fiscale,
            email=account.email if account else "",
        )
        RelazioneTutela.objects.get_or_create(
            tutore=genitore, minore=socio, defaults={"tipo": TipoTutela.GENITORE}
        )
        titolare = genitore
    else:
        titolare = socio
    libero = account is not None and not Persona.objects.filter(utente=account).exists()
    if libero and titolare.utente_id is None:
        titolare.utente = account
        titolare.save(update_fields=["utente", "aggiornato_il"])
    unita = richiesta.unita
    ruolo = (
        RuoloAppartenenza.CAPO
        if unita.tipo == TipoUnita.COMUNITA_CAPI
        else RuoloAppartenenza.RAGAZZO
    )
    if not Appartenenza.objects.attive().filter(persona=socio, unita=unita).exists():
        Appartenenza.objects.create(
            persona=socio,
            unita=unita,
            ruolo=ruolo,
            data_inizio=timezone.localdate(),
            fonte=FonteDato.APP,
        )
    richiesta.stato = StatoIscrizione.APPROVATA
    richiesta.persona = socio
    richiesta.decisa_il = timezone.now()
    richiesta.decisa_da = utente
    richiesta.scadenza_completamento = scadenza
    richiesta.save()
    _scrivi(
        richiesta,
        "Iscrizione accolta",
        f"l'iscrizione di {richiesta.nome} a {unita} è stata accolta.\n\n"
        f"Entro il {scadenza.strftime('%d/%m/%Y')} completa i dati e carica i moduli "
        f"firmati dall'app:\n{settings.FRONTEND_URL}/mia-iscrizione\n",
    )
    return socio


@transaction.atomic
def rifiuta(richiesta: RichiestaIscrizione, utente, motivo: str) -> None:
    if richiesta.stato != StatoIscrizione.IN_ATTESA:
        raise ValidationError("Questa richiesta è già stata decisa.")
    if not motivo.strip():
        raise ValidationError("Scrivi il motivo: lo legge chi ha chiesto l'iscrizione.")
    richiesta.stato = StatoIscrizione.RIFIUTATA
    richiesta.motivo_rifiuto = motivo.strip()
    richiesta.decisa_il = timezone.now()
    richiesta.decisa_da = utente
    richiesta.save()
    _scrivi(
        richiesta,
        "Iscrizione non accolta",
        f"l'iscrizione di {richiesta.nome} a {richiesta.unita} non è stata accolta:\n"
        f"{richiesta.motivo_rifiuto}\n\nPer chiarimenti rivolgiti ai capi dell'unità.\n",
    )


def _scrivi(richiesta: RichiestaIscrizione, oggetto: str, testo: str) -> None:
    if richiesta.utente is None or not richiesta.utente.email:
        return
    send_mail(
        subject=f"Quaderno di Caccia: {oggetto}",
        message=f"Ciao,\n\n{testo}",
        from_email=None,
        recipient_list=[richiesta.utente.email],
    )


def in_sessione(request) -> tuple[CodiceIscrizione, DatiIscrizione] | None:
    """The code and data kept in this browser session, if still valid."""
    salvata = request.session.get(CHIAVE_SESSIONE_ISCRIZIONE) if request else None
    if not salvata:
        return None
    codice = CodiceIscrizione.objects.filter(codice=salvata["codice"]).first()
    if codice is None or not codice.valido:
        return None
    dati = dict(salvata["dati"], data_nascita=date.fromisoformat(salvata["dati"]["data_nascita"]))
    return codice, DatiIscrizione(**dati)


def richiesta_da_sessione(request, utente) -> RichiestaIscrizione | None:
    """Sign-up through a registration code: the waiting request becomes real."""
    salvata = in_sessione(request)
    if salvata is None:
        return None
    request.session.pop(CHIAVE_SESSIONE_ISCRIZIONE, None)
    try:
        return crea_richiesta(*salvata, utente)
    except ValidationError:
        return None  # e.g. the code was used meanwhile: the account stays, without request
