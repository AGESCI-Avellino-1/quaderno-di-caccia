"""Fees, family discount, agevolazioni, payments and receipts (DEC-80…DEC-84, DEC-92).

The year under test is 2025/26 (anno 2026), with `oggi` passed explicitly: the
fixtures' memberships start on 1 October 2025.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.core import mail
from django.core.exceptions import ValidationError
from django.test import Client

from apps.accounts.models import User
from apps.anagrafica.models import (
    Appartenenza,
    RelazioneTutela,
    RuoloAppartenenza,
    VisibilitaGenitori,
)
from apps.organizzazione.models import Composizione, Incarico, RuoloIncarico, TipoUnita, Unita
from apps.permessi import policy
from apps.quote import servizi
from apps.quote.models import (
    Agevolazione,
    CategoriaQuota,
    Destinatari,
    LegameConiugale,
    MetodoPagamento,
    Quota,
    TipoQuota,
)
from tests.conftest import INIZIO_ANNO, crea_capo, crea_persona, nato_anni_fa

pytestmark = pytest.mark.django_db

ANNO = 2026
FINE_ANNO = date(2026, 9, 30)
GENNAIO = date(2026, 1, 15)


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi if isinstance(chi, User) else chi.utente)
    return client


def _post(chi, url, dati=None):
    return _client(chi).post(url, dati or {}, content_type="application/json")


def _mensile(unita, **campi) -> TipoQuota:
    tipo = TipoQuota.objects.create(
        nome="Quota mensile",
        categoria=CategoriaQuota.MENSILE,
        anno=ANNO,
        importo=Decimal("10.00"),
        sconto_famiglia=campi.pop("sconto_famiglia", Decimal("0")),
        destinatari=Destinatari.UNITA,
        mesi=campi.pop("mesi", [10, 11, 1]),
        giorno_scadenza=10,
        **campi,
    )
    tipo.unita.set([unita])
    return tipo


def _annuale(categoria=CategoriaQuota.GRUPPO, destinatari=Destinatari.TUTTI, **campi):
    return TipoQuota.objects.create(
        nome=campi.pop("nome", "Quota di gruppo"),
        categoria=categoria,
        anno=ANNO,
        importo=campi.pop("importo", Decimal("40.00")),
        destinatari=destinatari,
        scadenza=date(2025, 11, 30),
        **campi,
    )


@pytest.fixture
def fratello(reparto, genitore):
    persona = crea_persona("Luca", "Esploratore", data_nascita=nato_anni_fa(13))
    Appartenenza.objects.create(
        persona=persona, unita=reparto, ruolo=RuoloAppartenenza.RAGAZZO, data_inizio=INIZIO_ANNO
    )
    RelazioneTutela.objects.create(tutore=genitore, minore=persona, tipo="GENITORE")
    return persona


@pytest.fixture
def tesoriere_gruppo(coca, gruppo):
    persona = crea_capo("Teresa", "Tesoriera", "tg@example.invalid")
    Incarico.objects.create(
        persona=persona,
        ruolo=RuoloIncarico.TESORIERE_GRUPPO,
        gruppo=gruppo,
        data_inizio=INIZIO_ANNO,
    )
    return persona


@pytest.fixture
def clan(gruppo):
    return Unita.objects.create(
        gruppo=gruppo, nome="Hirpinia", tipo=TipoUnita.CLAN_FUOCO, composizione=Composizione.MISTA
    )


@pytest.fixture
def tesoriere_rs(clan):
    """An R/S treasurer of the clan (DEC-11): same rights, no agevolazioni."""
    persona = crea_persona("Rita", "Rover", "rita@example.invalid", data_nascita=nato_anni_fa(19))
    Appartenenza.objects.create(
        persona=persona, unita=clan, ruolo=RuoloAppartenenza.RAGAZZO, data_inizio=INIZIO_ANNO
    )
    Incarico.objects.create(
        persona=persona, ruolo=RuoloIncarico.TESORIERE_UNITA, unita=clan, data_inizio=INIZIO_ANNO
    )
    return persona


@pytest.fixture
def rover(clan):
    persona = crea_persona("Piero", "Rover", data_nascita=nato_anni_fa(17))
    Appartenenza.objects.create(
        persona=persona, unita=clan, ruolo=RuoloAppartenenza.RAGAZZO, data_inizio=INIZIO_ANNO
    )
    return persona


@pytest.fixture
def staff(reparto, coca):
    persona = crea_capo("Elena", "Staff", "staff@example.invalid")
    Incarico.objects.create(
        persona=persona, ruolo=RuoloIncarico.STAFF, unita=reparto, data_inizio=INIZIO_ANNO
    )
    return persona


# --- Family --------------------------------------------------------------------------------


def test_famiglia_fratelli_e_genitore(ragazza, fratello, genitore, genitrice_senza_account):
    assert servizi.famiglia(ragazza) == {
        ragazza.pk,
        fratello.pk,
        genitore.pk,
        genitrice_senza_account.pk,
    }
    # Only members count: the parents are not in the group.
    assert servizi.soci_della_famiglia(ragazza, GENNAIO) == 2


def test_famiglia_genitore_capo_e_figlio(ragazza, genitore, coca):
    assert servizi.soci_della_famiglia(ragazza, GENNAIO) == 1
    Appartenenza.objects.create(
        persona=genitore, unita=coca, ruolo=RuoloAppartenenza.CAPO, data_inizio=INIZIO_ANNO
    )
    assert servizi.soci_della_famiglia(ragazza, GENNAIO) == 2


def test_coniugi_registrati_a_mano(coca, capo):
    moglie = crea_capo("Marta", "Coniuge")
    assert servizi.soci_della_famiglia(capo, GENNAIO) == 1
    a, b = sorted((capo.pk, moglie.pk))
    LegameConiugale.objects.create(persona_id=a, coniuge_id=b)
    assert servizi.soci_della_famiglia(capo, GENNAIO) == 2


# --- Fee types and issue -------------------------------------------------------------------


def test_regole_del_tipo_di_quota(reparto):
    tipo = TipoQuota(
        nome="Censimento",
        categoria=CategoriaQuota.CENSIMENTO,
        anno=ANNO,
        importo=Decimal("40"),
        sconto_famiglia=Decimal("5"),
        destinatari=Destinatari.TUTTI,
        scadenza=date(2025, 11, 30),
    )
    with pytest.raises(ValidationError, match="quota nazionale"):
        tipo.full_clean()
    tipo.sconto_famiglia = Decimal("0")
    tipo.scadenza = date(2026, 11, 30)  # next year
    with pytest.raises(ValidationError, match="anno associativo"):
        tipo.full_clean()
    mensile = TipoQuota(
        nome="Mensile",
        categoria=CategoriaQuota.MENSILE,
        anno=ANNO,
        importo=Decimal("10"),
        destinatari=Destinatari.UNITA,
    )
    with pytest.raises(ValidationError, match="mesi"):
        mensile.full_clean()


def test_mensile_una_quota_per_mese_iniziato(reparto, ragazza, fratello):
    tipo = _mensile(reparto)
    assert tipo.periodi()[0] == (date(2025, 10, 1), date(2025, 10, 10))
    nuove = servizi.emetti(tipo, oggi=date(2025, 11, 5))
    assert len(nuove) == 4  # October and November, two members
    assert servizi.emetti(tipo, oggi=date(2025, 11, 5)) == []  # idempotent
    assert len(servizi.emetti(tipo, oggi=GENNAIO)) == 2  # January


def test_chi_entra_a_meta_anno_paga_dai_mesi_successivi(reparto):
    nuovo = crea_persona("Nino", "Nuovo", data_nascita=nato_anni_fa(12))
    Appartenenza.objects.create(
        persona=nuovo, unita=reparto, ruolo=RuoloAppartenenza.RAGAZZO, data_inizio=date(2025, 11, 2)
    )
    tipo = _mensile(reparto)
    servizi.emetti(tipo, oggi=GENNAIO)
    assert [q.periodo.month for q in Quota.objects.filter(persona=nuovo)] == [1]


def test_destinatari(reparto, ragazza, capo):
    servizi.emetti(_annuale(destinatari=Destinatari.RAGAZZI, nome="Ragazzi"), oggi=GENNAIO)
    servizi.emetti(_annuale(destinatari=Destinatari.CAPI, nome="Capi"), oggi=GENNAIO)
    assert set(Quota.objects.filter(tipo__nome="Ragazzi").values_list("persona", flat=True)) == {
        ragazza.pk
    }
    assert set(Quota.objects.filter(tipo__nome="Capi").values_list("persona", flat=True)) == {
        capo.pk
    }


def test_sconto_famiglia_solo_con_almeno_due_soci(reparto, ragazza, fratello, csq):
    tipo = _annuale(sconto_famiglia=Decimal("5.00"))
    servizi.emetti(tipo, oggi=GENNAIO)
    quote = {q.persona_id: q for q in Quota.objects.filter(tipo=tipo)}
    assert quote[ragazza.pk].sconto == quote[fratello.pk].sconto == Decimal("5.00")
    assert quote[ragazza.pk].dovuto == Decimal("35.00")
    assert quote[csq.pk].sconto == Decimal("0")  # alone in the group


def test_emissione_non_tocca_le_quote_gia_emesse(reparto, ragazza):
    tipo = _annuale()
    servizi.emetti(tipo, oggi=GENNAIO)
    tipo.importo = Decimal("50")
    tipo.save()
    assert Quota.objects.get(persona=ragazza).importo == Decimal("40.00")


# --- Payments and receipts --------------------------------------------------------------------


@pytest.fixture
def quote_famiglia(reparto, ragazza, fratello, genitore):
    tipo = _annuale(sconto_famiglia=Decimal("5.00"))
    servizi.emetti(tipo, oggi=GENNAIO)
    return Quota.objects.get(persona=ragazza), Quota.objects.get(persona=fratello)


def _paga(quote_importi, utente, **campi):
    return servizi.registra_pagamento(
        data=campi.pop("data", GENNAIO),
        metodo=MetodoPagamento.CONTANTI,
        versato_da="Mario Genitore",
        righe=[servizi.Riga(q, Decimal(i)) for q, i in quote_importi],
        utente=utente,
        **campi,
    )


def test_un_pagamento_su_piu_quote_con_acconto(quote_famiglia, staff):
    sua, del_fratello = quote_famiglia
    pagamento = _paga([(sua, "35"), (del_fratello, "10")], staff.utente)
    assert pagamento.importo == Decimal("45")
    assert pagamento.numero == "2025-26/001"
    sua.refresh_from_db()
    del_fratello.refresh_from_db()
    assert sua.residuo == 0
    assert del_fratello.residuo == Decimal("25")
    assert _paga([(del_fratello, "25")], staff.utente).numero == "2025-26/002"


def test_pagamento_oltre_il_dovuto_o_di_altre_famiglie(quote_famiglia, csq, staff):
    sua, _ = quote_famiglia
    with pytest.raises(ValidationError, match="restano da pagare 35,00 €"):
        _paga([(sua, "36")], staff.utente)
    servizi.emetti(_annuale(nome="Altra"), oggi=GENNAIO)
    di_altri = Quota.objects.get(persona=csq, tipo__nome="Altra")
    with pytest.raises(ValidationError, match="stessa famiglia"):
        _paga([(sua, "5"), (di_altri, "5")], staff.utente)
    with pytest.raises(ValidationError, match="futuro"):
        _paga([(sua, "5")], staff.utente, data=date(2999, 1, 1))


def test_annullare_pagamento_libera_la_quota_e_tiene_il_numero(quote_famiglia, staff):
    sua, _ = quote_famiglia
    pagamento = _paga([(sua, "35")], staff.utente)
    with pytest.raises(ValidationError, match="pagamenti"):
        servizi.annulla_quota(sua, staff.utente, "Errore")
    servizi.annulla_pagamento(pagamento, staff.utente, "Importo sbagliato")
    assert sua.residuo == Decimal("35")
    assert _paga([(sua, "30")], staff.utente).numero == "2025-26/002"


def test_ricevuta_ai_genitori_del_minore(quote_famiglia, genitore, genitrice_senza_account, staff):
    sua, _ = quote_famiglia
    pagamento = _paga([(sua, "35")], staff.utente)
    assert servizi.invia_ricevuta(pagamento)
    # One message per parent: separated parents do not see each other's address.
    assert sorted(m.to[0] for m in mail.outbox) == [
        "genitore@example.invalid",
        "lucia@example.invalid",
    ]
    messaggio = mail.outbox[0]
    assert len(messaggio.to) == 1 and "2025-26/001" in messaggio.subject
    nome, contenuto, tipo = messaggio.attachments[0]
    assert nome == "ricevuta-2025-26-001.pdf" and tipo == "application/pdf"
    assert contenuto.startswith(b"%PDF")


def test_ricevuta_del_maggiorenne_e_genitori_scollegati(rover, clan, staff):
    rover.data_nascita = nato_anni_fa(19)
    rover.email = "piero@example.invalid"
    rover.save()
    padre = crea_persona("Paolo", "Rover", email="paolo@example.invalid")
    RelazioneTutela.objects.create(tutore=padre, minore=rover, tipo="GENITORE")
    tipo = _annuale()
    servizi.emetti(tipo, oggi=GENNAIO)
    pagamento = _paga([(Quota.objects.get(persona=rover), "40")], staff.utente)
    assert set(servizi.destinatari_ricevuta(pagamento)) == {
        "piero@example.invalid",
        "paolo@example.invalid",
    }
    VisibilitaGenitori.objects.create(persona=rover, quote=False)
    assert servizi.destinatari_ricevuta(pagamento) == ["piero@example.invalid"]


# --- Who sees and does what -----------------------------------------------------------------


def test_chi_vede_e_registra(
    ragazza,
    genitore,
    capo,
    capogruppo,
    staff,
    csq,
    estraneo,
    tesoriere_gruppo,
    tesoriere_rs,
    rover,
):
    assert policy.puo_vedere_quote(capo.utente, ragazza)  # Co.Ca. (DEC-92)
    assert policy.puo_vedere_quote(genitore.utente, ragazza)
    assert policy.puo_vedere_quote(ragazza.utente, ragazza)
    assert not policy.puo_vedere_quote(csq.utente, ragazza)
    assert not policy.puo_vedere_quote(estraneo.utente, ragazza)
    assert not policy.puo_vedere_quote(tesoriere_rs.utente, ragazza)  # not their unit
    assert policy.puo_vedere_quote(tesoriere_rs.utente, rover)

    assert policy.puo_registrare_pagamenti(staff.utente, ragazza)
    assert policy.puo_registrare_pagamenti(capo.utente, ragazza)  # capo unità
    assert policy.puo_registrare_pagamenti(capogruppo.utente, ragazza)
    assert policy.puo_registrare_pagamenti(tesoriere_gruppo.utente, ragazza)
    assert policy.puo_registrare_pagamenti(tesoriere_rs.utente, rover)
    assert not policy.puo_registrare_pagamenti(tesoriere_rs.utente, ragazza)
    assert not policy.puo_registrare_pagamenti(staff.utente, rover)  # not their unit
    assert not policy.puo_registrare_pagamenti(genitore.utente, ragazza)

    assert policy.puo_gestire_quote(capogruppo.utente)
    assert policy.puo_gestire_quote(tesoriere_gruppo.utente)
    assert not policy.puo_gestire_quote(capo.utente)
    assert policy.puo_registrare_agevolazioni(tesoriere_gruppo.utente)
    assert not policy.puo_vedere_agevolazioni(tesoriere_rs.utente)
    assert policy.puo_vedere_agevolazione_di(genitore.utente, ragazza)


def test_genitore_di_maggiorenne_scollegato_dalle_quote(rover, genitore):
    rover.data_nascita = nato_anni_fa(19)
    rover.save()
    RelazioneTutela.objects.create(tutore=genitore, minore=rover, tipo="GENITORE")
    assert policy.puo_vedere_quote(genitore.utente, rover)
    VisibilitaGenitori.objects.create(persona=rover, quote=False)
    assert not policy.puo_vedere_quote(genitore.utente, rover)


# --- API ------------------------------------------------------------------------------------


def test_api_tipi_ed_emissione(reparto, ragazza, capo, capogruppo):
    dati = {
        "nome": "Quota mensile",
        "categoria": "MENSILE",
        "anno": ANNO,
        "importo": "10.00",
        "destinatari": "UNITA",
        "unita": [reparto.pk],
        "mesi": [10, 11],
        "giorno_scadenza": 10,
    }
    assert _post(capo, "/api/v1/quote/tipi", dati).status_code == 403
    risposta = _post(capogruppo, "/api/v1/quote/tipi", dati)
    assert risposta.status_code == 201, risposta.content
    tipo = risposta.json()
    assert tipo["categoria_nome"] == "Quota mensile di unità"
    emesse = _post(capogruppo, f"/api/v1/quote/tipi/{tipo['id']}/emetti").json()
    assert emesse["emesse"] == 2  # October and November 2025 for Giulia: already started
    sbagliato = _post(capogruppo, "/api/v1/quote/tipi", {**dati, "unita": []})
    assert sbagliato.status_code == 400


def test_api_pagamento_e_ricevuta(quote_famiglia, genitore, staff, estraneo, csq):
    sua, del_fratello = quote_famiglia
    corpo = {
        "data": "2026-01-15",
        "metodo": "BONIFICO",
        "versato_da": "Mario Genitore",
        "righe": [
            {"quota_id": sua.pk, "importo": "35.00"},
            {"quota_id": del_fratello.pk, "importo": "5.00"},
        ],
    }
    assert _post(csq, "/api/v1/pagamenti", corpo).status_code == 403
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("django.db.transaction.on_commit", lambda funzione: funzione())
        risposta = _post(staff, "/api/v1/pagamenti", corpo)
    assert risposta.status_code == 201, risposta.content
    pagamento = risposta.json()
    assert pagamento["numero"] == "2025-26/001"
    assert pagamento["registrato_da"] == "Elena Staff"
    assert len(mail.outbox) == 1

    pdf = _client(genitore).get(f"/api/v1/pagamenti/{pagamento['id']}/ricevuta.pdf")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    vietato = _client(estraneo).get(f"/api/v1/pagamenti/{pagamento['id']}/ricevuta.pdf")
    assert vietato.status_code == 404

    mie = _client(genitore).get("/api/v1/mie-quote?anno=2026").json()
    assert {q["residuo"] for q in mie["quote"]} == {"0.00", "30.00"}
    assert [p["numero"] for p in mie["pagamenti"]] == ["2025-26/001"]


def test_api_agevolazione_visibile_alla_famiglia_non_al_tesoriere_rs(
    rover, tesoriere_rs, tesoriere_gruppo, capo
):
    servizi.emetti(_annuale(), oggi=GENNAIO)
    quota = Quota.objects.get(persona=rover)
    url = f"/api/v1/quote/{quota.pk}/agevolazione"
    dati = {"importo": "15.00", "decisa_il": "2025-12-01", "nota": "Decisa in Co.Ca."}
    assert _client(capo).put(url, dati, content_type="application/json").status_code == 403
    risposta = _client(tesoriere_gruppo).put(url, dati, content_type="application/json")
    assert risposta.status_code == 200, risposta.content
    assert risposta.json()["dovuto"] == "25.00"

    da_rs = _client(tesoriere_rs).get(f"/api/v1/persone/{rover.pk}/quote?anno=2026").json()
    [vista] = da_rs["quote"]
    assert vista["agevolazione"] is None and vista["residuo"] == "25.00"
    da_capo = _client(capo).get(f"/api/v1/persone/{rover.pk}/quote?anno=2026").json()
    assert da_capo["quote"][0]["agevolazione"]["nota"] == "Decisa in Co.Ca."
    assert Agevolazione.objects.count() == 1


def test_api_situazione_dell_unita(reparto, clan, ragazza, fratello, capo, tesoriere_rs, csq):
    servizi.emetti(_annuale(), oggi=GENNAIO)
    url = f"/api/v1/quote/situazione?unita={reparto.pk}&anno=2026"
    righe = _client(capo).get(url).json()
    assert {r["persona"] for r in righe} == {"Esploratrice Giulia", "Esploratore Luca", "Csq Sara"}
    assert all(r["scadute"] == 1 for r in righe)  # due 30/11/2025
    assert _client(tesoriere_rs).get(url).status_code == 403
    assert _client(csq).get(url).status_code == 403


def test_quote_non_pagate_passano_all_anno_dopo(ragazza, genitore, capo, reparto):
    """Unpaid fees carry over to the following years as arrears (DEC-216)."""
    servizi.emetti(_annuale(), oggi=GENNAIO)
    pagata = _annuale(nome="Quota pagata", importo=Decimal("5.00"))
    servizi.emetti(pagata, oggi=GENNAIO)
    _paga([(Quota.objects.get(tipo=pagata, persona=ragazza), "5.00")], capo.utente)
    mie = _client(genitore).get(f"/api/v1/mie-quote?anno={ANNO + 1}").json()
    assert [(q["descrizione"], q["arretrata"]) for q in mie["quote"]] == [
        ("Quota di gruppo 2025/26", True)
    ]
    stesse = _client(genitore).get(f"/api/v1/mie-quote?anno={ANNO}").json()
    assert not any(q["arretrata"] for q in stesse["quote"])


def test_agevolazione_in_anno_chiuso_solo_sulle_pendenze(ragazza, tesoriere_gruppo, capo):
    """In a closed year an agevolazione goes only on a fee still unpaid (DEC-216)."""
    from apps.organizzazione.models import AnnoChiuso

    servizi.emetti(_annuale(), oggi=GENNAIO)
    pagata = _annuale(nome="Quota pagata", importo=Decimal("5.00"))
    servizi.emetti(pagata, oggi=GENNAIO)
    saldata = Quota.objects.get(tipo=pagata, persona=ragazza)
    _paga([(saldata, "5.00")], capo.utente)
    AnnoChiuso.objects.create(anno=ANNO, chiuso_il=date(2026, 10, 30))
    aperta = Quota.objects.get(tipo__nome="Quota di gruppo", persona=ragazza)
    dati = {"importo": "10.00", "decisa_il": "2026-11-05"}
    client = _client(tesoriere_gruppo)
    url = "/api/v1/quote/{}/agevolazione"
    risposta = client.put(url.format(aperta.pk), dati, content_type="application/json")
    assert risposta.status_code == 200
    rifiutata = client.put(url.format(saldata.pk), dati, content_type="application/json")
    assert rifiutata.status_code == 400


# --- How families pay (DEC-253) ------------------------------------------------------------

IBAN = "IT60X0542811101000000123456"  # the usual example, with valid check digits
PAGAMENTI = "/api/v1/quote/impostazioni"


def _imposta(chi, **dati):
    return _client(chi).put(PAGAMENTI, dati, content_type="application/json")


def test_iban_controllato():
    from apps.quote.modi_pagamento import iban_valido

    assert iban_valido(IBAN) and iban_valido("it60 x054 2811 1010 0000 0123 456")
    assert not iban_valido("IT61X0542811101000000123456")
    assert not iban_valido("IT60X05428")


def test_quota_aggiuntiva_paypal(gruppo):
    from apps.quote.modi_pagamento import maggiorazione_paypal

    gruppo.paypal_maggiorazione = "FISSA"
    gruppo.paypal_valore = Decimal("2")
    assert maggiorazione_paypal(gruppo, Decimal("35")) == Decimal("2.00")
    gruppo.paypal_maggiorazione = "PERCENTUALE"
    gruppo.paypal_valore = Decimal("3.4")
    assert maggiorazione_paypal(gruppo, Decimal("35")) == Decimal("1.19")
    gruppo.paypal_maggiorazione = "FASCE"
    gruppo.paypal_fasce = [
        {"fino_a": "10", "quota": "0.25"},
        {"fino_a": "50", "quota": "0.50"},
        {"fino_a": None, "quota": "1"},
    ]
    assert maggiorazione_paypal(gruppo, Decimal("10")) == Decimal("0.25")
    assert maggiorazione_paypal(gruppo, Decimal("10.01")) == Decimal("0.50")
    assert maggiorazione_paypal(gruppo, Decimal("200")) == Decimal("1.00")
    assert maggiorazione_paypal(gruppo, Decimal("0")) == Decimal("0.00")
    gruppo.paypal_maggiorazione = "NESSUNA"
    assert maggiorazione_paypal(gruppo, Decimal("35")) == Decimal("0.00")


def test_chi_imposta_i_pagamenti_e_cosa_si_controlla(
    gruppo, capo, capogruppo, tesoriere_gruppo, genitore, estraneo
):
    for chi in (capo, genitore, estraneo):
        assert _imposta(chi, contanti_attivo=False).status_code == 403
    assert _imposta(tesoriere_gruppo, bonifico_attivo=True).status_code == 400  # no IBAN
    sbagliato = _imposta(capogruppo, bonifico_attivo=True, iban="IT61X0542811101000000123456")
    assert "IBAN" in sbagliato.json()["detail"]
    assert _imposta(capogruppo, paypal_attivo=True).status_code == 400  # no link
    fasce = [{"fino_a": "50", "quota": "0.5"}, {"fino_a": "10", "quota": "0.25"}]
    disordinate = _imposta(
        capogruppo,
        paypal_attivo=True,
        link_pagamento="https://paypal.me/gruppo",
        paypal_maggiorazione="FASCE",
        paypal_fasce=fasce,
    )
    assert disordinate.status_code == 400
    senza_oltre = _imposta(
        capogruppo,
        paypal_attivo=True,
        link_pagamento="https://paypal.me/gruppo",
        paypal_maggiorazione="FASCE",
        paypal_fasce=[{"fino_a": "10", "quota": "0.25"}],
    )
    assert "oltre la fascia più alta" in senza_oltre.json()["detail"]
    giusto = _imposta(
        tesoriere_gruppo,
        bonifico_attivo=True,
        iban="it60 x054 2811 1010 0000 0123 456",
        intestatario_conto="AGESCI Gruppo Prova 1",
        paypal_attivo=True,
        link_pagamento="https://paypal.me/gruppo",
        paypal_maggiorazione="FISSA",
        paypal_valore="2",
    )
    assert giusto.status_code == 200 and giusto.json()["iban"] == IBAN


def test_la_famiglia_vede_solo_i_modi_abilitati(quote_famiglia, capogruppo, genitore):
    modi = _client(genitore).get(f"/api/v1/mie-quote?anno={ANNO}").json()["modi_pagamento"]
    assert modi == {"contanti": True, "bonifico": None, "paypal": None}
    _imposta(
        capogruppo,
        contanti_attivo=False,
        bonifico_attivo=True,
        iban=IBAN,
        intestatario_conto="AGESCI Gruppo Prova 1",
        paypal_attivo=True,
        link_pagamento="https://paypal.me/gruppo",
        paypal_maggiorazione="FISSA",
        paypal_valore="2",
    )
    dati = _client(genitore).get(f"/api/v1/mie-quote?anno={ANNO}").json()
    da_pagare = sum(Decimal(q["residuo"]) for q in dati["quote"])
    modi = dati["modi_pagamento"]
    assert modi["contanti"] is False
    assert modi["bonifico"] == {"iban": IBAN, "intestatario": "AGESCI Gruppo Prova 1"}
    assert Decimal(modi["paypal"]["maggiorazione"]) == Decimal("2.00")
    assert Decimal(modi["paypal"]["totale"]) == da_pagare + 2
    assert "2,00 €" in modi["paypal"]["regola"]
