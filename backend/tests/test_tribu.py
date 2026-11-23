"""Totem names, their images and «La mia tribù» (DEC-416)."""

from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from PIL import Image

from apps.anagrafica.models import Appartenenza, Persona, RuoloAppartenenza
from apps.diritti import servizi as diritti
from apps.impostazioni.models import Impostazioni
from apps.organizzazione.models import Composizione, TipoUnita, Unita
from apps.permessi import policy
from apps.tribu import servizi, testi
from apps.tribu.models import Totem
from tests.conftest import INIZIO_ANNO, crea_persona, nato_anni_fa

pytestmark = pytest.mark.django_db


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


def _jpeg() -> SimpleUploadedFile:
    buffer = BytesIO()
    Image.new("RGB", (400, 400), "brown").save(buffer, "JPEG")
    return SimpleUploadedFile("castoro.jpg", buffer.getvalue(), content_type="image/jpeg")


def _nell_unita(nome: str, unita: Unita, eta: int, login: str) -> Persona:
    persona = crea_persona(nome, "Prova", login, data_nascita=nato_anni_fa(eta))
    Appartenenza.objects.create(
        persona=persona, unita=unita, ruolo=RuoloAppartenenza.RAGAZZO, data_inizio=INIZIO_ANNO
    )
    return persona


@pytest.fixture
def clan(gruppo) -> Unita:
    return Unita.objects.create(
        gruppo=gruppo, nome="Clan Prova", tipo=TipoUnita.CLAN_FUOCO, composizione=Composizione.MISTA
    )


@pytest.fixture
def rover(clan) -> Persona:
    return _nell_unita("Marco", clan, 18, "rover@example.invalid")


@pytest.fixture
def lupetto(gruppo) -> Persona:
    branco = Unita.objects.create(
        gruppo=gruppo, nome="Branco", tipo=TipoUnita.BRANCO, composizione=Composizione.MISTA
    )
    return _nell_unita("Luca", branco, 9, "lupetto@example.invalid")


def test_chi_puo_avere_un_totem(capo, ragazza, rover, lupetto, genitore, estraneo):
    for chi in (capo, ragazza, rover):
        assert policy.puo_avere_totem(chi)
    for chi in (lupetto, genitore, estraneo):
        assert not policy.puo_avere_totem(chi)


def test_chi_assegna_il_totem(capo, capogruppo, csq, ragazza, rover, genitore, estraneo):
    # The capo is capo unità of the reparto, not of the clan.
    assert policy.puo_assegnare_totem(capo.utente, ragazza)
    assert not policy.puo_assegnare_totem(capo.utente, rover)
    assert policy.puo_assegnare_totem(capogruppo.utente, rover)
    # A capo's totem: the capigruppo only.
    assert policy.puo_assegnare_totem(capogruppo.utente, capo)
    assert not policy.puo_assegnare_totem(capo.utente, capo)
    for chi in (csq, ragazza, genitore, estraneo):
        assert not policy.puo_assegnare_totem(chi.utente, ragazza)

    url = f"/api/v1/persone/{ragazza.pk}/totem"
    assert (
        _client(capo).put(url, {"nome": "  Castoro   Operoso "}, "application/json").status_code
        == 200
    )
    assert Totem.objects.get(persona=ragazza).nome == "Castoro Operoso"
    for chi in (csq, genitore, estraneo):
        risposta = _client(chi).put(url, {"nome": "Altro"}, "application/json")
        assert risposta.status_code in (403, 404)
    # Her own totem: she sees it, she does not change it.
    assert _client(ragazza).get(url).json()["nome"] == "Castoro Operoso"
    assert _client(ragazza).put(url, {"nome": "Altro"}, "application/json").status_code == 403
    # Empty takes it away.
    assert _client(capo).put(url, {"nome": ""}, "application/json").status_code == 200
    assert not Totem.objects.filter(persona=ragazza).exists()


def test_chi_vede_il_totem_di_una_persona(capo, csq, ragazza, genitore, estraneo, lupetto):
    url = f"/api/v1/persone/{ragazza.pk}/totem"
    # Without a totem: the capi see the card, she does not.
    assert _client(capo).get(url).status_code == 200
    assert _client(ragazza).get(url).status_code == 404
    servizi.assegna(ragazza, "Castoro Operoso")
    servizi.assegna(csq, "Quercia Paziente")
    assert _client(ragazza).get(url).status_code == 200
    # Never the parents nor the other ragazzi, even with a totem, on the person's page.
    for chi in (genitore, estraneo, csq):
        assert _client(chi).get(url).status_code == 404
    # Nobody gives a totem below the reparto.
    assert _client(capo).get(f"/api/v1/persone/{lupetto.pk}/totem").status_code == 404


def test_la_mia_tribu(capo, capogruppo, csq, ragazza, rover, genitore, estraneo, lupetto):
    servizi.assegna(ragazza, "Castoro Operoso")
    servizi.assegna(rover, "Volpe Astuta")
    servizi.assegna(capo, "Aquila Saggia")
    # Who has a totem and the capi, even without one.
    for chi in (capo, capogruppo, ragazza, rover):
        assert policy.vede_tribu(chi.utente)
        assert _client(chi).get("/api/v1/io").json()["tribu"]
    for chi in (csq, genitore, estraneo, lupetto):
        assert not policy.vede_tribu(chi.utente)
        assert _client(chi).get("/api/v1/tribu").status_code == 404

    tribu = _client(ragazza).get("/api/v1/tribu").json()
    assert tribu["descrizione"] == testi.DESCRIZIONE_BASE
    assert tribu["mio"]["nome"] == "Castoro Operoso"
    altri = {t["nome"]: t["persona"] for t in tribu["totem"]}
    # Alphabetical, her own apart.
    assert list(altri) == ["Aquila Saggia", "Volpe Astuta"]
    # Whose it is: the capi, not the rover of another unit.
    assert altri["Aquila Saggia"]["id"] == capo.pk
    assert altri["Volpe Astuta"] is None
    assert not tribu["cerimonia"] and tribu["da_approvare"] == []

    # The capi always know whose it is.
    tribu = _client(capogruppo).get("/api/v1/tribu").json()
    assert tribu["mio"] is None
    assert {t["persona"]["id"] for t in tribu["totem"]} == {ragazza.pk, rover.pk, capo.pk}

    # A ragazza of the same unit is known by name.
    servizi.assegna(csq, "Quercia Paziente")
    tribu = _client(ragazza).get("/api/v1/tribu").json()
    assert {t["nome"]: t["persona"] for t in tribu["totem"]}["Quercia Paziente"]["id"] == csq.pk


def test_chi_lascia_il_gruppo_lascia_la_tribu(capo, ragazza):
    servizi.assegna(ragazza, "Castoro Operoso")
    Appartenenza.objects.filter(persona=ragazza).update(data_fine=INIZIO_ANNO.replace(day=2))
    assert not policy.vede_tribu(ragazza.utente)
    assert _client(capo).get("/api/v1/tribu").json()["totem"] == []


def test_immagine_del_ragazzo_attende_un_capo(capo, capogruppo, csq, ragazza, genitore):
    totem = servizi.assegna(ragazza, "Castoro Operoso")
    servizi.assegna(csq, "Quercia Paziente")
    url = f"/api/v1/persone/{ragazza.pk}/totem/immagine"
    # Only the owner and who assigns the totem.
    for chi in (csq, genitore):
        assert _client(chi).post(url, {"file": _jpeg()}).status_code in (403, 404)
    dati = _client(ragazza).post(url, {"file": _jpeg()}).json()
    assert dati["in_attesa"] and not dati["immagine"] and dati["da_approvare"]
    immagine = f"/api/v1/tribu/{totem.pk}/immagine"
    # Waiting: the others do not see it yet; she and the capi do.
    assert _client(csq).get(immagine).status_code == 404
    assert _client(csq).get(immagine, {"in_attesa": True}).status_code == 404
    assert _client(ragazza).get(immagine, {"in_attesa": True}).status_code == 200
    assert _client(capogruppo).get(immagine, {"in_attesa": True}).status_code == 200
    assert _client(capo).get("/api/v1/io").json()["immagini_totem_da_approvare"] == 1
    da_approvare = _client(capo).get("/api/v1/tribu").json()["da_approvare"]
    assert [t["id"] for t in da_approvare] == [totem.pk]

    # A ragazzo does not approve.
    approva = f"/api/v1/tribu/{totem.pk}/immagine/approva"
    assert _client(csq).post(approva).status_code == 403
    assert _client(capo).post(approva).status_code == 200
    assert _client(csq).get(immagine).status_code == 200
    assert _client(capo).get("/api/v1/io").json()["immagini_totem_da_approvare"] == 0

    # A new one waits while the approved one stays.
    _client(ragazza).post(url, {"file": _jpeg()})
    rifiuta = f"/api/v1/tribu/{totem.pk}/immagine/rifiuta"
    assert _client(capo).post(rifiuta, {"motivo": " "}, "application/json").status_code == 400
    risposta = _client(capo).post(rifiuta, {"motivo": "Non c'entra"}, "application/json")
    assert risposta.status_code == 200
    dati = _client(ragazza).get(f"/api/v1/persone/{ragazza.pk}/totem").json()
    assert dati["immagine"] and not dati["in_attesa"]
    assert dati["avviso"] == "Immagine non approvata da un capo: Non c'entra"


def test_immagine_del_capo_subito_e_tolta(capo, csq, ragazza):
    totem = servizi.assegna(ragazza, "Castoro Operoso")
    servizi.assegna(csq, "Quercia Paziente")
    url = f"/api/v1/persone/{ragazza.pk}/totem/immagine"
    dati = _client(capo).post(url, {"file": _jpeg()}).json()
    assert dati["immagine"] and not dati["in_attesa"]
    immagine = f"/api/v1/tribu/{totem.pk}/immagine"
    assert _client(csq).get(immagine).status_code == 200

    togli = f"/api/v1/tribu/{totem.pk}/immagine/togli"
    assert _client(csq).post(togli, {"motivo": "No"}, "application/json").status_code == 403
    assert (
        _client(capo).post(togli, {"motivo": "Non adatta"}, "application/json").status_code == 200
    )
    assert _client(csq).get(immagine).status_code == 404
    assert Totem.objects.get(pk=totem.pk).avviso_immagine == "Immagine tolta da un capo: Non adatta"
    # A new upload clears the notice.
    _client(ragazza).post(url, {"file": _jpeg()})
    assert Totem.objects.get(pk=totem.pk).avviso_immagine == ""


def test_cerimonia_solo_ai_capi(capo, capogruppo, ragazza):
    servizi.assegna(ragazza, "Castoro Operoso")
    # Not written: nothing at all.
    assert not _client(capo).get("/api/v1/tribu").json()["cerimonia"]
    assert _client(capo).get("/api/v1/tribu/cerimonia").status_code == 404

    url = "/api/v1/impostazioni/tribu"
    dati = {"descrizione": "", "cerimonia": "<p>Il <strong>fuoco</strong></p><script>x</script>"}
    assert _client(capo).put(url, dati, "application/json").status_code == 403
    risposta = _client(capogruppo).put(url, dati, "application/json")
    assert risposta.status_code == 200
    assert risposta.json()["cerimonia_totem"] == "<p>Il <strong>fuoco</strong></p>"

    assert _client(capo).get("/api/v1/tribu").json()["cerimonia"]
    assert "fuoco" in _client(capo).get("/api/v1/tribu/cerimonia").json()["html"]
    pdf = _client(capo).get("/api/v1/tribu/cerimonia.pdf")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    # Never the ragazzi, even with a totem.
    assert not _client(ragazza).get("/api/v1/tribu").json()["cerimonia"]
    assert _client(ragazza).get("/api/v1/tribu/cerimonia").status_code == 404
    assert _client(ragazza).get("/api/v1/tribu/cerimonia.pdf").status_code == 404
    # Only the capigruppo read it in the settings.
    assert "cerimonia_totem" not in _client(capo).get("/api/v1/impostazioni").json() or (
        _client(capo).get("/api/v1/impostazioni").json()["cerimonia_totem"] == ""
    )
    # Empty paragraphs: no ceremony.
    _client(capogruppo).put(url, {"cerimonia": "<p> </p><p><br></p>"}, "application/json")
    assert Impostazioni.carica().cerimonia_totem == ""


def test_descrizione_della_tribu(capogruppo, ragazza):
    servizi.assegna(ragazza, "Castoro Operoso")
    url = "/api/v1/impostazioni/tribu"
    risposta = _client(capogruppo).put(
        url, {"descrizione": " Il  nostro fuoco \r\n\r\n arde "}, "application/json"
    )
    assert risposta.json()["descrizione_tribu"] == "Il nostro fuoco\n\narde"
    assert risposta.json()["descrizione_tribu_base"] == testi.DESCRIZIONE_BASE
    assert _client(ragazza).get("/api/v1/tribu").json()["descrizione"] == "Il nostro fuoco\n\narde"
    # The base text saved as it is stays the base.
    _client(capogruppo).put(url, {"descrizione": testi.DESCRIZIONE_BASE}, "application/json")
    assert Impostazioni.carica().descrizione_tribu == ""
    troppo = {"descrizione": "x" * (testi.LUNGHEZZA_DESCRIZIONE + 1)}
    assert _client(capogruppo).put(url, troppo, "application/json").status_code == 400


def test_diritti_esporta_e_cancella_il_totem(ragazza):
    totem = servizi.assegna(ragazza, "Castoro Operoso")
    servizi.carica_immagine(totem, _jpeg(), da_approvare=False)
    assert diritti.fascicolo(ragazza)["nome_di_totem"] == ["Castoro Operoso"]
    diritti.cancella(ragazza)
    assert not Totem.objects.filter(persona=ragazza).exists()


# --- «Modifica totem» (DEC-418) ------------------------------------------------------


def _modifica(chi, persona, attiva: bool):
    return _client(chi).put(
        f"/api/v1/persone/{persona.pk}/totem/modifica", {"attiva": attiva}, "application/json"
    )


@pytest.fixture
def altro_capo(coca) -> Persona:
    persona = crea_persona("Carla", "Capo", "carla@example.invalid")
    Appartenenza.objects.create(
        persona=persona, unita=coca, ruolo=RuoloAppartenenza.CAPO, data_inizio=INIZIO_ANNO
    )
    return persona


def test_chi_accende_modifica_totem(
    capo, capogruppo, altro_capo, csq, ragazza, rover, genitore, estraneo
):
    # No capo has a totem: the capigruppo turn it on, the other capi not.
    assert not policy.capi_con_totem()
    assert policy.puo_attivare_modifica_totem(capogruppo.utente, altro_capo)
    assert policy.puo_attivare_modifica_totem(capogruppo.utente, ragazza)
    assert not policy.puo_attivare_modifica_totem(capogruppo.utente, capogruppo)
    assert not policy.puo_attivare_modifica_totem(capo.utente, ragazza)
    assert _modifica(capogruppo, altro_capo, True).status_code == 200

    # A capo with a totem: from now on only the capi with one, for anyone but themself,
    # even outside their unit.
    servizi.assegna(capo, "Aquila Saggia")
    assert policy.capi_con_totem()
    assert policy.puo_attivare_modifica_totem(capo.utente, rover)
    assert policy.puo_attivare_modifica_totem(capo.utente, altro_capo)
    assert not policy.puo_attivare_modifica_totem(capo.utente, capo)
    assert not policy.puo_attivare_modifica_totem(capogruppo.utente, ragazza)
    assert _modifica(capogruppo, ragazza, True).status_code == 403
    # A ragazzo with a totem is not a capo.
    servizi.assegna(csq, "Quercia Paziente")
    for chi in (csq, genitore, estraneo):
        assert not policy.puo_attivare_modifica_totem(chi.utente, ragazza)
        assert _modifica(chi, ragazza, True).status_code in (403, 404)

    # Only who may change the switch sees it.
    risposta = _modifica(capo, ragazza, True).json()
    assert risposta["puo_attivare_modifica"] and risposta["modifica_attiva"]
    vista = _client(capogruppo).get(f"/api/v1/persone/{ragazza.pk}/totem").json()
    assert not vista["puo_attivare_modifica"] and not vista["modifica_attiva"]
    vista = _client(ragazza).get(f"/api/v1/persone/{ragazza.pk}/totem").json()
    assert not vista["puo_attivare_modifica"] and not vista["modifica_attiva"]
    assert vista["puo_scrivere"]
    assert _modifica(capo, ragazza, False).json()["modifica_attiva"] is False


def test_ragazzo_senza_totem_scrive_il_suo_una_volta(capo, rover, ragazza):
    servizi.assegna(capo, "Aquila Saggia")
    servizi.assegna(rover, "Volpe Astuta")
    url = f"/api/v1/persone/{ragazza.pk}/totem"
    # Switch off: nothing about totems or the tribe.
    assert not policy.vede_tribu(ragazza.utente)
    assert not _client(ragazza).get("/api/v1/io").json()["tribu"]
    assert _client(ragazza).get(url).status_code == 404
    assert _client(ragazza).get("/api/v1/tribu").status_code == 404

    _modifica(capo, ragazza, True)
    # Switch on: her card and the tribe's entry, empty until she writes her own.
    assert _client(ragazza).get("/api/v1/io").json()["tribu"]
    tribu = _client(ragazza).get("/api/v1/tribu").json()
    assert tribu["scrivi_il_tuo"]
    assert tribu["totem"] == [] and tribu["mio"] is None and tribu["descrizione"] == ""
    volpe = Totem.objects.get(persona=rover)
    servizi.carica_immagine(volpe, _jpeg(), False)
    assert _client(ragazza).get(f"/api/v1/tribu/{volpe.pk}/immagine").status_code == 404
    vista = _client(ragazza).get(url).json()
    assert vista["id"] is None and vista["puo_scrivere"] and not vista["puo_assegnare"]
    # She cannot take it away nor leave it empty.
    assert _client(ragazza).put(url, {"nome": " "}, "application/json").status_code == 400

    vista = _client(ragazza).put(url, {"nome": "Castoro Operoso"}, "application/json").json()
    assert vista["nome"] == "Castoro Operoso" and not vista["puo_scrivere"]
    assert not policy.modifica_totem_attiva(ragazza)
    tribu = _client(ragazza).get("/api/v1/tribu").json()
    assert not tribu["scrivi_il_tuo"] and tribu["mio"]["nome"] == "Castoro Operoso"
    assert [t["nome"] for t in tribu["totem"]] == ["Aquila Saggia", "Volpe Astuta"]
    # Once only.
    assert _client(ragazza).put(url, {"nome": "Altro"}, "application/json").status_code == 403


def test_capo_scrive_il_suo_con_modifica_totem(capo, altro_capo):
    servizi.assegna(capo, "Aquila Saggia")
    url = f"/api/v1/persone/{altro_capo.pk}/totem"
    # A capo sees the tribe and her own card anyway, but writes only when allowed.
    assert _client(altro_capo).get("/api/v1/tribu").json()["scrivi_il_tuo"] is False
    assert not _client(altro_capo).get(url).json()["puo_scrivere"]
    assert _client(altro_capo).put(url, {"nome": "Lince"}, "application/json").status_code == 403
    _modifica(capo, altro_capo, True)
    assert _client(altro_capo).put(url, {"nome": "Lince"}, "application/json").status_code == 200
    assert not policy.modifica_totem_attiva(altro_capo)


def test_modifica_totem_si_spegne_dopo_ogni_modifica(capo, ragazza):
    servizi.assegna(capo, "Aquila Saggia")
    servizi.assegna(ragazza, "Castoro Operoso")
    _modifica(capo, ragazza, True)
    # Saving the same name changes nothing.
    servizi.assegna(ragazza, "Castoro  Operoso")
    assert policy.modifica_totem_attiva(ragazza)
    # The staff changing it turns it off as well.
    url = f"/api/v1/persone/{ragazza.pk}/totem"
    assert _client(capo).put(url, {"nome": "Castoro Saggio"}, "application/json").status_code == 200
    assert not policy.modifica_totem_attiva(ragazza)
    # With a totem and the switch off she sees, without changing.
    vista = _client(ragazza).get(url).json()
    assert vista["nome"] == "Castoro Saggio" and not vista["puo_scrivere"]
    _modifica(capo, ragazza, True)
    servizi.assegna(ragazza, "")
    assert not policy.modifica_totem_attiva(ragazza)
