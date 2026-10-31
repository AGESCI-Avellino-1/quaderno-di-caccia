"""Emails from templates the group may personalise (DEC-250).

Every email the platform sends has a type in `catalogo_email.TIPI`: name, when it is
sent, its placeholders (some indispensable) and the default subject and HTML. The group's
version, if any, is a `ModelloEmail`. Senders call `messaggio()` and send the result as
before; the plain-text part is always derived from the HTML.

A saved template that lacks a placeholder made indispensable by a later update is not
used: the email goes out with the default text, and the capigruppo and the technical
administrators are told once (DEC-250).
"""

import logging
import re
from dataclasses import dataclass
from html import escape

from django.conf import settings
from django.core.mail import EmailMessage, EmailMultiAlternatives, mailers
from django.utils import timezone

from apps.core.anno import AnnoAssociativo

from . import segnaposto as sp
from .html import in_testo, pulisci
from .models import Impostazioni, ModelloEmail

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Segnaposto:
    nome: str
    descrizione: str
    esempio: str
    indispensabile: bool = False
    # An address: in the HTML it becomes a clickable link.
    link: bool = False


@dataclass(frozen=True)
class TipoEmail:
    chiave: str
    nome: str
    # Who receives it and when, for the settings page.
    descrizione: str
    oggetto: str
    corpo: str
    segnaposto: tuple[Segnaposto, ...] = ()
    # Optional emails (DEC-157) end with the fixed line on how to stop them.
    facoltativa: bool = False


COMUNI = (
    Segnaposto(sp.NOME_SITO, "il nome del sito", "Quaderno di Caccia"),
    Segnaposto(sp.SIGLA_SITO, "la sigla del sito", "QdC"),
    Segnaposto(sp.GRUPPO, "il nome del gruppo", "AGESCI Avellino 1"),
    Segnaposto(sp.SIGLA_GRUPPO, "la sigla del gruppo", "AV1"),
    Segnaposto(sp.ANNO, "l'anno scout", "2025/26"),
)


def segnaposto_di(tipo: TipoEmail) -> tuple[Segnaposto, ...]:
    return COMUNI + tipo.segnaposto


def _tipi() -> dict[str, TipoEmail]:
    from .catalogo_email import TIPI

    return TIPI


def tipo(chiave: str) -> TipoEmail:
    return _tipi()[chiave]


def tutti() -> list[TipoEmail]:
    return list(_tipi().values())


# --- Checks ---------------------------------------------------------------------------------


def mancanti(t: TipoEmail, oggetto: str, corpo: str) -> list[str]:
    """Indispensable placeholders missing from subject and body."""
    usati = {n.casefold() for n in sp.usati(oggetto) + sp.usati(_solo_testo(corpo))}
    return [s.nome for s in t.segnaposto if s.indispensabile and s.nome.casefold() not in usati]


def problemi(t: TipoEmail, oggetto: str, corpo: str) -> list[str]:
    """Why a template cannot be saved; empty if it can."""
    errori = []
    if not oggetto.strip():
        errori.append("Scrivi l'oggetto.")
    if not _solo_testo(corpo).strip():
        errori.append("Scrivi il testo dell'email.")
    ammessi = tuple(s.nome for s in segnaposto_di(t))
    ignoti = sp.sconosciuti(oggetto, ammessi) + sp.sconosciuti(_solo_testo(corpo), ammessi)
    if ignoti:
        elenco = ", ".join(f"[{n}]" for n in dict.fromkeys(ignoti))
        errori.append(f"Segnaposto sconosciuto: {elenco}.")
    if dentro_link(corpo):
        errori.append("I segnaposto non possono stare dentro l'indirizzo di un link.")
    assenti = mancanti(t, oggetto, corpo)
    if assenti:
        elenco = ", ".join(f"[{n}]" for n in assenti)
        errori.append(f"Mancano segnaposto indispensabili: {elenco}.")
    return errori


_TAG = re.compile(r"(<[^>]*>)")


def _solo_testo(html: str) -> str:
    return "".join(p for p in _TAG.split(html) if not p.startswith("<"))


def dentro_link(html: str) -> bool:
    return any(p.startswith("<") and sp.SEGNAPOSTO.search(p) for p in _TAG.split(html))


# --- Composing ------------------------------------------------------------------------------


@dataclass(frozen=True)
class Composta:
    oggetto: str
    html: str
    testo: str


def _comuni() -> dict[str, str]:
    imp = Impostazioni.carica()
    gruppo = imp.nome_del_gruppo()
    return {
        sp.NOME_SITO: imp.nome_sito,
        sp.SIGLA_SITO: imp.sigla_sito or imp.nome_sito,
        sp.GRUPPO: gruppo,
        sp.SIGLA_GRUPPO: imp.sigla_gruppo or gruppo,
        sp.ANNO: AnnoAssociativo.corrente().etichetta,
    }


def _valore(valori: dict[str, str], nome: str) -> str | None:
    for chiave, valore in valori.items():
        if chiave.casefold() == nome.casefold():
            return valore
    return None


def _riempi_testo(testo: str, valori: dict[str, str]) -> str:
    def sostituisci(m: re.Match) -> str:
        valore = _valore(valori, m.group(1).strip())
        return m.group(0) if valore is None else " ".join(valore.split())

    return sp.SEGNAPOSTO.sub(sostituisci, testo)


def _riempi_html(html: str, valori: dict[str, str], link: set[str]) -> str:
    """Placeholders only in the text between tags: values escaped, line breaks kept,
    addresses as links."""

    def sostituisci(m: re.Match) -> str:
        nome = m.group(1).strip()
        valore = _valore(valori, nome)
        if valore is None:
            return m.group(0)
        if nome.casefold() in link and valore:
            indirizzo = escape(valore, quote=True)
            return f'<a href="{indirizzo}">{escape(valore)}</a>'
        return "<br>".join(escape(riga) for riga in valore.split("\n"))

    return "".join(
        p if p.startswith("<") else sp.SEGNAPOSTO.sub(sostituisci, p) for p in _TAG.split(html)
    )


def componi_da(t: TipoEmail, oggetto: str, corpo: str, valori: dict[str, str]) -> Composta:
    tutti_i_valori = {**_comuni(), **valori}
    link = {s.nome.casefold() for s in segnaposto_di(t) if s.link}
    html = _riempi_html(pulisci(corpo), tutti_i_valori, link)
    return Composta(oggetto=_riempi_testo(oggetto, tutti_i_valori), html=html, testo=in_testo(html))


def modello_in_uso(t: TipoEmail) -> tuple[str, str]:
    """The group's template, or the default when there is none or it lacks something
    indispensable (then the capigruppo are told, once)."""
    salvato = ModelloEmail.objects.filter(chiave=t.chiave).first()
    if salvato is None:
        return t.oggetto, t.corpo
    if mancanti(t, salvato.oggetto, salvato.corpo):
        _segnala_da_correggere(t, salvato)
        return t.oggetto, t.corpo
    return salvato.oggetto, salvato.corpo


def componi(chiave: str, valori: dict[str, str]) -> Composta:
    t = tipo(chiave)
    oggetto, corpo = modello_in_uso(t)
    return componi_da(t, oggetto, corpo, valori)


def _piede_facoltative() -> tuple[str, str]:
    """The fixed end of every optional email (DEC-157), not editable."""
    indirizzo = f"{settings.FRONTEND_URL}/email"
    return (
        f'<p><small>Per scegliere quali email ricevere: <a href="{escape(indirizzo)}">'
        f"{escape(indirizzo)}</a></small></p>",
        f"\nPer scegliere quali email ricevere: {indirizzo}\n",
    )


def _pagina(html: str) -> str:
    return (
        '<!doctype html><html lang="it"><head><meta charset="utf-8"></head>'
        '<body style="font-family: Arial, Helvetica, sans-serif; font-size: 15px; '
        f'line-height: 1.5; color: #222;">{html}</body></html>'
    )


class EmailConImmagini(EmailMultiAlternatives):
    """An email whose HTML carries its images inline (multipart/related with Content-ID),
    so they show even where remote images are blocked (DEC-250)."""

    def __init__(self, *args, immagini=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.immagini = list(immagini)  # (cid, bytes, subtype)

    def message(self, *, policy=None):
        msg = super().message() if policy is None else super().message(policy=policy)
        if not self.immagini:
            return msg
        for parte in msg.walk():
            if parte.get_content_type() == "text/html":
                for cid, dati, sottotipo in self.immagini:
                    parte.add_related(dati, maintype="image", subtype=sottotipo, cid=f"<{cid}>")
                break
        return msg


_IMMAGINE = re.compile(r'src="/api/v1/immagini/([A-Za-z0-9_.-]+)"')


def _incorpora(html: str) -> tuple[str, list[tuple[str, bytes, str]]]:
    """The app's images become inline parts: src="cid:…"."""
    from .models import ImmagineEmail

    immagini = []
    for nome in dict.fromkeys(_IMMAGINE.findall(html)):
        immagine = ImmagineEmail.objects.filter(file__endswith=f"/{nome}").first()
        if immagine is None:
            continue
        with immagine.file.open("rb") as f:
            immagini.append((nome, f.read(), immagine.tipo.split("/")[-1]))
        html = html.replace(f'src="/api/v1/immagini/{nome}"', f'src="cid:{nome}"')
    return html, immagini


def piede(chiave: str) -> tuple[str, str]:
    """The common footer (HTML, text) for this email type, or empty (DEC-250)."""
    imp = Impostazioni.carica()
    if not imp.piede_email or chiave in imp.email_senza_piede:
        return "", ""
    comuni = _comuni()
    html = _riempi_html(pulisci(imp.piede_email), comuni, set())
    if imp.piede_email_testo.strip():
        testo = sp.SEGNAPOSTO.sub(
            lambda m: _valore(comuni, m.group(1).strip()) or m.group(0), imp.piede_email_testo
        ).strip()
    else:
        testo = in_testo(html).strip()
    return html, testo


def messaggio(
    chiave: str,
    valori: dict[str, str],
    a: str,
    *,
    allegati: tuple[tuple[str, bytes, str], ...] = (),
) -> EmailMultiAlternatives:
    """One email to one address, ready to send (one each: no shared addresses)."""
    t = tipo(chiave)
    composta = componi(chiave, valori)
    html, testo = composta.html, composta.testo
    piede_html, piede_testo = piede(chiave)
    if piede_html:
        html += f'<hr style="border:0;border-top:1px solid #ccc">{piede_html}'
        testo += f"\n-- \n{piede_testo}\n"
    if t.facoltativa:
        piede_html, piede_testo = _piede_facoltative()
        html, testo = html + piede_html, testo + piede_testo
    html, immagini = _incorpora(html)
    email = EmailConImmagini(subject=composta.oggetto, body=testo, to=[a], immagini=immagini)
    email.attach_alternative(_pagina(html), "text/html")
    for nome, contenuto, tipo_mime in allegati:
        email.attach(nome, contenuto, tipo_mime)
    return email


def invia(chiave: str, valori: dict[str, str], destinatari, **opzioni) -> int:
    """One message per address, sent together."""
    messaggi = [messaggio(chiave, valori, a, **opzioni) for a in sorted(set(destinatari)) if a]
    return mailers.default.send_messages(messaggi) if messaggi else 0


# --- A saved template to fix -----------------------------------------------------------------


def _segnala_da_correggere(t: TipoEmail, salvato: ModelloEmail) -> None:
    if salvato.avvisato_il is not None:
        return
    from apps.accounts.models import User
    from apps.organizzazione.models import Incarico, RuoloIncarico

    capigruppo = Incarico.objects.attivi().filter(
        ruolo__in={RuoloIncarico.CAPOGRUPPO, RuoloIncarico.AMMINISTRATORE},
        persona__utente__isnull=False,
    )
    indirizzi = {i.persona.utente.email for i in capigruppo.select_related("persona__utente")}
    indirizzi |= set(
        User.objects.filter(amministratore_tecnico=True, is_active=True).values_list(
            "email", flat=True
        )
    )
    elenco = ", ".join(f"[{n}]" for n in mancanti(t, salvato.oggetto, salvato.corpo))
    testo = (
        f"Ciao,\n\nil modello personalizzato dell'email «{t.nome}» non contiene più "
        f"tutto quello che serve: manca {elenco}. Finché non lo correggi, l'email parte "
        f"con il testo di base.\n\nLo correggi nelle Impostazioni: "
        f"{settings.FRONTEND_URL}/impostazioni\n"
    )
    messaggi = [
        EmailMessage(subject="Un modello di email da correggere", body=testo, to=[a])
        for a in sorted(indirizzi)
        if a
    ]
    if messaggi:
        mailers.default.send_messages(messaggi)
    salvato.avvisato_il = timezone.now()
    salvato.save(update_fields=["avvisato_il", "aggiornato_il"])
    logger.warning("Modello email da correggere: %s", t.chiave)
