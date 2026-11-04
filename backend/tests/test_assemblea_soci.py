"""The assembly of the members (DEC-326, with DEC-322…DEC-331)."""

from datetime import timedelta

import pytest
from auditlog.models import LogEntry
from django.core import mail
from django.test import Client
from django.utils import timezone

from apps.anagrafica.models import Appartenenza, RelazioneTutela, RuoloAppartenenza, TipoTutela
from apps.eventi.models import Evento, Presenza
from apps.eventi.servizi import qualita_in_assemblea
from apps.impostazioni.models import Impostazioni
from apps.organizzazione.models import AnnoChiuso, TipoUnita, Unita
from apps.permessi import policy
from apps.verbali import servizi, stampa
from apps.verbali.models import TipoVerbale, Verbale
from tests.conftest import INIZIO_ANNO, crea_capo, crea_persona, nato_anni_fa

pytestmark = pytest.mark.django_db


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


def _post(chi, url, dati=None):
    return _client(chi).post(url, dati or {}, content_type="application/json")


def _put(chi, url, dati):
    return _client(chi).put(url, dati, content_type="application/json")


def _corpo(giorni=10) -> dict:
    giorno = timezone.localdate() + timedelta(days=giorni)
    return {
        "cerchia": "SOCI",
        "giorno": giorno.isoformat(),
        "ora_inizio": "18:00",
        "ora_fine": "20:00",
    }


@pytest.fixture(autouse=True)
def email_accese():
    imp = Impostazioni.carica()
    imp.email_capi = imp.email_genitori = imp.email_ragazzi = True
    imp.save()


@pytest.fixture
def clan(gruppo) -> Unita:
    return Unita.objects.create(gruppo=gruppo, nome="Clan", tipo=TipoUnita.CLAN_FUOCO)


@pytest.fixture
def adulto(clan):
    persona = crea_persona("Rino", "Rover", "rino-a@example.invalid", data_nascita=nato_anni_fa(19))
    Appartenenza.objects.create(
        persona=persona, unita=clan, ruolo=RuoloAppartenenza.RAGAZZO, data_inizio=INIZIO_ANNO
    )
    return persona


@pytest.fixture
def genitore_adulto(adulto):
    """A parent of an adult only: comes to be informed, no vote."""
    persona = crea_persona("Pia", "Rover", "pia-a@example.invalid", data_nascita=nato_anni_fa(50))
    RelazioneTutela.objects.create(tutore=persona, minore=adulto, tipo=TipoTutela.GENITORE)
    return persona


@pytest.fixture
def assemblea(capogruppo) -> Evento:
    risposta = _post(capogruppo, "/api/v1/riunioni", _corpo())
    assert risposta.status_code == 201, risposta.content
    return Evento.objects.get(pk=risposta.json()[0]["id"])


def _invitati(evento) -> set[int]:
    return set(evento.partecipazioni.values_list("persona_id", flat=True))


def _segna(evento, *persone) -> None:
    for persona in persone:
        Presenza.objects.create(evento=evento, persona=persona, stato="PRESENTE")


def _url(evento, altro="") -> str:
    return f"/api/v1/eventi/{evento.pk}/verbale{altro}"


def _pronto(evento, chi, presidente, *segretari) -> None:
    assert _put(chi, _url(evento), {"testo": "<p>Approvato il bilancio.</p>"}).status_code == 200
    corpo = {"presidente_id": presidente.pk, "segretari_ids": [s.pk for s in segretari]}
    risposta = _put(chi, _url(evento, "/cariche"), corpo)
    assert risposta.status_code == 200, risposta.content


# --- Creating and who is invited ----------------------------------------------------------


def test_chi_la_convoca(capo, capogruppo, csq, genitore, estraneo):
    for chi in (capo, csq, genitore, estraneo):
        assert _post(chi, "/api/v1/riunioni", _corpo()).status_code == 403
    risposta = _post(capogruppo, "/api/v1/riunioni", _corpo())
    assert risposta.status_code == 201
    evento = Evento.objects.get(pk=risposta.json()[0]["id"])
    assert evento.titolo == "Assemblea dei soci"
    assert evento.livello == "GRUPPO"
    assert servizi.tipo_di(evento) == TipoVerbale.ASSEMBLEA


def test_invitati(capogruppo, capo, adulto, genitore_adulto, genitore, ragazza, csq, assemblea):
    invitati = _invitati(assemblea)
    assert {capogruppo.pk, capo.pk, adulto.pk, genitore_adulto.pk, genitore.pk} <= invitati
    # The minors are represented, not invited.
    assert not {ragazza.pk, csq.pk} & invitati


def test_il_maggiorenne_al_posto_non_vale_per_l_assemblea(adulto, genitore_adulto, capogruppo):
    from apps.anagrafica.models import VisibilitaGenitori

    VisibilitaGenitori.objects.create(persona=adulto, al_posto_dei_genitori=True)
    risposta = _post(capogruppo, "/api/v1/riunioni", _corpo())
    invitati = _invitati(Evento.objects.get(pk=risposta.json()[0]["id"]))
    assert {adulto.pk, genitore_adulto.pk} <= invitati


def test_diritto_di_voto(capo, adulto, genitore_adulto, genitore, ragazza, reparto):
    oggi = timezone.localdate()
    assert qualita_in_assemblea(capo, oggi) == {"qualita": "Socio", "voto": True}
    assert qualita_in_assemblea(adulto, oggi) == {"qualita": "Socio", "voto": True}
    assert qualita_in_assemblea(genitore, oggi) == {"qualita": "Genitore", "voto": True}
    assert qualita_in_assemblea(genitore_adulto, oggi)["voto"] is False
    # A capo with a minor child in the group: votes for themself and for the child.
    RelazioneTutela.objects.create(tutore=capo, minore=ragazza, tipo=TipoTutela.GENITORE)
    assert qualita_in_assemblea(capo, oggi) == {"qualita": "Socio e genitore", "voto": True}


# --- Attendance ---------------------------------------------------------------------------


def test_chi_segna_le_presenze(capogruppo, capo, genitore, estraneo, assemblea):
    assert policy.puo_segnare_presenze(capogruppo.utente, assemblea)
    # Not any capo, as at the other group events.
    assert not policy.puo_segnare_presenze(capo.utente, assemblea)
    assert not policy.puo_segnare_presenze(genitore.utente, assemblea)
    url = f"/api/v1/eventi/{assemblea.pk}/convocazione/presenze"
    assert _put(capo, url, {"persona_id": genitore.pk}).status_code == 403
    assert _put(capogruppo, url, {"persona_id": estraneo.pk}).status_code == 400
    assert _put(capogruppo, url, {"persona_id": genitore.pk}).status_code == 200
    assemblea.refresh_from_db()
    assert policy.puo_segnare_presenze(genitore.utente, assemblea)
    assert policy.puo_vedere_partecipanti(genitore.utente, assemblea)
    dettaglio = _client(genitore).get(f"/api/v1/eventi/{assemblea.pk}").json()
    assert dettaglio["puo_presenze"] is True
    assert dettaglio["partecipanti"]


def test_niente_assenza_da_comunicare(adulto, assemblea):
    assert not policy.puo_segnalare_assenza(adulto.utente, adulto, assemblea)


# --- Minutes ------------------------------------------------------------------------------


def test_chi_scrive_e_chi_legge(
    capogruppo, capo, adulto, genitore_adulto, ragazza, estraneo, assemblea
):
    assert _put(capo, _url(assemblea), {"testo": "<p>x</p>"}).status_code == 403
    _segna(assemblea, capogruppo, adulto)
    _pronto(assemblea, capogruppo, adulto, capogruppo)
    assert _client(genitore_adulto).get(_url(assemblea)).status_code == 404  # still a draft
    assert _post(capogruppo, _url(assemblea, "/definitivo")).status_code == 200
    # Everyone invited reads it, the parents of an adult too.
    for chi in (capo, capogruppo, adulto, genitore_adulto):
        assert _client(chi).get(_url(assemblea)).status_code == 200
    for chi in (ragazza, estraneo):
        assert _client(chi).get(_url(assemblea)).status_code == 404


def test_cariche_solo_tra_i_presenti(capogruppo, capo, adulto, assemblea):
    _segna(assemblea, capo)
    url = _url(assemblea, "/cariche")
    corpo = {"presidente_id": adulto.pk, "segretari_ids": [capo.pk]}
    risposta = _put(capogruppo, url, corpo)
    assert risposta.status_code == 400
    assert "presenti" in risposta.json()["detail"]
    Presenza.objects.create(evento=assemblea, persona=adulto, stato="ASSENTE")
    assert _put(capogruppo, url, corpo).status_code == 400
    Presenza.objects.filter(persona=adulto).update(stato="PRESENTE")
    assert _put(capogruppo, url, corpo).status_code == 200


def test_solo_l_assemblea_ha_le_cariche(capogruppo, coca):

    inizio = timezone.now() - timedelta(days=1)
    evento = Evento.objects.create(
        titolo="Co.Ca.", tipo="RIUNIONE", livello="UNITA", inizio=inizio, fine=inizio
    )
    evento.unita.set([coca])
    risposta = _put(capogruppo, _url(evento, "/cariche"), {"presidente_id": None})
    assert risposta.status_code == 400


def test_definitivo_richiede_le_cariche(capogruppo, capo, assemblea):
    assert _put(capogruppo, _url(assemblea), {"testo": "<p>x</p>"}).status_code == 200
    risposta = _post(capogruppo, _url(assemblea, "/definitivo"))
    assert risposta.status_code == 400
    assert "presidente" in risposta.json()["detail"]
    # A secretary at least, and still present at the end.
    _segna(assemblea, capo, capogruppo)
    _pronto(assemblea, capogruppo, capo, capogruppo)
    Presenza.objects.filter(persona=capogruppo).update(stato="ASSENTE")
    assert _post(capogruppo, _url(assemblea, "/definitivo")).status_code == 400
    Presenza.objects.filter(persona=capogruppo).update(stato="PRESENTE")
    assert _post(capogruppo, _url(assemblea, "/definitivo")).status_code == 200


def test_non_previsto_non_esiste(capogruppo, assemblea):
    risposta = _put(capogruppo, _url(assemblea, "/non-previsto"), {"non_previsto": True})
    assert risposta.status_code == 400
    assert _client(capogruppo).get(_url(assemblea)).json()["puo_dire_non_previsto"] is False


def test_elenco_copiato_nel_definitivo(
    capogruppo, adulto, genitore_adulto, genitore, ragazza, assemblea
):
    _segna(assemblea, adulto, genitore_adulto, genitore)
    _pronto(assemblea, capogruppo, adulto, genitore)
    assert _post(capogruppo, _url(assemblea, "/definitivo")).status_code == 200
    verbale = Verbale.objects.get(evento=assemblea)
    voti = {p["nome"]: p["voto"] for p in verbale.presenti}
    assert voti == {
        f"{adulto.nome} {adulto.cognome}": True,
        f"{genitore_adulto.nome} {genitore_adulto.cognome}": False,
        f"{genitore.nome} {genitore.cognome}": True,
    }
    assert verbale.cariche["presidente"]["nome"] == f"{adulto.nome} {adulto.cognome}"
    # No child is named in what everyone invited reads.
    letto = _client(genitore_adulto).get(_url(assemblea, "?testo=true")).json()
    assert ragazza.nome not in str(letto["presenti"])
    assert [p["voto"] for p in letto["presenti"]].count(False) == 1
    assert letto["presidente"] == f"{adulto.nome} {adulto.cognome}"
    # The copy stays when attendance goes (two years later, DEC-78).
    Presenza.objects.filter(evento=assemblea).delete()
    assert _post(capogruppo, _url(assemblea, "/riapri"), {"motivo": "Refuso"}).status_code == 200
    verbale.refresh_from_db()
    assert len(verbale.presenti) == 3


def test_elenco_anche_per_la_coca(capogruppo, capo, coca):
    inizio = timezone.now() - timedelta(days=1)
    evento = Evento.objects.create(
        titolo="Co.Ca.", tipo="RIUNIONE", livello="UNITA", inizio=inizio, fine=inizio
    )
    evento.unita.set([coca])
    _segna(evento, capo)
    assert _put(capogruppo, _url(evento), {"testo": "<p>x</p>"}).status_code == 200
    assert _post(capogruppo, _url(evento, "/definitivo")).status_code == 200
    assert [p["persona_id"] for p in Verbale.objects.get(evento=evento).presenti] == [capo.pk]


def test_elenco_fuori_dal_registro_delle_modifiche(capogruppo, capo, assemblea):
    _segna(assemblea, capo, capogruppo)
    _pronto(assemblea, capogruppo, capo, capogruppo)
    assert _post(capogruppo, _url(assemblea, "/definitivo")).status_code == 200
    verbale = Verbale.objects.get(evento=assemblea)
    voci = {k for e in LogEntry.objects.get_for_object(verbale) for k in (e.changes or {})}
    assert "presenti" not in voci and "cariche" not in voci and "testo" not in voci


def test_pdf_con_presenti_e_firme(capogruppo, capo, gruppo, assemblea):
    _segna(assemblea, capo, capogruppo)
    _pronto(assemblea, capogruppo, capo, capogruppo)
    assert _post(capogruppo, _url(assemblea, "/definitivo")).status_code == 200
    risposta = _client(capo).get(_url(assemblea, ".pdf"))
    assert risposta.status_code == 200 and risposta.content.startswith(b"%PDF")
    verbale = Verbale.objects.get(evento=assemblea)
    # A line for the president and one for each secretary, each with its own space.
    assert len(stampa._firme(verbale, TipoVerbale.ASSEMBLEA)) == 5
    assert len(stampa._presenti(verbale, TipoVerbale.ASSEMBLEA)) == 2


def test_anno_chiuso_blocca_le_cariche(capogruppo, capo, assemblea):
    _segna(assemblea, capo)
    anno = servizi.AnnoAssociativo.da_data(timezone.localdate(assemblea.inizio)).anno_fine
    AnnoChiuso.objects.create(anno=anno, chiuso_il=timezone.now())
    corpo = {"presidente_id": capo.pk, "segretari_ids": []}
    assert _put(capogruppo, _url(assemblea, "/cariche"), corpo).status_code == 400


# --- Convocation --------------------------------------------------------------------------


def test_convocazione_a_tutti_gli_invitati(
    capogruppo, adulto, genitore_adulto, genitore, assemblea
):
    mail.outbox.clear()
    url = f"/api/v1/eventi/{assemblea.pk}/convocazione/invia"
    assert _post(genitore, url).status_code == 403
    assert _post(capogruppo, url).status_code == 200
    destinatari = {m.to[0] for m in mail.outbox}
    assert adulto.utente.email in destinatari or adulto.email in destinatari
    assert genitore_adulto.utente.email in destinatari
    assert all(m.subject == "Convocazione: Assemblea dei soci" for m in mail.outbox)


# --- Reminders and the missing minutes ------------------------------------------------------


def _passata(evento, giorni=7) -> None:
    momento = timezone.now() - timedelta(days=giorni)
    Evento.objects.filter(pk=evento.pk).update(inizio=momento, fine=momento)


def test_promemoria_senza_limite_finche_non_e_definitivo(capogruppo, capo, assemblea):
    _passata(assemblea)
    oggi = timezone.localdate()
    for settimana in range(5):
        mail.outbox.clear()
        assert servizi.promemoria(oggi + timedelta(days=7 * settimana)) == 1
    assert mail.outbox[0].to == [capogruppo.utente.email]
    # No way out of it: the sentence is not there.
    assert "non c'è" not in mail.outbox[0].body
    _segna(assemblea, capo, capogruppo)
    _pronto(assemblea, capogruppo, capo, capogruppo)
    assert _post(capogruppo, _url(assemblea, "/definitivo")).status_code == 200
    assert servizi.promemoria(oggi + timedelta(days=70)) == 0


def test_verbale_mancante_per_i_capigruppo(capogruppo, capo, genitore, assemblea):
    url = "/api/v1/verbali-mancanti"
    assert _client(capogruppo).get(url).json() == []  # not held yet
    _passata(assemblea)
    elenco = _client(capogruppo).get(url).json()
    assert [e["id"] for e in elenco] == [assemblea.pk]
    assert _client(capo).get(url).json() == []
    assert _client(genitore).get(url).json() == []
    _segna(assemblea, capo, capogruppo)
    _pronto(assemblea, capogruppo, capo, capogruppo)
    assert _post(capogruppo, _url(assemblea, "/definitivo")).status_code == 200
    assert _client(capogruppo).get(url).json() == []


def test_annullata_nessun_obbligo(capogruppo, assemblea):
    _passata(assemblea)
    Evento.objects.filter(pk=assemblea.pk).update(annullato_il=timezone.now())
    assert servizi.promemoria(timezone.localdate()) == 0
    assert _client(capogruppo).get("/api/v1/verbali-mancanti").json() == []


# --- Five years -----------------------------------------------------------------------------


def test_cancellazione_nei_cinque_anni(capogruppo, capo, assemblea):
    socio = crea_capo("Anna", "Socia", "socia@example.invalid")
    _segna(assemblea, socio, capo, capogruppo)
    _pronto(assemblea, capogruppo, socio, capo)
    assert _post(capogruppo, _url(assemblea, "/definitivo")).status_code == 200
    servizi.alla_cancellazione(socio)
    verbale = Verbale.objects.get(evento=assemblea)
    assert verbale.presidente is None
    # Within the five years the document keeps the name.
    assert verbale.cariche["presidente"]["nome"] == "Anna Socia"
    assert "Anna Socia" in [p["nome"] for p in verbale.presenti]
    assert servizi.togli_nomi_scaduti(timezone.localdate()) == 0
    # After them it goes, the list stays.
    giorno = timezone.localdate(assemblea.inizio) + timedelta(days=5 * 366)
    assert servizi.togli_nomi_scaduti(giorno) == 1
    verbale.refresh_from_db()
    assert verbale.cariche["presidente"]["nome"] == servizi.NOME_TOLTO
    nomi = [p["nome"] for p in verbale.presenti]
    assert "Anna Socia" not in nomi and servizi.NOME_TOLTO in nomi and len(nomi) == 3
    assert verbale.nomi_da_togliere == []


def test_cancellazione_oltre_i_cinque_anni(capogruppo, capo, coca):
    momento = timezone.now() - timedelta(days=2000)
    socio = crea_capo("Elsa", "Vecchia", "vecchia@example.invalid")
    evento = Evento.objects.create(
        titolo="Assemblea",
        tipo="RIUNIONE",
        livello="GRUPPO",
        cerchia="SOCI",
        inizio=momento,
        fine=momento,
    )
    Verbale.objects.create(
        evento=evento,
        stato="DEFINITIVO",
        presenti=[
            {"persona_id": socio.pk, "nome": "Elsa Vecchia", "qualita": "Socio", "voto": True}
        ],
    )
    servizi.alla_cancellazione(socio)
    assert Verbale.objects.get(evento=evento).presenti[0]["nome"] == servizi.NOME_TOLTO
