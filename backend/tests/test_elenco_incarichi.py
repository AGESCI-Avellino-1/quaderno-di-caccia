"""The PDF list of the group's roles, for the capigruppo (DEC-284)."""

from datetime import date

import pytest
from django.test import Client

from apps.core.anno import AnnoAssociativo
from apps.organizzazione import elenco_incarichi as elenco
from apps.organizzazione.models import Incarico, RuoloIncarico
from apps.permessi import policy
from tests.conftest import INIZIO_ANNO, crea_capo

pytestmark = pytest.mark.django_db

R = RuoloIncarico
TUTTI = {r.value for r in elenco.RUOLI_ELENCO}


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


def _incarico(persona, ruolo, gruppo=None, unita=None, **date_):
    return Incarico.objects.create(
        persona=persona,
        ruolo=ruolo,
        gruppo=gruppo,
        unita=unita,
        data_inizio=date_.get("dal", INIZIO_ANNO),
        data_fine=date_.get("al"),
    )


@pytest.fixture
def capi(gruppo, reparto, capo, capogruppo):
    """capo: capo unità of the reparto; capogruppo: no unit. Plus a capo serving the
    group, a capogruppo who serves the reparto too (and is group treasurer), and a group
    treasurer with no service."""
    disponibile = crea_capo("Dario", "Disponibile", "disp@example.invalid")
    _incarico(disponibile, R.SUPPORTO_GRUPPO, gruppo=gruppo)
    tesoriere = crea_capo("Tea", "Tesoriera", "tesoriera@example.invalid")
    _incarico(tesoriere, R.TESORIERE_GRUPPO, gruppo=gruppo)
    doppio = crea_capo("Elsa", "Doppia", "doppia@example.invalid")
    _incarico(doppio, R.CAPOGRUPPO, gruppo=gruppo)
    _incarico(doppio, R.STAFF, unita=reparto)
    _incarico(doppio, R.TESORIERE_GRUPPO, gruppo=gruppo)
    capo.livello_formazione = 3
    capo.save()
    return {"disponibile": disponibile, "doppio": doppio, "tesoriere": tesoriere}


def _nomi(sezione):
    return [(r.persona.cognome, r.incarichi) for r in sezione.righe]


def test_per_unita_ogni_capo_in_ogni_sezione_dei_suoi_incarichi(
    capi, capo, capogruppo, reparto, coca
):
    sezioni = elenco.sezioni(TUTTI, "unita", date.today())
    assert [s.titolo for s in sezioni] == [str(coca), str(reparto)]
    # The capogruppo serving the reparto is in both, with that section's roles only
    # (maintainer, 03/11).
    assert _nomi(sezioni[1]) == [("Capo", ["Capo unità"]), ("Doppia", ["Staff di unità"])]
    # The treasurer with no service shows the support service, in the PDF only.
    assert _nomi(sezioni[0]) == [
        ("Disponibile", ["Servizio di supporto al gruppo"]),
        ("Doppia", ["Capogruppo", "Tesoriere di gruppo"]),
        ("Gruppo", ["Capogruppo"]),
        ("Tesoriera", ["Servizio di supporto al gruppo", "Tesoriere di gruppo"]),
    ]


def test_per_unita_servizio_di_supporto_anche_se_non_scelto(capi, coca):
    # Only the group treasurers chosen: who has no service still shows the support one.
    sezioni = elenco.sezioni({R.TESORIERE_GRUPPO}, "unita", date.today())
    assert _nomi(sezioni[-1]) == [
        ("Doppia", ["Tesoriere di gruppo"]),
        ("Tesoriera", ["Servizio di supporto al gruppo", "Tesoriere di gruppo"]),
    ]


def test_per_unita_piu_unita_e_tesoriere_di_unita(gruppo, reparto, coca):
    from apps.organizzazione.models import TipoUnita, Unita

    branco = Unita.objects.create(
        gruppo=gruppo, nome="Branco", tipo=TipoUnita.BRANCO, composizione=reparto.composizione
    )
    in_due = crea_capo("Ugo", "Doppiaunita", "ugo@example.invalid")
    _incarico(in_due, R.STAFF, unita=reparto)
    _incarico(in_due, R.CAPO_UNITA, unita=branco)
    cassiere = crea_capo("Ivo", "Cassiere", "ivo@example.invalid")
    _incarico(cassiere, R.TESORIERE_UNITA, unita=branco)
    sezioni = {s.titolo: _nomi(s) for s in elenco.sezioni(TUTTI, "unita", date.today())}
    # In both units; the unit treasurer with no service in the unit and in the Co.Ca.
    assert sezioni[str(reparto)] == [("Doppiaunita", ["Staff di unità"])]
    assert sezioni[str(branco)] == [
        ("Cassiere", ["Tesoriere di unità"]),
        ("Doppiaunita", ["Capo unità"]),
    ]
    assert sezioni[str(coca)] == [("Cassiere", ["Servizio di supporto al gruppo"])]


def test_per_unita_capigruppo_in_coca_solo_se_scelti(capi, reparto, coca):
    sezioni = elenco.sezioni({R.STAFF}, "unita", date.today())
    assert [s.titolo for s in sezioni] == [str(reparto)]
    sezioni = elenco.sezioni({R.STAFF, R.CAPOGRUPPO}, "unita", date.today())
    assert [s.titolo for s in sezioni] == [str(coca), str(reparto)]
    assert _nomi(sezioni[0]) == [("Doppia", ["Capogruppo"]), ("Gruppo", ["Capogruppo"])]


def test_per_unita_solo_gli_incarichi_scelti(capi, reparto):
    sezioni = elenco.sezioni({R.STAFF, R.CAPO_UNITA}, "unita", date.today())
    # Nobody of the Co.Ca. has a chosen role; next to the name only the chosen ones.
    assert [s.titolo for s in sezioni] == [str(reparto)]
    assert _nomi(sezioni[0]) == [("Capo", ["Capo unità"]), ("Doppia", ["Staff di unità"])]


def test_per_incarico(capi, reparto):
    sezioni = elenco.sezioni({R.CAPOGRUPPO, R.CAPO_UNITA}, "incarico", date.today())
    assert [s.titolo for s in sezioni] == ["Capogruppo", "Capo unità"]
    assert _nomi(sezioni[0]) == [("Doppia", []), ("Gruppo", [])]
    assert _nomi(sezioni[1]) == [("Capo", [str(reparto)])]


def test_anno_passato_solo_gli_incarichi_attivi_alla_fine(gruppo, reparto, coca):
    anno = AnnoAssociativo.da_data(INIZIO_ANNO)
    cambiato = crea_capo("Fabio", "Cambiato", "fabio@example.invalid")
    # Staff until March, then capo unità: at the end of the year only the second.
    _incarico(cambiato, R.STAFF, unita=reparto, al=date(anno.anno_fine, 3, 1))
    _incarico(cambiato, R.CAPO_UNITA, unita=reparto, dal=date(anno.anno_fine, 3, 1))
    giorno = elenco.giorno_di_riferimento(anno.anno_fine, oggi=date(anno.anno_fine + 1, 11, 2))
    assert giorno == anno.fine
    sezioni = elenco.sezioni(TUTTI, "unita", giorno)
    assert _nomi(sezioni[0]) == [("Cambiato", ["Capo unità"])]
    # The year in course: today.
    oggi = date(anno.anno_fine, 5, 1)
    assert elenco.giorno_di_riferimento(anno.anno_fine, oggi=oggi) == oggi
    assert elenco.giorno_di_riferimento(None, oggi=oggi) == oggi


def test_pdf_solo_per_i_capigruppo(
    capi, capo, capogruppo, gruppo, ragazza, csq, genitore, estraneo
):
    assert policy.puo_esportare_incarichi(capogruppo.utente)
    for chi in (capo, ragazza, csq, genitore, estraneo):
        assert not policy.puo_esportare_incarichi(chi.utente)
        assert _client(chi).get("/api/v1/gruppo/incarichi/elenco").status_code == 403
        url = "/api/v1/gruppo/incarichi/elenco.pdf?ruoli=CAPOGRUPPO"
        assert _client(chi).get(url).status_code == 403

    opzioni = _client(capogruppo).get("/api/v1/gruppo/incarichi/elenco").json()
    # "A disposizione" only once someone held it (DEC-293).
    senza = [r.value for r in elenco.RUOLI_ELENCO if r != R.A_DISPOSIZIONE]
    assert [r["valore"] for r in opzioni["ruoli"]] == senza
    _incarico(
        capi["tesoriere"],
        R.A_DISPOSIZIONE,
        gruppo=gruppo,
        dal=date(2024, 1, 1),
        al=date(2025, 1, 1),
    )
    opzioni = _client(capogruppo).get("/api/v1/gruppo/incarichi/elenco").json()
    assert [r["valore"] for r in opzioni["ruoli"]] == [r.value for r in elenco.RUOLI_ELENCO]
    assert opzioni["anni"][0]["valore"] == str(AnnoAssociativo.corrente().anno_fine)

    risposta = _client(capogruppo).get(
        "/api/v1/gruppo/incarichi/elenco.pdf?ruoli=CAPOGRUPPO&ruoli=STAFF&raggruppa=incarico"
    )
    assert risposta.status_code == 200
    assert risposta["Content-Type"] == "application/pdf"
    assert risposta.content.startswith(b"%PDF")


def test_pdf_richieste_sbagliate(capogruppo):
    client = _client(capogruppo)
    base = "/api/v1/gruppo/incarichi/elenco.pdf"
    assert client.get(f"{base}?ruoli=CSQ").status_code == 400
    assert client.get(f"{base}?ruoli=STAFF&raggruppa=altro").status_code == 400
    futuro = AnnoAssociativo.corrente().anno_fine + 1
    assert client.get(f"{base}?ruoli=STAFF&anno={futuro}").status_code == 400


def test_per_unita_coca_poi_lc_eg_rs_per_codice(gruppo, coca):
    """The Co.Ca. first, then L/C, E/G and R/S, each by code (maintainer, 03/11)."""
    from apps.organizzazione.models import Composizione, TipoUnita, Unita

    def unita(tipo, codice, progressivo):
        nuova = Unita.objects.create(
            gruppo=gruppo,
            nome=f"Unità {codice}{progressivo}",
            tipo=tipo,
            composizione=Composizione.MISTA,
            codice_unita=codice,
            progressivo=progressivo,
        )
        capo = crea_capo("Capo", f"{codice}{progressivo}", f"{codice}{progressivo}@example.invalid")
        _incarico(capo, R.STAFF, unita=nuova)
        return nuova

    clan = unita(TipoUnita.CLAN_FUOCO, "T", 1)
    reparto2 = unita(TipoUnita.REPARTO, "E", 2)
    branco = unita(TipoUnita.BRANCO_CERCHIO, "L", 1)
    reparto1 = unita(TipoUnita.REPARTO, "E", 1)
    capogruppo = crea_capo("Lia", "Capogruppo", "lia@example.invalid")
    _incarico(capogruppo, R.CAPOGRUPPO, gruppo=gruppo)
    titoli = [s.titolo for s in elenco.sezioni(TUTTI, "unita", date.today())]
    assert titoli == [str(coca), str(branco), str(reparto1), str(reparto2), str(clan)]


def test_codice_provvisorio_stampato_come_nuovo_censito():
    assert elenco.codice_da_stampare("9000000012") == "NUOVO CENSITO"
    assert elenco.codice_da_stampare("123456") == "123456"
    assert elenco.codice_da_stampare(None) == ""
