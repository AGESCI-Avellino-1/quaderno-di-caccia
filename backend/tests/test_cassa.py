"""Cash book: boxes, movements, reversals, cash checks, refunds, fee payments,
Modello D totals (DEC-11, DEC-85…DEC-88).

Movements are dated in the past year 2025/26 (memberships start on 1 October 2025).
"""

import base64
from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.test import Client

from apps.accounts.models import User
from apps.anagrafica.models import Appartenenza, RuoloAppartenenza
from apps.cassa import servizi
from apps.cassa.catalogo import catalogo, voce_quota, voce_rimborsi
from apps.cassa.models import Cassa, Movimento, SpesaAnticipata, TipoCassa, TipoMovimento
from apps.core.anno import AnnoAssociativo
from apps.organizzazione.models import Composizione, Incarico, RuoloIncarico, TipoUnita, Unita
from apps.quote import servizi as quote
from apps.quote.models import CategoriaQuota, Destinatari, MetodoPagamento, Quota, TipoQuota
from tests.conftest import INIZIO_ANNO, crea_capo, crea_persona, nato_anni_fa

pytestmark = pytest.mark.django_db

ANNO = AnnoAssociativo(2026)
GENNAIO = date(2026, 1, 15)
SPESA = catalogo().cerca("U", "A.1").id  # materials
JPEG = "data:image/jpeg;base64," + base64.b64encode(b"\xff\xd8\xff\xe0" + b"0" * 20).decode()


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi if isinstance(chi, User) else chi.utente)
    return client


def _post(chi, url, dati=None):
    return _client(chi).post(url, dati or {}, content_type="application/json")


@pytest.fixture
def banca(gruppo):
    return Cassa.objects.create(
        nome="Conto bancario",
        tipo=TipoCassa.BANCA,
        saldo_iniziale=Decimal("1000"),
        data_saldo_iniziale=INIZIO_ANNO,
    )


@pytest.fixture
def contanti(reparto):
    return Cassa.objects.create(
        nome="Contanti reparto",
        tipo=TipoCassa.CONTANTI,
        unita=reparto,
        saldo_iniziale=Decimal("50"),
        data_saldo_iniziale=INIZIO_ANNO,
    )


@pytest.fixture
def clan(gruppo):
    return Unita.objects.create(
        gruppo=gruppo, nome="Hirpinia", tipo=TipoUnita.CLAN_FUOCO, composizione=Composizione.MISTA
    )


@pytest.fixture
def contanti_clan(clan):
    return Cassa.objects.create(
        nome="Contanti clan",
        tipo=TipoCassa.CONTANTI,
        unita=clan,
        data_saldo_iniziale=INIZIO_ANNO,
    )


@pytest.fixture
def tesoriere_rs(clan):
    persona = crea_persona("Rita", "Rover", "rita@example.invalid", data_nascita=nato_anni_fa(19))
    Appartenenza.objects.create(
        persona=persona, unita=clan, ruolo=RuoloAppartenenza.RAGAZZO, data_inizio=INIZIO_ANNO
    )
    Incarico.objects.create(
        persona=persona, ruolo=RuoloIncarico.TESORIERE_UNITA, unita=clan, data_inizio=INIZIO_ANNO
    )
    return persona


@pytest.fixture
def staff(reparto, coca):
    persona = crea_capo("Elena", "Staff", "staff@example.invalid")
    Incarico.objects.create(
        persona=persona, ruolo=RuoloIncarico.STAFF, unita=reparto, data_inizio=INIZIO_ANNO
    )
    return persona


def _uscita(cassa, importo="20", utente=None, **campi):
    return servizi.registra(
        cassa=cassa,
        tipo=TipoMovimento.USCITA,
        data=campi.pop("data", GENNAIO),
        importo=Decimal(importo),
        descrizione=campi.pop("descrizione", "Cancelleria"),
        voce_id=campi.pop("voce_id", SPESA),
        utente=utente,
        **campi,
    )


# --- Catalog -----------------------------------------------------------------------------------


def test_catalogo_voci_scout_o_ministeriali():
    voci = catalogo().voci
    assert not any(v.riga == "A.5" and v.lato == "E" for v in voci)  # 5x1000: grey
    assert not any(v.riga == "A.4" and v.lato == "U" for v in voci)  # staff: grey
    assert voce_quota("MENSILE").riga == "A.2"
    assert voce_rimborsi().nome == "Rimborsi spese volontari"


# --- Movements and balances --------------------------------------------------------------------


def test_saldi_con_uscite_giroconti_e_storni(banca, contanti, capogruppo, reparto):
    _uscita(contanti, "20")
    servizi.registra(
        cassa=banca,
        tipo=TipoMovimento.GIROCONTO,
        data=GENNAIO,
        importo=Decimal("100"),
        descrizione="Prelievo per la cassa del reparto",
        cassa_destinazione=contanti,
        unita=reparto,
        utente=capogruppo.utente,
    )
    assert contanti.saldo() == Decimal("130")
    assert banca.saldo() == Decimal("900")
    sbagliata = _uscita(contanti, "15")
    servizi.storna(sbagliata, capogruppo.utente, "Importo sbagliato")
    assert contanti.saldo() == Decimal("130")
    with pytest.raises(ValidationError, match="già stornato"):
        servizi.storna(sbagliata, capogruppo.utente, "Di nuovo")
    with pytest.raises(ValidationError, match="motivo"):
        servizi.storna(_uscita(contanti, "1"), capogruppo.utente, " ")


def test_regole_dei_movimenti(banca, contanti, reparto):
    with pytest.raises(ValidationError, match="voce"):
        _uscita(contanti, voce_id=voce_quota("GRUPPO").id)  # an income category
    with pytest.raises(ValidationError, match="futuro"):
        _uscita(contanti, data=date(2999, 1, 1))
    with pytest.raises(ValidationError, match="saldo iniziale"):
        _uscita(contanti, data=date(2025, 9, 1))
    with pytest.raises(ValidationError, match="positivo"):
        _uscita(contanti, "-5")
    cassa = Cassa(nome="X", tipo=TipoCassa.BANCA, unita=reparto, data_saldo_iniziale=INIZIO_ANNO)
    with pytest.raises(ValidationError, match="unità si indicano sui movimenti"):
        cassa.full_clean()


def test_contanti_sempre_dell_unita_della_cassa(contanti, clan):
    movimento = _uscita(contanti, unita=clan)
    assert movimento.unita == contanti.unita


def test_uscita_senza_giustificativo_segnalata(contanti):
    senza = _uscita(contanti)
    con = _uscita(contanti, giustificativo=servizi.giustificativo_da_testo(JPEG))
    assert senza.senza_giustificativo and not con.senza_giustificativo
    assert con.giustificativo.name.endswith(".jpg")
    with pytest.raises(ValidationError, match="foto"):
        servizi.giustificativo_da_testo(base64.b64encode(b"<html>").decode())


def test_verifica_con_differenza_registra_la_rettifica(contanti, capo):
    _uscita(contanti, "20")
    with pytest.raises(ValidationError, match="differisce di -5,00 €"):
        servizi.verifica(
            contanti, data=GENNAIO, saldo_contato=Decimal("25"), motivo="", utente=capo.utente
        )
    esito = servizi.verifica(
        contanti,
        data=GENNAIO,
        saldo_contato=Decimal("25"),
        motivo="Resto sbagliato",
        utente=capo.utente,
    )
    assert esito.saldo_app == Decimal("30") and esito.differenza == Decimal("-5")
    assert esito.rettifica.tipo == TipoMovimento.RETTIFICA
    with pytest.raises(ValidationError, match="nuova verifica"):
        servizi.storna(esito.rettifica, capo.utente, "Errore")
    assert contanti.saldo() == Decimal("25")
    pari = servizi.verifica(
        contanti, data=GENNAIO, saldo_contato=Decimal("25"), motivo="", utente=capo.utente
    )
    assert pari.rettifica is None


# --- Refunds to capi (DEC-86) ------------------------------------------------------------------


def test_spesa_anticipata_diventa_uscita_al_rimborso(contanti, staff, capo, reparto):
    spesa = SpesaAnticipata.objects.create(
        capo=staff, data=GENNAIO, importo=Decimal("12.50"), descrizione="Corde", unita=reparto
    )
    assert contanti.saldo() == Decimal("50")  # nothing yet
    movimento = servizi.rimborsa(spesa, contanti, capo.utente, GENNAIO)
    assert movimento.voce_nome == "Rimborsi spese volontari"
    assert contanti.saldo() == Decimal("37.50")
    with pytest.raises(ValidationError, match="già stata rimborsata"):
        servizi.rimborsa(spesa, contanti, capo.utente, GENNAIO)


# --- Fee payments enter by themselves ----------------------------------------------------------


@pytest.fixture
def quote_ragazza(reparto, ragazza):
    censimento = TipoQuota.objects.create(
        nome="Censimento",
        categoria=CategoriaQuota.CENSIMENTO,
        anno=2026,
        importo=Decimal("40"),
        destinatari=Destinatari.TUTTI,
        scadenza=date(2025, 11, 30),
    )
    mensile = TipoQuota.objects.create(
        nome="Mensile",
        categoria=CategoriaQuota.MENSILE,
        anno=2026,
        importo=Decimal("10"),
        destinatari=Destinatari.RAGAZZI,
        mesi=[10],
        giorno_scadenza=10,
    )
    quote.emetti(censimento, oggi=GENNAIO)
    quote.emetti(mensile, oggi=GENNAIO)
    return Quota.objects.get(tipo=censimento, persona=ragazza), Quota.objects.get(
        tipo=mensile, persona=ragazza
    )


def _paga(righe, metodo, utente, **campi):
    return quote.registra_pagamento(
        data=GENNAIO,
        metodo=metodo,
        versato_da="Mario Genitore",
        righe=[quote.Riga(q, Decimal(i)) for q, i in righe],
        utente=utente,
        **campi,
    )


def test_pagamento_in_contanti_nella_cassa_dell_unita_per_voce(
    quote_ragazza, banca, contanti, staff, reparto
):
    censimento, mensile = quote_ragazza
    pagamento = _paga([(censimento, "40"), (mensile, "10")], MetodoPagamento.CONTANTI, staff.utente)
    movimenti = {m.voce_id: m for m in pagamento.movimenti.all()}
    assert set(movimenti) == {voce_quota("CENSIMENTO").id, voce_quota("MENSILE").id}
    assert all(m.cassa == contanti and m.unita == reparto for m in movimenti.values())
    assert contanti.saldo() == Decimal("100")
    quote.annulla_pagamento(pagamento, staff.utente, "Errore")
    assert contanti.saldo() == Decimal("50")
    assert Movimento.objects.filter(storno_di__isnull=False).count() == 2


def test_bonifico_nel_conto_e_cassa_scelta(quote_ragazza, banca, contanti, staff):
    censimento, mensile = quote_ragazza
    _paga([(censimento, "40")], MetodoPagamento.BONIFICO, staff.utente)
    assert banca.saldo() == Decimal("1040")
    _paga([(mensile, "10")], MetodoPagamento.CONTANTI, staff.utente, cassa=banca)
    assert banca.saldo() == Decimal("1050")


def test_modello_d(quote_ragazza, banca, contanti, staff, capo):
    censimento, _ = quote_ragazza
    _paga([(censimento, "40")], MetodoPagamento.BONIFICO, staff.utente)
    _uscita(contanti, "20")
    servizi.verifica(
        contanti, data=GENNAIO, saldo_contato=Decimal("29"), motivo="Ammanco", utente=capo.utente
    )
    totali = servizi.modello_d(ANNO)
    righe = {(r["lato"], r["riga"]): r["totale"] for r in totali["righe"]}
    assert righe[("E", "A.1")] == Decimal("40")
    assert righe[("U", "A.1")] == Decimal("20")
    assert totali["entrate"] == Decimal("40") and totali["uscite"] == Decimal("20")
    assert totali["rettifiche"] == Decimal("-1")


# --- Who sees and does what ------------------------------------------------------------------


def test_chi_registra_e_chi_vede(
    banca, contanti, contanti_clan, capo, capogruppo, staff, tesoriere_rs, ragazza, clan, reparto
):
    from apps.permessi import policy

    assert policy.puo_registrare_in_cassa(capo.utente, contanti)  # capo unità
    assert not policy.puo_registrare_in_cassa(staff.utente, contanti)
    assert policy.puo_registrare_in_cassa(tesoriere_rs.utente, contanti_clan)
    assert not policy.puo_registrare_in_cassa(tesoriere_rs.utente, contanti)
    assert policy.puo_registrare_in_cassa(capogruppo.utente, contanti_clan)
    assert policy.puo_registrare_in_cassa(capo.utente, banca)  # for the reparto only
    assert policy.puo_registrare_movimenti(capo.utente, reparto.pk)
    assert not policy.puo_registrare_movimenti(capo.utente, clan.pk)
    assert not policy.puo_registrare_movimenti(capo.utente, None)  # group movements
    assert policy.unita_cassa_visibili(staff.utente) is None  # the Co.Ca. sees all
    assert policy.unita_cassa_visibili(tesoriere_rs.utente) == {clan.pk}
    assert not policy.puo_vedere_cassa(ragazza.utente)


def test_api_movimento_offline_con_foto_e_visibilita(
    banca, contanti, contanti_clan, capo, tesoriere_rs, ragazza, reparto, clan
):
    corpo = {
        "cassa_id": banca.pk,
        "tipo": "USCITA",
        "data": "2026-01-15",
        "importo": "30.00",
        "descrizione": "Benzina uscita",
        "voce_id": catalogo().cerca("U", "A.2").id,
        "unita_id": reparto.pk,
        "giustificativo": JPEG,
    }
    risposta = _post(capo, "/api/v1/movimenti", corpo)
    assert risposta.status_code == 201, risposta.content
    movimento = risposta.json()
    assert movimento["ha_giustificativo"] and not movimento["senza_giustificativo"]
    assert _post(capo, "/api/v1/movimenti", {**corpo, "unita_id": clan.pk}).status_code == 403
    assert _post(ragazza, "/api/v1/movimenti", corpo).status_code == 403

    _uscita(contanti_clan, "5", descrizione="Spesa clan")
    del_rs = _client(tesoriere_rs).get("/api/v1/movimenti?anno=2026").json()
    assert [m["descrizione"] for m in del_rs] == ["Spesa clan"]
    casse = {c["nome"]: c for c in _client(tesoriere_rs).get("/api/v1/casse").json()}
    assert casse["Conto bancario"]["saldo"] is None  # the shared account's balance
    assert casse["Contanti clan"]["saldo"] == "-5.00"
    assert "Contanti reparto" not in casse
    assert _client(tesoriere_rs).get("/api/v1/modello-d?anno=2026").status_code == 403

    foto = _client(capo).get(f"/api/v1/movimenti/{movimento['id']}/giustificativo")
    assert foto.status_code == 200
    vietata = _client(tesoriere_rs).get(f"/api/v1/movimenti/{movimento['id']}/giustificativo")
    assert vietata.status_code == 404


def test_api_storno_di_un_incasso_di_quote_no(quote_ragazza, banca, staff, capogruppo):
    censimento, _ = quote_ragazza
    pagamento = _paga([(censimento, "40")], MetodoPagamento.BONIFICO, staff.utente)
    movimento = pagamento.movimenti.get()
    risposta = _post(capogruppo, f"/api/v1/movimenti/{movimento.pk}/storno", {"motivo": "x"})
    assert risposta.status_code == 400
    assert "annulla il pagamento" in risposta.json()["detail"]


def test_api_spese_anticipate(contanti, staff, capo, reparto):
    risposta = _post(
        staff,
        "/api/v1/spese-anticipate",
        {"data": "2026-01-15", "importo": "8.00", "descrizione": "Nastro", "unita_id": reparto.pk},
    )
    assert risposta.status_code == 201, risposta.content
    spesa = risposta.json()
    assert spesa["stato"] == "da_rimborsare" and not spesa["puo_rimborsare"]
    da_capo = _client(capo).get("/api/v1/spese-anticipate").json()
    assert da_capo[0]["puo_rimborsare"]
    fatto = _post(
        capo, f"/api/v1/spese-anticipate/{spesa['id']}/rimborsa", {"cassa_id": contanti.pk}
    )
    assert fatto.json()["stato"] == "rimborsata"
    assert contanti.saldo() == Decimal("42")
