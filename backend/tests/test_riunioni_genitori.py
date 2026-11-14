"""Meetings of the parents and their convocation (DEC-325, DEC-327)."""

from datetime import timedelta

import pytest
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.utils import timezone

from apps.anagrafica.models import (
    Appartenenza,
    RelazioneTutela,
    RuoloAppartenenza,
    TipoTutela,
    VisibilitaGenitori,
)
from apps.eventi import servizi as eventi
from apps.eventi.models import Evento, Presenza, RiunioneRicorrente
from apps.impostazioni.models import Impostazioni
from apps.organizzazione.models import Incarico, RuoloIncarico, TipoUnita, Unita
from apps.permessi import policy
from apps.verbali import convocazione, servizi
from apps.verbali.models import AllegatoVerbale, TipoVerbale
from tests.conftest import INIZIO_ANNO, crea_capo, crea_persona, nato_anni_fa

pytestmark = pytest.mark.django_db

PDF = b"%PDF-1.4 prova"


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


def _post(chi, url, dati=None):
    return _client(chi).post(url, dati or {}, content_type="application/json")


def _dati(**altro) -> dict:
    giorno = timezone.localdate() + timedelta(days=10)
    return {
        "cerchia": "GENITORI",
        "giorno": giorno.isoformat(),
        "ora_inizio": "18:00",
        "ora_fine": "19:30",
        **altro,
    }


@pytest.fixture(autouse=True)
def email_accese():
    imp = Impostazioni.carica()
    imp.email_capi = imp.email_genitori = imp.email_ragazzi = True
    imp.save()


@pytest.fixture
def staff(reparto, coca):
    persona = crea_capo("Elena", "Staff", "staff-gen@example.invalid")
    Incarico.objects.create(
        persona=persona, ruolo=RuoloIncarico.STAFF, unita=reparto, data_inizio=INIZIO_ANNO
    )
    return persona


@pytest.fixture
def clan(gruppo) -> Unita:
    return Unita.objects.create(gruppo=gruppo, nome="Clan", tipo=TipoUnita.CLAN_FUOCO)


@pytest.fixture
def adulto(clan):
    """A rover of age, with a parent."""
    persona = crea_persona("Rino", "Rover", "rino@example.invalid", data_nascita=nato_anni_fa(19))
    Appartenenza.objects.create(
        persona=persona, unita=clan, ruolo=RuoloAppartenenza.RAGAZZO, data_inizio=INIZIO_ANNO
    )
    return persona


@pytest.fixture
def genitore_adulto(adulto):
    persona = crea_persona("Pia", "Rover", "pia@example.invalid", data_nascita=nato_anni_fa(50))
    RelazioneTutela.objects.create(tutore=persona, minore=adulto, tipo=TipoTutela.GENITORE)
    return persona


def _crea(chi, **altro) -> Evento:
    risposta = _post(chi, "/api/v1/riunioni", _dati(**altro))
    assert risposta.status_code == 201, risposta.content
    return Evento.objects.get(pk=risposta.json()[0]["id"])


def _invitati(evento) -> set[int]:
    return set(evento.partecipazioni.values_list("persona_id", flat=True))


# --- Creating -----------------------------------------------------------------------------


def test_chi_crea(capo, staff, capogruppo, csq, genitore, estraneo, reparto, clan):
    unita = {"unita": [reparto.pk]}
    for chi in (csq, genitore, estraneo):
        assert _post(chi, "/api/v1/riunioni", _dati(**unita)).status_code == 403
    assert _post(staff, "/api/v1/riunioni", _dati(unita=[clan.pk])).status_code == 403
    assert _post(staff, "/api/v1/riunioni", _dati(**unita)).status_code == 201
    assert _post(capogruppo, "/api/v1/riunioni", _dati(**unita)).status_code == 201
    # The whole group: the capigruppo only.
    assert _post(capo, "/api/v1/riunioni", _dati(di_gruppo=True)).status_code == 403
    assert _post(capogruppo, "/api/v1/riunioni", _dati(di_gruppo=True)).status_code == 201


def test_titolo_e_una_sola_alla_volta(capogruppo, reparto):
    evento = _crea(capogruppo, unita=[reparto.pk])
    assert evento.titolo == f"Riunione dei genitori di {reparto}"
    assert evento.convocata_il is None
    assert _crea(capogruppo, di_gruppo=True).titolo == "Riunione dei genitori"
    serie = {
        "cerchia": "GENITORI",
        "unita": [reparto.pk],
        "ora_inizio": "18:00",
        "ora_fine": "19:00",
        "giorno_settimana": 5,
        "dal": "2026-11-01",
        "al": "2026-12-01",
    }
    assert _post(capogruppo, "/api/v1/riunioni", serie).status_code == 400
    assert not RiunioneRicorrente.objects.exists()


def test_piu_unita_anche_non_collegate(capogruppo, reparto, clan):
    evento = _crea(capogruppo, unita=[reparto.pk, clan.pk])
    assert evento.unita.count() == 2


def test_di_gruppo_solo_per_i_genitori(capogruppo):
    corpo = _dati(cerchia="TUTTI", di_gruppo=True)
    assert _post(capogruppo, "/api/v1/riunioni", corpo).status_code == 400


# --- Who is invited -----------------------------------------------------------------------


def test_invitati_di_unita(capogruppo, capo, staff, ragazza, csq, genitore, reparto, adulto):
    evento = _crea(capogruppo, unita=[reparto.pk])
    invitati = _invitati(evento)
    # The parents and the staff; not the children, nor the capi of other units.
    assert genitore.pk in invitati
    assert {capo.pk, staff.pk} <= invitati
    assert not {ragazza.pk, csq.pk, adulto.pk, capogruppo.pk} & invitati


def test_entrambi_i_genitori(capogruppo, reparto, genitore, ragazza):
    altra = crea_persona("Altra", "Madre", "altra@example.invalid", data_nascita=nato_anni_fa(45))
    RelazioneTutela.objects.create(tutore=altra, minore=ragazza, tipo=TipoTutela.GENITORE)
    senza = crea_persona("Senza", "Resp", data_nascita=nato_anni_fa(45))
    RelazioneTutela.objects.create(
        tutore=senza, minore=ragazza, tipo=TipoTutela.GENITORE, responsabilita_genitoriale=False
    )
    invitati = _invitati(_crea(capogruppo, unita=[reparto.pk]))
    assert {genitore.pk, altra.pk} <= invitati
    assert senza.pk not in invitati


def test_di_gruppo_invita_tutta_la_coca(capogruppo, capo, staff, genitore, genitore_adulto):
    invitati = _invitati(_crea(capogruppo, di_gruppo=True))
    assert {capogruppo.pk, capo.pk, staff.pk, genitore.pk, genitore_adulto.pk} <= invitati


def test_il_maggiorenne_va_al_posto_dei_genitori(capogruppo, adulto, genitore_adulto, clan):
    evento = _crea(capogruppo, unita=[clan.pk])
    assert genitore_adulto.pk in _invitati(evento)
    assert adulto.pk not in _invitati(evento)
    url = f"/api/v1/persone/{adulto.pk}/visibilita-genitori"
    risposta = _client(adulto).put(
        url,
        {
            "contatti": True,
            "sanitarie": True,
            "scheda": True,
            "quote": True,
            "al_posto_dei_genitori": True,
        },
        content_type="application/json",
    )
    assert risposta.status_code == 200, risposta.content
    assert risposta.json()["al_posto_dei_genitori"] is True
    # The meeting to come changes by itself.
    assert adulto.pk in _invitati(evento)
    assert genitore_adulto.pk not in _invitati(evento)
    assert _invitati(_crea(capogruppo, unita=[clan.pk])) >= {adulto.pk}


def test_il_cambio_non_tocca_chi_ha_una_presenza(capogruppo, adulto, genitore_adulto, clan):
    evento = _crea(capogruppo, unita=[clan.pk])
    Presenza.objects.create(evento=evento, persona=genitore_adulto, stato="PRESENTE")
    VisibilitaGenitori.objects.create(persona=adulto, al_posto_dei_genitori=True)
    eventi.riallinea_riunioni_genitori()
    assert genitore_adulto.pk in _invitati(evento)


def test_il_minorenne_non_sceglie(capogruppo, ragazza, genitore, reparto):
    VisibilitaGenitori.objects.create(persona=ragazza, al_posto_dei_genitori=True)
    invitati = _invitati(_crea(capogruppo, unita=[reparto.pk]))
    assert genitore.pk in invitati
    assert ragazza.pk not in invitati


# --- Attendance and absence ---------------------------------------------------------------


def test_presenze_e_niente_assenza_da_comunicare(staff, capogruppo, genitore, ragazza, reparto):
    evento = _crea(staff, unita=[reparto.pk])
    assert policy.puo_segnare_presenze(staff.utente, evento)
    assert not policy.puo_segnare_presenze(genitore.utente, evento)
    assert not policy.puo_segnalare_assenza(genitore.utente, genitore, evento)
    assert not policy.puo_segnalare_assenza(staff.utente, genitore, evento)
    dettaglio = _client(genitore).get(f"/api/v1/eventi/{evento.pk}").json()
    assert all(not m["puo_segnalare"] for m in dettaglio["mie"])
    # Attendance of the parent, not of the child.
    Presenza.objects.create(evento=evento, persona=genitore, stato="PRESENTE")
    assert not Presenza.objects.filter(persona=ragazza).exists()


def test_chi_vede_la_riunione(capo, genitore, ragazza, estraneo, reparto, capogruppo):
    evento = _crea(capogruppo, unita=[reparto.pk])
    assert policy.eventi_visibili(genitore.utente).filter(pk=evento.pk).exists()
    assert policy.eventi_visibili(capo.utente).filter(pk=evento.pk).exists()
    assert not policy.eventi_visibili(ragazza.utente).filter(pk=evento.pk).exists()
    assert not policy.eventi_visibili(estraneo.utente).filter(pk=evento.pk).exists()


def test_non_conta_per_i_turni(capogruppo, reparto):
    from apps.eventi.turni import assegnazioni

    assert assegnazioni(_crea(capogruppo, unita=[reparto.pk])) == []


# --- Convocation --------------------------------------------------------------------------


def _carica(chi, evento, nome="programma.pdf", contenuto=PDF):
    risposta = _post(
        chi,
        f"/api/v1/eventi/{evento.pk}/convocazione/allegati",
        {"nome": nome, "dimensione": len(contenuto)},
    )
    if risposta.status_code != 201:
        return risposta
    return _client(chi).post(
        f"/api/v1/allegati-verbale/{risposta.json()['id']}/pezzo",
        {"inizio": 0, "file": SimpleUploadedFile("pezzo", contenuto)},
    )


def _alla_consegna(django_capture_on_commit_callbacks, funzione):
    with django_capture_on_commit_callbacks(execute=True):
        return funzione()


def test_convocazione_con_allegati(
    staff, genitore, capo, reparto, django_capture_on_commit_callbacks
):
    evento = _crea(staff, unita=[reparto.pk])
    mail.outbox.clear()
    # Added before the convocation: no email, it goes with it.
    risposta = _alla_consegna(django_capture_on_commit_callbacks, lambda: _carica(staff, evento))
    assert risposta.status_code == 200, risposta.content
    assert mail.outbox == []
    url = f"/api/v1/eventi/{evento.pk}/convocazione"
    assert _client(genitore).get(url).json()["puo_inviare"] is False
    assert _post(genitore, f"{url}/invia").status_code == 403
    assert _post(staff, f"{url}/invia").status_code == 200
    destinatari = {m.to[0] for m in mail.outbox}
    assert genitore.utente.email in destinatari or genitore.email in destinatari
    email = mail.outbox[0]
    assert email.subject.startswith("Convocazione:")
    assert [a[0] for a in email.attachments] == ["programma.pdf"]
    assert "In allegato: programma.pdf" in email.body
    # Once only.
    assert _post(staff, f"{url}/invia").status_code == 400


def test_allegato_aggiunto_dopo(staff, reparto, django_capture_on_commit_callbacks):
    evento = _crea(staff, unita=[reparto.pk])
    assert _post(staff, f"/api/v1/eventi/{evento.pk}/convocazione/invia").status_code == 200
    mail.outbox.clear()
    risposta = _alla_consegna(
        django_capture_on_commit_callbacks, lambda: _carica(staff, evento, "nuovo.pdf")
    )
    assert risposta.status_code == 200
    assert mail.outbox[0].subject.startswith("Nuovo documento:")
    assert [a[0] for a in mail.outbox[0].attachments] == ["nuovo.pdf"]


def test_allegato_troppo_grande_solo_link(staff, reparto, monkeypatch):
    monkeypatch.setattr(convocazione, "MASSIMO_NELL_EMAIL", 5)
    evento = _crea(staff, unita=[reparto.pk])
    assert _carica(staff, evento).status_code == 200
    mail.outbox.clear()
    assert _post(staff, f"/api/v1/eventi/{evento.pk}/convocazione/invia").status_code == 200
    assert mail.outbox[0].attachments == []
    assert "Da aprire nell'app" in mail.outbox[0].body
    assert f"/eventi/{evento.pk}" in mail.outbox[0].body


def test_email_arriva_anche_a_chi_le_ha_spente(staff, genitore, reparto):
    imp = Impostazioni.carica()
    imp.email_genitori = False
    imp.save()
    evento = _crea(staff, unita=[reparto.pk])
    mail.outbox.clear()
    assert _post(staff, f"/api/v1/eventi/{evento.pk}/convocazione/invia").status_code == 200
    assert mail.outbox  # always sent


def test_chi_legge_gli_allegati_prima_del_verbale(
    staff, capo, genitore, ragazza, estraneo, reparto
):
    evento = _crea(staff, unita=[reparto.pk])
    assert _carica(staff, evento).status_code == 200
    allegato = AllegatoVerbale.objects.get()
    url = f"/api/v1/allegati-verbale/{allegato.pk}"
    for chi in (staff, capo, genitore):
        assert _client(chi).get(url).status_code == 200
    for chi in (ragazza, estraneo):
        assert _client(chi).get(url).status_code == 404
        assert _client(chi).get(f"/api/v1/eventi/{evento.pk}/convocazione").status_code == 404
    elenco = _client(genitore).get(f"/api/v1/eventi/{evento.pk}/convocazione").json()
    assert [a["nome_file"] for a in elenco["allegati"]] == ["programma.pdf"]
    assert elenco["puo_gestire"] is False
    # Who may read them may not change them.
    assert _client(genitore).delete(url).status_code == 403
    assert _client(staff).delete(url).status_code == 204


def test_solo_le_riunioni_dei_genitori_hanno_la_convocazione(capo, reparto, staff):
    risposta = _post(
        staff,
        "/api/v1/riunioni",
        {
            "unita": [reparto.pk],
            "cerchia": "CONCA",
            "giorno": _dati()["giorno"],
            "ora_inizio": "18:00",
            "ora_fine": "19:00",
        },
    )
    assert risposta.status_code == 201
    url = f"/api/v1/eventi/{risposta.json()[0]['id']}/convocazione"
    assert _client(staff).get(url).status_code == 404


def test_avvisi_ai_soli_invitati_non_alle_loro_famiglie(capogruppo, genitore, reparto):
    """Moved: the parent is told, not who the parent is the child of."""
    nonna = crea_persona("Nonna", "Prova", "nonna@example.invalid", data_nascita=nato_anni_fa(75))
    RelazioneTutela.objects.create(tutore=nonna, minore=genitore, tipo=TipoTutela.GENITORE)
    evento = _crea(capogruppo, unita=[reparto.pk])
    mail.outbox.clear()
    from apps.eventi import avvisi

    assert avvisi.modificato(evento) >= 1
    destinatari = {m.to[0] for m in mail.outbox}
    assert "nonna@example.invalid" not in destinatari


# --- Minutes ------------------------------------------------------------------------------


def _testo(chi, evento, testo="<p>Si è deciso.</p>"):
    return _client(chi).put(
        f"/api/v1/eventi/{evento.pk}/verbale", {"testo": testo}, content_type="application/json"
    )


def test_chi_scrive_il_verbale(staff, capogruppo, capo, genitore, reparto, clan):
    di_uno = _crea(capogruppo, unita=[reparto.pk])
    assert servizi.tipo_di(di_uno) == TipoVerbale.GENITORI
    assert _testo(staff, di_uno).status_code == 200
    assert _testo(capogruppo, di_uno).status_code == 200
    assert _testo(genitore, di_uno).status_code == 403
    # Of more units or of the group: the capigruppo only.
    di_due = _crea(capogruppo, unita=[reparto.pk, clan.pk])
    assert _testo(staff, di_due).status_code == 403
    assert _testo(capogruppo, di_due).status_code == 200
    di_gruppo = _crea(capogruppo, di_gruppo=True)
    assert _testo(capo, di_gruppo).status_code == 403
    assert _testo(capogruppo, di_gruppo).status_code == 200


def test_chi_legge_il_verbale(capogruppo, capo, genitore, ragazza, estraneo, reparto):
    evento = _crea(capogruppo, unita=[reparto.pk])
    assert _testo(capogruppo, evento).status_code == 200
    url = f"/api/v1/eventi/{evento.pk}/verbale"
    assert _client(genitore).get(url).status_code == 404  # still a draft
    assert _post(capogruppo, f"{url}/definitivo").status_code == 200
    for chi in (capo, capogruppo, genitore):
        assert _client(chi).get(url).status_code == 200
    for chi in (ragazza, estraneo):
        assert _client(chi).get(url).status_code == 404


def test_promemoria_e_firma(capogruppo, staff, reparto):
    from apps.verbali import stampa

    evento = _crea(staff, unita=[reparto.pk])
    Evento.objects.filter(pk=evento.pk).update(
        inizio=timezone.now() - timedelta(days=7), fine=timezone.now() - timedelta(days=7)
    )
    mail.outbox.clear()
    oggi = timezone.localdate()
    assert servizi.promemoria(oggi) == 2  # the capogruppo and the unit's staff
    destinatari = {m.to[0] for m in mail.outbox}
    assert capogruppo.utente.email in destinatari
    assert staff.utente.email in destinatari
    url = f"/api/v1/eventi/{evento.pk}/verbale/non-previsto"
    risposta = _client(staff).put(url, {"non_previsto": True}, content_type="application/json")
    assert risposta.status_code == 200
    assert servizi.promemoria(oggi + timedelta(days=7)) == 0
    evento.refresh_from_db()
    verbale = servizi.verbale_di(evento)
    assert stampa._firme(verbale, TipoVerbale.GENITORI)


def test_annullata_nessuna_convocazione(capogruppo, reparto):
    evento = _crea(capogruppo, unita=[reparto.pk])
    Evento.objects.filter(pk=evento.pk).update(annullato_il=timezone.now())
    risposta = _post(capogruppo, f"/api/v1/eventi/{evento.pk}/convocazione/invia")
    assert risposta.status_code == 400
