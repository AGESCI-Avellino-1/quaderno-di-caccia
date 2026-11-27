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


# --- Conditions (block 2) --------------------------------------------------------------------


def _con_condizioni(voce, gruppi):
    voce.condizioni = gruppi
    voce.save()
    return voce


def test_condizioni_di_unita_e_branca(ragazza, lupetto, reparto, branco, voci):
    _con_condizioni(voci["reparto"], [[{"tipo": "unita", "unita": reparto.pk}]])
    _con_condizioni(voci["branco"], [[{"tipo": "branca", "branca": "LC"}]])
    assert _titoli(ragazza) == {"Alta Squadriglia"}
    assert _titoli(lupetto) == {"Passaggio dal branco"}


def test_dentro_un_gruppo_tutte_tra_i_gruppi_una(ragazza, csq, lupetto, reparto, voci):
    # The CSQ of the reparto, or anyone in the branco.
    _con_condizioni(
        voci["gruppo"],
        [
            [{"tipo": "unita", "unita": reparto.pk}, {"tipo": "incarico", "ruolo": "CSQ"}],
            [{"tipo": "branca", "branca": "LC"}],
        ],
    )
    assert "Fuoco di gruppo" in _titoli(csq)
    assert "Fuoco di gruppo" in _titoli(lupetto)
    assert "Fuoco di gruppo" not in _titoli(ragazza)


def test_consiglio_capi_e_alta_squadriglia(ragazza, csq, reparto, squadriglia, voci):
    from apps.anagrafica.models import AppartenenzaSquadriglia
    from apps.core.anno import AnnoAssociativo
    from apps.eventi.models import MembroAltaSquadriglia
    from apps.organizzazione.models import EquiparazioneCsq

    _con_condizioni(voci["reparto"], [[{"tipo": "consiglio_capi"}]])
    _con_condizioni(voci["gruppo"], [[{"tipo": "alta_squadriglia"}]])
    assert _titoli(csq) == {"Alta Squadriglia"}
    assert _titoli(ragazza) == set()
    # Treated as the CSQ (DEC-419) and in this year's Alta Squadriglia.
    EquiparazioneCsq.objects.create(
        appartenenza=AppartenenzaSquadriglia.objects.get(persona=ragazza),
        data_inizio=INIZIO_ANNO,
        data_fine=AnnoAssociativo.corrente().fine.replace(day=30),
    )
    MembroAltaSquadriglia.objects.create(
        reparto=reparto, persona=ragazza, anno=AnnoAssociativo.corrente().anno_fine
    )
    assert _titoli(ragazza) == {"Alta Squadriglia", "Fuoco di gruppo"}
    # Last year's Alta Squadriglia does not count.
    MembroAltaSquadriglia.objects.filter(persona=ragazza).update(
        anno=AnnoAssociativo.corrente().anno_fine - 1
    )
    assert _titoli(ragazza) == {"Alta Squadriglia"}


def test_totem(ragazza, csq, voci):
    _con_condizioni(voci["gruppo"], [[{"tipo": "totem"}]])
    tribu.assegna(ragazza, "Castoro Operoso")
    assert _titoli(ragazza) == {"Fuoco di gruppo"}
    assert _titoli(csq) == set()


def test_passaggio_dalla_proposta_per_sempre(lupetto, branco, reparto, voci):
    from apps.progressione.models import Passaggio, PassaggioPersona, StatoPassaggio

    _con_condizioni(voci["branco"], [[{"tipo": "passaggio", "da": "LC", "a": "EG"}]])
    assert _titoli(lupetto) == set()
    passaggio = Passaggio.objects.create(
        unita_origine=branco, unita_destinazione=reparto, data=date.today()
    )
    parte = PassaggioPersona.objects.create(passaggio=passaggio, persona=lupetto)
    assert _titoli(lupetto) == {"Passaggio dal branco"}
    passaggio.stato = StatoPassaggio.ESEGUITO
    passaggio.save()
    assert _titoli(lupetto) == {"Passaggio dal branco"}
    # Their part cancelled after the execution, or the whole passage cancelled: no more.
    parte.rettificata_il = parte.creato_il
    parte.save()
    assert _titoli(lupetto) == set()
    parte.rettificata_il = None
    parte.save()
    passaggio.stato = StatoPassaggio.ANNULLATO
    passaggio.save()
    assert _titoli(lupetto) == set()


def test_progressione(ragazza, csq, voci):
    from apps.progressione.models import (
        Conclusione,
        Fase,
        PeriodoBranca,
        Promessa,
        Tappa,
        TipoConclusione,
    )

    _con_condizioni(voci["gruppo"], [[{"tipo": "promessa"}]])
    _con_condizioni(voci["reparto"], [[{"tipo": "tappa", "branca": "EG", "fase": "COMPETENZA"}]])
    _con_condizioni(voci["branco"], [[{"tipo": "partenza"}]])
    periodo = PeriodoBranca.objects.create(persona=ragazza, branca="EG", data_inizio=INIZIO_ANNO)
    scoperta = Tappa.objects.create(periodo=periodo, fase=Fase.SCOPERTA, data_inizio=INIZIO_ANNO)
    assert _titoli(ragazza) == set()
    Promessa.objects.create(periodo=periodo, data=INIZIO_ANNO)
    scoperta.data_fine = date.today()
    scoperta.save()
    Tappa.objects.create(periodo=periodo, fase=Fase.RESPONSABILITA, data_inizio=date.today())
    # Reached: Responsabilità is past Competenza.
    assert _titoli(ragazza) == {"Fuoco di gruppo", "Alta Squadriglia"}
    # A tappa of another branch does not count.
    altro = PeriodoBranca.objects.create(persona=csq, branca="LC", data_inizio=INIZIO_ANNO)
    Tappa.objects.create(periodo=altro, fase=Fase.RESPONSABILITA, data_inizio=INIZIO_ANNO)
    assert "Alta Squadriglia" not in _titoli(csq)
    Conclusione.objects.create(periodo=altro, tipo=TipoConclusione.PARTENZA, data=date.today())
    assert "Passaggio dal branco" in _titoli(csq)


def test_condizioni_e_persone_aggiunte_insieme(ragazza, csq, lupetto, reparto, voci):
    _con_condizioni(voci["reparto"], [[{"tipo": "incarico", "ruolo": "CSQ"}]])
    voci["reparto"].aggiunti.add(lupetto)
    assert _titoli(csq) == {"Alta Squadriglia"}
    assert _titoli(lupetto) == {"Alta Squadriglia"}
    assert _titoli(ragazza) == set()


def test_condizioni_mai_ai_genitori_ne_a_chi_ha_lasciato(ragazza, genitore, voci, reparto):
    _con_condizioni(voci["reparto"], [[{"tipo": "unita", "unita": reparto.pk}]])
    assert _titoli(genitore) == set()
    Appartenenza.objects.filter(persona=ragazza).update(data_fine=date.today())
    assert _titoli(ragazza) == set()


def test_salvare_le_condizioni(capo, reparto, voci):
    client = _client(capo)
    condizioni = [
        [{"tipo": "unita", "unita": reparto.pk, "altro": 1}, {"tipo": "totem"}],
        [],
        [{"tipo": "tappa", "branca": "EG", "fase": "SCOPERTA"}, {"tipo": "totem"}],
    ]
    risposta = client.put(
        f"{URL}/{voci['reparto'].pk}",
        _dati(unita_id=reparto.pk, condizioni=condizioni),
        "application/json",
    )
    assert risposta.status_code == 200
    # Unknown fields and empty groups go.
    assert risposta.json()["condizioni"] == [
        [{"tipo": "unita", "unita": reparto.pk}, {"tipo": "totem"}],
        [{"tipo": "tappa", "branca": "EG", "fase": "SCOPERTA"}, {"tipo": "totem"}],
    ]
    for sbagliate in (
        [[{"tipo": "boh"}]],
        [[{"tipo": "unita", "unita": 99999}]],
        [[{"tipo": "branca", "branca": "COCA"}]],
        [[{"tipo": "incarico", "ruolo": "CAPOGRUPPO"}]],
        [[{"tipo": "passaggio", "da": "EG", "a": "EG"}]],
        [[{"tipo": "tappa", "branca": "EG", "fase": "BOH"}]],
        [[{"tipo": "totem"}]] * 11,
        "tutti",
    ):
        risposta = client.put(
            f"{URL}/{voci['reparto'].pk}",
            _dati(unita_id=reparto.pk, condizioni=sbagliate),
            "application/json",
        )
        assert risposta.status_code in (400, 422), sbagliate


def test_le_condizioni_solo_a_chi_scrive(capo, ragazza, reparto, voci):
    _con_condizioni(voci["reparto"], [[{"tipo": "unita", "unita": reparto.pk}]])
    assert _client(capo).get(f"{URL}/{voci['reparto'].pk}").json()["condizioni"]
    assert _client(ragazza).get(f"{URL}/{voci['reparto'].pk}").json()["condizioni"] == []
    libro = _client(capo).get(URL).json()
    assert reparto.pk in [u["id"] for u in libro["unita_condizioni"]]
    assert libro["incarichi"][0] == {"valore": "CSQ", "nome": "Capo squadriglia"}
    assert _client(ragazza).get(URL).json()["incarichi"] == []


def test_anteprima(capo, ragazza, csq, lupetto, estraneo, voci):
    client = _client(capo)
    risposta = client.post(
        f"{URL}/anteprima",
        {"condizioni": [[{"tipo": "incarico", "ruolo": "CSQ"}]], "aggiunti": [lupetto.pk]},
        "application/json",
    )
    assert risposta.status_code == 200
    assert {p["nome"] for p in risposta.json()} == {"Sara", "Lupo"}
    assert (
        client.post(
            f"{URL}/anteprima", {"condizioni": [[{"tipo": "boh"}]]}, "application/json"
        ).status_code
        == 400
    )
    assert _client(ragazza).post(f"{URL}/anteprima", {}, "application/json").status_code == 403
    assert _client(estraneo).post(f"{URL}/anteprima", {}, "application/json").status_code == 403


# --- The register of who lived an entry (block 3) --------------------------------------------


def _segna(chi, voce, persone, giorno=None):
    return _client(chi).post(
        f"{URL}/{voce.pk}/partecipanti",
        {"persone": [p.pk for p in persone], "data": str(giorno or date.today())},
        "application/json",
    )


def test_segnare_e_togliere_dal_registro(capo, csq, ragazza, voci):
    from datetime import timedelta

    passato = date.today() - timedelta(days=400)
    risposta = _segna(capo, voci["reparto"], [csq, capo], passato)
    assert risposta.status_code == 200
    registro = risposta.json()["partecipanti"]
    assert {(p["nome"], p["data"]) for p in registro} == {
        ("Sara", str(passato)),
        ("Anna", str(passato)),
    }
    # Marked again: the new day.
    _segna(capo, voci["reparto"], [csq])
    voce = _client(capo).get(f"{URL}/{voci['reparto'].pk}").json()
    assert {p["nome"]: p["data"] for p in voce["partecipanti"]}["Sara"] == str(date.today())
    risposta = _client(capo).delete(f"{URL}/{voci['reparto'].pk}/partecipanti/{csq.pk}")
    assert [p["nome"] for p in risposta.json()["partecipanti"]] == ["Anna"]


def test_registro_errori(capo, genitore, estraneo, voci):
    from datetime import timedelta

    assert _segna(capo, voci["reparto"], [genitore]).status_code == 400
    assert _segna(capo, voci["reparto"], [estraneo]).status_code == 400
    assert _segna(capo, voci["reparto"], []).status_code == 400
    domani = date.today() + timedelta(days=1)
    assert _segna(capo, voci["reparto"], [capo], domani).status_code == 400


def test_chi_segna(capo, capogruppo, ragazza, csq, voci):
    # The staff of the reparto: not the branco's register.
    assert _segna(capo, voci["branco"], [ragazza]).status_code == 403
    assert _segna(capogruppo, voci["branco"], [ragazza]).status_code == 200
    voci["reparto"].aggiunti.add(csq)
    # A ragazzo/a who reads the entry does not mark it.
    assert _segna(csq, voci["reparto"], [csq]).status_code == 403
    assert _client(csq).get(f"{URL}/segnabili").status_code == 403
    nomi = {p["nome"] for p in _client(capo).get(f"{URL}/segnabili").json()}
    # Ragazzi/e and capi, the active ones.
    assert {"Giulia", "Sara", "Anna", "Bruno"} <= nomi


def test_chi_legge_il_registro(capo, ragazza, csq, voci):
    voci["reparto"].aggiunti.add(ragazza, csq)
    _segna(capo, voci["reparto"], [csq, capo])
    # Every capo; a participant, the others; who reads the entry but was not there, nobody.
    assert _client(capo).get(f"{URL}/{voci['reparto'].pk}").json()["vede_registro"]
    letta = _client(csq).get(f"{URL}/{voci['reparto'].pk}").json()
    assert letta["vede_registro"] and {p["nome"] for p in letta["partecipanti"]} == {"Sara", "Anna"}
    letta = _client(ragazza).get(f"{URL}/{voci['reparto'].pk}").json()
    assert not letta["vede_registro"] and letta["partecipanti"] == []


def test_condizione_partecipazione(capo, ragazza, csq, voci):
    _con_condizioni(voci["gruppo"], [[{"tipo": "partecipazione", "voce": voci["reparto"].pk}]])
    assert _titoli(csq) == set()
    _segna(capo, voci["reparto"], [csq])
    # The register opens the entry it records; the condition opens the other.
    assert _titoli(csq) == {"Alta Squadriglia", "Fuoco di gruppo"}
    assert _titoli(ragazza) == set()
    risposta = _client(capo).put(
        f"{URL}/{voci['reparto'].pk}",
        _dati(
            condizioni=[[{"tipo": "partecipazione", "voce": 99999}]],
            unita_id=voci["reparto"].unita_id,
        ),
        "application/json",
    )
    assert risposta.status_code == 400


def test_registro_e_diritti(capo, csq, voci):
    _segna(capo, voci["reparto"], [csq])
    assert diritti.fascicolo(csq)["cerimonie_vissute"][0]["Voce"] == "Alta Squadriglia"
    diritti.cancella(csq)
    assert not voci["reparto"].partecipazioni.exists()


def test_chi_lascia_resta_nel_registro(capo, csq, voci):
    _segna(capo, voci["reparto"], [csq])
    Appartenenza.objects.filter(persona=csq).update(data_fine=date.today())
    nomi = [
        p["nome"] for p in _client(capo).get(f"{URL}/{voci['reparto'].pk}").json()["partecipanti"]
    ]
    assert nomi == ["Sara"]


def test_chi_e_nel_registro_legge_la_voce(capo, csq, ragazza, lupetto, voci):
    _segna(capo, voci["reparto"], [csq])
    # No condition, not added by hand: the register is enough (maintainer, 27/11).
    assert _titoli(csq) == {"Alta Squadriglia"}
    letta = _client(csq).get(f"{URL}/{voci['reparto'].pk}").json()
    assert letta["vede_registro"] and [p["nome"] for p in letta["partecipanti"]] == ["Sara"]
    assert _titoli(ragazza) == set()
    # The preview counts them for the entry being changed.
    risposta = _client(capo).post(
        f"{URL}/anteprima",
        {"condizioni": [], "aggiunti": [lupetto.pk], "voce_id": voci["reparto"].pk},
        "application/json",
    )
    assert {p["nome"] for p in risposta.json()} == {"Sara", "Lupo"}
    # Who left no longer reads it, though still in the register.
    Appartenenza.objects.filter(persona=csq).update(data_fine=date.today())
    assert _titoli(csq) == set()


# --- Block 4: attachments ----------------------------------------------------------------


def _carica(chi, voce, contenuto=b"%PDF-1.4 prova", titolo="Testo del canto"):
    from django.core.files.uploadedfile import SimpleUploadedFile

    file = SimpleUploadedFile("canto di Giulia.pdf", contenuto)
    return _client(chi).post(f"{URL}/{voce.pk}/allegati", {"titolo": titolo, "file": file})


def test_allegati_letti_da_chi_legge_la_voce(
    capo, capogruppo, ragazza, csq, genitore, estraneo, voci, settings, tmp_path
):
    settings.MEDIA_ROOT = tmp_path
    risposta = _carica(capo, voci["reparto"])
    assert risposta.status_code == 201
    allegato = risposta.json()["allegati"][0]
    assert allegato["titolo"] == "Testo del canto" and allegato["tipo_file"] == "application/pdf"
    url = f"/api/v1/allegati-voce/{allegato['id']}"
    voci["reparto"].aggiunti.add(ragazza)
    for chi in (capo, capogruppo, ragazza):
        letto = _client(chi).get(url)
        assert letto.status_code == 200 and letto.content.startswith(b"%PDF")
    # The original name may carry a person's: not kept.
    assert "Giulia" not in letto["Content-Disposition"]
    assert letto["Cache-Control"] == "private, no-store"
    # Who does not read the entry: not even that it exists.
    for chi in (csq, genitore, estraneo):
        assert _client(chi).get(url).status_code == 404
    assert _client(ragazza).get(f"{URL}/{voci['reparto'].pk}").json()["allegati"]


def test_chi_carica_e_toglie_gli_allegati(capo, capogruppo, ragazza, voci, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    voci["branco"].aggiunti.add(ragazza)
    # The staff of the reparto, not the branco's; a reader never.
    assert _carica(capo, voci["branco"]).status_code == 403
    assert _carica(ragazza, voci["branco"]).status_code == 403
    allegato = _carica(capogruppo, voci["branco"]).json()["allegati"][0]
    url = f"/api/v1/allegati-voce/{allegato['id']}"
    assert _client(ragazza).delete(url).status_code == 403
    assert _client(capo).delete(url).status_code == 403
    risposta = _client(capogruppo).delete(url)
    assert risposta.status_code == 200 and risposta.json()["allegati"] == []
    assert not list(tmp_path.rglob("*.pdf"))


def test_allegati_errori(capo, voci, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    assert _carica(capo, voci["reparto"], b"MZ non un pdf").status_code == 400
    assert _carica(capo, voci["reparto"], titolo="  ").status_code == 400
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 20
    assert _carica(capo, voci["reparto"], png).json()["allegati"][0]["tipo_file"] == "image/png"


def test_allegati_via_con_la_voce_e_con_la_funzione(capo, voci, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    allegato = _carica(capo, voci["reparto"]).json()["allegati"][0]
    funzioni.imposta(funzioni.CERIMONIE, False)
    assert _client(capo).get(f"/api/v1/allegati-voce/{allegato['id']}").status_code == 404
    _accendi()
    assert _client(capo).delete(f"{URL}/{voci['reparto'].pk}").status_code == 204
    assert not list(tmp_path.rglob("*.pdf"))
