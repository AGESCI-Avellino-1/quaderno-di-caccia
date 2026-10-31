"""Bank statement (DEC-93, DEC-221…DEC-224)."""

from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

from apps.banca import estratto, servizi
from apps.banca.models import CartaUnita, RigaBanca
from apps.cassa.models import Cassa, Movimento, TipoCassa, TipoMovimento
from apps.organizzazione.models import Incarico, RuoloIncarico
from apps.quote import servizi as quote
from apps.quote.models import (
    CategoriaQuota,
    Destinatari,
    MetodoPagamento,
    Pagamento,
    Quota,
    TipoQuota,
)
from tests.conftest import INIZIO_ANNO, crea_capo
from tests.estratto_sintetico import bonifico_ricevuto, costruisci_xlsx, movimento

pytestmark = pytest.mark.django_db

GENNAIO = date(2026, 1, 15)


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


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
        data_saldo_iniziale=INIZIO_ANNO,
    )


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
def censimento(reparto, ragazza, genitore):
    tipo = TipoQuota.objects.create(
        nome="Censimento",
        categoria=CategoriaQuota.CENSIMENTO,
        anno=2026,
        importo=Decimal("40"),
        destinatari=Destinatari.TUTTI,
        scadenza=date(2025, 11, 30),
    )
    quote.emetti(tipo, oggi=GENNAIO)
    return Quota.objects.get(tipo=tipo, persona=ragazza)


def _estratto(*movimenti, saldo_iniziale="1000"):
    return costruisci_xlsx(saldo_iniziale, list(movimenti))


BONIFICO = movimento(
    GENNAIO,
    "ACCREDITO BEU CON CONTABILE",
    "40",
    bonifico_ricevuto("CENSIMENTO GIULIA ESPLORATRICE", "GENITORE MARIO"),
)
CANONE = movimento(
    date(2026, 1, 31), "CANONE MENSILE BASE E SERVIZI AGGIUNTIVI", "-5", "CANONE MENSILE"
)
PRELIEVO = movimento(
    date(2026, 2, 3),
    "PRELIEVO CARTA DEBITO SU BANCHE DEL GRUPPO",
    "-100",
    "CON CARTA N.      4321 DEL 03/02/2026 ORE 10:00 PRESSO ABI 00000",
)


def test_lettura_del_file():
    letto = estratto.leggi(_estratto(BONIFICO, CANONE))
    assert letto.saldo_iniziale == Decimal("1000.00")
    assert letto.saldo_finale == Decimal("1035.00")
    assert letto.data_finale == date(2026, 9, 30)
    assert sorted(m.importo for m in letto.movimenti) == [Decimal("-5.00"), Decimal("40.00")]


def test_file_che_non_torna_o_non_valido():
    with pytest.raises(ValidationError, match="non tornano"):
        estratto.leggi(costruisci_xlsx("1000", [BONIFICO], saldo_finale="999"))
    with pytest.raises(ValidationError, match="formato"):
        estratto.leggi(b"non un file excel")


def test_righe_caricate_una_volta_sola(banca, capogruppo):
    primo = servizi.carica(banca, _estratto(BONIFICO, CANONE), capogruppo.utente)
    secondo = servizi.carica(banca, _estratto(BONIFICO, CANONE, PRELIEVO), capogruppo.utente)
    assert (primo.righe_nuove, secondo.righe_nuove, secondo.righe_gia_presenti) == (2, 1, 2)
    # Before the account's initial balance: already in it.
    vecchio = movimento(
        date(2025, 9, 20), "CANONE MENSILE BASE E SERVIZI AGGIUNTIVI", "-5", "VECCHIO"
    )
    assert servizi.carica(banca, _estratto(vecchio), capogruppo.utente).righe_nuove == 0


def test_bonifico_proposto_e_pagato(banca, censimento, capogruppo):
    servizi.carica(banca, _estratto(BONIFICO), capogruppo.utente)
    riga = RigaBanca.objects.get()
    proposte = servizi.quote_proposte(riga)
    assert proposte[0]["ripartizione"] == {censimento.pk: Decimal("40.00")}
    assert servizi.ordinante(riga) == "GENITORE MARIO"
    servizi.paga_quote(
        riga, [quote.Riga(censimento, Decimal("40"))], servizi.ordinante(riga), capogruppo.utente
    )
    pagamento = Pagamento.objects.get()
    assert (pagamento.metodo, pagamento.data, pagamento.versato_da) == (
        MetodoPagamento.BONIFICO,
        GENNAIO,
        "GENITORE MARIO",
    )
    assert censimento.residuo == 0
    assert not servizi.da_abbinare(banca).exists()
    assert banca.saldo() == Decimal("1040.00")


def test_ricevuta_del_bonifico_parte_per_email(
    banca, censimento, capogruppo, monkeypatch, django_capture_on_commit_callbacks
):
    """A payment confirmed from the bank statement sends its receipt like any other."""
    inviate = []
    monkeypatch.setattr(servizi, "invia_ricevuta", inviate.append)
    servizi.carica(banca, _estratto(BONIFICO), capogruppo.utente)
    riga = RigaBanca.objects.get()
    with django_capture_on_commit_callbacks(execute=True):
        servizi.paga_quote(riga, [quote.Riga(censimento, Decimal("40"))], "", capogruppo.utente)
    assert inviate == [Pagamento.objects.get()]


def test_pagamento_gia_registrato_si_collega(banca, censimento, capogruppo):
    quote.registra_pagamento(
        data=date(2026, 1, 12),
        metodo=MetodoPagamento.BONIFICO,
        versato_da="Mario Genitore",
        righe=[quote.Riga(censimento, Decimal("40"))],
        utente=capogruppo.utente,
        cassa=banca,
    )
    servizi.carica(banca, _estratto(BONIFICO), capogruppo.utente)
    riga = RigaBanca.objects.get()
    registrati = servizi.movimenti_registrati(riga)
    assert len(registrati) == 1
    servizi.collega(riga, registrati[0]["movimenti"], capogruppo.utente)
    assert Movimento.objects.count() == 1  # no second copy
    assert banca.saldo() == Decimal("1040.00")
    with pytest.raises(ValidationError):
        servizi.collega(riga, registrati[0]["movimenti"], capogruppo.utente)


def test_uscite_spese_bancarie_e_prelievo_con_carta(banca, contanti, reparto, capogruppo):
    CartaUnita.objects.create(unita=reparto, ultime_cifre="4321")
    servizi.carica(banca, _estratto(CANONE, PRELIEVO), capogruppo.utente)
    canone = RigaBanca.objects.get(importo=Decimal("-5"))
    prelievo = RigaBanca.objects.get(importo=Decimal("-100"))
    proposta = servizi.proposta_uscita(canone)
    assert proposta["tipo"] == TipoMovimento.USCITA and proposta["voce_id"]
    proposta = servizi.proposta_uscita(prelievo)
    assert proposta["unita"] == reparto and proposta["cassa_destinazione"] == contanti
    servizi.nuovo_movimento(
        canone,
        utente=capogruppo.utente,
        descrizione="Canone",
        voce_id=servizi.proposta_uscita(canone)["voce_id"],
    )
    servizi.nuovo_movimento(
        prelievo,
        utente=capogruppo.utente,
        descrizione="Prelievo",
        unita=reparto,
        cassa_destinazione=contanti,
    )
    assert banca.saldo() == Decimal("895.00")
    assert contanti.saldo() == Decimal("100.00")
    saldo = servizi.verifica_saldo(banca)
    assert saldo["differenza"] == 0


def test_scollega_e_storno(banca, capogruppo):
    servizi.carica(banca, _estratto(CANONE), capogruppo.utente)
    riga = RigaBanca.objects.get()
    voce = servizi.proposta_uscita(riga)["voce_id"]
    servizi.nuovo_movimento(riga, utente=capogruppo.utente, descrizione="Canone", voce_id=voce)
    assert not servizi.da_abbinare(banca).exists()
    from apps.cassa.servizi import storna

    storna(riga.movimenti.get(), capogruppo.utente, "Voce sbagliata")
    assert servizi.da_abbinare(banca).exists()  # back among the lines to match


def test_chi_gestisce(
    banca, capo, capogruppo, tesoriere_gruppo, ragazza, genitore, estraneo, reparto
):
    file = _estratto(CANONE)
    url = f"/api/v1/banca/{banca.pk}/estratti"
    for chi in (capo, ragazza, genitore, estraneo):
        assert (
            _client(chi).post(url, {"file": SimpleUploadedFile("e.xlsx", file)}).status_code == 403
        )
        assert _client(chi).get(f"/api/v1/banca/{banca.pk}/righe").status_code == 403
    risposta = _client(tesoriere_gruppo).post(url, {"file": SimpleUploadedFile("e.xlsx", file)})
    assert risposta.status_code == 201 and risposta.json()["righe_nuove"] == 1
    righe = _client(capogruppo).get(f"/api/v1/banca/{banca.pk}/righe").json()
    assert righe["righe"][0]["uscita"]["voce_id"]
    # Cards: only the capigruppo.
    carta = {"unita_id": reparto.pk, "ultime_cifre": "1111"}
    assert (
        _client(tesoriere_gruppo)
        .post("/api/v1/banca/carte", carta, content_type="application/json")
        .status_code
        == 403
    )
    assert (
        _client(capogruppo)
        .post("/api/v1/banca/carte", carta, content_type="application/json")
        .status_code
        == 201
    )


def test_conferma_dall_api(banca, censimento, tesoriere_gruppo):
    servizi.carica(banca, _estratto(BONIFICO), tesoriere_gruppo.utente)
    riga = RigaBanca.objects.get()
    dati = {
        "azione": "quote",
        "quote": [{"quota_id": censimento.pk, "importo": "40"}],
        "versato_da": "Mario Genitore",
    }
    risposta = _client(tesoriere_gruppo).post(
        f"/api/v1/banca/righe/{riga.pk}/conferma", dati, content_type="application/json"
    )
    assert risposta.status_code == 200, risposta.content
    sbagliata = {**dati, "quote": [{"quota_id": censimento.pk, "importo": "30"}]}
    assert (
        _client(tesoriere_gruppo)
        .post(f"/api/v1/banca/righe/{riga.pk}/conferma", sbagliata, content_type="application/json")
        .status_code
        == 400
    )
