"""Phone numbers into the phone's contacts: a vCard file for the capi and the CSQ,
with only the numbers they already see."""

import pytest
from django.test import Client

from apps.anagrafica.servizi import internazionale
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
    # Name and numbers only: no email, no birth date.
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


def test_bloccato_mentre_si_usa_l_app_come_un_altro():
    from apps.impersonazione.middleware import bloccata

    assert bloccata("GET", "/api/v1/rubrica")
