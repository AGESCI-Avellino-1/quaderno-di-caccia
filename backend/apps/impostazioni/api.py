"""Settings of the installation (DEC-245…DEC-248)."""

from django.core.exceptions import ValidationError
from ninja import Router, Schema
from ninja.errors import HttpError

from apps.core.anno import AnnoAssociativo
from apps.permessi import policy

from .models import Impostazioni

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
