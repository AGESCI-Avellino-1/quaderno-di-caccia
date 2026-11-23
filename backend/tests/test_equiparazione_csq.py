"""A member treated as the patrol's CSQ by the reparto staff (DEC-419)."""

from datetime import date, datetime, timedelta

import pytest
from django.test import Client
from django.utils import timezone

from apps.anagrafica.models import AppartenenzaSquadriglia
from apps.core.anno import AnnoAssociativo
from apps.eventi import servizi as eventi
from apps.eventi.models import Cerchia, Evento, Livello, TipoEvento
from apps.organizzazione.models import EquiparazioneCsq, Squadriglia
from apps.permessi import policy
from tests.conftest import INIZIO_ANNO

pytestmark = pytest.mark.django_db


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


def _membro(persona) -> AppartenenzaSquadriglia:
    return AppartenenzaSquadriglia.objects.attive().get(persona=persona)


def _equipara(chi, persona, attiva: bool = True):
    return _client(chi).put(
        f"/api/v1/membri-squadriglia/{_membro(persona).pk}/equiparazione",
        {"attiva": attiva},
        "application/json",
    )


def test_lo_staff_del_reparto_equipara(capo, capogruppo, csq, ragazza, genitore, estraneo):
    # The capogruppo is not in the reparto staff: as for appointing CSQ and VCSQ.
    for chi in (capogruppo, csq, ragazza, genitore, estraneo):
        assert _equipara(chi, ragazza).status_code in (403, 404)
    assert not policy.squadriglie_guidate(ragazza.utente).exists()

    risposta = _equipara(capo, ragazza)
    assert risposta.status_code == 200 and risposta.json()["equiparato"]
    equiparazione = EquiparazioneCsq.objects.get()
    # Until 30 September included.
    assert equiparazione.data_fine - timedelta(days=1) == AnnoAssociativo.corrente().fine
    # Twice changes nothing; the CSQ cannot be treated as one.
    assert _equipara(capo, ragazza).status_code == 200
    assert EquiparazioneCsq.objects.count() == 1
    assert _equipara(capo, csq).status_code == 400

    # The unit page tells the staff.
    unita = _client(capo).get(f"/api/v1/unita/{ragazza.appartenenze.first().unita_id}").json()
    sq = unita["squadriglie"][0]
    assert sq["puo_equiparare"]
    assert {m["persona"]["id"]: m["equiparato"] for m in sq["membri"]}[ragazza.pk]

    # Turned off the same day it was turned on: as if it never was.
    assert _equipara(capo, ragazza, False).json()["equiparato"] is False
    assert not EquiparazioneCsq.objects.exists()


def test_vede_e_fa_come_il_capo_squadriglia(capo, csq, ragazza, squadriglia):
    _equipara(capo, ragazza)
    assert list(policy.squadriglie_guidate(ragazza.utente)) == [squadriglia]
    # The real CSQ stays.
    assert list(policy.squadriglie_guidate(csq.utente)) == [squadriglia]
    # The CSQ's view of a patrol mate.
    assert policy._csq_di(ragazza.utente, csq)
    assert policy.puo_nominare(ragazza.utente, "CASSIERE", squadriglia=squadriglia)
    assert not policy.puo_nominare(ragazza.utente, "VCSQ", squadriglia=squadriglia)

    mia = _client(ragazza).get("/api/v1/mia-squadriglia").json()[0]
    assert mia["sono_capo"]
    assert mia["equiparato_fino_al"] == AnnoAssociativo.corrente().fine.isoformat()
    # The others never learn it.
    mia = _client(csq).get("/api/v1/mia-squadriglia").json()[0]
    assert mia["equiparato_fino_al"] is None
    assert "equiparato" not in str(mia["membri"])


def test_chi_sa_dell_equiparazione(capo, csq, ragazza, genitore):
    _equipara(capo, ragazza)
    url = f"/api/v1/persone/{ragazza.pk}/incarichi-squadriglia"
    fine = AnnoAssociativo.corrente().fine.isoformat()
    for chi in (capo, ragazza, genitore):
        assert _client(chi).get(url).json()["equiparato_fino_al"] == fine
    # A patrol mate sees only the assigned roles.
    assert _client(csq).get(url).json()["equiparato_fino_al"] is None
    url = f"/api/v1/squadriglie/{_membro(ragazza).squadriglia_id}/incarichi"
    assert _client(ragazza).get(url).json()["equiparato_fino_al"] is None


def test_finisce_con_l_anno_o_con_la_squadriglia(capo, ragazza, squadriglia, reparto):
    EquiparazioneCsq.objects.create(
        appartenenza=_membro(ragazza),
        data_inizio=INIZIO_ANNO,
        data_fine=AnnoAssociativo.corrente().fine + timedelta(days=1),
    )
    assert EquiparazioneCsq.objects.attive().exists()
    assert not EquiparazioneCsq.objects.attive(
        AnnoAssociativo.corrente().successivo().inizio
    ).exists()

    # Moving to another patrol ends it.
    altra = Squadriglia.objects.create(unita=reparto, nome="Volpi", sesso="F")
    assert (
        _client(capo)
        .post(
            f"/api/v1/squadriglie/{altra.pk}/membri", {"persona_id": ragazza.pk}, "application/json"
        )
        .status_code
        == 201
    )
    assert not policy.squadriglie_guidate(ragazza.utente).exists()
    # The record stays, as history.
    assert EquiparazioneCsq.objects.count() == 1


def test_invitata_al_consiglio_capi(capo, csq, ragazza, reparto):
    inizio = timezone.localtime() + timedelta(days=3)
    consiglio = Evento.objects.create(
        titolo="Consiglio Capi",
        tipo=TipoEvento.RIUNIONE,
        livello=Livello.UNITA,
        cerchia=Cerchia.CONSIGLIO_CAPI,
        inizio=inizio,
        fine=inizio + timedelta(hours=2),
    )
    consiglio.unita.set([reparto])
    assert set(eventi._previsti_base(consiglio)) == {csq}
    _equipara(capo, ragazza)
    assert set(eventi._previsti_base(consiglio)) == {csq, ragazza}
    # A council after 30 September: not any more.
    ottobre = AnnoAssociativo.corrente().successivo().inizio
    consiglio.inizio = timezone.make_aware(datetime(ottobre.year, ottobre.month, 2, 18))
    consiglio.fine = consiglio.inizio + timedelta(hours=2)
    consiglio.save()
    assert set(eventi._previsti_base(consiglio)) == {csq}
    assert date.today() < consiglio.inizio.date()
