"""The agenda of the meetings of the Co.Ca. and of the parents: who reads and writes it, in the
minutes and in the convocation, kept out of the audit log and of the event's card."""

from datetime import timedelta

import pytest
from auditlog.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from django.core import mail
from django.test import Client
from django.utils import timezone

from apps.eventi.models import Cerchia, Evento, Livello, Partecipazione, TipoEvento
from apps.impostazioni.models import Impostazioni
from apps.organizzazione.models import Gruppo
from apps.permessi import policy
from apps.verbali import modelli, servizi
from apps.verbali.models import Verbale

pytestmark = pytest.mark.django_db

AGENDA = "<ol><li><p>Programma dell'anno</p></li><li><p>Varie</p></li></ol>"


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


def _get(chi, url):
    return _client(chi).get(url)


def _post(chi, url, dati=None):
    return _client(chi).post(url, dati or {}, content_type="application/json")


def _put(chi, url, dati):
    return _client(chi).put(url, dati, content_type="application/json")


def _url(evento, altro="ordine-del-giorno") -> str:
    return f"/api/v1/eventi/{evento.pk}/{altro}"


def _nuova(cerchia=Cerchia.TUTTI, unita=(), livello=Livello.UNITA, **campi) -> Evento:
    inizio = timezone.now() + timedelta(days=5)
    evento = Evento.objects.create(
        titolo="Riunione",
        tipo=TipoEvento.RIUNIONE,
        inizio=inizio,
        fine=inizio + timedelta(hours=2),
        cerchia=cerchia,
        livello=livello,
        **campi,
    )
    evento.unita.set(unita)
    return evento


@pytest.fixture(autouse=True)
def email_accese():
    imp = Impostazioni.carica()
    imp.email_capi = imp.email_genitori = imp.email_ragazzi = True
    imp.save()


@pytest.fixture
def di_coca(coca) -> Evento:
    return _nuova(unita=[coca])


@pytest.fixture
def di_genitori(reparto, genitore) -> Evento:
    evento = _nuova(Cerchia.GENITORI, unita=[reparto])
    Partecipazione.objects.create(evento=evento, persona=genitore)
    return evento


def test_chi_legge_e_scrive_alla_coca(di_coca, capo, capogruppo, csq, ragazza, genitore, estraneo):
    assert policy.puo_leggere_ordine_del_giorno(capo.utente, di_coca)
    assert policy.puo_leggere_ordine_del_giorno(capogruppo.utente, di_coca)
    assert policy.puo_scrivere_ordine_del_giorno(capogruppo.utente, di_coca)
    assert not policy.puo_scrivere_ordine_del_giorno(capo.utente, di_coca)
    for persona in (csq, ragazza, genitore, estraneo):
        assert not policy.puo_leggere_ordine_del_giorno(persona.utente, di_coca)
        assert _get(persona, _url(di_coca)).status_code == 404
        assert _put(persona, _url(di_coca), {"testo": AGENDA}).status_code == 404
    assert _put(capo, _url(di_coca), {"testo": AGENDA}).status_code == 403
    assert _put(capogruppo, _url(di_coca), {"testo": AGENDA}).status_code == 200
    assert _get(capo, _url(di_coca)).json()["testo"] == AGENDA


def test_chi_legge_e_scrive_dai_genitori(
    di_genitori, capo, capogruppo, csq, ragazza, genitore, estraneo
):
    assert policy.puo_scrivere_ordine_del_giorno(capo.utente, di_genitori)
    assert policy.puo_scrivere_ordine_del_giorno(capogruppo.utente, di_genitori)
    assert _put(capo, _url(di_genitori), {"testo": AGENDA}).status_code == 200
    risposta = _get(genitore, _url(di_genitori))
    assert risposta.status_code == 200
    assert risposta.json() == {"testo": AGENDA, "puo_scrivere": False}
    assert _put(genitore, _url(di_genitori), {"testo": "x"}).status_code == 403
    assert _get(estraneo, _url(di_genitori)).status_code == 404
    for persona in (csq, ragazza):
        assert not policy.puo_scrivere_ordine_del_giorno(persona.utente, di_genitori)


def test_le_altre_riunioni_non_lo_hanno(reparto, capogruppo):
    evento = _nuova(unita=[reparto])
    assert _get(capogruppo, _url(evento)).status_code == 404
    assemblea = _nuova(Cerchia.SOCI, livello=Livello.GRUPPO)
    assert _get(capogruppo, _url(assemblea)).status_code == 404


def test_il_testo_viene_ripulito_e_vuoto_non_resta(di_coca, capogruppo):
    _put(capogruppo, _url(di_coca), {"testo": "<p>Punto</p><script>alert(1)</script>"})
    di_coca.refresh_from_db()
    assert di_coca.ordine_del_giorno == "<p>Punto</p>"
    _put(capogruppo, _url(di_coca), {"testo": "<p></p>"})
    di_coca.refresh_from_db()
    assert di_coca.ordine_del_giorno == ""


def test_fuori_dalla_scheda_della_riunione(di_coca, capogruppo):
    """The card stays on the device: only whether there is one."""
    _put(capogruppo, _url(di_coca), {"testo": AGENDA})
    risposta = _get(capogruppo, f"/api/v1/eventi/{di_coca.pk}").json()
    assert risposta["con_ordine_del_giorno"] is True
    assert "ordine_del_giorno" not in risposta
    assert "Programma" not in str(risposta)


def test_fuori_dal_registro_con_chi_e_quando(di_coca, capogruppo):
    _put(capogruppo, _url(di_coca), {"testo": AGENDA})
    voci = LogEntry.objects.filter(
        content_type=ContentType.objects.get_for_model(Evento), object_pk=str(di_coca.pk)
    )
    ultima = voci.order_by("-timestamp", "-pk").first()
    assert ultima.actor == capogruppo.utente
    assert list(ultima.changes) == ["ordine_del_giorno_cambiato_il"]
    assert not any("Programma" in str(v.changes) for v in voci)


def _crea(chi, **corpo):
    giorno = timezone.localdate() + timedelta(days=10)
    return _post(
        chi,
        "/api/v1/riunioni",
        {"giorno": giorno.isoformat(), "ora_inizio": "18:00", "ora_fine": "20:00", **corpo},
    )


def test_si_scrive_creando_una_riunione_singola_di_coca(capogruppo, coca):
    risposta = _crea(capogruppo, unita=[coca.pk], ordine_del_giorno=AGENDA)
    assert risposta.status_code == 201, risposta.content
    assert Evento.objects.get(pk=risposta.json()[0]["id"]).ordine_del_giorno == AGENDA


def test_si_scrive_creando_una_riunione_dei_genitori(capo, reparto):
    risposta = _crea(capo, cerchia="GENITORI", unita=[reparto.pk], ordine_del_giorno=AGENDA)
    assert risposta.status_code == 201, risposta.content
    assert Evento.objects.get(pk=risposta.json()[0]["id"]).ordine_del_giorno == AGENDA


def test_rifiutato_creando_una_riunione_che_non_lo_ha(capo, reparto):
    risposta = _crea(capo, unita=[reparto.pk], ordine_del_giorno=AGENDA)
    assert risposta.status_code == 400
    assert not Evento.objects.filter(unita=reparto).exists()


def test_in_una_serie_si_scrive_sulla_singola_riunione(capogruppo, coca):
    oggi = timezone.localdate()
    risposta = _post(
        capogruppo,
        "/api/v1/riunioni",
        {
            "unita": [coca.pk],
            "giorno_settimana": oggi.weekday(),
            "dal": (oggi + timedelta(days=1)).isoformat(),
            "al": (oggi + timedelta(days=21)).isoformat(),
            "ora_inizio": "18:00",
            "ora_fine": "20:00",
        },
    )
    assert risposta.status_code == 201, risposta.content
    prima, seconda = Evento.objects.filter(unita=coca).order_by("inizio")[:2]
    assert _put(capogruppo, _url(prima), {"testo": AGENDA}).status_code == 200
    seconda.refresh_from_db()
    assert seconda.ordine_del_giorno == ""


def test_il_verbale_nuovo_ha_il_segnaposto_si_puo_togliere(di_coca, capogruppo):
    url = _url(di_coca, "verbale")
    assert _get(capogruppo, f"{url}?testo=true").json()["testo"] == "<p>[Ordine del giorno]</p>"
    assert _put(capogruppo, url, {"testo": "<p>Senza</p>"}).status_code == 200
    assert _get(capogruppo, f"{url}?testo=true").json()["testo"] == "<p>Senza</p>"
    _put(capogruppo, url, {"testo": ""})
    assert _get(capogruppo, f"{url}?testo=true").json()["testo"] == ""


def test_il_verbale_gia_iniziato_resta_com_e(di_coca, capogruppo):
    Verbale.objects.create(evento=di_coca, testo="<p>Già scritto</p>", autore_nome="Una Capa")
    risposta = _get(capogruppo, f"{_url(di_coca, 'verbale')}?testo=true").json()
    assert risposta["testo"] == "<p>Già scritto</p>"


def test_chi_legge_la_bozza_vede_l_ordine_del_giorno(di_coca, capo, capogruppo):
    _put(capogruppo, _url(di_coca), {"testo": AGENDA})
    _put(capogruppo, _url(di_coca, "verbale"), {"testo": "<p>[Ordine del giorno]</p><p>Fatto</p>"})
    testo = _get(capo, f"{_url(di_coca, 'verbale')}?testo=true").json()["testo"]
    assert "[Ordine del giorno]" not in testo and "Programma dell'anno" in testo


def test_definitivo_copia_l_ordine_del_giorno(di_coca, capogruppo):
    _put(capogruppo, _url(di_coca), {"testo": AGENDA})
    url = _url(di_coca, "verbale")
    _put(capogruppo, url, {"testo": "<p>[Ordine del giorno]</p><p>Discusso.</p>"})
    assert _post(capogruppo, f"{url}/definitivo").status_code == 200
    _put(capogruppo, _url(di_coca), {"testo": "<p>Cambiato dopo</p>"})
    testo = _get(capogruppo, f"{url}?testo=true").json()["testo"]
    assert testo == f"<p><strong>Ordine del giorno</strong></p>{AGENDA}<p>Discusso.</p>"


def test_solo_il_segnaposto_e_un_verbale_vuoto(di_coca, capogruppo):
    _put(capogruppo, _url(di_coca), {"testo": AGENDA})
    url = _url(di_coca, "verbale")
    _put(capogruppo, url, {"testo": "<p>[Ordine del giorno]</p>"})
    assert _post(capogruppo, f"{url}/definitivo").status_code == 400


def test_segnaposto_in_mezzo_al_testo_e_senza_ordine_del_giorno(di_coca):
    di_coca.ordine_del_giorno = AGENDA
    testo = servizi._con_ordine_del_giorno("<p>Si parla di [Ordine del giorno] oggi</p>", di_coca)
    assert testo.startswith("<p>Si parla di ") and "<ol>" not in testo and "Varie" in testo
    di_coca.ordine_del_giorno = ""
    assert servizi._con_ordine_del_giorno("<p>[Ordine del giorno]</p><p>Sì</p>", di_coca) == (
        "<p>Sì</p>"
    )


def test_convocazione_dei_genitori_con_l_ordine_del_giorno(di_genitori, capo, genitore):
    _put(capo, _url(di_genitori), {"testo": AGENDA})
    assert _post(capo, _url(di_genitori, "convocazione/invia")).status_code == 200
    corpo = mail.outbox[-1].body
    assert "Ordine del giorno" in corpo and "Programma dell'anno" in corpo
    # Changed afterwards: no other email.
    quante = len(mail.outbox)
    _put(capo, _url(di_genitori), {"testo": "<p>Altro</p>"})
    assert len(mail.outbox) == quante


def test_convocazione_dei_genitori_senza_ordine_del_giorno(di_genitori, capo):
    assert _post(capo, _url(di_genitori, "convocazione/invia")).status_code == 200
    assert "Ordine del giorno" not in mail.outbox[-1].body


def test_assemblea_regolamento_non_spuntato_e_punti_nell_email(capogruppo):
    Gruppo.objects.update_or_create(
        defaults={"codice_fiscale": "90000000000"},
        denominazione="Prova 1",
        ordinale="T9999",
    )
    giorno = timezone.localdate() + timedelta(days=10)
    creata = _post(
        capogruppo,
        "/api/v1/riunioni",
        {
            "cerchia": "SOCI",
            "giorno": giorno.isoformat(),
            "ora_inizio": "18:00",
            "ora_fine": "20:00",
        },
    )
    assemblea = Evento.objects.get(pk=creata.json()[0]["id"])
    assert modelli.dati_convocazione(servizi.verbale_di(assemblea))["punti"] == [
        "ELEZIONE",
        "BILANCIO",
        "QUOTA",
        "VARIE",
    ]
    risposta = _put(
        capogruppo,
        _url(assemblea, "convocazione/modello"),
        {
            "punti": ["BILANCIO", "VARIE"],
            "anno_bilancio": 2026,
            "luogo": {
                "presso": "Sede",
                "via": "Via Roma",
                "civico": "1",
                "cap": "83100",
                "citta": "Avellino",
                "provincia": "AV",
            },
        },
    )
    assert risposta.status_code == 200, risposta.content
    assert _post(capogruppo, _url(assemblea, "convocazione/invia")).status_code == 200
    corpo = mail.outbox[-1].body
    assert "1. approvazione del bilancio" in corpo
    assert "2. varie ed eventuali." in corpo
    assert "Regolamento" not in corpo


# --- In the calendar feed (DEC-412) --------------------------------------------------------


def _descrizione(evento) -> str:
    from apps.eventi.calendario import ics

    righe = ics([evento]).replace("\r\n ", "").split("\r\n")
    return next((r for r in righe if r.startswith("DESCRIPTION:")), "")


def test_nel_feed_il_testo_dei_genitori(di_genitori, settings):
    di_genitori.ordine_del_giorno = AGENDA
    di_genitori.save()
    descrizione = _descrizione(di_genitori)
    assert "Ordine del giorno:" in descrizione
    assert "Programma dell'anno" in descrizione


def test_nel_feed_i_punti_dell_assemblea(gruppo):
    assemblea = _nuova(Cerchia.SOCI, livello=Livello.GRUPPO)
    descrizione = _descrizione(assemblea)
    assert descrizione.startswith("DESCRIPTION:Ordine del giorno:")


@pytest.mark.parametrize("cerchia", [Cerchia.TUTTI, Cerchia.STAFF])
def test_nel_feed_solo_il_link_per_coca_e_staff(cerchia, coca, reparto, settings):
    settings.FRONTEND_URL = "https://qdc.example"
    unita = [coca] if cerchia == Cerchia.TUTTI else [reparto]
    riunione = _nuova(cerchia, unita=unita)
    assert _descrizione(riunione) == ""  # no agenda, nothing
    riunione.ordine_del_giorno = AGENDA
    riunione.save()
    descrizione = _descrizione(riunione)
    assert "Programma dell" not in descrizione
    assert f"https://qdc.example/riunioni/{riunione.pk}" in descrizione.replace("\\", "")
