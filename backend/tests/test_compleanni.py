"""Birthdays (DEC-417): who sees whose in the calendar, who is told in the morning."""

import json
from datetime import date, timedelta

import pytest
from django.core.management import call_command
from django.test import Client

from apps.anagrafica.compleanni import compleanni_tra, compleanno_nel
from apps.anagrafica.compleanni import testo_notifica as frase
from apps.anagrafica.models import Appartenenza, RuoloAppartenenza
from apps.iscrizioni.models import RichiestaIscrizione, StatoIscrizione
from apps.notifiche import servizi
from apps.notifiche.models import PreferenzePush
from apps.organizzazione.models import Composizione, Incarico, RuoloIncarico, TipoUnita, Unita
from apps.permessi import policy

from .conftest import INIZIO_ANNO, crea_capo, crea_persona

pytestmark = pytest.mark.django_db

ENDPOINT = "https://fcm.googleapis.com/fcm/send/"


def oggi_di(anni: int) -> date:
    """Born `anni` years ago today: the birthday is today (multiples of 4, for 29 February)."""
    oggi = date.today()
    return compleanno_nel(oggi, oggi.year - anni)


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


def _membro(unita, nome, login=None, anni=10, ruolo=RuoloAppartenenza.RAGAZZO):
    persona = crea_persona(nome, "Prova", login, data_nascita=oggi_di(anni))
    Appartenenza.objects.create(persona=persona, unita=unita, ruolo=ruolo, data_inizio=INIZIO_ANNO)
    return persona


@pytest.fixture
def branco(gruppo) -> Unita:
    return Unita.objects.create(
        gruppo=gruppo, nome="Branco Prova", tipo=TipoUnita.BRANCO, composizione=Composizione.MISTA
    )


@pytest.fixture
def gruppo_intero(capo, capogruppo, ragazza, csq, genitore, estraneo, branco, reparto):
    """Everyone has the birthday today, so the rules are all that decides."""
    for persona in (capo, capogruppo, ragazza, csq):
        persona.data_nascita = oggi_di(36 if persona in (capo, capogruppo) else 12)
        persona.save()
    genitore.data_nascita = oggi_di(40)
    genitore.save()
    lupetto = _membro(branco, "Lupo", "lupo@example.invalid", anni=8)
    akela = crea_capo("Akela", "Branco", "akela@example.invalid")
    akela.data_nascita = oggi_di(32)
    akela.save()
    Incarico.objects.create(
        persona=akela, ruolo=RuoloIncarico.CAPO_UNITA, unita=branco, data_inizio=INIZIO_ANNO
    )
    return {"lupetto": lupetto, "akela": akela}


def _nomi(queryset) -> set[str]:
    return set(queryset.values_list("nome", flat=True))


# --- Policy ----------------------------------------------------------------------------------


def test_i_capi_vedono_tutto_il_gruppo(capo, capogruppo, gruppo_intero):
    # The parent (Mario) has the birthday today too, and is never among them.
    tutti = {"Anna", "Bruno", "Giulia", "Sara", "Lupo", "Akela"}
    assert _nomi(policy.compleanni_visibili(capo.utente)) == tutti
    assert _nomi(policy.compleanni_visibili(capogruppo.utente)) == tutti


def test_i_ragazzi_vedono_la_loro_unita_e_il_suo_staff(ragazza, csq, gruppo_intero):
    # The capo unità of the reparto, not the capogruppo nor the branco.
    assert _nomi(policy.compleanni_visibili(ragazza.utente)) == {"Giulia", "Sara", "Anna"}
    assert _nomi(policy.compleanni_visibili(csq.utente)) == {"Giulia", "Sara", "Anna"}
    assert _nomi(policy.compleanni_visibili(gruppo_intero["lupetto"].utente)) == {"Lupo", "Akela"}


def test_genitori_ed_estranei_niente(genitore, estraneo, gruppo_intero):
    for chi in (genitore, estraneo):
        assert not policy.riceve_compleanni(chi.utente)
        assert not policy.compleanni_visibili(chi.utente).exists()
        assert not policy.compleanni_notificati(chi.utente).exists()


def test_unita_collegate(ragazza, reparto, gruppo):
    altro = Unita.objects.create(
        gruppo=gruppo, nome="Altro", tipo=TipoUnita.REPARTO, composizione=Composizione.MISTA
    )
    reparto.collegata_a = altro
    reparto.save()
    altro.collegata_a = reparto
    altro.save()
    _membro(altro, "Vicino")
    assert "Vicino" in _nomi(policy.compleanni_visibili(ragazza.utente))


def test_notifiche_dei_capi_solo_unita_servite_e_coca(capo, capogruppo, gruppo_intero):
    # The capo unità of the reparto: the reparto and the Co.Ca., not the branco; never oneself.
    assert _nomi(policy.compleanni_notificati(capo.utente)) == {"Giulia", "Sara", "Bruno", "Akela"}
    # A capogruppo serves no unit: the Co.Ca. only.
    assert _nomi(policy.compleanni_notificati(capogruppo.utente)) == {"Anna", "Akela"}


def test_solo_soci_attivi(capo, ragazza, csq, reparto):
    for persona in (ragazza, csq):
        persona.data_nascita = oggi_di(12)
        persona.save()
    # Who left (or is suspended: every period closed).
    Appartenenza.objects.filter(persona=csq).update(data_fine=date.today())
    nuovo = _membro(reparto, "Nuovo")
    RichiestaIscrizione.objects.create(
        unita=reparto,
        nome="Nuovo",
        cognome="Prova",
        data_nascita=nuovo.data_nascita,
        codice_fiscale="XXXXXX00X00X000X",
        stato=StatoIscrizione.APPROVATA,
        persona=nuovo,
    )
    assert _nomi(policy.compleanni_visibili(capo.utente)) == {"Giulia", "Anna"}
    # The one who left no longer gets anything either.
    assert not policy.riceve_compleanni(csq.utente)


def test_capo_con_codice_provvisorio_come_gli_altri(capo, ragazza):
    capo.codice_socio = "9000000001"
    capo.save()
    assert policy.e_capo_in_attesa(capo.utente)
    ragazza.data_nascita = oggi_di(12)
    ragazza.save()
    assert "Giulia" in _nomi(policy.compleanni_visibili(capo.utente))


# --- Days and texts --------------------------------------------------------------------------


def test_29_febbraio_e_anni():
    assert compleanno_nel(date(2012, 2, 29), 2027) == date(2027, 2, 28)
    assert compleanno_nel(date(2012, 2, 29), 2028) == date(2028, 2, 29)


def test_compleanni_tra_a_cavallo_dell_anno(ragazza):
    ragazza.data_nascita = date(2014, 1, 2)
    ragazza.save()
    elenco = compleanni_tra([ragazza], date(2026, 12, 20), date(2027, 1, 10))
    assert [(c.giorno, c.anni) for c in elenco] == [(date(2027, 1, 2), 13)]
    # Not before being born.
    assert compleanni_tra([ragazza], date(2013, 12, 20), date(2014, 1, 10)) == []


def test_testo_della_notifica():
    assert frase(["Marco"]) == "Oggi compie gli anni Marco"
    assert frase(["Marco", "Giulia"]) == "Oggi compiono gli anni Marco e Giulia"
    assert frase(["A", "B", "C"]) == "Oggi compiono gli anni A, B e C"
    assert frase(["A", "B", "C", "D"]) == "Oggi compiono gli anni A, B e altri 2"


# --- API -------------------------------------------------------------------------------------


def test_api_del_capo(capo, gruppo_intero):
    risposta = _client(capo).get("/api/v1/calendario/compleanni")
    assert risposta.status_code == 200
    righe = {r["nome"]: r for r in risposta.json()}
    assert set(righe) == {"Anna", "Bruno", "Giulia", "Sara", "Lupo", "Akela"}
    assert righe["Giulia"]["anni"] == 12 and righe["Giulia"]["giorno"] == str(date.today())
    assert righe["Giulia"]["unita"].startswith("Reparto") and not righe["Giulia"]["coca"]
    assert righe["Akela"]["coca"] and righe["Akela"]["scheda"]
    assert _client(capo).get("/api/v1/calendario").json()["compleanni"] is True


def test_api_del_ragazzo(ragazza, gruppo_intero):
    righe = _client(ragazza).get("/api/v1/calendario/compleanni").json()
    assert {r["nome"] for r in righe} == {"Giulia", "Sara", "Anna"}
    # Co.Ca. is shown apart only to the capi; a ragazza opens only her own file.
    assert not any(r["coca"] for r in righe)
    assert {r["nome"] for r in righe if r["scheda"]} == {"Giulia"}


def test_api_del_genitore(genitore, gruppo_intero):
    assert _client(genitore).get("/api/v1/calendario/compleanni").json() == []
    assert _client(genitore).get("/api/v1/calendario").json()["compleanni"] is False


def test_api_trenta_giorni_e_limite(capo, ragazza):
    ragazza.data_nascita = date.today() - timedelta(days=30) - timedelta(days=12 * 365)
    ragazza.save()
    client = _client(capo)
    # Between 29 and 31 days from today depending on the years in between: ask for the exact day.
    giorno = compleanni_tra([ragazza], date.today(), date.today() + timedelta(days=400))[0].giorno
    entro = (giorno - date.today()).days < 30
    nomi = {r["nome"] for r in client.get("/api/v1/calendario/compleanni").json()}
    assert ("Giulia" in nomi) == entro
    dal, al = date.today(), date.today() + timedelta(days=42)
    risposta = client.get(f"/api/v1/calendario/compleanni?dal={dal}&al={al}")
    assert risposta.status_code == 400
    assert (
        client.get("/api/v1/calendario/compleanni?dal=2026-12-31&al=2026-12-01").status_code == 400
    )


def test_serve_l_accesso():
    assert Client().get("/api/v1/calendario/compleanni").status_code == 401


# --- The morning notification ----------------------------------------------------------------


@pytest.fixture
def spediti(monkeypatch):
    chiamate = []
    monkeypatch.setattr(servizi, "webpush", lambda **k: chiamate.append(k))
    return chiamate


def _iscrivi(chi):
    risposta = _client(chi).post(
        "/api/v1/push/iscrizioni",
        {"endpoint": ENDPOINT + chi.nome, "p256dh": "chiave", "auth": "segreto"},
        content_type="application/json",
    )
    assert risposta.status_code == 204, risposta.content


def _ricevute(spediti) -> dict[str, dict]:
    return {
        c["subscription_info"]["endpoint"].removeprefix(ENDPOINT): json.loads(c["data"])
        for c in spediti
    }


def test_notifica_del_mattino(capo, ragazza, genitore, spediti, gruppo_intero):
    for chi in (capo, ragazza, genitore, gruppo_intero["lupetto"]):
        _iscrivi(chi)
    call_command("avvisa_compleanni")
    ricevute = _ricevute(spediti)
    assert set(ricevute) == {"Anna", "Giulia", "Lupo"}
    # First names only, in order; four or more: two and how many others.
    assert ricevute["Anna"]["titolo"] == "Oggi compiono gli anni Akela, Bruno e altri 2"
    assert ricevute["Giulia"]["titolo"] == "Oggi compiono gli anni Anna e Sara"
    assert ricevute["Lupo"]["titolo"] == "Oggi compie gli anni Akela"
    assert ricevute["Giulia"]["percorso"] == "/calendario?mostra=compleanni"
    assert "Prova" not in json.dumps(list(ricevute.values()))


def test_notifica_spenta_nelle_preferenze(ragazza, spediti, gruppo_intero):
    _iscrivi(ragazza)
    risposta = _client(ragazza).put(
        "/api/v1/push/preferenze",
        {
            "eventi": True,
            "promemoria_quote": True,
            "riepiloghi": True,
            "avvisi": True,
            "compleanni": False,
        },
        content_type="application/json",
    )
    assert risposta.status_code == 200
    assert PreferenzePush.objects.get(persona=ragazza).compleanni is False
    call_command("avvisa_compleanni")
    assert spediti == []


def test_preferenza_nello_stato(ragazza, genitore):
    stato = _client(ragazza).get("/api/v1/push").json()
    assert stato["preferenze"]["compleanni"] is True and stato["compleanni"] is True
    assert _client(genitore).get("/api/v1/push").json()["compleanni"] is False


def test_nessun_compleanno_nessuna_notifica(ragazza, spediti):
    ragazza.data_nascita = oggi_di(12) - timedelta(days=1)
    ragazza.save()
    _iscrivi(ragazza)
    call_command("avvisa_compleanni")
    assert spediti == []
