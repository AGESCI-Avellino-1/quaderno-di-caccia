"""Roles the capigruppo define for the capi (DEC-347...DEC-349)."""

import json
from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.test import Client
from django.utils import timezone

from apps.fascicolo.capi import anni_di_servizio
from apps.organizzazione import elenco_incarichi as elenco
from apps.organizzazione.api import capi_senza_servizio
from apps.organizzazione.models import (
    AmbitoIncarico,
    Incarico,
    RuoloIncarico,
    TipoIncarico,
)
from apps.permessi import policy
from tests.conftest import INIZIO_ANNO, crea_capo

pytestmark = pytest.mark.django_db

SCHEDA = "/api/v1/gruppo/scheda-incarichi"
TIPI = "/api/v1/gruppo/tipi-incarico"


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


def _post(chi, percorso, dati):
    return _client(chi).post(percorso, json.dumps(dati), content_type="application/json")


def _tipo(nome="Referente sicurezza", ambito=AmbitoIncarico.GRUPPO, **campi) -> TipoIncarico:
    return TipoIncarico.objects.create(nome=nome, ambito=ambito, **campi)


def _assegnato(persona, tipo, gruppo=None, unita=None) -> Incarico:
    return Incarico.objects.create(
        persona=persona,
        ruolo=RuoloIncarico.DEFINITO,
        tipo=tipo,
        gruppo=gruppo,
        unita=unita,
        data_inizio=INIZIO_ANNO,
    )


NUOVO = {
    "nome": "Referente sicurezza",
    "ambito": "GRUPPO",
    "di_servizio": False,
    "educativo": False,
}


def test_definisce_solo_il_capogruppo(capo, capogruppo, csq, ragazza, genitore, estraneo):
    assert policy.puo_definire_incarichi(capogruppo.utente)
    for chi in (capo, csq, ragazza, genitore, estraneo):
        assert not policy.puo_definire_incarichi(chi.utente)
        assert _post(chi, TIPI, NUOVO).status_code == 403
    risposta = _post(capogruppo, TIPI, NUOVO)
    assert risposta.status_code == 201
    assert risposta.json()["usato"] is False


def test_chi_legge_la_scheda(capo, capogruppo, csq, ragazza, genitore, estraneo):
    _tipo()
    for chi, puo_modificare in ((capogruppo, True), (capo, False)):
        dati = _client(chi).get(SCHEDA).json()
        assert dati["puo_modificare"] is puo_modificare
        assert [t["nome"] for t in dati["definiti"]] == ["Referente sicurezza"]
    for chi in (csq, ragazza, genitore, estraneo):
        assert _client(chi).get(SCHEDA).status_code == 403


def test_gli_esistenti_si_leggono_come_da_regola(capogruppo):
    """Fixed roles stay as they are, read only (DEC-349, DEC-318)."""
    esistenti = {e["nome"]: e for e in _client(capogruppo).get(SCHEDA).json()["esistenti"]}
    assert esistenti["Tesoriere di gruppo"]["educativo"] is False
    assert esistenti["Staff di unità"]["educativo"] is True
    assert esistenti["Staff di unità"]["di_servizio"] is True
    assert esistenti["Staff di unità"]["ambito"] == "UNITA"
    assert "A disposizione" not in esistenti


def test_non_si_chiama_come_un_incarico_dell_app(capogruppo):
    risposta = _post(capogruppo, TIPI, NUOVO | {"nome": "capogruppo"})
    assert risposta.status_code == 400


def test_assegna_solo_il_capogruppo(gruppo, capo, capogruppo, csq, ragazza, genitore, estraneo):
    tipo = _tipo()
    dati = {"persona_id": capo.pk, "ruolo": tipo.codice}
    for chi in (capo, csq, ragazza, genitore, estraneo):
        assert not policy.puo_nominare(chi.utente, RuoloIncarico.DEFINITO)
        assert _post(chi, "/api/v1/incarichi", dati).status_code == 403
    risposta = _post(capogruppo, "/api/v1/incarichi", dati)
    assert risposta.status_code == 201
    assert risposta.json()["ruolo"] == tipo.codice
    assert risposta.json()["ruolo_nome"] == "Referente sicurezza"
    assert risposta.json()["chiudibile"] is True


def test_solo_ai_capi(gruppo, capogruppo, ragazza, genitore):
    tipo = _tipo()
    for chi in (ragazza, genitore):
        dati = {"persona_id": chi.pk, "ruolo": tipo.codice}
        risposta = _post(capogruppo, "/api/v1/incarichi", dati)
        assert risposta.status_code == 400
        assert "spetta a un capo" in risposta.json()["detail"]


def test_il_ruolo_nudo_e_un_codice_inventato_si_rifiutano(gruppo, capo, capogruppo):
    for ruolo, stato in (
        ("DEFINITO", 400),
        ("DEFINITO:x", 404),
        ("DEFINITO:999", 404),
        ("BOH", 400),
    ):
        dati = {"persona_id": capo.pk, "ruolo": ruolo}
        assert _post(capogruppo, "/api/v1/incarichi", dati).status_code == stato


def test_non_da_nessun_permesso(gruppo, coca, reparto, ragazza):
    """Neither on the unit's data nor as a capogruppo (DEC-347)."""
    capo = crea_capo("Dino", "Sicurezza", "dino@example.invalid")
    _assegnato(capo, _tipo(), gruppo=gruppo)
    _assegnato(capo, _tipo("Materiale", AmbitoIncarico.UNITA, di_servizio=True), unita=reparto)
    assert not policy.e_capogruppo(capo.utente)
    assert not policy.e_staff(capo.utente, reparto)
    assert not policy.puo_gestire_squadriglie(capo.utente, reparto)
    assert not policy.puo_modificare_sanitarie(capo.utente, ragazza)


def test_di_unita_si_assegna_nell_unita(gruppo, reparto, coca, capo, capogruppo):
    tipo = _tipo("Materiale", AmbitoIncarico.UNITA)
    dati = {"persona_id": capo.pk, "ruolo": tipo.codice}
    assert _post(capogruppo, "/api/v1/incarichi", dati).status_code == 404
    in_coca = _post(capogruppo, "/api/v1/incarichi", dati | {"unita_id": coca.pk})
    assert in_coca.status_code == 400
    assert (
        _post(capogruppo, "/api/v1/incarichi", dati | {"unita_id": reparto.pk}).status_code == 201
    )


def test_nomina_dove_vale_ognuno(gruppo, reparto, coca, capo, capogruppo):
    di_gruppo = _tipo()
    servizio = _tipo("Segreteria", di_servizio=True)
    di_unita = _tipo("Materiale", AmbitoIncarico.UNITA)
    spento = _tipo("Vecchio", attivo=False)

    def valori(scelte):
        return {s["valore"] for s in scelte}

    org = _client(capogruppo).get("/api/v1/gruppo/incarichi").json()
    assert di_gruppo.codice in valori(org["nomina"])
    assert servizio.codice not in valori(org["nomina"])
    assert servizio.codice in valori(org["nomina_supporto"])
    assert di_gruppo.codice not in valori(org["nomina_supporto"])
    for scelte in (org["nomina"], org["nomina_supporto"]):
        assert spento.codice not in valori(scelte)
    nell_unita = _client(capogruppo).get(f"/api/v1/unita/{reparto.pk}").json()
    assert di_unita.codice in valori(nell_unita["nomina"])
    assert di_gruppo.codice not in valori(nell_unita["nomina"])
    # A capo does not assign them.
    assert di_unita.codice not in valori(
        _client(capo).get(f"/api/v1/unita/{reparto.pk}").json()["nomina"]
    )
    # In the Co.Ca. only the group's roles apply.
    in_coca = _client(capogruppo).get(f"/api/v1/unita/{coca.pk}").json()
    assert di_unita.codice not in valori(in_coca["nomina"])


# --- Services (DEC-348) ---------------------------------------------------------------------


def test_servizio_di_gruppo_toglie_da_senza_servizio(gruppo, coca):
    capo = crea_capo("Dino", "Segreteria", "dino@example.invalid")
    assert capo in capi_senza_servizio()
    _assegnato(capo, _tipo("Aggiuntivo"), gruppo=gruppo)
    assert capo in capi_senza_servizio()
    _assegnato(capo, _tipo("Segreteria", di_servizio=True), gruppo=gruppo)
    assert capo not in capi_senza_servizio()


def test_servizio_di_unita_toglie_da_senza_servizio(coca, reparto):
    capo = crea_capo("Dino", "Materiale", "dino@example.invalid")
    _assegnato(capo, _tipo("Materiale", AmbitoIncarico.UNITA, di_servizio=True), unita=reparto)
    assert capo not in capi_senza_servizio()


def test_servizio_di_gruppo_esclude_il_servizio_in_unita(gruppo, capo, capogruppo):
    """`capo` is capo unità of the reparto."""
    dati = {"persona_id": capo.pk, "ruolo": _tipo("Segreteria", di_servizio=True).codice}
    risposta = _post(capogruppo, "/api/v1/incarichi", dati)
    assert risposta.status_code == 400
    assert "fa servizio in un'unità" in risposta.json()["detail"]


def test_servizio_di_gruppo_esclude_gli_altri_supporti(gruppo, capogruppo):
    capo = crea_capo("Dino", "Segreteria", "dino@example.invalid")
    Incarico.objects.create(
        persona=capo, ruolo=RuoloIncarico.SUPPORTO_GRUPPO, gruppo=gruppo, data_inizio=INIZIO_ANNO
    )
    dati = {"persona_id": capo.pk, "ruolo": _tipo("Segreteria", di_servizio=True).codice}
    risposta = _post(capogruppo, "/api/v1/incarichi", dati)
    assert risposta.status_code == 400
    assert "servizio di supporto" in risposta.json()["detail"]


def test_il_supporto_esclude_il_servizio_definito_di_gruppo(gruppo, coca):
    capo = crea_capo("Dino", "Segreteria", "dino@example.invalid")
    _assegnato(capo, _tipo("Segreteria", di_servizio=True), gruppo=gruppo)
    nuovo = Incarico(
        persona=capo, ruolo=RuoloIncarico.SUPPORTO_EDUCATIVO, gruppo=gruppo, data_inizio=INIZIO_ANNO
    )
    with pytest.raises(ValidationError, match="servizio di supporto"):
        nuovo.full_clean()


def test_assegnare_un_unita_chiude_il_servizio_definito_di_gruppo(gruppo, reparto, capogruppo):
    capo = crea_capo("Dino", "Segreteria", "dino@example.invalid")
    servizio = _assegnato(capo, _tipo("Segreteria", di_servizio=True), gruppo=gruppo)
    aggiuntivo = _assegnato(capo, _tipo("Aggiuntivo"), gruppo=gruppo)
    dati = {"persona_id": capo.pk, "ruolo": "STAFF", "unita_id": reparto.pk}
    assert _post(capogruppo, "/api/v1/incarichi", dati).status_code == 201
    servizio.refresh_from_db()
    aggiuntivo.refresh_from_db()
    assert servizio.data_fine == timezone.localdate()
    assert aggiuntivo.data_fine is None


def test_servizio_di_unita_chiude_i_supporti(gruppo, reparto, capogruppo):
    capo = crea_capo("Dino", "Materiale", "dino@example.invalid")
    supporto = Incarico.objects.create(
        persona=capo, ruolo=RuoloIncarico.SUPPORTO_GRUPPO, gruppo=gruppo, data_inizio=INIZIO_ANNO
    )
    tipo = _tipo("Materiale", AmbitoIncarico.UNITA, di_servizio=True)
    dati = {"persona_id": capo.pk, "ruolo": tipo.codice, "unita_id": reparto.pk}
    assert _post(capogruppo, "/api/v1/incarichi", dati).status_code == 201
    supporto.refresh_from_db()
    assert supporto.data_fine == timezone.localdate()


def test_il_supporto_esclude_il_servizio_definito_di_unita(gruppo, reparto, capogruppo):
    capo = crea_capo("Dino", "Materiale", "dino@example.invalid")
    _assegnato(capo, _tipo("Materiale", AmbitoIncarico.UNITA, di_servizio=True), unita=reparto)
    dati = {"persona_id": capo.pk, "ruolo": "SUPPORTO_GRUPPO"}
    risposta = _post(capogruppo, "/api/v1/incarichi", dati)
    assert risposta.status_code == 400
    assert "fa servizio in un'unità" in risposta.json()["detail"]


def test_servizio_di_unita_nell_organigramma(reparto, capogruppo):
    capo = crea_capo("Dino", "Materiale", "dino@example.invalid")
    _assegnato(capo, _tipo("Materiale", AmbitoIncarico.UNITA, di_servizio=True), unita=reparto)
    _assegnato(capo, _tipo("Solo aggiuntivo", AmbitoIncarico.UNITA), unita=reparto)
    staff = _client(capogruppo).get("/api/v1/gruppo/incarichi").json()["staff_unita"]
    nomi = [i["ruolo_nome"] for s in staff if s["unita_id"] == reparto.pk for i in s["incarichi"]]
    assert "Materiale" in nomi
    assert "Solo aggiuntivo" not in nomi


# --- Changing and removing ------------------------------------------------------------------


def test_in_uso_non_cambia_natura_ne_si_cancella(gruppo, capo, capogruppo):
    tipo = _tipo()
    _assegnato(capo, tipo, gruppo=gruppo)
    percorso = f"{TIPI}/{tipo.pk}"
    client = _client(capogruppo)
    for cambio in ({"ambito": "UNITA"}, {"di_servizio": True}):
        risposta = client.put(percorso, json.dumps(NUOVO | cambio), content_type="application/json")
        assert risposta.status_code == 400
    assert client.delete(percorso).status_code == 400
    # The name, educational or not and being offered may change.
    risposta = client.put(
        percorso,
        json.dumps(NUOVO | {"nome": "Sicurezza", "educativo": True, "attivo": False}),
        content_type="application/json",
    )
    assert risposta.status_code == 200
    assert risposta.json()["usato"] is True


def test_mai_usato_si_cancella_e_si_cambia(capogruppo):
    tipo = _tipo()
    client = _client(capogruppo)
    risposta = client.put(
        f"{TIPI}/{tipo.pk}",
        json.dumps(NUOVO | {"ambito": "UNITA"}),
        content_type="application/json",
    )
    assert risposta.status_code == 200
    assert client.delete(f"{TIPI}/{tipo.pk}").status_code == 204
    assert not TipoIncarico.objects.exists()


def test_modifica_e_cancella_solo_il_capogruppo(capo, capogruppo):
    tipo = _tipo()
    client = _client(capo)
    assert client.delete(f"{TIPI}/{tipo.pk}").status_code == 403
    risposta = client.put(f"{TIPI}/{tipo.pk}", json.dumps(NUOVO), content_type="application/json")
    assert risposta.status_code == 403


def test_disattivato_non_si_assegna_ma_si_chiude(gruppo, capo, capogruppo):
    tipo = _tipo()
    in_corso = _assegnato(capo, tipo, gruppo=gruppo)
    tipo.attivo = False
    tipo.save()
    altro = crea_capo("Dino", "Altro", "dino@example.invalid")
    dati = {"persona_id": altro.pk, "ruolo": tipo.codice}
    risposta = _post(capogruppo, "/api/v1/incarichi", dati)
    assert risposta.status_code == 400
    assert "disattivato" in risposta.json()["detail"]
    org = _client(capogruppo).get("/api/v1/gruppo/incarichi").json()
    assert [i["chiudibile"] for i in org["incarichi"] if i["id"] == in_corso.pk] == [True]
    assert _post(capogruppo, f"/api/v1/incarichi/{in_corso.pk}/termina", {}).status_code == 200


def test_un_capo_non_chiude(gruppo, capo, capogruppo):
    in_corso = _assegnato(capogruppo, _tipo(), gruppo=gruppo)
    org = _client(capo).get("/api/v1/gruppo/incarichi").json()
    assert [i["chiudibile"] for i in org["incarichi"] if i["id"] == in_corso.pk] == [False]
    assert _post(capo, f"/api/v1/incarichi/{in_corso.pk}/termina", {}).status_code == 403


def test_lo_stesso_due_volte_no(gruppo, capo, capogruppo):
    tipo = _tipo()
    _assegnato(capo, tipo, gruppo=gruppo)
    risposta = _post(capogruppo, "/api/v1/incarichi", {"persona_id": capo.pk, "ruolo": tipo.codice})
    assert risposta.status_code == 400
    assert "ha già questo incarico" in risposta.json()["detail"]


def test_due_tipi_diversi_si_sommano(gruppo, capo):
    _assegnato(capo, _tipo("Uno"), gruppo=gruppo).full_clean()
    secondo = Incarico(
        persona=capo,
        ruolo=RuoloIncarico.DEFINITO,
        tipo=_tipo("Due"),
        gruppo=gruppo,
        data_inizio=INIZIO_ANNO,
    )
    secondo.full_clean()


def test_ruolo_e_tipo_vanno_insieme(gruppo, capo):
    senza = Incarico(persona=capo, ruolo=RuoloIncarico.DEFINITO, gruppo=gruppo)
    with pytest.raises(ValidationError, match="Scegli"):
        senza.full_clean()
    con = Incarico(persona=capo, ruolo=RuoloIncarico.CAPOGRUPPO, gruppo=gruppo, tipo=_tipo())
    with pytest.raises(ValidationError, match="Solo un incarico definito"):
        con.full_clean()


# --- PDF and file ---------------------------------------------------------------------------


def test_educativo_nelle_opzioni_del_pdf(capogruppo):
    """Only the quick choice in the PDF depends on it (DEC-349)."""
    sì = _tipo("Educativo")
    no = _tipo("Non educativo", educativo=False)
    spento = _tipo("Mai usato", attivo=False)
    ruoli = _client(capogruppo).get("/api/v1/gruppo/incarichi/elenco").json()["ruoli"]
    per_codice = {r["valore"]: r for r in ruoli}
    assert per_codice[sì.codice]["educativo"] is True
    assert per_codice[no.codice]["educativo"] is False
    assert spento.codice not in per_codice


def test_disattivato_ma_usato_resta_nelle_opzioni(gruppo, capo, capogruppo):
    tipo = _tipo(attivo=False)
    _assegnato(capo, tipo, gruppo=gruppo)
    ruoli = _client(capogruppo).get("/api/v1/gruppo/incarichi/elenco").json()["ruoli"]
    assert tipo.codice in {r["valore"] for r in ruoli}


def test_pdf_per_unita_e_per_incarico(gruppo, reparto, capogruppo):
    capo = crea_capo("Dino", "Segreteria", "dino@example.invalid")
    di_gruppo = _tipo("Segreteria", di_servizio=True)
    di_unita = _tipo("Materiale", AmbitoIncarico.UNITA)
    _assegnato(capo, di_gruppo, gruppo=gruppo)
    oggi = timezone.localdate()
    tutti = {di_gruppo.codice, di_unita.codice}
    _assegnato(crea_capo("Eva", "Materiale", "eva@example.invalid"), di_unita, unita=reparto)

    per_incarico = elenco.sezioni(tutti, "incarico", oggi)
    assert [s.titolo for s in per_incarico] == ["Materiale", "Segreteria"]
    per_unita = {s.titolo: s for s in elenco.sezioni(tutti, "unita", oggi)}
    riga = per_unita[str(reparto)].righe[0]
    # A unit role alone is no service: the capo also shows in the Co.Ca. as without one.
    assert riga.incarichi == ["Materiale"]
    in_coca = next(s for t, s in per_unita.items() if t != str(reparto))
    assert {r.persona.nome: r.incarichi for r in in_coca.righe}["Dino"] == ["Segreteria"]
    assert {r.persona.nome: r.incarichi for r in in_coca.righe}["Eva"] == [elenco.SENZA_SERVIZIO]

    risposta = _client(capogruppo).get(
        "/api/v1/gruppo/incarichi/elenco.pdf",
        {"ruoli": [di_gruppo.codice], "raggruppa": "incarico"},
    )
    assert risposta.status_code == 200
    assert risposta["Content-Type"] == "application/pdf"


def test_pdf_rifiuta_un_tipo_inesistente(capogruppo):
    risposta = _client(capogruppo).get(
        "/api/v1/gruppo/incarichi/elenco.pdf", {"ruoli": ["DEFINITO:999"]}
    )
    assert risposta.status_code == 400


def test_nel_fascicolo_del_capo_col_suo_nome(gruppo, capo):
    _assegnato(capo, _tipo(educativo=False), gruppo=gruppo)
    ruoli = [r for a in anni_di_servizio(capo) for r in a["ruoli"]]
    assert "Referente sicurezza" in ruoli


def test_chiuso_nel_passato_non_conta_come_servizio(gruppo, coca):
    capo = crea_capo("Dino", "Segreteria", "dino@example.invalid")
    incarico = _assegnato(capo, _tipo("Segreteria", di_servizio=True), gruppo=gruppo)
    incarico.data_fine = timezone.localdate() - timedelta(days=1)
    incarico.save()
    assert capo in capi_senza_servizio()
