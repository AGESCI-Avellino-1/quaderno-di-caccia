"""The capo's project (DEC-335)."""

import pytest
from auditlog.models import LogEntry
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

from apps.diritti import servizi as diritti
from apps.fascicolo import trasferimento
from apps.fascicolo.models import ProgettoCapo
from apps.impersonazione.middleware import bloccata
from tests.conftest import crea_capo

pytestmark = pytest.mark.django_db


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


def _url(persona) -> str:
    return f"/api/v1/persone/{persona.pk}/progetto-capo"


def _pdf(contenuto=b"%PDF-1.4 x", nome="progetto.pdf"):
    return SimpleUploadedFile(nome, contenuto, content_type="application/pdf")


def _scrivi(chi, persona, **corpo):
    return _client(chi).post(_url(persona), corpo)


def test_lo_scrive_solo_il_capo(capo, capogruppo, csq, genitore, estraneo):
    for chi in (capogruppo, csq, genitore, estraneo):
        assert _scrivi(chi, capo, testo="<p>x</p>").status_code in (403, 404)
    assert _scrivi(capo, capo, testo="<p>Il mio progetto</p>").status_code == 201
    assert _client(capogruppo).get(_url(capo)).json()["puo_modificare"] is False
    assert _client(capo).get(_url(capo)).json()["puo_modificare"] is True


def test_lo_legge_la_coca_e_nessun_altro(capo, capogruppo, csq, ragazza, genitore, estraneo):
    _scrivi(capo, capo, testo="<p>Il mio progetto</p>")
    versione = ProgettoCapo.objects.get()
    altro = crea_capo("Sara", "Altra", "altra-p@example.invalid")
    for chi in (capogruppo, altro):
        assert _client(chi).get(_url(capo)).status_code == 200
        risposta = _client(chi).get(f"/api/v1/progetti-capo/{versione.pk}/testo")
        assert "Il mio progetto" in risposta.json()["testo"]
    for chi in (csq, ragazza, genitore, estraneo):
        assert _client(chi).get(_url(capo)).status_code == 404
        assert _client(chi).get(f"/api/v1/progetti-capo/{versione.pk}/testo").status_code == 404
        assert _client(chi).get(f"/api/v1/progetti-capo/{versione.pk}/file").status_code == 404


def test_chi_non_e_capo_non_ha_progetto(ragazza):
    assert _scrivi(ragazza, ragazza, testo="<p>x</p>").status_code == 404


def test_testo_o_pdf(capo):
    assert _scrivi(capo, capo).status_code == 400
    assert _scrivi(capo, capo, testo="<p>x</p>", file=_pdf()).status_code == 400
    assert _scrivi(capo, capo, file=_pdf(b"MZ finto")).status_code == 400
    assert _scrivi(capo, capo, file=_pdf(b"PK\x03\x04", "a.docx")).status_code == 400
    assert _scrivi(capo, capo, file=_pdf()).status_code == 201


def test_versioni_ultima_in_vigore(capo, capogruppo):
    _scrivi(capo, capo, testo="<p>Prima</p>")
    risposta = _scrivi(capo, capo, file=_pdf())
    versioni = risposta.json()["versioni"]
    assert [v["in_vigore"] for v in versioni] == [True, False]
    assert versioni[0]["nome_file"] == "progetto.pdf" and versioni[1]["ha_testo"] is True
    # Who is not the capo cannot remove it.
    pk = versioni[0]["id"]
    assert _client(capogruppo).delete(f"/api/v1/progetti-capo/{pk}").status_code == 403
    dopo = _client(capo).delete(f"/api/v1/progetti-capo/{pk}").json()["versioni"]
    assert len(dopo) == 1 and dopo[0]["in_vigore"] is True


def test_pdf_caricato_e_pdf_dal_testo(capo):
    _scrivi(capo, capo, file=_pdf(b"%PDF caricato"))
    caricato = ProgettoCapo.objects.get()
    risposta = _client(capo).get(f"/api/v1/progetti-capo/{caricato.pk}/file")
    assert b"".join(risposta.streaming_content) == b"%PDF caricato"
    assert "progetto.pdf" in risposta["Content-Disposition"]
    _scrivi(capo, capo, testo="<p>Testo</p>")
    testo = ProgettoCapo.objects.first()
    risposta = _client(capo).get(f"/api/v1/progetti-capo/{testo.pk}/file")
    assert risposta.status_code == 200 and risposta.content.startswith(b"%PDF")


def test_pdf_dal_testo_senza_carta_intestata(capo, gruppo, monkeypatch):
    from apps.fascicolo import progetto

    usata = []
    monkeypatch.setattr("apps.core.stampa.intestazione", lambda *a: usata.append(a))
    _scrivi(capo, capo, testo="<p>Testo</p>")
    assert progetto.pdf_del_testo(ProgettoCapo.objects.get()).startswith(b"%PDF")
    assert usata == []


def test_html_ripulito_e_fuori_dal_registro(capo):
    _scrivi(capo, capo, testo="<p>x</p><script>y</script>")
    versione = ProgettoCapo.objects.get()
    assert "<script>" not in versione.testo
    voci = {k for e in LogEntry.objects.get_for_object(versione) for k in (e.changes or {})}
    assert "testo" not in voci


def test_bloccato_impersonando():
    assert bloccata("POST", "/api/v1/persone/3/progetto-capo")
    assert bloccata("DELETE", "/api/v1/progetti-capo/3")
    assert not bloccata("GET", "/api/v1/persone/3/progetto-capo")


def test_diritti_export_e_cancellazione(capo, capogruppo, coca):
    _scrivi(capo, capo, testo="<p>Il mio progetto</p>")
    assert "Il mio progetto" in diritti.fascicolo(capo)["progetto_del_capo"][0]["Testo"]
    assert any("Progetto del capo" in v for v in diritti.anteprima_cancellazione(capo)["voci"])


def test_il_trasferimento_porta_i_testi(capo):
    _scrivi(capo, capo, testo="<p>Il mio progetto</p>")
    _scrivi(capo, capo, file=_pdf())
    capo_dati = trasferimento.esporta(capo)["capo"]
    assert [p["testo"] for p in capo_dati["progetti"]] == ["<p>Il mio progetto</p>"]
