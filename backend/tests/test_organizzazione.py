"""Units, staff and roles (DEC-09, DEC-10, DEC-11, DEC-14, DEC-18).

Who appoints CSQ/VCSQ, group roles and unit treasurers: decided with the maintainer on
2026-10-28 (see TODO.md).
"""

from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone

from apps.accounts.models import User
from apps.anagrafica.models import Appartenenza, RuoloAppartenenza
from apps.organizzazione.models import (
    Composizione,
    Incarico,
    RuoloIncarico,
    TipoUnita,
    Unita,
)
from apps.permessi import policy
from tests.conftest import INIZIO_ANNO, crea_capo, crea_persona, nato_anni_fa

pytestmark = pytest.mark.django_db

R = RuoloIncarico


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi if isinstance(chi, User) else chi.utente)
    return client


def _valori(nomina) -> list[str]:
    return [n["valore"] for n in nomina]


def _post(chi, url, dati=None):
    return _client(chi).post(url, dati or {}, content_type="application/json")


@pytest.fixture
def staff(reparto, coca):
    """A capo of the reparto staff, not capo unità."""
    persona = crea_capo("Elena", "Staff", "staff@example.invalid")
    Incarico.objects.create(persona=persona, ruolo=R.STAFF, unita=reparto, data_inizio=INIZIO_ANNO)
    return persona


@pytest.fixture
def capo_semplice(coca):
    return crea_capo("Carlo", "Semplice", "semplice@example.invalid")


@pytest.fixture
def amministratore(db) -> User:
    return User.objects.create_user(
        email="admin@example.invalid",
        password="x",  # noqa: S106
        amministratore_tecnico=True,
    )


@pytest.fixture
def clan(gruppo) -> Unita:
    return Unita.objects.create(
        gruppo=gruppo, nome="Clan", tipo=TipoUnita.CLAN_FUOCO, composizione=Composizione.MISTA
    )


# --- policy -------------------------------------------------------------------------------


def test_chi_nomina_chi(capo, capogruppo, staff, capo_semplice, ragazza, csq, reparto, squadriglia):
    # Staff and capo unità: capigruppo only (DEC-10).
    for ruolo in (R.STAFF, R.CAPO_UNITA):
        assert policy.puo_nominare(capogruppo.utente, ruolo, unita=reparto)
        assert not policy.puo_nominare(capo.utente, ruolo, unita=reparto)
    # Unit treasurer: capo unità and capigruppo.
    assert policy.puo_nominare(capo.utente, R.TESORIERE_UNITA, unita=reparto)
    assert policy.puo_nominare(capogruppo.utente, R.TESORIERE_UNITA, unita=reparto)
    assert not policy.puo_nominare(staff.utente, R.TESORIERE_UNITA, unita=reparto)
    # CSQ and VCSQ: the whole staff of the reparto (capo unità included), nobody else.
    for ruolo in (R.CSQ, R.VCSQ):
        assert policy.puo_nominare(staff.utente, ruolo, squadriglia=squadriglia)
        assert policy.puo_nominare(capo.utente, ruolo, squadriglia=squadriglia)
        for altro in (capogruppo, capo_semplice, ragazza, csq):
            assert not policy.puo_nominare(altro.utente, ruolo, squadriglia=squadriglia)
    # Units: capigruppo only.
    assert policy.puo_gestire_unita(capogruppo.utente)
    assert not policy.puo_gestire_unita(capo.utente)


def test_amministratore_nomina_capigruppo_solo_se_mancano(amministratore, coca, gruppo):
    assert policy.puo_nominare(amministratore, R.CAPOGRUPPO)
    assert not policy.puo_nominare(amministratore, R.STAFF, unita=coca)
    assert not policy.puo_gestire_unita(amministratore)
    Incarico.objects.create(
        persona=crea_capo("Primo", "Cg"), ruolo=R.CAPOGRUPPO, gruppo=gruppo, data_inizio=INIZIO_ANNO
    )
    assert not policy.puo_nominare(amministratore, R.CAPOGRUPPO)
    assert not policy.puo_nominare(amministratore, R.TESORIERE_GRUPPO)


def test_lo_staff_scrive_le_sanitarie_della_sua_unita(staff, capo_semplice, ragazza):
    """DEC-09: a capo writes for the unit they serve."""
    assert policy.puo_modificare_sanitarie(staff.utente, ragazza)
    assert not policy.puo_modificare_sanitarie(capo_semplice.utente, ragazza)


# --- units -------------------------------------------------------------------------------


NUOVA_UNITA = {"nome": "Reparto Nuovo", "tipo": "REPARTO", "composizione": "F"}


@pytest.mark.parametrize("ruolo", ["capo", "csq", "ragazza", "genitore", "estraneo"])
def test_solo_i_capigruppo_creano_unita(request, ruolo):
    chi = request.getfixturevalue(ruolo)
    assert _post(chi, "/api/v1/unita", NUOVA_UNITA).status_code == 403


def test_capogruppo_crea_collega_e_chiude_unita(capogruppo, reparto):
    risposta = _post(
        capogruppo,
        "/api/v1/unita",
        NUOVA_UNITA | {"collegata_a": reparto.pk, "nota_collegamento": "Reparto parallelo"},
    )
    assert risposta.status_code == 201, risposta.content
    nuova = risposta.json()
    assert nuova["branca"] == "EG"
    assert nuova["collegata_a"] == reparto.pk

    chiusa = _client(capogruppo).put(
        f"/api/v1/unita/{nuova['id']}",
        NUOVA_UNITA | {"attiva": False},
        content_type="application/json",
    )
    assert chiusa.json()["attiva"] is False
    attive = {u["id"] for u in _client(capogruppo).get("/api/v1/unita").json()}
    tutte = {u["id"] for u in _client(capogruppo).get("/api/v1/unita?tutte=true").json()}
    assert nuova["id"] not in attive
    assert nuova["id"] in tutte


def test_unita_collegata_a_se_stessa_rifiutata(capogruppo, reparto):
    risposta = _client(capogruppo).put(
        f"/api/v1/unita/{reparto.pk}",
        NUOVA_UNITA | {"collegata_a": reparto.pk},
        content_type="application/json",
    )
    assert risposta.status_code == 400


@pytest.mark.parametrize("ruolo", ["csq", "ragazza", "genitore", "estraneo", "amministratore"])
def test_dettaglio_unita_solo_ai_capi(request, ruolo, reparto):
    chi = request.getfixturevalue(ruolo)
    assert _client(chi).get(f"/api/v1/unita/{reparto.pk}").status_code == 403


def test_dettaglio_unita(capo, capogruppo, staff, csq, reparto):
    dati = _client(staff).get(f"/api/v1/unita/{reparto.pk}").json()
    assert {(i["ruolo"], i["persona"]["nome"]) for i in dati["incarichi"]} == {
        ("CAPO_UNITA", "Anna"),
        ("STAFF", "Elena"),
    }
    [aquile] = dati["squadriglie"]
    assert aquile["incarichi"][0]["persona"]["nome"] == "Sara"
    assert _valori(aquile["nomina"]) == ["CSQ", "VCSQ"]
    assert dati["nomina"] == []
    assert dati["puo_modificare"] is False
    assert dati["puo_gestire_squadriglie"] is True

    del_capo = _client(capo).get(f"/api/v1/unita/{reparto.pk}").json()
    assert _valori(del_capo["nomina"]) == ["TESORIERE_UNITA"]
    del_cg = _client(capogruppo).get(f"/api/v1/unita/{reparto.pk}").json()
    assert _valori(del_cg["nomina"]) == ["CAPO_UNITA", "STAFF", "TESORIERE_UNITA"]
    assert del_cg["puo_modificare"] is True
    assert del_cg["squadriglie"][0]["nomina"] == []


# --- roles -------------------------------------------------------------------------------


def _nomina(chi, persona, ruolo, **dove):
    return _post(chi, "/api/v1/incarichi", {"persona_id": persona.pk, "ruolo": ruolo, **dove})


def test_capogruppo_assegna_lo_staff(capogruppo, capo, capo_semplice, ragazza, reparto):
    risposta = _nomina(capogruppo, capo_semplice, "STAFF", unita_id=reparto.pk)
    assert risposta.status_code == 201, risposta.content
    assert risposta.json()["ruolo_nome"] == "Staff di unità"
    assert policy.e_staff(capo_semplice.utente, reparto)
    # Twice the same person: refused.
    doppio = _nomina(capogruppo, capo_semplice, "STAFF", unita_id=reparto.pk)
    assert doppio.status_code == 400
    assert "ha già questo incarico" in doppio.json()["detail"]
    # Staff are capi (DEC-09): a ragazza cannot be.
    assert _nomina(capogruppo, ragazza, "STAFF", unita_id=reparto.pk).status_code == 400
    # The capo unità does not choose the staff (DEC-10).
    altro = crea_capo("Dino", "Altro")
    assert _nomina(capo, altro, "STAFF", unita_id=reparto.pk).status_code == 403


def test_lo_staff_nomina_il_csq(staff, capo_semplice, ragazza, csq, reparto, squadriglia):
    # The seat is taken by Sara: one CSQ at a time.
    pieno = _nomina(staff, ragazza, "CSQ", squadriglia_id=squadriglia.pk)
    assert pieno.status_code == 400
    assert "al massimo 1" in pieno.json()["detail"]
    vice = _nomina(staff, ragazza, "VCSQ", squadriglia_id=squadriglia.pk)
    assert vice.status_code == 201, vice.content
    assert _nomina(capo_semplice, ragazza, "VCSQ", squadriglia_id=squadriglia.pk).status_code == 403


def test_csq_deve_essere_del_reparto(staff, squadriglia, coca):
    fuori = crea_persona("Pino", "Fuori", data_nascita=nato_anni_fa(14))
    risposta = _nomina(staff, fuori, "VCSQ", squadriglia_id=squadriglia.pk)
    assert risposta.status_code == 400
    assert "Reparto Prova" in risposta.json()["detail"]


def test_tesoriere_rs_puo_essere_un_rover(capogruppo, clan):
    """DEC-11: in R/S the unit treasurer may be a rover or scolta of that unit."""
    rover = crea_persona("Rino", "Rover", data_nascita=nato_anni_fa(19))
    Appartenenza.objects.create(
        persona=rover, unita=clan, ruolo=RuoloAppartenenza.RAGAZZO, data_inizio=INIZIO_ANNO
    )
    assert _nomina(capogruppo, rover, "TESORIERE_UNITA", unita_id=clan.pk).status_code == 201


def test_tesoriere_eg_deve_essere_un_capo(capo, ragazza, reparto):
    assert _nomina(capo, ragazza, "TESORIERE_UNITA", unita_id=reparto.pk).status_code == 400


def test_amministratore_nomina_il_primo_capogruppo(amministratore, capo_semplice, gruppo):
    capi = _client(amministratore).get("/api/v1/capi").json()
    assert [c["nome"] for c in capi] == ["Carlo"]
    assert _nomina(amministratore, capo_semplice, "CAPOGRUPPO").status_code == 201
    assert policy.e_capogruppo(capo_semplice.utente)
    secondo = crea_capo("Secondo", "Cg")
    assert _nomina(amministratore, secondo, "CAPOGRUPPO").status_code == 403
    # The capogruppo in office completes the diarchy.
    assert _nomina(capo_semplice, secondo, "CAPOGRUPPO").status_code == 201
    dati = _client(capo_semplice).get("/api/v1/gruppo/incarichi").json()
    assert len(dati["incarichi"]) == 2
    assert _valori(dati["nomina"]) == ["CAPOGRUPPO", "TESORIERE_GRUPPO"]


@pytest.mark.parametrize("ruolo", ["csq", "ragazza", "genitore", "estraneo"])
def test_incarichi_di_gruppo_nascosti_agli_altri(request, ruolo, capogruppo):
    chi = request.getfixturevalue(ruolo)
    assert _client(chi).get("/api/v1/gruppo/incarichi").status_code == 403
    assert _client(chi).get("/api/v1/capi").status_code == 403


def test_chiudere_un_incarico(capogruppo, capo, staff, reparto):
    incarico = Incarico.objects.get(persona=staff, ruolo=R.STAFF)
    assert _post(capo, f"/api/v1/incarichi/{incarico.pk}/termina").status_code == 403
    risposta = _post(capogruppo, f"/api/v1/incarichi/{incarico.pk}/termina")
    assert risposta.json() == {
        "id": incarico.pk,
        "rimosso": False,
        "data_fine": timezone.localdate().isoformat(),
    }
    assert not policy.e_staff(staff.utente, reparto)
    assert _post(capogruppo, f"/api/v1/incarichi/{incarico.pk}/termina").status_code == 409


def test_chiudere_un_incarico_appena_aperto_lo_rimuove(capogruppo, capo_semplice, reparto):
    """A mistake fixed the same day leaves no zero-length period behind."""
    nuovo = _nomina(capogruppo, capo_semplice, "STAFF", unita_id=reparto.pk).json()
    risposta = _post(capogruppo, f"/api/v1/incarichi/{nuovo['id']}/termina")
    assert risposta.json()["rimosso"] is True
    assert not Incarico.objects.filter(pk=nuovo["id"]).exists()


def test_chiudere_chi_ha_lasciato_il_servizio(capogruppo, staff, reparto):
    """DEC-20: closing the roles of a capo who left must stay possible."""
    Appartenenza.objects.filter(persona=staff).update(
        data_fine=timezone.localdate() - timedelta(days=1)
    )
    incarico = Incarico.objects.get(persona=staff, ruolo=R.STAFF)
    assert _post(capogruppo, f"/api/v1/incarichi/{incarico.pk}/termina").status_code == 200


# --- patrols -----------------------------------------------------------------------------


def test_squadriglie(staff, capogruppo, capo_semplice, reparto, coca):
    url = f"/api/v1/unita/{reparto.pk}/squadriglie"
    nuova = _post(staff, url, {"nome": "Volpi", "sesso": "M"})
    assert nuova.status_code == 201, nuova.content
    assert _post(capogruppo, url, {"nome": "Volpi", "sesso": "M"}).status_code == 400  # same name
    assert _post(capo_semplice, url, {"nome": "Lupi", "sesso": "M"}).status_code == 403
    # Patrols live in a reparto only.
    assert (
        _post(capogruppo, f"/api/v1/unita/{coca.pk}/squadriglie", {"nome": "X", "sesso": "M"})
    ).status_code == 400
    chiusa = _client(staff).put(
        f"/api/v1/squadriglie/{nuova.json()['id']}",
        {"nome": "Volpi", "sesso": "M", "attiva": False},
        content_type="application/json",
    )
    assert chiusa.json()["attiva"] is False


# --- patrol members (DEC-30, DEC-65) -----------------------------------------------------


@pytest.fixture
def volpi(reparto):
    from apps.organizzazione.models import Squadriglia

    return Squadriglia.objects.create(unita=reparto, nome="Volpi", sesso="F")


@pytest.fixture
def nuova_ragazza(reparto):
    persona = crea_persona("Marta", "Nuova", data_nascita=nato_anni_fa(11))
    Appartenenza.objects.create(
        persona=persona, unita=reparto, ruolo=RuoloAppartenenza.RAGAZZO, data_inizio=INIZIO_ANNO
    )
    return persona


def _membri(chi, reparto, nome):
    dati = _client(chi).get(f"/api/v1/unita/{reparto.pk}").json()
    [s] = [s for s in dati["squadriglie"] if s["nome"] == nome]
    return [m["persona"]["nome"] for m in s["membri"]], [
        p["nome"] for p in dati["senza_squadriglia"]
    ]


def test_comporre_le_squadriglie(staff, reparto, squadriglia, volpi, nuova_ragazza, ragazza):
    membri, senza = _membri(staff, reparto, "Aquile")
    assert "Giulia" in membri
    assert senza == ["Marta"]

    risposta = _post(
        staff, f"/api/v1/squadriglie/{volpi.pk}/membri", {"persona_id": nuova_ragazza.pk}
    )
    assert risposta.status_code == 201, risposta.content
    assert _membri(staff, reparto, "Volpi") == (["Marta"], [])

    # A change of patrol mid-year closes the previous membership (DEC-65).
    spostata = _post(staff, f"/api/v1/squadriglie/{volpi.pk}/membri", {"persona_id": ragazza.pk})
    assert spostata.status_code == 201, spostata.content
    assert "Giulia" not in _membri(staff, reparto, "Aquile")[0]
    assert sorted(_membri(staff, reparto, "Volpi")[0]) == ["Giulia", "Marta"]
    vecchia = ragazza.appartenenze_squadriglia.get(squadriglia=squadriglia)
    assert vecchia.data_fine == timezone.localdate()


def test_solo_ragazzi_del_reparto(staff, volpi, capo_semplice):
    risposta = _post(
        staff, f"/api/v1/squadriglie/{volpi.pk}/membri", {"persona_id": capo_semplice.pk}
    )
    assert risposta.status_code == 400
    assert "Reparto Prova" in risposta.json()["detail"]


def test_capo_squadriglia_non_si_sposta(staff, csq, volpi):
    risposta = _post(staff, f"/api/v1/squadriglie/{volpi.pk}/membri", {"persona_id": csq.pk})
    assert risposta.status_code == 400
    assert "chiudi prima l'incarico" in risposta.json()["detail"]


def test_squadriglia_chiusa_non_accoglie(staff, volpi, nuova_ragazza):
    volpi.attiva = False
    volpi.save()
    url = f"/api/v1/squadriglie/{volpi.pk}/membri"
    assert _post(staff, url, {"persona_id": nuova_ragazza.pk}).status_code == 400


def test_togliere_dalla_squadriglia(staff, reparto, ragazza, volpi, nuova_ragazza):
    vecchia = ragazza.appartenenze_squadriglia.get()
    risposta = _post(staff, f"/api/v1/membri-squadriglia/{vecchia.pk}/termina")
    assert risposta.json() == {"id": vecchia.pk, "rimosso": False}
    assert "Giulia" in _membri(staff, reparto, "Volpi")[1]
    assert _post(staff, f"/api/v1/membri-squadriglia/{vecchia.pk}/termina").status_code == 409
    # Added and removed the same day: no zero-length period left behind.
    nuovo = _post(staff, f"/api/v1/squadriglie/{volpi.pk}/membri", {"persona_id": nuova_ragazza.pk})
    tolto = _post(staff, f"/api/v1/membri-squadriglia/{nuovo.json()['id']}/termina")
    assert tolto.json()["rimosso"] is True


@pytest.mark.parametrize("ruolo", ["capo_semplice", "csq", "ragazza", "genitore", "estraneo"])
def test_composizione_riservata(request, ruolo, volpi, nuova_ragazza):
    chi = request.getfixturevalue(ruolo)
    url = f"/api/v1/squadriglie/{volpi.pk}/membri"
    assert _post(chi, url, {"persona_id": nuova_ragazza.pk}).status_code == 403


def test_il_csq_vede_la_squadriglia_che_guida(csq, staff, volpi, nuova_ragazza):
    """The patrol members define what the CSQ sees (DEC-13): a new member becomes visible."""
    assert not policy.persone_visibili(csq.utente).filter(pk=nuova_ragazza.pk).exists()
    from apps.organizzazione.models import Squadriglia

    aquile = Squadriglia.objects.get(nome="Aquile")
    _post(staff, f"/api/v1/squadriglie/{aquile.pk}/membri", {"persona_id": nuova_ragazza.pk})
    assert policy.persone_visibili(csq.utente).filter(pk=nuova_ragazza.pk).exists()


def test_csq_scelto_tra_i_membri(staff, volpi, nuova_ragazza):
    risposta = _nomina(staff, nuova_ragazza, "CSQ", squadriglia_id=volpi.pk)
    assert risposta.status_code == 400
    assert "non fa parte di Sq. Volpi" in risposta.json()["detail"]
    _post(staff, f"/api/v1/squadriglie/{volpi.pk}/membri", {"persona_id": nuova_ragazza.pk})
    assert _nomina(staff, nuova_ragazza, "CSQ", squadriglia_id=volpi.pk).status_code == 201


# --- single-sex patrols and Co.Ca. exceptions (maintainer, 2026-10-28) -------------------


@pytest.fixture
def ragazzo(reparto):
    persona = crea_persona("Teo", "Ragazzo", sesso="M", data_nascita=nato_anni_fa(13))
    Appartenenza.objects.create(
        persona=persona, unita=reparto, ruolo=RuoloAppartenenza.RAGAZZO, data_inizio=INIZIO_ANNO
    )
    return persona


def _deroga(chi, persona, reparto, **altro):
    dati = {
        "reparto_id": reparto.pk,
        "sesso_squadriglia": "F",
        "data_decisione": (timezone.localdate() - timedelta(days=3)).isoformat(),
        "motivazione": "Percorso di transizione, decisione della Co.Ca.",
        **altro,
    }
    return _post(chi, f"/api/v1/persone/{persona.pk}/deroghe-squadriglia", dati)


def test_squadriglia_dell_altro_sesso_rifiutata(staff, ragazzo, volpi):
    risposta = _post(staff, f"/api/v1/squadriglie/{volpi.pk}/membri", {"persona_id": ragazzo.pk})
    assert risposta.status_code == 400
    assert "eccezione decisa dalla Co.Ca." in risposta.json()["detail"]


def test_sesso_mancante_non_blocca_ma_si_segnala(staff, reparto, volpi, nuova_ragazza):
    assert nuova_ragazza.sesso == ""
    url = f"/api/v1/squadriglie/{volpi.pk}/membri"
    assert _post(staff, url, {"persona_id": nuova_ragazza.pk}).status_code == 201
    avvisi = _client(staff).get(f"/api/v1/unita/{reparto.pk}").json()["avvisi"]
    assert any("Marta" in a and "non è indicato" in a for a in avvisi)


def test_eccezione_della_coca(capogruppo, staff, ragazzo, reparto, volpi):
    from apps.permessi.models import AccessoDatoSensibile

    # Staff cannot record it: the capogruppo does, after the Co.Ca. decided.
    assert _deroga(staff, ragazzo, reparto).status_code == 403
    risposta = _deroga(capogruppo, ragazzo, reparto)
    assert risposta.status_code == 201, risposta.content
    assert risposta.json()["valida"] is True
    assert risposta.json()["squadriglie_ammesse"] == "Femminili"

    entra = _post(staff, f"/api/v1/squadriglie/{volpi.pk}/membri", {"persona_id": ragazzo.pk})
    assert entra.status_code == 201, entra.content
    assert _client(staff).get(f"/api/v1/unita/{reparto.pk}").json()["avvisi"] == []

    # Revoked: the membership stays, the unit page reports it.
    deroga_id = risposta.json()["id"]
    assert _post(staff, f"/api/v1/deroghe-squadriglia/{deroga_id}/revoca").status_code == 403
    revoca = _post(capogruppo, f"/api/v1/deroghe-squadriglia/{deroga_id}/revoca")
    assert revoca.json()["valida"] is False
    assert _post(capogruppo, f"/api/v1/deroghe-squadriglia/{deroga_id}/revoca").status_code == 409
    avvisi = _client(staff).get(f"/api/v1/unita/{reparto.pk}").json()["avvisi"]
    assert any("Teo" in a and "senza un'eccezione valida" in a for a in avvisi)

    azioni = list(
        AccessoDatoSensibile.objects.filter(persona=ragazzo, categoria="DEROGA_SQ")
        .order_by("creato_il")
        .values_list("azione", flat=True)
    )
    assert azioni == ["MODIFICA", "MODIFICA"]


def test_lettura_registrata_solo_se_c_e_un_eccezione(capo, capogruppo, ragazzo, ragazza, reparto):
    from apps.permessi.models import AccessoDatoSensibile

    vuoto = _client(capo).get(f"/api/v1/persone/{ragazza.pk}/deroghe-squadriglia").json()
    assert vuoto["deroghe"] == []
    assert vuoto["puo_gestire"] is False
    assert not AccessoDatoSensibile.objects.filter(persona=ragazza).exists()

    _deroga(capogruppo, ragazzo, reparto)
    dati = _client(capo).get(f"/api/v1/persone/{ragazzo.pk}/deroghe-squadriglia").json()
    assert dati["deroghe"][0]["motivazione"].startswith("Percorso")
    assert AccessoDatoSensibile.objects.filter(
        persona=ragazzo, utente=capo.utente, azione="LETTURA"
    ).exists()


@pytest.mark.parametrize("ruolo", ["csq", "ragazza", "genitore", "estraneo", "amministratore"])
def test_eccezioni_visibili_solo_ai_capi(request, ruolo, capogruppo, ragazzo, reparto):
    _deroga(capogruppo, ragazzo, reparto)
    chi = request.getfixturevalue(ruolo)
    url = f"/api/v1/persone/{ragazzo.pk}/deroghe-squadriglia"
    assert _client(chi).get(url).status_code == 404
    assert _deroga(chi, ragazzo, reparto).status_code == 404


def test_eccezione_vale_finche_resta_nel_reparto(capogruppo, ragazzo, reparto):
    from apps.anagrafica.models import DerogaSquadriglia

    _deroga(capogruppo, ragazzo, reparto)
    assert DerogaSquadriglia.objects.valide().filter(persona=ragazzo).exists()
    Appartenenza.objects.filter(persona=ragazzo).update(data_fine=timezone.localdate())
    assert not DerogaSquadriglia.objects.valide().filter(persona=ragazzo).exists()


def test_eccezione_solo_per_un_reparto_della_persona(capogruppo, ragazzo, coca):
    assert _deroga(capogruppo, ragazzo, coca).status_code == 400


def test_motivazione_fuori_dal_registro_delle_modifiche(capogruppo, ragazzo, reparto):
    """The audit log is visible in the admin: the reason must not end up there."""
    from auditlog.models import LogEntry

    from apps.anagrafica.models import DerogaSquadriglia

    _deroga(capogruppo, ragazzo, reparto)
    voce = LogEntry.objects.get_for_model(DerogaSquadriglia).get()
    assert "motivazione" not in (voce.changes or {})
    assert "transizione" not in str(voce.changes) + str(voce.object_repr)


def test_nome_obbligatorio_tranne_per_la_coca(gruppo):
    from django.core.exceptions import ValidationError

    with pytest.raises(ValidationError):
        Unita(
            gruppo=gruppo, nome=" ", tipo=TipoUnita.REPARTO, composizione=Composizione.MISTA
        ).full_clean()
    coca = Unita(
        gruppo=gruppo, nome="", tipo=TipoUnita.COMUNITA_CAPI, composizione=Composizione.MISTA
    )
    coca.full_clean()
    assert str(coca) == "Comunità Capi"


def test_dare_il_nome_toglie_il_provvisorio(capogruppo, reparto):
    reparto.nome_provvisorio = True
    reparto.save()
    dati = {"nome": "Reparto Millennium", "tipo": "REPARTO", "composizione": "X"}
    risposta = _client(capogruppo).put(
        f"/api/v1/unita/{reparto.pk}", dati, content_type="application/json"
    )
    assert risposta.json()["nome_provvisorio"] is False
