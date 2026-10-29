"""Registration requests: creation, approval, rejection (maintainer, 2026-10-29)."""

import uuid
from dataclasses import dataclass
from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.anagrafica.models import (
    ETICHETTE_CAMPI,
    Appartenenza,
    Persona,
    RelazioneTutela,
    RuoloAppartenenza,
    TipoTutela,
)
from apps.anagrafica.servizi import codice_fiscale_valido, nuovo_codice_provvisorio
from apps.core.anno import eta_in_data
from apps.core.models import FonteDato
from apps.organizzazione.models import TipoUnita

from .models import (
    CAMPI_CONTATTO_OBBLIGATORI,
    CAMPI_SOCIO,
    CAMPI_SOCIO_OBBLIGATORI,
    DA_COMPLETARE,
    DIMENSIONE_MASSIMA,
    NON_RECEPITE,
    AllegatoIscrizione,
    CodiceIscrizione,
    RichiestaIscrizione,
    StatoIscrizione,
    tipo_file,
)

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
    aggiorna_stato(richiesta)  # someone already known to the app may need nothing more
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


# --- Completion (maintainer, 2026-10-29) ----------------------------------------------


def genitore(richiesta: RichiestaIscrizione) -> Persona | None:
    """The parent who asked for a minor."""
    if not richiesta.per_minore:
        return None
    return Persona.objects.filter(codice_fiscale=richiesta.genitore_codice_fiscale).first()


def altro_genitore(richiesta: RichiestaIscrizione) -> Persona | None:
    """The other parent or guardian of a minor, when the family declared both."""
    chi_iscrive = genitore(richiesta)
    if richiesta.persona is None or chi_iscrive is None:
        return None
    return (
        Persona.objects.filter(tutele__minore=richiesta.persona)
        .exclude(pk=chi_iscrive.pk)
        .order_by("pk")
        .first()
    )


def _dati_mancanti(persona: Persona, campi: dict[str, str]) -> list[str]:
    return [etichetta for campo, etichetta in campi.items() if not getattr(persona, campo)]


def mancanti(richiesta: RichiestaIscrizione) -> list[str]:
    """What is still missing to complete the registration, in words."""
    socio = richiesta.persona
    if socio is None:
        return []
    voci = [ETICHETTE_CAMPI[c] for c in CAMPI_SOCIO_OBBLIGATORI if not getattr(socio, c)]
    if richiesta.contatti_obbligatori:
        voci += [ETICHETTE_CAMPI[c] for c in CAMPI_CONTATTO_OBBLIGATORI if not getattr(socio, c)]
    padre_o_madre = genitore(richiesta)
    if padre_o_madre is not None:
        voci += [
            f"{v} del genitore"
            for v in _dati_mancanti(padre_o_madre, {"cellulare": "Cellulare", "email": "Email"})
        ]
        if richiesta.genitore_unico is None:
            voci.append("Genitore singolo o entrambi i genitori")
        elif not richiesta.genitore_unico:
            altro = altro_genitore(richiesta)
            if altro is None:
                voci.append("Dati dell'altro genitore")
            else:
                voci += [
                    f"{v} dell'altro genitore"
                    for v in _dati_mancanti(
                        altro,
                        {
                            "codice_fiscale": "Codice fiscale",
                            "cellulare": "Cellulare",
                            "email": "Email",
                        },
                    )
                ]
    if not richiesta.allegati.exists():
        voci.append("Moduli firmati da caricare")
    elif richiesta.moduli_verificati_il is None:
        voci.append("Verifica dei moduli da parte dei capi")
    return voci


def aggiorna_stato(richiesta: RichiestaIscrizione) -> None:
    """Complete when nothing is missing; a suspended account is active again."""
    if richiesta.stato in DA_COMPLETARE and not mancanti(richiesta):
        richiesta.stato = StatoIscrizione.COMPLETATA
        richiesta.completata_il = timezone.now()
        richiesta.save(update_fields=["stato", "completata_il", "aggiornato_il"])


@transaction.atomic
def completa(richiesta: RichiestaIscrizione, dati: dict) -> None:
    """Write the remaining BuonaStrada data. They are not corrections: BuonaStrada has
    no record of this member yet."""
    if richiesta.stato not in DA_COMPLETARE:
        raise ValidationError("Questa iscrizione non è da completare.")
    socio = richiesta.persona
    for campo in CAMPI_SOCIO:
        if campo in dati:
            setattr(socio, campo, (dati[campo] or "").strip())
    socio.provincia = socio.provincia.upper()
    socio.email = socio.email.lower()
    padre_o_madre = genitore(richiesta)
    if padre_o_madre is not None and socio.email and socio.email == padre_o_madre.email.lower():
        raise ValidationError("L'email del ragazzo deve essere sua, non quella del genitore.")
    if socio.cap and not (socio.cap.isdigit() and len(socio.cap) == 5):
        raise ValidationError("Il CAP ha 5 cifre.")
    if socio.provincia and not (socio.provincia.isalpha() and len(socio.provincia) == 2):
        raise ValidationError("La provincia è la sigla di 2 lettere (es. AV).")
    altri = [f.name for f in Persona._meta.fields if f.name not in CAMPI_SOCIO]
    socio.full_clean(exclude=altri)
    socio.save()
    if padre_o_madre is not None:
        if "cellulare_genitore" in dati:
            padre_o_madre.cellulare = (dati["cellulare_genitore"] or "").strip()
            padre_o_madre.save(update_fields=["cellulare", "aggiornato_il"])
        if dati.get("genitore_unico") is not None:
            _genitori(
                richiesta, padre_o_madre, bool(dati["genitore_unico"]), dati.get("altro_genitore")
            )
    aggiorna_stato(richiesta)


def _genitori(richiesta, chi_iscrive: Persona, unico: bool, altro: dict | None) -> None:
    """One parent with exclusive custody, or both: as BuonaStrada records them."""
    socio = richiesta.persona
    richiesta.genitore_unico = unico
    richiesta.save(update_fields=["genitore_unico", "aggiornato_il"])
    RelazioneTutela.objects.filter(tutore=chi_iscrive, minore=socio).update(
        tipo=TipoTutela.UNICO_GENITORE if unico else TipoTutela.GENITORE
    )
    if unico or not altro:
        return
    codice_fiscale = (altro.get("codice_fiscale") or "").strip().upper()
    if not codice_fiscale_valido(codice_fiscale):
        raise ValidationError("Il codice fiscale dell'altro genitore non è valido.")
    if codice_fiscale in {chi_iscrive.codice_fiscale, socio.codice_fiscale}:
        raise ValidationError("Il codice fiscale dell'altro genitore è già usato qui.")
    nome, cognome = (altro.get("nome") or "").strip(), (altro.get("cognome") or "").strip()
    if not (nome and cognome):
        raise ValidationError("Scrivi nome e cognome dell'altro genitore.")
    precedente = altro_genitore(richiesta)
    if precedente is not None and precedente.codice_fiscale != codice_fiscale:
        RelazioneTutela.objects.filter(tutore=precedente, minore=socio).delete()
    persona = _persona(nome, cognome, codice_fiscale)
    # Contacts as given by the family, unless BuonaStrada's are there already.
    for campo in ("cellulare", "email"):
        valore = (altro.get(campo) or "").strip()
        if valore and not getattr(persona, campo):
            setattr(persona, campo, valore.lower() if campo == "email" else valore)
    persona.full_clean(exclude=[f.name for f in Persona._meta.fields if f.name not in ("email",)])
    persona.save()
    RelazioneTutela.objects.get_or_create(
        tutore=persona, minore=socio, defaults={"tipo": TipoTutela.GENITORE}
    )


def persone_sospese(utente) -> set[int]:
    """Members whose registration from this account passed its deadline incomplete:
    the family no longer sees them until it completes (maintainer, 2026-10-29)."""
    return set(
        RichiestaIscrizione.objects.filter(
            utente=utente, stato=StatoIscrizione.SOSPESA, persona__isnull=False
        ).values_list("persona_id", flat=True)
    )


# --- Signed forms --------------------------------------------------------------------

CONSENSI = ("consenso_iscrizione", "consenso_foto", "consenso_commerciale", "consenso_riviste")


def carica_allegato(richiesta: RichiestaIscrizione, file, utente) -> AllegatoIscrizione:
    """A scan of a signed form: PDF, JPEG or PNG up to 10 MB, checked on its first bytes.
    Stored under a random name: the original name may contain the person's."""
    if richiesta.stato not in DA_COMPLETARE:
        raise ValidationError("I moduli si caricano finché l'iscrizione è da completare.")
    if file.size > DIMENSIONE_MASSIMA:
        raise ValidationError("Il file è troppo grande: al massimo 10 MB.")
    tipo = tipo_file(file.read(8))
    file.seek(0)
    if tipo is None:
        raise ValidationError("Carica un PDF o una foto (JPEG o PNG).")
    estensione = {"application/pdf": ".pdf", "image/jpeg": ".jpg", "image/png": ".png"}[tipo]
    nome_originale = (file.name or "modulo")[-200:]
    file.name = f"{uuid.uuid4().hex}{estensione}"
    allegato = AllegatoIscrizione.objects.create(
        richiesta=richiesta,
        file=file,
        nome_file=nome_originale,
        tipo_contenuto=tipo,
        caricato_da=utente,
    )
    if richiesta.moduli_verificati_il is not None:  # a new form needs a new check
        richiesta.moduli_verificati_il = None
        richiesta.moduli_verificati_da = None
        richiesta.save(update_fields=["moduli_verificati_il", "moduli_verificati_da"])
    return allegato


def togli_allegato(allegato: AllegatoIscrizione) -> None:
    richiesta = allegato.richiesta
    if richiesta.stato not in DA_COMPLETARE or richiesta.moduli_verificati_il is not None:
        raise ValidationError("I moduli già verificati non si tolgono.")
    allegato.file.delete(save=False)
    allegato.delete()


@transaction.atomic
def verifica_moduli(richiesta: RichiestaIscrizione, utente, consensi: dict[str, bool]) -> None:
    """A capo checked the signed forms: the consents go on the member (BuonaStrada has
    no record of them yet); only then the forms count as done."""
    if richiesta.stato not in DA_COMPLETARE:
        raise ValidationError("Questa iscrizione non è da completare.")
    if not richiesta.allegati.exists():
        raise ValidationError("Non ci sono moduli caricati da verificare.")
    socio = richiesta.persona
    for campo in CONSENSI:
        setattr(socio, campo, bool(consensi.get(campo, False)))
    socio.save(update_fields=[*CONSENSI, "aggiornato_il"])
    richiesta.moduli_verificati_il = timezone.now()
    richiesta.moduli_verificati_da = utente
    richiesta.save(update_fields=["moduli_verificati_il", "moduli_verificati_da", "aggiornato_il"])
    aggiorna_stato(richiesta)


# --- Into BuonaStrada ------------------------------------------------------------------


def segna_inserita(richiesta: RichiestaIscrizione, utente) -> None:
    """A capogruppo entered the member in BuonaStrada (by hand, on its portal)."""
    if richiesta.stato != StatoIscrizione.COMPLETATA:
        raise ValidationError("Si segnano come inserite solo le iscrizioni complete.")
    richiesta.stato = StatoIscrizione.INSERITA
    richiesta.inserita_il = timezone.now()
    richiesta.inserita_da = utente
    richiesta.save(update_fields=["stato", "inserita_il", "inserita_da", "aggiornato_il"])


def recepisci(persona: Persona) -> list[RichiestaIscrizione]:
    """The import found the member in BuonaStrada (by codice fiscale): BuonaStrada wins,
    the registration is closed whatever its state, a suspended account is active again."""
    richieste = list(RichiestaIscrizione.objects.filter(persona=persona, stato__in=NON_RECEPITE))
    for richiesta in richieste:
        richiesta.stato = StatoIscrizione.RECEPITA
        richiesta.recepita_il = timezone.now()
        richiesta.save(update_fields=["stato", "recepita_il", "aggiornato_il"])
    return richieste


COLONNE = (
    "Codice provvisorio",
    "Cognome",
    "Nome",
    "Sesso",
    "Data di nascita",
    "Luogo di nascita",
    "Codice fiscale",
    "Indirizzo",
    "Comune",
    "Provincia",
    "CAP",
    "Email",
    "Cellulare",
    "Unità",
    "Consensi 2A/2B/2C/riviste",
    "Genitore",
    "Codice fiscale del genitore",
    "Email del genitore",
    "Cellulare del genitore",
    "Stato",
)


def _si_no(valore) -> str:
    return {True: "sì", False: "no"}.get(valore, "—")


def riga_per_buonastrada(richiesta: RichiestaIscrizione) -> list[str]:
    """The data to copy into BuonaStrada, in plain text."""
    s = richiesta.persona
    g = genitore(richiesta)
    consensi = "/".join(_si_no(getattr(s, c)) for c in CONSENSI)
    return [
        s.codice_socio or "",
        s.cognome,
        s.nome,
        s.sesso,
        s.data_nascita.strftime("%d/%m/%Y") if s.data_nascita else "",
        s.luogo_nascita,
        s.codice_fiscale or "",
        f"{s.indirizzo} {s.civico}".strip(),
        s.comune,
        s.provincia,
        s.cap,
        s.email,
        s.cellulare,
        str(richiesta.unita),
        consensi,
        f"{g.nome} {g.cognome}" if g else "",
        (g.codice_fiscale or "") if g else "",
        g.email if g else "",
        g.cellulare if g else "",
        richiesta.get_stato_display(),
    ]
