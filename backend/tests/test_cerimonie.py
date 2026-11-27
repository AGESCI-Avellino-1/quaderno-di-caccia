"""The book of ceremonies and traditions, block 1 (DEC-437): entries of the group or of a unit,
read by every capo and by the ragazzi/e added by hand; the totem ceremony moved into it."""

from datetime import date

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import Client

from apps.anagrafica.models import Appartenenza, Persona, RuoloAppartenenza
from apps.cerimonie.models import TipoVoce, VoceLibro
from apps.diritti import servizi as diritti
from apps.impostazioni import funzioni
from apps.organizzazione.models import Composizione, Incarico, RuoloIncarico, TipoUnita, Unita
from apps.permessi import policy
from apps.tribu import servizi as tribu
from tests.conftest import INIZIO_ANNO, crea_persona, nato_anni_fa

pytestmark = pytest.mark.django_db

URL = "/api/v1/cerimonie"


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente if isinstance(chi, Persona) else chi)
    return client


def _accendi() -> None:
    funzioni.imposta(funzioni.CERIMONIE, True)


@pytest.fixture
def branco(gruppo) -> Unita:
    return Unita.objects.create(
        gruppo=gruppo, nome="Branco Prova", tipo=TipoUnita.BRANCO, composizione=Composizione.MISTA
    )


@pytest.fixture
def lupetto(branco) -> Persona:
    persona = crea_persona("Lupo", "Prova", "lupo@example.invalid", data_nascita=nato_anni_fa(9))
    Appartenenza.objects.create(
        persona=persona, unita=branco, ruolo=RuoloAppartenenza.RAGAZZO, data_inizio=INIZIO_ANNO
    )
    return persona


@pytest.fixture
def voci(reparto, branco):
    _accendi()
    gruppo = VoceLibro.objects.create(titolo="Fuoco di gruppo", testo="<p>Il fuoco</p>")
    del_reparto = VoceLibro.objects.create(
        titolo="Alta Squadriglia", unita=reparto, testo="<p>La notte</p>"
    )
    del_branco = VoceLibro.objects.create(
        titolo="Passaggio dal branco", tipo=TipoVoce.TRADIZIONE, unita=branco
    )
    return {"gruppo": gruppo, "reparto": del_reparto, "branco": del_branco}


def _titoli(chi) -> set[str]:
    return {v["titolo"] for v in _client(chi).get(URL).json()["voci"]}


def _dati(**campi) -> dict:
    return {"titolo": "Nuova", "tipo": "CERIMONIA", "unita_id": None, "testo": "", **campi}


# --- Who reads -------------------------------------------------------------------------------


def test_i_capi_leggono_tutto(capo, capogruppo, voci):
    tutte = {"Fuoco di gruppo", "Alta Squadriglia", "Passaggio dal branco"}
    assert _titoli(capo) == tutte
    assert _titoli(capogruppo) == tutte
    risposta = _client(capo).get(f"{URL}/{voci['branco'].pk}")
    assert risposta.status_code == 200 and risposta.json()["tipo"] == "TRADIZIONE"


def test_anche_il_capo_in_attesa_legge_tutto(capo, voci):
    capo.codice_socio = "9000000001"
    capo.save()
    assert policy.e_capo_in_attesa(capo.utente)
    assert len(_titoli(capo)) == 3
    # But writes nothing, as for the other staff checks.
    assert not policy.puo_scrivere_voci(capo.utente)


def test_i_ragazzi_solo_le_voci_a_cui_sono_aggiunti(ragazza, csq, lupetto, voci):
    for chi in (ragazza, csq, lupetto):
        assert _titoli(chi) == set()
        assert _client(chi).get(f"{URL}/{voci['reparto'].pk}").status_code == 404
    voci["reparto"].aggiunti.add(csq)
    voci["gruppo"].aggiunti.add(lupetto)
    assert _titoli(csq) == {"Alta Squadriglia"}
    assert _titoli(lupetto) == {"Fuoco di gruppo"}
    assert _titoli(ragazza) == set()
    letta = _client(csq).get(f"{URL}/{voci['reparto'].pk}").json()
    assert letta["testo"] == "<p>La notte</p>"
    # Who else was added is for who writes the entry.
    assert letta["aggiunti"] == [] and letta["puo_modificare"] is False


def test_genitori_ed_estranei_mai(genitore, estraneo, ragazza, voci):
    voci["reparto"].aggiunti.add(ragazza)
    for chi in (genitore, estraneo):
        assert _titoli(chi) == set()
        assert _client(chi).get(f"{URL}/{voci['reparto'].pk}").status_code == 404
        assert not _client(chi).get("/api/v1/io").json()["cerimonie"]


def test_chi_lascia_il_gruppo_non_legge_piu(ragazza, voci):
    voci["reparto"].aggiunti.add(ragazza)
    assert _titoli(ragazza) == {"Alta Squadriglia"}
    Appartenenza.objects.filter(persona=ragazza).update(data_fine=date.today())
    assert _titoli(ragazza) == set()
    assert _client(ragazza).get(f"{URL}/{voci['reparto'].pk}/pdf").status_code == 404


def test_pdf(capo, voci):
    risposta = _client(capo).get(f"{URL}/{voci['reparto'].pk}/pdf")
    assert risposta.status_code == 200 and risposta.content.startswith(b"%PDF")
    assert 'filename="alta-squadriglia.pdf"' in risposta["Content-Disposition"]


def test_voce_di_menu(capo, ragazza, voci):
    assert _client(capo).get("/api/v1/io").json()["cerimonie"] is True
    assert _client(ragazza).get("/api/v1/io").json()["cerimonie"] is False
    voci["reparto"].aggiunti.add(ragazza)
    assert _client(ragazza).get("/api/v1/io").json()["cerimonie"] is True


def test_spenta_non_esiste(capo, capogruppo, voci):
    funzioni.imposta(funzioni.CERIMONIE, False)
    assert _client(capo).get(URL).status_code == 404
    assert _client(capo).get(f"{URL}/{voci['gruppo'].pk}").status_code == 404
    assert _client(capogruppo).post(URL, _dati(), "application/json").status_code == 404
    assert _client(capo).get("/api/v1/io").json()["cerimonie"] is False


# --- Who writes ------------------------------------------------------------------------------


def test_capogruppo_scrive_tutto(capogruppo, reparto, ragazza, voci):
    client = _client(capogruppo)
    risposta = client.post(
        URL,
        _dati(titolo="  Promessa   al  campo ", testo="<p>Ciao</p><script>x</script>"),
        "application/json",
    )
    assert risposta.status_code == 201
    nuova = risposta.json()
    assert nuova["titolo"] == "Promessa al campo" and nuova["testo"] == "<p>Ciao</p>"
    assert nuova["unita"] == "Tutto il gruppo" and nuova["puo_modificare"]
    risposta = client.put(
        f"{URL}/{nuova['id']}",
        _dati(titolo="Promessa", unita_id=reparto.pk, aggiunti=[ragazza.pk]),
        "application/json",
    )
    assert risposta.status_code == 200 and risposta.json()["aggiunti"] == [ragazza.pk]
    assert client.delete(f"{URL}/{voci['branco'].pk}").status_code == 204
    assert not VoceLibro.objects.filter(pk=voci["branco"].pk).exists()


def test_lo_staff_scrive_solo_le_voci_della_sua_unita(capo, reparto, branco, voci):
    client = _client(capo)
    # The capo unità of the reparto.
    assert (
        client.put(
            f"{URL}/{voci['reparto'].pk}", _dati(unita_id=reparto.pk), "application/json"
        ).json()["titolo"]
        == "Nuova"
    )
    assert client.post(URL, _dati(unita_id=reparto.pk), "application/json").status_code == 201
    # Not the group's, not the branco's, nor moving one there.
    for voce in (voci["gruppo"], voci["branco"]):
        assert client.put(f"{URL}/{voce.pk}", _dati(), "application/json").status_code == 403
        assert client.delete(f"{URL}/{voce.pk}").status_code == 403
    assert client.post(URL, _dati(), "application/json").status_code == 403
    assert client.post(URL, _dati(unita_id=branco.pk), "application/json").status_code == 403
    risposta = client.put(
        f"{URL}/{voci['reparto'].pk}", _dati(unita_id=branco.pk), "application/json"
    )
    assert risposta.status_code == 403
    libro = client.get(URL).json()
    assert libro["puo_scrivere"] and not libro["puo_tutto_il_gruppo"]
    assert [u["id"] for u in libro["unita"]] == [reparto.pk]


def test_unita_collegate(capo, reparto, gruppo, voci):
    altro = Unita.objects.create(
        gruppo=gruppo, nome="Altro", tipo=TipoUnita.REPARTO, composizione=Composizione.MISTA
    )
    reparto.collegata_a = altro
    reparto.save()
    altro.collegata_a = reparto
    altro.save()
    risposta = _client(capo).post(URL, _dati(unita_id=altro.pk), "application/json")
    assert risposta.status_code == 201


def test_chi_non_scrive(ragazza, csq, genitore, estraneo, voci, reparto, coca):
    # A capo with no service writes nothing either.
    senza = crea_persona("Senza", "Servizio", "senza@example.invalid")
    Appartenenza.objects.create(
        persona=senza,
        unita=coca,
        ruolo=RuoloAppartenenza.CAPO,
        data_inizio=INIZIO_ANNO,
    )
    for chi in (ragazza, csq, genitore, estraneo, senza):
        assert not policy.puo_scrivere_voci(chi.utente)
        client = _client(chi)
        assert client.post(URL, _dati(unita_id=reparto.pk), "application/json").status_code == 403
        assert client.get(f"{URL}/aggiungibili").status_code == 403
    # Capi read and do not change: the entry is there, not theirs.
    assert (
        _client(senza)
        .put(f"{URL}/{voci['reparto'].pk}", _dati(unita_id=reparto.pk), "application/json")
        .status_code
        == 403
    )
    # The others do not even know it exists.
    assert _client(ragazza).delete(f"{URL}/{voci['reparto'].pk}").status_code == 404


def test_errori(capogruppo, voci):
    client = _client(capogruppo)
    assert client.post(URL, _dati(titolo="  "), "application/json").status_code == 400
    assert client.post(URL, _dati(titolo="x" * 201), "application/json").status_code == 400
    assert client.post(URL, _dati(tipo="ALTRO"), "application/json").status_code == 400
    vuoto = client.post(URL, _dati(testo="<p> </p><p><br></p>"), "application/json")
    assert vuoto.json()["testo"] == ""


# --- Added by hand ---------------------------------------------------------------------------


def test_aggiungibili_i_ragazzi_attivi_di_tutto_il_gruppo(capo, capogruppo, ragazza, lupetto):
    _accendi()
    elenco = {p["nome"] for p in _client(capo).get(f"{URL}/aggiungibili").json()}
    # The capo unità of the reparto adds a lupetto too (a passage's tradition); no capo.
    assert elenco == {"Giulia", "Lupo"}
    assert elenco == {p["nome"] for p in _client(capogruppo).get(f"{URL}/aggiungibili").json()}


def test_non_si_aggiunge_chi_non_si_puo(capo, capogruppo, reparto, genitore, estraneo, voci):
    for chi in (genitore, estraneo, capogruppo):
        risposta = _client(capo).put(
            f"{URL}/{voci['reparto'].pk}",
            _dati(unita_id=reparto.pk, aggiunti=[chi.pk]),
            "application/json",
        )
        assert risposta.status_code == 400


def test_chi_e_gia_aggiunto_resta(capo, reparto, ragazza, voci):
    voci["reparto"].aggiunti.add(ragazza)
    Appartenenza.objects.filter(persona=ragazza).update(data_fine=date.today())
    # She left: changing the text keeps her, she just no longer reads it.
    risposta = _client(capo).put(
        f"{URL}/{voci['reparto'].pk}",
        _dati(titolo="Alta", unita_id=reparto.pk, aggiunti=[ragazza.pk]),
        "application/json",
    )
    assert risposta.status_code == 200


def test_diritti_degli_interessati(ragazza, voci):
    voci["reparto"].aggiunti.add(ragazza)
    assert diritti.fascicolo(ragazza)["cerimonie_e_tradizioni"] == ["Alta Squadriglia"]
    diritti.cancella(ragazza)
    assert not voci["reparto"].aggiunti.exists()
    assert VoceLibro.objects.filter(pk=voci["reparto"].pk).exists()


# --- The totem ceremony ----------------------------------------------------------------------


def test_la_mia_tribu_rimanda_alla_cerimonia(capo, ragazza):
    tribu.assegna(ragazza, "Castoro Operoso")
    voce = VoceLibro.objects.create(
        titolo="Cerimonia del totem", cerimonia_del_totem=True, testo="<p>Il fuoco</p>"
    )
    # Off: nothing.
    assert _client(capo).get("/api/v1/tribu").json()["cerimonia"] is None
    _accendi()
    assert _client(capo).get("/api/v1/tribu").json()["cerimonia"] == voce.pk
    # As before, never a ragazzo/a with a totem, unless added to the entry.
    assert _client(ragazza).get("/api/v1/tribu").json()["cerimonia"] is None
    voce.aggiunti.add(ragazza)
    assert _client(ragazza).get("/api/v1/tribu").json()["cerimonia"] == voce.pk


def test_impostazioni_senza_cerimonia(capogruppo):
    dati = _client(capogruppo).get("/api/v1/impostazioni").json()
    assert "cerimonia_totem" not in dati
    risposta = _client(capogruppo).put(
        "/api/v1/impostazioni/tribu", {"descrizione": "Noi"}, "application/json"
    )
    assert risposta.status_code == 200 and risposta.json()["descrizione_tribu"] == "Noi"


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("scritta", [True, False])
def test_migrazione_della_cerimonia_del_totem(scritta):
    prima = [("impostazioni", "0015_testo_auguri"), ("cerimonie", "0001_initial")]
    dopo = [
        ("impostazioni", "0016_senza_cerimonia_totem"),
        ("cerimonie", "0002_cerimonia_del_totem"),
    ]
    executor = MigrationExecutor(connection)
    executor.migrate(prima)
    vecchie = executor.loader.project_state(prima).apps
    Impostazioni = vecchie.get_model("impostazioni", "Impostazioni")
    imp = Impostazioni.objects.first() or Impostazioni.objects.create()
    imp.cerimonia_totem = "<p>Il fuoco</p>" if scritta else ""
    imp.funzioni_attive = []
    imp.save()
    executor = MigrationExecutor(connection)
    executor.migrate(dopo)
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())
    voce = VoceLibro.objects.filter(cerimonia_del_totem=True).first()
    if scritta:
        assert voce is not None and voce.testo == "<p>Il fuoco</p>" and voce.unita is None
        assert voce.titolo == "Cerimonia del totem" and not voce.aggiunti.exists()
        assert funzioni.attiva(funzioni.CERIMONIE)
    else:
        assert voce is None and not funzioni.attiva(funzioni.CERIMONIE)


def test_una_sola_cerimonia_del_totem(voci):
    from django.db import IntegrityError, transaction

    VoceLibro.objects.create(titolo="Totem", cerimonia_del_totem=True)
    with pytest.raises(IntegrityError), transaction.atomic():
        VoceLibro.objects.create(titolo="Altro totem", cerimonia_del_totem=True)


def test_ruoli_di_unita_dello_staff(capo, lupetto, branco, voci):
    # Appointed to the branco too: now writes its entries.
    Incarico.objects.create(
        persona=capo, ruolo=RuoloIncarico.STAFF, unita=branco, data_inizio=INIZIO_ANNO
    )
    assert policy.puo_scrivere_voce(capo.utente, voci["branco"])
    assert not policy.puo_scrivere_voce(capo.utente, voci["gruppo"])


def test_scegliere_la_cerimonia_del_totem(capogruppo, capo, reparto, voci):
    client = _client(capogruppo)
    vecchia = VoceLibro.objects.create(titolo="Vecchia", cerimonia_del_totem=True)
    risposta = client.put(
        f"{URL}/{voci['gruppo'].pk}", _dati(cerimonia_del_totem=True), "application/json"
    )
    assert risposta.status_code == 200 and risposta.json()["cerimonia_del_totem"]
    vecchia.refresh_from_db()
    assert not vecchia.cerimonia_del_totem
    # Only of the whole group, only by a capogruppo.
    assert (
        client.put(
            f"{URL}/{voci['gruppo'].pk}",
            _dati(unita_id=reparto.pk, cerimonia_del_totem=True),
            "application/json",
        ).status_code
        == 400
    )
    assert (
        _client(capo)
        .put(
            f"{URL}/{voci['reparto'].pk}",
            _dati(unita_id=reparto.pk, cerimonia_del_totem=True),
            "application/json",
        )
        .status_code
        == 403
    )
    # The staff changing its own entry leaves the flag as it is.
    assert (
        _client(capo)
        .put(f"{URL}/{voci['reparto'].pk}", _dati(unita_id=reparto.pk), "application/json")
        .status_code
        == 200
    )
