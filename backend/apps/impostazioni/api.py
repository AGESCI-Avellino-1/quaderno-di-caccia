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

from . import blocchi, segreti
from .models import MESSAGGIO_MANUTENZIONE, Impostazioni, ModelloEmail, SicurezzaSmtp

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
    # Maintenance (DEC-268): the PWA shows the message, the login page too.
    manutenzione: bool = False
    messaggio_manutenzione: str = ""


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
        "manutenzione": imp.manutenzione,
        "messaggio_manutenzione": imp.avviso_manutenzione() if imp.manutenzione else "",
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
    # Maintenance (DEC-268) and login locks (DEC-269): the technical administrator.
    manutenzione: bool
    messaggio_manutenzione: str
    messaggio_manutenzione_predefinito: str
    puo_manutenzione: bool
    puo_sbloccare_accessi: bool
    # Who receives the emails (DEC-276), and how many a group switched off did not get.
    email_capi: bool = False
    email_genitori: bool = False
    email_ragazzi: bool = False
    email_scartate: dict[str, int] = {}
    puo_destinatari_email: bool = False
    # The SMTP server (DEC-277): for the technical administrator only, never the password.
    puo_smtp: bool = False
    smtp_disponibile: bool = False
    smtp_host: str = ""
    smtp_porta: int = 587
    smtp_sicurezza: str = "STARTTLS"
    smtp_utente: str = ""
    smtp_password_salvata: bool = False
    mittente: str = ""
    # Used when the settings name no SMTP server.
    mittente_predefinito: str = ""


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
        "manutenzione": imp.manutenzione,
        "messaggio_manutenzione": imp.messaggio_manutenzione,
        "messaggio_manutenzione_predefinito": MESSAGGIO_MANUTENZIONE,
        "puo_manutenzione": policy.puo_gestire_manutenzione(request.auth),
        "puo_sbloccare_accessi": policy.puo_sbloccare_accessi(request.auth),
        "email_capi": imp.email_capi,
        "email_genitori": imp.email_genitori,
        "email_ragazzi": imp.email_ragazzi,
        "email_scartate": imp.email_scartate,
        "puo_destinatari_email": policy.puo_scegliere_destinatari_email(request.auth),
        **_smtp(request, imp),
    }


def _smtp(request, imp: Impostazioni) -> dict:
    if not policy.puo_configurare_smtp(request.auth):
        return {}
    return {
        "puo_smtp": True,
        "smtp_disponibile": segreti.disponibile(),
        "smtp_host": imp.smtp_host,
        "smtp_porta": imp.smtp_porta,
        "smtp_sicurezza": imp.smtp_sicurezza,
        "smtp_utente": imp.smtp_utente,
        "smtp_password_salvata": bool(imp.smtp_password),
        "mittente": imp.mittente,
        "mittente_predefinito": settings.DEFAULT_FROM_EMAIL,
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


class DestinatariEmailIn(Schema):
    capi: bool
    genitori: bool
    ragazzi: bool


@router.put("/impostazioni/destinatari-email", response=ImpostazioniOut)
def destinatari_email(request, dati: DestinatariEmailIn):
    """DEC-276: to a group switched off the emails are dropped, only counted."""
    if not policy.puo_scegliere_destinatari_email(request.auth):
        raise HttpError(403, "Chi riceve le email lo scelgono i capigruppo.")
    imp = Impostazioni.carica()
    imp.email_capi, imp.email_genitori, imp.email_ragazzi = dati.capi, dati.genitori, dati.ragazzi
    imp.save(update_fields=["email_capi", "email_genitori", "email_ragazzi", "aggiornato_il"])
    return _impostazioni(request)


class SmtpIn(Schema):
    host: str = ""
    porta: int = 587
    sicurezza: str = SicurezzaSmtp.STARTTLS
    utente: str = ""
    # Empty: the saved one stays.
    password: str = ""
    mittente: str = ""


def _controlla_smtp(dati: SmtpIn) -> None:
    from email.utils import parseaddr

    from django.core.validators import validate_email

    if dati.host and (" " in dati.host.strip() or "/" in dati.host):
        raise HttpError(400, "Scrivi solo il nome del server, per esempio smtp.gmail.com.")
    if not 1 <= dati.porta <= 65535:
        raise HttpError(400, "La porta è un numero tra 1 e 65535.")
    if dati.sicurezza not in SicurezzaSmtp.values:
        raise HttpError(400, "Scegli la sicurezza della connessione.")
    if dati.mittente.strip():
        try:
            validate_email(parseaddr(dati.mittente)[1])
        except ValidationError as errore:
            raise HttpError(
                400, "Il mittente va scritto come «Nome <indirizzo@dominio.it>»."
            ) from errore


@router.put("/impostazioni/smtp", response=ImpostazioniOut)
def salva_smtp(request, dati: SmtpIn):
    """DEC-277: no server = the one in the server's configuration; the password is
    encrypted and never sent back."""
    if not policy.puo_configurare_smtp(request.auth):
        raise HttpError(403, "Il server di posta lo imposta l'amministratore tecnico.")
    _controlla_smtp(dati)
    imp = Impostazioni.carica()
    imp.smtp_host = dati.host.strip()
    imp.smtp_porta = dati.porta
    imp.smtp_sicurezza = dati.sicurezza
    imp.smtp_utente = dati.utente.strip()
    imp.mittente = " ".join(dati.mittente.split())
    if not imp.smtp_host:
        imp.smtp_password = ""
    elif dati.password:
        if not segreti.disponibile():
            raise HttpError(
                400,
                "Manca la chiave per conservare la password: la imposta chi ha installato "
                "l'app (QDC_CHIAVE_SEGRETI).",
            )
        imp.smtp_password = segreti.cifra(dati.password)
    imp.save()
    return _impostazioni(request)


class ProvaSmtpOut(Schema):
    inviata_a: str


@router.post("/impostazioni/smtp/prova", response=ProvaSmtpOut)
def prova_smtp(request):
    """An email to the technical administrator themself, straight through the server
    in use: what goes wrong comes back in plain words (DEC-277)."""
    import smtplib

    from django.core.mail import EmailMessage

    from .posta import connessione

    if not policy.puo_configurare_smtp(request.auth):
        raise HttpError(403, "Il server di posta lo imposta l'amministratore tecnico.")
    imp = Impostazioni.carica()
    indirizzo = request.auth.email
    email = EmailMessage(
        subject="Prova del server di posta",
        body=(
            f"Ciao,\n\nquesta è l'email di prova di {imp.nome_sito}: se la leggi, il server "
            "di posta funziona.\n"
        ),
        from_email=imp.mittente or None,
        to=[indirizzo],
    )
    try:
        connessione(imp).send_messages([email])
    except smtplib.SMTPAuthenticationError as errore:
        raise HttpError(
            400,
            "Il server ha rifiutato utente o password. Con Gmail serve una password per le "
            "app; con Microsoft 365 l'accesso con password può essere disattivato.",
        ) from errore
    except smtplib.SMTPSenderRefused as errore:
        raise HttpError(400, "Il server non accetta questo mittente: controllalo.") from errore
    except (smtplib.SMTPException, OSError) as errore:
        raise HttpError(
            400,
            "Non riesco a mandare l'email: controlla server, porta e sicurezza della connessione.",
        ) from errore
    return {"inviata_a": indirizzo}


class ManutenzioneIn(Schema):
    attiva: bool
    messaggio: str = ""


@router.put("/impostazioni/manutenzione", response=ImpostazioniOut)
def manutenzione(request, dati: ManutenzioneIn):
    """DEC-268: only the technical administrators get in while it is on."""
    if not policy.puo_gestire_manutenzione(request.auth):
        raise HttpError(403, "La manutenzione la decide l'amministratore tecnico.")
    imp = Impostazioni.carica()
    imp.manutenzione = dati.attiva
    imp.messaggio_manutenzione = dati.messaggio.strip()
    imp.save(update_fields=["manutenzione", "messaggio_manutenzione", "aggiornato_il"])
    return _impostazioni(request)


class BloccoOut(Schema):
    tipo: str
    valore: str
    tentativi: int
    fino_al: str


class SbloccaIn(Schema):
    tipo: str
    valore: str


def _sblocchi(request) -> None:
    if not policy.puo_sbloccare_accessi(request.auth):
        raise HttpError(403, "Gli accessi bloccati li sblocca l'amministratore tecnico.")


@router.get("/impostazioni/blocchi-accesso", response=list[BloccoOut])
def blocchi_accesso(request):
    """DEC-269: who cannot log in now after too many wrong attempts."""
    _sblocchi(request)
    return [
        {**b, "fino_al": timezone.localtime(b["fino_al"]).isoformat()} for b in blocchi.in_corso()
    ]


@router.post("/impostazioni/blocchi-accesso/sblocca", response=list[BloccoOut])
def sblocca_accesso(request, dati: SbloccaIn):
    _sblocchi(request)
    if dati.tipo not in blocchi.TIPI or not dati.valore.strip():
        raise HttpError(400, "Indica l'account o l'indirizzo da sbloccare.")
    blocchi.sblocca(dati.tipo, dati.valore.strip())
    return blocchi_accesso(request)


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
