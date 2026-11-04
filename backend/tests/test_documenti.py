"""The Download page and the Progetto Educativo di Gruppo (DEC-341…DEC-344)."""

from datetime import date, timedelta

import pytest
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import Client
from django.utils import timezone

from apps.anagrafica.models import PreferenzeEmail, RelazioneTutela, TipoTutela, VisibilitaGenitori
from apps.core.anno import AnnoAssociativo
from apps.documenti import servizi
from apps.documenti.models import Documento, VersionePeg
from apps.impostazioni.models import Impostazioni
from apps.organizzazione.models import Gruppo
from tests.conftest import INIZIO_ANNO, crea_capo, crea_persona, nato_anni_fa

pytestmark = pytest.mark.django_db

PDF = b"%PDF-1.4 contenuto"
DOCX = b"PK\x03\x04 contenuto"
URL = "/api/v1/download"


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


def _pdf(nome="regolamento.pdf", contenuto=PDF):
    return SimpleUploadedFile(nome, contenuto, content_type="application/pdf")


def _dati(**altri) -> dict:
    return {
        "titolo": "Regolamento",
        "descrizione": "Le regole del campo",
        "durata": "SEMPRE",
        **altri,
    }


def _carica(chi, file=None, **altri):
    corpo = _dati(**altri)
    corpo["file"] = file or _pdf()
    return _client(chi).post("/api/v1/documenti", corpo)


def _titoli(chi) -> list[str]:
    return [d["titolo"] for d in _client(chi).get(URL).json()["documenti"]]


@pytest.fixture(autouse=True)
def email_accese():
    imp = Impostazioni.carica()
    imp.email_capi = imp.email_genitori = imp.email_ragazzi = True
    imp.save()


# --- Who loads ---------------------------------------------------------------------------


def test_caricano_tutti_i_capi_mai_i_ragazzi(capo, capogruppo, csq, ragazza, genitore, estraneo):
    for chi in (csq, ragazza, genitore, estraneo):
        assert _carica(chi, per_coca=True).status_code == 403
    assert _carica(capo, per_coca=True).status_code == 201
    assert _client(capo).get(URL).json()["puo_caricare"] is True
    assert _client(ragazza).get(URL).json()["puo_caricare"] is False


def test_un_capo_carica_anche_per_un_altra_unita(capogruppo, reparto):
    altro = crea_capo("Sara", "Altra", "altra@example.invalid")
    assert _carica(altro, unita=str(reparto.pk)).status_code == 201


def test_capo_in_attesa_non_carica(capogruppo, coca):
    in_attesa = crea_capo("Tea", "Attesa", "attesa@example.invalid")
    in_attesa.codice_socio = "9000000001"
    in_attesa.save()
    assert _carica(in_attesa, per_coca=True).status_code == 403


def test_titolo_descrizione_e_destinatari_obbligatori(capo):
    assert _carica(capo, titolo=" ", per_coca=True).status_code == 400
    assert _carica(capo, descrizione=" ", per_coca=True).status_code == 400
    risposta = _carica(capo)
    assert risposta.status_code == 400
    assert "chi lo vede" in risposta.json()["detail"]


def test_tipi_di_file(capo):
    for nome, contenuto in (
        ("a.docx", DOCX),
        ("a.xlsx", DOCX),
        ("a.pptx", DOCX),
        ("a.doc", b"\xd0\xcf\x11\xe0 x"),
    ):
        assert _carica(capo, _pdf(nome, contenuto), per_coca=True).status_code == 201
    assert _carica(capo, _pdf("a.exe", b"MZ"), per_coca=True).status_code == 400
    # The first bytes must say what the name says.
    assert _carica(capo, _pdf("a.pdf", b"MZ finto"), per_coca=True).status_code == 400
    grande = _pdf("a.pdf", PDF + b"0" * (20 * 1024 * 1024))
    risposta = _carica(capo, grande, per_coca=True)
    assert risposta.status_code == 400
    assert "20 MB" in risposta.json()["detail"]


# --- Who sees ----------------------------------------------------------------------------


def test_tutti_i_capi_vedono_tutto(capo, capogruppo, reparto):
    altro = crea_capo("Sara", "Altra", "altra@example.invalid")
    assert _carica(capogruppo, unita=str(reparto.pk)).status_code == 201
    assert _titoli(altro) == ["Regolamento"]


def test_solo_coca(capo, csq, ragazza, genitore, estraneo):
    _carica(capo, per_coca=True)
    for chi in (csq, ragazza, genitore, estraneo):
        assert _titoli(chi) == []


def test_tutti_i_genitori(capo, ragazza, csq, genitore, estraneo):
    _carica(capo, per_genitori=True)
    assert _titoli(genitore) == ["Regolamento"]
    for chi in (ragazza, csq, estraneo):
        assert _titoli(chi) == []


def test_unita_con_ragazzi_e_genitori_a_scelta(capo, reparto, ragazza, genitore, estraneo):
    _carica(capo, unita=str(reparto.pk))
    assert _titoli(ragazza) == [] and _titoli(genitore) == []
    documento = Documento.objects.get()
    documento.unita_ragazzi = True
    documento.save()
    assert _titoli(ragazza) == ["Regolamento"] and _titoli(genitore) == []
    documento.unita_ragazzi, documento.unita_genitori = False, True
    documento.save()
    assert _titoli(ragazza) == [] and _titoli(genitore) == ["Regolamento"]
    assert _titoli(estraneo) == []


def test_genitore_di_un_altra_unita(capo, gruppo, reparto, genitore):
    from apps.organizzazione.models import TipoUnita, Unita

    altra = Unita.objects.create(gruppo=gruppo, nome="Clan", tipo=TipoUnita.CLAN_FUOCO)
    _carica(capo, unita=str(altra.pk), unita_genitori="true")
    assert _titoli(genitore) == []


def test_genitori_di_maggiorenne_secondo_il_figlio(capo, gruppo):
    from apps.anagrafica.models import Appartenenza, RuoloAppartenenza
    from apps.organizzazione.models import TipoUnita, Unita

    clan = Unita.objects.create(gruppo=gruppo, nome="Clan", tipo=TipoUnita.CLAN_FUOCO)
    rover = crea_persona("Rino", "Rover", "rino-d@example.invalid", data_nascita=nato_anni_fa(19))
    Appartenenza.objects.create(
        persona=rover, unita=clan, ruolo=RuoloAppartenenza.RAGAZZO, data_inizio=INIZIO_ANNO
    )
    padre = crea_persona("Pio", "Rover", "pio-d@example.invalid", data_nascita=nato_anni_fa(50))
    RelazioneTutela.objects.create(tutore=padre, minore=rover, tipo=TipoTutela.GENITORE)
    _carica(capo, unita=str(clan.pk), unita_genitori="true")
    assert _titoli(padre) == ["Regolamento"]
    VisibilitaGenitori.objects.create(persona=rover, scheda=False)
    assert _titoli(padre) == []


def test_visibilita_che_cambia_toglie_l_accesso(capo, genitore):
    _carica(capo, per_genitori=True)
    pk = Documento.objects.get().pk
    assert _client(genitore).get(f"/api/v1/documenti/{pk}/file").status_code == 200
    assert _client(capo).post(f"/api/v1/documenti/{pk}", _dati(per_coca="true")).status_code == 200
    assert _client(genitore).get(f"/api/v1/documenti/{pk}/file").status_code == 404


def test_il_file_si_scarica_col_suo_nome(capo, estraneo):
    _carica(capo, _pdf("Regolamento campo.pdf"), per_coca=True)
    documento = Documento.objects.get()
    risposta = _client(capo).get(f"/api/v1/documenti/{documento.pk}/file")
    assert b"".join(risposta.streaming_content) == PDF
    assert "Regolamento%20campo.pdf" in risposta["Content-Disposition"]
    assert _client(estraneo).get(f"/api/v1/documenti/{documento.pk}/file").status_code == 404
    # Never the original name on disk: it may contain someone's.
    assert "Regolamento" not in documento.file.name


# --- Changing and deleting ---------------------------------------------------------------


def test_modificano_autore_e_capigruppo(capo, capogruppo, genitore):
    _carica(capo, per_genitori=True)
    pk = Documento.objects.get().pk
    altro = crea_capo("Sara", "Altra", "altra@example.invalid")
    url = f"/api/v1/documenti/{pk}"
    assert _client(altro).post(url, _dati(per_coca="true")).status_code == 403
    assert _client(altro).delete(url).status_code == 403
    assert _client(genitore).delete(url).status_code == 403
    assert _client(capo).post(url, _dati(per_coca="true")).status_code == 200
    assert _client(capogruppo).post(url, _dati(per_coca="true")).status_code == 200
    elenco = _client(altro).get(URL).json()["documenti"]
    assert elenco[0]["puo_modificare"] is False


def test_aggiornato_solo_se_cambia_il_file(capo):
    _carica(capo, per_coca=True)
    documento = Documento.objects.get()
    url = f"/api/v1/documenti/{documento.pk}"
    corpo = _dati(per_coca="true", titolo="Nuovo titolo", descrizione="Altra")
    assert _client(capo).post(url, corpo).json()["aggiornato"] is False
    risposta = _client(capo).post(url, {**corpo, "file": _pdf(contenuto=b"%PDF nuovo")})
    assert risposta.json()["aggiornato"] is True
    documento.refresh_from_db()
    assert documento.file.read() == b"%PDF nuovo"
    # After seven days the label goes by itself.
    Documento.objects.update(file_cambiato_il=timezone.now() - timedelta(days=8))
    assert _client(capo).get(URL).json()["documenti"][0]["aggiornato"] is False


@pytest.mark.django_db(transaction=True)
def test_il_file_sostituito_e_quello_eliminato_spariscono(capo, gruppo, coca):
    _carica(capo, per_coca=True)
    documento = Documento.objects.get()
    vecchio, storage = documento.file.name, documento.file.storage
    url = f"/api/v1/documenti/{documento.pk}"
    corpo = _dati(per_coca="true", file=_pdf(contenuto=b"%PDF nuovo"))
    assert _client(capo).post(url, corpo).status_code == 200
    assert not storage.exists(vecchio)
    documento.refresh_from_db()
    nome = documento.file.name
    assert storage.exists(nome)
    assert _client(capo).delete(url).status_code == 204
    assert not Documento.objects.exists()
    assert not storage.exists(nome)


# --- Duration ----------------------------------------------------------------------------


def test_durate(capo):
    corrente = AnnoAssociativo.corrente().anno_fine
    assert _carica(capo, per_coca=True, durata="ANNO", anno=str(corrente)).status_code == 201
    assert _carica(capo, per_coca=True, durata="ANNO", anno=str(corrente + 1)).status_code == 201
    assert _carica(capo, per_coca=True, durata="ANNO", anno=str(corrente - 1)).status_code == 400
    assert _carica(capo, per_coca=True, durata="ANNO").status_code == 400
    ieri = (date.today() - timedelta(days=1)).isoformat()
    assert _carica(capo, per_coca=True, durata="DATA", scade_il=ieri).status_code == 400
    assert _carica(capo, per_coca=True, durata="DATA").status_code == 400
    domani = (date.today() + timedelta(days=1)).isoformat()
    risposta = _carica(capo, per_coca=True, durata="DATA", scade_il=domani)
    assert risposta.json()["ultimo_giorno"] == domani


@pytest.mark.django_db(transaction=True)
def test_alla_scadenza_si_cancella_anche_il_file(capo, gruppo, coca):
    corrente = AnnoAssociativo.corrente().anno_fine
    _carica(capo, per_coca=True, titolo="Scaduto", durata="ANNO", anno=str(corrente))
    _carica(capo, per_coca=True, titolo="Resta")
    scaduto = Documento.objects.get(titolo="Scaduto")
    Documento.objects.filter(pk=scaduto.pk).update(anno=corrente - 1)
    # Out of sight even before the cleaning.
    assert _titoli(capo) == ["Resta"]
    nome, storage = scaduto.file.name, scaduto.file.storage
    call_command("pulisci_documenti")
    assert list(Documento.objects.values_list("titolo", flat=True)) == ["Resta"]
    assert not storage.exists(nome)


def test_l_ultimo_giorno_e_ancora_visibile(capo):
    oggi = date.today().isoformat()
    _carica(capo, per_coca=True, durata="DATA", scade_il=oggi)
    assert servizi.cancella_scaduti(date.today()) == 0
    assert _titoli(capo) == ["Regolamento"]
    assert servizi.cancella_scaduti(date.today() + timedelta(days=1)) == 1


# --- Emails ------------------------------------------------------------------------------


def test_avviso_a_scelta(capo, reparto, ragazza, genitore):
    mail.outbox.clear()
    _carica(capo, unita=str(reparto.pk), unita_genitori="true")
    assert mail.outbox == []
    _carica(capo, unita=str(reparto.pk), unita_genitori="true", avvisa="true")
    destinatari = {m.to[0] for m in mail.outbox}
    assert genitore.utente.email in destinatari or genitore.email in destinatari
    assert ragazza.utente.email not in destinatari
    # The staff of the chosen unit is told too.
    assert capo.utente.email in destinatari or capo.email in destinatari
    assert all("Regolamento" in m.subject for m in mail.outbox)


def test_chi_ha_rifiutato_non_la_riceve(capo, genitore):
    PreferenzeEmail.objects.create(persona=genitore, avvisi=False)
    mail.outbox.clear()
    _carica(capo, per_genitori=True, avvisa="true")
    assert mail.outbox == []


# --- Progetto Educativo di Gruppo --------------------------------------------------------


def _versione(chi, file=None, **altri):
    corpo = {"approvato_il": date.today().isoformat(), "durata": "2026/2029", **altri}
    if file:
        corpo["file"] = file
    return _client(chi).post("/api/v1/peg/versioni", corpo)


def test_lo_caricano_i_capigruppo(capogruppo, capo, genitore, estraneo):
    for chi in (capo, genitore, estraneo):
        assert _versione(chi, _pdf()).status_code == 403
    assert _versione(capogruppo, _pdf()).status_code == 201


def test_pdf_o_testo_mai_entrambi(capogruppo):
    assert _versione(capogruppo).status_code == 400
    assert _versione(capogruppo, _pdf(), testo="<p>x</p>").status_code == 400
    assert _versione(capogruppo, _pdf("a.docx", DOCX)).status_code == 400
    assert _versione(capogruppo, testo="<p>Il nostro progetto</p>").status_code == 201


def test_l_ultima_e_in_vigore_e_lo_storico_resta(capogruppo, capo, ragazza, genitore):
    _versione(capogruppo, _pdf())
    _versione(capogruppo, testo="<p>Seconda</p>")
    for chi in (capo, ragazza, genitore):
        versioni = _client(chi).get(URL).json()["peg"]["versioni"]
        assert [v["in_vigore"] for v in versioni] == [True, False]
        assert versioni[0]["ha_testo"] is True and versioni[1]["nome_file"] == "regolamento.pdf"


def test_chi_e_fuori_non_vede_lo_storico(capogruppo, estraneo):
    _versione(capogruppo, _pdf())
    vecchia = VersionePeg.objects.get().pk
    assert _client(estraneo).get(URL).json()["peg"] is None
    assert _client(estraneo).get(f"/api/v1/peg/versioni/{vecchia}/file").status_code == 404
    assert Client().get(f"/api/v1/peg/versioni/{vecchia}/file").status_code == 401


def test_pagina_pubblica_solo_la_versione_in_vigore(capogruppo):
    pubblica = Client()
    assert pubblica.get("/api/v1/peg/pubblico").json()["ha_pdf"] is False
    assert pubblica.get("/api/v1/peg/pubblico.pdf").status_code == 404
    _versione(capogruppo, _pdf(contenuto=b"%PDF vecchio"))
    _versione(capogruppo, _pdf(contenuto=b"%PDF nuovo"))
    assert pubblica.get("/api/v1/peg/pubblico").json()["durata"] == "2026/2029"
    risposta = pubblica.get("/api/v1/peg/pubblico.pdf")
    assert b"".join(risposta.streaming_content) == b"%PDF nuovo"


def test_il_testo_diventa_pdf_su_carta_intestata(capogruppo, capo):
    _versione(capogruppo, testo="<p>Il nostro progetto</p><script>x</script>")
    assert "<script>" not in VersionePeg.objects.get().testo
    risposta = Client().get("/api/v1/peg/pubblico.pdf")
    assert risposta.status_code == 200 and risposta.content.startswith(b"%PDF")
    assert "Il nostro progetto" in Client().get("/api/v1/peg/pubblico").json()["testo"]


def test_versione_sbagliata_torna_la_precedente(capogruppo, capo):
    _versione(capogruppo, _pdf(contenuto=b"%PDF giusta"), durata="prima")
    _versione(capogruppo, _pdf(contenuto=b"%PDF sbagliata"), durata="seconda")
    ultima = VersionePeg.objects.first()
    url = f"/api/v1/peg/versioni/{ultima.pk}"
    assert _client(capo).delete(url).status_code == 403
    assert _client(capogruppo).delete(url).status_code == 204
    assert Client().get("/api/v1/peg/pubblico").json()["durata"] == "prima"


def test_in_redazione_visibile_a_tutti(capogruppo, capo, genitore):
    url = "/api/v1/peg/in-redazione"
    corpo = {"in_redazione": True}
    assert _client(capo).put(url, corpo, content_type="application/json").status_code == 403
    assert _client(capogruppo).put(url, corpo, content_type="application/json").status_code == 204
    assert Gruppo.objects.get().peg_in_redazione is True
    assert Client().get("/api/v1/peg/pubblico").json()["in_redazione"] is True
    assert _client(genitore).get(URL).json()["peg"]["in_redazione"] is True


def test_avviso_del_peg_a_scelta(capogruppo, capo, genitore, ragazza):
    mail.outbox.clear()
    _versione(capogruppo, _pdf())
    assert mail.outbox == []
    _versione(capogruppo, _pdf(), avvisa="true")
    assert len(mail.outbox) >= 3


def test_durata_sconosciuta_rifiutata(capo):
    assert _carica(capo, per_coca=True, durata="ALTRO").status_code == 422
