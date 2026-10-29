"""Requests from data subjects: register, full export, erasure (DEC-102).

DEC-136: only the capigruppo export
and erase; JSON plus a readable page; erasure removes the app-only data and anonymises
an ex member, keeping the periods in units; a register of the requests.
"""

from datetime import date, timedelta

import pytest
from auditlog.models import LogEntry
from django.test import Client

from apps.accounts.models import User
from apps.anagrafica.models import (
    Appartenenza,
    DerogaSquadriglia,
    Persona,
    RelazioneTutela,
    VisibilitaGenitori,
)
from apps.permessi.models import AccessoDatoSensibile, Azione, Categoria
from apps.sanitaria.models import InformazioniSanitarie

pytestmark = pytest.mark.django_db


def _client(persona) -> Client:
    client = Client()
    client.force_login(persona.utente)
    return client


def _sanitarie(ragazza, genitore):
    _client(genitore).put(
        f"/api/v1/persone/{ragazza.pk}/sanitarie",
        {
            "allergie": [{"tipo": "ALLERGIA", "sostanza": "Arachidi", "gravita": "GRAVE"}],
            "esigenze_alimentari": "Vegetariana",
        },
        content_type="application/json",
    )


def test_solo_i_capigruppo(ragazza, capo, genitore, csq, estraneo):
    for chi in (capo, genitore, csq, estraneo, ragazza):
        client = _client(chi)
        assert client.get(f"/api/v1/persone/{ragazza.pk}/fascicolo").status_code == 403
        assert client.get("/api/v1/richieste-diritti").status_code == 403
        assert client.get(f"/api/v1/persone/{ragazza.pk}/cancellazione").status_code == 403


def test_fascicolo_completo_e_registrato(ragazza, genitore, capogruppo):
    ragazza.stato_socio = "R"
    ragazza.consenso_foto = True
    ragazza.save()
    _sanitarie(ragazza, genitore)
    risposta = _client(capogruppo).get(f"/api/v1/persone/{ragazza.pk}/fascicolo")
    assert risposta.status_code == 200
    dati = risposta.json()
    assert dati["anagrafica"]["Nome"] == "Giulia"
    assert dati["account"]["Email di accesso"] == "giulia@example.invalid"
    assert dati["genitori_e_tutori"] == [{"Nome": "Mario Genitore", "Relazione": "Genitore"}]
    assert dati["informazioni_sanitarie"]["Esigenze alimentari"] == "Vegetariana"
    assert "Aquile" in dati["squadriglie"][0]["Squadriglia"]
    assert dati["anagrafica"]["Stato del socio"] == "Rinnovo adesione"
    assert dati["anagrafica"]["Consenso per le foto (2B)"] is True
    assert any(a["Azione"] == "Modifica" for a in dati["accessi_ai_dati_delicati"])
    assert AccessoDatoSensibile.objects.filter(
        persona=ragazza, categoria=Categoria.FASCICOLO, azione=Azione.ESPORTAZIONE
    ).exists()


def test_registro_delle_richieste(ragazza, capogruppo):
    client = _client(capogruppo)
    oggi = date.today()
    creata = client.post(
        "/api/v1/richieste-diritti",
        {
            "persona_id": ragazza.pk,
            "tipo": "ACCESSO",
            "richiedente": "La madre, via email",
            "ricevuta_il": oggi.isoformat(),
        },
        content_type="application/json",
    )
    assert creata.status_code == 201
    richiesta = creata.json()
    assert richiesta["scadenza"] == (oggi + timedelta(days=30)).isoformat()

    url = f"/api/v1/richieste-diritti/{richiesta['id']}"
    aggiornata = client.patch(
        url, {"inoltrata_nazionale_il": oggi.isoformat()}, content_type="application/json"
    )
    assert aggiornata.json()["inoltrata_nazionale_il"] == oggi.isoformat()
    ieri = (oggi - timedelta(days=1)).isoformat()
    assert client.patch(url, {"evasa_il": ieri}, content_type="application/json").status_code == 400
    domani = (oggi + timedelta(days=1)).isoformat()
    futura = client.post(
        "/api/v1/richieste-diritti",
        {"persona_id": ragazza.pk, "tipo": "ACCESSO", "richiedente": "x", "ricevuta_il": domani},
        content_type="application/json",
    )
    assert futura.status_code == 400


def test_cancellazione_di_un_socio_tiene_l_anagrafica(ragazza, genitore, capogruppo, reparto):
    _sanitarie(ragazza, genitore)
    VisibilitaGenitori.objects.create(persona=ragazza)
    DerogaSquadriglia.objects.create(
        persona=ragazza,
        reparto=reparto,
        sesso_squadriglia="M",
        data_decisione=date.today(),
        motivazione="Decisione della Co.Ca.",
    )
    client = _client(capogruppo)
    url = f"/api/v1/persone/{ragazza.pk}/cancellazione"
    anteprima = client.get(url).json()
    assert anteprima["anonimizza"] is False
    assert "socio" in anteprima["motivo_anagrafica"]

    assert client.post(url, {"cognome": "Sbagliato"}, "application/json").status_code == 400
    assert client.post(url, {"cognome": "esploratrice"}, "application/json").status_code == 200

    ragazza.refresh_from_db()
    assert ragazza.nome == "Giulia" and ragazza.utente is None
    assert not User.objects.filter(email="giulia@example.invalid").exists()
    assert not InformazioniSanitarie.objects.filter(persona=ragazza).exists()
    assert not DerogaSquadriglia.objects.filter(persona=ragazza).exists()
    assert not VisibilitaGenitori.objects.filter(persona=ragazza).exists()
    assert AccessoDatoSensibile.objects.filter(
        persona=ragazza, azione=Azione.CANCELLAZIONE
    ).exists()
    assert not LogEntry.objects.filter(
        content_type__model="informazionisanitarie", changes_text__icontains="Vegetariana"
    ).exists()


def test_cancellazione_di_un_ex_socio_anonimizza(ragazza, genitore, capogruppo):
    Appartenenza.objects.filter(persona=ragazza).update(data_fine=date.today())
    ragazza.appartenenze_squadriglia.update(data_fine=date.today())
    client = _client(capogruppo)
    url = f"/api/v1/persone/{ragazza.pk}/cancellazione"
    assert client.get(url).json()["anonimizza"] is True
    assert client.post(url, {"cognome": "Esploratrice"}, "application/json").status_code == 200

    persona = Persona.objects.get(pk=ragazza.pk)
    assert persona.nome == "Persona" and persona.cognome.startswith("cancellata")
    assert persona.codice_fiscale is None and persona.cellulare == "" and persona.email == ""
    assert persona.data_nascita is None
    assert not RelazioneTutela.objects.filter(minore=persona).exists()
    assert Appartenenza.objects.filter(persona=persona).exists()  # periods stay
    assert not LogEntry.objects.get_for_object(persona).exists()
    assert not LogEntry.objects.filter(object_repr__icontains="Esploratrice").exists()


def test_il_genitore_di_un_socio_non_si_anonimizza(ragazza, genitore, capogruppo):
    anteprima = _client(capogruppo).get(f"/api/v1/persone/{genitore.pk}/cancellazione").json()
    assert anteprima["anonimizza"] is False
    assert "genitore" in anteprima["motivo_anagrafica"]


def test_non_cancella_se_stesso(capogruppo):
    url = f"/api/v1/persone/{capogruppo.pk}/cancellazione"
    risposta = _client(capogruppo).post(url, {"cognome": "Gruppo"}, "application/json")
    assert risposta.status_code == 400
