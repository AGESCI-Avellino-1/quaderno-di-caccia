"""Leaving the group, recorded in the app (DEC-420)."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.test import Client
from django.utils import timezone

from apps.anagrafica.models import (
    Appartenenza,
    AppartenenzaSquadriglia,
    CorrezioneAnagrafica,
    UscitaDalGruppo,
)
from apps.anagrafica.servizi import inoltra_correzione, scarta_correzione
from apps.core.anno import AnnoAssociativo
from apps.organizzazione.models import Incarico, RuoloIncarico
from apps.quote.models import CategoriaQuota, Destinatari, Quota, TipoQuota

pytestmark = pytest.mark.django_db


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


def _url(persona) -> str:
    return f"/api/v1/persone/{persona.pk}/uscita"


def _esce(chi, persona, giorni_fa=0, quote=()):
    giorno = timezone.localdate() - timedelta(days=giorni_fa)
    return _client(chi).post(
        _url(persona), {"data": giorno.isoformat(), "quote": list(quote)}, "application/json"
    )


@pytest.fixture
def quota(ragazza):
    anno = AnnoAssociativo.corrente()
    tipo = TipoQuota.objects.create(
        nome="Censimento",
        categoria=CategoriaQuota.CENSIMENTO,
        anno=anno.anno_fine,
        importo=Decimal("40"),
        destinatari=Destinatari.TUTTI,
        scadenza=anno.inizio + timedelta(days=60),
    )
    return Quota.objects.create(
        tipo=tipo, persona=ragazza, periodo=anno.inizio, importo=40, scadenza=tipo.scadenza
    )


def test_chi_registra_l_uscita(capo, capogruppo, csq, ragazza, genitore, estraneo):
    for chi in (csq, genitore, estraneo):
        assert _client(chi).get(_url(ragazza)).status_code == 404
        assert _esce(chi, ragazza).status_code in (403, 404)
    # The staff for its ragazzi, never for a capo; the capigruppo for everyone.
    assert _client(capo).get(_url(ragazza)).json()["puo_registrare"]
    assert _client(capo).get(_url(capogruppo)).status_code == 404
    assert _esce(capo, capogruppo).status_code == 403
    assert _client(capogruppo).get(_url(capo)).json()["puo_registrare"]
    # Never in the future.
    risposta = _client(capo).post(
        _url(ragazza),
        {"data": (timezone.localdate() + timedelta(days=1)).isoformat()},
        "application/json",
    )
    assert risposta.status_code == 400


def test_uscita_chiude_tutto_e_si_annulla(capo, capogruppo, csq, genitore, quota, ragazza):
    vista = _client(capo).get(_url(ragazza)).json()
    assert [q["id"] for q in vista["quote"]] == [quota.pk]
    giorno = timezone.localdate() - timedelta(days=3)
    risposta = _esce(capo, ragazza, giorni_fa=3, quote=[quota.pk])
    assert risposta.status_code == 200, risposta.content
    uscita = risposta.json()["uscita"]
    assert uscita["data"] == giorno.isoformat() and uscita["puo_annullare"]
    assert uscita["stato"] == "Da inoltrare alla segreteria"
    # Out of the unit and of the patrol from that day; the fee cancelled with the reason.
    assert not Appartenenza.objects.attive().filter(persona=ragazza).exists()
    assert Appartenenza.objects.get(persona=ragazza).data_fine == giorno
    assert not AppartenenzaSquadriglia.objects.attive().filter(persona=ragazza).exists()
    quota.refresh_from_db()
    assert quota.annullata_il and quota.motivo_annullamento == "Ha lasciato il gruppo"
    correzione = CorrezioneAnagrafica.objects.get(persona=ragazza, campo="uscita")
    assert correzione.stato == "IN_ATTESA"
    # The capigruppo find it among the corrections to forward.
    elenco = _client(capogruppo).get("/api/v1/correzioni").json()
    assert "Uscita dal gruppo" in str(elenco)
    # The parent still enters and sees the child's file.
    assert _client(genitore).get(f"/api/v1/persone/{ragazza.pk}").status_code == 200
    # Twice: no.
    assert _esce(capo, ragazza).status_code in (400, 403)

    # Undone: everything back, nothing left to forward.
    assert _client(capo).post(f"{_url(ragazza)}/annulla").status_code == 200
    assert Appartenenza.objects.attive().get(persona=ragazza).data_fine is None
    assert AppartenenzaSquadriglia.objects.attive().filter(persona=ragazza).exists()
    quota.refresh_from_db()
    assert quota.annullata_il is None
    assert not CorrezioneAnagrafica.objects.filter(campo="uscita").exists()
    assert UscitaDalGruppo.objects.get().annullata_il is not None


def test_il_csq_perde_l_incarico(capo, csq):
    _esce(capo, csq)
    assert not Incarico.objects.attivi().filter(persona=csq, ruolo=RuoloIncarico.CSQ).exists()
    _client(capo).post(f"{_url(csq)}/annulla")
    assert Incarico.objects.attivi().filter(persona=csq, ruolo=RuoloIncarico.CSQ).exists()


def test_scartata_dal_capogruppo_si_annulla(capo, capogruppo, ragazza):
    _esce(capo, ragazza, giorni_fa=1)
    correzione = CorrezioneAnagrafica.objects.get(campo="uscita")
    inoltra_correzione(correzione, capogruppo.utente)
    scarta_correzione(correzione, capogruppo.utente, "Errore")
    assert Appartenenza.objects.attive().filter(persona=ragazza).exists()
    assert UscitaDalGruppo.objects.get().annullata_il is not None


def test_annullata_dopo_l_inoltro_resta_scartata(capo, capogruppo, ragazza):
    _esce(capo, ragazza)
    correzione = CorrezioneAnagrafica.objects.get(campo="uscita")
    inoltra_correzione(correzione, capogruppo.utente)
    assert _client(capo).post(f"{_url(ragazza)}/annulla").status_code == 200
    correzione.refresh_from_db()
    assert correzione.stato == "SCARTATA"
