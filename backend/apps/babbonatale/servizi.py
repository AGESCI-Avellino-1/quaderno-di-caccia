"""Babbo Natale segreto (DEC-422): the draw, the changes after it and who is told.

The draw makes one circle: each participant gives a gift to the next, the last to the first.
Nobody draws themself and no two give a gift to each other; where possible brothers and sisters
(a guardian in common, `anagrafica.servizi.fratelli`) are not next to each other. Nothing here
logs or returns who gives a gift to whom, except `regalo_di` for the one who may read it.
"""

import secrets
from dataclasses import dataclass
from enum import StrEnum

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Invito, User
from apps.anagrafica.models import Persona
from apps.impostazioni.email import invia
from apps.notifiche.servizi import notifica

from .models import MINIMO_PARTECIPANTI, Partecipante, ScambioRegali

TENTATIVI = 500
PERCORSO = "/babbo-natale"
_caso = secrets.SystemRandom()


class Avviso(StrEnum):
    """How a participant learns who they give a gift to; says nothing about the draw."""

    APP = "app"  # has an account: notification and the entry in the app
    EMAIL = "email"  # an email of their own, from 14: email with the invitation
    GENITORI = "genitori"  # a minor without either: email to the parents
    NESSUNO = "nessuno"  # nobody can be told: the organiser sees it before the draw


# --- Who is told, and how ---------------------------------------------------------------------


def _email_propria(persona: Persona) -> str:
    """An email nobody else in the registry has (a child's is often a parent's, DEC-116)."""
    if not persona.email:
        return ""
    altre = Persona.objects.exclude(pk=persona.pk).filter(email__iexact=persona.email)
    return "" if altre.exists() else persona.email


def _genitori(persona: Persona) -> list[Persona]:
    return [
        r.tutore
        for r in persona.tutori.filter(responsabilita_genitoriale=True).select_related(
            "tutore__utente"
        )
    ]


def _indirizzo(persona: Persona) -> str:
    return persona.email or (persona.utente.email if persona.utente_id else "")


def come_avvisato(persona: Persona) -> Avviso:
    if persona.utente_id is not None:
        return Avviso.APP
    eta = persona.eta()
    if _email_propria(persona) and (eta is None or eta >= 14):
        # Age unknown: an adult imported without a birth date is still told directly.
        return Avviso.EMAIL
    if eta is not None and eta < 18 and any(_indirizzo(g) for g in _genitori(persona)):
        return Avviso.GENITORI
    return Avviso.NESSUNO


def _consegna(scambio: ScambioRegali) -> str:
    giorno = scambio.consegna_il.strftime("%d/%m/%Y")
    return f"{giorno}, {scambio.luogo}" if scambio.luogo else giorno


def _nome(persona: Persona | None) -> str:
    return f"{persona.nome} {persona.cognome}" if persona else ""


def _link_invito(persona: Persona, email: str, da) -> str:
    """The invitation to create the account (DEC-422): a valid one is reused; none when the
    address is already an account's."""
    from apps.accounts.servizi import link_invito

    valido = next((i for i in persona.inviti.all() if i.valido and i.email == email), None)
    if valido is None:
        if User.objects.filter(email__iexact=email).exists():
            return settings.FRONTEND_URL
        valido = Invito(email=email, persona=persona, creato_da=da)
        try:
            valido.full_clean()
        except ValidationError:
            return settings.FRONTEND_URL
        valido.save()
    return link_invito(valido)


def avvisa(partecipante: Partecipante, da=None) -> Avviso:
    """Tell one participant who they give a gift to. The organiser never sees the text."""
    persona, scambio = partecipante.persona, partecipante.scambio
    modo = come_avvisato(persona)
    titolo = "Babbo Natale segreto"
    testo = f"Scopri a chi fai il regalo per «{scambio.nome}»"
    valori = {"Scambio": scambio.nome, "A chi": _nome(partecipante.a_chi)}
    valori["Consegna"] = _consegna(scambio)
    if modo == Avviso.APP:
        notifica("babbo_natale", [persona], titolo, PERCORSO, testo)
    elif modo == Avviso.EMAIL:
        email = _email_propria(persona)
        link = _link_invito(persona, email, da)
        invia("babbo_natale_partecipante", {**valori, "Nome": persona.nome, "Link": link}, [email])
    elif modo == Avviso.GENITORI:
        genitori = _genitori(persona)
        for genitore in genitori:
            indirizzo = _indirizzo(genitore)
            if indirizzo:
                invia(
                    "babbo_natale_genitori",
                    {
                        **valori,
                        "Nome": genitore.nome,
                        "Ragazzo": _nome(persona),
                        "Link": f"{settings.FRONTEND_URL}{PERCORSO}",
                    },
                    [indirizzo],
                )
        notifica("babbo_natale", genitori, titolo, PERCORSO, testo)
    return modo


# --- The draw ---------------------------------------------------------------------------------


def _famiglie(persone: list[Persona]) -> set[frozenset[int]]:
    """Pairs of participants with a guardian in common."""
    from apps.anagrafica.models import RelazioneTutela

    tutori: dict[int, set[int]] = {}
    for r in RelazioneTutela.objects.filter(minore__in=persone).values("minore_id", "tutore_id"):
        tutori.setdefault(r["minore_id"], set()).add(r["tutore_id"])
    ids = list(tutori)
    return {
        frozenset((a, b)) for i, a in enumerate(ids) for b in ids[i + 1 :] if tutori[a] & tutori[b]
    }


def _vicini_fratelli(cerchio: list[int], famiglie: set[frozenset[int]]) -> int:
    return sum(
        frozenset((cerchio[i], cerchio[(i + 1) % len(cerchio)])) in famiglie
        for i in range(len(cerchio))
    )


def cerchio(persone: list[Persona]) -> list[int]:
    """A random circle with as few brothers and sisters side by side as possible."""
    ids = [p.pk for p in persone]
    famiglie = _famiglie(persone)
    migliore, peggio = list(ids), None
    for _ in range(TENTATIVI):
        prova = list(ids)
        _caso.shuffle(prova)
        vicini = _vicini_fratelli(prova, famiglie)
        if peggio is None or vicini < peggio:
            migliore, peggio = prova, vicini
        if vicini == 0:
            break
    return migliore


@dataclass
class Esito:
    avvisati: dict[str, int]


def _conta(modi: list[Avviso]) -> dict[str, int]:
    return {m.value: modi.count(m) for m in Avviso if modi.count(m)}


@transaction.atomic
def estrai(scambio: ScambioRegali, da) -> Esito:
    scambio = ScambioRegali.objects.select_for_update().get(pk=scambio.pk)
    if scambio.estratto:
        raise ValidationError("L'estrazione è già stata fatta.")
    if scambio.chiuso():
        raise ValidationError("Il giorno della consegna è passato.")
    partecipanti = list(scambio.partecipanti.select_related("persona"))
    if len(partecipanti) < MINIMO_PARTECIPANTI:
        raise ValidationError(f"Servono almeno {MINIMO_PARTECIPANTI} partecipanti.")
    per_persona = {p.persona_id: p for p in partecipanti}
    giro = cerchio([p.persona for p in partecipanti])
    for i, persona_id in enumerate(giro):
        per_persona[persona_id].a_chi_id = giro[(i + 1) % len(giro)]
    Partecipante.objects.bulk_update(partecipanti, ["a_chi"])
    scambio.estratto_il = timezone.now()
    scambio.save(update_fields=["estratto_il", "aggiornato_il"])
    modi = [avvisa(p, da) for p in partecipanti]
    return Esito(avvisati=_conta(modi))


# --- Before the draw --------------------------------------------------------------------------


@transaction.atomic
def imposta_partecipanti(scambio: ScambioRegali, persone: list[Persona]) -> None:
    if scambio.estratto:
        raise ValidationError(
            "Dopo l'estrazione i partecipanti si aggiungono o si ritirano uno alla volta."
        )
    scambio.partecipanti.exclude(persona__in=persone).delete()
    esistenti = set(scambio.partecipanti.values_list("persona_id", flat=True))
    Partecipante.objects.bulk_create(
        Partecipante(scambio=scambio, persona=p) for p in persone if p.pk not in esistenti
    )


# --- After the draw: only the point of the circle touched changes -----------------------------


def _modificabile(scambio: ScambioRegali) -> None:
    if not scambio.estratto:
        raise ValidationError("L'estrazione non è ancora stata fatta.")
    if scambio.chiuso():
        raise ValidationError("Il giorno della consegna è passato: lo scambio è chiuso.")


@transaction.atomic
def ritira(scambio: ScambioRegali, persona: Persona, da) -> None:
    """Who gave the gift to the one leaving gives it to whom that one gave it to; only they
    are told again."""
    scambio = ScambioRegali.objects.select_for_update().get(pk=scambio.pk)
    _modificabile(scambio)
    uscente = scambio.partecipanti.filter(persona=persona).first()
    if uscente is None:
        raise ValidationError("Questa persona non partecipa allo scambio.")
    if scambio.partecipanti.count() - 1 < MINIMO_PARTECIPANTI:
        raise ValidationError(
            f"Resterebbero meno di {MINIMO_PARTECIPANTI} partecipanti: lo scambio non si può fare."
        )
    precedente = scambio.partecipanti.select_related("persona").get(a_chi=persona)
    precedente.a_chi_id = uscente.a_chi_id
    uscente.delete()
    precedente.save(update_fields=["a_chi"])
    avvisa(precedente, da)


@transaction.atomic
def aggiungi(scambio: ScambioRegali, persona: Persona, da) -> None:
    """The new participant goes in a random point of the circle, where possible not next to a
    brother or sister: they and who now gives them the gift are told."""
    scambio = ScambioRegali.objects.select_for_update().get(pk=scambio.pk)
    _modificabile(scambio)
    if scambio.partecipanti.filter(persona=persona).exists():
        raise ValidationError("Questa persona partecipa già allo scambio.")
    presenti = list(scambio.partecipanti.select_related("persona"))
    famiglie = _famiglie([persona, *(p.persona for p in presenti)])
    _caso.shuffle(presenti)
    presenti.sort(
        key=lambda p: (frozenset((p.persona_id, persona.pk)) in famiglie)
        + (frozenset((persona.pk, p.a_chi_id)) in famiglie)
    )
    prima = presenti[0]
    nuovo = Partecipante.objects.create(scambio=scambio, persona=persona, a_chi_id=prima.a_chi_id)
    prima.a_chi = persona
    prima.save(update_fields=["a_chi"])
    avvisa(nuovo, da)
    avvisa(prima, da)


def reinvia(scambio: ScambioRegali, persone: list[Persona], da) -> int:
    """Tell again the chosen participants, without seeing what they are told."""
    _modificabile(scambio)
    scelti = scambio.partecipanti.filter(persona__in=persone).select_related("persona", "a_chi")
    return sum(avvisa(p, da) != Avviso.NESSUNO for p in scelti)
