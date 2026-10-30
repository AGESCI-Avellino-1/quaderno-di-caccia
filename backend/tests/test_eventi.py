"""Events, recurring meetings, participants and attendance (DEC-75, DEC-78).

Events are dated in the past year 2025/26: the fixtures' memberships start on
1 October 2025.
"""

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import pytest
from django.test import Client

from apps.accounts.models import User
from apps.anagrafica.models import Appartenenza, RelazioneTutela, RuoloAppartenenza
from apps.eventi import servizi
from apps.eventi.models import (
    Evento,
    Livello,
    Partecipazione,
    Presenza,
    PresenzeAnnue,
    RiunioneRicorrente,
    StatoPartecipazione,
    StatoPresenza,
    TipoEvento,
)
from apps.organizzazione.models import Composizione, Incarico, RuoloIncarico, TipoUnita, Unita
from apps.permessi import policy
from tests.conftest import INIZIO_ANNO, crea_capo, crea_persona, nato_anni_fa

pytestmark = pytest.mark.django_db

ROMA = ZoneInfo("Europe/Rome")


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi if isinstance(chi, User) else chi.utente)
    return client


def _post(chi, url, dati=None):
    return _client(chi).post(url, dati or {}, content_type="application/json")


def _quando(giorno: date, ora: int = 16) -> datetime:
    return datetime.combine(giorno, time(ora), ROMA)


@pytest.fixture
def clan(gruppo):
    return Unita.objects.create(
        gruppo=gruppo, nome="Hirpinia", tipo=TipoUnita.CLAN_FUOCO, composizione=Composizione.MISTA
    )


@pytest.fixture
def rover(clan):
    persona = crea_persona("Piero", "Rover", "piero@example.invalid", data_nascita=nato_anni_fa(19))
    Appartenenza.objects.create(
        persona=persona, unita=clan, ruolo=RuoloAppartenenza.RAGAZZO, data_inizio=INIZIO_ANNO
    )
    return persona


@pytest.fixture
def staff(reparto, coca):
    persona = crea_capo("Elena", "Staff", "staff@example.invalid")
    Incarico.objects.create(
        persona=persona, ruolo=RuoloIncarico.STAFF, unita=reparto, data_inizio=INIZIO_ANNO
    )
    return persona


@pytest.fixture
def uscita(reparto, ragazza, csq, staff):
    evento = Evento(
        titolo="Uscita al lago",
        tipo=TipoEvento.USCITA,
        livello=Livello.UNITA,
        inizio=_quando(date(2026, 3, 14), 9),
        fine=_quando(date(2026, 3, 15), 17),
        luogo="Lago Laceno",
    )
    return servizi.crea(evento, [reparto], staff.utente)


# --- Participants ----------------------------------------------------------------------------


def test_partecipanti_di_default_i_soci_delle_unita(uscita, ragazza, csq, rover, capo):
    persone = set(uscita.partecipazioni.values_list("persona_id", flat=True))
    assert persone == {ragazza.pk, csq.pk}  # not the clan, not the capi


def test_evento_di_gruppo_tutti_i_soci(reparto, coca, ragazza, csq, rover, capo, capogruppo):
    evento = servizi.crea(
        Evento(
            titolo="San Giorgio",
            tipo=TipoEvento.ALTRO,
            livello=Livello.GRUPPO,
            inizio=_quando(date(2026, 4, 23)),
            fine=_quando(date(2026, 4, 23), 19),
        ),
        [],
        capogruppo.utente,
    )
    persone = set(evento.partecipazioni.values_list("persona_id", flat=True))
    assert {ragazza.pk, csq.pk, rover.pk, capo.pk, capogruppo.pk} <= persone


def test_evento_di_squadriglia(squadriglia, ragazza, csq, staff, reparto):
    nuova = crea_persona("Nina", "Altra", data_nascita=nato_anni_fa(12))
    Appartenenza.objects.create(
        persona=nuova, unita=reparto, ruolo=RuoloAppartenenza.RAGAZZO, data_inizio=INIZIO_ANNO
    )
    evento = Evento(
        titolo="Missione",
        tipo=TipoEvento.USCITA,
        livello=Livello.SQUADRIGLIA,
        squadriglia=squadriglia,
        inizio=_quando(date(2026, 2, 7)),
        fine=_quando(date(2026, 2, 7), 18),
    )
    servizi.crea(evento, [], csq.utente)
    assert set(evento.partecipazioni.values_list("persona_id", flat=True)) == {ragazza.pk, csq.pk}


def test_chi_entra_dopo_viene_aggiunto(uscita, reparto):
    nuova = crea_persona("Nina", "Nuova", data_nascita=nato_anni_fa(12))
    Appartenenza.objects.create(
        persona=nuova, unita=reparto, ruolo=RuoloAppartenenza.RAGAZZO, data_inizio=date(2026, 1, 10)
    )
    servizi.allinea_partecipanti(uscita)
    assert uscita.partecipazioni.filter(persona=nuova).exists()


def test_riunioni_ricorrenti(reparto, staff, ragazza):
    riunione = RiunioneRicorrente.objects.create(
        unita=reparto,
        giorno_settimana=5,  # Saturday
        ora_inizio=time(16),
        ora_fine=time(18),
        dal=date(2025, 10, 1),
        al=date(2025, 10, 31),
    )
    eventi = servizi.genera_riunioni(riunione, staff.utente)
    assert [servizi.giorno_evento(e) for e in eventi] == [
        date(2025, 10, 4),
        date(2025, 10, 11),
        date(2025, 10, 18),
        date(2025, 10, 25),
    ]
    assert servizi.genera_riunioni(riunione, staff.utente) == []  # dates kept
    assert eventi[0].partecipazioni.filter(persona=ragazza).exists()


# --- Who does what ---------------------------------------------------------------------------


def test_chi_crea_eventi(reparto, clan, squadriglia, capo, capogruppo, staff, csq, ragazza):
    assert policy.puo_creare_evento(capogruppo.utente, "GRUPPO")
    assert not policy.puo_creare_evento(capo.utente, "GRUPPO")
    assert policy.puo_creare_evento(staff.utente, "UNITA", unita_ids=[reparto.pk])
    assert not policy.puo_creare_evento(staff.utente, "UNITA", unita_ids=[reparto.pk, clan.pk])
    assert policy.puo_creare_evento(staff.utente, "BRANCA", branca="EG")
    assert not policy.puo_creare_evento(staff.utente, "BRANCA", branca="RS")
    assert policy.puo_creare_evento(csq.utente, "SQUADRIGLIA", squadriglia=squadriglia)
    assert not policy.puo_creare_evento(csq.utente, "UNITA", unita_ids=[reparto.pk])
    assert not policy.puo_creare_evento(ragazza.utente, "SQUADRIGLIA", squadriglia=squadriglia)


def test_presenze_solo_capi(uscita, staff, capo, csq, ragazza, capogruppo):
    assert policy.puo_segnare_presenze(staff.utente, uscita)
    assert policy.puo_segnare_presenze(capogruppo.utente, uscita)
    assert not policy.puo_segnare_presenze(csq.utente, uscita)
    capo_altrove = crea_capo("Ciro", "Altrove", "ciro@example.invalid")
    assert not policy.puo_segnare_presenze(capo_altrove.utente, uscita)


def test_chi_vede_l_evento(uscita, ragazza, genitore, estraneo, rover, capo):
    assert policy.eventi_visibili(genitore.utente).filter(pk=uscita.pk).exists()
    assert policy.eventi_visibili(ragazza.utente).filter(pk=uscita.pk).exists()
    assert policy.eventi_visibili(capo.utente).filter(pk=uscita.pk).exists()
    assert not policy.eventi_visibili(rover.utente).filter(pk=uscita.pk).exists()
    assert not policy.eventi_visibili(estraneo.utente).filter(pk=uscita.pk).exists()


# --- API ---------------------------------------------------------------------------------------


def test_api_crea_e_vede(reparto, staff, genitore, ragazza, csq):
    corpo = {
        "titolo": "Uscita di primavera",
        "tipo": "USCITA",
        "livello": "UNITA",
        "unita": [reparto.pk],
        "inizio": "2026-04-11T09:00:00+02:00",
        "fine": "2026-04-12T17:00:00+02:00",
        "luogo": "Montevergine",
    }
    assert _post(csq, "/api/v1/eventi", corpo).status_code == 403
    risposta = _post(staff, "/api/v1/eventi", corpo)
    assert risposta.status_code == 201, risposta.content
    evento = risposta.json()
    assert evento["unita_nomi"] == [str(reparto)]

    della_famiglia = _client(genitore).get(f"/api/v1/eventi/{evento['id']}").json()
    assert della_famiglia["partecipanti"] == []  # only their own, in "mie"
    assert [m["persona"] for m in della_famiglia["mie"]] == ["Giulia Esploratrice"]
    assert della_famiglia["mie"][0]["puo_segnalare"]
    dello_staff = _client(staff).get(f"/api/v1/eventi/{evento['id']}").json()
    assert {p["nome"] for p in dello_staff["partecipanti"]} == {"Giulia", "Sara"}


def test_api_famiglia_non_partecipa_staff_non_invita(uscita, genitore, ragazza, staff, csq):
    url = f"/api/v1/eventi/{uscita.pk}/partecipanti/{ragazza.pk}"
    assert _post(csq, f"{url}/partecipa", {"partecipa": False}).status_code == 403
    risposta = _post(genitore, f"{url}/partecipa", {"partecipa": False})
    assert risposta.json()["mie"][0]["stato"] == "NON_PARTECIPA"

    assert _post(genitore, f"{url}/non-invitare", {"motivo": "x"}).status_code == 403
    assert _post(staff, f"{url}/non-invitare", {"motivo": " "}).status_code == 400
    _post(staff, f"{url}/non-invitare", {"motivo": "Patto di corresponsabilità non rispettato"})
    vista = _client(genitore).get(f"/api/v1/eventi/{uscita.pk}").json()
    assert vista["mie"][0] == {
        "persona_id": ragazza.pk,
        "persona": "Giulia Esploratrice",
        "stato": "NON_INVITATO",
        "motivo": "Patto di corresponsabilità non rispettato",
        "puo_segnalare": True,
    }
    rifiutata = _post(genitore, f"{url}/partecipa", {"partecipa": True})
    assert rifiutata.status_code == 400  # the family cannot undo the staff's decision
    _post(staff, f"{url}/reinvita")
    assert Partecipazione.objects.get(persona=ragazza).stato == StatoPartecipazione.INVITATO


def test_api_presenze(uscita, staff, ragazza, csq, rover):
    url = f"/api/v1/eventi/{uscita.pk}/presenze"
    segni = {
        "segni": [
            {"persona_id": ragazza.pk, "stato": "PRESENTE"},
            {"persona_id": csq.pk, "stato": "GIUSTIFICATO"},
        ]
    }
    assert _client(csq).put(url, segni, content_type="application/json").status_code == 403
    risposta = _client(staff).put(url, segni, content_type="application/json")
    assert risposta.json() == {"segnate": 2}
    # The same mark again (an offline replay) changes nothing; a new mark wins.
    segni["segni"][0]["stato"] = "ASSENTE"
    _client(staff).put(url, segni, content_type="application/json")
    assert Presenza.objects.get(persona=ragazza).stato == StatoPresenza.ASSENTE
    estraneo = {"segni": [{"persona_id": rover.pk, "stato": "PRESENTE"}]}
    assert _client(staff).put(url, estraneo, content_type="application/json").status_code == 400
    foglio = _client(staff).get(f"/api/v1/eventi/{uscita.pk}/foglio-presenze.pdf")
    assert foglio.status_code == 200 and foglio.content.startswith(b"%PDF")


def test_api_riunioni_ricorrenti(reparto, staff, csq):
    corpo = {
        "giorno_settimana": 5,
        "ora_inizio": "16:00",
        "ora_fine": "18:00",
        "luogo": "Sede",
        "dal": "2025-10-01",
        "al": "2025-12-31",
    }
    url = f"/api/v1/unita/{reparto.pk}/riunioni"
    assert _post(csq, url, corpo).status_code == 403
    risposta = _post(staff, url, corpo)
    assert risposta.status_code == 201, risposta.content
    assert risposta.json()["riunioni"] == 13
    assert _post(staff, url, {**corpo, "ora_fine": "15:00"}).status_code == 400


def test_api_annulla(uscita, staff, genitore):
    url = f"/api/v1/eventi/{uscita.pk}/annulla"
    assert _post(genitore, url, {"motivo": "Pioggia"}).status_code == 403
    assert _post(staff, url, {"motivo": "Pioggia"}).json()["annullato"]


# --- Two years later: only the totals --------------------------------------------------------


def test_riassunto_delle_presenze_dopo_due_anni(uscita, staff, ragazza, csq):
    servizi.segna_presenze(
        uscita, {ragazza.pk: StatoPresenza.PRESENTE, csq.pk: StatoPresenza.ASSENTE}, staff.utente
    )
    assert servizi.riassumi_presenze(oggi=date(2027, 9, 30)) == 0  # 2025/26 still in detail
    assert servizi.riassumi_presenze(oggi=date(2028, 10, 1)) == 2
    assert not Presenza.objects.exists()
    annue = PresenzeAnnue.objects.get(persona=ragazza)
    assert (annue.anno, annue.presenti, annue.assenti) == (2026, 1, 0)


def test_genitore_di_un_maggiorenne_che_non_mostra_le_attivita(clan, rover, genitore):
    from apps.anagrafica.models import VisibilitaGenitori

    RelazioneTutela.objects.create(tutore=genitore, minore=rover, tipo="GENITORE")
    evento = servizi.crea(
        Evento(
            titolo="Route",
            tipo=TipoEvento.CAMPO,
            livello=Livello.UNITA,
            inizio=_quando(date(2026, 8, 1)),
            fine=_quando(date(2026, 8, 7)),
        ),
        [clan],
        None,
    )
    assert policy.eventi_visibili(genitore.utente).filter(pk=evento.pk).exists()
    VisibilitaGenitori.objects.create(persona=rover, scheda=False)
    assert not policy.eventi_visibili(genitore.utente).filter(pk=evento.pk).exists()


# --- Patrols, councils, Alta Squadriglia (DEC-139, DEC-140) ------------------------------


def _evento_sq(squadriglia, tipo, utente, **campi):
    return servizi.crea(
        Evento(
            titolo=campi.pop("titolo", "Riunione di squadriglia"),
            tipo=tipo,
            livello=Livello.SQUADRIGLIA,
            squadriglia=squadriglia,
            inizio=_quando(date(2026, 2, 7)),
            fine=_quando(date(2026, 2, 7), 18),
            **campi,
        ),
        [],
        utente,
    )


def test_riunione_di_squadriglia_presenze_del_csq(squadriglia, csq, ragazza, staff):
    riunione = _evento_sq(squadriglia, TipoEvento.RIUNIONE, csq.utente)
    assert policy.puo_segnare_presenze(csq.utente, riunione)
    assert policy.puo_segnare_presenze(staff.utente, riunione)
    assert not policy.puo_segnare_presenze(ragazza.utente, riunione)
    uscita = _evento_sq(squadriglia, TipoEvento.USCITA, staff.utente, titolo="Uscita")
    assert not policy.puo_segnare_presenze(csq.utente, uscita)  # capi only


def test_delegato_crea_solo_riunioni(squadriglia, csq, ragazza, staff, estraneo):
    assert not policy.puo_creare_evento(
        ragazza.utente, "SQUADRIGLIA", squadriglia=squadriglia, tipo="RIUNIONE"
    )
    servizi.delega(squadriglia, ragazza, csq.utente)
    assert policy.puo_creare_evento(
        ragazza.utente, "SQUADRIGLIA", squadriglia=squadriglia, tipo="RIUNIONE"
    )
    assert not policy.puo_creare_evento(
        ragazza.utente, "SQUADRIGLIA", squadriglia=squadriglia, tipo="USCITA"
    )
    riunione = _evento_sq(squadriglia, TipoEvento.RIUNIONE, ragazza.utente)
    assert not policy.puo_segnare_presenze(ragazza.utente, riunione)
    with pytest.raises(Exception, match="membro della squadriglia"):
        servizi.delega(squadriglia, estraneo, csq.utente)
    servizi.revoca(squadriglia)
    assert servizi.delegato(squadriglia) is None


def test_missione_solo_staff_note_ai_genitori_non_ai_ragazzi(
    squadriglia, csq, ragazza, genitore, staff
):
    assert not policy.puo_creare_evento(
        csq.utente, "SQUADRIGLIA", squadriglia=squadriglia, tipo="MISSIONE"
    )
    missione = _evento_sq(
        squadriglia,
        TipoEvento.MISSIONE,
        staff.utente,
        titolo="Missione",
        note_genitori="Partenza alle 7, si dorme da Tizio",
    )
    url = f"/api/v1/eventi/{missione.pk}"
    assert (
        _client(genitore).get(url).json()["note_genitori"] == "Partenza alle 7, si dorme da Tizio"
    )
    assert _client(staff).get(url).json()["note_genitori"]
    assert _client(ragazza).get(url).json()["note_genitori"] is None
    assert _client(csq).get(url).json()["note_genitori"] is None


def test_consiglio_capi_e_alta_squadriglia(reparto, squadriglia, csq, ragazza, staff, gruppo):
    altro = Unita.objects.create(
        gruppo=gruppo, nome="Altro", tipo=TipoUnita.REPARTO, composizione=Composizione.MASCHILE
    )
    Incarico.objects.create(
        persona=ragazza, ruolo=RuoloIncarico.VCSQ, squadriglia=squadriglia, data_inizio=INIZIO_ANNO
    )

    def consiglio(cerchia):
        return servizi.crea(
            Evento(
                titolo="Consiglio",
                tipo=TipoEvento.RIUNIONE,
                livello=Livello.UNITA,
                cerchia=cerchia,
                inizio=_quando(date(2026, 3, 1)),
                fine=_quando(date(2026, 3, 1), 18),
            ),
            [reparto, altro],
            staff.utente,
        )

    assert policy.puo_creare_evento(
        staff.utente, "UNITA", unita_ids=[reparto.pk, altro.pk], cerchia="CONCA"
    )
    assert set(consiglio("CONCA").partecipazioni.values_list("persona_id", flat=True)) == {csq.pk}
    assert set(consiglio("CONCAVI").partecipazioni.values_list("persona_id", flat=True)) == {
        csq.pk,
        ragazza.pk,
    }
    servizi.imposta_alta_squadriglia(reparto, 2026, [ragazza])
    assert set(consiglio("ALTA_SQ").partecipazioni.values_list("persona_id", flat=True)) == {
        ragazza.pk
    }


def test_consiglio_solo_tra_reparti(clan, reparto, staff, capogruppo):
    with pytest.raises(Exception, match="eventi di reparto"):
        servizi.crea(
            Evento(
                titolo="Consiglio",
                tipo=TipoEvento.RIUNIONE,
                livello=Livello.UNITA,
                cerchia="CONCA",
                inizio=_quando(date(2026, 3, 1)),
                fine=_quando(date(2026, 3, 1), 18),
            ),
            [reparto, clan],
            capogruppo.utente,
        )


def test_api_delega_e_alta_squadriglia(squadriglia, csq, ragazza, staff, reparto, rover):
    url = f"/api/v1/squadriglie/{squadriglia.pk}/delega"
    assert (
        _client(ragazza)
        .put(url, {"persona_id": ragazza.pk}, content_type="application/json")
        .status_code
        == 403
    )
    risposta = _client(csq).put(url, {"persona_id": ragazza.pk}, content_type="application/json")
    assert risposta.json()["persona"] == "Giulia Esploratrice"
    assert _client(ragazza).get(url).json()["persona_id"] == ragazza.pk

    alta = f"/api/v1/unita/{reparto.pk}/alta-squadriglia"
    corpo = {"anno": 2026, "persone": [ragazza.pk]}
    assert _client(csq).put(alta, corpo, content_type="application/json").status_code == 403
    assert _client(staff).put(alta, corpo, content_type="application/json").json()["persone"] == [
        ragazza.pk
    ]
    fuori = {"anno": 2026, "persone": [rover.pk]}
    assert _client(staff).put(alta, fuori, content_type="application/json").status_code == 400


# --- The event's fee, in instalments (DEC-77) -----------------------------------------------


def _quota_campo(evento, capo, rate, sconto="0"):
    return _client(capo).put(
        f"/api/v1/eventi/{evento.pk}/quota",
        {"nome": "Campo estivo", "rate": rate, "sconto_famiglia": sconto},
        content_type="application/json",
    )


RATE = [
    {"descrizione": "Primo acconto", "importo": "50.00", "scadenza": "2026-05-01"},
    {"descrizione": "Secondo acconto", "importo": "50.00", "scadenza": "2026-06-01"},
    {"descrizione": "Saldo", "importo": "80.00", "scadenza": "2026-07-15"},
]


def test_quota_a_rate_per_i_partecipanti(uscita, staff, ragazza, csq, genitore):
    from apps.quote.models import Quota

    _post(
        genitore,
        f"/api/v1/eventi/{uscita.pk}/partecipanti/{ragazza.pk}/partecipa",
        {"partecipa": False},
    )
    risposta = _quota_campo(uscita, staff, RATE)
    assert risposta.status_code == 200, risposta.content
    assert risposta.json()["quota"]["totale"] == "180.00"
    assert Quota.objects.valide().filter(persona=csq).count() == 3
    assert not Quota.objects.filter(persona=ragazza).exists()  # not taking part
    assert {q.descrizione for q in Quota.objects.filter(persona=csq)} == {
        "Campo estivo, Primo acconto",
        "Campo estivo, Secondo acconto",
        "Campo estivo, Saldo",
    }
    # She takes part after all: her fees arrive; she withdraws again: they go.
    _post(
        genitore,
        f"/api/v1/eventi/{uscita.pk}/partecipanti/{ragazza.pk}/partecipa",
        {"partecipa": True},
    )
    assert Quota.objects.valide().filter(persona=ragazza).count() == 3
    _post(
        genitore,
        f"/api/v1/eventi/{uscita.pk}/partecipanti/{ragazza.pk}/partecipa",
        {"partecipa": False},
    )
    assert not Quota.objects.valide().filter(persona=ragazza).exists()
    _post(
        genitore,
        f"/api/v1/eventi/{uscita.pk}/partecipanti/{ragazza.pk}/partecipa",
        {"partecipa": True},
    )
    assert Quota.objects.valide().filter(persona=ragazza).count() == 3  # the same fees, back


def test_quota_pagata_in_parte_resta_se_non_partecipa(uscita, staff, csq):
    from decimal import Decimal

    from apps.quote import servizi as quote
    from apps.quote.models import MetodoPagamento, Quota

    _quota_campo(uscita, staff, RATE)
    acconto = Quota.objects.get(persona=csq, periodo=date(2026, 5, 1))
    quote.registra_pagamento(
        data=date(2026, 4, 20),
        metodo=MetodoPagamento.CONTANTI,
        versato_da="Genitore",
        righe=[quote.Riga(acconto, Decimal("50"))],
        utente=staff.utente,
    )
    partecipazione = Partecipazione.objects.get(evento=uscita, persona=csq)
    servizi.non_partecipa(partecipazione, staff.utente)
    restano = Quota.objects.valide().filter(persona=csq)
    assert list(restano.values_list("periodo", flat=True)) == [date(2026, 5, 1)]


def test_importo_per_persona_e_rate_cambiate(uscita, staff, csq, ragazza, genitore):
    from apps.quote.models import Quota

    _quota_campo(uscita, staff, RATE)
    saldo = Quota.objects.get(persona=ragazza, periodo=date(2026, 7, 15))
    url = f"/api/v1/eventi/{uscita.pk}/quote/{saldo.pk}"
    assert (
        _client(genitore).put(url, {"importo": "0"}, content_type="application/json").status_code
        == 403
    )
    risposta = _client(staff).put(url, {"importo": "0"}, content_type="application/json")
    assert risposta.json()["residuo"] == "0.00"
    # One instalment less: its unpaid fees are withdrawn.
    _quota_campo(uscita, staff, [RATE[0], RATE[2]])
    assert Quota.objects.valide().filter(persona=csq).count() == 2
    situazione = _client(staff).get(f"/api/v1/eventi/{uscita.pk}/quote").json()
    assert {r["persona"] for r in situazione} == {"Csq Sara", "Esploratrice Giulia"}
    assert _client(genitore).get(f"/api/v1/eventi/{uscita.pk}/quote").status_code == 403


def test_quota_evento_regole(uscita, staff, csq, genitore):
    assert _quota_campo(uscita, csq, RATE).status_code == 403
    doppia = [RATE[0], {**RATE[1], "scadenza": RATE[0]["scadenza"]}]
    assert _quota_campo(uscita, staff, doppia).status_code == 400
    assert _quota_campo(uscita, staff, RATE, sconto="100").status_code == 400  # > last instalment
    vista = _client(genitore).get(f"/api/v1/eventi/{uscita.pk}").json()
    assert vista["quota"] is None


def test_sconto_famiglia_sul_saldo(uscita, staff, ragazza, genitore, reparto):
    from decimal import Decimal

    from apps.quote.models import Quota

    fratello = crea_persona("Luca", "Esploratore", data_nascita=nato_anni_fa(13))
    Appartenenza.objects.create(
        persona=fratello, unita=reparto, ruolo=RuoloAppartenenza.RAGAZZO, data_inizio=INIZIO_ANNO
    )
    RelazioneTutela.objects.create(tutore=genitore, minore=fratello, tipo="GENITORE")
    servizi.allinea_partecipanti(uscita)
    _quota_campo(uscita, staff, RATE, sconto="10")
    sconti = dict(Quota.objects.filter(persona=ragazza).values_list("periodo", "sconto"))
    assert sconti == {
        date(2026, 5, 1): Decimal("0"),
        date(2026, 6, 1): Decimal("0"),
        date(2026, 7, 15): Decimal("10"),
    }
