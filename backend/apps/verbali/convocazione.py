"""The convocation of a meeting (DEC-327): first the attachments, then one email to who is
invited; every attachment added later goes out by itself. The files travel with the email up
to a limit, and stay in the app."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.anagrafica.models import Persona
from apps.eventi.avvisi import indirizzi_diretti, quando
from apps.eventi.models import CERCHIE_CONVOCATE, Cerchia, Evento, StatoPartecipazione
from apps.notifiche.servizi import notifica

from .models import AllegatoVerbale

# All the files of one email: it is built for each person and waits in the queue, and
# mailboxes refuse big messages anyway [da verificare with the group's mail server].
MASSIMO_NELL_EMAIL = 5 * 1024 * 1024


def ha_convocazione(evento: Evento) -> bool:
    return evento.cerchia in CERCHIE_CONVOCATE


def allegati_di(evento: Evento):
    return AllegatoVerbale.objects.filter(
        verbale__evento=evento, di_convocazione=True, completo=True
    )


def si_puo_inviare(evento: Evento) -> bool:
    return (
        evento.convocata_il is None and evento.annullato_il is None and evento.fine > timezone.now()
    )


def _invitati(evento: Evento) -> list[str]:
    return indirizzi_diretti(
        Persona.objects.filter(
            partecipazioni__evento=evento, partecipazioni__stato=StatoPartecipazione.INVITATO
        )
    )


def _da_allegare(allegati) -> tuple[list[tuple[str, bytes, str]], list[AllegatoVerbale]]:
    """Files that fit in the email, smallest first; the others only named."""
    from . import servizi

    dentro, fuori, totale = [], [], 0
    for allegato in sorted(allegati, key=lambda a: a.dimensione):
        if totale + allegato.dimensione > MASSIMO_NELL_EMAIL:
            fuori.append(allegato)
            continue
        contenuto = b"".join(servizi.contenuto(allegato))
        dentro.append((allegato.nome_file, contenuto, allegato.tipo_file))
        totale += allegato.dimensione
    return dentro, fuori


def _testo_documenti(dentro, fuori) -> str:
    parti = []
    if dentro:
        parti.append("In allegato: " + ", ".join(nome for nome, _, _ in dentro) + ".")
    if fuori:
        nomi = ", ".join(a.nome_file for a in fuori)
        parti.append(f"Da aprire nell'app, perché troppo grandi per un'email: {nomi}.")
    return " ".join(parti)


def pdf_del_modello(evento: Evento) -> bytes:
    """The assembly's convocation on the group's letterhead (DEC-337), never stored: its data
    do not change once sent, and it stays readable in the app."""
    from . import modelli, servizi, stampa

    inviata = timezone.localdate(evento.convocata_il) if evento.convocata_il else None
    return stampa.pdf_convocazione(modelli.testo_convocazione(servizi.verbale_di(evento), inviata))


def testo_ordine_del_giorno(evento: Evento) -> str:
    """The points of the template at the assembly, the agenda written elsewhere; nothing when
    there is none (DEC-364). Plain lines: placeholders' values are escaped in the email."""
    from apps.impostazioni.html import in_testo

    from . import modelli, servizi

    if evento.cerchia == Cerchia.SOCI:
        dati = modelli.dati_convocazione(servizi.verbale_di(evento))
        punti = modelli.punti_convocazione(dati)
        righe = [f"{numero}. {punto}" for numero, punto in enumerate(punti, 1)]
    else:
        righe = [r.strip() for r in in_testo(evento.ordine_del_giorno).splitlines() if r.strip()]
    return "\n".join(["Ordine del giorno:", *righe]) if righe else ""


def _invia(evento: Evento, modello: str, allegati, primo=(), valori=None) -> int:
    from apps.impostazioni.email import invia as invia_email

    dentro, fuori = _da_allegare(allegati)
    dentro = [*primo, *dentro]
    invitati = Persona.objects.filter(
        partecipazioni__evento=evento, partecipazioni__stato=StatoPartecipazione.INVITATO
    ).select_related("utente")
    titolo = "Convocazione" if modello == "convocazione_riunione" else "Nuovo documento"
    notifica("eventi", list(invitati), f"{titolo}: {evento.titolo}", f"/eventi/{evento.pk}")
    return invia_email(
        modello,
        {
            "Evento": evento.titolo,
            "Quando": quando(evento) + (f", {evento.dove()}" if evento.dove() else ""),
            "Documenti": _testo_documenti(dentro, fuori),
            "Link": f"{settings.FRONTEND_URL}/eventi/{evento.pk}",
            **(valori or {}),
        },
        _invitati(evento),
        allegati=tuple(dentro),
    )


def invia(evento: Evento) -> int:
    if evento.convocata_il is not None:
        raise ValidationError("La convocazione è già stata inviata.")
    if not si_puo_inviare(evento):
        raise ValidationError("La riunione è passata o annullata.")
    assemblea = evento.cerchia == Cerchia.SOCI
    if assemblea:
        from . import modelli, servizi

        mancanti = modelli.mancanti_convocazione(servizi.verbale_di(evento))
        if mancanti:
            raise ValidationError("Per inviarla manca: " + "; ".join(mancanti) + ".")
    evento.convocata_il = timezone.now()
    evento.save(update_fields=["convocata_il", "aggiornato_il"])
    primo = ()
    if assemblea:
        primo = (("convocazione-assemblea.pdf", pdf_del_modello(evento), "application/pdf"),)
    valori = {"Ordine del giorno": testo_ordine_del_giorno(evento)}
    return _invia(evento, "convocazione_riunione", list(allegati_di(evento)), primo, valori)


def allegato_aggiunto(allegato: AllegatoVerbale) -> int:
    """Before the convocation it simply goes with it."""
    evento = allegato.verbale.evento
    if evento.convocata_il is None or evento.annullato_il or evento.fine <= timezone.now():
        return 0
    return _invia(evento, "documento_riunione", [allegato])
