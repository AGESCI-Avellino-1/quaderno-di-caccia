"""Using the app as another user (DEC-167): who may, what is blocked, what
is recorded."""

from datetime import timedelta

import pytest
from auditlog.models import LogEntry
from django.test import Client
from django.utils import timezone

from apps.impersonazione.models import Impersonazione
from apps.permessi import policy
from apps.permessi.models import AccessoDatoSensibile
from tests.conftest import crea_capo, crea_persona

pytestmark = pytest.mark.django_db


@pytest.fixture
def altro_capo(coca):
    return crea_capo("Carlo", "Altro", "altro@example.invalid")


@pytest.fixture
def admin_non_capo(db):
    persona = crea_persona("Tecnico", "Admin", "admin@example.invalid")
    persona.utente.amministratore_tecnico = True
    persona.utente.save()
    return persona


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


def _inizia(client, chi, motivo="Non riesce a compilare la scheda"):
    return client.post(
        "/api/v1/impersonazione",
        {"persona_id": chi.pk, "motivo": motivo},
        content_type="application/json",
    )


def test_chi_puo_impersonare_chi(
    capo, capogruppo, altro_capo, admin_non_capo, ragazza, genitore, csq, estraneo
):
    puo = policy.puo_impersonare
    # Capigruppo: anyone with an account, other capi included.
    for chi in (capo, altro_capo, genitore, ragazza, estraneo, admin_non_capo):
        assert puo(capogruppo.utente, chi.utente)
    # Unit staff (capo is capo unità of the reparto): its ragazzi and their parents.
    for chi in (ragazza, csq, genitore):
        assert puo(capo.utente, chi.utente)
    for chi in (estraneo, capogruppo, altro_capo, admin_non_capo):
        assert not puo(capo.utente, chi.utente)
    # A capo serving no unit, a technical administrator who is not a capo (DEC-12).
    assert not puo(altro_capo.utente, ragazza.utente)
    assert not puo(admin_non_capo.utente, ragazza.utente)
    assert not policy.puo_impersonare_qualcuno(admin_non_capo.utente)
    # Never oneself, never the ragazzi and parents.
    assert not puo(capogruppo.utente, capogruppo.utente)
    assert not puo(genitore.utente, ragazza.utente)
    assert not puo(ragazza.utente, genitore.utente)


def test_l_admin_capo_impersona_chiunque(admin_non_capo, coca, capogruppo, estraneo):
    from apps.anagrafica.models import Appartenenza, RuoloAppartenenza
    from tests.conftest import INIZIO_ANNO

    Appartenenza.objects.create(
        persona=admin_non_capo, unita=coca, ruolo=RuoloAppartenenza.CAPO, data_inizio=INIZIO_ANNO
    )
    assert policy.puo_impersonare(admin_non_capo.utente, capogruppo.utente)
    assert policy.puo_impersonare(admin_non_capo.utente, estraneo.utente)


def test_l_app_si_usa_come_l_altro_e_si_torna_a_se(capo, genitore, ragazza):
    client = _client(capo)
    assert _inizia(client, genitore, motivo=" ").status_code == 400
    risposta = _inizia(client, genitore)
    assert risposta.status_code == 201
    io = client.get("/api/v1/io").json()
    assert io["persona"]["id"] == genitore.pk
    assert io["impersonazione"]["impersonato"] == "Mario Genitore"
    assert io["capo"] is False  # what the parent sees, nothing more
    assert client.get("/api/v1/eventi").status_code == 200
    assert client.post("/api/v1/impersonazione/fine").status_code == 200
    io = client.get("/api/v1/io").json()
    assert io["persona"]["id"] == capo.pk and io["impersonazione"] is None
    assert Impersonazione.objects.get().finita_il is not None


def test_account_e_scelte_personali_sono_bloccati(capogruppo, genitore, ragazza):
    client = _client(capogruppo)
    _inizia(client, genitore)
    bloccate = [
        client.put("/api/v1/io/email", {}, content_type="application/json"),
        client.get("/api/v1/dispositivi"),
        client.get("/api/v1/calendario"),
        client.put(
            f"/api/v1/persone/{ragazza.pk}/visibilita-genitori",
            {},
            content_type="application/json",
        ),
        client.post(
            "/_allauth/browser/v1/account/password/change",
            {"current_password": "x", "new_password": "y"},
            content_type="application/json",
        ),
        client.get("/admin/"),
        _inizia(client, ragazza),  # never nested
    ]
    for risposta in bloccate:
        assert risposta.status_code == 403
        assert risposta.json()["codice"] == "impersonazione"
    # Reading the allauth session is fine (the PWA does it at start-up).
    assert client.get("/_allauth/browser/v1/auth/session").status_code == 200


def test_chi_non_puo_riceve_403(capo, estraneo, altro_capo, ragazza):
    assert _inizia(_client(capo), estraneo).status_code == 403
    assert _inizia(_client(altro_capo), ragazza).status_code == 403
    assert not Impersonazione.objects.exists()


def test_dopo_30_minuti_finisce_da_sola(capo, genitore):
    client = _client(capo)
    _inizia(client, genitore)
    Impersonazione.objects.update(scade_il=timezone.now() - timedelta(seconds=1))
    assert client.get("/api/v1/io").json()["persona"]["id"] == capo.pk
    assert Impersonazione.objects.get().finita_il is not None


def test_se_il_ruolo_cambia_finisce(capo, genitore):
    client = _client(capo)
    _inizia(client, genitore)
    capo.incarichi.update(data_fine=timezone.localdate())
    assert client.get("/api/v1/io").json()["persona"]["id"] == capo.pk


def test_lo_storico_registra_chi_ha_agito_davvero(capogruppo, capo, reparto):
    client = _client(capogruppo)
    _inizia(client, capo)
    adesso = timezone.now()
    risposta = client.post(
        "/api/v1/eventi",
        {
            "titolo": "Uscita",
            "tipo": "USCITA",
            "livello": "UNITA",
            "unita": [reparto.pk],
            "inizio": (adesso + timedelta(days=3)).isoformat(),
            "fine": (adesso + timedelta(days=3, hours=4)).isoformat(),
        },
        content_type="application/json",
    )
    assert risposta.status_code == 201, risposta.content
    voce = LogEntry.objects.filter(content_type__model="evento").latest("timestamp")
    assert voce.actor == capogruppo.utente


def test_il_registro_accessi_nomina_entrambi(capogruppo, genitore, ragazza):
    client = _client(capogruppo)
    _inizia(client, genitore)
    assert client.get(f"/api/v1/persone/{ragazza.pk}/sanitarie").status_code == 200
    accesso = AccessoDatoSensibile.objects.get(persona=ragazza)
    assert accesso.utente == capogruppo.utente
    assert accesso.per_conto_di == genitore.utente


def test_la_persona_vede_chi_ha_usato_l_app_al_suo_posto(capo, genitore, capogruppo):
    client = _client(capo)
    _inizia(client, genitore, motivo="Aiuto con la liberatoria")
    client.post("/api/v1/impersonazione/fine")
    (riga,) = _client(genitore).get("/api/v1/impersonazioni/mie").json()
    assert (riga["impersonatore"], riga["motivo"]) == ("Anna Capo", "Aiuto con la liberatoria")
    assert len(_client(capogruppo).get("/api/v1/impersonazioni").json()) == 1
    assert _client(genitore).get("/api/v1/impersonazioni").status_code == 403


def test_candidati_per_nome(capo, ragazza, genitore, estraneo):
    trovati = _client(capo).get("/api/v1/impersonazione/candidati?cerca=Genitore").json()
    assert [c["persona_id"] for c in trovati] == [genitore.pk]
    assert _client(capo).get("/api/v1/impersonazione/candidati?cerca=Ugo").json() == []
    assert _client(estraneo).get("/api/v1/impersonazione/candidati?cerca=Gi").status_code == 403
