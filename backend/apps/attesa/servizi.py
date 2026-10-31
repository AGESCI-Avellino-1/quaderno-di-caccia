"""The waiting list (DEC-256…DEC-263).

Who leaves the list leaves no data (DEC-263): `esci` deletes the entry and counts it,
without names, in `ConteggioAttesa`.
"""

from dataclasses import dataclass
from datetime import date, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.core.anno import AnnoAssociativo, eta_al_riferimento, eta_in_data
from apps.impostazioni.email import invia
from apps.organizzazione.models import Composizione, Gruppo, TipoUnita, Unita

from .models import ConteggioAttesa, InAttesa, StatoAttesa

# How long before the question on the interest, and how long to answer it (DEC-262).
DUE_ANNI = 365 * 2
GIORNI_PER_RISPONDERE = 30
PROMEMORIA_DOPO = 15
# The personal code sent to join (DEC-261) stays valid this long.
VALIDITA_CODICE = timedelta(days=30)


# --- Ages and units -------------------------------------------------------------------------


def _riferimento() -> tuple[int, int]:
    gruppo = Gruppo.objects.first()
    if gruppo is None:
        return 4, 30
    return gruppo.mese_riferimento_eta, gruppo.giorno_riferimento_eta


def eta(data_nascita: date, anno: AnnoAssociativo) -> int:
    """Age in the associative year, at the group's reference date (DEC-37)."""
    mese, giorno = _riferimento()
    return eta_al_riferimento(data_nascita, anno, mese, giorno)


def unita_della_lista():
    """The active units a child may join: not the Co.Ca."""
    return Unita.objects.filter(attiva=True).exclude(tipo=TipoUnita.COMUNITA_CAPI)


def consigliate(voce: InAttesa, anno: AnnoAssociativo) -> list[Unita]:
    """Units whose ages include the child's in `anno` and that take their sex
    (DEC-259, DEC-260): hints, never constraints."""
    anni = eta(voce.data_nascita, anno)
    risultato = []
    for unita in unita_della_lista():
        limiti = unita.eta
        if limiti is None or not (limiti[0] <= anni <= limiti[1]):
            continue
        if unita.composizione in (Composizione.MISTA, voce.sesso):
            risultato.append(unita)
    return risultato


def primo_anno_con_l_eta(data_nascita: date) -> AnnoAssociativo | None:
    """The first associative year in which the child has the minimum age of a unit of the
    group, even if already past; None if the group has no unit to join."""
    minime = [u.eta[0] for u in unita_della_lista() if u.eta is not None]
    if not minime:
        return None
    anno = AnnoAssociativo(data_nascita.year + min(minime) - 1)
    while eta(data_nascita, anno) < min(minime):
        anno = anno.successivo()
    return anno


def anno_contattabile(data_nascita: date) -> AnnoAssociativo | None:
    """From which associative year the child may be contacted (DEC-257): the first with
    the minimum age of a unit, not before the current one."""
    anno = primo_anno_con_l_eta(data_nascita)
    if anno is None:
        return None
    corrente = AnnoAssociativo.corrente()
    return anno if anno.anno_fine > corrente.anno_fine else corrente


def scadenza_interesse(voce: InAttesa) -> date | None:
    """When to ask whether the interest remains (DEC-262): two years after entering or
    the last confirmation, counted from when the child has the minimum age of a unit."""
    anno = primo_anno_con_l_eta(voce.data_nascita)
    if anno is None:
        return None
    partenza = max(voce.confermato_il or voce.creato_il.date(), anno.inizio)
    return partenza + timedelta(days=DUE_ANNI)


# --- Counting (DEC-263) ---------------------------------------------------------------------


def _conta(campo: str) -> None:
    anno = AnnoAssociativo.corrente().anno_fine
    ConteggioAttesa.objects.get_or_create(anno=anno)
    ConteggioAttesa.objects.filter(anno=anno).update(**{campo: F(campo) + 1})


def esci(voce: InAttesa, *, iscritto: bool = False) -> None:
    """Out of the list, whatever the reason: the data go (DEC-263)."""
    voce.delete()
    _conta("iscritti" if iscritto else "usciti")


# --- Emails ---------------------------------------------------------------------------------


def link_personale(voce: InAttesa) -> str:
    return f"{settings.FRONTEND_URL}/lista-attesa/{voce.token}"


def _valori(voce: InAttesa) -> dict[str, str]:
    anno = anno_contattabile(voce.data_nascita)
    if anno is None:
        quando = "quando il gruppo avrà un'unità adatta alla sua età"
    elif anno.anno_fine == AnnoAssociativo.corrente().anno_fine:
        quando = f"già da quest'anno scout ({anno.etichetta})"
    else:
        quando = f"dall'anno scout {anno.etichetta}"
    return {
        "Ragazzo": f"{voce.nome} {voce.cognome}",
        "Link": link_personale(voce),
        "Quando": quando,
    }


def manda_conferma(voce: InAttesa) -> None:
    invia("attesa_conferma", _valori(voce), [voce.email])


def manda_link(email: str) -> int:
    """The personal links of every entry with this address; nothing if there is none,
    and the caller answers the same either way (DEC-257)."""
    voci = InAttesa.objects.filter(email__iexact=email.strip())
    for voce in voci:
        invia("attesa_link", _valori(voce), [voce.email])
    return len(voci)


# --- Entering and changing ------------------------------------------------------------------

CAMPI = (
    "nome",
    "cognome",
    "sesso",
    "data_nascita",
    "luogo_nascita",
    "da_se",
    "contatto_nome",
    "contatto_cognome",
    "telefono",
    "email",
    "indirizzo",
    "comune",
    "provincia",
    "cap",
)


@dataclass
class DatiAttesa:
    nome: str
    cognome: str
    sesso: str
    data_nascita: date
    luogo_nascita: str
    da_se: bool
    contatto_nome: str
    contatto_cognome: str
    telefono: str
    email: str
    indirizzo: str
    comune: str
    provincia: str
    cap: str


def _applica(voce: InAttesa, dati: DatiAttesa) -> None:
    for campo in CAMPI:
        valore = getattr(dati, campo)
        setattr(voce, campo, valore.strip() if isinstance(valore, str) else valore)
    voce.email = voce.email.lower()
    voce.provincia = voce.provincia.upper()
    if voce.da_se:
        if eta_in_data(voce.data_nascita, timezone.localdate()) < 18:
            raise ValidationError("Chi è minorenne lo mette in lista un genitore.")
        voce.contatto_nome, voce.contatto_cognome = voce.nome, voce.cognome
    if voce.data_nascita > timezone.localdate():
        raise ValidationError("La data di nascita non può essere nel futuro.")
    if not (voce.cap.isdigit() and len(voce.cap) == 5):
        raise ValidationError("Il CAP ha 5 cifre.")
    voce.full_clean(exclude=["inserito_da", "contattato_per", "contattato_da"])


@transaction.atomic
def inserisci(dati: DatiAttesa, utente=None) -> InAttesa:
    """From the public form, or by a capo (DEC-258); the confirmation email either way."""
    voce = InAttesa(privacy_accettata_il=timezone.now(), inserito_da=utente)
    _applica(voce, dati)
    voce.save()
    _conta("entrati")
    transaction.on_commit(lambda: manda_conferma(voce))
    return voce


def modifica(voce: InAttesa, dati: DatiAttesa) -> InAttesa:
    _applica(voce, dati)
    voce.save()
    return voce


def conferma_interesse(voce: InAttesa) -> None:
    """The family still wants it (DEC-262): the question comes back in two years."""
    voce.confermato_il = timezone.localdate()
    voce.conferma_chiesta_il = None
    voce.promemoria_il = None
    voce.save(update_fields=["confermato_il", "conferma_chiesta_il", "promemoria_il"])


# --- The capi ---------------------------------------------------------------------------------


def segna_contatto(voce: InAttesa, unita: Unita | None, utente) -> None:
    """Contacted for a unit, or back to "da contattare" (DEC-261)."""
    if unita is None:
        voce.stato = StatoAttesa.DA_CONTATTARE
        voce.contattato_per = voce.contattato_il = voce.contattato_da = None
    else:
        voce.stato = StatoAttesa.CONTATTATO
        voce.contattato_per = unita
        voce.contattato_il = timezone.localdate()
        voce.contattato_da = utente
    voce.save()


@transaction.atomic
def iscrivi(voce: InAttesa, unita: Unita, utente):
    """The family (or the adult) gets a personal registration code for `unita` with the
    list's data, and the registration goes on as one from the app (DEC-261, DEC-120…
    DEC-127). The entry leaves the list."""
    from apps.iscrizioni.models import CodiceIscrizione, TipoCodice

    if unita.tipo == TipoUnita.COMUNITA_CAPI or not unita.attiva:
        raise ValidationError("Scegli un'unità attiva del gruppo.")
    codice = CodiceIscrizione.objects.create(
        unita=unita,
        tipo=TipoCodice.PERSONALE,
        scadenza=timezone.localdate() + VALIDITA_CODICE,
        creato_da=utente,
        dati_proposti={
            "nome": voce.nome,
            "cognome": voce.cognome,
            "data_nascita": voce.data_nascita.isoformat(),
            "sesso": voce.sesso,
            "luogo_nascita": voce.luogo_nascita,
            "indirizzo": voce.indirizzo,
            "comune": voce.comune,
            "provincia": voce.provincia,
            "cap": voce.cap,
            "da_se": voce.da_se,
            "contatto_nome": voce.contatto_nome,
            "contatto_cognome": voce.contatto_cognome,
            "telefono": voce.telefono,
            "email": voce.email,
        },
    )
    valori = {
        "Ragazzo": f"{voce.nome} {voce.cognome}",
        "Unità": str(unita),
        "Link": f"{settings.FRONTEND_URL}/iscrizione/{codice.codice}",
        "Scadenza": codice.scadenza.strftime("%d/%m/%Y"),
    }
    indirizzo = voce.email
    esci(voce, iscritto=True)
    transaction.on_commit(lambda: invia("attesa_iscrizione", valori, [indirizzo]))
    return codice


# --- Daily (DEC-262) ---------------------------------------------------------------------------


def promemoria(oggi: date) -> dict[str, int]:
    """Ask whether the interest remains, remind halfway, take out who never answered."""
    fatti = {"chiesti": 0, "ricordati": 0, "usciti": 0}
    for voce in InAttesa.objects.filter(stato=StatoAttesa.DA_CONTATTARE):
        if voce.conferma_chiesta_il is None:
            scadenza = scadenza_interesse(voce)
            if scadenza is not None and scadenza <= oggi:
                voce.conferma_chiesta_il = oggi
                voce.save(update_fields=["conferma_chiesta_il"])
                invia("attesa_interesse", _valori(voce), [voce.email])
                fatti["chiesti"] += 1
            continue
        giorni = (oggi - voce.conferma_chiesta_il).days
        if giorni >= GIORNI_PER_RISPONDERE:
            valori, indirizzo = _valori(voce), voce.email
            esci(voce)
            invia("attesa_uscita", valori, [indirizzo])
            fatti["usciti"] += 1
        elif giorni >= PROMEMORIA_DOPO and voce.promemoria_il is None:
            voce.promemoria_il = oggi
            voce.save(update_fields=["promemoria_il"])
            invia("attesa_interesse", _valori(voce), [voce.email])
            fatti["ricordati"] += 1
    return fatti
