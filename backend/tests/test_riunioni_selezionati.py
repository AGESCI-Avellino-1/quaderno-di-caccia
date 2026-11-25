"""Meetings with the people chosen one by one (DEC-430), the email at creation (DEC-431) and
one's own events told apart from the others (DEC-432)."""

# The fixtures come from the staff meetings.
# ruff: noqa: F401, F811

import pytest
from django.core import mail
from django.utils import timezone

from apps.anagrafica.models import Appartenenza, RelazioneTutela, RuoloAppartenenza
from apps.eventi import allineamento, calendario, servizi
from apps.eventi.models import Evento, Presenza, StatoPartecipazione, StatoPresenza
from apps.permessi import policy
from tests.conftest import INIZIO_ANNO, crea_persona, nato_anni_fa
from tests.test_riunioni_staff import (
    MEET,
    _client,
    _post,
    _put,
    _sabato,
    _singola,
    akela,
    altro_capo,
    branco,
    email_accese,
)

pytestmark = pytest.mark.django_db
URL = "/api/v1/riunioni"


def _corpo(persone, **altro):
    return _singola(
        [],
        cerchia="SCELTI",
        titolo="Route",
        persone=[p.pk for p in persone],
        **altro,
    )


def _crea(chi, persone, **altro) -> Evento:
    risposta = _post(chi, URL, _corpo(persone, **altro))
    assert risposta.status_code == 201, risposta.content
    return Evento.objects.get(pk=risposta.json()[0]["id"])


def _invitati(evento) -> set[int]:
    return set(evento.partecipazioni.values_list("persona_id", flat=True))


@pytest.fixture
def lupetto(branco):
    persona = crea_persona("Lia", "Lupetta", data_nascita=nato_anni_fa(9))
    Appartenenza.objects.create(
        persona=persona, unita=branco, ruolo=RuoloAppartenenza.RAGAZZO, data_inizio=INIZIO_ANNO
    )
    return persona


def test_invitati_solo_i_selezionati(capo, akela, ragazza, csq):
    evento = _crea(capo, [akela, ragazza])
    assert _invitati(evento) == {akela.pk, ragazza.pk}
    assert _client(capo).get(f"/api/v1/eventi/{evento.pk}").json()["puo_scegliere"]
    assert _invitati(evento) == {akela.pk, ragazza.pk}


def test_titolo_e_partecipanti_obbligatori(capo, ragazza):
    assert _post(capo, URL, {**_corpo([ragazza]), "titolo": " "}).status_code == 400
    assert _post(capo, URL, _corpo([])).status_code == 400
    serie = {**_corpo([ragazza]), "titolo": "", "giorno": None, "giorno_settimana": 5}
    serie |= {"dal": _sabato(1).isoformat(), "al": _sabato(3).isoformat()}
    assert _post(capo, URL, serie).status_code == 400
    assert not Evento.objects.exists()


def test_chi_crea_e_tra_chi(
    capo, akela, altro_capo, capogruppo, csq, ragazza, genitore, estraneo, lupetto
):
    for chi in (altro_capo, csq, ragazza, genitore, estraneo):
        assert _post(chi, URL, _corpo([ragazza])).status_code == 403
        assert _client(chi).get(f"{URL}/selezionabili").json() == []
    ids = {p["id"] for p in _client(capo).get(f"{URL}/selezionabili").json()}
    assert {capo.pk, akela.pk, altro_capo.pk, ragazza.pk, csq.pk} <= ids
    assert lupetto.pk not in ids and genitore.pk not in ids
    assert _post(capo, URL, _corpo([lupetto])).status_code == 400
    assert _post(capogruppo, URL, _corpo([lupetto, ragazza])).status_code == 201
    assert _post(capogruppo, URL, _corpo([genitore])).status_code == 400


def test_chi_vede(capo, akela, altro_capo, capogruppo, csq, ragazza, genitore, estraneo):
    evento = _crea(capo, [akela, ragazza])
    url = f"/api/v1/eventi/{evento.pk}"
    for chi in (capo, akela, capogruppo, ragazza, genitore):
        assert _client(chi).get(url).status_code == 200, chi
    for chi in (altro_capo, csq, estraneo):
        assert _client(chi).get(url).status_code == 404, chi
        elenco = _client(chi).get("/api/v1/eventi?riunioni=true").json()
        assert evento.pk not in [e["id"] for e in elenco]
        for vista in calendario.VISTE:
            assert not calendario.eventi_del_calendario(chi.utente, vista).filter(pk=evento.pk)
    assert calendario.eventi_del_calendario(akela.utente, "miei").filter(pk=evento.pk)
    assert calendario.eventi_del_calendario(genitore.utente).filter(pk=evento.pk)


def test_non_i_genitori_di_un_maggiorenne(capogruppo, reparto, estraneo):
    adulta = crea_persona("Ada", "Adulta", "ada@example.invalid", data_nascita=nato_anni_fa(19))
    Appartenenza.objects.create(
        persona=adulta, unita=reparto, ruolo=RuoloAppartenenza.RAGAZZO, data_inizio=INIZIO_ANNO
    )
    RelazioneTutela.objects.create(tutore=estraneo, minore=adulta, tipo="GENITORE")
    evento = _crea(capogruppo, [adulta])
    assert _client(adulta).get(f"/api/v1/eventi/{evento.pk}").status_code == 200
    assert _client(estraneo).get(f"/api/v1/eventi/{evento.pk}").status_code == 404
    assert not calendario.eventi_del_calendario(estraneo.utente).filter(pk=evento.pk)


def test_chi_gestisce(capo, akela, altro_capo, capogruppo, ragazza, genitore):
    evento = _crea(capo, [akela, ragazza])
    for chi, si in (
        (capo, True),
        (capogruppo, True),
        (akela, False),
        (altro_capo, False),
        (ragazza, False),
        (genitore, False),
    ):
        assert policy.puo_gestire_evento(chi.utente, evento) is si
        assert policy.puo_segnare_presenze(chi.utente, evento) is si
        # Inviting someone never opens their medical form.
        assert not policy.puo_stampare_schede_evento(chi.utente, evento)
    Appartenenza.objects.filter(persona=capo).update(data_fine=timezone.localdate())
    assert not policy.puo_gestire_evento(capo.utente, evento)


def test_aggiungere_e_togliere(capo, akela, altro_capo, capogruppo, ragazza, csq, lupetto):
    evento = _crea(capo, [capo, ragazza])
    url = f"{URL}/{evento.pk}/partecipanti"
    nuovi = {"persone": [capo.pk, csq.pk]}
    assert _put(akela, url, nuovi).status_code == 404
    assert _put(capo, url, nuovi).status_code == 200
    assert _invitati(evento) == {capo.pk, csq.pk}
    assert _client(ragazza).get(f"/api/v1/eventi/{evento.pk}").status_code == 404
    # Who the capogruppo chose stays, even if the creator could not choose them.
    assert _put(capogruppo, url, {"persone": [capo.pk, csq.pk, lupetto.pk]}).status_code == 200
    assert _put(capo, url, {"persone": [capo.pk, csq.pk, lupetto.pk]}).status_code == 200
    Presenza.objects.create(evento=evento, persona=csq, stato=StatoPresenza.PRESENTE)
    risposta = _put(capo, url, {"persone": [capo.pk]})
    assert risposta.status_code == 400 and "presenza" in risposta.content.decode()
    assert _invitati(evento) == {capo.pk, csq.pk, lupetto.pk}
    assert _put(capo, url, {"persone": []}).status_code == 400


def test_chi_lascia_il_gruppo_esce_chi_cambia_unita_resta(capogruppo, ragazza, csq, branco):
    evento = _crea(capogruppo, [ragazza, csq])
    Appartenenza.objects.filter(persona=csq).update(data_fine=timezone.localdate())
    Appartenenza.objects.filter(persona=ragazza).update(unita=branco)
    allineamento.riallinea({branco.pk})
    assert _invitati(evento) == {ragazza.pk}


def test_serie_stesso_elenco(capo, akela, altro_capo, ragazza):
    corpo = _corpo([akela, ragazza], modalita="MISTA", link=MEET)
    corpo |= {"giorno": None, "giorno_settimana": 5}
    corpo |= {"dal": _sabato(1).isoformat(), "al": _sabato(3).isoformat()}
    risposta = _post(capo, URL, corpo)
    assert risposta.status_code == 201, risposta.content
    eventi = [Evento.objects.get(pk=r["id"]) for r in risposta.json()]
    assert len(eventi) == 3
    assert all(_invitati(e) == {akela.pk, ragazza.pk} for e in eventi)
    _put(capo, f"{URL}/{eventi[0].pk}/partecipanti", {"persone": [akela.pk]})
    assert _invitati(eventi[1]) == {akela.pk, ragazza.pk}
    (serie,) = _client(capo).get(f"{URL}/serie").json()
    assert serie["titolo"] == "Route" and serie["puo_gestire"] and serie["unita"] == []
    assert _client(altro_capo).get(f"{URL}/serie").json() == []
    tolta = _client(capo).delete(f"{URL}/serie/{serie['id']}")
    assert tolta.status_code == 200, tolta.content


def test_ordine_del_giorno_e_verbale(capo, akela, altro_capo, capogruppo, ragazza, genitore, csq):
    evento = _crea(capo, [akela, ragazza], ordine_del_giorno="<p>Passaggi</p>")
    odg = f"/api/v1/eventi/{evento.pk}/ordine-del-giorno"
    verbale = f"/api/v1/eventi/{evento.pk}/verbale"
    for chi in (capo, akela, capogruppo, ragazza, genitore):
        assert "Passaggi" in _client(chi).get(odg).json()["testo"]
    for chi in (altro_capo, csq):
        assert _client(chi).get(odg).status_code == 404
    candidati = {p["id"] for p in _client(capo).get(verbale).json()["candidati"]}
    assert candidati == {akela.pk, ragazza.pk}
    assert _put(akela, verbale, {"testo": "<p>Detto</p>"}).status_code == 403
    assert _put(capo, verbale, {"testo": "<p>Detto</p>"}).status_code == 200
    for chi in (akela, ragazza, genitore):
        assert _client(chi).get(verbale).status_code == 404  # a draft
    assert _post(capo, f"{verbale}/definitivo").status_code == 200
    for chi in (capo, akela, capogruppo, ragazza, genitore):
        assert _client(chi).get(verbale).status_code == 200
    for chi in (altro_capo, csq):
        assert _client(chi).get(verbale).status_code == 404


def _a() -> list[str]:
    return sorted(a for m in mail.outbox for a in m.to)


def test_avviso_ai_selezionati_e_ai_genitori(
    capo, akela, ragazza, genitore, csq, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        _crea(capo, [akela, ragazza])
    assert mail.outbox == []
    with django_capture_on_commit_callbacks(execute=True):
        evento = _crea(capo, [akela, ragazza], avvisa=True)
    assert _a() == ["akela@example.invalid", "genitore@example.invalid", "giulia@example.invalid"]
    assert f"/riunioni/{evento.pk}" in mail.outbox[0].body
    mail.outbox.clear()
    with django_capture_on_commit_callbacks(execute=True):
        _put(
            capo,
            f"{URL}/{evento.pk}/partecipanti",
            {"persone": [akela.pk, ragazza.pk, csq.pk], "avvisa": True},
        )
    assert _a() == ["csq@example.invalid"]


def test_una_sola_email_per_la_serie(
    capo, reparto, ragazza, genitore, django_capture_on_commit_callbacks
):
    corpo = _singola([reparto], giorno_settimana=5, avvisa=True)
    corpo |= {"giorno": None, "dal": _sabato(1).isoformat(), "al": _sabato(4).isoformat()}
    with django_capture_on_commit_callbacks(execute=True):
        assert _post(capo, URL, corpo).status_code == 201
    assert _a() == ["genitore@example.invalid", "giulia@example.invalid"]
    assert "ogni sabato, dalle 21:00 alle 22:30" in mail.outbox[0].body


def test_avviso_di_staff_solo_agli_invitati(
    capo, reparto, django_capture_on_commit_callbacks, estraneo
):
    RelazioneTutela.objects.create(tutore=estraneo, minore=capo, tipo="GENITORE")
    with django_capture_on_commit_callbacks(execute=True):
        _post(capo, URL, _singola([reparto], cerchia="STAFF", avvisa=True))
    assert _a() == [capo.utente.email]


# --- One's own events (DEC-432) -----------------------------------------------------------------


def test_miei_e_altri(capo, akela, capogruppo, ragazza, genitore, reparto):
    unita = Evento.objects.get(pk=_post(capo, URL, _singola([reparto])).json()[0]["id"])
    assert servizi.miei(capo.utente, [unita]) == {unita.pk}  # the unit they serve
    assert servizi.miei(genitore.utente, [unita]) == {unita.pk}
    assert servizi.miei(ragazza.utente, [unita]) == {unita.pk}
    for chi in (akela, capogruppo):
        assert servizi.miei(chi.utente, [unita]) == set()
    (letto,) = _client(capogruppo).get("/api/v1/calendario/eventi?vista=gruppo").json()
    assert letto["mio"] is False
    (letto,) = _client(capogruppo).get("/api/v1/eventi?riunioni=true").json()
    assert letto["mio"] is False
    unita.partecipazioni.update(stato=StatoPartecipazione.NON_PARTECIPA)
    assert servizi.miei(genitore.utente, [unita]) == set()


def test_mio_non_se_ho_detto_che_non_vengo(capo, akela, reparto):
    staff = Evento.objects.get(
        pk=_post(capo, URL, _singola([reparto], cerchia="STAFF")).json()[0]["id"]
    )
    staff.partecipazioni.update(stato=StatoPartecipazione.NON_PARTECIPA)
    assert servizi.miei(capo.utente, [staff]) == set()


def test_creatore_non_piu_capo_non_vede(capo, ragazza):
    evento = _crea(capo, [ragazza])
    Appartenenza.objects.filter(persona=capo).update(data_fine=timezone.localdate())
    assert not policy.eventi_visibili(capo.utente).filter(pk=evento.pk)
