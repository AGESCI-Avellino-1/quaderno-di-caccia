"""The waiting list (DEC-256…DEC-263)."""

from datetime import timedelta

import pytest
from django.core import mail
from django.core.exceptions import ValidationError
from django.test import Client
from django.utils import timezone

from apps.attesa import servizi
from apps.attesa.models import ConteggioAttesa, InAttesa
from apps.core.anno import AnnoAssociativo
from apps.organizzazione.models import Composizione, TipoUnita, Unita
from tests.conftest import nato_anni_fa

PUBBLICA = "/api/v1/lista-attesa"


@pytest.fixture(autouse=True)
def _senza_limiti():
    """The public pages are rate-limited per address: every test starts afresh."""
    from django.core.cache import cache

    cache.clear()


def _client(chi=None) -> Client:
    client = Client()
    if chi is not None:
        client.force_login(chi.utente)
    return client


def _dati(anni=12, **altri):
    return {
        "nome": "Marta",
        "cognome": "Verdi",
        "sesso": "F",
        "data_nascita": nato_anni_fa(anni).isoformat(),
        "luogo_nascita": "Avellino",
        "contatto_nome": "Carla",
        "contatto_cognome": "Verdi",
        "telefono": "3330000099",
        "email": "carla.verdi@example.invalid",
        "indirizzo": "Via Roma 1",
        "comune": "Avellino",
        "provincia": "av",
        "cap": "83100",
        **altri,
    }


@pytest.fixture
def clan(gruppo):
    return Unita.objects.create(
        gruppo=gruppo, nome="Hirpinia", tipo=TipoUnita.CLAN_FUOCO, composizione=Composizione.MISTA
    )


@pytest.fixture
def in_lista(reparto, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        risposta = _client().post(
            PUBBLICA, {**_dati(), "privacy": True}, content_type="application/json"
        )
    assert risposta.status_code == 201
    return InAttesa.objects.get()


def test_mettersi_in_lista(in_lista):
    [conferma] = mail.outbox
    assert conferma.to == ["carla.verdi@example.invalid"]
    assert f"/lista-attesa/{in_lista.token}" in conferma.body
    assert "quest'anno scout" in conferma.body  # 12 years old: E/G now
    assert in_lista.provincia == "AV"
    assert ConteggioAttesa.objects.get().entrati == 1


def test_modulo_pubblico_controllato(reparto):
    senza_privacy = _client().post(PUBBLICA, _dati(), content_type="application/json")
    assert senza_privacy.status_code in (400, 422)
    minorenne_da_se = {**_dati(anni=15), "da_se": True, "privacy": True}
    assert (
        _client().post(PUBBLICA, minorenne_da_se, content_type="application/json").status_code
        == 400
    )
    assert not InAttesa.objects.exists()


def test_link_personale_e_uscita(in_lista):
    url = f"{PUBBLICA}/{in_lista.token}"
    dati = _client().get(url).json()
    assert dati["nome"] == "Marta" and "posizione" not in dati
    assert (
        _client().put(url, _dati(nome="Martina"), content_type="application/json").json()["nome"]
        == "Martina"
    )
    # Asking the link again: the same answer whether or not the address is on the list.
    mail.outbox.clear()
    for email in ("carla.verdi@example.invalid", "nessuno@example.invalid"):
        risposta = _client().post(
            f"{PUBBLICA}/link", {"email": email}, content_type="application/json"
        )
        assert risposta.status_code == 202
    assert [m.to for m in mail.outbox] == [["carla.verdi@example.invalid"]]
    # Leaving: the data go, a count stays (DEC-263).
    assert _client().delete(url).status_code == 204
    assert not InAttesa.objects.exists() and _client().get(url).status_code == 404
    assert ConteggioAttesa.objects.get().usciti == 1


def test_chi_vede_e_gestisce(in_lista, capo, capogruppo, ragazza, genitore, estraneo, clan):
    for chi in (ragazza, genitore, estraneo):
        assert _client(chi).get("/api/v1/attesa").status_code == 403
    lista = _client(capo).get("/api/v1/attesa").json()
    [voce] = lista["voci"]
    assert voce["eta"] == 12 and voce["eta_prossimo"] == 13
    assert [u["nome"] for u in voce["consigliate"]] == ["Reparto Reparto Prova"]
    assert voce["stato"] == "DA_CONTATTARE" and not voce["possibile_doppione"]
    # The capo unità of the reparto acts for the reparto, not for the clan.
    url = f"/api/v1/attesa/{in_lista.pk}/contatto"
    assert (
        _client(capo).post(url, {"unita_id": clan.pk}, content_type="application/json").status_code
        == 403
    )
    assert (
        _client(capo)
        .post(url, {"unita_id": in_lista_reparto(capo)}, content_type="application/json")
        .status_code
        == 204
    )
    assert _client(genitore).post(url, {}, content_type="application/json").status_code == 403
    in_lista.refresh_from_db()
    assert in_lista.stato == "CONTATTATO"


def in_lista_reparto(capo) -> int:
    return Unita.objects.get(tipo=TipoUnita.REPARTO).pk


def test_un_capo_mette_in_lista_e_i_doppioni(reparto, capo, genitore):
    assert (
        _client(genitore)
        .post("/api/v1/attesa", _dati(), content_type="application/json")
        .status_code
        == 403
    )
    for _ in range(2):
        assert (
            _client(capo)
            .post("/api/v1/attesa", _dati(), content_type="application/json")
            .status_code
            == 201
        )
    voci = _client(capo).get("/api/v1/attesa").json()["voci"]
    assert all(v["possibile_doppione"] and v["inserito_da_un_capo"] for v in voci)


def test_iscrizione_dalla_lista(in_lista, reparto, capo, django_capture_on_commit_callbacks):
    from apps.accounts.models import User
    from apps.iscrizioni import servizi as iscrizioni
    from apps.iscrizioni.models import CodiceIscrizione

    mail.outbox.clear()
    with django_capture_on_commit_callbacks(execute=True):
        risposta = _client(capo).post(
            f"/api/v1/attesa/{in_lista.pk}/iscrivi",
            {"unita_id": reparto.pk},
            content_type="application/json",
        )
    assert risposta.status_code == 204
    assert not InAttesa.objects.exists()  # out of the list, the data in the code
    assert ConteggioAttesa.objects.get().iscritti == 1
    codice = CodiceIscrizione.objects.get()
    [email] = mail.outbox
    assert f"/iscrizione/{codice.codice}" in email.body
    # The public page of the code fills in the form.
    info = _client().get(f"/api/v1/iscrizione/{codice.codice}").json()
    assert info["proposti"]["nome"] == "Marta" and info["proposti"]["contatto_nome"] == "Carla"
    # The family joins as from the app; at the approval the list's data reach the card.
    genitore = User.objects.create_user(email="carla.verdi@example.invalid")
    dati = iscrizioni.DatiIscrizione(
        nome="Marta",
        cognome="Verdi",
        data_nascita=in_lista.data_nascita,
        codice_fiscale="VRDMRT14A41A509X",
        genitore_nome="Carla",
        genitore_cognome="Verdi",
        genitore_codice_fiscale="VRDCRL80A41A509X",
        sesso="F",
        responsabilita="UNICO_GENITORE",
        genitore_cellulare="3330000099",
    )
    # The link is for Marta only.
    altra = iscrizioni.DatiIscrizione(**{**vars(dati), "nome": "Giulia"})
    with pytest.raises(ValidationError):
        iscrizioni.crea_richiesta(codice, altra, genitore)
    richiesta = iscrizioni.crea_richiesta(codice, dati, genitore)
    socio = iscrizioni.approva(richiesta, capo.utente, timezone.localdate() + timedelta(days=30))
    assert (socio.sesso, socio.luogo_nascita, socio.cap) == ("F", "Avellino", "83100")
    assert socio.tutori.get().tutore.cellulare == "3330000099"
    codice.refresh_from_db()
    assert codice.dati_proposti == {}


def test_due_anni_poi_fuori(in_lista):
    oggi = timezone.localdate()
    # 15: old enough for the reparto for more than two years, on the list as long.
    in_lista.data_nascita = nato_anni_fa(15)
    in_lista.creato_il = timezone.now() - timedelta(days=servizi.DUE_ANNI + 1)
    in_lista.save()
    mail.outbox.clear()
    assert servizi.promemoria(oggi)["chiesti"] == 1
    assert servizi.promemoria(oggi + timedelta(days=15))["ricordati"] == 1
    assert len([m for m in mail.outbox if "restare in lista" in m.subject]) == 2
    # Confirming brings the question back in two years.
    servizi.conferma_interesse(in_lista)
    assert servizi.promemoria(oggi + timedelta(days=40))["chiesti"] == 0
    # Asked again, nobody answers for 30 days: out, with an email.
    in_lista.refresh_from_db()
    in_lista.conferma_chiesta_il = oggi
    in_lista.save()
    assert servizi.promemoria(oggi + timedelta(days=30))["usciti"] == 1
    assert not InAttesa.objects.exists()
    assert "uscita dalla lista" in mail.outbox[-1].subject


def test_i_due_anni_contano_dall_eta_minima(reparto):
    piccolo = InAttesa(data_nascita=nato_anni_fa(5), creato_il=timezone.now())
    anno = servizi.anno_contattabile(piccolo.data_nascita)
    assert anno is not None and anno.anno_fine > AnnoAssociativo.corrente().anno_fine
    assert servizi.scadenza_interesse(piccolo) == anno.inizio + timedelta(days=servizi.DUE_ANNI)


def test_eta_delle_unita(reparto, capo, ragazza, capogruppo):
    assert reparto.eta == (12, 16)
    url = f"/api/v1/unita/{reparto.pk}/eta"
    assert (
        _client(ragazza).put(url, {"eta_minima": 11}, content_type="application/json").status_code
        == 403
    )
    assert _client(capo).put(url, {"eta_minima": 11}, content_type="application/json").json() == {
        "eta_minima": 11,
        "eta_massima": 16,
    }
    sbagliato = {"eta_minima": 17, "eta_massima": 12}
    assert (
        _client(capogruppo).put(url, sbagliato, content_type="application/json").status_code == 400
    )
