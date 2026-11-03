"""Turns of the patrols and of the sestiglie (DEC-312)."""

from datetime import date, datetime, time, timedelta

import pytest
from django.test import Client
from django.utils import timezone

from apps.anagrafica.models import Appartenenza, RuoloAppartenenza
from apps.eventi import servizi
from apps.eventi.models import Evento, Livello, Rotazione, TipoEvento, TurniUnita
from apps.organizzazione.models import Composizione, Squadriglia, TipoUnita, Unita
from tests.conftest import INIZIO_ANNO, crea_persona, nato_anni_fa

pytestmark = pytest.mark.django_db
ROMA = timezone.get_default_timezone()


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


def _riunione(unita, giorno: date, utente):
    return servizi.crea(
        Evento(
            titolo="Riunione",
            tipo=TipoEvento.RIUNIONE,
            livello=Livello.UNITA,
            inizio=datetime.combine(giorno, time(16), ROMA),
            fine=datetime.combine(giorno, time(18), ROMA),
        ),
        [unita],
        utente,
    )


def _turni_di(evento) -> dict[str, str]:
    from apps.eventi import turni

    return {a["turno"]: str(a["gruppo"]) for a in turni.assegnazioni(evento)}


@pytest.fixture
def due_squadriglie(reparto, squadriglia):
    altra = Squadriglia.objects.create(unita=reparto, nome="Volpi", sesso="M")
    return squadriglia, altra


@pytest.fixture
def sabati():
    oggi = timezone.localdate()
    primo = oggi + timedelta(days=(5 - oggi.weekday()) % 7 + 7)
    return [primo + timedelta(weeks=i) for i in range(4)]


def test_rotazione_settimanale_salta_le_annullate(capo, reparto, due_squadriglie, sabati):
    leoni, volpi = due_squadriglie
    riunioni = [_riunione(reparto, g, capo.utente) for g in sabati]
    TurniUnita.objects.create(unita=reparto, nomi=["Pulizia", "Preghiera"], dal=sabati[0])
    primi = _turni_di(riunioni[0])
    assert primi == {"Pulizia": str(sorted([leoni, volpi], key=lambda s: s.nome)[0]),
                     "Preghiera": str(sorted([leoni, volpi], key=lambda s: s.nome)[1])}  # fmt: skip
    assert _turni_di(riunioni[1]) == {"Pulizia": primi["Preghiera"], "Preghiera": primi["Pulizia"]}
    # The second meeting is cancelled: the third takes its turns.
    servizi.annulla(riunioni[1], "Pioggia")
    assert _turni_di(riunioni[2]) == {"Pulizia": primi["Preghiera"], "Preghiera": primi["Pulizia"]}


def test_rotazione_mensile_alla_prima_riunione_del_mese(capo, reparto, due_squadriglie):
    giorni = [date(2027, 1, 9), date(2027, 1, 23), date(2027, 2, 6), date(2027, 4, 3)]
    riunioni = [_riunione(reparto, g, capo.utente) for g in giorni]
    TurniUnita.objects.create(
        unita=reparto, nomi=["Pulizia"], dal=giorni[0], rotazione=Rotazione.MENSILE
    )
    turni = [_turni_di(r)["Pulizia"] for r in riunioni]
    assert turni[0] == turni[1] != turni[2]
    assert turni[3] == turni[0]  # March had no meetings: April is the third month


def test_api_dello_staff_e_cambio_a_mano(
    capo, ragazza, csq, genitore, reparto, due_squadriglie, sabati
):
    riunioni = [_riunione(reparto, g, capo.utente) for g in sabati]
    url = f"/api/v1/unita/{reparto.pk}/turni"
    corpo = {"nomi": ["Pulizia", " ", "Preghiera"], "dal": sabati[0].isoformat()}
    assert _client(csq).put(url, corpo, content_type="application/json").status_code == 403
    risposta = _client(capo).put(url, corpo, content_type="application/json").json()
    assert risposta["nomi"] == ["Pulizia", "Preghiera"]
    assert len(risposta["prossime"]) == 4
    leoni = due_squadriglie[0]
    # The family of Giulia (Leoni) sees only the Leoni's turn.
    visti = _client(genitore).get(f"/api/v1/eventi/{riunioni[0].pk}").json()["turni"]
    assert [(t["gruppo"], t["mio"]) for t in visti] == [(str(leoni), True)]
    assert len(_client(capo).get(f"/api/v1/eventi/{riunioni[0].pk}").json()["turni"]) == 2
    # By hand: this meeting's cleaning to the Volpi; the next ones as planned.
    prima = _turni_di(riunioni[1])
    cambio = {"turno": "Pulizia", "squadriglia_id": due_squadriglie[1].pk}
    fatto = (
        _client(capo)
        .put(f"/api/v1/riunioni/{riunioni[0].pk}/turni", cambio, content_type="application/json")
        .json()
    )
    assert {t["turno"]: t["cambiato"] for t in fatto["turni"]}["Pulizia"] is True
    assert _turni_di(riunioni[0])["Pulizia"] == str(due_squadriglie[1])
    assert _turni_di(riunioni[1]) == prima


def test_sestiglie_del_branco(gruppo, coca, capogruppo, capo):
    branco = Unita.objects.create(
        gruppo=gruppo, nome="Branco", tipo=TipoUnita.BRANCO, composizione=Composizione.MISTA
    )
    lupi = []
    for nome in ("Lino", "Lia"):
        lupo = crea_persona(nome, "Lupo", data_nascita=nato_anni_fa(9))
        Appartenenza.objects.create(
            persona=lupo, unita=branco, ruolo=RuoloAppartenenza.RAGAZZO, data_inizio=INIZIO_ANNO
        )
        lupi.append(lupo)
    url = f"/api/v1/unita/{branco.pk}/sestiglie"
    assert (
        _client(capo).post(url, {"nome": "Bianchi"}, content_type="application/json").status_code
        == 403
    )
    dati = (
        _client(capogruppo).post(url, {"nome": "Bianchi"}, content_type="application/json").json()
    )
    (bianchi,) = dati["sestiglie"]
    assert len(dati["senza_sestiglia"]) == 2
    _client(capogruppo).post(url, {"nome": "Neri"}, content_type="application/json")
    dati = (
        _client(capogruppo)
        .post(
            f"/api/v1/sestiglie/{bianchi['id']}/membri",
            {"persona_id": lupi[0].pk},
            content_type="application/json",
        )
        .json()
    )
    assert [m["persona"]["nome"] for m in dati["sestiglie"][0]["membri"]] == ["Lino"]
    assert [b["nome"] for b in dati["senza_sestiglia"]] == ["Lia"]
    # One at a time: moved to the other.
    neri = dati["sestiglie"][1]["id"]
    dati = (
        _client(capogruppo)
        .post(
            f"/api/v1/sestiglie/{neri}/membri",
            {"persona_id": lupi[0].pk},
            content_type="application/json",
        )
        .json()
    )
    assert [len(s["membri"]) for s in dati["sestiglie"]] == [0, 1]
    # Leaving the branco ends the sestiglia.
    from apps.organizzazione.servizi import esci_dal_reparto

    esci_dal_reparto(lupi[0], branco, timezone.localdate() + timedelta(days=1))
    from apps.eventi.models import MembroSestiglia

    assert MembroSestiglia.objects.get(persona=lupi[0], sestiglia_id=neri).data_fine
