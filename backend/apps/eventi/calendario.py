"""The personal calendar feed (DEC-79), RFC 5545 written by hand: title, dates and place
of the user's and their children's events, nothing else (no names, no notes)."""

from datetime import UTC, datetime

from django.conf import settings
from django.db.models import Q, QuerySet

from apps.organizzazione.models import Incarico, RuoloIncarico
from apps.permessi import policy

from .models import Evento, StatoPartecipazione


def eventi_del_calendario(utente) -> QuerySet[Evento]:
    """Events the user or their children are invited to (taking part), and, for a
    capo, the events of the units they serve."""
    persone = [p.pk for p in policy.tutelati(utente) if policy.genitori_vedono(p, "scheda")]
    propria = policy.persona_di(utente)
    filtro = Q(pk__in=[])
    if propria is not None:
        persone.append(propria.pk)
        unita = Incarico.objects.attivi().filter(
            persona=propria,
            ruolo__in={RuoloIncarico.STAFF, RuoloIncarico.CAPO_UNITA},
        )
        filtro |= Q(unita__in=unita.values("unita_id")) | Q(
            squadriglia__unita__in=unita.values("unita_id")
        )
    filtro |= Q(
        partecipazioni__persona_id__in=persone,
        partecipazioni__stato=StatoPartecipazione.INVITATO,
    )
    return Evento.objects.filter(filtro).distinct().order_by("inizio")


def _testo(valore: str) -> str:
    return (
        valore.replace("\\", "\\\\")
        .replace(";", r"\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )


def _piega(riga: str) -> str:
    """Lines longer than 75 octets are folded (RFC 5545, 3.1)."""
    dati = riga.encode("utf-8")
    if len(dati) <= 75:
        return riga
    parti, inizio = [], 0
    while inizio < len(dati):
        fine = min(inizio + (75 if not parti else 74), len(dati))
        while fine < len(dati) and (dati[fine] & 0xC0) == 0x80:  # not inside a character
            fine -= 1
        parti.append(dati[inizio:fine].decode("utf-8"))
        inizio = fine
    return "\r\n ".join(parti)


def _utc(momento: datetime) -> str:
    return momento.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def ics(eventi) -> str:
    dominio = settings.FRONTEND_URL.split("//", 1)[-1].split("/", 1)[0]
    righe = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Quaderno di Caccia//QdC//IT",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Quaderno di Caccia",
    ]
    adesso = _utc(datetime.now(UTC))
    for evento in eventi:
        righe += [
            "BEGIN:VEVENT",
            f"UID:evento-{evento.pk}@{dominio}",
            f"DTSTAMP:{adesso}",
            f"LAST-MODIFIED:{_utc(evento.aggiornato_il)}",
            f"DTSTART:{_utc(evento.inizio)}",
            f"DTEND:{_utc(evento.fine)}",
            f"SUMMARY:{_testo(evento.titolo)}",
        ]
        if evento.luogo:
            righe.append(f"LOCATION:{_testo(evento.luogo)}")
        righe.append(f"URL:{settings.FRONTEND_URL}/eventi/{evento.pk}")
        righe.append("STATUS:CANCELLED" if evento.annullato_il else "STATUS:CONFIRMED")
        righe.append("END:VEVENT")
    righe.append("END:VCALENDAR")
    return "\r\n".join(_piega(r) for r in righe) + "\r\n"
