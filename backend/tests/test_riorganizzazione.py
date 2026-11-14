"""Draft reorganisation of the patrols (DEC-410)."""

from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone

from apps.anagrafica.models import (
    Appartenenza,
    AppartenenzaSquadriglia,
    RuoloAppartenenza,
)
from apps.organizzazione import servizi
from apps.organizzazione.models import (
    AnimaleSquadriglia,
    BozzaSquadriglie,
    Composizione,
    Incarico,
    RuoloIncarico,
    Squadriglia,
    TipoUnita,
    Unita,
)
from tests.conftest import INIZIO_ANNO, crea_persona, nato_anni_fa

pytestmark = pytest.mark.django_db


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


def _json(chi, metodo, url, dati=None):
    return getattr(_client(chi), metodo)(url, dati or {}, content_type="application/json")


def _guida(nome, reparto, squadriglia=None, sesso="F", login=None):
    persona = crea_persona(nome, "Prova", login, data_nascita=nato_anni_fa(13), sesso=sesso)
    Appartenenza.objects.create(
        persona=persona, unita=reparto, ruolo=RuoloAppartenenza.RAGAZZO, data_inizio=INIZIO_ANNO
    )
    if squadriglia is not None:
        AppartenenzaSquadriglia.objects.create(
            persona=persona, squadriglia=squadriglia, data_inizio=INIZIO_ANNO
        )
    return persona


@pytest.fixture
def scena(gruppo, reparto, capo):
    """Two linked mixed reparti; three girls' patrols in the first, one in the second."""
    parallelo = Unita.objects.create(
        gruppo=gruppo, nome="Parallelo", tipo=TipoUnita.REPARTO, composizione=Composizione.MISTA
    )
    servizi.collega(reparto, parallelo, "")
    sq = {
        n: Squadriglia.objects.create(unita=u, nome=n, sesso="F")
        for n, u in (
            ("Civette", reparto),
            ("Volpi", reparto),
            ("Gazze", reparto),
            ("Linci", parallelo),
        )
    }
    persone = {
        "anna": _guida("Anna", reparto, sq["Civette"], login="anna@example.invalid"),
        "bea": _guida("Bea", reparto, sq["Volpi"]),
        "cloe": _guida("Cloe", reparto, sq["Gazze"]),
        "dora": _guida("Dora", parallelo, sq["Linci"]),
    }
    Incarico.objects.create(
        persona=persona_csq(persone), ruolo=RuoloIncarico.CSQ, squadriglia=sq["Volpi"],
        data_inizio=INIZIO_ANNO,
    )  # fmt: skip
    return {"reparto": reparto, "parallelo": parallelo, "sq": sq, "p": persone}


def persona_csq(persone):
    return persone["bea"]


def _crea(chi, reparto, giorno):
    return _json(
        chi,
        "post",
        f"/api/v1/unita/{reparto.pk}/bozza-squadriglie",
        {"data_inizio": giorno.isoformat()},
    )


def _posto(bozza, nome):
    return next(s for s in bozza["squadriglie"] if s["nome"].startswith(nome))


def test_la_bozza_non_tocca_le_squadriglie_attuali(capo, scena):
    oggi = timezone.localdate()
    bozza = _crea(capo, scena["reparto"], oggi + timedelta(days=10)).json()
    # Both reparti, every patrol, every girl where she is today, the CSQ.
    assert {s["nome"] for s in bozza["squadriglie"]} == {"Civette", "Volpi", "Gazze", "Linci"}
    assert _posto(bozza, "Volpi")["capo_id"] == scena["p"]["bea"].pk
    url = f"/api/v1/bozze-squadriglie/{bozza['id']}"
    nuova = _json(
        capo, "post", f"{url}/squadriglie", {"unita_id": scena["reparto"].pk, "sesso": "F"}
    )
    assert nuova.status_code == 201, nuova.content
    posto = _posto(nuova.json(), "Nuova squadriglia 1")["id"]
    for nome in ("anna", "bea", "cloe"):
        _json(capo, "put", f"{url}/membri/{scena['p'][nome].pk}", {"squadriglia_id": posto})
    # Nothing real changed.
    assert (
        AppartenenzaSquadriglia.objects.get(persona=scena["p"]["anna"]).squadriglia.nome
        == "Civette"
    )
    # Moving the CSQ out of Volpi left Volpi without one.
    bozza = _client(capo).get(url).json()
    assert _posto(bozza, "Volpi")["capo_id"] is None
    # Not before its first day.
    assert _json(capo, "post", f"{url}/applica").status_code == 400
    # A second draft for the linked reparto: no, the open one is shared.
    assert _crea(capo, scena["parallelo"], oggi).status_code == 400


def test_applicare_e_annullare(capo, scena):
    giorno = timezone.localdate() - timedelta(days=2)
    bozza = _crea(capo, scena["reparto"], giorno).json()
    url = f"/api/v1/bozze-squadriglie/{bozza['id']}"
    pantera = AnimaleSquadriglia.objects.get_or_create(
        nome="Pantera", defaults={"plurale": "Pantere"}
    )[0]
    risposta = _json(
        capo, "post", f"{url}/squadriglie",
        {"unita_id": scena["reparto"].pk, "animale_id": pantera.pk, "sesso": "F"},
    )  # fmt: skip
    pantere = _posto(risposta.json(), "Pantere")["id"]
    p = scena["p"]
    for nome in ("bea", "cloe"):
        _json(capo, "put", f"{url}/membri/{p[nome].pk}", {"squadriglia_id": pantere})
    # Dora goes into the linked reparto's Civette.
    civette = _posto(_client(capo).get(url).json(), "Civette")["id"]
    assert (
        _json(capo, "put", f"{url}/membri/{p['dora'].pk}", {"squadriglia_id": civette}).status_code
        == 200
    )
    guide = {"capo_id": p["bea"].pk, "vice_id": p["cloe"].pk}
    assert _json(capo, "put", f"{url}/squadriglie/{pantere}/guide", guide).status_code == 200
    applicata = _json(capo, "post", f"{url}/applica")
    assert applicata.status_code == 200, applicata.content
    # The moves from the draft's first day.
    nuova = Squadriglia.objects.get(nome="Pantere", unita=scena["reparto"])
    assert AppartenenzaSquadriglia.objects.attive().get(persona=p["bea"]).squadriglia == nuova
    assert (
        AppartenenzaSquadriglia.objects.get(persona=p["bea"], squadriglia=nuova).data_inizio
        == giorno
    )
    # Dora is now in the first reparto.
    assert Appartenenza.objects.attive().get(persona=p["dora"]).unita == scena["reparto"]
    # Volpi, Gazze and Linci are empty: archived. Bea's old CSQ role ended, the new one began.
    for nome in ("Volpi", "Gazze", "Linci"):
        assert Squadriglia.objects.get(nome=nome).attiva is False
    assert (
        Incarico.objects.attivi().get(persona=p["bea"], ruolo=RuoloIncarico.CSQ).squadriglia
        == nuova
    )
    assert Incarico.objects.attivi().get(persona=p["cloe"]).ruolo == RuoloIncarico.VCSQ
    # Undo: everything as before.
    stato = _client(capo).get(f"/api/v1/unita/{scena['reparto'].pk}/bozza-squadriglie").json()
    assert stato["applicata"]["annullabile"] is True
    assert _json(capo, "post", f"{url}/annulla").status_code == 200
    assert not Squadriglia.objects.filter(nome="Pantere").exists()
    for nome in ("Volpi", "Gazze", "Linci"):
        assert Squadriglia.objects.get(nome=nome).attiva is True
    assert (
        AppartenenzaSquadriglia.objects.attive().get(persona=p["bea"]).squadriglia.nome == "Volpi"
    )
    assert Appartenenza.objects.attive().get(persona=p["dora"]).unita == scena["parallelo"]
    assert Incarico.objects.attivi().get(persona=p["bea"]).squadriglia.nome == "Volpi"
    assert BozzaSquadriglie.objects.get().stato == "APERTA"


def test_non_si_annulla_dopo_altri_cambi(capo, scena):
    bozza = _crea(capo, scena["reparto"], timezone.localdate()).json()
    url = f"/api/v1/bozze-squadriglie/{bozza['id']}"
    _json(
        capo,
        "put",
        f"{url}/membri/{scena['p']['cloe'].pk}",
        {"squadriglia_id": _posto(bozza, "Volpi")["id"]},
    )
    _json(capo, "post", f"{url}/applica")
    # Afterwards a capo moves Anna by hand.
    membro = AppartenenzaSquadriglia.objects.attive().get(persona=scena["p"]["anna"])
    _json(capo, "post", f"/api/v1/membri-squadriglia/{membro.pk}/termina")
    risposta = _json(capo, "post", f"{url}/annulla")
    assert risposta.status_code == 400
    assert "correggi a mano" in risposta.json()["detail"]


def test_chi_arriva_dopo_resta_dove_e(capo, scena):
    bozza = _crea(capo, scena["reparto"], timezone.localdate()).json()
    url = f"/api/v1/bozze-squadriglie/{bozza['id']}"
    nuova = _guida("Ella", scena["reparto"], scena["sq"]["Gazze"])
    Appartenenza.objects.filter(persona=scena["p"]["dora"]).update(data_fine=timezone.localdate())
    differenze = _client(capo).get(url).json()["differenze"]
    assert any("Dora" in d and "ignorato" in d for d in differenze)
    assert any("Ella" in d and "resta" in d for d in differenze)
    assert _json(capo, "post", f"{url}/applica").status_code == 200
    assert AppartenenzaSquadriglia.objects.attive().get(persona=nuova).squadriglia.nome == "Gazze"


def test_i_sessi(capo, scena, gruppo):
    scena["reparto"].composizione = Composizione.FEMMINILE
    scena["reparto"].save()
    marco = _guida("Marco", scena["parallelo"], sesso="M")
    bozza = _crea(capo, scena["reparto"], timezone.localdate()).json()
    url = f"/api/v1/bozze-squadriglie/{bozza['id']}"
    # Not into a female reparto, nor into a female patrol.
    for nome in ("Civette", "Linci"):
        risposta = _json(
            capo, "put", f"{url}/membri/{marco.pk}", {"squadriglia_id": _posto(bozza, nome)["id"]}
        )
        assert risposta.status_code == 400
    maschile = {"unita_id": scena["reparto"].pk, "sesso": "M"}
    assert _json(capo, "post", f"{url}/squadriglie", maschile).status_code == 400


def test_i_futuri_capi_squadriglia_la_vedono_se_lo_staff_vuole(capo, scena):
    bozza = _crea(capo, scena["reparto"], timezone.localdate() + timedelta(days=5)).json()
    url = f"/api/v1/bozze-squadriglie/{bozza['id']}"
    anna = scena["p"]["anna"]
    _json(
        capo,
        "put",
        f"{url}/squadriglie/{_posto(bozza, 'Civette')['id']}/guide",
        {"capo_id": anna.pk},
    )
    assert _client(anna).get(url).status_code == 404
    assert _client(anna).get("/api/v1/io").json()["bozza_squadriglie"] is None
    giorno = bozza["data_inizio"]
    _json(capo, "put", url, {"data_inizio": giorno, "visibile_ai_capi_squadriglia": True})
    letta = _client(anna).get(url)
    assert letta.status_code == 200
    assert letta.json()["puo_gestire"] is False
    assert letta.json()["differenze"] == []
    assert _client(anna).get("/api/v1/io").json()["bozza_squadriglie"] == bozza["id"]
    # Read only.
    assert _json(anna, "post", f"{url}/applica").status_code == 403


@pytest.mark.parametrize("ruolo", ["capogruppo"])
def test_anche_i_capigruppo(request, ruolo, scena):
    assert (
        _crea(request.getfixturevalue(ruolo), scena["reparto"], timezone.localdate()).status_code
        == 201
    )


@pytest.mark.parametrize("ruolo", ["csq", "ragazza", "genitore", "estraneo"])
def test_gli_altri_no(request, ruolo, capo, scena):
    chi = request.getfixturevalue(ruolo)
    assert _crea(chi, scena["reparto"], timezone.localdate()).status_code == 403
    bozza = _crea(capo, scena["reparto"], timezone.localdate()).json()
    url = f"/api/v1/bozze-squadriglie/{bozza['id']}"
    assert _client(chi).get(url).status_code == 404
    assert _json(chi, "post", f"{url}/applica").status_code == 403
    assert _json(chi, "delete", url).status_code == 403


def test_scartare(capo, scena):
    bozza = _crea(capo, scena["reparto"], timezone.localdate()).json()
    assert _json(capo, "delete", f"/api/v1/bozze-squadriglie/{bozza['id']}").status_code == 204
    assert not BozzaSquadriglie.objects.exists()


def test_uno_spostamento_vero_dopo_la_bozza_e_segnalato(capo, scena):
    # Reported, never blocking: applying it, the draft wins.
    bozza = _crea(capo, scena["reparto"], timezone.localdate()).json()
    url = f"/api/v1/bozze-squadriglie/{bozza['id']}"
    cloe = scena["p"]["cloe"]
    membro = AppartenenzaSquadriglia.objects.attive().get(persona=cloe)
    _json(capo, "post", f"/api/v1/membri-squadriglia/{membro.pk}/termina")
    _json(
        capo,
        "post",
        f"/api/v1/squadriglie/{scena['sq']['Volpi'].pk}/membri",
        {"persona_id": cloe.pk},
    )
    differenze = _client(capo).get(url).json()["differenze"]
    assert any(
        "Cloe" in d and "da Sq. Gazze a Sq. Volpi" in d and "andrà in Sq. Gazze" in d
        for d in differenze
    ), differenze
    assert _json(capo, "post", f"{url}/applica").status_code == 200
    assert AppartenenzaSquadriglia.objects.attive().get(persona=cloe).squadriglia.nome == "Gazze"


# --- The PDF and who goes to R/S (DEC-411) ------------------------------------------------


def test_passa_in_rs_solo_senza_squadriglia(capo, scena):
    bozza = _crea(capo, scena["reparto"], timezone.localdate()).json()
    url = f"/api/v1/bozze-squadriglie/{bozza['id']}"
    anna = scena["p"]["anna"]
    rs = f"{url}/membri/{anna.pk}/rs"
    assert _json(capo, "put", rs, {"passa": True}).status_code == 400  # still in a patrol
    _json(capo, "put", f"{url}/membri/{anna.pk}", {"squadriglia_id": None})
    letta = _json(capo, "put", rs, {"passa": True}).json()
    [senza] = [p for p in letta["senza_squadriglia"] if p["id"] == anna.pk]
    assert senza["passa_in_rs"] is True
    # Back into a patrol: no more.
    volpi = _posto(letta, "Volpi")["id"]
    letta = _json(capo, "put", f"{url}/membri/{anna.pk}", {"squadriglia_id": volpi}).json()
    _json(capo, "put", f"{url}/membri/{anna.pk}", {"squadriglia_id": None})
    letta = _client(capo).get(url).json()
    assert [p["passa_in_rs"] for p in letta["senza_squadriglia"] if p["id"] == anna.pk] == [False]


def test_il_pdf_della_bozza(capo, scena):
    from apps.organizzazione import riorganizzazione

    bozza = _crea(capo, scena["reparto"], timezone.localdate()).json()
    url = f"/api/v1/bozze-squadriglie/{bozza['id']}/bozza.pdf"
    risposta = _client(capo).get(url)
    assert risposta.status_code == 200
    assert risposta["Content-Type"] == "application/pdf"
    assert risposta.content.startswith(b"%PDF")
    assert risposta["Cache-Control"] == "no-store"
    # The link on the unit page.
    dettaglio = _client(capo).get(f"/api/v1/unita/{scena['reparto'].pk}").json()
    assert dettaglio["bozza_squadriglie_pdf"] == bozza["id"]
    # Applied: no more.
    _json(capo, "post", f"/api/v1/bozze-squadriglie/{bozza['id']}/applica")
    assert _client(capo).get(url).status_code == 404
    assert riorganizzazione  # the module builds it without the network


def test_il_pdf_lo_scarica_la_coca(capo, capogruppo, scena):
    from tests.conftest import crea_capo

    altro = crea_capo("Carlo", "Altro", "altro@example.invalid")  # in no staff
    bozza = _crea(capo, scena["reparto"], timezone.localdate()).json()
    url = f"/api/v1/bozze-squadriglie/{bozza['id']}/bozza.pdf"
    for chi in (altro, capogruppo):
        assert _client(chi).get(url).status_code == 200


@pytest.mark.parametrize("ruolo", ["csq", "ragazza", "genitore", "estraneo"])
def test_il_pdf_non_per_gli_altri(request, ruolo, capo, scena):
    bozza = _crea(capo, scena["reparto"], timezone.localdate()).json()
    anna = scena["p"]["anna"]
    url = f"/api/v1/bozze-squadriglie/{bozza['id']}"
    # Even a future CSQ who reads the draft.
    _json(
        capo,
        "put",
        f"{url}/squadriglie/{_posto(bozza, 'Civette')['id']}/guide",
        {"capo_id": anna.pk},
    )
    _json(
        capo,
        "put",
        url,
        {"data_inizio": bozza["data_inizio"], "visibile_ai_capi_squadriglia": True},
    )
    for chi in (request.getfixturevalue(ruolo), anna):
        assert _client(chi).get(f"{url}/bozza.pdf").status_code == 404


def test_il_pdf_non_per_il_capo_in_attesa(capo, scena):
    from tests.conftest import crea_capo

    nuovo = crea_capo("Nino", "Nuovo", "nuovo@example.invalid")
    nuovo.codice_socio = "9000000001"  # provisional
    nuovo.save()
    bozza = _crea(capo, scena["reparto"], timezone.localdate()).json()
    url = f"/api/v1/bozze-squadriglie/{bozza['id']}/bozza.pdf"
    assert _client(nuovo).get(url).status_code == 404
    nuovo.abilitato_come_censito_il = timezone.now()  # let in by a capogruppo (DEC-400)
    nuovo.save()
    assert _client(nuovo).get(url).status_code == 200
