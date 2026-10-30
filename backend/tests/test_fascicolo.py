"""The ragazzo's file (DEC-38, DEC-41, DEC-42, DEC-201…DEC-204): profile photo,
attachments to the Progressione, the file of a year, the passage report; for every
role."""

from datetime import date, timedelta
from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from PIL import Image

from apps.anagrafica.models import FotoProfilo
from apps.permessi.models import AccessoDatoSensibile, Categoria
from apps.progressione.models import AllegatoPP

pytestmark = pytest.mark.django_db

OGGI = date.today()
PDF = b"%PDF-1.4\n% prova\n"


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


def _jpeg(lato=800) -> SimpleUploadedFile:
    buffer = BytesIO()
    Image.new("RGB", (lato, lato), "green").save(buffer, "JPEG")
    return SimpleUploadedFile("Giulia al mare.jpg", buffer.getvalue(), content_type="image/jpeg")


@pytest.fixture(autouse=True)
def _media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def test_foto_profilo(capo, capogruppo, csq, ragazza, genitore, estraneo):
    url = f"/api/v1/persone/{ragazza.pk}/foto"
    for chi in (csq, estraneo):
        assert _client(chi).post(url, {"file": _jpeg()}).status_code in (403, 404)
    falso = SimpleUploadedFile("x.jpg", b"non una foto")
    assert _client(genitore).post(url, {"file": falso}).status_code == 400
    assert _client(genitore).post(url, {"file": _jpeg()}).status_code == 201
    assert _client(capo).post(url, {"file": _jpeg(400)}).status_code == 201
    for chi in (capo, capogruppo, ragazza, genitore):
        risposta = _client(chi).get(url)
        assert risposta.status_code == 200 and risposta["Content-Type"] == "image/jpeg"
    for chi in (csq, estraneo):
        assert _client(chi).get(url).status_code == 404
    # The earlier one stays, for the capi.
    storico = _client(capo).get(f"{url}/storico").json()
    assert len(storico) == 2
    assert _client(genitore).get(f"{url}/storico").status_code == 403
    assert _client(genitore).get(url, {"foto_id": storico[1]["id"]}).status_code == 404
    assert _client(capo).get(url, {"foto_id": storico[1]["id"]}).status_code == 200
    assert "Giulia" not in FotoProfilo.objects.first().file.name
    assert _client(capo).get(f"/api/v1/persone/{ragazza.pk}").json()["foto"] is True
    assert _client(csq).get(f"/api/v1/persone/{ragazza.pk}").json()["foto"] is False


@pytest.fixture
def impegno(capo, ragazza):
    _client(capo).post(
        f"/api/v1/persone/{ragazza.pk}/progressione/sentiero",
        {"data": (OGGI - timedelta(days=100)).isoformat(), "precisione": "GIORNO"},
        content_type="application/json",
    )
    dati = (
        _client(capo)
        .post(
            f"/api/v1/persone/{ragazza.pk}/progressione/impegni",
            {"testo": "Costruire un forno"},
            content_type="application/json",
        )
        .json()
    )
    return dati["impegni"][0]["id"]


def test_allegati_alla_progressione(capo, csq, ragazza, genitore, estraneo, impegno):
    url = f"/api/v1/allegati-pp/impegni/{impegno}"
    allegato = SimpleUploadedFile("Rossi.pdf", PDF)
    assert _client(genitore).post(url, {"titolo": "x", "file": allegato}).status_code == 403
    exe = SimpleUploadedFile("x.pdf", b"MZ\x90\x00")
    assert _client(ragazza).post(url, {"titolo": "Foto", "file": exe}).status_code == 400
    dati = (
        _client(ragazza)
        .post(url, {"titolo": "Progetto del forno", "file": SimpleUploadedFile("Rossi.pdf", PDF)})
        .json()
    )
    voce = dati["impegni"][0]["allegati"][0]
    assert voce["titolo"] == "Progetto del forno"
    assert "Rossi" not in AllegatoPP.objects.get().file.name
    scarica = f"/api/v1/allegati-pp/{voce['id']}"
    for chi in (capo, ragazza, genitore, csq):
        assert _client(chi).get(scarica).status_code == 200
    assert _client(estraneo).get(scarica).status_code == 404
    assert _client(genitore).delete(scarica).status_code in (403, 404)
    assert _client(capo).delete(scarica).status_code == 200
    assert not AllegatoPP.objects.exists()


def test_allegato_di_una_meta_riservata(capo, csq, ragazza):
    _client(capo).post(
        f"/api/v1/persone/{ragazza.pk}/progressione/sentiero",
        {"data": OGGI.isoformat(), "precisione": "GIORNO"},
        content_type="application/json",
    )
    meta = (
        _client(capo)
        .post(
            f"/api/v1/persone/{ragazza.pk}/progressione/mete",
            {"testo": "Delicata", "riservata": True},
            content_type="application/json",
        )
        .json()["mete"][0]
    )
    dati = (
        _client(capo)
        .post(
            f"/api/v1/allegati-pp/mete/{meta['id']}",
            {"titolo": "Nota", "file": SimpleUploadedFile("a.pdf", PDF)},
        )
        .json()
    )
    allegato = dati["mete"][0]["allegati"][0]["id"]
    assert _client(csq).get(f"/api/v1/allegati-pp/{allegato}").status_code == 404


def test_fascicolo_dell_anno(capo, csq, ragazza, genitore, estraneo):
    _client(capo).put(
        f"/api/v1/persone/{ragazza.pk}/regole-rapporto",
        {"testo": "Regola riservata"},
        content_type="application/json",
    )
    _client(capo).post(
        f"/api/v1/persone/{ragazza.pk}/note",
        {"testo": "Per i genitori", "visibile_genitori": True},
        content_type="application/json",
    )
    url = f"/api/v1/persone/{ragazza.pk}/fascicolo-anno"
    dati = _client(capo).get(url).json()
    titoli = [s["titolo"] for s in dati["sezioni"]]
    assert {
        "Anagrafica e famiglia",
        "Regole sul rapporto con il minore",
        "Scheda sanitaria",
    } <= set(titoli)
    assert "Documenti" in titoli and dati["anni"]
    assert AccessoDatoSensibile.objects.filter(
        persona=ragazza, categoria=Categoria.SANITARIE
    ).exists()
    del_genitore = _client(genitore).get(url).json()
    titoli = [s["titolo"] for s in del_genitore["sezioni"]]
    assert "Regole sul rapporto con il minore" not in titoli and "Documenti" not in titoli
    note = next(s for s in del_genitore["sezioni"] if s["titolo"] == "Note")
    assert [v["valore"] for v in note["voci"]] == ["Per i genitori"]
    for chi in (csq, estraneo):
        assert _client(chi).get(url).status_code == 404
    pdf = _client(genitore).get(f"/api/v1/persone/{ragazza.pk}/fascicolo-anno.pdf")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    assert ragazza.cognome not in pdf["Content-Disposition"]


def test_report_del_passaggio(capo, ragazza, genitore, gruppo, reparto):
    from apps.organizzazione.models import Composizione, TipoUnita, Unita

    clan = Unita.objects.create(
        gruppo=gruppo, nome="Clan", tipo=TipoUnita.CLAN_FUOCO, composizione=Composizione.MISTA
    )
    _client(capo).post(
        f"/api/v1/persone/{ragazza.pk}/progressione/sentiero",
        {"data": (OGGI - timedelta(days=300)).isoformat(), "precisione": "GIORNO"},
        content_type="application/json",
    )
    dati = (
        _client(capo)
        .post(
            f"/api/v1/unita/{reparto.pk}/passaggi",
            {
                "unita_destinazione_id": clan.pk,
                "data": OGGI.isoformat(),
                "persone": [{"persona_id": ragazza.pk, "sintesi": "Brava"}],
            },
            content_type="application/json",
        )
        .json()
    )
    passaggio = dati["in_uscita"][0]["id"]
    url = f"/api/v1/passaggi/{passaggio}/report/{ragazza.pk}.pdf"
    assert _client(genitore).get(url).status_code == 403
    risposta = _client(capo).get(url)
    assert risposta.status_code == 200 and risposta.content.startswith(b"%PDF")


def test_foto_al_campo_e_cancellazione(capo, capogruppo, ragazza, genitore, reparto):
    _client(genitore).post(f"/api/v1/persone/{ragazza.pk}/foto", {"file": _jpeg()})
    client = _client(capo)
    client.post("/api/v1/dispositivi", {"nome": "Telefono"}, content_type="application/json")
    scheda = next(
        p
        for p in client.get(f"/api/v1/campo/{reparto.pk}").json()["persone"]
        if p["id"] == ragazza.pk
    )
    assert scheda["foto"].startswith("data:image/jpeg;base64,")
    _client(capogruppo).post(
        f"/api/v1/persone/{ragazza.pk}/cancellazione",
        {"cognome": "Esploratrice"},
        content_type="application/json",
    )
    assert not FotoProfilo.objects.exists()
