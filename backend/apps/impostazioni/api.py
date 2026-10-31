"""Settings of the installation (DEC-245…DEC-248, DEC-266)."""

import re
from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import FileResponse
from django.utils import timezone
from ninja import File, Router, Schema, UploadedFile
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
    # When the privacy policy changed: the cookie banner shows again (DEC-266).
    privacy_aggiornata_il: str = ""


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
        "privacy_aggiornata_il": (
            imp.privacy_aggiornata_il.isoformat() if imp.privacy_aggiornata_il else ""
        ),
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
    # The common footer is added to this email (DEC-250).
    con_piede: bool = True
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
        "con_piede": t.chiave not in Impostazioni.carica().email_senza_piede,
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
    html, testo = composta.html, composta.testo
    piede_html, piede_testo = email.piede(t.chiave)
    if piede_html:
        html += f"<hr>{piede_html}"
        testo += f"\n-- \n{piede_testo}\n"
    return {"oggetto": composta.oggetto, "html": html, "testo": testo}


class AttivoIn(Schema):
    attivo: bool


@router.put("/impostazioni/email/{chiave}/piede", response=ModelloEmailOut)
def piede_del_modello(request, chiave: str, dati: AttivoIn):
    """Whether this email gets the common footer (DEC-250)."""
    _gestore_modelli(request)
    t = _tipo(chiave)
    imp = Impostazioni.carica()
    senza = [c for c in imp.email_senza_piede if c != t.chiave]
    imp.email_senza_piede = senza if dati.attivo else [*senza, t.chiave]
    imp.save(update_fields=["email_senza_piede", "aggiornato_il"])
    return _modello_out(t)


class PiedeEmail(Schema):
    html: str
    # Empty: derived from the HTML.
    testo: str = ""


class PiedeEmailOut(PiedeEmail):
    segnaposto: list[str]
    anteprima_html: str
    anteprima_testo: str


def _piede_out() -> dict:
    from . import email
    from .html import in_testo

    imp = Impostazioni.carica()
    comuni = email._comuni()
    html = email._riempi_html(imp.piede_email, comuni, set()) if imp.piede_email else ""
    testo = email.piede("")[1] if imp.piede_email else ""
    return {
        "html": imp.piede_email,
        "testo": imp.piede_email_testo,
        "segnaposto": [s.nome for s in email.COMUNI],
        "anteprima_html": html,
        "anteprima_testo": testo or (in_testo(html) if html else ""),
    }


@router.get("/impostazioni/email-piede", response=PiedeEmailOut)
def piede_email(request):
    _gestore_modelli(request)
    return _piede_out()


@router.put("/impostazioni/email-piede", response=PiedeEmailOut)
def salva_piede_email(request, dati: PiedeEmail):
    from . import email
    from . import segnaposto as sp
    from .html import pulisci

    _gestore_modelli(request)
    html = pulisci(dati.html)
    ammessi = tuple(s.nome for s in email.COMUNI)
    ignoti = sp.sconosciuti(re.sub(r"<[^>]*>", " ", html) + " " + dati.testo, ammessi)
    if ignoti:
        raise HttpError(400, "Segnaposto sconosciuto: " + ", ".join(f"[{n}]" for n in ignoti) + ".")
    imp = Impostazioni.carica()
    vuoto = not re.sub(r"<[^>]*>", "", html).strip() and "<img" not in html
    imp.piede_email = "" if vuoto else html
    imp.piede_email_testo = dati.testo.strip()
    imp.save(update_fields=["piede_email", "piede_email_testo", "aggiornato_il"])
    return _piede_out()


# --- Images for the emails and the pages (DEC-250) ------------------------------------------


class ImmagineOut(Schema):
    url: str


@router.post("/impostazioni/immagini", response=ImmagineOut)
def carica_immagine(request, file: File[UploadedFile]):
    """PNG or JPEG, re-encoded without metadata, at most 1200 px wide and 1 MB."""
    import io
    import secrets

    from django.core.files.base import ContentFile
    from PIL import Image, UnidentifiedImageError

    from .models import ImmagineEmail

    _gestore_modelli(request)
    if file.size > 10 * 1024 * 1024:
        raise HttpError(400, "L'immagine è troppo grande: al massimo 10 MB.")
    try:
        immagine = Image.open(file)
        immagine.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as errore:
        raise HttpError(400, "Carica un'immagine PNG o JPEG.") from errore
    immagine.thumbnail((1200, 1200))
    trasparente = immagine.mode in ("RGBA", "LA", "P")
    buffer = io.BytesIO()
    if trasparente:
        immagine.convert("RGBA").save(buffer, "PNG", optimize=True)
        tipo, estensione = "image/png", "png"
    else:
        immagine.convert("RGB").save(buffer, "JPEG", quality=85, optimize=True)
        tipo, estensione = "image/jpeg", "jpg"
    if buffer.tell() > 1024 * 1024:
        raise HttpError(400, "L'immagine resta sopra 1 MB anche ridotta: usane una più leggera.")
    nuova = ImmagineEmail(tipo=tipo, caricata_da=request.auth)
    nuova.file.save(
        f"{secrets.token_hex(16)}.{estensione}", ContentFile(buffer.getvalue()), save=True
    )
    return {"url": f"/api/v1/immagini/{nuova.nome}"}


@router.get("/immagini/{nome}", auth=None)
def immagine(request, nome: str):
    """Logos and the like for the emails and the public pages: public by design."""
    from .models import ImmagineEmail

    trovata = ImmagineEmail.objects.filter(file__endswith=f"/{nome}").first()
    if trovata is None or "/" in nome:
        raise HttpError(404, "Immagine non trovata.")
    return FileResponse(trovata.file.open("rb"), content_type=trovata.tipo)


# --- Privacy policy and terms (DEC-266) -----------------------------------------------------


class PaginaOut(Schema):
    titolo: str
    html: str
    aggiornata_il: date | None


def _pagina(chiave: str):
    from .pagine import PAGINE

    pagina = PAGINE.get(chiave)
    if pagina is None:
        raise HttpError(404, "Pagina non trovata.")
    return pagina


@router.get("/pagine/{chiave}", response=PaginaOut, auth=None)
def pagina_pubblica(request, chiave: str):
    from .pagine import riempi, valori

    pagina = _pagina(chiave)
    imp = Impostazioni.carica()
    testo = getattr(imp, pagina.campo) or pagina.base
    return {
        "titolo": pagina.titolo,
        "html": riempi(testo, valori()),
        "aggiornata_il": getattr(imp, pagina.campo_data),
    }


class PaginaModificaOut(Schema):
    titolo: str
    testo: str
    base: str
    personalizzata: bool
    segnaposto: list[str]


class PaginaIn(Schema):
    testo: str


def _pagina_modifica(pagina) -> dict:
    from .pagine import SEGNAPOSTO_PAGINE

    imp = Impostazioni.carica()
    salvato = getattr(imp, pagina.campo)
    return {
        "titolo": pagina.titolo,
        "testo": salvato or pagina.base,
        "base": pagina.base,
        "personalizzata": bool(salvato),
        "segnaposto": list(SEGNAPOSTO_PAGINE),
    }


@router.get("/impostazioni/pagine/{chiave}", response=PaginaModificaOut)
def pagina_da_modificare(request, chiave: str):
    if not policy.puo_modificare_impostazioni(request.auth):
        raise HttpError(403, "Privacy policy e termini li cambiano i capigruppo.")
    return _pagina_modifica(_pagina(chiave))


def _salva_pagina(pagina, testo: str) -> None:
    imp = Impostazioni.carica()
    setattr(imp, pagina.campo, testo)
    setattr(imp, pagina.campo_data, timezone.localdate())
    imp.save(update_fields=[pagina.campo, pagina.campo_data, "aggiornato_il"])


@router.put("/impostazioni/pagine/{chiave}", response=PaginaModificaOut)
def salva_pagina(request, chiave: str, dati: PaginaIn):
    from . import segnaposto as sp
    from .html import pulisci
    from .pagine import SEGNAPOSTO_PAGINE

    if not policy.puo_modificare_impostazioni(request.auth):
        raise HttpError(403, "Privacy policy e termini li cambiano i capigruppo.")
    pagina = _pagina(chiave)
    testo = pulisci(dati.testo)
    if not sp.SEGNAPOSTO.sub("", re.sub(r"<[^>]*>", "", testo)).strip():
        raise HttpError(400, "Il testo è vuoto.")
    ignoti = sp.sconosciuti(re.sub(r"<[^>]*>", " ", testo), SEGNAPOSTO_PAGINE)
    if ignoti:
        raise HttpError(400, "Segnaposto sconosciuto: " + ", ".join(f"[{n}]" for n in ignoti) + ".")
    _salva_pagina(pagina, testo)
    return _pagina_modifica(pagina)


@router.delete("/impostazioni/pagine/{chiave}", response=PaginaModificaOut)
def pagina_di_base(request, chiave: str):
    if not policy.puo_modificare_impostazioni(request.auth):
        raise HttpError(403, "Privacy policy e termini li cambiano i capigruppo.")
    pagina = _pagina(chiave)
    _salva_pagina(pagina, "")
    return _pagina_modifica(pagina)
