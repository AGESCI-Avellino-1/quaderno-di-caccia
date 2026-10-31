"""The waiting list (DEC-256…DEC-263): public pages for the families, the list for the
capi. The family never sees its place in the list (DEC-257)."""

from datetime import date, datetime

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from ninja import Router, Schema, Status
from ninja.errors import HttpError
from ninja.throttling import AnonRateThrottle, AuthRateThrottle

from apps.core.anno import AnnoAssociativo
from apps.organizzazione.models import Unita
from apps.permessi import policy

from . import servizi
from .models import InAttesa, StatoAttesa

router = Router(tags=["attesa"])

# Public form and link requests: enough for a family, not for a robot.
LIMITI = [AnonRateThrottle("20/h"), AuthRateThrottle("60/h")]


def _o_errore(funzione, *argomenti, **opzioni):
    try:
        return funzione(*argomenti, **opzioni)
    except ValidationError as errore:
        raise HttpError(400, " ".join(errore.messages)) from errore


class DatiAttesaIn(Schema):
    nome: str
    cognome: str
    sesso: str
    data_nascita: date
    luogo_nascita: str
    da_se: bool = False
    contatto_nome: str = ""
    contatto_cognome: str = ""
    telefono: str
    email: str
    indirizzo: str
    comune: str
    provincia: str
    cap: str


class IscrizioneListaIn(DatiAttesaIn):
    # The short notice and the privacy policy, read and accepted (DEC-256).
    privacy: bool


class DatiAttesaOut(DatiAttesaIn):
    """What the family sees through its link: its data, never the place in the list."""

    # When the question on the interest is pending (DEC-262).
    conferma_chiesta: bool = False
    contattabile_dal: str = ""


def _dati(dati: DatiAttesaIn) -> servizi.DatiAttesa:
    campi = dati.dict()
    campi.pop("privacy", None)
    return servizi.DatiAttesa(**campi)


def _per_la_famiglia(voce: InAttesa) -> dict:
    anno = servizi.anno_contattabile(voce.data_nascita)
    return {
        **{c: getattr(voce, c) for c in servizi.CAMPI},
        "conferma_chiesta": voce.conferma_chiesta_il is not None,
        "contattabile_dal": anno.etichetta if anno else "",
    }


# --- Public: the family ------------------------------------------------------------------------


@router.post("/lista-attesa", response={201: None}, auth=None, throttle=LIMITI)
def mettiti_in_lista(request, dati: IscrizioneListaIn):
    if not dati.privacy:
        raise HttpError(400, "Per mettersi in lista serve leggere e accettare l'informativa.")
    _o_errore(servizi.inserisci, _dati(dati))
    return Status(201, None)


class EmailIn(Schema):
    email: str


@router.post("/lista-attesa/link", response={202: None}, auth=None, throttle=LIMITI)
def chiedi_link(request, dati: EmailIn):
    """Always the same answer: nobody learns who is on the list (DEC-257)."""
    servizi.manda_link(dati.email)
    return Status(202, None)


def _voce(token: str) -> InAttesa:
    voce = InAttesa.objects.filter(token=token).first()
    if voce is None:
        raise HttpError(404, "Link non valido: forse l'iscrizione alla lista non c'è più.")
    return voce


@router.get("/lista-attesa/{token}", response=DatiAttesaOut, auth=None, throttle=LIMITI)
def la_mia_iscrizione(request, token: str):
    return _per_la_famiglia(_voce(token))


@router.put("/lista-attesa/{token}", response=DatiAttesaOut, auth=None, throttle=LIMITI)
def correggi(request, token: str, dati: DatiAttesaIn):
    voce = _voce(token)
    _o_errore(servizi.modifica, voce, _dati(dati))
    return _per_la_famiglia(voce)


@router.post("/lista-attesa/{token}/conferma", response=DatiAttesaOut, auth=None, throttle=LIMITI)
def conferma(request, token: str):
    voce = _voce(token)
    servizi.conferma_interesse(voce)
    return _per_la_famiglia(voce)


@router.delete("/lista-attesa/{token}", response={204: None}, auth=None, throttle=LIMITI)
def esci_dalla_lista(request, token: str):
    servizi.esci(_voce(token))
    return Status(204, None)


# --- The capi ------------------------------------------------------------------------------------


class UnitaBreve(Schema):
    id: int
    nome: str


class VoceOut(DatiAttesaIn):
    id: int
    # Age in the current and in the next associative year (DEC-259).
    eta: int
    eta_prossimo: int
    consigliate: list[UnitaBreve]
    consigliate_prossimo: list[UnitaBreve]
    stato: StatoAttesa
    contattato_per: UnitaBreve | None
    contattato_il: date | None
    contattato_da: str
    inserito_il: datetime
    inserito_da_un_capo: bool
    possibile_doppione: bool
    conferma_chiesta_il: date | None


class ListaOut(Schema):
    anno: str
    anno_prossimo: str
    voci: list[VoceOut]
    # The units the user may act for (mark contacted, enrol), with their ages.
    unita: list[UnitaBreve]
    puo_inserire: bool


def _unita(u: Unita) -> dict:
    return {"id": u.pk, "nome": str(u)}


def _nome(utente) -> str:
    if utente is None:
        return ""
    persona = policy.persona_di(utente)
    return f"{persona.nome} {persona.cognome}" if persona else utente.email


@router.get("/attesa", response=ListaOut)
def lista(request):
    utente = request.auth
    if not policy.vede_lista_attesa(utente):
        raise HttpError(403, "La lista d'attesa la vedono i capi.")
    anno = AnnoAssociativo.corrente()
    prossimo = anno.successivo()
    voci = list(InAttesa.objects.select_related("contattato_per", "contattato_da"))
    chiavi = [(v.nome.casefold(), v.cognome.casefold(), v.data_nascita) for v in voci]
    uscita = []
    for voce, chiave in zip(voci, chiavi, strict=True):
        uscita.append(
            {
                "id": voce.pk,
                **{c: getattr(voce, c) for c in servizi.CAMPI},
                "eta": servizi.eta(voce.data_nascita, anno),
                "eta_prossimo": servizi.eta(voce.data_nascita, prossimo),
                "consigliate": [_unita(u) for u in servizi.consigliate(voce, anno)],
                "consigliate_prossimo": [_unita(u) for u in servizi.consigliate(voce, prossimo)],
                "stato": voce.stato,
                "contattato_per": _unita(voce.contattato_per) if voce.contattato_per else None,
                "contattato_il": voce.contattato_il,
                "contattato_da": _nome(voce.contattato_da),
                "inserito_il": voce.creato_il,
                "inserito_da_un_capo": voce.inserito_da_id is not None,
                "possibile_doppione": chiavi.count(chiave) > 1,
                "conferma_chiesta_il": voce.conferma_chiesta_il,
            }
        )
    return {
        "anno": anno.etichetta,
        "anno_prossimo": prossimo.etichetta,
        "voci": uscita,
        "unita": [
            _unita(u)
            for u in servizi.unita_della_lista()
            if policy.puo_gestire_lista_attesa(utente, u)
        ],
        "puo_inserire": policy.puo_gestire_lista_attesa(utente),
    }


@router.post("/attesa", response={201: None})
def inserisci(request, dati: DatiAttesaIn):
    """A capo puts someone on the list (DEC-258): the family gets the same email."""
    if not policy.puo_gestire_lista_attesa(request.auth):
        raise HttpError(403, "In lista mettono i capigruppo e gli staff delle unità.")
    _o_errore(servizi.inserisci, _dati(dati), request.auth)
    return Status(201, None)


class UnitaIn(Schema):
    unita_id: int | None = None


def _unita_scelta(request, dati: UnitaIn, obbligatoria: bool) -> Unita | None:
    if dati.unita_id is None:
        if obbligatoria:
            raise HttpError(400, "Scegli l'unità.")
        if not policy.puo_gestire_lista_attesa(request.auth):
            raise HttpError(403, "Lo segnano i capigruppo e gli staff delle unità.")
        return None
    unita = get_object_or_404(Unita, pk=dati.unita_id)
    if not policy.puo_gestire_lista_attesa(request.auth, unita):
        raise HttpError(403, "Per questa unità lo segnano il suo staff e i capigruppo.")
    return unita


@router.post("/attesa/{voce_id}/contatto", response={204: None})
def contatto(request, voce_id: int, dati: UnitaIn):
    """Contacted for a unit, or (no unit) back to "da contattare" (DEC-261)."""
    voce = get_object_or_404(InAttesa, pk=voce_id)
    unita = _unita_scelta(request, dati, obbligatoria=False)
    servizi.segna_contatto(voce, unita, request.auth)
    return Status(204, None)


@router.post("/attesa/{voce_id}/iscrivi", response={204: None})
def iscrivi(request, voce_id: int, dati: UnitaIn):
    """The family gets the link to join `unita`; the entry leaves the list (DEC-261)."""
    voce = get_object_or_404(InAttesa, pk=voce_id)
    unita = _unita_scelta(request, dati, obbligatoria=True)
    _o_errore(servizi.iscrivi, voce, unita, request.auth)
    return Status(204, None)


@router.delete("/attesa/{voce_id}", response={204: None})
def togli(request, voce_id: int):
    """Out of the list (no longer interested, a mistake): the data go (DEC-263)."""
    voce = get_object_or_404(InAttesa, pk=voce_id)
    if not policy.puo_gestire_lista_attesa(request.auth):
        raise HttpError(403, "Dalla lista tolgono i capigruppo e gli staff delle unità.")
    servizi.esci(voce)
    return Status(204, None)


# --- Ages of the units (DEC-260) ---------------------------------------------------------------


class EtaIn(Schema):
    eta_minima: int | None = None
    eta_massima: int | None = None


class EtaOut(Schema):
    eta_minima: int
    eta_massima: int


@router.put("/unita/{unita_id}/eta", response=EtaOut)
def eta_unita(request, unita_id: int, dati: EtaIn):
    """None = back to the branch's default."""
    unita = get_object_or_404(Unita, pk=unita_id)
    if unita.eta is None:
        raise HttpError(400, "La Comunità capi non ha età per la lista d'attesa.")
    if not policy.puo_modificare_eta_unita(request.auth, unita):
        raise HttpError(403, "Le età le cambiano lo staff dell'unità e i capigruppo.")
    unita.eta_minima, unita.eta_massima = dati.eta_minima, dati.eta_massima
    minima, massima = unita.eta
    if not (5 <= minima <= massima <= 25):
        raise HttpError(400, "L'età minima non può superare la massima (tra 5 e 25 anni).")
    unita.save(update_fields=["eta_minima", "eta_massima", "aggiornato_il"])
    return {"eta_minima": minima, "eta_massima": massima}
