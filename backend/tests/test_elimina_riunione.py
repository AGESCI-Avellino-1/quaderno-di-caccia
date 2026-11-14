"""Deleting a meeting for good, not only cancelling it (DEC-413)."""

from datetime import timedelta

import pytest
from django.core import mail
from django.core.files.base import ContentFile
from django.test import Client
from django.utils import timezone

from apps.eventi import servizi
from apps.eventi.models import Evento, Livello, Partecipazione, Presenza, TipoEvento
from apps.impostazioni.models import Impostazioni
from apps.verbali.models import AllegatoVerbale, Verbale
from tests.test_cassa import _uscita, contanti  # noqa: F401

pytestmark = pytest.mark.django_db


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


@pytest.fixture(autouse=True)
def email_accese():
    imp = Impostazioni.carica()
    imp.email_capi = imp.email_genitori = imp.email_ragazzi = True
    imp.save()


@pytest.fixture
def riunione(capo, reparto, ragazza, genitore) -> Evento:
    inizio = timezone.now() + timedelta(days=7)
    evento = servizi.crea(
        Evento(
            titolo="Riunione di reparto",
            tipo=TipoEvento.RIUNIONE,
            livello=Livello.UNITA,
            inizio=inizio,
            fine=inizio + timedelta(hours=2),
        ),
        [reparto],
        capo.utente,
    )
    assert Partecipazione.objects.filter(evento=evento, persona=ragazza).exists()
    return evento


def _elimina(chi, evento, avvisa=False):
    url = f"/api/v1/riunioni/{evento.pk}" + ("?avvisa=true" if avvisa else "")
    return _client(chi).delete(url)


def test_lo_staff_elimina_una_riunione_vuota(capo, riunione):
    dettaglio = _client(capo).get(f"/api/v1/eventi/{riunione.pk}").json()
    assert dettaglio["puo_eliminare"] is True
    assert dettaglio["si_perde"] == []
    assert _elimina(capo, riunione).status_code == 204
    assert not Evento.objects.filter(pk=riunione.pk).exists()
    assert not Partecipazione.objects.filter(evento_id=riunione.pk).exists()
    assert mail.outbox == []  # nobody told unless asked


def test_avvisa_gli_invitati_se_lo_chiede(capo, riunione, genitore):
    assert _elimina(capo, riunione, avvisa=True).status_code == 204
    assert mail.outbox
    [email] = [e for e in mail.outbox if genitore.utente.email in e.to]
    assert "Annullata" in email.subject
    assert f"/riunioni/{riunione.pk}" not in email.body  # the page is gone


def test_con_presenze_solo_un_capogruppo(capo, capogruppo, riunione, ragazza):
    Presenza.objects.create(evento=riunione, persona=ragazza, stato="PRESENTE")
    assert _client(capo).get(f"/api/v1/eventi/{riunione.pk}").json()["puo_eliminare"] is False
    assert _elimina(capo, riunione).status_code == 403
    dettaglio = _client(capogruppo).get(f"/api/v1/eventi/{riunione.pk}").json()
    assert dettaglio["si_perde"] == ["le presenze segnate (1)"]
    assert _elimina(capogruppo, riunione).status_code == 204
    assert not Presenza.objects.filter(evento_id=riunione.pk).exists()


def test_con_il_verbale_e_i_suoi_allegati(
    capogruppo, riunione, monkeypatch, django_capture_on_commit_callbacks
):
    from apps.archivio import drive

    tolti = []
    monkeypatch.setattr(drive, "cancella", tolti.append)
    verbale = Verbale.objects.create(evento=riunione, testo="<p>Scritto.</p>")
    sul_drive = AllegatoVerbale.objects.create(
        verbale=verbale, nome_file="a.pdf", tipo_file="application/pdf", dimensione=1, drive_id="X1"
    )
    sul_server = AllegatoVerbale(
        verbale=verbale, nome_file="b.pdf", tipo_file="application/pdf", dimensione=1
    )
    sul_server.file.save("prova.pdf", ContentFile(b"%PDF"), save=True)
    percorso = sul_server.file.path
    dettaglio = _client(capogruppo).get(f"/api/v1/eventi/{riunione.pk}").json()
    assert "il verbale" in dettaglio["si_perde"]
    assert "gli allegati del verbale (2)" in dettaglio["si_perde"]
    with django_capture_on_commit_callbacks(execute=True):
        assert _elimina(capogruppo, riunione).status_code == 204
    assert not Verbale.objects.filter(pk=verbale.pk).exists()
    assert not AllegatoVerbale.objects.filter(pk__in=[sul_drive.pk, sul_server.pk]).exists()
    assert tolti == ["X1"]
    import os

    assert not os.path.exists(percorso)


def test_con_movimenti_di_cassa_solo_annullare(capogruppo, riunione, contanti):  # noqa: F811
    _uscita(contanti, evento=riunione, data=timezone.localdate())
    risposta = _elimina(capogruppo, riunione)
    assert risposta.status_code == 400
    assert "movimenti di cassa" in risposta.json()["detail"]
    assert Evento.objects.filter(pk=riunione.pk).exists()


def test_un_evento_non_si_elimina_cosi(capogruppo, reparto, capo):
    inizio = timezone.now() + timedelta(days=7)
    uscita = servizi.crea(
        Evento(
            titolo="Uscita",
            tipo=TipoEvento.USCITA,
            livello=Livello.UNITA,
            inizio=inizio,
            fine=inizio + timedelta(hours=8),
        ),
        [reparto],
        capo.utente,
    )
    assert _elimina(capogruppo, uscita).status_code == 403


@pytest.mark.parametrize("ruolo", ["csq", "ragazza", "genitore"])
def test_gli_altri_no(request, ruolo, riunione):
    chi = request.getfixturevalue(ruolo)
    assert _elimina(chi, riunione).status_code in (403, 404)  # 404: not invited, unseen
    assert Evento.objects.filter(pk=riunione.pk).exists()


def test_chi_non_la_vede_non_la_trova(estraneo, riunione):
    assert _elimina(estraneo, riunione).status_code == 404
