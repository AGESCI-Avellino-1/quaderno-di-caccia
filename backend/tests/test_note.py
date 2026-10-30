"""Notes and rules on the relationship with the minor (DEC-39, DEC-40, DEC-43,
DEC-197…DEC-199), for every role: capo, capogruppo, CSQ, ragazzo, genitore, estraneo."""

import pytest
from django.test import Client

from apps.note.models import Nota, RegoleRapporto
from apps.permessi.models import AccessoDatoSensibile, Azione, Categoria
from tests.conftest import crea_capo

pytestmark = pytest.mark.django_db


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


def _post(chi, url, dati):
    return _client(chi).post(url, dati, content_type="application/json")


def _put(chi, url, dati):
    return _client(chi).put(url, dati, content_type="application/json")


def _leggi(chi, persona):
    return _client(chi).get(f"/api/v1/persone/{persona.pk}/note")


def test_nota_di_staff_e_chi_la_legge(capo, capogruppo, csq, ragazza, genitore, estraneo):
    url = f"/api/v1/persone/{ragazza.pk}/note"
    assert _post(csq, url, {"testo": "x"}).status_code == 201  # a CSQ note, see below
    Nota.objects.all().delete()
    for chi in (genitore, ragazza, estraneo):
        assert _post(chi, url, {"testo": "x"}).status_code in (403, 404)
    dati = _post(capo, url, {"testo": "Riservata alla Co.Ca."}).json()
    assert dati["note"][0]["tipo"] == "STAFF" and not dati["note"][0]["condivisa_fuori_coca"]
    _post(
        capogruppo,
        url,
        {
            "testo": "Per tutti",
            "visibile_ragazzo": True,
            "visibile_genitori": True,
            "visibile_csq": True,
        },
    )
    altro = crea_capo("Carlo", "Altro", "altro@example.invalid")
    assert len(_leggi(altro, ragazza).json()["note"]) == 2  # every capo reads (DEC-09)
    assert _leggi(altro, ragazza).json()["scrive"] is None
    for chi in (ragazza, genitore, csq):
        testi = [n["testo"] for n in _leggi(chi, ragazza).json()["note"]]
        assert testi == ["Per tutti"]
    assert _leggi(estraneo, ragazza).status_code == 404


def test_nota_del_csq(capo, csq, ragazza, genitore):
    url = f"/api/v1/persone/{ragazza.pk}/note"
    dati = _post(csq, url, {"testo": "Brava in cucina"}).json()
    nota = dati["note"][0]
    assert nota["tipo"] == "CSQ"
    assert _leggi(capo, ragazza).json()["note"][0]["testo"] == "Brava in cucina"
    assert _leggi(genitore, ragazza).json()["note"] == []
    # The staff changes who reads it, not the text.
    _put(capo, f"/api/v1/note/{nota['id']}", {"testo": "Cambiata", "visibile_genitori": True})
    assert Nota.objects.get().testo == "Brava in cucina"
    assert [n["testo"] for n in _leggi(genitore, ragazza).json()["note"]] == ["Brava in cucina"]
    # The CSQ does not write on the CSQ itself, nor on other patrols' members.
    assert _post(csq, f"/api/v1/persone/{csq.pk}/note", {"testo": "x"}).status_code in (403, 404)


def test_solo_l_autore_modifica_e_cancella(capo, capogruppo, ragazza):
    nota = _post(capo, f"/api/v1/persone/{ragazza.pk}/note", {"testo": "Prima"}).json()["note"][0]
    url = f"/api/v1/note/{nota['id']}"
    assert _put(capogruppo, url, {"testo": "Altro"}).status_code == 403
    assert _client(capogruppo).delete(url).status_code == 403
    assert _put(capo, url, {"testo": "Dopo"}).json()["note"][0]["testo"] == "Dopo"
    assert _client(capo).delete(url).status_code == 200
    assert not Nota.objects.exists()


def test_al_csq_solo_in_reparto(capo, rover_fixture):
    risposta = _post(
        capo,
        f"/api/v1/persone/{rover_fixture.pk}/note",
        {"testo": "x", "visibile_csq": True},
    )
    assert risposta.status_code in (400, 403)


@pytest.fixture
def rover_fixture(gruppo):
    from apps.anagrafica.models import Appartenenza, RuoloAppartenenza
    from apps.organizzazione.models import Composizione, TipoUnita, Unita
    from tests.conftest import INIZIO_ANNO, crea_persona, nato_anni_fa

    clan = Unita.objects.create(
        gruppo=gruppo, nome="Clan", tipo=TipoUnita.CLAN_FUOCO, composizione=Composizione.MISTA
    )
    persona = crea_persona("Paolo", "Rover", data_nascita=nato_anni_fa(17))
    Appartenenza.objects.create(
        persona=persona, unita=clan, ruolo=RuoloAppartenenza.RAGAZZO, data_inizio=INIZIO_ANNO
    )
    return persona


def test_regole_sul_rapporto_con_il_minore(capo, capogruppo, csq, ragazza, genitore, estraneo):
    url = f"/api/v1/persone/{ragazza.pk}/regole-rapporto"
    testo = {"testo": "Il padre non può riprenderla all'uscita"}
    for chi in (genitore, csq, ragazza, estraneo):
        assert _put(chi, url, testo).status_code in (403, 404)
    assert _put(capogruppo, url, testo).status_code == 200
    assert _leggi(capo, ragazza).json()["regole"] == testo["testo"]
    assert AccessoDatoSensibile.objects.filter(
        persona=ragazza, categoria=Categoria.REGOLE_MINORE, azione=Azione.LETTURA
    ).exists()
    for chi in (genitore, csq, ragazza):
        assert _leggi(chi, ragazza).json()["regole"] is None
    # Empty: no rules any more.
    _put(capo, url, {"testo": ""})
    assert not RegoleRapporto.objects.exists()


def test_regole_al_campo_e_niente_altro_della_scheda(capo, ragazza, genitore, reparto):
    _put(
        genitore,
        f"/api/v1/persone/{ragazza.pk}/sanitarie",
        {"tessera_sanitaria": "123", "note_sanitarie": "Riservato"},
    )
    _put(capo, f"/api/v1/persone/{ragazza.pk}/regole-rapporto", {"testo": "Regola"})
    client = _client(capo)
    client.post("/api/v1/dispositivi", {"nome": "Telefono"}, content_type="application/json")
    risposta = client.get(f"/api/v1/campo/{reparto.pk}")
    assert risposta.status_code == 200, risposta.content
    scheda = next(p for p in risposta.json()["persone"] if p["id"] == ragazza.pk)
    assert scheda["regole_rapporto"] == "Regola"
    assert not scheda["sanitarie"].get("note_sanitarie")
    assert not scheda["sanitarie"].get("tessera_sanitaria")


def test_fascicolo_e_cancellazione(capo, capogruppo, ragazza):
    _post(capo, f"/api/v1/persone/{ragazza.pk}/note", {"testo": "Nota"})
    _put(capo, f"/api/v1/persone/{ragazza.pk}/regole-rapporto", {"testo": "Regola"})
    dati = _client(capogruppo).get(f"/api/v1/persone/{ragazza.pk}/fascicolo").json()
    assert dati["note"][0]["Testo"] == "Nota"
    assert dati["regole_sul_rapporto_con_il_minore"] == "Regola"
    url = f"/api/v1/persone/{ragazza.pk}/cancellazione"
    _client(capogruppo).post(url, {"cognome": "Esploratrice"}, "application/json")
    assert not (Nota.objects.exists() or RegoleRapporto.objects.exists())
