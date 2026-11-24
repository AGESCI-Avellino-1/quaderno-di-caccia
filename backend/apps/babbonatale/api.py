"""Babbo Natale segreto (DEC-422), online only. Off in the settings, none of it exists (DEC-421).

Who gives a gift to whom is returned only by `GET /babbo-natale`, to the giver and to the parents
of a minor taking part; never to the organisers, nor to someone using the app as another user.
"""

from datetime import date

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from ninja import Router, Schema, Status
from ninja.errors import HttpError

from apps.anagrafica.models import AppartenenzaSquadriglia, Persona
from apps.impostazioni import funzioni
from apps.organizzazione.models import Unita
from apps.permessi import policy

from . import servizi
from .models import MINIMO_PARTECIPANTI, ScambioRegali

router = Router(tags=["babbo-natale"])

NON_TROVATO = "Scambio non trovato."


def _attiva() -> None:
    funzioni.richiedi(funzioni.BABBO_NATALE)


def _o_errore(funzione, *argomenti):
    try:
        return funzione(*argomenti)
    except ValidationError as errore:
        raise HttpError(400, " ".join(errore.messages)) from errore


def _gestibile(request, scambio_id: int) -> ScambioRegali:
    _attiva()
    scambio = get_object_or_404(ScambioRegali, pk=scambio_id)
    if not policy.puo_gestire_scambio(request.auth, scambio):
        raise HttpError(404, NON_TROVATO)
    return scambio


class RegaloOut(Schema):
    scambio: str
    consegna_il: date
    luogo: str
    # Who takes part: oneself or a child.
    chi: str
    proprio: bool
    # Who to give the gift to; empty while using the app as another user (DEC-167).
    a_chi: str
    chiuso: bool


class ScambioBreve(Schema):
    id: int
    nome: str
    unita: str
    consegna_il: date
    luogo: str
    estratto: bool
    chiuso: bool
    partecipanti: int


class UnitaScelta(Schema):
    id: int
    nome: str


class BabboNataleOut(Schema):
    regali: list[RegaloOut]
    # Using the app as another user: the gifts are hidden.
    nascosti: bool
    puo_organizzare: bool
    scambi: list[ScambioBreve]
    unita: list[UnitaScelta]
    puo_tutto_il_gruppo: bool


def _unita(scambio: ScambioRegali) -> str:
    return str(scambio.unita) if scambio.unita_id else "Tutto il gruppo"


def _breve(scambio: ScambioRegali) -> dict:
    return {
        "id": scambio.pk,
        "nome": scambio.nome,
        "unita": _unita(scambio),
        "consegna_il": scambio.consegna_il,
        "luogo": scambio.luogo,
        "estratto": scambio.estratto,
        "chiuso": scambio.chiuso(),
        "partecipanti": scambio.partecipanti.count(),
    }


def _scambi_gestibili(user) -> list[ScambioRegali]:
    if not policy.puo_organizzare_scambi(user):
        return []
    scambi = ScambioRegali.objects.select_related("unita")
    return [s for s in scambi if policy.puo_gestire_scambio(user, s)]


@router.get("/babbo-natale", response=BabboNataleOut)
def babbo_natale(request):
    _attiva()
    user = request.auth
    if not policy.vede_babbo_natale(user):
        raise HttpError(404, "Pagina non trovata.")
    nascosti = getattr(request, "impersonatore", None) is not None
    propria = policy.persona_di(user)
    regali = [
        {
            "scambio": p.scambio.nome,
            "consegna_il": p.scambio.consegna_il,
            "luogo": p.scambio.luogo,
            "chi": servizi._nome(p.persona),
            "proprio": propria is not None and p.persona_id == propria.pk,
            "a_chi": "" if nascosti else servizi._nome(p.a_chi),
            "chiuso": p.scambio.chiuso(),
        }
        for p in policy.regali_da_fare(user)
    ]
    regali.sort(key=lambda r: (not r["proprio"], r["consegna_il"]))
    return {
        "regali": regali,
        "nascosti": nascosti,
        "puo_organizzare": policy.puo_organizzare_scambi(user),
        "scambi": [_breve(s) for s in _scambi_gestibili(user)],
        "unita": [{"id": u.pk, "nome": str(u)} for u in policy.unita_per_scambi(user)],
        "puo_tutto_il_gruppo": policy.e_capogruppo(user),
    }


class ScambioIn(Schema):
    nome: str
    # None: the whole group (capigruppo only).
    unita_id: int | None = None
    consegna_il: date
    luogo: str = ""


def _dati(request, scambio: ScambioRegali, dati: ScambioIn) -> None:
    nome = " ".join(dati.nome.split())
    if not nome:
        raise HttpError(400, "Scrivi il nome dello scambio.")
    if dati.unita_id is None:
        if not policy.e_capogruppo(request.auth):
            raise HttpError(400, "Scegli l'unità dello scambio.")
        scambio.unita = None
    elif scambio.unita_id != dati.unita_id:
        if scambio.estratto:
            raise HttpError(400, "Dopo l'estrazione l'unità non si cambia.")
        unita = policy.unita_per_scambi(request.auth).filter(pk=dati.unita_id).first()
        if unita is None:
            raise HttpError(
                400, "Puoi creare scambi solo per le unità di cui fai parte dello staff."
            )
        scambio.unita = unita
    if dati.consegna_il < date.today() and dati.consegna_il != scambio.consegna_il:
        raise HttpError(400, "Il giorno della consegna non può essere passato.")
    scambio.nome = nome[:120]
    scambio.consegna_il = dati.consegna_il
    scambio.luogo = " ".join(dati.luogo.split())[:200]


class PartecipanteOut(Schema):
    id: int
    nome: str
    cognome: str
    # How they will be told: app, email, genitori, nessuno.
    avviso: str
    # Whom they give a gift to: only for who nobody can tell, after the draw (DEC-422).
    a_chi: str | None = None


class CandidatoOut(Schema):
    id: int
    nome: str
    cognome: str
    unita: list[UnitaScelta]
    squadriglia: UnitaScelta | None


class ScambioOut(ScambioBreve):
    unita_id: int | None
    elenco: list[PartecipanteOut]
    minimo: int


def _scambio_out(request, scambio: ScambioRegali) -> dict:
    partecipanti = sorted(
        scambio.partecipanti.select_related("persona__utente", "a_chi"),
        key=lambda p: (p.persona.cognome.casefold(), p.persona.nome.casefold()),
    )
    # Never while using the app as another user (DEC-167).
    nascosti = getattr(request, "impersonatore", None) is not None
    elenco = []
    for p in partecipanti:
        avviso = servizi.come_avvisato(p.persona)
        # Who nobody can tell: the organiser sees whom they give a gift to, to say it aloud
        # (exception to the secrecy, maintainer 24/11, DEC-422). Nobody else's, ever.
        a_chi = (
            servizi._nome(p.a_chi)
            if avviso == servizi.Avviso.NESSUNO and scambio.estratto and not nascosti
            else None
        )
        elenco.append(
            {
                "id": p.persona_id,
                "nome": p.persona.nome,
                "cognome": p.persona.cognome,
                "avviso": avviso.value,
                "a_chi": a_chi,
            }
        )
    return {
        **_breve(scambio),
        "unita_id": scambio.unita_id,
        "elenco": elenco,
        "minimo": MINIMO_PARTECIPANTI,
    }


@router.post("/babbo-natale/scambi", response={201: ScambioOut})
def crea(request, dati: ScambioIn):
    _attiva()
    if not policy.puo_organizzare_scambi(request.auth):
        raise HttpError(403, "Gli scambi li creano lo staff delle unità e i capigruppo.")
    scambio = ScambioRegali(creato_da=request.auth, consegna_il=dati.consegna_il)
    if dati.consegna_il < date.today():
        raise HttpError(400, "Il giorno della consegna non può essere passato.")
    _dati(request, scambio, dati)
    scambio.save()
    return Status(201, _scambio_out(request, scambio))


@router.get("/babbo-natale/scambi/{scambio_id}", response=ScambioOut)
def scambio(request, scambio_id: int):
    return _scambio_out(request, _gestibile(request, scambio_id))


@router.put("/babbo-natale/scambi/{scambio_id}", response=ScambioOut)
def modifica(request, scambio_id: int, dati: ScambioIn):
    scambio = _gestibile(request, scambio_id)
    if scambio.chiuso():
        raise HttpError(400, "Il giorno della consegna è passato: lo scambio è chiuso.")
    _dati(request, scambio, dati)
    scambio.save()
    return _scambio_out(request, scambio)


@router.delete("/babbo-natale/scambi/{scambio_id}", response={204: None})
def elimina(request, scambio_id: int):
    scambio = _gestibile(request, scambio_id)
    if scambio.estratto:
        raise HttpError(400, "Dopo l'estrazione lo scambio non si elimina.")
    scambio.delete()
    return Status(204, None)


@router.get("/babbo-natale/scambi/{scambio_id}/candidati", response=list[CandidatoOut])
def candidati(request, scambio_id: int):
    """Who may be added, with their units and patrol, to add a whole unit or patrol at once."""
    scambio = _gestibile(request, scambio_id)
    persone = list(policy.candidati_scambio(request.auth, scambio).order_by("cognome", "nome"))
    from apps.anagrafica.models import Appartenenza

    unita: dict[int, list[Unita]] = {}
    for a in Appartenenza.objects.attive().filter(persona__in=persone).select_related("unita"):
        unita.setdefault(a.persona_id, []).append(a.unita)
    squadriglie = {
        a.persona_id: a.squadriglia
        for a in AppartenenzaSquadriglia.objects.attive()
        .filter(persona__in=persone)
        .select_related("squadriglia")
    }
    return [
        {
            "id": p.pk,
            "nome": p.nome,
            "cognome": p.cognome,
            "unita": [{"id": u.pk, "nome": str(u)} for u in unita.get(p.pk, [])],
            "squadriglia": (
                {"id": s.pk, "nome": s.nome} if (s := squadriglie.get(p.pk)) is not None else None
            ),
        }
        for p in persone
    ]


class PersoneIn(Schema):
    persone: list[int]


def _persone(request, scambio: ScambioRegali, ids: list[int]) -> list[Persona]:
    ammesse = list(policy.candidati_scambio(request.auth, scambio).filter(pk__in=ids))
    if len(ammesse) != len(set(ids)):
        raise HttpError(400, "Alcune persone non si possono aggiungere a questo scambio.")
    return ammesse


@router.put("/babbo-natale/scambi/{scambio_id}/partecipanti", response=ScambioOut)
def partecipanti(request, scambio_id: int, dati: PersoneIn):
    """Before the draw: the whole list at once."""
    scambio = _gestibile(request, scambio_id)
    _o_errore(servizi.imposta_partecipanti, scambio, _persone(request, scambio, dati.persone))
    return _scambio_out(request, scambio)


class EstrazioneOut(ScambioOut):
    avvisati: dict[str, int]


@router.post("/babbo-natale/scambi/{scambio_id}/estrai", response=EstrazioneOut)
def estrai(request, scambio_id: int):
    scambio = _gestibile(request, scambio_id)
    esito = _o_errore(servizi.estrai, scambio, request.auth)
    scambio.refresh_from_db()
    return {**_scambio_out(request, scambio), "avvisati": esito.avvisati}


class PersonaIn(Schema):
    persona_id: int


@router.post("/babbo-natale/scambi/{scambio_id}/aggiungi", response=ScambioOut)
def aggiungi(request, scambio_id: int, dati: PersonaIn):
    """After the draw: one more participant, in a random point of the circle."""
    scambio = _gestibile(request, scambio_id)
    persona = _persone(request, scambio, [dati.persona_id])[0]
    _o_errore(servizi.aggiungi, scambio, persona, request.auth)
    return _scambio_out(request, scambio)


@router.post("/babbo-natale/scambi/{scambio_id}/ritira", response=ScambioOut)
def ritira(request, scambio_id: int, dati: PersonaIn):
    """After the draw: a participant leaves; the circle closes around them."""
    scambio = _gestibile(request, scambio_id)
    persona = get_object_or_404(Persona, pk=dati.persona_id)
    _o_errore(servizi.ritira, scambio, persona, request.auth)
    return _scambio_out(request, scambio)


class ReinviatiOut(Schema):
    reinviati: int


@router.post("/babbo-natale/scambi/{scambio_id}/reinvia", response=ReinviatiOut)
def reinvia(request, scambio_id: int, dati: PersoneIn):
    """Notification and email again to the chosen participants (DEC-422)."""
    scambio = _gestibile(request, scambio_id)
    if not dati.persone:
        raise HttpError(400, "Scegli a chi rimandare l'avviso.")
    persone = list(Persona.objects.filter(pk__in=dati.persone))
    return {"reinviati": _o_errore(servizi.reinvia, scambio, persone, request.auth)}
