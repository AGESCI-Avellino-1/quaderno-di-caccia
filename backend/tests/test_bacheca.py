"""Notice board (DEC-03, DEC-218…DEC-220)."""

from datetime import date, timedelta

import pytest
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

from apps.anagrafica.models import PreferenzeEmail
from apps.bacheca.models import Avviso, Destinatari
from apps.organizzazione.models import TipoUnita, Unita

pytestmark = pytest.mark.django_db

OGGI = date.today()


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


def _pubblica(chi, **campi):
    dati = {
        "titolo": "Uscita di sabato",
        "testo": "Appuntamento alle 9 in sede.",
        "destinatari": Destinatari.FAMIGLIE,
        "scade_il": str(OGGI + timedelta(days=7)),
        **campi,
    }
    return _client(chi).post("/api/v1/avvisi", dati, content_type="application/json")


def _titoli(chi, **parametri) -> list[str]:
    risposta = _client(chi).get("/api/v1/avvisi", parametri).json()
    return [a["titolo"] for a in risposta["avvisi"]]


@pytest.fixture
def altro_reparto(gruppo) -> Unita:
    return Unita.objects.create(gruppo=gruppo, tipo=TipoUnita.REPARTO, nome="Altro")


def test_chi_pubblica(capo, capogruppo, csq, ragazza, genitore, estraneo, reparto, altro_reparto):
    # The staff for their unit only; the capigruppo for the group and every unit.
    assert _pubblica(capo, unita_id=reparto.pk).status_code == 201
    assert _pubblica(capo, unita_id=altro_reparto.pk).status_code == 403
    assert _pubblica(capo).status_code == 403  # families of the whole group
    assert _pubblica(capogruppo).status_code == 201
    assert _pubblica(capogruppo, unita_id=altro_reparto.pk).status_code == 201
    for chi in (csq, ragazza, genitore, estraneo):
        assert _pubblica(chi, unita_id=reparto.pk).status_code == 403
    pubblica_in = _client(capo).get("/api/v1/avvisi").json()["pubblica_in"]
    assert [d["unita_id"] for d in pubblica_in] == [None, reparto.pk]


def test_chi_legge(capo, capogruppo, csq, ragazza, genitore, estraneo, reparto, altro_reparto):
    _pubblica(capo, unita_id=reparto.pk, titolo="Reparto, famiglie")
    _pubblica(capo, unita_id=reparto.pk, titolo="Reparto, genitori", destinatari="GENITORI")
    _pubblica(capo, unita_id=reparto.pk, titolo="Reparto, ragazzi", destinatari="RAGAZZI")
    _pubblica(capogruppo, unita_id=altro_reparto.pk, titolo="Altro reparto")
    _pubblica(capogruppo, titolo="Gruppo")
    _pubblica(capogruppo, titolo="Co.Ca.", destinatari="CAPI")
    assert set(_titoli(ragazza)) == {"Reparto, famiglie", "Reparto, ragazzi", "Gruppo"}
    assert set(_titoli(csq)) == {"Reparto, famiglie", "Reparto, ragazzi", "Gruppo"}
    assert set(_titoli(genitore)) == {"Reparto, famiglie", "Reparto, genitori", "Gruppo"}
    assert _titoli(estraneo) == []
    assert len(_titoli(capo)) == 6
    # A notice the reader may not see is not found.
    coca = Avviso.objects.get(titolo="Co.Ca.")
    assert (
        _client(ragazza)
        .put(
            f"/api/v1/avvisi/{coca.pk}",
            {"titolo": "x", "testo": "x", "destinatari": "CAPI", "scade_il": str(OGGI)},
            content_type="application/json",
        )
        .status_code
        == 404
    )


def test_scaduti_solo_ai_capi(capo, ragazza, reparto):
    _pubblica(capo, unita_id=reparto.pk, titolo="Vecchio")
    Avviso.objects.update(scade_il=OGGI - timedelta(days=1))
    assert _titoli(ragazza) == []
    assert _titoli(capo) == []
    assert _titoli(capo, scaduti=True) == ["Vecchio"]
    assert _titoli(ragazza, scaduti=True) == []


def test_capi_solo_per_tutto_il_gruppo(capogruppo, reparto):
    assert _pubblica(capogruppo, unita_id=reparto.pk, destinatari="CAPI").status_code == 403
    assert _pubblica(capogruppo, scade_il=str(OGGI - timedelta(days=1))).status_code == 400


def test_modifica_autore_e_capogruppo(capo, capogruppo, reparto, coca):
    from apps.anagrafica.models import Appartenenza, RuoloAppartenenza
    from apps.organizzazione.models import Incarico, RuoloIncarico
    from tests.conftest import INIZIO_ANNO, crea_persona

    altro = crea_persona("Carla", "Staff", "staff2@example.invalid")
    Appartenenza.objects.create(
        persona=altro, unita=coca, ruolo=RuoloAppartenenza.CAPO, data_inizio=INIZIO_ANNO
    )
    Incarico.objects.create(
        persona=altro, ruolo=RuoloIncarico.STAFF, unita=reparto, data_inizio=INIZIO_ANNO
    )
    avviso = _pubblica(capo, unita_id=reparto.pk).json()
    url = f"/api/v1/avvisi/{avviso['id']}"
    nuovo = {**avviso, "titolo": "Cambiato", "scade_il": avviso["scade_il"]}
    assert _client(altro).put(url, nuovo, content_type="application/json").status_code == 403
    assert _client(capogruppo).put(url, nuovo, content_type="application/json").status_code == 200
    assert _client(capo).delete(url).status_code == 204


def test_email_facoltativa(capo, ragazza, genitore, genitrice_senza_account, reparto):
    _pubblica(capo, unita_id=reparto.pk)
    assert mail.outbox == []
    PreferenzeEmail.objects.create(persona=genitrice_senza_account, avvisi=False)
    _pubblica(capo, unita_id=reparto.pk, invia_email=True, destinatari="GENITORI")
    destinatari = {m.to[0] for m in mail.outbox}
    assert destinatari == {"genitore@example.invalid"}
    assert "Appuntamento alle 9" in mail.outbox[0].body


def test_allegati(capo, ragazza, estraneo, reparto, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    avviso = _pubblica(capo, unita_id=reparto.pk).json()
    pdf = SimpleUploadedFile("programma Giulia.pdf", b"%PDF-1.4 prova")
    risposta = _client(capo).post(
        f"/api/v1/avvisi/{avviso['id']}/allegati", {"titolo": "Programma", "file": pdf}
    )
    assert risposta.status_code == 201
    allegato = risposta.json()["allegati"][0]
    assert allegato["titolo"] == "Programma"
    url = f"/api/v1/allegati-avviso/{allegato['id']}"
    letto = _client(ragazza).get(url)
    assert letto.status_code == 200 and letto.content.startswith(b"%PDF")
    assert "Giulia" not in letto["Content-Disposition"]
    assert _client(estraneo).get(url).status_code == 404
    finto = SimpleUploadedFile("x.pdf", b"MZ non un pdf")
    assert (
        _client(capo)
        .post(f"/api/v1/avvisi/{avviso['id']}/allegati", {"titolo": "x", "file": finto})
        .status_code
        == 400
    )
    assert _client(ragazza).delete(url).status_code == 403
    assert _client(capo).delete(url).status_code == 200


def test_avvisi_per_i_capi_da_ogni_capo(capo, csq, genitore, reparto):
    """Any capo publishes for the Co.Ca.; not for families outside their unit (DEC-218)."""
    assert _pubblica(capo, destinatari="CAPI").status_code == 201
    assert _pubblica(capo, destinatari="FAMIGLIE").status_code == 403
    for chi in (csq, genitore):
        assert _pubblica(chi, destinatari="CAPI").status_code == 403
    pubblica_in = _client(capo).get("/api/v1/avvisi").json()["pubblica_in"]
    assert pubblica_in[0] == {"unita_id": None, "nome": "Tutto il gruppo", "destinatari": ["CAPI"]}
    assert "CAPI" not in pubblica_in[1]["destinatari"]
