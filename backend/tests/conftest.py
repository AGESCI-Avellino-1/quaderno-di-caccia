from datetime import date, timedelta

import pytest

from apps.accounts.models import User
from apps.anagrafica.models import Appartenenza, Persona, RelazioneTutela, RuoloAppartenenza
from apps.organizzazione.models import (
    Composizione,
    Gruppo,
    Incarico,
    RuoloIncarico,
    Squadriglia,
    TipoUnita,
    Unita,
)

INIZIO_ANNO = date(2025, 10, 1)


def nato_anni_fa(anni: int) -> date:
    """Birth date giving `anni` completed years today (tests must not age)."""
    return date.today() - timedelta(days=round(anni * 365.25) + 30)


@pytest.fixture
def gruppo(db) -> Gruppo:
    return Gruppo.objects.create(denominazione="Prova 1", ordinale="T9999")


@pytest.fixture
def reparto(gruppo) -> Unita:
    return Unita.objects.create(
        gruppo=gruppo, nome="Reparto Prova", tipo=TipoUnita.REPARTO, composizione=Composizione.MISTA
    )


@pytest.fixture
def coca(gruppo) -> Unita:
    return Unita.objects.create(
        gruppo=gruppo,
        nome="Comunità Capi",
        tipo=TipoUnita.COMUNITA_CAPI,
        composizione=Composizione.MISTA,
    )


@pytest.fixture
def squadriglia(reparto) -> Squadriglia:
    return Squadriglia.objects.create(unita=reparto, nome="Aquile", sesso="F")


def crea_persona(nome: str, cognome: str, login: str | None = None, **campi) -> Persona:
    """Create a Persona; with `login` also a User account with that email."""
    utente = User.objects.create_user(email=login, password="x") if login else None  # noqa: S106
    return Persona.objects.create(nome=nome, cognome=cognome, utente=utente, **campi)


def crea_capo(nome: str, cognome: str, login: str | None = None) -> Persona:
    """A capo of the Co.Ca. of the (only) group, without roles."""
    persona = crea_persona(nome, cognome, login, data_nascita=date(1985, 1, 1))
    Appartenenza.objects.create(
        persona=persona,
        unita=Unita.objects.get(tipo=TipoUnita.COMUNITA_CAPI),
        ruolo=RuoloAppartenenza.CAPO,
        data_inizio=INIZIO_ANNO,
    )
    return persona


@pytest.fixture
def capo(coca, reparto) -> Persona:
    persona = crea_persona("Anna", "Capo", "capo@example.invalid", data_nascita=date(1990, 1, 1))
    Appartenenza.objects.create(
        persona=persona, unita=coca, ruolo=RuoloAppartenenza.CAPO, data_inizio=INIZIO_ANNO
    )
    Incarico.objects.create(
        persona=persona, ruolo=RuoloIncarico.CAPO_UNITA, unita=reparto, data_inizio=INIZIO_ANNO
    )
    return persona


@pytest.fixture
def capogruppo(coca, gruppo) -> Persona:
    persona = crea_persona("Bruno", "Gruppo", "cg@example.invalid", data_nascita=date(1980, 1, 1))
    Appartenenza.objects.create(
        persona=persona, unita=coca, ruolo=RuoloAppartenenza.CAPO, data_inizio=INIZIO_ANNO
    )
    Incarico.objects.create(
        persona=persona, ruolo=RuoloIncarico.CAPOGRUPPO, gruppo=gruppo, data_inizio=INIZIO_ANNO
    )
    return persona


@pytest.fixture
def ragazza(reparto, squadriglia) -> Persona:
    from apps.anagrafica.models import AppartenenzaSquadriglia

    persona = crea_persona(
        "Giulia",
        "Esploratrice",
        "giulia@example.invalid",
        data_nascita=nato_anni_fa(12),
        email="giulia@example.invalid",
        cellulare="3330000000",
    )
    Appartenenza.objects.create(
        persona=persona, unita=reparto, ruolo=RuoloAppartenenza.RAGAZZO, data_inizio=INIZIO_ANNO
    )
    AppartenenzaSquadriglia.objects.create(
        persona=persona, squadriglia=squadriglia, data_inizio=INIZIO_ANNO
    )
    return persona


@pytest.fixture
def genitore(ragazza) -> Persona:
    persona = crea_persona("Mario", "Genitore", "genitore@example.invalid")
    RelazioneTutela.objects.create(tutore=persona, minore=ragazza, tipo="GENITORE")
    return persona


@pytest.fixture
def genitrice_senza_account(ragazza) -> Persona:
    """Second parent of `ragazza`, imported from BuonaStrada and not yet invited."""
    persona = crea_persona("Lucia", "Genitore", email="lucia@example.invalid")
    RelazioneTutela.objects.create(tutore=persona, minore=ragazza, tipo="GENITORE")
    return persona


@pytest.fixture
def csq(reparto, squadriglia) -> Persona:
    from apps.anagrafica.models import AppartenenzaSquadriglia

    persona = crea_persona("Sara", "Csq", "csq@example.invalid", data_nascita=nato_anni_fa(15))
    Appartenenza.objects.create(
        persona=persona, unita=reparto, ruolo=RuoloAppartenenza.RAGAZZO, data_inizio=INIZIO_ANNO
    )
    AppartenenzaSquadriglia.objects.create(
        persona=persona, squadriglia=squadriglia, data_inizio=INIZIO_ANNO
    )
    Incarico.objects.create(
        persona=persona, ruolo=RuoloIncarico.CSQ, squadriglia=squadriglia, data_inizio=INIZIO_ANNO
    )
    return persona


@pytest.fixture
def estraneo(db) -> Persona:
    return crea_persona("Ugo", "Estraneo", "estraneo@example.invalid")
