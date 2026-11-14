"""The patrol animals (DEC-350...DEC-354)."""

import io
import json
import shutil

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from PIL import Image

from apps.anagrafica.models import Appartenenza, RuoloAppartenenza
from apps.organizzazione import animali
from apps.organizzazione.models import (
    AnimaleSquadriglia,
    Incarico,
    RuoloIncarico,
    Squadriglia,
    TipoUnita,
    Unita,
)
from apps.permessi import policy
from tests.conftest import INIZIO_ANNO, crea_capo, crea_persona

pytestmark = pytest.mark.django_db

ELENCO = "/api/v1/animali"
PULITO = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 9 9"><circle r="5"/></svg>'


@pytest.fixture(autouse=True)
def catalogo():
    animali.carica_catalogo()


@pytest.fixture(autouse=True)
def cartella_media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    yield
    shutil.rmtree(tmp_path, ignore_errors=True)


def _client(chi) -> Client:
    client = Client()
    client.force_login(chi.utente)
    return client


def _post(chi, percorso, dati):
    return _client(chi).post(percorso, json.dumps(dati), content_type="application/json")


def _put(chi, percorso, dati):
    return _client(chi).put(percorso, json.dumps(dati), content_type="application/json")


def _animale(nome="Pantera") -> AnimaleSquadriglia:
    return AnimaleSquadriglia.objects.get(nome=nome)


def _png(formato="PNG") -> bytes:
    uscita = io.BytesIO()
    Image.new("RGB", (900, 450), "red").save(uscita, formato)
    return uscita.getvalue()


def _carica(chi, animale, nome, contenuto):
    return _client(chi).post(
        f"{ELENCO}/{animale.pk}/immagine", {"file": SimpleUploadedFile(nome, contenuto)}
    )


def _capo_altra_unita(gruppo):
    capo = crea_capo("Dino", "Clan", "dino@example.invalid")
    clan = Unita.objects.create(gruppo=gruppo, nome="Clan", tipo=TipoUnita.CLAN_FUOCO)
    Incarico.objects.create(
        persona=capo, ruolo=RuoloIncarico.STAFF, unita=clan, data_inizio=INIZIO_ANNO
    )
    return capo


def _rover(gruppo):
    rover = crea_persona("Rino", "Rover", "rino@example.invalid")
    clan = Unita.objects.create(gruppo=gruppo, nome="Clan 2", tipo=TipoUnita.CLAN_FUOCO)
    Appartenenza.objects.create(
        persona=rover, unita=clan, ruolo=RuoloAppartenenza.RAGAZZO, data_inizio=INIZIO_ANNO
    )
    return rover


# --- Catalog --------------------------------------------------------------------------------


def test_il_catalogo_e_completo():
    assert AnimaleSquadriglia.objects.count() == 93
    assert AnimaleSquadriglia.objects.filter(tipo="NAUTICO").count() == 12
    pantera = _animale()
    assert pantera.plurale == "Pantere"
    assert pantera.simbolo == "pantera"
    assert animali.percorso_immagine(pantera) == "/animali/pantera.svg"


def test_ogni_colore_ha_il_suo_codice():
    for animale in AnimaleSquadriglia.objects.all():
        animale.full_clean()
        for colore in animali.colori_di(animale):
            assert colore["codice"].startswith("#")


def test_caricarlo_due_volte_non_cambia_nulla():
    pantera = _animale()
    pantera.plurale = "Pantere nere"
    pantera.save()
    animali.carica_catalogo()
    assert AnimaleSquadriglia.objects.count() == 93
    assert _animale().plurale == "Pantere nere"


def test_la_migrazione_collega_le_squadriglie(reparto):
    """DEC-351: singular or plural, whatever the case; the others stay as they are."""
    from importlib import import_module

    from django.apps import apps

    AnimaleSquadriglia.objects.all().delete()
    plurale = Squadriglia.objects.create(unita=reparto, nome="pantere", sesso="F")
    singolare = Squadriglia.objects.create(unita=reparto, nome="Volpe", sesso="M")
    altra = Squadriglia.objects.create(unita=reparto, nome="Stelle", sesso="F")
    migrazione = import_module("apps.organizzazione.migrations.0023_catalogo_animali")
    migrazione.carica_e_collega(apps, None)
    for s in (plurale, singolare, altra):
        s.refresh_from_db()
    assert (plurale.animale.nome, plurale.nome) == ("Pantera", "Pantere")
    assert (singolare.animale.nome, singolare.nome) == ("Volpe", "Volpi")
    assert (altra.animale, altra.nome) == (None, "Stelle")


# --- Who reads and who changes (DEC-350) ----------------------------------------------------


def test_chi_legge(gruppo, capo, capogruppo, csq, ragazza, genitore, estraneo):
    for chi in (capo, capogruppo, csq, ragazza):
        assert policy.puo_vedere_animali(chi.utente)
        assert _client(chi).get(ELENCO).status_code == 200
    for chi in (genitore, estraneo, _capo_altra_unita(gruppo), _rover(gruppo)):
        assert not policy.puo_vedere_animali(chi.utente)
        assert _client(chi).get(ELENCO).status_code == 403


def test_chi_modifica(gruppo, capo, capogruppo, csq, ragazza, genitore, estraneo):
    for chi in (capo, capogruppo):
        assert policy.puo_modificare_animali(chi.utente)
    nuovo = {"nome": "Drago", "plurale": "Draghi"}
    for chi in (csq, ragazza, genitore, estraneo, _capo_altra_unita(gruppo)):
        assert not policy.puo_modificare_animali(chi.utente)
        assert _post(chi, ELENCO, nuovo).status_code == 403
        assert _put(chi, f"{ELENCO}/{_animale().pk}", nuovo).status_code == 403
        assert _client(chi).delete(f"{ELENCO}/{_animale().pk}").status_code == 403
        assert _carica(chi, _animale(), "a.png", _png()).status_code == 403
    assert _post(capo, ELENCO, nuovo).status_code == 201
    assert (
        _post(capogruppo, ELENCO, nuovo | {"nome": "Grifone", "plurale": "Grifoni"}).status_code
        == 201
    )


def test_lo_staff_di_un_altro_reparto_modifica(gruppo, coca, reparto):
    """One list for the group: any reparto's staff (DEC-350)."""
    capo = crea_capo("Dino", "Collegato", "dino@example.invalid")
    altro = Unita.objects.create(gruppo=gruppo, nome="Altro", tipo=TipoUnita.REPARTO)
    Incarico.objects.create(
        persona=capo, ruolo=RuoloIncarico.STAFF, unita=altro, data_inizio=INIZIO_ANNO
    )
    assert policy.puo_modificare_animali(capo.utente)


def test_chi_non_modifica_non_vede_i_disattivati(capo, ragazza):
    spento = _animale()
    spento.attivo = False
    spento.save()
    assert spento.pk in {a["id"] for a in _client(capo).get(ELENCO).json()["animali"]}
    dati = _client(ragazza).get(ELENCO).json()
    assert spento.pk not in {a["id"] for a in dati["animali"]}
    assert dati["puo_modificare"] is False


def test_cosa_mostra_l_elenco(capo):
    dati = _client(capo).get(ELENCO).json()
    voce = next(a for a in dati["animali"] if a["nome"] == "Airone")
    assert voce["plurale"] == "Aironi"
    assert voce["tipo_nome"] == "Generale"
    assert voce["colori"][0]["nome"] == "Verde"
    assert voce["colori"][0]["codice"].startswith("#")
    assert voce["colori"][0]["significato"]
    assert voce["richiamo"]
    assert voce["immagine"] == "/animali/airone.svg"
    # Not for the people: the English name and the notes on the sources.
    assert "nome_inglese" not in voce and "nota" not in voce
    assert "Verde" in dati["colori"]


def test_colore_sconosciuto_rifiutato(capo):
    dati = {"nome": "Drago", "plurale": "Draghi", "colore_1": "Fucsia <b>"}
    risposta = _post(capo, ELENCO, dati)
    assert risposta.status_code == 400
    assert "colori proposti" in risposta.json()["detail"]


def test_nome_e_plurale_unici(capo):
    assert _post(capo, ELENCO, {"nome": "Pantera", "plurale": "Altre"}).status_code == 400
    assert _post(capo, ELENCO, {"nome": "Altra", "plurale": "Pantere"}).status_code == 400


# --- Patrols (DEC-351, DEC-352) -------------------------------------------------------------


def _nuova(chi, reparto, animale, sesso="F"):
    return _post(
        chi, f"/api/v1/unita/{reparto.pk}/squadriglie", {"animale_id": animale.pk, "sesso": sesso}
    )


def test_il_nome_e_il_plurale_dell_animale(reparto, capo):
    risposta = _nuova(capo, reparto, _animale())
    assert risposta.status_code == 201
    assert risposta.json()["nome"] == "Pantere"
    assert risposta.json()["animale"]["immagine"] == "/animali/pantera.svg"
    squadriglia = Squadriglia.objects.get(pk=risposta.json()["id"])
    assert squadriglia.animale == _animale()


def test_senza_animale_non_si_crea(reparto, capo):
    risposta = _post(capo, f"/api/v1/unita/{reparto.pk}/squadriglie", {"sesso": "F"})
    assert risposta.status_code == 400
    assert "Scegli l'animale" in risposta.json()["detail"]
    # A name written by hand counts for nothing.
    risposta = _post(capo, f"/api/v1/unita/{reparto.pk}/squadriglie", {"nome": "X", "sesso": "F"})
    assert risposta.status_code == 400


def test_disattivato_non_si_sceglie(reparto, capo):
    spento = _animale()
    spento.attivo = False
    spento.save()
    assert _nuova(capo, reparto, spento).status_code == 400


def test_lo_stesso_animale_due_volte_nel_reparto(gruppo, reparto, capo):
    assert _nuova(capo, reparto, _animale()).status_code == 201
    risposta = _nuova(capo, reparto, _animale())
    assert risposta.status_code == 400
    assert "c'è già la squadriglia Pantere" in risposta.json()["detail"]


def test_l_animale_di_un_archiviata_si_riusa(reparto, capo):
    # DEC-403: a new patrol, not the archived one back.
    creata = _nuova(capo, reparto, _animale()).json()
    archiviata = _post(capo, f"/api/v1/squadriglie/{creata['id']}/archivia", {})
    assert archiviata.json()["attiva"] is False
    nuova = _nuova(capo, reparto, _animale())
    assert nuova.status_code == 201
    assert nuova.json()["id"] != creata["id"]


def test_due_reparti_scelgono_lo_stesso_animale(gruppo, reparto, capogruppo):
    altro = Unita.objects.create(
        gruppo=gruppo, nome="Altro", tipo=TipoUnita.REPARTO, composizione=reparto.composizione
    )
    assert _nuova(capogruppo, reparto, _animale()).status_code == 201
    assert _nuova(capogruppo, altro, _animale()).status_code == 201


def test_una_vecchia_sceglie_l_animale(reparto, capo):
    vecchia = Squadriglia.objects.create(unita=reparto, nome="Stelle", sesso="F")
    avvisi = _client(capo).get(f"/api/v1/unita/{reparto.pk}").json()["avvisi"]
    assert any("Stelle non ha ancora un animale" in a for a in avvisi)
    dati = {"animale_id": _animale().pk, "sesso": "F"}
    risposta = _put(capo, f"/api/v1/squadriglie/{vecchia.pk}", dati)
    assert risposta.json()["nome"] == "Pantere"
    avvisi = _client(capo).get(f"/api/v1/unita/{reparto.pk}").json()["avvisi"]
    assert not any("non ha ancora un animale" in a for a in avvisi)


def test_una_vecchia_si_archivia_senza_animale(reparto, capo):
    vecchia = Squadriglia.objects.create(unita=reparto, nome="Stelle", sesso="F")
    risposta = _post(capo, f"/api/v1/squadriglie/{vecchia.pk}/archivia", {})
    assert risposta.status_code == 200
    assert risposta.json()["nome"] == "Stelle"


def test_il_plurale_cambia_il_nome_ovunque(gruppo, reparto, capo):
    altro = Unita.objects.create(gruppo=gruppo, nome="Altro", tipo=TipoUnita.REPARTO)
    pantera = _animale()
    prime = [
        Squadriglia.objects.create(unita=u, nome=pantera.plurale, animale=pantera, sesso="F")
        for u in (reparto, altro)
    ]
    dati = {"nome": "Pantera", "plurale": "Pantere Nere", "colore_1": "Nero"}
    assert _put(capo, f"{ELENCO}/{pantera.pk}", dati).status_code == 200
    for squadriglia in prime:
        squadriglia.refresh_from_db()
        assert squadriglia.nome == "Pantere Nere"


def test_il_plurale_non_si_scontra_con_una_vecchia(reparto, capo):
    pantera = _animale()
    Squadriglia.objects.create(unita=reparto, nome="Pantere", animale=pantera, sesso="F")
    Squadriglia.objects.create(unita=reparto, nome="Stelle", sesso="F")
    risposta = _put(capo, f"{ELENCO}/{pantera.pk}", {"nome": "Pantera", "plurale": "Stelle"})
    assert risposta.status_code == 400
    assert "c'è già una squadriglia Stelle" in risposta.json()["detail"]
    assert _animale().plurale == "Pantere"


def test_in_uso_non_si_cancella_ma_si_disattiva(reparto, capo):
    pantera = _animale()
    squadriglia = Squadriglia.objects.create(
        unita=reparto, nome="Pantere", animale=pantera, sesso="F", attiva=False
    )
    assert _client(capo).delete(f"{ELENCO}/{pantera.pk}").status_code == 400
    dati = {"nome": "Pantera", "plurale": "Pantere", "attivo": False}
    assert _put(capo, f"{ELENCO}/{pantera.pk}", dati).json()["usato"] is True
    squadriglia.refresh_from_db()
    assert squadriglia.animale == _animale()


def test_mai_usato_si_cancella(capo):
    pantera = _animale()
    assert _client(capo).delete(f"{ELENCO}/{pantera.pk}").status_code == 204
    assert not AnimaleSquadriglia.objects.filter(pk=pantera.pk).exists()


# --- Who sees the image (DEC-353) -----------------------------------------------------------


def test_l_immagine_va_con_il_nome(reparto, squadriglia, ragazza):
    squadriglia.animale = _animale()
    squadriglia.save()
    [mia] = _client(ragazza).get("/api/v1/mia-squadriglia").json()
    assert mia["animale"]["immagine"] == "/animali/pantera.svg"
    assert mia["animale"]["colori"]


def test_al_genitore_arriva_l_immagine(squadriglia, ragazza, genitore):
    squadriglia.animale = _animale()
    squadriglia.save()
    risposta = _client(genitore).get(f"/api/v1/persone/{ragazza.pk}/incarichi-squadriglia")
    assert risposta.status_code == 200
    assert risposta.json()["animale"]["nome"] == "Pantera"


def test_negli_eventi_di_squadriglia(squadriglia, capo):
    from datetime import timedelta

    from django.utils import timezone

    from apps.eventi.models import Evento, Livello, TipoEvento

    squadriglia.animale = _animale()
    squadriglia.save()
    inizio = timezone.now() + timedelta(days=3)
    evento = Evento.objects.create(
        titolo="Uscita",
        tipo=TipoEvento.USCITA,
        livello=Livello.SQUADRIGLIA,
        squadriglia=squadriglia,
        inizio=inizio,
        fine=inizio + timedelta(hours=2),
    )
    risposta = _client(capo).get(f"/api/v1/eventi/{evento.pk}")
    assert risposta.status_code == 200
    assert risposta.json()["animale"]["immagine"] == "/animali/pantera.svg"


def test_offline_solo_quelli_in_uso(gruppo, reparto, genitore, estraneo):
    """DEC-353: for anyone with an account, no personal data, only the patrols' animals."""
    pantera, volpe, cane = _animale(), _animale("Volpe"), _animale("Cane")
    Squadriglia.objects.create(unita=reparto, nome="Pantere", animale=pantera, sesso="F")
    Squadriglia.objects.create(unita=reparto, nome="Volpi", animale=volpe, sesso="M", attiva=False)
    chiuso = Unita.objects.create(
        gruppo=gruppo, nome="Chiuso", tipo=TipoUnita.REPARTO, attiva=False
    )
    Squadriglia.objects.create(unita=chiuso, nome="Cani", animale=cane, sesso="M")
    for chi in (genitore, estraneo):
        assert _client(chi).get(f"{ELENCO}/in-uso").json() == ["/animali/pantera.svg"]
    assert Client().get(f"{ELENCO}/in-uso").status_code == 401


# --- Uploaded images (DEC-354) --------------------------------------------------------------


CATTIVI = {
    "script": b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script><circle r="5"/></svg>',
    "handler": b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"><circle r="5" onclick="alert(2)"/></svg>',
    "link": b'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"><a xlink:href="javascript:alert(1)"><circle r="5"/></a></svg>',
}
RIFIUTATI = {
    "foreign": b'<svg xmlns="http://www.w3.org/2000/svg"><foreignObject><body xmlns="http://www.w3.org/1999/xhtml"><img src=x onerror=alert(1)></body></foreignObject></svg>',
    "use_esterno": b'<svg xmlns="http://www.w3.org/2000/svg"><use href="https://evil.example/x.svg#a"/></svg>',
    "image_esterna": b'<svg xmlns="http://www.w3.org/2000/svg"><image href="https://evil.example/a.png"/></svg>',
    "style_esterno": b'<svg xmlns="http://www.w3.org/2000/svg"><circle r="5" style="fill:url(https://evil.example/z)"/></svg>',
    "animazione": b'<svg xmlns="http://www.w3.org/2000/svg"><a><animate attributeName="href" to="javascript:alert(1)"/><circle r="5"/></a></svg>',
    "html": b"<html><body><script>alert(1)</script></body></html>",
    "testo": b"non e xml",
}


@pytest.mark.parametrize("contenuto", CATTIVI.values(), ids=CATTIVI.keys())
def test_svg_cattivi_ripuliti(contenuto):
    pulito = animali.pulisci_svg(contenuto).lower()
    for parola in (b"script", b"onload", b"onclick", b"alert"):
        assert parola not in pulito
    assert b"circle" in pulito


@pytest.mark.parametrize("contenuto", RIFIUTATI.values(), ids=RIFIUTATI.keys())
def test_svg_cattivi_rifiutati(contenuto):
    with pytest.raises(ValidationError):
        animali.pulisci_svg(contenuto)


def test_i_riferimenti_interni_restano():
    svg = (
        b'<svg xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="g"/></defs>'
        b'<circle r="5" fill="url(#g)"/></svg>'
    )
    assert b"url(#g)" in animali.pulisci_svg(svg)


def test_svg_caricato_e_servito_senza_rischi(capo, ragazza):
    animale = _animale()
    risposta = _carica(capo, animale, "pantera.SVG", CATTIVI["script"])
    assert risposta.status_code == 200
    assert risposta.json()["simbolo"] == ""
    percorso = risposta.json()["immagine"]
    assert percorso.startswith("/api/v1/animali/immagini/") and percorso.endswith(".svg")
    assert "pantera" not in percorso.lower()

    letto = _client(ragazza).get(percorso)
    assert letto.status_code == 200
    assert letto["Content-Type"] == "image/svg+xml"
    assert "sandbox" in letto["Content-Security-Policy"]
    assert "default-src 'none'" in letto["Content-Security-Policy"]
    assert letto["X-Content-Type-Options"] == "nosniff"
    assert letto["Content-Disposition"] == "inline"
    assert b"script" not in b"".join(letto.streaming_content)


@pytest.mark.parametrize("formato", ["PNG", "JPEG"])
def test_png_e_jpeg_ricodificati(capo, formato):
    risposta = _carica(capo, _animale(), f"a.{formato.lower()}", _png(formato))
    assert risposta.status_code == 200
    letto = _client(capo).get(risposta.json()["immagine"])
    assert letto["Content-Type"] == "image/png"
    immagine = Image.open(io.BytesIO(b"".join(letto.streaming_content)))
    assert immagine.format == "PNG"
    assert max(immagine.size) == animali.LATO_MASSIMO


def test_html_travestito_rifiutato(capo):
    finto = b"<html><script>alert(1)</script></html>"
    for nome in ("a.png", "a.svg", "a.html"):
        risposta = _carica(capo, _animale(), nome, finto)
        assert risposta.status_code == 400
    assert animali.percorso_immagine(_animale()) == "/animali/pantera.svg"


def test_troppo_grande(capo):
    troppo = PULITO + b" " * animali.MASSIMO_SVG
    risposta = _carica(capo, _animale(), "a.svg", troppo)
    assert risposta.status_code == 400
    assert "1 MB" in risposta.json()["detail"]


def test_serve_un_account(capo):
    percorso = _carica(capo, _animale(), "a.svg", PULITO).json()["immagine"]
    assert Client().get(percorso).status_code == 401


def test_nome_inventato_o_con_percorso(capo):
    for nome in ("nessuno.svg", "..%2f..%2fsettings.py", "x.html"):
        assert _client(capo).get(f"{ELENCO}/immagini/{nome}").status_code == 404


def test_la_vecchia_immagine_si_cancella(capo, settings, django_capture_on_commit_callbacks):
    animale = _animale()
    with django_capture_on_commit_callbacks(execute=True):
        _carica(capo, animale, "a.svg", PULITO)
    animale.refresh_from_db()
    prima = animale.immagine.name
    with django_capture_on_commit_callbacks(execute=True):
        _carica(capo, animale, "b.svg", PULITO)
    animale.refresh_from_db()
    assert animale.immagine.name != prima
    assert not animale.immagine.storage.exists(prima)
    assert animale.immagine.storage.exists(animale.immagine.name)
