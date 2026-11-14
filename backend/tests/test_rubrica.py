"""Phone numbers into the phone's contacts: a vCard file for the capi and the CSQ,
with only the numbers they already see."""

from datetime import date

import pytest
from django.test import Client

from apps.anagrafica.models import Appartenenza, RelazioneTutela, RuoloAppartenenza, TipoTutela
from apps.anagrafica.servizi import internazionale
from apps.impostazioni.models import Impostazioni
from apps.organizzazione.models import Composizione, TipoUnita, Unita
from apps.permessi import policy

pytestmark = pytest.mark.django_db


def _scarica(persona, *scelte):
    client = Client()
    client.force_login(persona.utente)
    return client.get("/api/v1/rubrica", {"persone": ",".join(str(p.pk) for p in scelte)})


def test_numero_internazionale():
    assert internazionale("333 000 0000") == "+393330000000"
    assert internazionale("+41 79 123 45 67") == "+41791234567"
    assert internazionale("0041791234567") == "+41791234567"


def test_chi_usa_la_rubrica(capo, capogruppo, csq, ragazza, genitore, estraneo):
    assert policy.puo_usare_rubrica(capo.utente)
    assert policy.puo_usare_rubrica(capogruppo.utente)
    assert policy.puo_usare_rubrica(csq.utente)
    for persona in (ragazza, genitore, estraneo):
        assert not policy.puo_usare_rubrica(persona.utente)
        assert _scarica(persona, ragazza).status_code == 403


def test_il_capo_scarica_nome_e_numeri(capo, ragazza, genitore):
    genitore.cellulare = "3471111111"
    genitore.telefono_fisso = "0825 123456"
    genitore.save()
    risposta = _scarica(capo, ragazza, genitore)
    assert risposta.status_code == 200
    assert risposta["Content-Type"].startswith("text/vcard")
    assert "attachment" in risposta["Content-Disposition"]
    testo = risposta.content.decode()
    assert testo.count("BEGIN:VCARD") == 2
    assert "FN:Giulia Esploratrice" in testo
    assert "TEL;TYPE=CELL:+393330000000" in testo
    assert "TEL;TYPE=VOICE:+390825123456" in testo
    # No email, no birth date.
    assert "EMAIL" not in testo and "BDAY" not in testo
    assert "giulia@example.invalid" not in testo


def test_il_csq_scarica_solo_la_sua_squadriglia(csq, ragazza, genitore, estraneo):
    genitore.cellulare = "3471111111"
    genitore.save()
    estraneo.cellulare = "3209999999"
    estraneo.save()
    testo = _scarica(csq, ragazza, genitore, estraneo).content.decode()
    assert "FN:Giulia Esploratrice" in testo and "FN:Mario Genitore" in testo
    assert "Estraneo" not in testo and "3209999999" not in testo
    # Someone outside the patrol only: nothing to give.
    assert _scarica(csq, estraneo).status_code == 404


def test_il_csq_vede_il_numero_del_genitore_scelto(csq, ragazza, genitore):
    ragazza.cellulare = ""
    ragazza.telefono_squadriglia_da = genitore
    ragazza.save()
    genitore.cellulare = "3471111111"
    genitore.save()
    testo = _scarica(csq, ragazza).content.decode()
    assert "TEL;TYPE=CELL:+393471111111" in testo
    assert "NOTE:numero di Mario (genitore)" in testo


def _azienda(testo: str, nome: str) -> str:
    scheda = next(s for s in testo.split("END:VCARD") if f"FN:{nome}" in s)
    return next(r for r in scheda.splitlines() if r.startswith("ORG:"))


def test_azienda_con_il_gruppo_e_chi_e_la_persona(capo, capogruppo, reparto, ragazza, genitore):
    reparto.nome = "Aquile"
    reparto.save()
    capo.cellulare = "3201111111"
    capo.save()
    genitore.cellulare = "3471111111"
    genitore.save()
    testo = _scarica(capogruppo, capo, ragazza, genitore).content.decode()
    assert _azienda(testo, "Giulia Esploratrice") == "ORG:AGESCI Prova 1 - Reparto Aquile"
    assert _azienda(testo, "Mario Genitore") == "ORG:AGESCI Prova 1 - Genitore"
    assert _azienda(testo, f"{capo.nome} {capo.cognome}") == "ORG:AGESCI Prova 1 - Capo"


def test_azienda_con_il_nome_del_gruppo_nelle_impostazioni(capo, ragazza):
    impostazioni = Impostazioni.carica()
    impostazioni.nome_gruppo = "Gruppo, di prova"
    impostazioni.save()
    testo = _scarica(capo, ragazza).content.decode()
    assert "ORG:Gruppo\\, di prova - " in testo


def test_azienda_con_il_codice_se_l_unita_non_ha_nome(capo, gruppo, ragazza):
    unita = Unita.objects.create(
        gruppo=gruppo,
        nome="",
        tipo=TipoUnita.CLAN_FUOCO,
        composizione=Composizione.MISTA,
        codice_unita="T",
        progressivo=7,
    )
    Appartenenza.objects.filter(persona=ragazza).update(data_fine=date.today())
    Appartenenza.objects.create(
        persona=ragazza,
        unita=unita,
        ruolo=RuoloAppartenenza.RAGAZZO,
        data_inizio=date.today(),
    )
    testo = _scarica(capo, ragazza).content.decode()
    assert _azienda(testo, "Giulia Esploratrice").endswith(" - Clan/Fuoco (T7)")


def test_azienda_il_capo_viene_prima_del_genitore(capo, capogruppo, ragazza):
    capo.cellulare = "3201111111"
    capo.save()
    RelazioneTutela.objects.create(tutore=capo, minore=ragazza, tipo=TipoTutela.GENITORE)
    testo = _scarica(capogruppo, capo).content.decode()
    assert _azienda(testo, f"{capo.nome} {capo.cognome}").endswith(" - Capo")


def test_azienda_socio_senza_unita_attiva(capo, capogruppo, ragazza):
    Appartenenza.objects.filter(persona=ragazza).update(data_fine=date.today())
    testo = _scarica(capogruppo, ragazza).content.decode()
    assert _azienda(testo, "Giulia Esploratrice").endswith(" - Socio")


def test_bloccato_mentre_si_usa_l_app_come_un_altro():
    from apps.impersonazione.middleware import bloccata

    assert bloccata("GET", "/api/v1/rubrica")
