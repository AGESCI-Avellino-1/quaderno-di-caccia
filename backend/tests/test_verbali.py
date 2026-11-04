"""The minutes of a meeting (DEC-322…DEC-331)."""

from datetime import date, timedelta
from io import BytesIO
from types import SimpleNamespace

import pytest
from auditlog.models import LogEntry
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import Client, override_settings
from django.utils import timezone

from apps.anagrafica.models import Appartenenza, RuoloAppartenenza
from apps.archivio import drive
from apps.diritti import servizi as diritti
from apps.eventi.models import Cerchia, Evento, Livello, Partecipazione, TipoEvento
from apps.impostazioni.models import Impostazioni
from apps.organizzazione.models import AnnoChiuso, Incarico, RuoloIncarico
from apps.permessi import policy
from apps.permessi.models import AccessoDatoSensibile, Categoria
from apps.verbali import servizi, stampa
from apps.verbali.models import AllegatoVerbale, StatoVerbale, TipoVerbale, Verbale
from tests.conftest import INIZIO_ANNO, crea_capo, crea_persona

pytestmark = pytest.mark.django_db

PDF = b"%PDF-1.4 prova"


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


def _post(chi, url, dati=None):
    return _client(chi).post(url, dati or {}, content_type="application/json")


def _put(chi, url, dati):
    return _client(chi).put(url, dati, content_type="application/json")


def _url(evento, altro="") -> str:
    return f"/api/v1/eventi/{evento.pk}/verbale{altro}"


def _riunione(titolo="Riunione", giorni_fa=1, unita=(), **campi) -> Evento:
    inizio = timezone.now() - timedelta(days=giorni_fa)
    evento = Evento.objects.create(
        titolo=titolo,
        tipo=TipoEvento.RIUNIONE,
        inizio=inizio,
        fine=inizio + timedelta(hours=2),
        **{"livello": Livello.UNITA, **campi},
    )
    evento.unita.set(unita)
    return evento


@pytest.fixture(autouse=True)
def email_accese():
    imp = Impostazioni.carica()
    imp.email_capi = imp.email_genitori = imp.email_ragazzi = True
    imp.save()


@pytest.fixture
def staff(reparto, coca):
    persona = crea_capo("Elena", "Staff", "staff-verbali@example.invalid")
    Incarico.objects.create(
        persona=persona, ruolo=RuoloIncarico.STAFF, unita=reparto, data_inizio=INIZIO_ANNO
    )
    return persona


@pytest.fixture
def di_squadriglia(squadriglia, csq, ragazza) -> Evento:
    evento = _riunione(
        "Riunione di squadriglia", livello=Livello.SQUADRIGLIA, squadriglia=squadriglia
    )
    for persona in (csq, ragazza):
        Partecipazione.objects.create(evento=evento, persona=persona)
    return evento


@pytest.fixture
def di_coca(coca) -> Evento:
    return _riunione("Comunità capi", unita=[coca])


@pytest.fixture
def consiglio(reparto, csq) -> Evento:
    evento = _riunione("Consiglio Capi", unita=[reparto], cerchia=Cerchia.CONSIGLIO_CAPI)
    Partecipazione.objects.create(evento=evento, persona=csq)
    return evento


def _definitivo(evento, chi, testo="<p>Si è deciso.</p>") -> None:
    assert _put(chi, _url(evento), {"testo": testo}).status_code == 200
    assert _post(chi, _url(evento, "/definitivo")).status_code == 200


# --- Which meetings -----------------------------------------------------------------------


def test_quali_riunioni(di_squadriglia, di_coca, consiglio, reparto):
    assert servizi.tipo_di(di_squadriglia) == TipoVerbale.SQUADRIGLIA
    assert servizi.tipo_di(di_coca) == TipoVerbale.COCA
    assert servizi.tipo_di(consiglio) == TipoVerbale.CONSIGLIO_CAPI
    # Not the ordinary meeting of a unit, nor the Consiglio degli Anziani, nor an outing.
    assert servizi.tipo_di(_riunione(unita=[reparto])) is None
    assert servizi.tipo_di(_riunione(unita=[reparto], cerchia=Cerchia.CONSIGLIO_ANZIANI)) is None
    uscita = _riunione(unita=[reparto])
    uscita.tipo = TipoEvento.USCITA
    assert servizi.tipo_di(uscita) is None


def test_una_riunione_senza_verbale_risponde_404(capo, reparto):
    assert _client(capo).get(_url(_riunione(unita=[reparto]))).status_code == 404


# --- Who writes ---------------------------------------------------------------------------


def test_chi_scrive_in_squadriglia(
    staff, csq, ragazza, capogruppo, genitore, estraneo, di_squadriglia
):
    corpo = {"testo": "<p>Ciao</p>"}
    for chi in (ragazza, capogruppo, genitore, estraneo):
        assert _put(chi, _url(di_squadriglia), corpo).status_code == 403
    assert _put(csq, _url(di_squadriglia), corpo).status_code == 200
    assert _put(staff, _url(di_squadriglia), corpo).status_code == 200


def test_chi_scrive_nei_consigli_e_in_coca(staff, csq, capogruppo, capo, consiglio, di_coca):
    corpo = {"testo": "<p>Ciao</p>"}
    assert _put(staff, _url(consiglio), corpo).status_code == 200
    assert _put(csq, _url(consiglio), corpo).status_code == 403
    assert _put(capogruppo, _url(consiglio), corpo).status_code == 403
    assert _put(capogruppo, _url(di_coca), corpo).status_code == 200
    assert _put(capo, _url(di_coca), corpo).status_code == 403


def test_il_csq_indica_chi_scrive_anche_col_cronista(csq, ragazza, capo, estraneo, di_squadriglia):
    # The cronista's role alone gives no permission (DEC-324).
    Incarico.objects.create(
        persona=ragazza,
        ruolo=RuoloIncarico.CRONISTA,
        squadriglia=di_squadriglia.squadriglia,
        data_inizio=INIZIO_ANNO,
    )
    corpo = {"testo": "<p>Ciao</p>"}
    assert _put(ragazza, _url(di_squadriglia), corpo).status_code == 403
    url = _url(di_squadriglia, "/redattore")
    assert _put(ragazza, url, {"persona_id": ragazza.pk}).status_code == 403
    # Only who was invited, or a capo.
    assert _put(csq, url, {"persona_id": estraneo.pk}).status_code == 400
    assert _put(csq, url, {"persona_id": capo.pk}).status_code == 200
    assert _put(csq, url, {"persona_id": ragazza.pk}).status_code == 200
    assert _put(ragazza, _url(di_squadriglia), corpo).status_code == 200
    assert (
        _client(ragazza).get(_url(di_squadriglia, "?testo=true")).json()["testo"] == "<p>Ciao</p>"
    )
    # They write, they do not close it, and their permission ends with it.
    assert _post(ragazza, _url(di_squadriglia, "/definitivo")).status_code == 403
    assert _post(csq, _url(di_squadriglia, "/definitivo")).status_code == 200
    assert Verbale.objects.get(evento=di_squadriglia).redattore is None
    assert _put(ragazza, _url(di_squadriglia), corpo).status_code == 403


# --- Who reads ----------------------------------------------------------------------------


def test_chi_legge_in_bozza(capo, csq, ragazza, genitore, estraneo, di_squadriglia):
    assert _put(csq, _url(di_squadriglia), {"testo": "<p>Bozza</p>"}).status_code == 200
    for chi in (capo, csq):
        assert _client(chi).get(_url(di_squadriglia)).status_code == 200
    for chi in (ragazza, genitore, estraneo):
        assert _client(chi).get(_url(di_squadriglia)).status_code == 404


def test_chi_legge_il_definitivo_di_squadriglia(
    capo, csq, ragazza, genitore, estraneo, di_squadriglia
):
    _definitivo(di_squadriglia, csq)
    for chi in (capo, csq, ragazza, genitore):
        risposta = _client(chi).get(_url(di_squadriglia, "?testo=true"))
        assert risposta.status_code == 200, chi
        assert risposta.json()["testo"] == "<p>Si è deciso.</p>"
    assert _client(estraneo).get(_url(di_squadriglia)).status_code == 404


def test_chi_legge_il_definitivo_dei_consigli(
    staff, capo, csq, ragazza, genitore, estraneo, consiglio
):
    _definitivo(consiglio, staff)
    for chi in (staff, capo, csq):
        assert _client(chi).get(_url(consiglio)).status_code == 200
    # Parents read the councils' minutes of no one (DEC-323), nor who was not invited.
    for chi in (ragazza, genitore, estraneo):
        assert _client(chi).get(_url(consiglio)).status_code == 404


def test_la_coca_solo_per_i_capi(capo, capogruppo, csq, genitore, estraneo, di_coca):
    _definitivo(di_coca, capogruppo)
    for chi in (capo, capogruppo):
        assert _client(chi).get(_url(di_coca)).status_code == 200
    for chi in (csq, genitore, estraneo):
        assert _client(chi).get(_url(di_coca)).status_code == 404
        assert _client(chi).get(_url(di_coca, ".pdf")).status_code == 404


def test_capo_in_attesa_non_legge(capogruppo, di_coca, coca):
    _definitivo(di_coca, capogruppo)
    nuovo = crea_persona("Nuovo", "Capo", "nuovo-capo@example.invalid", codice_socio="9000000001")
    Appartenenza.objects.create(
        persona=nuovo, unita=coca, ruolo=RuoloAppartenenza.CAPO, data_inizio=INIZIO_ANNO
    )
    assert policy.e_capo_in_attesa(nuovo.utente)
    assert _client(nuovo).get(_url(di_coca)).status_code == 404


# --- States -------------------------------------------------------------------------------


def test_definitivo_e_riapertura(csq, staff, di_squadriglia):
    assert _post(csq, _url(di_squadriglia, "/definitivo")).status_code == 400  # empty
    _definitivo(di_squadriglia, csq)
    assert _put(csq, _url(di_squadriglia), {"testo": "<p>Altro</p>"}).status_code == 403
    assert _post(csq, _url(di_squadriglia, "/riapri"), {"motivo": " "}).status_code == 400
    assert _post(csq, _url(di_squadriglia, "/riapri"), {"motivo": "Un errore"}).status_code == 200
    verbale = Verbale.objects.get(evento=di_squadriglia)
    assert verbale.stato == StatoVerbale.BOZZA
    # The reason stays in the log.
    assert "Un errore" in str([e.changes for e in LogEntry.objects.get_for_object(verbale)])
    assert _put(staff, _url(di_squadriglia), {"testo": "<p>Altro</p>"}).status_code == 200


def test_anno_chiuso(csq, di_squadriglia):
    _definitivo(di_squadriglia, csq)
    anno = servizi.AnnoAssociativo.da_data(timezone.localdate(di_squadriglia.inizio)).anno_fine
    AnnoChiuso.objects.create(anno=anno, chiuso_il=timezone.now())
    risposta = _post(csq, _url(di_squadriglia, "/riapri"), {"motivo": "Errore"})
    assert risposta.status_code == 400
    assert "è chiuso" in risposta.json()["detail"]


def test_niente_immagini_e_html_ripulito(csq, di_squadriglia):
    testo = '<p>Ok</p><img src="/api/v1/immagini/1"><script>x()</script>'
    assert _put(csq, _url(di_squadriglia), {"testo": testo}).status_code == 200
    assert Verbale.objects.get(evento=di_squadriglia).testo == "<p>Ok</p>"


# --- Confidentiality ----------------------------------------------------------------------


def test_testo_fuori_dal_registro_delle_modifiche(capogruppo, di_coca):
    segreto = "<p>Parole riservate</p>"
    assert _put(capogruppo, _url(di_coca), {"testo": segreto}).status_code == 200
    verbale = Verbale.objects.get(evento=di_coca)
    assert "riservate" not in str([e.changes for e in LogEntry.objects.get_for_object(verbale)])
    assert LogEntry.objects.get_for_object(verbale).exists()


def test_letture_registrate_solo_per_la_coca(capo, capogruppo, csq, di_coca, di_squadriglia):
    _definitivo(di_coca, capogruppo)
    _definitivo(di_squadriglia, csq)
    AccessoDatoSensibile.objects.all().delete()
    # Opening the meeting is not reading.
    assert _client(capo).get(_url(di_coca)).status_code == 200
    assert not AccessoDatoSensibile.objects.exists()
    assert _client(capo).get(_url(di_coca, "?testo=true")).status_code == 200
    assert _client(capo).get(_url(di_coca, ".pdf")).status_code == 200
    accessi = AccessoDatoSensibile.objects.filter(categoria=Categoria.VERBALI)
    assert accessi.count() == 2
    assert all(a.utente == capo.utente and a.persona is None for a in accessi)
    assert _client(capo).get(_url(di_squadriglia, "?testo=true")).status_code == 200
    assert accessi.count() == 2
    # Who reads the register: the capigruppo.
    assert _client(capo).get(_url(di_coca)).json()["accessi"] is None
    assert len(_client(capogruppo).get(_url(di_coca)).json()["accessi"]) == 2


# --- PDF ----------------------------------------------------------------------------------


def test_pdf_da_tutto_cio_che_fa_l_editor(gruppo, capogruppo, di_coca):
    testo = (
        '<h2 style="text-align: center">Titolo</h2><p><strong>Grassetto</strong> <em>corsivo</em> '
        '<u>sotto</u> <s>barrato</s> <a href="https://esempio.it/?a=1&amp;b=2">link</a><br>a capo</p>'
        "<ul><li><p>uno</p></li><li><p>due</p><ol><li><p>dentro</p></li></ol></li></ul>"
        "<table><tbody><tr><th><p>A</p></th><th><p>B</p></th></tr>"
        "<tr><td><p>1 &lt; 2</p></td><td></td></tr></tbody></table><p>È finita &amp; ok</p>"
    )
    _definitivo(di_coca, capogruppo, testo)
    risposta = _client(capogruppo).get(_url(di_coca, ".pdf"))
    assert risposta.status_code == 200
    assert risposta.content.startswith(b"%PDF")
    assert "attachment" in risposta["Content-Disposition"]


def test_firme_solo_senza_ragazzi(capogruppo, csq, di_coca, di_squadriglia):
    _definitivo(di_coca, capogruppo)
    _definitivo(di_squadriglia, csq)
    assert stampa._firme(Verbale.objects.get(evento=di_coca), TipoVerbale.COCA)
    assert not stampa._firme(Verbale.objects.get(evento=di_squadriglia), TipoVerbale.SQUADRIGLIA)


def test_pdf_solo_definitivo(csq, di_squadriglia):
    assert _put(csq, _url(di_squadriglia), {"testo": "<p>x</p>"}).status_code == 200
    assert _client(csq).get(_url(di_squadriglia, ".pdf")).status_code == 400


# --- Files without a Drive ----------------------------------------------------------------


def _carica(chi, evento, nome="ordine.pdf", contenuto=PDF):
    risposta = _post(chi, _url(evento, "/allegati"), {"nome": nome, "dimensione": len(contenuto)})
    if risposta.status_code != 201:
        return risposta
    return _client(chi).post(
        f"/api/v1/allegati-verbale/{risposta.json()['id']}/pezzo",
        {"inizio": 0, "file": SimpleUploadedFile("pezzo", contenuto)},
    )


def test_allegato_sul_server_senza_drive(capo, csq, ragazza, estraneo, di_squadriglia):
    assert _carica(csq, di_squadriglia).status_code == 200
    allegato = AllegatoVerbale.objects.get()
    assert allegato.completo and allegato.file and not allegato.drive_id
    assert "ordine" not in allegato.file.name  # a random name on disk
    url = f"/api/v1/allegati-verbale/{allegato.pk}"
    risposta = _client(capo).get(url)
    assert b"".join(risposta.streaming_content) == PDF
    assert risposta["Content-Type"] == "application/pdf"
    assert 'filename="ordine.pdf"' in risposta["Content-Disposition"]
    assert risposta["X-Content-Type-Options"] == "nosniff"
    # Reads as the minutes: in draft the ragazza no, and nor does an outsider.
    assert _client(ragazza).get(url).status_code == 404
    assert _client(estraneo).get(url).status_code == 404
    _definitivo(di_squadriglia, csq)
    assert _client(ragazza).get(url).status_code == 200
    assert _client(estraneo).get(url).status_code == 404


def test_tipi_e_dimensioni(csq, di_squadriglia):
    assert _carica(csq, di_squadriglia, "virus.exe").status_code == 400
    # The name says PDF, the first bytes do not.
    risposta = _carica(csq, di_squadriglia, "finto.pdf", b"MZ esegui")
    assert risposta.status_code == 400
    assert not AllegatoVerbale.objects.filter(completo=True).exists()
    troppo = {"nome": "grande.pdf", "dimensione": servizi.MASSIMO_SUL_SERVER + 1}
    risposta = _post(csq, _url(di_squadriglia, "/allegati"), troppo)
    assert risposta.status_code == 400
    assert "20 MB" in risposta.json()["detail"]
    # Office, audio and video are accepted.
    for nome, inizio in (
        ("a.docx", b"PK\x03\x04dati"),
        ("b.xls", b"\xd0\xcf\x11\xe0dati"),
        ("c.mp3", b"ID3dati"),
        ("d.mp4", b"\x00\x00\x00\x18ftypmp42"),
        ("e.png", b"\x89PNGdati"),
    ):
        assert _carica(csq, di_squadriglia, nome, inizio).status_code == 200, nome


def test_incompleto_non_si_vede_e_si_pulisce(csq, di_squadriglia):
    risposta = _post(csq, _url(di_squadriglia, "/allegati"), {"nome": "a.pdf", "dimensione": 5})
    allegato = AllegatoVerbale.objects.get(pk=risposta.json()["id"])
    assert _client(csq).get(f"/api/v1/allegati-verbale/{allegato.pk}").status_code == 404
    assert _client(csq).get(_url(di_squadriglia)).json()["allegati"] == []
    AllegatoVerbale.objects.update(creato_il=timezone.now() - timedelta(days=9))
    assert servizi.pulisci_caricamenti_interrotti(timezone.localdate()) == 1


def test_allegato_del_definitivo_si_toglie_riaprendo(csq, ragazza, di_squadriglia):
    assert _carica(csq, di_squadriglia).status_code == 200
    allegato = AllegatoVerbale.objects.get()
    url = f"/api/v1/allegati-verbale/{allegato.pk}"
    assert _client(ragazza).delete(url).status_code == 403
    _definitivo(di_squadriglia, csq)
    assert _client(csq).delete(url).status_code == 403
    assert _post(csq, _url(di_squadriglia, "/riapri"), {"motivo": "Errato"}).status_code == 200
    assert _client(csq).delete(url).status_code == 204
    assert not AllegatoVerbale.objects.exists()


def test_zip_con_verbale_e_allegati(csq, di_squadriglia):
    import zipfile

    assert _carica(csq, di_squadriglia, "a.pdf").status_code == 200
    assert _carica(csq, di_squadriglia, "a.pdf", b"%PDF altro").status_code == 200
    assert _client(csq).get(_url(di_squadriglia, ".zip")).status_code == 400  # still a draft
    _definitivo(di_squadriglia, csq)
    risposta = _client(csq).get(_url(di_squadriglia, ".zip"))
    assert risposta.status_code == 200
    with zipfile.ZipFile(BytesIO(b"".join(risposta.streaming_content))) as archivio:
        assert set(archivio.namelist()) == {"verbale.pdf", "allegati/a.pdf", "allegati/a (2).pdf"}
        assert archivio.read("allegati/a (2).pdf") == b"%PDF altro"
    AllegatoVerbale.objects.update(dimensione=servizi.MASSIMO_ZIP)
    assert _client(csq).get(_url(di_squadriglia, ".zip")).status_code == 400
    assert _client(csq).get(_url(di_squadriglia)).json()["zip_possibile"] is False


# --- Files on the Drive -------------------------------------------------------------------


class _DriveFinto:
    """Google's side, at the level of `requests`: resumable upload, folders, reading."""

    def __init__(self) -> None:
        self.cartelle: dict[tuple[str, str], str] = {}
        self.sessioni: dict[str, dict] = {}
        self.file: dict[str, bytes] = {}
        self.cancellati: list[str] = []
        self.pezzi: list[str] = []

    @staticmethod
    def _risposta(stato, json=None, intestazioni=None, contenuto=b""):
        return SimpleNamespace(
            status_code=stato,
            json=lambda: json,
            headers=intestazioni or {},
            iter_content=lambda n: [contenuto[i : i + n] for i in range(0, len(contenuto), n)],
        )

    def get(self, url, params=None, headers=None, **_):
        assert headers and headers["Authorization"] == "Bearer finto"
        if params.get("alt") == "media":
            return self._risposta(200, contenuto=self.file[url.rsplit("/", 1)[-1]])
        nome, genitore = params["q"].split("'")[1], params["q"].split("'")[3]
        trovata = self.cartelle.get((nome, genitore))
        return self._risposta(200, {"files": [{"id": trovata}] if trovata else []})

    def post(self, url, params=None, headers=None, json=None, **_):
        if params.get("uploadType") == "resumable":
            sessione = f"https://google.invalid/sessione/{len(self.sessioni)}"
            self.sessioni[sessione] = {
                "nome": json["name"],
                "genitore": json["parents"][0],
                "dati": b"",
            }
            return self._risposta(200, intestazioni={"Location": sessione})
        identificativo = f"cartella-{json['name']}"
        self.cartelle[(json["name"], json["parents"][0])] = identificativo
        return self._risposta(200, {"id": identificativo})

    def put(self, url, data=None, headers=None, **_):
        self.pezzi.append(headers["Content-Range"])
        sessione = self.sessioni[url]
        sessione["dati"] += data
        totale = int(headers["Content-Range"].rsplit("/", 1)[-1])
        if len(sessione["dati"]) < totale:
            return self._risposta(308)
        identificativo = f"file-{len(self.file)}"
        self.file[identificativo] = sessione["dati"]
        return self._risposta(200, {"id": identificativo, "size": str(totale)})

    def delete(self, url, **_):
        self.cancellati.append(url.rsplit("/", 1)[-1])
        return self._risposta(204)


@pytest.fixture
def google(monkeypatch):
    finto = _DriveFinto()
    for verbo in ("get", "post", "put", "delete"):
        monkeypatch.setattr(drive.requests, verbo, getattr(finto, verbo))
    monkeypatch.setattr(drive, "_token", lambda: "finto")
    with override_settings(QDC_DRIVE_CREDENZIALI="/x.json", QDC_DRIVE_CARTELLA="radice"):
        yield finto


def test_caricamento_a_pezzi_su_drive(google, csq, capo, di_squadriglia):
    contenuto = PDF + b"x" * 300
    risposta = _post(
        csq, _url(di_squadriglia, "/allegati"), {"nome": "grande.pdf", "dimensione": len(contenuto)}
    )
    assert risposta.status_code == 201, risposta.content
    allegato = AllegatoVerbale.objects.get(pk=risposta.json()["id"])
    assert allegato.sessione and not allegato.completo
    # A folder for the minutes and one for the year, once only.
    anno = servizi.AnnoAssociativo.da_data(timezone.localdate(di_squadriglia.inizio))
    cartella = anno.etichetta.replace("/", "-")
    assert ("Verbali", "radice") in google.cartelle
    assert (cartella, "cartella-Verbali") in google.cartelle
    url = f"/api/v1/allegati-verbale/{allegato.pk}/pezzo"
    primo = _client(csq).post(url, {"inizio": 0, "file": SimpleUploadedFile("p", contenuto[:100])})
    assert primo.json() == {"ricevuti": 100, "completo": False}
    # Out of order: refused, nothing is sent.
    fuori = _client(csq).post(url, {"inizio": 50, "file": SimpleUploadedFile("p", contenuto[100:])})
    assert fuori.status_code == 400
    ultimo = _client(csq).post(
        url, {"inizio": 100, "file": SimpleUploadedFile("p", contenuto[100:])}
    )
    assert ultimo.json()["completo"] is True
    assert google.pezzi == [
        f"bytes 0-99/{len(contenuto)}",
        f"bytes 100-{len(contenuto) - 1}/{len(contenuto)}",
    ]
    allegato.refresh_from_db()
    assert allegato.drive_id == "file-0" and allegato.sessione == "" and not allegato.file
    # Never a link to the Drive: through the app, as the minutes.
    assert "drive" not in str(_client(capo).get(_url(di_squadriglia)).json()["allegati"])
    risposta = _client(capo).get(f"/api/v1/allegati-verbale/{allegato.pk}")
    assert b"".join(risposta.streaming_content) == contenuto
    assert risposta["X-Accel-Buffering"] == "no"
    assert _client(csq).delete(f"/api/v1/allegati-verbale/{allegato.pk}").status_code == 204
    assert google.cancellati == ["file-0"]


def test_massimo_due_giga_su_drive(google, csq, di_squadriglia):
    url = _url(di_squadriglia, "/allegati")
    assert (
        _post(csq, url, {"nome": "v.mp4", "dimensione": servizi.MASSIMO_SU_DRIVE}).status_code
        == 201
    )
    troppo = _post(csq, url, {"nome": "v.mp4", "dimensione": servizi.MASSIMO_SU_DRIVE + 1})
    assert troppo.status_code == 400
    assert "2 GB" in troppo.json()["detail"]


def test_drive_che_non_risponde(google, monkeypatch, csq, di_squadriglia):
    monkeypatch.setattr(
        drive.requests, "post", lambda *a, **k: SimpleNamespace(status_code=500, headers={})
    )
    risposta = _post(csq, _url(di_squadriglia, "/allegati"), {"nome": "a.pdf", "dimensione": 5})
    assert risposta.status_code == 503
    assert not AllegatoVerbale.objects.exists()


# --- Reminders ----------------------------------------------------------------------------


def _promemoria(giorno: date) -> int:
    mail.outbox.clear()
    return servizi.promemoria(giorno)


def test_promemoria_ogni_sette_giorni_massimo_tre(capogruppo, coca, csq):
    evento = _riunione("Comunità capi", giorni_fa=7, unita=[coca])
    oggi = timezone.localdate()
    assert _promemoria(oggi - timedelta(days=1)) == 0  # not yet seven days
    assert _promemoria(oggi) == 1
    assert mail.outbox[0].to == [capogruppo.utente.email]
    assert "Comunità capi" in mail.outbox[0].subject
    assert mail.outbox[0].extra_headers.get("X-QdC-Tipo") == "promemoria_verbale"
    assert _promemoria(oggi + timedelta(days=6)) == 0
    assert _promemoria(oggi + timedelta(days=7)) == 1
    assert _promemoria(oggi + timedelta(days=14)) == 1
    assert _promemoria(oggi + timedelta(days=21)) == 0  # three at most
    assert Verbale.objects.get(evento=evento).promemoria_inviati == 3


def test_promemoria_anche_a_chi_e_indicato(capogruppo, capo, coca):
    evento = _riunione("Comunità capi", giorni_fa=7, unita=[coca])
    assert _put(capogruppo, _url(evento, "/redattore"), {"persona_id": capo.pk}).status_code == 200
    assert _promemoria(timezone.localdate()) == 2
    assert {m.to[0] for m in mail.outbox} == {capogruppo.utente.email, capo.utente.email}


def test_nessun_promemoria_se_non_serve(capogruppo, coca, reparto, csq, squadriglia):
    oggi = timezone.localdate()
    non_previsto = _riunione("Senza verbale", giorni_fa=7, unita=[coca])
    assert (
        _put(capogruppo, _url(non_previsto, "/non-previsto"), {"non_previsto": True}).status_code
        == 200
    )
    definitivo = _riunione("Già scritto", giorni_fa=7, unita=[coca])
    _definitivo(definitivo, capogruppo)
    _riunione("Annullata", giorni_fa=7, unita=[coca], annullato_il=timezone.now())
    _riunione("Vecchia", giorni_fa=40, unita=[coca])
    # The other types are optional, no reminders.
    _riunione("Consiglio", giorni_fa=7, unita=[reparto], cerchia=Cerchia.CONSIGLIO_CAPI)
    _riunione("Squadriglia", giorni_fa=7, livello=Livello.SQUADRIGLIA, squadriglia=squadriglia)
    assert _promemoria(oggi) == 0


def test_non_previsto_solo_per_la_coca(staff, consiglio):
    url = _url(consiglio, "/non-previsto")
    assert _put(staff, url, {"non_previsto": True}).status_code == 400


def test_comando_quotidiano(capogruppo, coca):
    _riunione("Comunità capi", giorni_fa=7, unita=[coca])
    mail.outbox.clear()
    call_command("promemoria_verbali")
    assert len(mail.outbox) == 1


# --- Data subjects' rights ----------------------------------------------------------------


def test_cancellazione_e_cinque_anni(capogruppo, csq, di_coca, di_squadriglia):
    autore = crea_capo("Anna", "Scrive", "scrive@example.invalid")
    coca_recente = servizi.verbale_di(di_coca)
    coca_recente.save()
    squadriglia = servizi.verbale_di(di_squadriglia)
    squadriglia.save()
    for verbale in (coca_recente, squadriglia):
        Verbale.objects.filter(pk=verbale.pk).update(
            autore=autore, autore_nome="Anna Scrive", redattore=autore
        )
    vecchia = _riunione("Vecchia", giorni_fa=2000, unita=di_coca.unita.all())
    coca_vecchia = Verbale.objects.create(evento=vecchia, autore=autore, autore_nome="Anna Scrive")
    servizi.alla_cancellazione(autore)
    for verbale in (coca_recente, squadriglia, coca_vecchia):
        verbale.refresh_from_db()
        assert verbale.autore is None and verbale.redattore is None
    # Within the five years the Co.Ca. keeps the name, the others lose it at once.
    assert coca_recente.autore_nome == "Anna Scrive" and coca_recente.nome_a_scadenza
    assert squadriglia.autore_nome == "" and coca_vecchia.autore_nome == ""
    # When the five years are over it goes.
    assert servizi.togli_nomi_scaduti(timezone.localdate()) == 0
    giorno = timezone.localdate(di_coca.inizio) + timedelta(days=5 * 366)
    assert servizi.togli_nomi_scaduti(giorno) == 1
    coca_recente.refresh_from_db()
    assert coca_recente.autore_nome == "" and not coca_recente.nome_a_scadenza


def test_anteprima_segnala_il_nome_nel_testo(capogruppo, di_coca, ragazza):
    testo = f"<p>Abbiamo parlato di {ragazza.nome} {ragazza.cognome}.</p>"
    assert _put(capogruppo, _url(di_coca), {"testo": testo}).status_code == 200
    anteprima = diritti.anteprima_cancellazione(ragazza)
    assert anteprima["verbali_col_nome"] == [str(di_coca)]
    # The text is not touched by the erasure.
    diritti.cancella(ragazza)
    assert ragazza.nome in Verbale.objects.get(evento=di_coca).testo


def test_chi_ha_scritto_nel_fascicolo(capogruppo, di_coca):
    assert _put(capogruppo, _url(di_coca), {"testo": "<p>x</p>"}).status_code == 200
    assert diritti.fascicolo(capogruppo)["verbali_scritti"] == [{"Riunione": str(di_coca)}]
