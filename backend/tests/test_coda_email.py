"""Emails to many a few at a time (DEC-311)."""

from datetime import timedelta

import pytest
from django.core import mail
from django.core.mail import EmailMessage, mailers
from django.test import Client
from django.utils import timezone

from apps.impostazioni import coda
from apps.impostazioni.models import EmailInCoda, Impostazioni
from apps.impostazioni.posta import INTESTAZIONE_TIPO
from tests.test_impostazioni import MAILERS_VERI

pytestmark = pytest.mark.django_db


@pytest.fixture
def con_coda(settings):
    settings.MAILERS = MAILERS_VERI
    settings.QDC_EMAIL_IN_CODA = True
    imp = Impostazioni.carica()
    imp.email_capi = imp.email_genitori = imp.email_ragazzi = True
    imp.coda_blocco, imp.coda_pausa_minuti, imp.coda_massimo_giorno = 3, 2, 5
    imp.save()
    return imp


def _manda(tipo: str, *indirizzi: str) -> None:
    mailers["default"].send_messages(
        [
            EmailMessage(subject="Prova", body="Testo", to=[a], headers={INTESTAZIONE_TIPO: tipo})
            for a in indirizzi
        ]
    )


def _indirizzi(n: int) -> list[str]:
    return [f"persona{i}@example.invalid" for i in range(n)]


def test_chiesto_dalla_persona_parte_subito(con_coda):
    _manda("codice_accesso", "a@example.invalid")
    assert [m.to for m in mail.outbox] == [["a@example.invalid"]]
    assert not EmailInCoda.objects.exists()


def test_le_altre_aspettano_in_coda(con_coda):
    _manda("invito", *_indirizzi(4))
    assert mail.outbox == []
    assert coda.stato()["in_attesa"] == 4


def test_un_blocco_poi_la_pausa_poi_il_massimo_del_giorno(con_coda):
    _manda("evento_nuovo", *_indirizzi(7))
    adesso = timezone.now()
    assert coda.smaltisci(adesso) == 3
    assert coda.smaltisci(adesso + timedelta(minutes=1)) == 0  # still in the pause
    assert coda.smaltisci(adesso + timedelta(minutes=3)) == 2  # 5 a day at most
    assert coda.smaltisci(adesso + timedelta(minutes=6)) == 0
    assert len(mail.outbox) == 5
    assert coda.stato() == {"in_attesa": 2, "inviate_oggi": 5, "abbandonate": 0}
    # In order, the same message as built.
    assert mail.outbox[0].to == ["persona0@example.invalid"]
    assert mail.outbox[0].message()["Subject"] == "Prova"


def test_inviate_svuotate_e_poi_cancellate(con_coda):
    _manda("evento_nuovo", "a@example.invalid")
    coda.smaltisci()
    voce = EmailInCoda.objects.get()
    assert voce.inviata_il and bytes(voce.messaggio) == b"" and voce.destinatari == []
    coda.smaltisci(timezone.now() + timedelta(days=3))
    assert not EmailInCoda.objects.exists()


def test_errore_riprova_poi_abbandona(con_coda, monkeypatch):
    class Guasto:
        def send_messages(self, messaggi):
            raise ConnectionRefusedError("server giù")

    monkeypatch.setattr("apps.impostazioni.posta.connessione", lambda imp: Guasto())
    _manda("evento_nuovo", "a@example.invalid", "b@example.invalid")
    for _ in range(coda.TENTATIVI_MASSIMI):
        assert coda.smaltisci() == 0
    voce = EmailInCoda.objects.first()
    assert voce.abbandonata and voce.ultimo_errore == "ConnectionRefusedError"
    assert coda.stato()["abbandonate"] == 1
    assert coda.riprova_abbandonate() == 1
    assert coda.stato()["in_attesa"] == 2


def test_senza_coda_parte_tutto_subito(con_coda, settings):
    settings.QDC_EMAIL_IN_CODA = False
    _manda("invito", *_indirizzi(3))
    assert len(mail.outbox) == 3


def test_impostazioni_solo_amministratore_tecnico(con_coda, capo, capogruppo):
    from apps.organizzazione.models import Incarico, RuoloIncarico
    from tests.conftest import INIZIO_ANNO

    Incarico.objects.create(
        persona=capo,
        ruolo=RuoloIncarico.AMMINISTRATORE,
        gruppo=capogruppo.incarichi.first().gruppo,
        data_inizio=INIZIO_ANNO,
    )
    dati = {"blocco": 10, "pausa_minuti": 5, "massimo_giorno": 300}
    for chi, atteso in ((capogruppo, 403), (capo, 200)):
        client = Client()
        client.force_login(chi.utente)
        risposta = client.put(
            "/api/v1/impostazioni/coda-email", dati, content_type="application/json"
        )
        assert risposta.status_code == atteso
    imp = Impostazioni.carica()
    assert (imp.coda_blocco, imp.coda_pausa_minuti, imp.coda_massimo_giorno) == (10, 5, 300)
    client.force_login(capo.utente)
    sbagliati = {"blocco": 50, "pausa_minuti": 1, "massimo_giorno": 10}
    assert (
        client.put(
            "/api/v1/impostazioni/coda-email", sbagliati, content_type="application/json"
        ).status_code
        == 400
    )
    assert client.get("/api/v1/impostazioni").json()["coda_blocco"] == 10
