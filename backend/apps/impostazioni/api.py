"""Settings of the installation (DEC-245…DEC-248)."""

from django.conf import settings
from django.core.exceptions import ValidationError
from ninja import Router, Schema
from ninja.errors import HttpError

from apps.core.anno import AnnoAssociativo
from apps.permessi import policy

from .models import Impostazioni, ModelloEmail

router = Router(tags=["impostazioni"])


class SitoOut(Schema):
    """What every page needs to write its title and footer, also before the login."""

    nome_sito: str
    sigla_sito: str
    gruppo: str
    sigla_gruppo: str
    anno: str
    titolo_completo: str
    titolo_breve: str
    riga_piede: str
    # Emails go to Mailpit: every page says so, the login page too (DEC-249).
    email_di_prova: bool


def _sito() -> dict:
    imp = Impostazioni.carica()
    return {
        "nome_sito": imp.nome_sito,
        "sigla_sito": imp.sigla_sito,
        "gruppo": imp.nome_del_gruppo(),
        "sigla_gruppo": imp.sigla_gruppo,
        "anno": AnnoAssociativo.corrente().etichetta,
        "titolo_completo": imp.titolo_completo,
        "titolo_breve": imp.titolo_breve,
        "riga_piede": imp.riga_piede,
        "email_di_prova": imp.email_di_prova_attiva(),
    }


@router.get("/sito", response=SitoOut, auth=None)
def sito(request):
    return _sito()


class ImpostazioniSitoIO(Schema):
    nome_sito: str
    sigla_sito: str = ""
    nome_gruppo: str = ""
    sigla_gruppo: str = ""
    titolo_completo: str
    titolo_breve: str
    riga_piede: str = ""


class ImpostazioniOut(ImpostazioniSitoIO):
    # The group's name when `nome_gruppo` is empty.
    gruppo_predefinito: str
    puo_modificare: bool
    puo_modificare_intestazione: bool
    puo_modificare_pagamenti: bool
    # Email test mode (DEC-249): on, possible on this server, who may switch it.
    email_di_prova: bool
    email_di_prova_consentita: bool
    puo_email_di_prova: bool


CAMPI_SITO = list(ImpostazioniSitoIO.model_fields)


def _impostazioni(request) -> dict:
    imp = Impostazioni.carica()
    predefinito = Impostazioni(nome_gruppo="").nome_del_gruppo()
    return {
        **{c: getattr(imp, c) for c in CAMPI_SITO},
        "gruppo_predefinito": predefinito,
        "puo_modificare": policy.puo_modificare_impostazioni(request.auth),
        "puo_modificare_intestazione": policy.e_capogruppo(request.auth),
        "puo_modificare_pagamenti": policy.puo_gestire_quote(request.auth),
        "email_di_prova": imp.email_di_prova_attiva(),
        "email_di_prova_consentita": settings.QDC_MAILPIT_CONSENTITO,
        "puo_email_di_prova": policy.puo_gestire_email_di_prova(request.auth),
    }


@router.get("/impostazioni", response=ImpostazioniOut)
def impostazioni(request):
    if not policy.vede_impostazioni(request.auth):
        raise HttpError(403, "Le impostazioni le cambiano i capigruppo.")
    return _impostazioni(request)


@router.put("/impostazioni/sito", response=ImpostazioniOut)
def salva_sito(request, dati: ImpostazioniSitoIO):
    if not policy.puo_modificare_impostazioni(request.auth):
        raise HttpError(403, "Le impostazioni le cambiano i capigruppo.")
    imp = Impostazioni.carica()
    for campo in CAMPI_SITO:
        setattr(imp, campo, " ".join(getattr(dati, campo).split()))
    try:
        imp.full_clean()
    except ValidationError as errore:
        raise HttpError(400, " ".join(errore.messages)) from errore
    imp.save()
    return _impostazioni(request)


class EmailDiProvaIn(Schema):
    attiva: bool


@router.put("/impostazioni/email-di-prova", response=ImpostazioniOut)
def email_di_prova(request, dati: EmailDiProvaIn):
    if not policy.puo_gestire_email_di_prova(request.auth):
        raise HttpError(403, "La modalità di prova delle email la usa l'amministratore tecnico.")
    if dati.attiva and not settings.QDC_MAILPIT_CONSENTITO:
        raise HttpError(
            400,
            "Su questo server la modalità di prova delle email non è permessa: la attiva "
            "chi lo installa.",
        )
    imp = Impostazioni.carica()
    imp.email_di_prova = dati.attiva
    imp.save(update_fields=["email_di_prova", "aggiornato_il"])
    return _impostazioni(request)


# --- Email templates (DEC-250) --------------------------------------------------------------


class SegnapostoOut(Schema):
    nome: str
    descrizione: str
    indispensabile: bool


class ModelloEmailBreve(Schema):
    chiave: str
    nome: str
    descrizione: str
    personalizzato: bool
    # A personalised template that lacks something indispensable: the default is used.
    da_correggere: bool


class ModelloEmailOut(ModelloEmailBreve):
    oggetto: str
    corpo: str
    oggetto_predefinito: str
    corpo_predefinito: str
    segnaposto: list[SegnapostoOut]
    facoltativa: bool


class ModelloEmailIn(Schema):
    oggetto: str
    corpo: str


class AnteprimaOut(Schema):
    oggetto: str
    html: str
    testo: str


def _gestore_modelli(request) -> None:
    if not policy.puo_modificare_impostazioni(request.auth):
        raise HttpError(403, "I modelli delle email li cambiano i capigruppo.")


def _tipo(chiave: str):
    from . import email

    try:
        return email.tipo(chiave)
    except KeyError as errore:
        raise HttpError(404, "Email non trovata.") from errore


def _breve(t, salvato) -> dict:
    from . import email

    return {
        "chiave": t.chiave,
        "nome": t.nome,
        "descrizione": t.descrizione,
        "personalizzato": salvato is not None,
        "da_correggere": bool(salvato and email.mancanti(t, salvato.oggetto, salvato.corpo)),
    }


def _modello_out(t) -> dict:
    from . import email

    salvato = ModelloEmail.objects.filter(chiave=t.chiave).first()
    return {
        **_breve(t, salvato),
        "oggetto": salvato.oggetto if salvato else t.oggetto,
        "corpo": salvato.corpo if salvato else t.corpo,
        "oggetto_predefinito": t.oggetto,
        "corpo_predefinito": t.corpo,
        "segnaposto": [
            {"nome": s.nome, "descrizione": s.descrizione, "indispensabile": s.indispensabile}
            for s in email.segnaposto_di(t)
        ],
        "facoltativa": t.facoltativa,
    }


@router.get("/impostazioni/email", response=list[ModelloEmailBreve])
def modelli_email(request):
    from . import email

    _gestore_modelli(request)
    salvati = {m.chiave: m for m in ModelloEmail.objects.all()}
    return [_breve(t, salvati.get(t.chiave)) for t in email.tutti()]


@router.get("/impostazioni/email/{chiave}", response=ModelloEmailOut)
def modello_email(request, chiave: str):
    _gestore_modelli(request)
    return _modello_out(_tipo(chiave))


@router.put("/impostazioni/email/{chiave}", response=ModelloEmailOut)
def salva_modello_email(request, chiave: str, dati: ModelloEmailIn):
    from . import email
    from .html import pulisci

    _gestore_modelli(request)
    t = _tipo(chiave)
    oggetto = " ".join(dati.oggetto.split())
    corpo = pulisci(dati.corpo)
    errori = email.problemi(t, oggetto, corpo)
    if errori:
        raise HttpError(400, " ".join(errori))
    ModelloEmail.objects.update_or_create(
        chiave=t.chiave,
        defaults={
            "oggetto": oggetto,
            "corpo": corpo,
            "modificato_da": request.auth,
            "avvisato_il": None,
        },
    )
    return _modello_out(t)


@router.delete("/impostazioni/email/{chiave}", response=ModelloEmailOut)
def ripristina_modello_email(request, chiave: str):
    _gestore_modelli(request)
    t = _tipo(chiave)
    ModelloEmail.objects.filter(chiave=t.chiave).delete()
    return _modello_out(t)


@router.post("/impostazioni/email/{chiave}/anteprima", response=AnteprimaOut)
def anteprima_modello_email(request, chiave: str, dati: ModelloEmailIn):
    """The email as it would arrive, with example values; nothing is saved."""
    from . import email

    _gestore_modelli(request)
    t = _tipo(chiave)
    esempi = {s.nome: s.esempio for s in t.segnaposto}
    composta = email.componi_da(t, dati.oggetto, dati.corpo, esempi)
    return {"oggetto": composta.oggetto, "html": composta.html, "testo": composta.testo}
