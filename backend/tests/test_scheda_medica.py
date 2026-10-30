"""The full medical form (DEC-48…DEC-54, DEC-192…DEC-195): the rest of the AGESCI form,
the paper signature and prescription, the contact for one event, the print, the
group's letterhead."""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest
from django.test import Client

from apps.anagrafica.models import RelazioneTutela
from apps.eventi import servizi as eventi
from apps.eventi.models import Evento, Livello, TipoEvento
from apps.organizzazione.models import Gruppo
from apps.permessi.models import AccessoDatoSensibile, Azione
from apps.sanitaria.models import InformazioniSanitarie
from tests.conftest import crea_capo, crea_persona

pytestmark = pytest.mark.django_db

OGGI = date.today()
ROMA = ZoneInfo("Europe/Rome")


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


def _put(chi, url, dati):
    return _client(chi).put(url, dati, content_type="application/json")


def _compila(genitore, ragazza, **altro):
    return _put(
        genitore,
        f"/api/v1/persone/{ragazza.pk}/sanitarie",
        {
            "nessuna_allergia": True,
            "nessun_farmaco": True,
            "tessera_sanitaria": "80380000000000000001",
            "reperibilita_nome": "Mario Genitore",
            "reperibilita_telefono": "3331112222",
            "antitetanica": True,
            "note_sanitarie": "Porta gli occhiali",
            "gruppo_sanguigno": "0+",
            **altro,
        },
    )


def test_il_resto_del_modulo(genitore, ragazza, capo):
    dati = _compila(genitore, ragazza).json()
    assert dati["tessera_sanitaria"] == "80380000000000000001"
    assert dati["antitetanica"] is True and dati["gruppo_sanguigno"] == "0+"
    # An older request (from the offline queue) without the new fields keeps them.
    _put(
        genitore,
        f"/api/v1/persone/{ragazza.pk}/sanitarie",
        {"nessuna_allergia": True, "nessun_farmaco": True},
    )
    info = InformazioniSanitarie.objects.get()
    assert info.tessera_sanitaria and info.antitetanica is True and info.note_sanitarie
    letto = _client(capo).get(f"/api/v1/persone/{ragazza.pk}/sanitarie").json()
    assert letto["reperibilita_telefono"] == "3331112222"
    assert letto["puo_registrare_firma"] is True


def test_firma_su_carta_e_modifiche_dopo(genitore, ragazza, capo, capogruppo, csq):
    from django.utils import timezone

    _compila(genitore, ragazza)
    # Filled in a few days ago, signed on paper yesterday.
    InformazioniSanitarie.objects.update(dati_modificati_il=timezone.now() - timedelta(days=3))
    url = f"/api/v1/persone/{ragazza.pk}/sanitarie/carta"
    ieri = OGGI - timedelta(days=1)
    dati = {"firmata_il": ieri.isoformat(), "prescrizione_consegnata_il": ieri.isoformat()}
    assert _put(genitore, url, dati).status_code == 403
    assert _put(csq, url, dati).status_code in (403, 404)
    altro = crea_capo("Carlo", "Altro", "altro@example.invalid")
    assert _put(altro, url, dati).status_code == 403
    assert _put(capogruppo, url, dati).status_code == 200
    risposta = _put(capo, url, {**dati, "firmata_il": (OGGI + timedelta(days=1)).isoformat()})
    assert risposta.status_code == 400
    assert (
        _client(capo).get(f"/api/v1/persone/{ragazza.pk}/sanitarie").json()["da_rifirmare"] is False
    )
    # Changed after the signature: to be signed again (DEC-52).
    letto = _compila(genitore, ragazza, note_sanitarie="Ora anche le lenti").json()
    assert letto["da_rifirmare"] is True and letto["firmata_il"] == ieri.isoformat()


def test_stampa_del_modulo(genitore, ragazza, capo, estraneo):
    RelazioneTutela.objects.create(
        tutore=crea_persona("Lucia", "Genitore", email="lucia@example.invalid"),
        minore=ragazza,
        tipo="GENITORE",
    )
    _compila(genitore, ragazza)
    url = f"/api/v1/persone/{ragazza.pk}/sanitarie/modulo.pdf"
    assert _client(estraneo).get(url).status_code == 404
    for chi in (genitore, capo):
        risposta = _client(chi).get(url)
        assert risposta.status_code == 200
        assert risposta["Content-Type"] == "application/pdf"
        assert risposta.content.startswith(b"%PDF")
        assert ragazza.cognome.encode() not in risposta["Content-Disposition"].encode()
    assert AccessoDatoSensibile.objects.filter(persona=ragazza, azione=Azione.STAMPA).count() == 2


def test_stampa_di_un_maggiorenne(rover_adulto):
    risposta = _client(rover_adulto).get(f"/api/v1/persone/{rover_adulto.pk}/sanitarie/modulo.pdf")
    assert risposta.status_code == 200 and risposta.content.startswith(b"%PDF")


@pytest.fixture
def rover_adulto(gruppo):
    from tests.conftest import nato_anni_fa

    return crea_persona("Paolo", "Adulto", "paolo@example.invalid", data_nascita=nato_anni_fa(19))


@pytest.fixture
def uscita(reparto, ragazza, csq, capo):
    evento = Evento(
        titolo="Uscita al lago",
        tipo=TipoEvento.USCITA,
        livello=Livello.UNITA,
        inizio=datetime.combine(OGGI + timedelta(days=10), time(9), ROMA),
        fine=datetime.combine(OGGI + timedelta(days=11), time(17), ROMA),
    )
    return eventi.crea(evento, [reparto], capo.utente)


def test_reperibilita_per_un_evento_e_stampa(uscita, genitore, ragazza, capo, csq, estraneo):
    _compila(genitore, ragazza)
    url = f"/api/v1/eventi/{uscita.pk}/reperibilita/{ragazza.pk}"
    assert _put(capo, url, {"nome": "Nonna Rosa", "telefono": "3330000000"}).status_code == 200
    assert _put(estraneo, url, {"nome": "x", "telefono": "1"}).status_code == 403
    assert _put(genitore, url, {"nome": "Nonna Rosa", "telefono": ""}).status_code == 400
    assert _put(genitore, url, {"nome": "Nonna Rosa", "telefono": "3330000000"}).json() == {
        "nome": "Nonna Rosa",
        "telefono": "3330000000",
    }
    stampa = f"/api/v1/eventi/{uscita.pk}/schede-sanitarie.pdf"
    assert _client(csq).get(stampa).status_code == 403
    assert _client(genitore).get(stampa).status_code == 403
    risposta = _client(capo).get(stampa)
    assert risposta.status_code == 200 and risposta.content.startswith(b"%PDF")
    assert AccessoDatoSensibile.objects.filter(persona=csq, azione=Azione.STAMPA).exists()
    # Empty: back to the yearly contact.
    assert _put(genitore, url, {"nome": "", "telefono": ""}).json() is None


def test_intestazione_del_gruppo(capogruppo, capo, gruppo):
    url = "/api/v1/gruppo/intestazione"
    dati = {
        "denominazione_sociale": "AGESCI Gruppo Prova 1",
        "codice_fiscale": "00000000000",
        "sede_indirizzo": "Via Roma 1",
        "sede_cap": "83100",
        "sede_comune": "Avellino",
        "sede_provincia": "av",
        "email": "prova@example.invalid",
        "runts_repertorio": "12345",
        "runts_data": "2023-05-02",
    }
    assert _put(capo, url, dati).status_code == 403
    risposta = _put(capogruppo, url, dati)
    assert risposta.status_code == 200 and risposta.json()["sede_provincia"] == "AV"
    assert _put(capogruppo, url, {**dati, "email": "non-una-email"}).status_code == 400
    assert _client(capo).get(url).json()["puo_modificare"] is False
    # Logo: re-encoded, not anything that claims to be an image.
    from io import BytesIO

    from django.core.files.uploadedfile import SimpleUploadedFile
    from PIL import Image

    buffer = BytesIO()
    Image.new("RGB", (900, 300), "purple").save(buffer, "JPEG")
    client = _client(capogruppo)
    falso = SimpleUploadedFile("logo.png", b"not an image", content_type="image/png")
    assert client.post("/api/v1/gruppo/logo", {"file": falso}).status_code == 400
    vero = SimpleUploadedFile("logo.jpg", buffer.getvalue(), content_type="image/jpeg")
    assert client.post("/api/v1/gruppo/logo", {"file": vero}).json()["logo"] is True
    gruppo = Gruppo.objects.get()
    assert gruppo.logo.name.endswith(".png") and "logo" not in gruppo.logo.name
    gruppo.logo.delete(save=True)


def test_fascicolo_e_cancellazione(uscita, genitore, ragazza, capogruppo):
    from apps.sanitaria.models import ReperibilitaEvento

    _compila(genitore, ragazza)
    _put(
        genitore,
        f"/api/v1/eventi/{uscita.pk}/reperibilita/{ragazza.pk}",
        {"nome": "Nonna", "telefono": "1"},
    )
    dati = _client(capogruppo).get(f"/api/v1/persone/{ragazza.pk}/fascicolo").json()
    assert dati["informazioni_sanitarie"]["Tessera sanitaria"] == "80380000000000000001"
    assert dati["reperibilita_per_evento"][0]["Chi"] == "Nonna"
    url = f"/api/v1/persone/{ragazza.pk}/cancellazione"
    assert (
        _client(capogruppo).post(url, {"cognome": "Esploratrice"}, "application/json").status_code
        == 200
    )
    assert not ReperibilitaEvento.objects.exists()


def test_il_link_di_stampa_solo_a_chi_puo(uscita, capo, csq):
    assert _client(capo).get(f"/api/v1/eventi/{uscita.pk}").json()["puo_stampare_schede"] is True
    assert _client(csq).get(f"/api/v1/eventi/{uscita.pk}").json()["puo_stampare_schede"] is False
