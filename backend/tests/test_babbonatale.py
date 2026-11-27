"""Babbo Natale segreto (DEC-422) and the features the group may switch off (DEC-421)."""

from datetime import date, timedelta
from unittest import mock

import pytest
from django.core import mail
from django.test import Client
from django.utils import timezone

from apps.accounts.models import Invito, User
from apps.anagrafica.models import Appartenenza, Persona, RelazioneTutela, RuoloAppartenenza
from apps.babbonatale import servizi
from apps.babbonatale.models import Partecipante, ScambioRegali
from apps.impostazioni import funzioni
from apps.organizzazione.models import Composizione, TipoUnita, Unita
from apps.permessi import policy
from tests.conftest import INIZIO_ANNO, crea_persona, nato_anni_fa

pytestmark = pytest.mark.django_db

DOMANI = date.today() + timedelta(days=1)


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente if isinstance(chi, Persona) else chi)
    return client


def _accendi() -> None:
    funzioni.imposta(funzioni.BABBO_NATALE, True)


def _nel_reparto(reparto, nome: str, eta: int = 12, login: str | None = None, **campi) -> Persona:
    persona = crea_persona(nome, "Prova", login, data_nascita=nato_anni_fa(eta), **campi)
    Appartenenza.objects.create(
        persona=persona, unita=reparto, ruolo=RuoloAppartenenza.RAGAZZO, data_inizio=INIZIO_ANNO
    )
    return persona


def _scambio(reparto, persone, **campi) -> ScambioRegali:
    scambio = ScambioRegali.objects.create(
        nome="Natale", unita=reparto, consegna_il=campi.pop("consegna_il", DOMANI), **campi
    )
    for p in persone:
        Partecipante.objects.create(scambio=scambio, persona=p)
    return scambio


def _giro(scambio) -> dict[int, int]:
    return dict(scambio.partecipanti.values_list("persona_id", "a_chi_id"))


def _un_cerchio(giro: dict[int, int]) -> bool:
    inizio = next(iter(giro))
    visti, corrente = set(), inizio
    while corrente not in visti:
        visti.add(corrente)
        corrente = giro[corrente]
    return corrente == inizio and visti == set(giro)


@pytest.fixture
def ragazzi(reparto, ragazza, csq):
    altri = [_nel_reparto(reparto, n, login=f"{n}@example.invalid") for n in ("Paolo", "Elena")]
    return [ragazza, csq, *altri]


# --- The switch (DEC-421) ---------------------------------------------------------------------


def test_spenta_all_inizio_e_non_esiste(capogruppo, capo):
    assert not funzioni.attiva(funzioni.BABBO_NATALE)
    client = _client(capogruppo)
    assert client.get("/api/v1/babbo-natale").status_code == 404
    risposta = client.post(
        "/api/v1/babbo-natale/scambi",
        {"nome": "Natale", "consegna_il": DOMANI.isoformat(), "unita_id": None},
        content_type="application/json",
    )
    assert risposta.status_code == 404
    io = client.get("/api/v1/io").json()
    assert io["funzioni"] == [] and io["babbo_natale"] is False
    modelli = [m["chiave"] for m in client.get("/api/v1/impostazioni/email").json()]
    assert "babbo_natale_partecipante" not in modelli
    assert client.get("/api/v1/impostazioni/email/babbo_natale_genitori").status_code == 404


def test_chi_accende_e_spegne(capogruppo, capo, ragazza):
    impostazioni = _client(capogruppo).get("/api/v1/impostazioni").json()
    assert [f["chiave"] for f in impostazioni["funzioni"]] == [funzioni.BABBO_NATALE]
    assert impostazioni["funzioni"][0]["attiva"] is False
    for chi in (capo, ragazza):
        risposta = _client(chi).put(
            "/api/v1/impostazioni/funzioni/babbo_natale",
            {"attiva": True},
            content_type="application/json",
        )
        assert risposta.status_code == 403
    risposta = _client(capogruppo).put(
        "/api/v1/impostazioni/funzioni/babbo_natale",
        {"attiva": True},
        content_type="application/json",
    )
    assert risposta.status_code == 200
    assert risposta.json()["funzioni"][0]["attiva"] is True
    assert funzioni.attiva(funzioni.BABBO_NATALE)
    assert _client(capo).get("/api/v1/io").json()["babbo_natale"] is True
    assert "babbo_natale_partecipante" in [
        m["chiave"] for m in _client(capogruppo).get("/api/v1/impostazioni/email").json()
    ]


def test_l_amministratore_tecnico_accende(db):
    admin = User.objects.create_user(email="admin@example.invalid", amministratore_tecnico=True)
    risposta = _client(admin).put(
        "/api/v1/impostazioni/funzioni/babbo_natale",
        {"attiva": True},
        content_type="application/json",
    )
    assert risposta.status_code == 200
    assert (
        _client(admin)
        .put(
            "/api/v1/impostazioni/funzioni/sconosciuta",
            {"attiva": True},
            content_type="application/json",
        )
        .status_code
        == 404
    )


def test_spenta_i_dati_restano_nascosti(capo, reparto, ragazzi):
    _accendi()
    scambio = _scambio(reparto, ragazzi)
    servizi.estrai(scambio, capo.utente)
    funzioni.imposta(funzioni.BABBO_NATALE, False)
    assert _client(ragazzi[0]).get("/api/v1/babbo-natale").status_code == 404
    assert _client(capo).get(f"/api/v1/babbo-natale/scambi/{scambio.pk}").status_code == 404
    assert _client(ragazzi[0]).get("/api/v1/io").json()["babbo_natale"] is False
    _accendi()
    assert _un_cerchio(_giro(scambio))
    assert _client(ragazzi[0]).get("/api/v1/babbo-natale").json()["regali"]


# --- Who organises ----------------------------------------------------------------------------


def test_chi_crea_gli_scambi(gruppo, capo, capogruppo, reparto, ragazza, genitore, estraneo):
    _accendi()
    branco = Unita.objects.create(
        gruppo=gruppo, nome="Branco", tipo=TipoUnita.BRANCO, composizione=Composizione.MISTA
    )

    def crea(chi, unita_id):
        return _client(chi).post(
            "/api/v1/babbo-natale/scambi",
            {"nome": "Natale", "consegna_il": DOMANI.isoformat(), "unita_id": unita_id},
            content_type="application/json",
        )

    assert crea(capo, reparto.pk).status_code == 201
    assert crea(capo, branco.pk).status_code == 400
    assert crea(capo, None).status_code == 400
    assert crea(capogruppo, None).status_code == 201
    assert crea(capogruppo, branco.pk).status_code == 201
    for chi in (ragazza, genitore, estraneo):
        assert crea(chi, reparto.pk).status_code == 403
        assert _client(chi).get("/api/v1/babbo-natale").status_code == 404


def test_lo_staff_gestisce_solo_i_suoi(gruppo, capo, capogruppo, reparto, ragazzi):
    _accendi()
    del_gruppo = ScambioRegali.objects.create(nome="Gruppo", consegna_il=DOMANI)
    del_reparto = _scambio(reparto, ragazzi)
    assert _client(capo).get(f"/api/v1/babbo-natale/scambi/{del_gruppo.pk}").status_code == 404
    assert _client(capo).get(f"/api/v1/babbo-natale/scambi/{del_reparto.pk}").status_code == 200
    assert (
        _client(capogruppo).get(f"/api/v1/babbo-natale/scambi/{del_gruppo.pk}").status_code == 200
    )
    elenco = _client(capo).get("/api/v1/babbo-natale").json()
    assert [s["id"] for s in elenco["scambi"]] == [del_reparto.pk]


def test_candidati(gruppo, capo, capogruppo, reparto, ragazza, genitore):
    _accendi()
    branco = Unita.objects.create(
        gruppo=gruppo, nome="Branco", tipo=TipoUnita.BRANCO, composizione=Composizione.MISTA
    )
    lupetto = crea_persona("Luca", "Lupo", data_nascita=nato_anni_fa(9))
    Appartenenza.objects.create(
        persona=lupetto, unita=branco, ruolo=RuoloAppartenenza.RAGAZZO, data_inizio=INIZIO_ANNO
    )
    scambio = _scambio(reparto, [])
    dello_staff = {
        p["id"]
        for p in _client(capo).get(f"/api/v1/babbo-natale/scambi/{scambio.pk}/candidati").json()
    }
    # The reparto's ragazzi and its staff; never another unit, never a parent only.
    assert ragazza.pk in dello_staff and capo.pk in dello_staff
    assert lupetto.pk not in dello_staff and genitore.pk not in dello_staff
    del_capogruppo = {
        p["id"]
        for p in _client(capogruppo)
        .get(f"/api/v1/babbo-natale/scambi/{scambio.pk}/candidati")
        .json()
    }
    assert {ragazza.pk, capo.pk, lupetto.pk, capogruppo.pk} <= del_capogruppo
    assert genitore.pk not in del_capogruppo
    risposta = _client(capo).put(
        f"/api/v1/babbo-natale/scambi/{scambio.pk}/partecipanti",
        {"persone": [ragazza.pk, lupetto.pk]},
        content_type="application/json",
    )
    assert risposta.status_code == 400


# --- The draw ---------------------------------------------------------------------------------


def test_estrazione_un_solo_cerchio(capo, reparto, ragazzi):
    _accendi()
    scambio = _scambio(reparto, ragazzi)
    client = _client(capo)
    with mock.patch("apps.babbonatale.servizi.notifica") as notifica:
        risposta = client.post(f"/api/v1/babbo-natale/scambi/{scambio.pk}/estrai")
    assert risposta.status_code == 200
    giro = _giro(scambio)
    assert all(a != b for a, b in giro.items())
    assert all(giro[giro[a]] != a for a in giro)  # nobody gives a gift to each other
    assert _un_cerchio(giro)
    assert notifica.call_count == 4  # all four have an account
    # The organiser never gets who gives a gift to whom.
    testo = (
        risposta.content.decode()
        + client.get(f"/api/v1/babbo-natale/scambi/{scambio.pk}").content.decode()
    )
    assert '"a_chi": "' not in testo  # all four are told: no name for the organiser
    assert client.post(f"/api/v1/babbo-natale/scambi/{scambio.pk}/estrai").status_code == 400


def test_servono_tre_partecipanti(capo, reparto, ragazza, csq):
    _accendi()
    scambio = _scambio(reparto, [ragazza, csq])
    risposta = _client(capo).post(f"/api/v1/babbo-natale/scambi/{scambio.pk}/estrai")
    assert risposta.status_code == 400
    assert "almeno 3" in risposta.json()["detail"]


def test_fratelli_non_vicini(reparto, genitore, ragazza):
    fratello = _nel_reparto(reparto, "Fratello")
    RelazioneTutela.objects.create(tutore=genitore, minore=fratello, tipo="GENITORE")
    altri = [_nel_reparto(reparto, n) for n in ("Uno", "Due", "Tre")]
    for _ in range(20):
        giro = servizi.cerchio([ragazza, fratello, *altri])
        coppie = {frozenset((giro[i], giro[(i + 1) % 5])) for i in range(5)}
        assert frozenset((ragazza.pk, fratello.pk)) not in coppie


# --- Who sees what ----------------------------------------------------------------------------


def test_ognuno_vede_solo_il_suo(capo, reparto, ragazzi, genitore, estraneo):
    _accendi()
    scambio = _scambio(reparto, ragazzi)
    servizi.estrai(scambio, capo.utente)
    giro = _giro(scambio)
    ragazza = ragazzi[0]
    dati = _client(ragazza).get("/api/v1/babbo-natale").json()
    assert len(dati["regali"]) == 1
    a_chi = Persona.objects.get(pk=giro[ragazza.pk])
    assert dati["regali"][0]["a_chi"] == f"{a_chi.nome} {a_chi.cognome}"
    assert dati["scambi"] == [] and dati["puo_organizzare"] is False
    # The parent sees their child's; the organiser and anyone else nothing.
    dei_figli = _client(genitore).get("/api/v1/babbo-natale").json()["regali"]
    assert [r["proprio"] for r in dei_figli] == [False]
    assert dei_figli[0]["a_chi"] == f"{a_chi.nome} {a_chi.cognome}"
    assert _client(capo).get("/api/v1/babbo-natale").json()["regali"] == []
    assert _client(estraneo).get("/api/v1/babbo-natale").status_code == 404
    assert _client(estraneo).get("/api/v1/io").json()["babbo_natale"] is False


def test_bozza_invisibile_ai_partecipanti_e_fine_dopo_un_mese(capo, reparto, ragazzi):
    _accendi()
    scambio = _scambio(reparto, ragazzi)
    assert _client(ragazzi[0]).get("/api/v1/babbo-natale").status_code == 404
    servizi.estrai(scambio, capo.utente)
    assert _client(ragazzi[0]).get("/api/v1/io").json()["babbo_natale"] is True
    ScambioRegali.objects.filter(pk=scambio.pk).update(
        consegna_il=date.today() - timedelta(days=31)
    )
    assert _client(ragazzi[0]).get("/api/v1/babbo-natale").status_code == 404


def test_impersonando_non_si_vede(capogruppo, coca, reparto, ragazzi):
    _accendi()
    scambio = _scambio(reparto, ragazzi)
    servizi.estrai(scambio, capogruppo.utente)
    client = _client(capogruppo)
    avvio = client.post(
        "/api/v1/impersonazione",
        {"persona_id": ragazzi[0].pk, "motivo": "Non trova la pagina"},
        content_type="application/json",
    )
    assert avvio.status_code == 201
    dati = client.get("/api/v1/babbo-natale").json()
    assert dati["nascosti"] is True
    assert [r["a_chi"] for r in dati["regali"]] == [""]


# --- How each one is told ---------------------------------------------------------------------


def test_avvisi_email_invito_e_genitori(capo, reparto, genitore, genitrice_senza_account):
    _accendi()
    adulto = _nel_reparto(reparto, "Adulto", 19, email="adulto@example.invalid")
    piccolo = _nel_reparto(reparto, "Piccolo", 11)
    RelazioneTutela.objects.create(tutore=genitore, minore=piccolo, tipo="GENITORE")
    con_account = _nel_reparto(reparto, "Conto", 15, login="conto@example.invalid")
    irraggiungibile = _nel_reparto(reparto, "Nessuno", 30)
    scambio = _scambio(reparto, [adulto, piccolo, con_account, irraggiungibile])
    modi = {
        p["nome"]: p["avviso"]
        for p in _client(capo).get(f"/api/v1/babbo-natale/scambi/{scambio.pk}").json()["elenco"]
    }
    assert modi == {"Adulto": "email", "Piccolo": "genitori", "Conto": "app", "Nessuno": "nessuno"}
    mail.outbox = []
    with mock.patch("apps.babbonatale.servizi.notifica") as notifica:
        esito = servizi.estrai(scambio, capo.utente)
    assert esito.avvisati == {"app": 1, "email": 1, "genitori": 1, "nessuno": 1}
    destinatari = sorted(m.to[0] for m in mail.outbox)
    # Everyone gets an email: who has an account too, with the notification.
    assert destinatari == [
        "adulto@example.invalid",
        "conto@example.invalid",
        "genitore@example.invalid",
    ]
    al_conto = next(m for m in mail.outbox if m.to == ["conto@example.invalid"])
    a_chi_conto = Persona.objects.get(pk=_giro(scambio)[con_account.pk])
    assert f"{a_chi_conto.nome} {a_chi_conto.cognome}" in al_conto.body
    assert "/babbo-natale" in al_conto.body and "/invito/" not in al_conto.body
    invito = Invito.objects.get(persona=adulto)
    all_adulto = next(m for m in mail.outbox if m.to == ["adulto@example.invalid"])
    assert invito.token in all_adulto.body
    giro = _giro(scambio)
    a_chi = Persona.objects.get(pk=giro[adulto.pk])
    assert f"{a_chi.nome} {a_chi.cognome}" in all_adulto.body
    # The push says nothing of who: the participant with an account and the minor's parents.
    persone_avvisate = [c.args[1] for c in notifica.call_args_list]
    assert [con_account] in persone_avvisate
    for chiamata in notifica.call_args_list:
        assert a_chi.nome not in chiamata.args[2] + chiamata.args[4]


def test_chi_non_si_puo_avvisare_lo_vede_l_organizzatore(capo, reparto, ragazzi):
    # DEC-422: only for who nobody can tell, to say it aloud; nobody else's.
    _accendi()
    nessuno = _nel_reparto(reparto, "Nessuno", 12)
    scambio = _scambio(reparto, [*ragazzi, nessuno])
    url = f"/api/v1/babbo-natale/scambi/{scambio.pk}"
    prima = _client(capo).get(url).json()["elenco"]
    assert all(p["a_chi"] is None for p in prima)  # not drawn yet
    servizi.estrai(scambio, capo.utente)
    elenco = {p["id"]: p for p in _client(capo).get(url).json()["elenco"]}
    a_chi = Persona.objects.get(pk=_giro(scambio)[nessuno.pk])
    assert elenco[nessuno.pk]["avviso"] == "nessuno"
    assert elenco[nessuno.pk]["a_chi"] == f"{a_chi.nome} {a_chi.cognome}"
    assert [p["a_chi"] for k, p in elenco.items() if k != nessuno.pk] == [None] * 4


# --- After the draw ---------------------------------------------------------------------------


def test_ritiro_e_aggiunta_toccano_solo_il_punto(capo, reparto, ragazzi):
    _accendi()
    scambio = _scambio(reparto, ragazzi)
    servizi.estrai(scambio, capo.utente)
    prima = _giro(scambio)
    uscente = ragazzi[1]
    chi_gli_dava = next(a for a, b in prima.items() if b == uscente.pk)
    with mock.patch("apps.babbonatale.servizi.notifica") as notifica:
        risposta = _client(capo).post(
            f"/api/v1/babbo-natale/scambi/{scambio.pk}/ritira",
            {"persona_id": uscente.pk},
            content_type="application/json",
        )
    assert risposta.status_code == 200
    dopo = _giro(scambio)
    assert dopo[chi_gli_dava] == prima[uscente.pk]
    assert {k: v for k, v in dopo.items() if k != chi_gli_dava} == {
        k: v for k, v in prima.items() if k not in (chi_gli_dava, uscente.pk)
    }
    assert [c.args[1][0].pk for c in notifica.call_args_list] == [chi_gli_dava]
    assert _un_cerchio(dopo)
    # Below three it refuses.
    risposta = _client(capo).post(
        f"/api/v1/babbo-natale/scambi/{scambio.pk}/ritira",
        {"persona_id": ragazzi[0].pk},
        content_type="application/json",
    )
    assert risposta.status_code == 400
    nuovo = _nel_reparto(reparto, "Nuovo", login="nuovo@example.invalid")
    with mock.patch("apps.babbonatale.servizi.notifica") as notifica:
        risposta = _client(capo).post(
            f"/api/v1/babbo-natale/scambi/{scambio.pk}/aggiungi",
            {"persona_id": nuovo.pk},
            content_type="application/json",
        )
    assert risposta.status_code == 200
    finale = _giro(scambio)
    assert _un_cerchio(finale) and len(finale) == 4
    cambiati = {k for k in finale if finale[k] != dopo.get(k)}
    assert len(cambiati) == 2 and nuovo.pk in cambiati
    assert {c.args[1][0].pk for c in notifica.call_args_list} == cambiati


def test_reinvio_e_chiusura(capo, reparto, ragazzi, ragazza):
    _accendi()
    scambio = _scambio(reparto, ragazzi)
    client = _client(capo)
    assert (
        client.post(
            f"/api/v1/babbo-natale/scambi/{scambio.pk}/reinvia",
            {"persone": [ragazza.pk]},
            content_type="application/json",
        ).status_code
        == 400
    )  # not drawn yet
    servizi.estrai(scambio, capo.utente)
    with mock.patch("apps.babbonatale.servizi.notifica") as notifica:
        risposta = client.post(
            f"/api/v1/babbo-natale/scambi/{scambio.pk}/reinvia",
            {"persone": [ragazza.pk]},
            content_type="application/json",
        )
    assert risposta.json() == {"reinviati": 1}
    assert notifica.call_args.args[1] == [ragazza]
    assert client.delete(f"/api/v1/babbo-natale/scambi/{scambio.pk}").status_code == 400
    ScambioRegali.objects.filter(pk=scambio.pk).update(consegna_il=date.today() - timedelta(1))
    assert (
        client.post(
            f"/api/v1/babbo-natale/scambi/{scambio.pk}/reinvia",
            {"persone": [ragazza.pk]},
            content_type="application/json",
        ).status_code
        == 400
    )
    assert (
        client.put(
            f"/api/v1/babbo-natale/scambi/{scambio.pk}",
            {"nome": "Altro", "unita_id": reparto.pk, "consegna_il": DOMANI.isoformat()},
            content_type="application/json",
        ).status_code
        == 400
    )


def test_policy_per_ruolo(capo, capogruppo, csq, ragazza, genitore, estraneo, reparto):
    scambio = _scambio(reparto, [])
    assert policy.puo_organizzare_scambi(capo.utente)
    assert policy.puo_organizzare_scambi(capogruppo.utente)
    for chi in (csq, ragazza, genitore, estraneo):
        assert not policy.puo_organizzare_scambi(chi.utente)
        assert not policy.puo_gestire_scambio(chi.utente, scambio)
    assert policy.puo_gestire_scambio(capo.utente, scambio)
    assert policy.puo_gestire_scambio(capogruppo.utente, scambio)


# --- The Django admin, read only, for the technical administrator (DEC-436) -----------------


@pytest.fixture
def estratto(reparto, ragazzi):
    scambio = _scambio(reparto, ragazzi, estratto_il=timezone.now())
    for chi, a_chi in zip(ragazzi, ragazzi[1:] + ragazzi[:1], strict=True):
        Partecipante.objects.filter(scambio=scambio, persona=chi).update(a_chi=a_chi)
    return scambio


@pytest.fixture
def tecnico():
    return User.objects.create_user(email="tecnico@example.invalid", amministratore_tecnico=True)


def test_l_amministratore_tecnico_legge_gli_abbinamenti(tecnico, estratto, ragazzi):
    _accendi()
    client = _client(tecnico)
    assert "Partecipanti" in client.get("/admin/").content.decode()
    elenco = client.get("/admin/babbonatale/partecipante/?q=Prova")
    assert elenco.status_code == 200
    giulia = Partecipante.objects.get(scambio=estratto, persona=ragazzi[0])
    scheda = client.get(f"/admin/babbonatale/partecipante/{giulia.pk}/change/")
    assert scheda.status_code == 200 and str(ragazzi[1]) in scheda.content.decode()
    assert client.get(f"/admin/babbonatale/scambioregali/{estratto.pk}/change/").status_code == 200


def test_nell_admin_niente_si_cambia(tecnico, estratto, ragazzi):
    _accendi()
    client = _client(tecnico)
    giulia = Partecipante.objects.get(scambio=estratto, persona=ragazzi[0])
    assert client.get("/admin/babbonatale/partecipante/add/").status_code == 403
    assert client.get("/admin/babbonatale/scambioregali/add/").status_code == 403
    risposta = client.post(
        f"/admin/babbonatale/partecipante/{giulia.pk}/change/",
        {"scambio": estratto.pk, "persona": ragazzi[0].pk, "a_chi": ragazzi[2].pk},
    )
    assert risposta.status_code == 403
    assert (
        client.post(
            f"/admin/babbonatale/partecipante/{giulia.pk}/delete/", {"post": "yes"}
        ).status_code
        == 403
    )
    giulia.refresh_from_db()
    assert giulia.a_chi == ragazzi[1]
    assert ScambioRegali.objects.filter(pk=estratto.pk).exists()


def test_con_la_funzione_spenta_non_c_e_nemmeno_nell_admin(tecnico, estratto):
    client = _client(tecnico)
    assert not policy.vede_abbinamenti_in_admin(tecnico)
    assert "Partecipanti" not in client.get("/admin/").content.decode()
    assert client.get("/admin/babbonatale/partecipante/").status_code == 403


def test_solo_l_amministratore_tecnico(capo, capogruppo, ragazza, genitore, estraneo, estratto):
    _accendi()
    # A plain Django staff user enters the admin but does not see them.
    staff = User.objects.create_user(email="staff@example.invalid", is_staff=True)
    assert not policy.vede_abbinamenti_in_admin(staff)
    assert _client(staff).get("/admin/babbonatale/partecipante/").status_code == 403
    for chi in (capo, capogruppo, ragazza, genitore, estraneo):
        assert not policy.vede_abbinamenti_in_admin(chi.utente)
        # They do not even enter the admin.
        assert _client(chi).get("/admin/babbonatale/partecipante/").status_code == 302
