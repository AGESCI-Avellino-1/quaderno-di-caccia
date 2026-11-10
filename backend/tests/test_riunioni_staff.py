"""Staff meetings (DEC-401) and meetings online or mixed (DEC-402)."""

from datetime import date, timedelta

import pytest
from django.core import mail
from django.test import Client
from django.utils import timezone

from apps.eventi import calendario
from apps.eventi.models import Evento, RiunioneRicorrente
from apps.impostazioni.models import Impostazioni
from apps.organizzazione.models import Composizione, Incarico, RuoloIncarico, TipoUnita, Unita
from tests.conftest import INIZIO_ANNO, crea_capo

pytestmark = pytest.mark.django_db

MEET = "https://meet.google.com/abc-defg-hij"


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


def _post(chi, url, dati=None):
    return _client(chi).post(url, dati or {}, content_type="application/json")


def _put(chi, url, dati):
    return _client(chi).put(url, dati, content_type="application/json")


def _sabato(settimane: int = 1) -> date:
    oggi = timezone.localdate()
    return oggi + timedelta(days=(5 - oggi.weekday()) % 7 + 7 * settimane)


def _singola(unita, **altro):
    return {
        "unita": [u.pk for u in unita],
        "giorno": _sabato(1).isoformat(),
        "ora_inizio": "21:00",
        "ora_fine": "22:30",
        "uniforme": False,
        **altro,
    }


@pytest.fixture(autouse=True)
def email_accese():
    imp = Impostazioni.carica()
    imp.email_capi = imp.email_genitori = imp.email_ragazzi = True
    imp.save()


@pytest.fixture
def branco(gruppo) -> Unita:
    return Unita.objects.create(
        gruppo=gruppo, nome="Branco Prova", tipo=TipoUnita.BRANCO, composizione=Composizione.MISTA
    )


@pytest.fixture
def akela(branco, coca):
    persona = crea_capo("Paolo", "Branco", "akela@example.invalid")
    Incarico.objects.create(
        persona=persona, ruolo=RuoloIncarico.CAPO_UNITA, unita=branco, data_inizio=INIZIO_ANNO
    )
    return persona


@pytest.fixture
def altro_capo(coca):
    """A capo of the Co.Ca. serving neither unit."""
    return crea_capo("Carla", "Altra", "altra@example.invalid")


def _staff_congiunti(capo, reparto, branco, **altro) -> dict:
    risposta = _post(
        capo, "/api/v1/riunioni", _singola([reparto, branco], cerchia="STAFF", **altro)
    )
    assert risposta.status_code == 201, risposta.content
    return risposta.json()[0]


def test_staff_congiunti_di_unita_non_collegate(capo, akela, capogruppo, reparto, branco):
    riunione = _staff_congiunti(capo, reparto, branco)
    assert riunione["titolo"] == "Riunione degli staff di Reparto Prova e Branco Prova"
    assert riunione["cerchia"] == "STAFF"
    evento = Evento.objects.get(pk=riunione["id"])
    invitati = set(evento.partecipazioni.values_list("persona_id", flat=True))
    # The staffs of both units; the capogruppo outside them is not invited (DEC-401).
    assert invitati == {capo.pk, akela.pk}


def test_chi_crea_una_riunione_di_staff(
    capo, akela, capogruppo, altro_capo, csq, genitore, reparto, branco
):
    corpo = _singola([reparto], cerchia="STAFF")
    for chi in (altro_capo, csq, genitore):
        assert _post(chi, "/api/v1/riunioni", corpo).status_code == 403
    assert _post(akela, "/api/v1/riunioni", corpo).status_code == 403  # not their unit
    singola = _post(capogruppo, "/api/v1/riunioni", corpo).json()[0]
    assert singola["titolo"] == "Riunione di staff di Reparto Prova"
    # One staff serving one of the two units creates the joint meeting.
    assert (
        _post(akela, "/api/v1/riunioni", _singola([reparto, branco], cerchia="STAFF")).status_code
        == 201
    )


def test_la_coca_non_e_uno_staff(capogruppo, coca):
    corpo = _singola([coca], cerchia="STAFF")
    assert _post(capogruppo, "/api/v1/riunioni", corpo).status_code == 400


def test_chi_vede_una_riunione_di_staff(
    capo, akela, capogruppo, altro_capo, csq, ragazza, genitore, estraneo, reparto, branco
):
    riunione = _staff_congiunti(capo, reparto, branco)
    url = f"/api/v1/eventi/{riunione['id']}"
    for chi in (capo, akela, capogruppo):
        assert _client(chi).get(url).status_code == 200
    for chi in (altro_capo, csq, ragazza, genitore, estraneo):
        assert _client(chi).get(url).status_code == 404
        elenco = _client(chi).get("/api/v1/eventi?riunioni=true").json()
        assert riunione["id"] not in [e["id"] for e in elenco]
    # Not even in the view of the whole group of the calendar.
    assert not calendario.eventi_del_calendario(altro_capo.utente, "gruppo").filter(
        pk=riunione["id"]
    )
    assert calendario.eventi_del_calendario(akela.utente, "unita").filter(pk=riunione["id"])


def test_verbale_e_ordine_del_giorno_di_staff(capo, akela, capogruppo, altro_capo, reparto, branco):
    riunione = _staff_congiunti(capo, reparto, branco, ordine_del_giorno="<p>Passaggi</p>")
    odg = f"/api/v1/eventi/{riunione['id']}/ordine-del-giorno"
    assert "Passaggi" in _client(akela).get(odg).json()["testo"]
    assert _client(altro_capo).get(odg).status_code == 404
    verbale = f"/api/v1/eventi/{riunione['id']}/verbale"
    assert _put(akela, verbale, {"testo": "<p>Deciso</p>"}).status_code == 200
    assert _put(capogruppo, verbale, {"testo": "<p>No</p>"}).status_code == 403
    assert _post(akela, f"{verbale}/definitivo").status_code == 200
    # Who is invited and the capigruppo, not every capo (DEC-401).
    for chi in (capo, akela, capogruppo):
        assert _client(chi).get(f"{verbale}?testo=true").status_code == 200
    assert _client(altro_capo).get(f"{verbale}?testo=true").status_code == 404


def test_coca_online_con_il_link(capogruppo, coca, django_capture_on_commit_callbacks):
    corpo = _singola([coca], modalita="ONLINE", link=MEET, localita_id=None)
    assert _post(capogruppo, "/api/v1/riunioni", {**corpo, "link": ""}).status_code == 400
    assert (
        _post(capogruppo, "/api/v1/riunioni", {**corpo, "link": "http://x.it"}).status_code == 400
    )
    riunione = _post(capogruppo, "/api/v1/riunioni", corpo).json()[0]
    assert (riunione["modalita"], riunione["link"], riunione["luogo"]) == ("ONLINE", MEET, "")
    evento = Evento.objects.get(pk=riunione["id"])
    feed = calendario.ics([evento])
    assert f"LOCATION:{MEET}" in feed and "DESCRIPTION:Link della riunione" in feed
    # Moved online, then mixed: the email carries the link.
    url = f"/api/v1/riunioni/{riunione['id']}"
    corpo = {"inizio": riunione["inizio"], "fine": riunione["fine"], "uniforme": False}
    with django_capture_on_commit_callbacks(execute=True):
        cambiata = _put(
            capogruppo,
            url,
            {**corpo, "modalita": "MISTA", "link": MEET, "nuova_localita": {"nome": "Sede"}},
        ).json()
    assert (cambiata["modalita"], cambiata["luogo"]) == ("MISTA", "Sede")
    assert mail.outbox and f"a Sede e online: {MEET}" in mail.outbox[0].body
    # An app not yet updated does not send the mode: nothing changes.
    rimasta = _put(capogruppo, url, {**corpo, "luogo": "Sede"}).json()
    assert (rimasta["modalita"], rimasta["link"]) == ("MISTA", MEET)
    # In person again: no link left.
    assert _put(capogruppo, url, {**corpo, "modalita": "PRESENZA"}).json()["link"] == ""


def test_dove_si_puo_essere_online(capo, capogruppo, reparto):
    # A unit meeting and the assembly stay in person (DEC-402).
    corpo = _singola([reparto], modalita="ONLINE", link=MEET)
    assert _post(capo, "/api/v1/riunioni", corpo).status_code == 400
    assemblea = {**_singola([], cerchia="SOCI", modalita="MISTA", link=MEET), "di_gruppo": True}
    assert _post(capogruppo, "/api/v1/riunioni", assemblea).status_code == 400
    genitori = _singola([reparto], cerchia="GENITORI", modalita="MISTA", link=MEET)
    assert _post(capo, "/api/v1/riunioni", genitori).json()[0]["modalita"] == "MISTA"
    staff = _singola([reparto], cerchia="STAFF", modalita="ONLINE", link=MEET)
    assert _post(capo, "/api/v1/riunioni", staff).json()[0]["modalita"] == "ONLINE"


def test_serie_di_staff_online_cambiata(capo, reparto):
    corpo = {
        "unita": [reparto.pk],
        "cerchia": "STAFF",
        "giorno_settimana": 2,
        "ora_inizio": "21:00",
        "ora_fine": "22:30",
        "dal": _sabato(1).isoformat(),
        "al": _sabato(4).isoformat(),
        "uniforme": False,
        "modalita": "ONLINE",
        "link": MEET,
    }
    riunioni = _post(capo, "/api/v1/riunioni", corpo).json()
    assert {(r["modalita"], r["link"]) for r in riunioni} == {("ONLINE", MEET)}
    serie = RiunioneRicorrente.objects.get()
    # One meeting in person; then the series moves to another link: that one stays.
    prima = riunioni[0]
    _put(
        capo,
        f"/api/v1/riunioni/{prima['id']}",
        {"inizio": prima["inizio"], "fine": prima["fine"], "modalita": "PRESENZA"},
    )
    nuovo = "https://meet.google.com/zzz-zzzz-zzz"
    risposta = _put(capo, f"/api/v1/riunioni/serie/{serie.pk}", {"uniforme": False, "link": nuovo})
    assert risposta.json()["link"] == nuovo
    eventi = Evento.objects.filter(riunione=serie).order_by("inizio")
    assert [(e.modalita, e.link) for e in eventi] == [("PRESENZA", "")] + [("ONLINE", nuovo)] * (
        len(riunioni) - 1
    )
