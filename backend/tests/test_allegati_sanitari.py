"""Documents of the medical form and the signed form (DEC-290)."""

from datetime import date
from unittest import mock

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

from apps.permessi.models import AccessoDatoSensibile, Azione
from apps.sanitaria.models import AllegatoSanitario, InformazioniSanitarie

pytestmark = pytest.mark.django_db

PDF = b"%PDF-1.4 scheda firmata"


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


def _carica(chi, persona, tipo="TESSERA", contenuto=PDF):
    return _client(chi).post(
        f"/api/v1/persone/{persona.pk}/sanitarie/allegati",
        {"tipo": tipo, "file": SimpleUploadedFile("Tessera di Giulia.pdf", contenuto)},
    )


def _post(chi, url, dati=None):
    return _client(chi).post(url, dati or {}, content_type="application/json")


def test_la_famiglia_carica_e_il_capo_verifica(genitore, ragazza, capo, csq, estraneo):
    risposta = _carica(genitore, ragazza)
    assert risposta.status_code == 200, risposta.content
    dati = risposta.json()
    assert dati["puo_caricare"] and not dati["puo_verificare"]
    assert [t["valore"] for t in dati["tipi"]][-2:] == ["DOC_GENITORE", "SCHEDA"]
    allegato = AllegatoSanitario.objects.get()
    assert allegato.file.name.endswith(".pdf") and "Giulia" not in allegato.file.name
    # Not a PDF or a picture: refused.
    assert _carica(genitore, ragazza, contenuto=b"MZ...").status_code == 400
    for chi in (csq, estraneo):
        url = f"/api/v1/allegati-sanitari/{allegato.pk}/file"
        assert _client(chi).get(url).status_code in (403, 404)

    url = f"/api/v1/allegati-sanitari/{allegato.pk}/file"
    file = _client(capo).get(url)
    assert file.status_code == 200 and b"".join(file.streaming_content) == PDF
    assert AccessoDatoSensibile.objects.filter(utente=capo.utente, azione=Azione.LETTURA).exists()
    # The family cannot confirm; the capo saved it on the computer: the server forgets it.
    conferma = f"/api/v1/allegati-sanitari/{allegato.pk}/conferma"
    assert _post(genitore, conferma).status_code == 403
    dati = _post(capo, conferma).json()
    voce = dati["allegati"][0]
    assert voce["verificato_il"] and voce["salvato_su"] == "Computer del capo"
    allegato.refresh_from_db()
    assert not allegato.file
    assert _client(capo).get(url).status_code == 404
    assert _client(capo).delete(f"/api/v1/allegati-sanitari/{allegato.pk}").status_code == 400


def test_scheda_firmata_porta_la_data_della_firma(genitore, ragazza, capo):
    InformazioniSanitarie.objects.create(persona=ragazza, inserite_da="GENITORE")
    _carica(genitore, ragazza, tipo="SCHEDA")
    allegato = AllegatoSanitario.objects.get()
    conferma = f"/api/v1/allegati-sanitari/{allegato.pk}/conferma"
    assert _post(capo, conferma).status_code == 400  # which day?
    giorno = date.today().replace(day=1)
    assert _post(capo, conferma, {"firmata_il": giorno.isoformat()}).status_code == 200
    assert InformazioniSanitarie.objects.get(persona=ragazza).firmata_il == giorno


def test_sul_drive_del_gruppo(genitore, ragazza, capo):
    _carica(genitore, ragazza)
    allegato = AllegatoSanitario.objects.get()
    with mock.patch("apps.archivio.drive.carica") as carica:
        risposta = _post(capo, f"/api/v1/allegati-sanitari/{allegato.pk}/drive")
    assert risposta.status_code == 200, risposta.content
    nome, contenuto, tipo = carica.call_args.args
    assert contenuto == PDF and tipo == "application/pdf"
    assert nome.startswith("Esploratrice Giulia - Tessera sanitaria")
    assert risposta.json()["allegati"][0]["salvato_su"] == "Drive del gruppo"
    # Drive refusing: nothing deleted.
    _carica(genitore, ragazza)
    secondo = AllegatoSanitario.objects.filter(verificato_il__isnull=True).get()
    from apps.archivio.drive import ErroreDrive

    with mock.patch("apps.archivio.drive.carica", side_effect=ErroreDrive("Non riuscito.")):
        assert _post(capo, f"/api/v1/allegati-sanitari/{secondo.pk}/drive").status_code == 400
    secondo.refresh_from_db()
    assert secondo.file and secondo.verificato_il is None


def test_chi_carica_puo_togliere_prima_della_verifica(genitore, ragazza):
    _carica(genitore, ragazza)
    allegato = AllegatoSanitario.objects.get()
    assert _client(genitore).delete(f"/api/v1/allegati-sanitari/{allegato.pk}").status_code == 200
    assert not AllegatoSanitario.objects.exists()
