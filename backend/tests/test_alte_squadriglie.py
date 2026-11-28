"""The Alta Squadriglia with a name (DEC-440): one open per reparto or pair of linked reparti,
renamed by the staff, closed for good with its history, a new one empty with copies of the
old one's entries."""

from datetime import date, timedelta

import pytest
from django.core.files.base import ContentFile
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import Client

from apps.anagrafica.models import Persona
from apps.cerimonie.models import AllegatoVoce, AmbitoVoce, PartecipazioneVoce, VoceLibro
from apps.eventi import servizi
from apps.eventi.models import AltaSquadriglia, MembroAltaSquadriglia
from apps.impostazioni import funzioni
from apps.organizzazione.models import Composizione, TipoUnita, Unita

pytestmark = pytest.mark.django_db

OGGI = date.today()


def _client(chi: Persona) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


def _url(reparto, dopo: str = "") -> str:
    return f"/api/v1/unita/{reparto.pk}/alta-squadriglia{dopo}"


def _titoli(chi) -> set[str]:
    return {v["titolo"] for v in _client(chi).get("/api/v1/cerimonie").json()["voci"]}


def test_crea_rinomina_chiudi(capo, ragazza, csq, reparto, gruppo):
    client = _client(capo)
    alta = client.get(_url(reparto)).json()
    assert alta["alta"] is None and alta["candidati"] == []
    # Nobody enters one that does not exist.
    risposta = client.post(
        _url(reparto, "/ingresso"), {"persone": [ragazza.pk]}, "application/json"
    )
    assert risposta.status_code == 400
    alta = client.post(_url(reparto), {"nome": "Aquile Randagie"}, "application/json").json()
    assert alta["alta"]["titolo"] == "Alta Squadriglia «Aquile Randagie»"
    # One open at a time, also for the linked reparto.
    altro = Unita.objects.create(
        gruppo=gruppo, nome="Altro", tipo=TipoUnita.REPARTO, composizione=Composizione.MISTA
    )
    reparto.collegata_a, altro.collegata_a = altro, reparto
    reparto.save()
    altro.save()
    risposta = client.post(_url(altro), {"nome": "Seconda"}, "application/json")
    assert risposta.status_code == 400
    # Renamed when the staff likes.
    alta = client.put(_url(altro), {"nome": "Alta Squadriglia Orsa"}, "application/json").json()
    assert alta["alta"]["titolo"] == "Alta Squadriglia Orsa"
    assert client.put(_url(reparto), {"nome": "  "}, "application/json").status_code == 400
    # Closed: who was in leaves and stays in its history; the antechamber empties.
    servizi.fai_entrare(reparto, [csq], OGGI - timedelta(days=30))
    servizi.metti_in_anticamera(reparto, [ragazza])
    alta = client.post(_url(reparto, "/chiudi")).json()
    assert alta["alta"] is None and alta["entrati"] == [] and alta["anticamera"] == []
    [chiusa] = alta["chiuse"]
    assert chiusa["titolo"] == "Alta Squadriglia Orsa" and chiusa["chiusa_il"] == OGGI.isoformat()
    assert [(m["persona_id"], m["al"]) for m in chiusa["membri"]] == [(csq.pk, OGGI.isoformat())]
    assert not MembroAltaSquadriglia.objects.filter(persona=ragazza).exists()
    # The new one starts empty.
    alta = client.post(_url(reparto), {"nome": "Lupi"}, "application/json").json()
    assert alta["entrati"] == [] and {c["persona_id"] for c in alta["candidati"]} == {
        ragazza.pk,
        csq.pk,
    }
    # Only the reparto staff.
    assert _client(csq).post(_url(reparto, "/chiudi")).status_code == 403


def test_voci_della_vecchia_e_copie(capo, ragazza, csq, reparto):
    funzioni.imposta(funzioni.CERIMONIE, True)
    vecchia = servizi.crea_alta(reparto, "Aquile Randagie")
    ingresso = VoceLibro.objects.create(
        titolo="Ingresso",
        ambito=AmbitoVoce.ALTA_SQUADRIGLIA,
        alta=vecchia,
        cerimonia_ingresso_alta=True,
        testo="<p>Il fuoco</p>",
        condizioni=[[{"tipo": "alta_squadriglia", "alta": vecchia.pk}]],
    )
    ingresso.aggiunti.add(ragazza)
    AllegatoVoce.objects.create(
        voce=ingresso,
        titolo="Il canto",
        tipo_file="application/pdf",
        file=ContentFile(b"%PDF-1.4 prova", name="canto.pdf"),
    )
    notte = VoceLibro.objects.create(
        titolo="Notte", ambito=AmbitoVoce.ALTA_SQUADRIGLIA, alta=vecchia
    )
    servizi.fai_entrare(reparto, [csq], OGGI - timedelta(days=30))
    PartecipazioneVoce.objects.create(voce=notte, persona=csq, data=OGGI)
    assert {"Ingresso", "Notte"} <= _titoli(csq)
    servizi.chiudi_alta(vecchia)
    vecchia.refresh_from_db()
    # Who lived them still reads them; the condition holds for nobody any more.
    ingresso.aggiunti.clear()
    assert _titoli(csq) == {"Ingresso", "Notte"}
    assert _titoli(ragazza) == set()
    voce = _client(capo).get(f"/api/v1/cerimonie/{ingresso.pk}").json()
    assert voce["unita"] == "Alta Squadriglia «Aquile Randagie» (chiusa)"
    # The new one, copying the entry ceremony.
    alta = _client(capo).get(_url(reparto)).json()
    assert {v["titolo"] for v in alta["da_copiare"]} == {"Ingresso", "Notte"}
    alta = (
        _client(capo)
        .post(_url(reparto), {"nome": "Lupi", "copia": [ingresso.pk]}, "application/json")
        .json()
    )
    nuova = AltaSquadriglia.objects.get(pk=alta["alta"]["id"])
    copia = VoceLibro.objects.get(alta=nuova)
    assert copia.titolo == "Ingresso" and copia.testo == "<p>Il fuoco</p>"
    assert copia.cerimonia_ingresso_alta
    assert copia.condizioni == [[{"tipo": "alta_squadriglia", "alta": nuova.pk}]]
    assert not copia.partecipazioni.exists() and not copia.aggiunti.exists()
    [allegato] = copia.allegati.all()
    assert allegato.titolo == "Il canto" and allegato.file.read() == b"%PDF-1.4 prova"
    assert allegato.file.name != ingresso.allegati.get().file.name
    # The old one is as it was.
    ingresso.refresh_from_db()
    assert ingresso.cerimonia_ingresso_alta and ingresso.alta == vecchia
    assert alta["cerimonia"] == copia.pk
    # Marked in the old ceremony nobody enters the closed one.
    _client(capo).post(
        f"/api/v1/cerimonie/{ingresso.pk}/partecipanti",
        {"persone": [ragazza.pk], "data": OGGI.isoformat()},
        "application/json",
    )
    assert not MembroAltaSquadriglia.objects.filter(persona=ragazza).exists()


def test_voce_solo_dell_alta_aperta(capo, reparto):
    funzioni.imposta(funzioni.CERIMONIE, True)
    vecchia = servizi.crea_alta(reparto, "Vecchia")
    servizi.chiudi_alta(vecchia)
    nuova = servizi.crea_alta(reparto, "Nuova")
    libro = _client(capo).get("/api/v1/cerimonie").json()
    assert [a["id"] for a in libro["alte"]] == [nuova.pk]
    assert {a["id"] for a in libro["alte_condizioni"]} == {vecchia.pk, nuova.pk}
    risposta = _client(capo).post(
        "/api/v1/cerimonie",
        {"titolo": "x", "tipo": "CERIMONIA", "ambito": "ALTA_SQ", "alta_id": vecchia.pk},
        "application/json",
    )
    assert risposta.status_code == 400


def test_titolo_delle_riunioni(capo, reparto):
    from apps.eventi.models import Cerchia, RiunioneRicorrente

    servizi.crea_alta(reparto, "Aquile Randagie")
    serie = RiunioneRicorrente(unita=reparto, cerchia=Cerchia.ALTA_SQUADRIGLIA)
    assert servizi.titolo_riunione(serie) == "Alta Squadriglia «Aquile Randagie»"


@pytest.mark.django_db(transaction=True)
def test_migrazione_ad_alte_con_nome(reparto, ragazza, gruppo):
    """What there was becomes the open Alta Squadriglia «Alta Squadriglia» of each reparto, two
    linked ones sharing it, with its periods; the entries and conditions follow."""
    altro = Unita.objects.create(
        gruppo=gruppo, nome="Altro", tipo=TipoUnita.REPARTO, composizione=Composizione.MISTA
    )
    reparto.collegata_a, altro.collegata_a = altro, reparto
    reparto.save()
    altro.save()
    prima = [
        ("eventi", "0016_alta_squadriglia_senza_anno"),
        ("cerimonie", "0008_cerimonia_ingresso_alta"),
    ]
    executor = MigrationExecutor(connection)
    executor.migrate(prima)
    vecchie = executor.loader.project_state(prima).apps
    Membro = vecchie.get_model("eventi", "MembroAltaSquadriglia")
    Voce = vecchie.get_model("cerimonie", "VoceLibro")
    Membro.objects.create(reparto_id=altro.pk, persona_id=ragazza.pk, data_inizio=date(2024, 10, 1))
    voce = Voce.objects.create(
        titolo="Notte",
        ambito="ALTA_SQ",
        condizioni=[[{"tipo": "alta_squadriglia", "unita": altro.pk}]],
    )
    voce.unita.add(altro.pk)
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(executor.loader.graph.leaf_nodes())
    [alta] = AltaSquadriglia.objects.all()
    assert alta.nome == "Alta Squadriglia" and alta.chiusa_il is None
    assert alta.aperta_il == date(2024, 10, 1)
    assert MembroAltaSquadriglia.objects.get(persona=ragazza).alta == alta
    notte = VoceLibro.objects.get(titolo="Notte")
    assert notte.alta == alta and not notte.unita.exists()
    assert notte.condizioni == [[{"tipo": "alta_squadriglia", "alta": alta.pk}]]
