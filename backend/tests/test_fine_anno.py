"""Closed years, archiving to the group's shared Drive, moving a file to another group
(DEC-44…DEC-46, DEC-196, DEC-209…DEC-213)."""

import hashlib
import json
from datetime import date, timedelta
from decimal import Decimal
from unittest import mock

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

from apps.anagrafica.models import Appartenenza, Persona
from apps.archivio import drive, servizi
from apps.archivio.models import Archiviazione
from apps.cassa import servizi as cassa
from apps.cassa.catalogo import catalogo
from apps.cassa.models import Cassa, TipoCassa, TipoMovimento
from apps.core.anno import AnnoAssociativo
from apps.note.models import Nota
from apps.organizzazione.models import AnnoChiuso
from apps.progressione.models import Obiettivo, PeriodoBranca

pytestmark = pytest.mark.django_db

OGGI = date.today()
CORRENTE = AnnoAssociativo.corrente()
PASSATO = AnnoAssociativo(CORRENTE.anno_fine - 1)


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


def _post(chi, url, dati=None):
    return _client(chi).post(url, dati or {}, content_type="application/json")


# --- Closed years (DEC-45, DEC-209, DEC-210) -----------------------------------------------


@pytest.fixture
def banca(gruppo):
    return Cassa.objects.create(
        nome="Conto",
        tipo=TipoCassa.BANCA,
        saldo_iniziale=Decimal("100"),
        data_saldo_iniziale=PASSATO.inizio,
    )


def _uscita(banca, giorno):
    return cassa.registra(
        cassa=banca,
        tipo=TipoMovimento.USCITA,
        data=giorno,
        importo=Decimal("10"),
        descrizione="Cancelleria",
        voce_id=catalogo().cerca("U", "A.1").id,
        utente=None,
    )


def test_chiudere_e_riaprire_un_anno(capo, capogruppo, banca):
    url = f"/api/v1/gruppo/anni/{PASSATO.anno_fine}"
    assert _post(capo, f"{url}/chiudi").status_code == 403
    assert _post(capogruppo, f"/api/v1/gruppo/anni/{CORRENTE.anno_fine}/chiudi").status_code == 400
    dati = _post(capogruppo, f"{url}/chiudi").json()
    assert next(a for a in dati["anni"] if a["anno"] == PASSATO.anno_fine)["chiuso_il"]
    giorno = PASSATO.inizio + timedelta(days=10)
    with pytest.raises(ValidationError, match="chiuso"):
        _uscita(banca, giorno)
    _uscita(banca, OGGI)  # the current year is open
    # Reopened for a few days, with a reason; at most 30.
    troppo = {"fino_al": (OGGI + timedelta(days=31)).isoformat(), "motivo": "Correzione"}
    assert _post(capogruppo, f"{url}/riapri", troppo).status_code == 400
    assert _post(capogruppo, f"{url}/riapri", {**troppo, "motivo": ""}).status_code == 400
    dati = _post(
        capogruppo,
        f"{url}/riapri",
        {"fino_al": (OGGI + timedelta(days=3)).isoformat(), "motivo": "Ricevuta"},
    ).json()
    assert next(a for a in dati["anni"] if a["anno"] == PASSATO.anno_fine)["riaperto_fino_al"]
    _uscita(banca, giorno)
    # Closed again before the date.
    _post(capogruppo, f"{url}/chiudi")
    with pytest.raises(ValidationError):
        _uscita(banca, giorno)


def test_l_anno_chiuso_blocca_presenze_e_progressione(capo, capogruppo, ragazza, reparto):
    from apps.progressione import servizi as pp

    periodo = pp.apri_sentiero(ragazza, pp.DataParziale.giorno(PASSATO.inizio), capo.utente)
    AnnoChiuso.objects.create(anno=PASSATO.anno_fine, chiuso_il="2026-01-01T00:00Z")
    with pytest.raises(ValidationError):
        pp.registra_promessa(
            periodo, pp.DataParziale.giorno(PASSATO.inizio + timedelta(days=5)), capo.utente
        )
    pp.registra_promessa(periodo, pp.DataParziale.giorno(OGGI), capo.utente)


def test_promemoria_dal_primo_novembre():
    assert servizi.anno_da_chiudere(date(CORRENTE.anno_fine - 1, 10, 20)) is None
    assert servizi.anno_da_chiudere(date(CORRENTE.anno_fine - 1, 11, 2)) == CORRENTE.anno_fine - 1


# --- Archiving (DEC-44, DEC-196, DEC-211, DEC-212) -----------------------------------------


@pytest.fixture
def uscito(reparto, ragazza):
    """Left the group three years ago."""
    Appartenenza.objects.filter(persona=ragazza).update(
        data_inizio=OGGI - timedelta(days=2000), data_fine=OGGI - timedelta(days=3 * 365)
    )
    return ragazza


def test_chi_e_da_archiviare(uscito, capo, capogruppo):
    assert list(servizi.da_archiviare()) == [uscito]
    assert _client(capo).get("/api/v1/archivio").status_code == 403
    dati = _client(capogruppo).get("/api/v1/archivio").json()
    assert dati["da_archiviare"][0]["id"] == uscito.pk and dati["drive_configurato"] is False


def test_archiviazione(uscito, capo, capogruppo, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    Nota.objects.create(persona=uscito, tipo="STAFF", testo="Riservata", autore=capo.utente)
    caricati = {}

    def finto(nome, contenuto):
        caricati[nome] = contenuto
        return {
            "id": "file-1",
            "md5": hashlib.md5(contenuto, usedforsecurity=False).hexdigest(),
            "dimensione": len(contenuto),
        }

    with mock.patch.object(drive, "carica", side_effect=drive.ErroreDrive("Drive giù")):
        risposta = _post(capogruppo, f"/api/v1/archivio/{uscito.pk}")
    assert risposta.status_code == 400 and Nota.objects.exists()  # nothing erased
    with mock.patch.object(drive, "carica", side_effect=finto):
        risposta = _post(capogruppo, f"/api/v1/archivio/{uscito.pk}")
    assert risposta.status_code == 200, risposta.content
    nome, contenuto = next(iter(caricati.items()))
    assert "Esploratrice Giulia" in nome
    import io
    import zipfile

    with zipfile.ZipFile(io.BytesIO(contenuto)) as z:
        nomi = z.namelist()
        assert "fascicolo.json" in nomi and any(n.endswith(".pdf") for n in nomi)
    persona = Persona.objects.get(pk=uscito.pk)
    assert (persona.nome, persona.cognome) == ("Giulia", "Esploratrice")
    assert persona.codice_fiscale is None and persona.utente_id is None
    assert Appartenenza.objects.filter(persona=persona).exists()
    assert not Nota.objects.exists()
    assert Archiviazione.objects.get().file_drive == "file-1"
    assert not servizi.da_archiviare().exists()


def test_caricamento_sul_drive(settings, tmp_path):
    chiave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = chiave.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    ).decode()
    credenziali = tmp_path / "chiave.json"
    credenziali.write_text(
        json.dumps({"client_email": "qdc@progetto.iam.example", "private_key": pem})
    )
    settings.QDC_DRIVE_CREDENZIALI = str(credenziali)
    settings.QDC_DRIVE_CARTELLA = "cartella"
    contenuto = b"PK archivio"

    def risposta(stato, dati):
        r = mock.Mock(status_code=stato)
        r.json.return_value = dati
        return r

    giusto = {
        "id": "x",
        "md5Checksum": hashlib.md5(contenuto, usedforsecurity=False).hexdigest(),
        "size": str(len(contenuto)),
    }
    with mock.patch.object(
        drive.requests,
        "post",
        side_effect=[risposta(200, {"access_token": "t"}), risposta(200, giusto)],
    ) as post:
        assert drive.carica("a.zip", contenuto)["id"] == "x"
    assert post.call_args.kwargs["params"]["supportsAllDrives"] == "true"
    sbagliato = {**giusto, "md5Checksum": "0" * 32}
    with (
        mock.patch.object(
            drive.requests,
            "post",
            side_effect=[risposta(200, {"access_token": "t"}), risposta(200, sbagliato)],
        ),
        pytest.raises(drive.ErroreDrive, match="non corrisponde"),
    ):
        drive.carica("a.zip", contenuto)


# --- Moving a file to another group (DEC-46, DEC-213) --------------------------------------


def test_esportazione_e_importazione(capo, capogruppo, ragazza):
    from apps.progressione import servizi as pp

    ragazza.codice_fiscale = "ESPGLI13A41Z000X"  # fictional
    ragazza.save()
    periodo = pp.apri_sentiero(
        ragazza, pp.DataParziale.giorno(OGGI - timedelta(days=100)), capo.utente
    )
    pp.nuovo(Obiettivo, periodo, capo.utente, testo="Riservata", dal_ragazzo=False, riservata=True)
    pp.nuovo(Obiettivo, periodo, capo.utente, testo="Condivisibile", dal_ragazzo=False)
    Nota.objects.create(persona=ragazza, tipo="STAFF", testo="Solo Co.Ca.", autore=capo.utente)
    Nota.objects.create(
        persona=ragazza, tipo="STAFF", testo="Per la famiglia", visibile_genitori=True
    )
    url = f"/api/v1/persone/{ragazza.pk}/trasferimento.json"
    assert _client(capo).get(url).status_code == 403
    dati = json.loads(_client(capogruppo).get(url).content)
    assert dati["formato"] == "qdc-fascicolo"
    assert [m["testo"] for m in dati["progressione"][0]["mete"]] == ["Condivisibile"]
    assert [n["testo"] for n in dati["note"]] == ["Per la famiglia"]
    assert "presenze" not in dati
    # The other group: here simulated by removing what was there and importing.
    PeriodoBranca.objects.all().delete()
    Nota.objects.all().delete()
    dati["gruppo"] = "Gruppo di provenienza"
    file = SimpleUploadedFile("f.json", json.dumps(dati).encode())
    esito = _client(capogruppo).post("/api/v1/trasferimenti", {"file": file}).json()
    assert esito["periodi"] == 1 and esito["note"] == 1
    assert PeriodoBranca.objects.get().provenienza == "Gruppo di provenienza"
    assert PeriodoBranca.objects.get().data_fine is None  # nothing open here: it goes on
    # Twice: refused.
    file = SimpleUploadedFile("f.json", json.dumps(dati).encode())
    assert _client(capogruppo).post("/api/v1/trasferimenti", {"file": file}).status_code == 400
    # Unknown person or a wrong file.
    dati["persona"]["codice_fiscale"] = "XXXXXX00X00X000X"
    file = SimpleUploadedFile("f.json", json.dumps(dati).encode())
    assert (
        "BuonaStrada"
        in _client(capogruppo).post("/api/v1/trasferimenti", {"file": file}).json()["detail"]
    )
    file = SimpleUploadedFile("f.json", b"[1, 2]")
    assert _client(capogruppo).post("/api/v1/trasferimenti", {"file": file}).status_code == 400


def test_il_capo_porta_servizio_e_formazione(capo, capogruppo):
    from apps.fascicolo.models import Formazione

    Formazione.objects.create(persona=capo, tipo="CFM", data=date(2019, 7, 1), luogo="Bracigliano")
    dati = json.loads(
        _client(capogruppo).get(f"/api/v1/persone/{capo.pk}/trasferimento.json").content
    )
    assert dati["capo"]["formazione"][0]["tipo"] == "CFM" and dati["capo"]["anni"]


def test_i_genitori_vanno_con_l_ultimo_figlio(uscito, genitore, capogruppo, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    dati = _client(capogruppo).get("/api/v1/archivio").json()
    assert dati["da_archiviare"][0]["genitori"] == ["Genitore Mario"]

    def finto(nome, contenuto):
        return {
            "id": "f",
            "md5": hashlib.md5(contenuto, usedforsecurity=False).hexdigest(),
            "dimensione": len(contenuto),
        }

    with mock.patch.object(drive, "carica", side_effect=finto):
        assert _post(capogruppo, f"/api/v1/archivio/{uscito.pk}").status_code == 200
    genitore.refresh_from_db()
    assert genitore.nome == "Persona" and genitore.utente_id is None and not genitore.email


def test_un_genitore_con_un_altro_figlio_nel_gruppo_resta(uscito, genitore, reparto):
    from apps.anagrafica.models import RelazioneTutela, RuoloAppartenenza
    from tests.conftest import INIZIO_ANNO, crea_persona

    fratello = crea_persona("Luca", "Fratello")
    Appartenenza.objects.create(
        persona=fratello, unita=reparto, ruolo=RuoloAppartenenza.RAGAZZO, data_inizio=INIZIO_ANNO
    )
    RelazioneTutela.objects.create(tutore=genitore, minore=fratello, tipo="GENITORE")
    assert servizi.genitori_da_includere(uscito) == []


def _archivia(capogruppo, persona):
    caricati = []

    def finto(nome, contenuto):
        caricati.append(contenuto)
        md5 = hashlib.md5(contenuto, usedforsecurity=False).hexdigest()
        return {"id": "f", "md5": md5, "dimensione": len(contenuto)}

    with mock.patch.object(drive, "carica", side_effect=finto):
        risposta = _post(capogruppo, f"/api/v1/archivio/{persona.pk}")
    assert risposta.status_code == 200, risposta.content
    return caricati[0]


def test_rientro_dopo_l_archiviazione(uscito, capo, capogruppo, settings, tmp_path):
    """Back years later: the archive ZIP brings back the Progressione and joins the
    record that stayed (DEC-215)."""
    from apps.progressione import servizi as pp
    from tests.conftest import crea_persona

    settings.MEDIA_ROOT = tmp_path
    uscito.codice_fiscale = "ESPGLI13A41Z000X"  # fictional
    uscito.save()
    periodo = PeriodoBranca.objects.create(
        persona=uscito,
        branca="EG",
        data_inizio=OGGI - timedelta(days=1900),
        data_fine=OGGI - timedelta(days=3 * 365),
    )
    pp.Tappa.objects.create(periodo=periodo, fase="SCOPERTA", data_inizio=periodo.data_inizio)
    zip_archivio = _archivia(capogruppo, uscito)
    assert not PeriodoBranca.objects.exists()
    # BuonaStrada brings her back as a new record, with her codice fiscale.
    tornata = crea_persona("Giulia", "Esploratrice", codice_fiscale="ESPGLI13A41Z000X")
    file = SimpleUploadedFile("archivio.zip", zip_archivio)
    esito = _client(capogruppo).post("/api/v1/trasferimenti", {"file": file}).json()
    assert esito["persona_id"] == tornata.pk and esito["periodi"] == 1
    assert PeriodoBranca.objects.get().persona == tornata
    # The years in the group are hers again; the record that stayed is gone.
    assert Appartenenza.objects.filter(persona=tornata).exists()
    assert not Persona.objects.filter(pk=uscito.pk).exists()
    assert Archiviazione.objects.get().persona == tornata


def test_rientro_da_capo(capo, capogruppo, settings, tmp_path):
    from apps.fascicolo.models import Formazione
    from apps.organizzazione.models import Incarico
    from tests.conftest import crea_persona

    settings.MEDIA_ROOT = tmp_path
    capo.codice_fiscale = "CPANNA90A41Z000X"  # fictional
    capo.save()
    Formazione.objects.create(persona=capo, tipo="CFM", data=date(2019, 7, 1))
    passato = OGGI - timedelta(days=3 * 365)
    Appartenenza.objects.filter(persona=capo).update(
        data_inizio=passato - timedelta(days=900), data_fine=passato
    )
    Incarico.objects.filter(persona=capo).update(
        data_inizio=passato - timedelta(days=900), data_fine=passato
    )
    zip_archivio = _archivia(capogruppo, capo)
    assert not Formazione.objects.exists()
    tornato = crea_persona("Anna", "Capo", codice_fiscale="CPANNA90A41Z000X")
    file = SimpleUploadedFile("archivio.zip", zip_archivio)
    esito = _client(capogruppo).post("/api/v1/trasferimenti", {"file": file}).json()
    assert esito["formazione"] == 1 and esito["anni_di_servizio"] == 0  # roles came back
    assert Incarico.objects.filter(persona=tornato).exists()
