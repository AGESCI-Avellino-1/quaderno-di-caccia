"""Personal calendar feed and emails about events and fees (DEC-79)."""

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from django.core import mail
from django.core.management import call_command
from django.test import Client
from django.utils import timezone

from apps.accounts.models import User
from apps.eventi import calendario, servizi
from apps.eventi.models import CalendarioPersonale, Evento, Livello, TipoEvento
from apps.organizzazione.models import Incarico, RuoloIncarico
from apps.quote.models import CategoriaQuota, Destinatari, Quota, TipoQuota
from tests.conftest import INIZIO_ANNO, crea_capo

pytestmark = pytest.mark.django_db

ROMA = ZoneInfo("Europe/Rome")


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi if isinstance(chi, User) else chi.utente)
    return client


@pytest.fixture
def staff(reparto, coca):
    persona = crea_capo("Elena", "Staff", "staff@example.invalid")
    Incarico.objects.create(
        persona=persona, ruolo=RuoloIncarico.STAFF, unita=reparto, data_inizio=INIZIO_ANNO
    )
    return persona


def _futuro(giorni: int, ora: int = 9) -> datetime:
    return datetime.combine(date.today() + timedelta(days=giorni), time(ora), ROMA)


def _uscita(reparto, staff, **campi):
    return servizi.crea(
        Evento(
            titolo=campi.pop("titolo", "Uscita, al lago"),
            tipo=TipoEvento.USCITA,
            livello=Livello.UNITA,
            inizio=campi.pop("inizio", _futuro(30)),
            fine=campi.pop("fine", _futuro(31, 17)),
            luogo="Lago Laceno; piazzale",
            **campi,
        ),
        [reparto],
        staff.utente,
    )


# --- Calendar ---------------------------------------------------------------------------------


def test_feed_con_link_segreto(reparto, staff, ragazza, genitore, estraneo):
    evento = _uscita(reparto, staff)
    indirizzo = _client(genitore).get("/api/v1/calendario").json()["url"]
    token = indirizzo.rsplit("/", 1)[-1]
    feed = Client().get(f"/api/v1/calendario/{token}")  # no login: calendar apps
    assert feed.status_code == 200
    assert feed["Content-Type"].startswith("text/calendar")
    testo = feed.content.decode()
    assert f"UID:evento-{evento.pk}@" in testo
    assert "SUMMARY:Uscita\\, al lago" in testo
    assert r"LOCATION:Lago Laceno\; piazzale" in testo
    assert "Giulia" not in testo  # no names
    assert "\r\n" in testo

    nuovo = _client(genitore).post("/api/v1/calendario/rigenera").json()["url"]
    assert nuovo != indirizzo
    assert Client().get(f"/api/v1/calendario/{token}").status_code == 404
    assert Client().get("/api/v1/calendario/inventato.ics").status_code == 404
    estraneo_feed = calendario.eventi_del_calendario(estraneo.utente)
    assert not estraneo_feed.exists()


def test_feed_del_capo_e_di_chi_non_partecipa(reparto, staff, ragazza, genitore):
    evento = _uscita(reparto, staff)
    assert calendario.eventi_del_calendario(staff.utente).filter(pk=evento.pk).exists()
    servizi.non_partecipa(evento.partecipazioni.get(persona=ragazza), genitore.utente)
    assert not calendario.eventi_del_calendario(genitore.utente).filter(pk=evento.pk).exists()


def test_righe_lunghe_piegate():
    riga = "SUMMARY:" + "à" * 60
    piegata = calendario._piega(riga)
    assert all(len(p.encode()) <= 75 for p in piegata.split("\r\n"))
    assert piegata.replace("\r\n ", "") == riga


def test_token_lungo_e_unico(genitore):
    calendario_ = CalendarioPersonale.objects.create(utente=genitore.utente)
    assert len(calendario_.token) >= 40


# --- Emails about events ----------------------------------------------------------------------


def test_email_nuovo_evento_modifica_annullamento(
    reparto, staff, ragazza, genitore, genitrice_senza_account
):
    corpo = {
        "titolo": "Uscita di primavera",
        "tipo": "USCITA",
        "livello": "UNITA",
        "unita": [reparto.pk],
        "inizio": _futuro(20).isoformat(),
        "fine": _futuro(21, 17).isoformat(),
        "luogo": "Montevergine",
    }
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("django.db.transaction.on_commit", lambda funzione: funzione())
        evento = (
            _client(staff).post("/api/v1/eventi", corpo, content_type="application/json").json()
        )
        destinatari = sorted(m.to[0] for m in mail.outbox)
        assert destinatari == ["genitore@example.invalid", "lucia@example.invalid"]
        assert all(len(m.to) == 1 for m in mail.outbox)  # nobody sees the others
        assert "Montevergine" in mail.outbox[0].body
        assert "Giulia" not in mail.outbox[0].body

        mail.outbox.clear()
        _client(staff).put(
            f"/api/v1/eventi/{evento['id']}",
            {**corpo, "titolo": "Altro titolo"},
            content_type="application/json",
        )
        assert mail.outbox == []  # only dates and place are announced
        _client(staff).put(
            f"/api/v1/eventi/{evento['id']}",
            {**corpo, "luogo": "Sede"},
            content_type="application/json",
        )
        assert mail.outbox[0].subject.startswith("Cambiato")

        mail.outbox.clear()
        _client(staff).post(
            f"/api/v1/eventi/{evento['id']}/annulla",
            {"motivo": "Pioggia"},
            content_type="application/json",
        )
        assert mail.outbox[0].subject.startswith("Annullato")
        assert "Pioggia" in mail.outbox[0].body


def test_riunioni_ricorrenti_e_eventi_passati_non_annunciati(reparto, staff, ragazza, genitore):
    from apps.eventi import avvisi
    from apps.eventi.models import RiunioneRicorrente

    passato = _uscita(reparto, staff, inizio=_futuro(-10), fine=_futuro(-9))
    assert avvisi.nuovo(passato) == 0
    riunione = RiunioneRicorrente.objects.create(
        unita=reparto,
        giorno_settimana=5,
        ora_inizio=time(16),
        ora_fine=time(18),
        dal=date.today(),
        al=date.today() + timedelta(days=14),
    )
    [prima, *_] = servizi.genera_riunioni(riunione, staff.utente)
    assert avvisi.nuovo(prima) == 0


# --- Fee reminders ----------------------------------------------------------------------------


def test_promemoria_quote_una_volta(reparto, staff, ragazza, genitore, csq):
    tipo = TipoQuota.objects.create(
        nome="Quota di gruppo",
        categoria=CategoriaQuota.GRUPPO,
        anno=2026,
        importo=Decimal("40"),
        destinatari=Destinatari.TUTTI,
        scadenza=date(2025, 11, 30),
    )
    oggi = date.today()
    vicina = Quota.objects.create(
        tipo=tipo,
        persona=ragazza,
        periodo=oggi,
        scadenza=oggi + timedelta(days=5),
        importo=Decimal("40"),
    )
    Quota.objects.create(
        tipo=tipo,
        persona=ragazza,
        periodo=oggi - timedelta(days=1),
        scadenza=oggi + timedelta(days=30),
        importo=Decimal("40"),
    )
    call_command("promemoria_quote")
    [messaggio] = [m for m in mail.outbox if m.to == ["genitore@example.invalid"]]
    assert "40,00 €" in messaggio.body and "Giulia" in messaggio.body
    vicina.refresh_from_db()
    assert vicina.promemoria_il == timezone.localdate()
    mail.outbox.clear()
    call_command("promemoria_quote")
    assert mail.outbox == []


def test_tre_viste_del_calendario_per_i_capi(
    reparto, coca, clan_e_staff, staff, capogruppo, ragazza
):
    clan, staff_clan = clan_e_staff
    del_reparto = _uscita(reparto, staff, titolo="Reparto")
    del_clan = _uscita(clan, staff_clan, titolo="Clan")
    di_coca = _uscita(coca, capogruppo, titolo="Co.Ca.")

    def titoli(utente, vista):
        return set(calendario.eventi_del_calendario(utente, vista).values_list("titolo", flat=True))

    assert titoli(staff.utente, "unita") == {"Reparto"}
    assert titoli(staff.utente, "coca") == {"Reparto", "Co.Ca."}
    assert titoli(staff.utente, "gruppo") == {"Reparto", "Clan", "Co.Ca."}
    # A capogruppo who serves no unit: nothing in the narrowest view.
    assert titoli(capogruppo.utente, "unita") == set()
    assert titoli(capogruppo.utente, "coca") == {"Co.Ca."}
    del del_reparto, del_clan, di_coca
    viste = _client(staff).get("/api/v1/calendario").json()["viste"]
    assert [v["vista"] for v in viste] == ["unita", "coca", "gruppo"]
    assert viste[1]["url"].endswith("?vista=coca")
    assert _client(ragazza).get("/api/v1/calendario").json()["viste"] == []


@pytest.fixture
def clan_e_staff(gruppo, coca):
    from apps.organizzazione.models import Composizione, TipoUnita, Unita

    clan = Unita.objects.create(
        gruppo=gruppo, nome="Hirpinia", tipo=TipoUnita.CLAN_FUOCO, composizione=Composizione.MISTA
    )
    persona = crea_capo("Carla", "Clan", "carla@example.invalid")
    Incarico.objects.create(
        persona=persona, ruolo=RuoloIncarico.STAFF, unita=clan, data_inizio=INIZIO_ANNO
    )
    return clan, persona
