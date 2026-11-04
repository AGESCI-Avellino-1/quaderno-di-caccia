"""The AGESCI templates: convocation and minutes of the assembly, separate minutes
(DEC-336…DEC-340)."""

from datetime import date, timedelta

import pytest
from auditlog.models import LogEntry
from django.core import mail
from django.test import Client
from django.utils import timezone

from apps.anagrafica.models import Persona
from apps.eventi.models import Evento, Presenza
from apps.impostazioni.models import Impostazioni
from apps.organizzazione.models import Gruppo, Incarico, RuoloIncarico
from apps.permessi.models import AccessoDatoSensibile
from apps.verbali import modelli, servizi
from apps.verbali.models import Verbale, VerbaleCollegato
from tests.conftest import INIZIO_ANNO, crea_capo

pytestmark = pytest.mark.django_db

LUOGO = {
    "presso": "Sede scout",
    "via": "Via Roma",
    "civico": "1",
    "cap": "83100",
    "citta": "Avellino",
    "provincia": "AV",
}


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


def _put(chi, url, dati):
    return _client(chi).put(url, dati, content_type="application/json")


def _post(chi, url, dati=None):
    return _client(chi).post(url, dati or {}, content_type="application/json")


@pytest.fixture(autouse=True)
def ambiente(gruppo):
    Gruppo.objects.update(codice_fiscale="90000000000")
    imp = Impostazioni.carica()
    imp.email_capi = imp.email_genitori = imp.email_ragazzi = True
    imp.save()


@pytest.fixture
def assemblea(capogruppo) -> Evento:
    giorno = timezone.localdate() + timedelta(days=10)
    corpo = {
        "cerchia": "SOCI",
        "giorno": giorno.isoformat(),
        "ora_inizio": "18:00",
        "ora_fine": "20:00",
    }
    risposta = _post(capogruppo, "/api/v1/riunioni", corpo)
    assert risposta.status_code == 201, risposta.content
    return Evento.objects.get(pk=risposta.json()[0]["id"])


def _url(evento, altro="") -> str:
    return f"/api/v1/eventi/{evento.pk}{altro}"


def _convocazione(evento, chi, punti=("BILANCIO", "VARIE"), **altri):
    corpo = {"punti": list(punti), "luogo": LUOGO, "anno_bilancio": 2026, **altri}
    return _put(chi, _url(evento, "/convocazione/modello"), corpo)


def _segna(evento, *persone) -> None:
    for persona in persone:
        Presenza.objects.create(evento=evento, persona=persona, stato="PRESENTE")


def _verbale_compilato(evento, chi, scrutatore, **altri) -> None:
    corpo = {
        "ora_apertura": "18:05",
        "ora_chiusura": "19:30",
        "scrutatori": [scrutatore.pk],
        "risultato": "150.5",
        "voti": {"BILANCIO": {"favorevoli": 10, "contrari": 2}},
        **altri,
    }
    risposta = _put(chi, _url(evento, "/verbale/modello"), corpo)
    assert risposta.status_code == 200, risposta.content


def _cariche(evento, chi, presidente, segretario) -> None:
    corpo = {"presidente_id": presidente.pk, "segretari_ids": [segretario.pk]}
    assert _put(chi, _url(evento, "/verbale/cariche"), corpo).status_code == 200


def _scheda_completa(persona: Persona, sesso="F") -> None:
    persona.sesso = sesso
    persona.codice_fiscale = f"XXXXXX00X00X{persona.pk:03d}X"[:16]
    persona.data_nascita = date(1980, 5, 2)
    persona.luogo_nascita = "Avellino"
    persona.indirizzo = "Via Verdi"
    persona.civico = "3"
    persona.cap = "83100"
    persona.comune = "Avellino"
    persona.provincia = "AV"
    persona.save()


# --- Convocation ----------------------------------------------------------------------------


def test_prima_convocazione_di_base_alle_zero(capogruppo, assemblea):
    risposta = _convocazione(assemblea, capogruppo).json()
    assert risposta["mancanti"] == []
    testo = risposta["testo"]
    giorno = f"{timezone.localdate(assemblea.inizio):%d/%m/%Y}"
    assert f"in prima convocazione, il giorno {giorno} alle ore 00:00" in testo
    assert "seconda convocazione lo stesso giorno presso il medesimo luogo alle ore 18:00" in testo
    assert "bilancio d'esercizio 2025/2026, chiuso al 30/09/2026" in testo


def test_prima_convocazione_in_un_altro_giorno(capogruppo, assemblea):
    prima = timezone.localtime(assemblea.inizio) - timedelta(days=1)
    testo = _convocazione(assemblea, capogruppo, prima_il=prima.isoformat()).json()["testo"]
    assert (
        f"in seconda convocazione il giorno {timezone.localdate(assemblea.inizio):%d/%m/%Y}"
        in testo
    )
    dopo = timezone.localtime(assemblea.inizio) + timedelta(hours=1)
    mancanti = _convocazione(assemblea, capogruppo, prima_il=dopo.isoformat()).json()["mancanti"]
    assert any("prima dell'orario" in m for m in mancanti)


def test_anni_scelti_separatamente(capogruppo, assemblea):
    punti = ("ELEZIONE", "BILANCIO", "QUOTA")
    testo = _convocazione(
        assemblea, capogruppo, punti=punti, anno_bilancio=2026, anno_elezione=2028
    ).json()["testo"]
    assert "per l'anno scout 2027/2028" in testo
    assert "chiuso al 30/09/2026" in testo


def test_anno_proposto_ultimo_chiuso(capogruppo, assemblea):
    dati = _client(capogruppo).get(_url(assemblea, "/convocazione/modello")).json()["dati"]
    anno = servizi.AnnoAssociativo.da_data(timezone.localdate(assemblea.inizio))
    assert dati["anno_bilancio"] == anno.anno_fine - 1
    assert dati["anno_elezione"] == anno.anno_fine


def test_convocazione_incompleta_non_parte(capogruppo, assemblea):
    risposta = _post(capogruppo, _url(assemblea, "/convocazione/invia"))
    assert risposta.status_code == 400
    assert "manca" in risposta.json()["detail"]
    assemblea.refresh_from_db()
    assert assemblea.convocata_il is None


def test_convocazione_parte_col_pdf_e_si_ferma(capogruppo, capo, genitore, estraneo, assemblea):
    _convocazione(assemblea, capogruppo)
    # Before it goes out only who sends it can see it.
    assert _client(genitore).get(_url(assemblea, "/convocazione.pdf")).status_code == 404
    mail.outbox.clear()
    assert _post(capogruppo, _url(assemblea, "/convocazione/invia")).status_code == 200
    allegati = [a[0] for a in mail.outbox[0].attachments]
    assert "convocazione-assemblea.pdf" in allegati
    risposta = _client(genitore).get(_url(assemblea, "/convocazione.pdf"))
    assert risposta.status_code == 200 and risposta.content.startswith(b"%PDF")
    assert _client(estraneo).get(_url(assemblea, "/convocazione.pdf")).status_code == 404
    assert _convocazione(assemblea, capogruppo).status_code == 400


def test_solo_chi_convoca_compila(capo, genitore, estraneo, assemblea):
    for chi in (capo, genitore, estraneo):
        assert _convocazione(assemblea, chi).status_code == 403
    assert _client(estraneo).get(_url(assemblea, "/convocazione/modello")).status_code == 404


def test_punto_sconosciuto(capogruppo, assemblea):
    assert _convocazione(assemblea, capogruppo, punti=("ALTRO",)).status_code == 400


def test_riunione_senza_modello(capogruppo, coca):
    inizio = timezone.now() - timedelta(days=1)
    evento = Evento.objects.create(
        titolo="Co.Ca.", tipo="RIUNIONE", livello="UNITA", inizio=inizio, fine=inizio
    )
    evento.unita.set([coca])
    assert _client(capogruppo).get(_url(evento, "/convocazione/modello")).status_code == 404


# --- Minutes of the assembly ----------------------------------------------------------------


def test_testo_a_mano_rifiutato(capogruppo, assemblea):
    risposta = _put(capogruppo, _url(assemblea, "/verbale"), {"testo": "<p>x</p>"})
    assert risposta.status_code == 400
    assert _client(capogruppo).get(_url(assemblea, "/verbale")).json()["da_modello"] is True


def test_verbale_gia_scritto_resta_com_e(capogruppo, assemblea):
    Verbale.objects.create(evento=assemblea, testo="<p>Scritto prima.</p>")
    assert _put(capogruppo, _url(assemblea, "/verbale"), {"testo": "<p>y</p>"}).status_code == 200
    assert _client(capogruppo).get(_url(assemblea, "/verbale")).json()["da_modello"] is False


def test_definitivo_elenca_cosa_manca(capogruppo, capo, assemblea):
    _convocazione(assemblea, capogruppo)
    _segna(assemblea, capo, capogruppo)
    _cariche(assemblea, capogruppo, capo, capogruppo)
    risposta = _post(capogruppo, _url(assemblea, "/verbale/definitivo"))
    assert risposta.status_code == 400
    assert "ora di apertura" in risposta.json()["detail"]
    assert "risultato di bilancio" in risposta.json()["detail"]
    _verbale_compilato(assemblea, capogruppo, capo)
    assert _post(capogruppo, _url(assemblea, "/verbale/definitivo")).status_code == 200
    verbale = Verbale.objects.get(evento=assemblea)
    assert "euro 150,50" in verbale.testo
    assert "con 10 voti favorevoli e 2 contrari, su 2 presenti" in verbale.testo
    assert "Lì Avellino" in verbale.testo
    # Once definitive the text is what was copied.
    Presenza.objects.filter(evento=assemblea).delete()
    letto = _client(capo).get(_url(assemblea, "/verbale?testo=true")).json()
    assert "su 2 presenti" in letto["testo"]


def test_unanimita_senza_numeri(capogruppo, capo, assemblea):
    _convocazione(assemblea, capogruppo)
    _segna(assemblea, capo)
    voti = {"BILANCIO": {"unanimita": True}}
    _verbale_compilato(assemblea, capogruppo, capo, voti=voti)
    testo = Verbale.objects.get(evento=assemblea)
    assert "all'unanimità dei 1 presenti" in modelli.testo_assemblea(testo)
    assert "voti favorevoli" not in modelli.testo_assemblea(testo)


def test_solo_i_punti_scelti(capogruppo, capo, assemblea):
    _convocazione(assemblea, capogruppo, punti=("REGOLAMENTO",))
    _segna(assemblea, capo)
    _verbale_compilato(assemblea, capogruppo, capo)
    testo = modelli.testo_assemblea(Verbale.objects.get(evento=assemblea))
    assert "proposta di Regolamento" in testo
    assert "bilancio" not in testo
    assert "quota associativa" not in testo


def test_elezione_elenca_capi_e_assistenti(capogruppo, capo, coca, assemblea):
    assistente = crea_capo("Don", "Paolo", "don@example.invalid")
    Incarico.objects.create(
        persona=assistente, ruolo=RuoloIncarico.AE_GRUPPO, data_inizio=INIZIO_ANNO
    )
    _convocazione(assemblea, capogruppo, punti=("ELEZIONE",), anno_elezione=2027)
    _segna(assemblea, capo)
    verbale = Verbale.objects.get(evento=assemblea)
    testo = modelli.testo_assemblea(verbale)
    for persona in (capo, capogruppo, assistente):
        assert f"{persona.nome} {persona.cognome}" in testo


def test_scrutatori_solo_tra_i_presenti(capogruppo, capo, estraneo, assemblea):
    _segna(assemblea, capo)
    corpo = {"scrutatori": [estraneo.pk]}
    assert _put(capogruppo, _url(assemblea, "/verbale/modello"), corpo).status_code == 400


def test_html_nei_dati_non_passa(capogruppo, capo, assemblea):
    _convocazione(assemblea, capogruppo, punti=("VARIE",))
    _segna(assemblea, capo)
    _verbale_compilato(assemblea, capogruppo, capo, varie="<script>x</script>")
    testo = modelli.testo_assemblea(Verbale.objects.get(evento=assemblea))
    assert "<script>" not in testo and "&lt;script&gt;" in testo


def test_dati_fuori_dal_registro(capogruppo, capo, assemblea):
    _convocazione(assemblea, capogruppo)
    verbale = Verbale.objects.get(evento=assemblea)
    voci = {k for e in LogEntry.objects.get_for_object(verbale) for k in (e.changes or {})}
    assert "dati" not in voci


# --- Separate minutes of the budget ---------------------------------------------------------


def _pronta_col_bilancio(assemblea, capogruppo, capo):
    _convocazione(assemblea, capogruppo)
    _segna(assemblea, capo, capogruppo)
    _cariche(assemblea, capogruppo, capo, capogruppo)
    _verbale_compilato(assemblea, capogruppo, capo, bilancio_separato=True)


def test_bilancio_separato_a_scelta(capogruppo, capo, assemblea):
    _pronta_col_bilancio(assemblea, capogruppo, capo)
    assert VerbaleCollegato.objects.filter(evento=assemblea, tipo="BILANCIO").exists()
    _verbale_compilato(assemblea, capogruppo, capo, bilancio_separato=False)
    assert not VerbaleCollegato.objects.filter(evento=assemblea).exists()


def test_bilancio_separato_stessi_dati_stato_proprio(
    capogruppo, capo, genitore, estraneo, assemblea
):
    _pronta_col_bilancio(assemblea, capogruppo, capo)
    url = _url(assemblea, "/verbali-collegati/BILANCIO")
    # Still a draft: only who manages it.
    assert _client(capo).get(url).status_code == 404
    assert _client(capogruppo).get(url).json()["mancanti"] == []
    assert _client(capo).get(url + ".pdf").status_code == 404
    assert _post(capo, url + "/definitivo").status_code == 404
    assert _post(capogruppo, url + "/definitivo").status_code == 200
    assert Verbale.objects.get(evento=assemblea).definitivo is False
    collegato = VerbaleCollegato.objects.get(evento=assemblea)
    assert "euro 150,50" in collegato.testo
    assert "in persona di" in collegato.testo
    capigruppo = collegato.firme[1]["righe"]
    assert any(capogruppo.cognome in riga for riga in capigruppo)
    risposta = _client(capo).get(url + ".pdf")
    assert risposta.status_code == 200 and risposta.content.startswith(b"%PDF")
    # Readers of the assembly's minutes: the invited, nobody else.
    assert _client(genitore).get(url).status_code == 200
    assert _client(estraneo).get(url).status_code == 404
    assert _post(capogruppo, url + "/riapri", {"motivo": ""}).status_code == 400
    assert _post(capogruppo, url + "/riapri", {"motivo": "Refuso"}).status_code == 200
    assert _client(capo).get(url).status_code == 404


def test_bilancio_non_in_ordine_del_giorno(capogruppo, capo, assemblea):
    _convocazione(assemblea, capogruppo, punti=("VARIE",))
    _segna(assemblea, capo)
    _verbale_compilato(assemblea, capogruppo, capo, bilancio_separato=True)
    url = _url(assemblea, "/verbali-collegati/BILANCIO/definitivo")
    risposta = _post(capogruppo, url)
    assert risposta.status_code == 400
    assert "ordine del giorno" in risposta.json()["detail"]


# --- Minutes of the Co.Ca. on Capi Gruppo, representative, seat -----------------------------


@pytest.fixture
def di_coca(coca) -> Evento:
    inizio = timezone.now() - timedelta(days=1)
    evento = Evento.objects.create(
        titolo="Co.Ca.", tipo="RIUNIONE", livello="UNITA", inizio=inizio, fine=inizio
    )
    evento.unita.set([coca])
    return evento


CAPI_GRUPPO = "/verbali-collegati/CAPI_GRUPPO"


def _capi_gruppo(evento, chi, **parti):
    corpo = {"ora_apertura": "21:00", "ora_chiusura": "22:30", "luogo": LUOGO, **parti}
    return _put(chi, _url(evento, CAPI_GRUPPO), corpo)


def test_si_produce_solo_quando_serve(capogruppo, di_coca):
    assert not VerbaleCollegato.objects.exists()
    elenco = _client(capogruppo).get(_url(di_coca, "/verbali-collegati")).json()
    assert elenco["collegati"] == []
    assert elenco["da_aggiungere"] == ["CAPI_GRUPPO"]
    risposta = _capi_gruppo(di_coca, capogruppo)
    assert any("almeno una parte" in m for m in risposta.json()["mancanti"])
    assert _client(capogruppo).delete(_url(di_coca, CAPI_GRUPPO)).status_code == 204
    assert not VerbaleCollegato.objects.exists()


def test_solo_la_parte_cambiata(capogruppo, di_coca):
    sede = {
        "via": "Via Nuova",
        "civico": "9",
        "cap": "83100",
        "citta": "Avellino",
        "provincia": "AV",
    }
    testo = _capi_gruppo(di_coca, capogruppo, cambia_sede=True, sede=sede).json()["testo"]
    assert "nuova sede legale" in testo and "Via Nuova" in testo
    assert "esprime nei ruoli" not in testo
    assert "Rappresentante legale" not in testo
    assert "espressione dei Capi Gruppo" not in testo
    # The first part in the text has no «inoltre».
    assert "inoltre" not in testo


def test_rappresentante_tra_i_capi_gruppo_con_dati_dalla_scheda(capogruppo, capo, di_coca):
    risposta = _capi_gruppo(
        di_coca, capogruppo, cambia_rappresentante=True, rappresentante=capo.pk
    ).json()
    assert any("va scelto tra i Capi Gruppo" in m for m in risposta["mancanti"])
    Persona.objects.filter(pk=capo.pk).update(codice_fiscale=None, luogo_nascita="")
    risposta = _capi_gruppo(
        di_coca,
        capogruppo,
        cambia_capi_gruppo=True,
        capi_gruppo=[capo.pk],
        cambia_rappresentante=True,
        rappresentante=capo.pk,
    ).json()
    assert any(f"{capo.nome} {capo.cognome}: codice fiscale" == m for m in risposta["mancanti"])
    _scheda_completa(capo, "F")
    capo.refresh_from_db()
    risposta = _capi_gruppo(
        di_coca,
        capogruppo,
        cambia_capi_gruppo=True,
        capi_gruppo=[capo.pk],
        cambia_rappresentante=True,
        rappresentante=capo.pk,
    ).json()
    assert risposta["mancanti"] == []
    testo = risposta["testo"]
    assert f"Sig.ra {capo.cognome} {capo.nome}" in testo
    assert "nata a Avellino (AV) il 02/05/1980" in testo
    assert "83100 Avellino (AV)" in testo
    assert "artt. 26 e 30" in testo
    assert "inoltre nomina, tra i Capi Gruppo, la Sig.ra" in testo


def test_chi_compila_e_chi_legge(capogruppo, capo, genitore, estraneo, di_coca):
    sede = {
        "via": "Via Nuova",
        "civico": "9",
        "cap": "83100",
        "citta": "Avellino",
        "provincia": "AV",
    }
    assert _capi_gruppo(di_coca, capo, cambia_sede=True, sede=sede).status_code == 403
    assert _capi_gruppo(di_coca, capogruppo, cambia_sede=True, sede=sede).status_code == 200
    url = _url(di_coca, CAPI_GRUPPO)
    # In draft it carries personal data: not even the other capi.
    assert _client(capo).get(url).status_code == 404
    _segna(di_coca, capo, capogruppo)
    assert _post(capogruppo, url + "/definitivo").status_code == 200
    # Definitive: every capo, reads logged; no family, nobody outside.
    AccessoDatoSensibile.objects.all().delete()
    assert _client(capo).get(url).status_code == 200
    assert AccessoDatoSensibile.objects.filter(utente=capo.utente).count() == 1
    assert (
        _client(capo).get(_url(di_coca, "/verbali-collegati")).json()["collegati"][0]["testo"] == ""
    )
    assert AccessoDatoSensibile.objects.filter(utente=capo.utente).count() == 1
    for chi in (genitore, estraneo):
        assert _client(chi).get(url).status_code == 404
    risposta = _client(capo).get(url + ".pdf")
    assert risposta.status_code == 200 and risposta.content.startswith(b"%PDF")


def test_nulla_cambia_da_solo(capogruppo, capo, gruppo, di_coca):
    _scheda_completa(capo)
    sede = {
        "via": "Via Nuova",
        "civico": "9",
        "cap": "83100",
        "citta": "Avellino",
        "provincia": "AV",
    }
    prima = (Incarico.objects.count(), gruppo.sede_indirizzo, gruppo.rappresentante_legale)
    _capi_gruppo(
        di_coca,
        capogruppo,
        cambia_capi_gruppo=True,
        capi_gruppo=[capo.pk],
        cambia_rappresentante=True,
        rappresentante=capo.pk,
        cambia_sede=True,
        sede=sede,
    )
    _segna(di_coca, capo)
    assert _post(capogruppo, _url(di_coca, CAPI_GRUPPO + "/definitivo")).status_code == 200
    gruppo.refresh_from_db()
    assert prima == (Incarico.objects.count(), gruppo.sede_indirizzo, gruppo.rappresentante_legale)


def test_copia_dei_dati_e_firme_nel_definitivo(capogruppo, capo, di_coca):
    _scheda_completa(capo)
    _capi_gruppo(di_coca, capogruppo, cambia_capi_gruppo=True, capi_gruppo=[capo.pk])
    _segna(di_coca, capo, capogruppo)
    assert _post(capogruppo, _url(di_coca, CAPI_GRUPPO + "/definitivo")).status_code == 200
    Persona.objects.filter(pk=capo.pk).update(comune="Salerno")
    collegato = VerbaleCollegato.objects.get(evento=di_coca)
    assert "Salerno" not in servizi.testo_collegato(collegato)
    assert collegato.firme[0]["intro"] == "Firme dei presenti"
    assert len(collegato.firme[0]["righe"]) == 2


def test_fuori_dal_registro(capogruppo, capo, di_coca):
    _scheda_completa(capo)
    _capi_gruppo(di_coca, capogruppo, cambia_capi_gruppo=True, capi_gruppo=[capo.pk])
    collegato = VerbaleCollegato.objects.get(evento=di_coca)
    voci = {k for e in LogEntry.objects.get_for_object(collegato) for k in (e.changes or {})}
    assert not voci & {"dati", "testo", "firme"}


def test_cancellazione(capogruppo, capo, di_coca):
    _scheda_completa(capo)
    _capi_gruppo(
        di_coca,
        capogruppo,
        cambia_capi_gruppo=True,
        capi_gruppo=[capo.pk],
        cambia_rappresentante=True,
        rappresentante=capo.pk,
    )
    assert f"{capo.cognome} {capo.nome}" in str(
        servizi.testo_collegato(VerbaleCollegato.objects.get(evento=di_coca))
    )
    servizi.alla_cancellazione(capo)
    collegato = VerbaleCollegato.objects.get(evento=di_coca)
    assert collegato.dati["capi_gruppo"] == []
    assert collegato.dati["rappresentante"] is None
    # What is definitive is text: it is signalled to the capogruppo.
    _scheda_completa(capo)
    _capi_gruppo(di_coca, capogruppo, cambia_capi_gruppo=True, capi_gruppo=[capo.pk])
    _segna(di_coca, capo)
    assert _post(capogruppo, _url(di_coca, CAPI_GRUPPO + "/definitivo")).status_code == 200
    Verbale.objects.get_or_create(evento=di_coca)
    assert [v.evento_id for v in servizi.verbali_col_nome(capo)] == [di_coca.pk]


def test_tipo_di_un_altra_riunione(capogruppo, assemblea):
    risposta = _put(capogruppo, _url(assemblea, CAPI_GRUPPO), {})
    assert risposta.status_code == 404
