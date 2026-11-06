"""The placeholders of the minutes written by hand, their preview and the group's VAT number."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from django.test import Client
from django.utils import timezone

from apps.eventi.models import Cerchia, Evento, Livello, Localita, Partecipazione, TipoEvento
from apps.organizzazione.models import Gruppo
from apps.verbali import segnaposto, servizi
from apps.verbali.models import Verbale

pytestmark = pytest.mark.django_db

ROMA = ZoneInfo("Europe/Rome")
TUTTI = " ".join(segnaposto.ELENCO)


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


def _url(evento, altro="") -> str:
    return f"/api/v1/eventi/{evento.pk}/verbale{altro}"


def _post(chi, url, dati=None):
    return _client(chi).post(url, dati or {}, content_type="application/json")


def _put(chi, url, dati):
    return _client(chi).put(url, dati, content_type="application/json")


def _riunione(unita=(), **campi) -> Evento:
    # This year, so that the associative year is open whenever the tests run.
    oggi = datetime.now(ROMA)
    evento = Evento.objects.create(
        titolo="Riunione",
        tipo=TipoEvento.RIUNIONE,
        inizio=oggi.replace(hour=20, minute=30, second=0, microsecond=0),
        fine=oggi.replace(hour=22, minute=0, second=0, microsecond=0),
        **{"livello": Livello.UNITA, **campi},
    )
    evento.unita.set(unita)
    return evento


@pytest.fixture
def di_coca(coca) -> Evento:
    return _riunione(unita=[coca])


@pytest.fixture
def sede() -> Localita:
    return Localita.objects.create(
        nome="Sede",
        denominazione="Parrocchia <San Francesco>",
        indirizzo="Via Roma, 83100 Avellino",
        civico="1",
    )


@pytest.fixture
def dati_gruppo(gruppo) -> Gruppo:
    gruppo.denominazione = "Prova 1"
    gruppo.denominazione_sociale = "AGESCI Gruppo Prova 1"
    gruppo.codice_fiscale = "01234567890"
    gruppo.partita_iva = "09876543210"
    gruppo.save()
    return gruppo


# --- The values ---------------------------------------------------------------------------


def test_data_e_orari_dal_calendario(gruppo):
    evento = Evento(
        inizio=datetime(2026, 3, 6, 20, 30, tzinfo=ROMA),
        fine=datetime(2026, 3, 6, 22, 0, tzinfo=ROMA),
    )
    valori = segnaposto.valori(evento)
    assert valori[segnaposto.DATA] == "6 marzo 2026"
    assert valori[segnaposto.ORA_INIZIO] == "20:30"
    assert valori[segnaposto.ORA_FINE] == "22:00"


def test_la_denominazione_sociale_e_se_manca_la_breve(dati_gruppo, di_coca):
    assert segnaposto.valori(di_coca)[segnaposto.DENOMINAZIONE] == "AGESCI Gruppo Prova 1"
    dati_gruppo.denominazione_sociale = ""
    dati_gruppo.save()
    assert segnaposto.valori(di_coca)[segnaposto.DENOMINAZIONE] == "Prova 1"


def test_indirizzi_e_citta_di_una_localita_salvata(gruppo, di_coca, sede):
    di_coca.localita = sede
    valori = segnaposto.valori(di_coca)
    assert valori[segnaposto.INDIRIZZO_COMPLETO] == (
        "Parrocchia <San Francesco>, Via Roma 1, 83100 Avellino"
    )
    assert valori[segnaposto.INDIRIZZO] == "Via Roma 1, 83100 Avellino"
    assert valori[segnaposto.LUOGO] == "Avellino"


def test_senza_denominazione_la_localita_usa_il_nome_dell_elenco(gruppo, di_coca, sede):
    sede.denominazione = ""
    di_coca.localita = sede
    assert segnaposto.valori(di_coca)[segnaposto.INDIRIZZO_COMPLETO] == (
        "Sede, Via Roma 1, 83100 Avellino"
    )


def test_un_luogo_scritto_a_mano_vale_per_i_due_indirizzi(gruppo, di_coca):
    di_coca.luogo = "Campo base, Laceno"
    valori = segnaposto.valori(di_coca)
    assert valori[segnaposto.INDIRIZZO_COMPLETO] == "Campo base, Laceno"
    assert valori[segnaposto.INDIRIZZO] == "Campo base, Laceno"
    assert valori[segnaposto.LUOGO] == ""


@pytest.mark.parametrize(
    ("indirizzo", "citta"),
    [
        ("Via Roma 1, 83100 Avellino", "Avellino"),
        ("Via Roma 1, 83100 Avellino (AV)", "Avellino"),
        ("Via Roma 1, 83042 Atripalda, Campania", "Atripalda"),
        ("Via Roma 1, 80100 Reggio di Calabria", "Reggio di Calabria"),
        ("Via Roma 1, Avellino", ""),
        ("Via 25 Aprile 1", ""),
        ("", ""),
    ],
)
def test_la_citta_si_cerca_dopo_il_cap(indirizzo, citta):
    assert segnaposto._citta(indirizzo) == citta


def test_quello_che_manca_sparisce_e_si_dice_una_volta(gruppo, di_coca):
    testo = f"<p>P.IVA {segnaposto.PARTITA_IVA}, a {segnaposto.INDIRIZZO}, {segnaposto.INDIRIZZO_COMPLETO}</p>"
    assert segnaposto.sostituisci(testo, di_coca) == "<p>P.IVA , a , </p>"
    assert segnaposto.mancanti(testo, di_coca) == [
        "la partita IVA del gruppo",
        "l'indirizzo della riunione",
    ]
    assert segnaposto.mancanti("<p>Niente</p>", di_coca) == []


# --- In the life of the minutes -------------------------------------------------------------


def test_chi_scrive_vede_il_segnaposto_chi_legge_il_valore(capogruppo, capo, dati_gruppo, di_coca):
    url = _url(di_coca)
    assert _put(capogruppo, url, {"testo": "<p>Alle [Ora di inizio]</p>"}).status_code == 200
    scritto = _client(capogruppo).get(url, {"testo": "true"}).json()
    assert scritto["testo"] == "<p>Alle [Ora di inizio]</p>"
    assert segnaposto.DATA in scritto["segnaposto"]
    verbale = Verbale.objects.get(evento=di_coca)
    assert servizi.testo_in_bozza(verbale, scrive=False) == "<p>Alle 20:30</p>"


def test_il_definitivo_copia_i_valori_e_non_cambia_piu(capogruppo, dati_gruppo, di_coca, sede):
    di_coca.localita = sede
    di_coca.save()
    url = _url(di_coca)
    assert _put(capogruppo, url, {"testo": f"<p>{TUTTI}</p>"}).status_code == 200
    assert _post(capogruppo, _url(di_coca, "/definitivo")).status_code == 200
    testo = Verbale.objects.get(evento=di_coca).testo
    assert "[" not in testo
    assert "AGESCI Gruppo Prova 1" in testo
    assert "09876543210" in testo
    assert "&lt;San Francesco&gt;" in testo

    dati_gruppo.partita_iva = "11111111111"
    dati_gruppo.save()
    assert Verbale.objects.get(evento=di_coca).testo == testo
    assert "09876543210" in _client(capogruppo).get(url, {"testo": "true"}).json()["testo"]


def test_i_segnaposto_valgono_anche_senza_ordine_del_giorno(capogruppo, dati_gruppo, reparto, csq):
    consiglio = _riunione(unita=[reparto], cerchia=Cerchia.CONSIGLIO_CAPI)
    Partecipazione.objects.create(evento=consiglio, persona=csq)
    assert not servizi.ha_ordine_del_giorno(consiglio)
    verbale = servizi.verbale_di(consiglio)
    verbale.testo = "<p>Alle [Ora di fine]</p>"
    assert servizi.anteprima(verbale, verbale.testo)["testo"] == "<p>Alle 22:00</p>"


def test_l_ordine_del_giorno_non_e_toccato_dai_segnaposto(capogruppo, dati_gruppo, di_coca):
    di_coca.ordine_del_giorno = "<ol><li><p>Scegliere la [Data]</p></li></ol>"
    di_coca.save()
    risposta = _post(
        capogruppo,
        _url(di_coca, "/anteprima"),
        {"testo": "<p>[Ordine del giorno]</p><p>[Ora di fine]</p>"},
    ).json()
    assert "Scegliere la [Data]" in risposta["testo"]
    assert "22:00" in risposta["testo"]


def test_l_assemblea_col_modello_non_offre_segnaposto(capogruppo, gruppo):
    assemblea = _riunione(cerchia=Cerchia.SOCI, livello=Livello.GRUPPO)
    letto = _client(capogruppo).get(_url(assemblea)).json()
    assert letto["da_modello"] is True
    assert letto["segnaposto"] == []
    assert _post(capogruppo, _url(assemblea, "/anteprima"), {"testo": "x"}).status_code == 400


# --- The preview -----------------------------------------------------------------------------


def test_l_anteprima_mostra_il_testo_a_schermo_senza_salvarlo(capogruppo, dati_gruppo, di_coca):
    risposta = _post(
        capogruppo,
        _url(di_coca, "/anteprima"),
        {"testo": "<p>[Data] a [Luogo]</p><script>alert(1)</script>"},
    )
    assert risposta.status_code == 200
    dati = risposta.json()
    assert "[Data]" not in dati["testo"]
    assert "<script" not in dati["testo"]
    assert dati["mancanti"] == ["la città della riunione, che non si riconosce dall'indirizzo"]
    assert not Verbale.objects.filter(evento=di_coca).exists()


def test_l_anteprima_e_per_chi_scrive(capogruppo, capo, csq, ragazza, genitore, estraneo, di_coca):
    url = _url(di_coca, "/anteprima")
    assert _post(capogruppo, url, {"testo": "x"}).status_code == 200
    for chi in (capo, csq, ragazza, genitore, estraneo):
        assert _post(chi, url, {"testo": "x"}).status_code in (403, 404), chi


def test_chi_non_scrive_non_riceve_i_segnaposto(capogruppo, capo, csq, di_coca):
    assert _put(capogruppo, _url(di_coca), {"testo": "<p>Testo</p>"}).status_code == 200
    assert _post(capogruppo, _url(di_coca, "/definitivo")).status_code == 200
    # Definitive: nobody writes any more.
    assert _client(capo).get(_url(di_coca)).json()["segnaposto"] == []


# --- The VAT number ----------------------------------------------------------------------------


def test_la_partita_iva_la_scrivono_i_capigruppo(capogruppo, capo, gruppo):
    url = "/api/v1/gruppo/intestazione"
    assert _put(capogruppo, url, {"partita_iva": " 01234567890 "}).json()["partita_iva"] == (
        "01234567890"
    )
    assert _client(capo).get(url).json()["partita_iva"] == "01234567890"
    assert _put(capo, url, {"partita_iva": ""}).status_code == 403
    assert _put(capogruppo, url, {"partita_iva": ""}).status_code == 200


def test_la_partita_iva_e_di_11_cifre(capogruppo, gruppo):
    risposta = _put(capogruppo, "/api/v1/gruppo/intestazione", {"partita_iva": "123"})
    assert risposta.status_code == 400
    assert "11 cifre" in risposta.json()["detail"]


# --- The name of the PDF -----------------------------------------------------------------------


def _alle(giorno: int) -> Evento:
    return Evento(titolo="Comunità capi", inizio=datetime(2026, 3, giorno, 20, 30, tzinfo=ROMA))


def test_il_nome_del_pdf_ha_titolo_e_data():
    assert servizi.nome_pdf(_alle(6)) == "Comunità capi-06032026.pdf"


def test_il_nome_del_pdf_prende_il_giorno_locale():
    # 23:30 in Italy on the 6th is still the 6th, though it is 22:30 UTC.
    evento = Evento(titolo="Sera", inizio=datetime(2026, 3, 6, 23, 30, tzinfo=ROMA))
    assert servizi.nome_pdf(evento) == "Sera-06032026.pdf"


def test_il_nome_del_pdf_toglie_quello_che_non_puo_starci():
    evento = _alle(6)
    evento.titolo = 'Staff/Co.Ca. "marzo"'
    assert servizi.nome_pdf(evento) == "Staff-Co.Ca. _marzo_-06032026.pdf"
    evento.titolo = "Due\r\nrighe"
    assert servizi.nome_pdf(evento) == "Due__righe-06032026.pdf"
    evento.titolo = ""
    assert servizi.nome_pdf(evento) == "verbale-06032026.pdf"


def test_i_verbali_separati_hanno_il_loro_nome():
    nomi = servizi.NOMI_FILE_COLLEGATI
    assert servizi.nome_pdf(_alle(6), nomi["CAPI_GRUPPO"]) == (
        "verbale_legale_rappresentante-06032026.pdf"
    )
    assert servizi.nome_pdf(_alle(6), nomi["BILANCIO"]) == "verbale_bilancio-06032026.pdf"


def test_il_pdf_scaricato_si_chiama_cosi(capogruppo, gruppo, di_coca):
    di_coca.titolo = "Comunità capi"
    di_coca.save()
    assert _put(capogruppo, _url(di_coca), {"testo": "<p>Testo</p>"}).status_code == 200
    assert _post(capogruppo, _url(di_coca, "/definitivo")).status_code == 200
    intestazione = _client(capogruppo).get(_url(di_coca, ".pdf"))["Content-Disposition"]
    giorno = timezone.localdate(di_coca.inizio)
    assert f"filename*=UTF-8''Comunit%C3%A0%20capi-{giorno:%d%m%Y}.pdf" in intestazione
