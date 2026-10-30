"""Events on BuonaCaccia (DEC-158…DEC-164). Dates are relative to today: registrations
cannot be in the future and the deadlines count from them."""

import io
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import Client

from apps.anagrafica.models import Appartenenza, RuoloAppartenenza
from apps.buonacaccia import servizi
from apps.buonacaccia.avvisi import promemoria
from apps.buonacaccia.models import (
    EventoBuonaCaccia,
    IscrizioneBuonaCaccia,
    StatoIscrizione,
    TipoCampoFormazione,
)
from apps.eventi.models import Evento, Livello, Partecipazione, StatoPartecipazione, TipoEvento
from apps.organizzazione.models import Composizione, TipoUnita, Unita
from apps.permessi import policy
from apps.permessi.models import AccessoDatoSensibile, Categoria
from apps.quote.models import CategoriaQuota, Quota
from tests.conftest import INIZIO_ANNO, crea_capo, crea_persona, nato_anni_fa

pytestmark = pytest.mark.django_db

ROMA = ZoneInfo("Europe/Rome")
OGGI = date.today()
PDF = b"%PDF-1.4\n% prova\n"


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


def _json(chi, metodo, url, dati=None):
    client = _client(chi)
    return getattr(client, metodo)(url, dati or {}, content_type="application/json")


def _quando(giorno: date, ora: int = 9) -> datetime:
    return datetime.combine(giorno, time(ora), ROMA)


@pytest.fixture
def altro_capo(coca):
    """A capo of the Co.Ca. who does not serve the reparto."""
    return crea_capo("Carlo", "Altro", "altro@example.invalid")


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
def piccole_orme(capo):
    evento = Evento(
        titolo="Piccole Orme di cucina",
        tipo=TipoEvento.CAMPO,
        inizio=_quando(OGGI + timedelta(days=30)),
        fine=_quando(OGGI + timedelta(days=32), 17),
        luogo="Bracigliano",
    )
    return servizi.salva_evento(evento, EventoBuonaCaccia(), capo.utente)


def _iscrivi(capo, evento, persona, giorni_fa=1, **altri):
    return servizi.iscrivi(
        evento,
        persona,
        capo.utente,
        iscritto_il=OGGI - timedelta(days=giorni_fa),
        stato=StatoIscrizione.AMMESSO,
        **altri,
    )


# --- Policy -------------------------------------------------------------------------------


def test_chi_gestisce_e_chi_vede_l_iscrizione(
    capo, capogruppo, altro_capo, ragazza, genitore, csq, estraneo
):
    gestisce = policy.puo_gestire_iscrizione_buonacaccia
    vede = policy.puo_vedere_iscrizione_buonacaccia
    risponde = policy.puo_rispondere_scheda
    assert gestisce(capo.utente, ragazza) and gestisce(capogruppo.utente, ragazza)
    for nessuno in (altro_capo, genitore, ragazza, csq, estraneo):
        assert not gestisce(nessuno.utente, ragazza)
    for chi in (capo, capogruppo, altro_capo, genitore, ragazza):
        assert vede(chi.utente, ragazza)
    assert not vede(csq.utente, ragazza) and not vede(estraneo.utente, ragazza)
    assert risponde(genitore.utente, ragazza) and risponde(ragazza.utente, ragazza)
    for nessuno in (capo, altro_capo, csq, estraneo):
        assert not risponde(nessuno.utente, ragazza)
    assert policy.vede_presentazione_buonacaccia(altro_capo.utente)
    assert not policy.vede_presentazione_buonacaccia(genitore.utente)


def test_chi_crea_eventi_e_segna_la_partecipazione(capo, rover, ragazza, genitore, estraneo):
    assert policy.puo_creare_evento_buonacaccia(capo.utente)
    assert policy.puo_creare_evento_buonacaccia(rover.utente)  # an adult member
    for nessuno in (ragazza, genitore, estraneo):
        assert not policy.puo_creare_evento_buonacaccia(nessuno.utente)
    assert policy.puo_segnare_partecipazione_esterna(rover.utente, rover)
    assert not policy.puo_segnare_partecipazione_esterna(ragazza.utente, ragazza)
    # A parent is an adult but not a member: nothing to record for themself.
    assert not policy.puo_segnare_partecipazione_esterna(genitore.utente, genitore)
    assert not policy.puo_creare_evento(capo.utente, Livello.ESTERNO)


def test_solo_i_capigruppo_vedono_la_formazione(capogruppo, capo, rover):
    assert policy.puo_vedere_formazione_capi(capogruppo.utente)
    assert not policy.puo_vedere_formazione_capi(capo.utente)
    assert not policy.puo_vedere_formazione_capi(rover.utente)


# --- Events ----------------------------------------------------------------------------------


def test_un_evento_solo_per_piu_soci(capo, rover, piccole_orme):
    """Before creating one, the event is searched (DEC-158)."""
    trovati = _client(rover).get("/api/v1/buonacaccia/eventi?cerca=cucina").json()
    assert [e["id"] for e in trovati] == [piccole_orme.pk]
    assert _client(rover).get("/api/v1/buonacaccia/eventi?cerca=nautica").json() == []


def test_crea_evento_e_tipo_di_campo(capo):
    url = "/api/v1/buonacaccia/eventi"
    dati = {
        "titolo": "Modulo di formazione",
        "inizio": _quando(OGGI + timedelta(days=10)).isoformat(),
        "fine": _quando(OGGI + timedelta(days=11)).isoformat(),
        "formazione_capi": True,
        "tipo_campo": "MODULO",
    }
    risposta = _json(capo, "post", url, dati)
    assert risposta.status_code == 400
    assert "titolo del modulo" in risposta.json()["detail"]
    risposta = _json(capo, "post", url, {**dati, "specifica": "Comunicazione"})
    assert risposta.status_code == 201
    evento = Evento.objects.get(pk=risposta.json()["id"])
    assert evento.livello == Livello.ESTERNO and evento.creato_da == capo.utente
    assert evento.buonacaccia.tipo_campo_testo == "Modulo formativo: Comunicazione"


def test_gli_eventi_esterni_non_passano_dagli_eventi_del_gruppo(capogruppo):
    risposta = _json(
        capogruppo,
        "post",
        "/api/v1/eventi",
        {
            "titolo": "Finto",
            "tipo": "CAMPO",
            "livello": "ESTERNO",
            "inizio": _quando(OGGI).isoformat(),
            "fine": _quando(OGGI).isoformat(),
        },
    )
    assert risposta.status_code == 403


# --- Registrations ----------------------------------------------------------------------


def test_iscrizione_con_scadenze_quota_e_avviso(
    capo, ragazza, genitore, piccole_orme, django_capture_on_commit_callbacks
):
    mail.outbox.clear()
    with django_capture_on_commit_callbacks(execute=True):
        risposta = _json(
            capo,
            "post",
            f"/api/v1/buonacaccia/eventi/{piccole_orme.pk}/iscrizioni",
            {
                "persona_id": ragazza.pk,
                "iscritto_il": (OGGI - timedelta(days=1)).isoformat(),
                "link_gestione": "https://buonacaccia.net/gestione/abc",
                "importo": "45.00",
                "scadenza_quota": (OGGI + timedelta(days=20)).isoformat(),
            },
        )
    assert risposta.status_code == 201, risposta.content
    dati = risposta.json()
    assert dati["scadenza"] == (OGGI + timedelta(days=8)).isoformat()
    assert dati["scadenza_liberatoria"] == (OGGI + timedelta(days=6)).isoformat()
    assert dati["limite_cancellazione"] == (OGGI + timedelta(days=23)).isoformat()
    assert dati["link_gestione"] == "https://buonacaccia.net/gestione/abc"
    quota = Quota.objects.get(persona=ragazza)
    assert quota.tipo.categoria == CategoriaQuota.BUONACACCIA
    assert (quota.importo, quota.sconto) == (Decimal("45.00"), Decimal("0"))
    assert Partecipazione.objects.get(evento=piccole_orme, persona=ragazza).stato == (
        StatoPartecipazione.INVITATO
    )
    destinatari = {m.to[0] for m in mail.outbox}
    assert {"genitore@example.invalid", "giulia@example.invalid"} <= destinatari


def test_il_link_lo_vede_solo_chi_gestisce(capo, altro_capo, genitore, ragazza, piccole_orme):
    _iscrivi(capo, piccole_orme, ragazza, link_gestione="https://buonacaccia.net/x")
    url = f"/api/v1/buonacaccia/eventi/{piccole_orme.pk}"
    for chi in (altro_capo, genitore, ragazza):
        (iscrizione,) = _client(chi).get(url).json()["iscrizioni"]
        assert iscrizione["link_gestione"] is None
    assert _client(capo).get(url).json()["iscrizioni"][0]["link_gestione"]


def test_solo_lo_staff_iscrive_e_i_maggiorenni_fanno_da_soli(
    capo, altro_capo, ragazza, rover, piccole_orme
):
    url = f"/api/v1/buonacaccia/eventi/{piccole_orme.pk}/iscrizioni"
    dati = {"persona_id": ragazza.pk, "iscritto_il": OGGI.isoformat()}
    assert _json(altro_capo, "post", url, dati).status_code == 403
    risposta = _json(capo, "post", url, {**dati, "persona_id": rover.pk})
    assert risposta.status_code in (400, 403)
    # The adult records only their participation.
    risposta = _json(
        rover,
        "put",
        f"/api/v1/buonacaccia/eventi/{piccole_orme.pk}/partecipanti",
        {"persona_id": rover.pk},
    )
    assert risposta.status_code == 200
    assert Partecipazione.objects.filter(evento=piccole_orme, persona=rover).exists()
    assert not IscrizioneBuonaCaccia.objects.exists()


def test_la_famiglia_non_cambia_la_partecipazione_di_un_minorenne(
    capo, genitore, ragazza, piccole_orme
):
    _iscrivi(capo, piccole_orme, ragazza)
    eventi = _client(genitore).get("/api/v1/eventi").json()
    (mia,) = next(e for e in eventi if e["id"] == piccole_orme.pk)["mie"]
    assert mia["puo_segnalare"] is False


def test_cancellata_entro_il_limite_la_quota_si_toglie(capo, ragazza, piccole_orme):
    iscrizione = _iscrivi(capo, piccole_orme, ragazza)
    servizi.imposta_quota(iscrizione, Decimal("30"), OGGI, capo.utente)
    url = f"/api/v1/buonacaccia/iscrizioni/{iscrizione.pk}"
    risposta = _json(capo, "post", f"{url}/chiudi", {"stato": "CANCELLATA", "il": OGGI.isoformat()})
    assert risposta.json()["puo_togliere_quota"] is True
    assert Partecipazione.objects.get(persona=ragazza).stato == StatoPartecipazione.NON_PARTECIPA
    risposta = _json(capo, "post", f"{url}/togli-quota")
    assert risposta.json()["quota"]["annullata"] is True


def test_cancellata_dopo_il_limite_la_quota_resta(capo, ragazza, piccole_orme):
    iscrizione = _iscrivi(capo, piccole_orme, ragazza)
    servizi.imposta_quota(iscrizione, Decimal("30"), OGGI, capo.utente)
    servizi.chiudi(iscrizione, StatoIscrizione.CANCELLATA, OGGI + timedelta(days=25), capo.utente)
    risposta = _json(capo, "post", f"/api/v1/buonacaccia/iscrizioni/{iscrizione.pk}/togli-quota")
    assert risposta.status_code == 400
    assert Quota.objects.valide().filter(persona=ragazza).exists()


def test_non_ammesso_la_quota_si_toglie(capo, ragazza, piccole_orme):
    iscrizione = _iscrivi(capo, piccole_orme, ragazza)
    servizi.imposta_quota(iscrizione, Decimal("30"), OGGI, capo.utente)
    servizi.chiudi(iscrizione, StatoIscrizione.NON_AMMESSO, OGGI, capo.utente)
    servizi.togli_quota(iscrizione, capo.utente)
    assert not Quota.objects.valide().filter(persona=ragazza).exists()


def test_le_quote_buonacaccia_non_vanno_a_tutti_ne_nei_promemoria(capo, ragazza, csq, piccole_orme):
    from apps.quote.servizi import emetti_tutte

    iscrizione = _iscrivi(capo, piccole_orme, ragazza)
    servizi.imposta_quota(iscrizione, Decimal("30"), OGGI + timedelta(days=3), capo.utente)
    emetti_tutte()
    assert list(Quota.objects.values_list("persona_id", flat=True)) == [ragazza.pk]
    mail.outbox.clear()
    call_command("promemoria_quote", stdout=io.StringIO())
    assert mail.outbox == []


# --- Release form (DEC-160) --------------------------------------------------------------


def test_liberatoria_passa_dall_app(
    capo, genitore, ragazza, piccole_orme, django_capture_on_commit_callbacks
):
    iscrizione = _iscrivi(capo, piccole_orme, ragazza)
    url = f"/api/v1/buonacaccia/iscrizioni/{iscrizione.pk}"
    mail.outbox.clear()
    with django_capture_on_commit_callbacks(execute=True):
        risposta = _client(capo).post(
            f"{url}/liberatoria", {"file": SimpleUploadedFile("Rossi Giulia.pdf", PDF)}
        )
    assert risposta.status_code == 200 and risposta.json()["liberatoria_da_firmare"]
    assert any("liberatoria" in m.body for m in mail.outbox)
    iscrizione.refresh_from_db()
    assert "Giulia" not in iscrizione.liberatoria_da_firmare.name  # random name
    # The family downloads it (no access log), completes, signs and sends it back.
    assert _client(genitore).get(f"{url}/liberatoria").status_code == 200
    assert not AccessoDatoSensibile.objects.exists()
    risposta = _client(genitore).post(
        f"{url}/liberatoria-firmata", {"file": SimpleUploadedFile("firmata.pdf", PDF)}
    )
    assert risposta.json()["liberatoria_ricevuta_il"] == OGGI.isoformat()
    # The staff reads it: logged.
    assert _client(capo).get(f"{url}/liberatoria-firmata").status_code == 200
    assert AccessoDatoSensibile.objects.filter(persona=ragazza, categoria=Categoria.MODULI).exists()
    # Loaded on BuonaCaccia, then rejected with a reason: asked again of the family.
    _json(capo, "put", f"{url}/passi", {"liberatoria_caricata_il": OGGI.isoformat()})
    # Once on BuonaCaccia a new one would undo the work: refused until a rejection.
    risposta = _client(genitore).post(
        f"{url}/liberatoria-firmata", {"file": SimpleUploadedFile("altra.pdf", PDF)}
    )
    assert risposta.status_code == 400
    risposta = _json(capo, "post", f"{url}/esito-liberatoria", {"esito": "RIGETTATA"})
    assert risposta.status_code == 400
    mail.outbox.clear()
    with django_capture_on_commit_callbacks(execute=True):
        risposta = _json(
            capo,
            "post",
            f"{url}/esito-liberatoria",
            {"esito": "RIGETTATA", "motivo": "Manca la firma"},
        )
    assert risposta.json()["liberatoria_ricevuta_il"] is None
    assert any("Manca la firma" in m.body for m in mail.outbox)
    risposta = _client(ragazza).post(
        f"{url}/liberatoria-firmata", {"file": SimpleUploadedFile("di nuovo.pdf", PDF)}
    )
    dati = risposta.json()
    assert dati["esito_liberatoria"] == "" and dati["liberatoria_caricata_il"] is None


def test_liberatoria_per_altri_canali_e_file_non_ammessi(capo, genitore, ragazza, piccole_orme):
    iscrizione = _iscrivi(capo, piccole_orme, ragazza, modo_liberatoria="ALTRI_CANALI")
    url = f"/api/v1/buonacaccia/iscrizioni/{iscrizione.pk}"
    risposta = _client(genitore).post(
        f"{url}/liberatoria-firmata", {"file": SimpleUploadedFile("x.pdf", PDF)}
    )
    assert risposta.status_code == 400
    risposta = _json(capo, "put", f"{url}/passi", {"liberatoria_ricevuta_il": OGGI.isoformat()})
    assert risposta.json()["liberatoria_ricevuta_il"] == OGGI.isoformat()
    _json(capo, "put", url, {"modo_liberatoria": "APP"})
    risposta = _client(capo).post(
        f"{url}/liberatoria", {"file": SimpleUploadedFile("x.exe", b"MZ\x90\x00")}
    )
    assert risposta.status_code == 400


def test_estranei_e_altri_ragazzi_non_vedono_l_iscrizione(
    capo, csq, estraneo, ragazza, piccole_orme
):
    iscrizione = _iscrivi(capo, piccole_orme, ragazza)
    for chi in (csq, estraneo):
        assert (
            _client(chi).get(f"/api/v1/buonacaccia/iscrizioni/{iscrizione.pk}/foto").status_code
            == 404
        )
        assert _client(chi).get(f"/api/v1/buonacaccia/eventi/{piccole_orme.pk}").status_code == 404


# --- Event forms and photo (DEC-161, DEC-162) ---------------------------------------------

DOMANDE = [
    {
        "tipo": "SCELTA_SINGOLA",
        "testo": "Taglia maglietta",
        "opzioni": ["S", "M"],
        "obbligatoria": True,
    },
    {"tipo": "LUNGA", "testo": "Perché vuoi partecipare?", "obbligatoria": True},
    {"tipo": "SI_NO", "testo": "Sai nuotare?"},
    {"tipo": "FOTO", "testo": "Una tua foto", "obbligatoria": True},
]


def _scheda(capo, evento) -> dict:
    scheda = _json(
        capo, "post", "/api/v1/buonacaccia/schede", {"nome": "Piccole Orme", "domande": DOMANDE}
    )
    assert scheda.status_code == 201, scheda.content
    scheda = scheda.json()
    _json(
        capo,
        "put",
        f"/api/v1/buonacaccia/eventi/{evento.pk}/scheda",
        {"versione_id": scheda["ultima"]["id"]},
    )
    return scheda


def test_le_schede_si_salvano_in_versioni(capo):
    scheda = _scheda(capo, _evento_finto(capo))
    url = f"/api/v1/buonacaccia/schede/{scheda['id']}"
    domande = scheda["ultima"]["domande"]
    # Unchanged: the same version.
    assert (
        _json(capo, "put", url, {"nome": "Piccole Orme", "domande": domande}).json()["versioni"]
        == 1
    )
    cambiate = [*domande[:3], {"tipo": "BREVE", "testo": "Allergie?"}]
    nuova = _json(capo, "put", url, {"nome": "Piccole Orme", "domande": cambiate}).json()
    assert nuova["versioni"] == 2
    # The kept questions keep their id: older answers still match.
    assert [d["id"] for d in nuova["ultima"]["domande"][:3]] == [d["id"] for d in domande[:3]]


def _evento_finto(capo):
    evento = Evento(
        titolo="Campetto", tipo=TipoEvento.CAMPO, inizio=_quando(OGGI), fine=_quando(OGGI)
    )
    return servizi.salva_evento(evento, EventoBuonaCaccia(), capo.utente)


def test_scheda_non_valida(capo):
    risposta = _json(
        capo,
        "post",
        "/api/v1/buonacaccia/schede",
        {
            "nome": "X",
            "domande": [{"tipo": "SCELTA_SINGOLA", "testo": "Una sola", "opzioni": ["A"]}],
        },
    )
    assert risposta.status_code == 400


def _foto_grande() -> SimpleUploadedFile:
    from PIL import Image

    immagine = Image.effect_noise((2400, 1800), 120).convert("RGB")
    buffer = io.BytesIO()
    immagine.save(buffer, "PNG")
    return SimpleUploadedFile("IMG_0001.png", buffer.getvalue())


def test_la_famiglia_risponde_e_lo_staff_ricopia(capo, genitore, ragazza, piccole_orme):
    scheda = _scheda(capo, piccole_orme)
    taglia, perche, nuoto, _foto = (d["id"] for d in scheda["ultima"]["domande"])
    iscrizione = _iscrivi(capo, piccole_orme, ragazza)
    url = f"/api/v1/buonacaccia/iscrizioni/{iscrizione.pk}"
    assert (
        _json(genitore, "put", f"{url}/risposte", {"risposte": {taglia: "XL"}}).status_code == 400
    )
    risposta = _json(ragazza, "put", f"{url}/risposte", {"risposte": {taglia: "M", nuoto: True}})
    assert risposta.json()["risposte_mancanti"] == ["Perché vuoi partecipare?", "Una tua foto"]
    assert _json(capo, "put", f"{url}/risposte", {"risposte": {}}).status_code == 403
    # The photo becomes a JPEG of at most 1 MB.
    risposta = _client(genitore).post(f"{url}/foto", {"file": _foto_grande()})
    assert risposta.status_code == 200, risposta.content
    iscrizione.refresh_from_db()
    contenuto = iscrizione.foto.read()
    assert contenuto[:3] == b"\xff\xd8\xff" and len(contenuto) <= 1024 * 1024
    _json(
        genitore, "put", f"{url}/risposte", {"risposte": {taglia: "M", perche: "Mi piace cucinare"}}
    )
    # The presentation: capi only.
    _json(capo, "put", f"{url}/presentazione", {"testo": "Giulia è attenta e curiosa."})
    evento = _client(genitore).get(f"/api/v1/buonacaccia/eventi/{piccole_orme.pk}").json()
    assert evento["iscrizioni"][0]["presentazione"] is None
    assert evento["iscrizioni"][0]["risposte_mancanti"] == []
    assert _client(genitore).get(f"{url}/riepilogo").status_code == 403
    riepilogo = _client(capo).get(f"{url}/riepilogo").json()
    assert [r["risposta"] for r in riepilogo["righe"]] == [
        "M",
        "Mi piace cucinare",
        "",
        "Foto pronta",
    ]
    assert riepilogo["presentazione"] == "Giulia è attenta e curiosa."
    # Filled in on BuonaCaccia: the answers are closed.
    _json(capo, "put", f"{url}/passi", {"scheda_inviata_il": OGGI.isoformat()})
    assert _json(genitore, "put", f"{url}/risposte", {"risposte": {taglia: "S"}}).status_code == 400


# --- Reminders (DEC-158, DEC-160) --------------------------------------------------------


def test_promemoria_allo_staff_e_alla_famiglia_una_volta(capo, genitore, ragazza, piccole_orme):
    # Registered 7 days ago: the deadline is in 2 days, the release form's today.
    _iscrivi(capo, piccole_orme, ragazza, giorni_fa=7)
    mail.outbox.clear()
    assert promemoria(OGGI) > 0
    allo_staff = [m for m in mail.outbox if m.to == ["capo@example.invalid"]]
    assert allo_staff and "caricare la liberatoria" in allo_staff[0].body
    alla_famiglia = [m for m in mail.outbox if m.to == ["genitore@example.invalid"]]
    assert alla_famiglia and "liberatoria" in alla_famiglia[0].body
    mail.outbox.clear()
    assert promemoria(OGGI) == 0


def test_promemoria_dell_ultimo_giorno_per_cancellare(capo, ragazza, piccole_orme):
    iscrizione = _iscrivi(capo, piccole_orme, ragazza)
    iscrizione.liberatoria_ricevuta_il = OGGI
    iscrizione.save()
    mail.outbox.clear()
    promemoria(iscrizione.limite_cancellazione)
    assert any("ultimo giorno per cancellare" in m.body for m in mail.outbox)


# --- Adults and capi training (DEC-164) -------------------------------------------------


def test_formazione_capi_per_la_zona(capogruppo, capo, altro_capo):
    evento = Evento(
        titolo="CFM Campania",
        tipo=TipoEvento.CAMPO,
        inizio=_quando(OGGI + timedelta(days=5)),
        fine=_quando(OGGI + timedelta(days=11)),
        luogo="Sorrento",
    )
    servizi.salva_evento(
        evento,
        EventoBuonaCaccia(formazione_capi=True, tipo_campo=TipoCampoFormazione.CFM),
        altro_capo.utente,
    )
    risposta = _json(
        altro_capo,
        "put",
        f"/api/v1/buonacaccia/eventi/{evento.pk}/partecipanti",
        {"persona_id": altro_capo.pk, "quota_versata": "120.00"},
    )
    assert risposta.status_code == 200
    from apps.core.anno import AnnoAssociativo

    anno = AnnoAssociativo.da_data(OGGI + timedelta(days=5)).anno_fine
    assert _client(capo).get(f"/api/v1/buonacaccia/formazione?anno={anno}").status_code == 403
    (riga,) = _client(capogruppo).get(f"/api/v1/buonacaccia/formazione?anno={anno}").json()
    assert riga["tipo_campo"] == "Campo di Formazione Metodologica (CFM)"
    assert (riga["luogo"], riga["quota_versata"]) == ("Sorrento", "120.00")
    foglio = _client(capogruppo).get(f"/api/v1/buonacaccia/formazione.xlsx?anno={anno}")
    assert foglio.status_code == 200 and foglio.content[:2] == b"PK"
    # In the capo's own calendar, whatever the view.
    from apps.eventi.calendario import eventi_del_calendario

    assert evento in eventi_del_calendario(altro_capo.utente, "unita")


def test_quota_versata_solo_per_la_formazione(capo, piccole_orme):
    risposta = _json(
        capo,
        "put",
        f"/api/v1/buonacaccia/eventi/{piccole_orme.pk}/partecipanti",
        {"persona_id": capo.pk, "quota_versata": "10"},
    )
    assert risposta.status_code == 400


# --- Data subjects' rights (DEC-102) --------------------------------------------------------


def test_esportazione_e_cancellazione(capo, ragazza, piccole_orme):
    from apps.diritti.servizi import cancella, fascicolo

    iscrizione = _iscrivi(capo, piccole_orme, ragazza)
    iscrizione.presentazione = "Brava"
    iscrizione.save()
    (riga,) = fascicolo(ragazza)["eventi_buonacaccia"]
    assert riga["Presentazione dello staff"] == "Brava"
    cancella(ragazza)
    assert not IscrizioneBuonaCaccia.objects.exists()
