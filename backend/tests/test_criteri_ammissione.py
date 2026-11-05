"""The admission criteria of the year (DEC-355...DEC-359)."""

import json
from datetime import date, timedelta
from io import StringIO
from unittest import mock

import pytest
from django.core import mail
from django.core.management import call_command
from django.test import Client
from django.utils import timezone

from apps.core.anno import AnnoAssociativo
from apps.documenti import criteri
from apps.documenti.models import MassimoUnita, VersioneCriteri
from apps.iscrizioni.models import RichiestaIscrizione, StatoIscrizione
from apps.permessi import policy
from tests.conftest import crea_persona

pytestmark = pytest.mark.django_db

GESTIONE = "/api/v1/criteri-ammissione"
PUBBLICI = "/api/v1/criteri-ammissione/pubblici"


def _oggi(giorno: date):
    return mock.patch("django.utils.timezone.localdate", return_value=giorno)


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


def _post(chi, dati):
    return _client(chi).post(GESTIONE, json.dumps(dati), content_type="application/json")


def _anno() -> AnnoAssociativo:
    return AnnoAssociativo.corrente()


def _versione(anno=None, dal=None, **campi) -> VersioneCriteri:
    anno = anno or _anno()
    return VersioneCriteri.objects.create(
        anno=anno.anno_fine,
        valida_dal=dal or anno.inizio,
        verbale_numero="3",
        verbale_data=anno.inizio,
        testo=campi.pop("testo", "<p>Testo dei criteri</p>"),
        **campi,
    )


def _dati(**campi) -> dict:
    anno = _anno()
    return {
        "anno": anno.anno_fine,
        "valida_dal": anno.inizio.isoformat(),
        "verbale_numero": "3",
        "verbale_data": anno.inizio.isoformat(),
        "testo": "<p>Testo</p>",
        "massimi": [],
    } | campi


def _richiesta(unita, **campi) -> RichiestaIscrizione:
    return RichiestaIscrizione.objects.create(
        unita=unita,
        nome="Nuova",
        cognome="Richiesta",
        data_nascita=date(2014, 3, 3),
        **campi,
    )


# --- Who writes (DEC-355) -------------------------------------------------------------------


def test_compila_solo_il_capogruppo(capo, capogruppo, csq, ragazza, genitore, estraneo):
    assert policy.puo_gestire_criteri(capogruppo.utente)
    for chi in (capo, csq, ragazza, genitore, estraneo):
        assert not policy.puo_gestire_criteri(chi.utente)
        assert _post(chi, _dati()).status_code == 403
        assert _client(chi).get(GESTIONE).status_code == 403
    assert _post(capogruppo, _dati()).status_code == 201


def test_chi_non_e_capogruppo_non_cancella_ne_scarica_le_future(capo, capogruppo):
    futura = _versione(dal=_anno().fine)
    assert _client(capo).delete(f"{GESTIONE}/{futura.pk}").status_code == 403
    assert _client(capo).get(f"{GESTIONE}/{futura.pk}.pdf").status_code == 403
    assert _client(capogruppo).get(f"{GESTIONE}/{futura.pk}.pdf").status_code == 200
    assert _client(capogruppo).delete(f"{GESTIONE}/{futura.pk}").status_code == 204


def test_si_parte_dal_modello(capogruppo):
    dati = _client(capogruppo).get(GESTIONE).json()
    assert "Nessuna richiesta viene esclusa per disabilità" in dati["testo"]
    assert [a["valore"] for a in dati["anni"]] == [_anno().anno_fine, _anno().anno_fine + 1]


def test_poi_si_parte_dall_ultima(capogruppo, reparto):
    versione = _versione(testo="<p>Il nostro testo</p>")
    MassimoUnita.objects.create(versione=versione, unita=reparto, massimo=30)
    dati = _client(capogruppo).get(GESTIONE).json()
    assert dati["testo"] == "<p>Il nostro testo</p>"
    assert dati["massimi"] == [{"unita_id": reparto.pk, "massimo": 30}]


def test_il_testo_viene_ripulito(capogruppo):
    risposta = _post(capogruppo, _dati(testo='<p onclick="x()">Testo<script>alert(1)</script></p>'))
    assert risposta.status_code == 201
    testo = VersioneCriteri.objects.get().testo
    assert "script" not in testo and "onclick" not in testo


@pytest.mark.parametrize(
    ("cambio", "parola"),
    [
        ({"testo": "  "}, "testo"),
        ({"testo": "<script>alert(1)</script>"}, "testo"),
        ({"verbale_numero": " "}, ""),
    ],
)
def test_dati_mancanti(capogruppo, cambio, parola):
    risposta = _post(capogruppo, _dati(**cambio))
    assert risposta.status_code == 400
    assert parola in risposta.json()["detail"]


def test_la_data_deve_stare_nell_anno(capogruppo):
    fuori = (_anno().inizio - timedelta(days=1)).isoformat()
    risposta = _post(capogruppo, _dati(valida_dal=fuori))
    assert risposta.status_code == 400
    assert "nell'anno" in risposta.json()["detail"]


def test_due_versioni_lo_stesso_giorno_no(capogruppo):
    assert _post(capogruppo, _dati()).status_code == 201
    assert _post(capogruppo, _dati()).status_code == 400


def test_solo_l_anno_in_corso_o_il_successivo(capogruppo):
    passato = _anno().precedente()
    dati = _dati(anno=passato.anno_fine, valida_dal=passato.inizio.isoformat())
    assert _post(capogruppo, dati).status_code == 400
    prossimo = _anno().successivo()
    dati = _dati(anno=prossimo.anno_fine, valida_dal=prossimo.inizio.isoformat())
    assert _post(capogruppo, dati).status_code == 201


def test_massimi_controllati(capogruppo, reparto, coca):
    dati = _dati(massimi=[{"unita_id": reparto.pk, "massimo": 0}])
    assert _post(capogruppo, dati).status_code == 400
    dati = _dati(massimi=[{"unita_id": coca.pk, "massimo": 5}])
    assert _post(capogruppo, dati).status_code == 400
    assert not VersioneCriteri.objects.exists()
    dati = _dati(massimi=[{"unita_id": reparto.pk, "massimo": 30}])
    assert _post(capogruppo, dati).status_code == 201
    assert MassimoUnita.objects.get().massimo == 30


# --- Versions (DEC-356) ---------------------------------------------------------------------


def test_ogni_versione_vale_fino_alla_successiva():
    anno = _anno()
    prima = _versione(dal=anno.inizio)
    seconda = _versione(dal=anno.inizio + timedelta(days=30))
    assert criteri.valida_fino_al(prima) == anno.inizio + timedelta(days=29)
    assert criteri.valida_fino_al(seconda) == anno.fine


def test_quella_in_vigore():
    anno = _anno()
    prima = _versione(dal=anno.inizio)
    seconda = _versione(dal=anno.inizio + timedelta(days=30))
    assert criteri.in_vigore(anno.inizio + timedelta(days=29)) == prima
    assert criteri.in_vigore(anno.inizio + timedelta(days=30)) == seconda


def test_cancellata_torna_valida_la_precedente(capogruppo):
    anno = _anno()
    prima = _versione(dal=anno.inizio)
    seconda = _versione(dal=anno.inizio + timedelta(days=1))
    assert _client(capogruppo).delete(f"{GESTIONE}/{seconda.pk}").status_code == 204
    assert criteri.valida_fino_al(prima) == anno.fine


# --- Who reads (DEC-357) --------------------------------------------------------------------


def test_chiunque_legge_e_scarica_senza_account():
    versione = _versione()
    dati = Client().get(PUBBLICI).json()
    assert dati["traccia"] is False
    assert [v["id"] for v in dati["versioni"]] == [versione.pk]
    risposta = Client().get(f"{PUBBLICI}/{versione.pk}.pdf")
    assert risposta.status_code == 200
    assert risposta["Content-Type"] == "application/pdf"
    assert risposta.content.startswith(b"%PDF")
    assert "criteri-di-ammissione" in risposta["Content-Disposition"]


def test_anche_le_versioni_superate_dell_anno():
    anno = _anno()
    with _oggi(anno.inizio + timedelta(days=40)):
        _versione(dal=anno.inizio)
        _versione(dal=anno.inizio + timedelta(days=30))
        versioni = Client().get(PUBBLICI).json()["versioni"]
    assert [v["in_vigore"] for v in versioni] == [True, False]
    assert versioni[1]["valida_fino_al"] == (anno.inizio + timedelta(days=29)).isoformat()


def test_una_versione_futura_non_si_vede_prima_del_suo_giorno():
    anno = _anno()
    with _oggi(anno.inizio + timedelta(days=5)):
        _versione(dal=anno.inizio)
        futura = _versione(dal=anno.inizio + timedelta(days=30))
        assert len(Client().get(PUBBLICI).json()["versioni"]) == 1
        assert Client().get(f"{PUBBLICI}/{futura.pk}.pdf").status_code == 404
    with _oggi(anno.inizio + timedelta(days=30)):
        assert len(Client().get(PUBBLICI).json()["versioni"]) == 2


def test_quella_di_un_anno_vecchio_non_si_scarica_piu():
    vecchio = _anno().precedente()
    vecchia = _versione(anno=vecchio)
    _versione()
    assert Client().get(f"{PUBBLICI}/{vecchia.pk}.pdf").status_code == 404


def test_senza_quelli_dell_anno_l_ultimo_come_traccia():
    vecchio = _anno().precedente()
    versione = _versione(anno=vecchio)
    dati = Client().get(PUBBLICI).json()
    assert dati["traccia"] is True
    assert dati["anno_nome"] == vecchio.etichetta
    assert dati["anno_corrente_nome"] == _anno().etichetta
    assert [v["id"] for v in dati["versioni"]] == [versione.pk]
    assert dati["versioni"][0]["in_vigore"] is False
    assert Client().get(f"{PUBBLICI}/{versione.pk}.pdf").status_code == 200


def test_leggerli_non_consuma_il_limite_della_lista_d_attesa():
    """Ninja shares one count per address among AnonRateThrottles: not with these."""
    from django.core.cache import cache

    from apps.attesa.api import LIMITI

    cache.clear()
    client = Client()
    for _ in range(25):
        assert client.get(PUBBLICI).status_code == 200
    assert cache.get("throttle_anon_127.0.0.1", []) == []
    assert LIMITI[0].scope == "anon"
    cache.clear()


def test_senza_nessuno_non_c_e_niente():
    dati = Client().get(PUBBLICI).json()
    assert dati["versioni"] == [] and dati["traccia"] is False


def test_il_pdf_non_si_rompe_col_modello_e_i_massimi(reparto):
    versione = _versione(testo=criteri.MODELLO)
    MassimoUnita.objects.create(versione=versione, unita=reparto, massimo=30)
    assert criteri.pdf(versione).startswith(b"%PDF")


# --- Maximum per unit (DEC-358) -------------------------------------------------------------


def test_massimo_e_soci(reparto, ragazza):
    assert criteri.massimo_di(reparto) is None
    assert criteri.posti(reparto) == ""
    versione = _versione()
    MassimoUnita.objects.create(versione=versione, unita=reparto, massimo=30)
    assert criteri.massimo_di(reparto) == 30
    assert criteri.posti(reparto) == f"{criteri.soci_giovani(reparto)} su 30"
    assert criteri.soci_giovani(reparto) == 1


def test_avviso_a_chi_decide(reparto, capogruppo, ragazza):
    versione = _versione()
    MassimoUnita.objects.create(versione=versione, unita=reparto, massimo=1)
    _richiesta(reparto)
    [r] = _client(capogruppo).get("/api/v1/iscrizioni").json()
    assert r["posti"] == "1 su 1"
    assert r["al_completo"] is True


def test_oltre_il_massimo_si_puo_approvare_lo_stesso(reparto, capogruppo, ragazza):
    versione = _versione()
    MassimoUnita.objects.create(versione=versione, unita=reparto, massimo=1)
    famiglia = crea_persona("Pia", "Famiglia", "pia@example.invalid")
    richiesta = _richiesta(
        reparto,
        utente=famiglia.utente,
        codice_fiscale="NVURCH14C43A509X",
        genitore_nome="Pia",
        genitore_cognome="Famiglia",
        genitore_codice_fiscale="FMLPIA80A41A509Y",
    )
    scadenza = (timezone.localdate() + timedelta(days=30)).isoformat()
    risposta = _client(capogruppo).post(
        f"/api/v1/iscrizioni/{richiesta.pk}/approva",
        json.dumps({"scadenza_completamento": scadenza}),
        content_type="application/json",
    )
    assert risposta.status_code == 200, risposta.content


def test_la_famiglia_non_vede_posti_e_termine(reparto, genitore):
    richiesta = _richiesta(reparto, utente=genitore.utente)
    MassimoUnita.objects.create(versione=_versione(), unita=reparto, massimo=1)
    [mia] = _client(genitore).get("/api/v1/mie-iscrizioni").json()
    assert mia["id"] == richiesta.pk
    assert mia["posti"] == "" and mia["giorni_per_decidere"] is None


def test_nella_lista_d_attesa_dei_capi(reparto, capo):
    MassimoUnita.objects.create(versione=_versione(), unita=reparto, massimo=30)
    dati = _client(capo).get("/api/v1/attesa").json()
    assert dati["posti"][str(reparto.pk)] == "0 su 30"


# --- Sixty days (DEC-359) -------------------------------------------------------------------


def _dopo(richiesta, giorni: int) -> date:
    return timezone.localtime(richiesta.creato_il).date() + timedelta(days=giorni)


def _promemoria(oggi: date) -> None:
    call_command("promemoria_iscrizioni", oggi=oggi, stdout=StringIO())


def test_giorni_rimasti(reparto, capogruppo):
    richiesta = _richiesta(reparto)
    [r] = _client(capogruppo).get("/api/v1/iscrizioni").json()
    assert r["giorni_per_decidere"] == 60
    # Local time: in UTC the change of the clocks can move the local day, late in the evening.
    richiesta.creato_il = timezone.localtime() - timedelta(days=61)
    richiesta.save()
    [r] = _client(capogruppo).get("/api/v1/iscrizioni").json()
    assert r["giorni_per_decidere"] == -1


def test_promemoria_dieci_giorni_prima_una_volta(reparto, capogruppo):
    richiesta = _richiesta(reparto, segnalata_il=timezone.now())
    _promemoria(_dopo(richiesta, 49))
    assert mail.outbox == []
    _promemoria(_dopo(richiesta, 50))
    assert len(mail.outbox) == 1
    assert capogruppo.utente.email in mail.outbox[0].to
    assert _dopo(richiesta, 60).strftime("%d/%m/%Y") in mail.outbox[0].body
    _promemoria(_dopo(richiesta, 51))
    assert len(mail.outbox) == 1


def test_una_gia_scaduta_avvisa_una_volta(reparto, capogruppo):
    """A request older than the feature: the term is past, who decides is told once."""
    richiesta = _richiesta(reparto, segnalata_il=timezone.now())
    _promemoria(_dopo(richiesta, 90))
    assert len(mail.outbox) == 1


def test_una_decisa_non_avvisa(reparto, capogruppo):
    richiesta = _richiesta(reparto, segnalata_il=timezone.now(), stato=StatoIscrizione.RIFIUTATA)
    _promemoria(_dopo(richiesta, 55))
    assert mail.outbox == []


# --- Reminder of the year (DEC-355) ---------------------------------------------------------


def test_promemoria_il_primo_del_mese_finche_mancano(capogruppo, coca):
    primo = date(_anno().anno_fine, 1, 1)
    with _oggi(primo):
        call_command("promemoria_fine_anno", stdout=StringIO())
    assert any("criteri di ammissione" in m.body for m in mail.outbox)


def test_nessun_promemoria_se_ci_sono(capogruppo, coca):
    anno = _anno()
    _versione()
    with _oggi(date(anno.anno_fine, 1, 1)):
        call_command("promemoria_fine_anno", stdout=StringIO())
    assert not any("criteri di ammissione" in m.body for m in mail.outbox)
