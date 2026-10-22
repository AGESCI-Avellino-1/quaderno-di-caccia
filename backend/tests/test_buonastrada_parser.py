from datetime import date

import pytest

from apps.importazione.buonastrada import (
    FormatoNonValido,
    Gravita,
    codice_cognome,
    codice_nome,
    interpreta_tipo_unita,
    leggi_genitori,
    leggi_ricerca_soci,
    separa_nome_completo,
)
from apps.organizzazione.models import Composizione, TipoUnita
from tests.export_sintetico import GENITORI_ROSSI, costruisci_csv, riga, righe_standard

OGGI = date(2026, 10, 21)


def test_trappole_del_formato_gestite():
    risultato = leggi_ricerca_soci(costruisci_csv(righe_standard()), oggi=OGGI)
    assert len(risultato.intestazioni) == 81
    assert [r.codice_socio for r in risultato.righe] == [
        "9000001",
        "9000002",
        "9000003",
        "9000004",
        "9000005",
    ]
    giulia = risultato.righe[0]
    # ="..." unwrapped, dates parsed although not wrapped, trailing comma ignored.
    assert giulia.nome == "Giulia"
    assert giulia.data_nascita == date(2013, 5, 10)
    assert giulia.anno_scout == 2026
    assert giulia.consenso_foto is True
    assert giulia.consenso_commerciale is False


def test_colonne_mancanti_rifiutano_il_file():
    with pytest.raises(FormatoNonValido):
        leggi_ricerca_soci(b'sep=,\nNOME,COGNOME\n="A",="B",\n')


def test_codice_socio_mancante_e_errore():
    righe = [riga(**{"CODICE SOCIO": "", "NOME": "Senza", "COGNOME": "Codice"})]
    risultato = leggi_ricerca_soci(costruisci_csv(righe), oggi=OGGI)
    assert risultato.righe == []
    assert risultato.errori[0].gravita == Gravita.ERRORE


def test_date_nel_futuro_segnalate():
    risultato = leggi_ricerca_soci(
        costruisci_csv(
            [riga(**{"CODICE SOCIO": "1", "NOME": "A", "COGNOME": "B", "INGRESSO COCA": "2099"})]
        ),
        oggi=OGGI,
    )
    assert any("INGRESSO COCA nel futuro" in a.messaggio for a in risultato.avvisi)


def test_avvisi_degli_ex_soci_non_mostrati():
    risultato = leggi_ricerca_soci(costruisci_csv(righe_standard()), oggi=OGGI)
    assert not any(a.codice_socio == "9000005" for a in risultato.avvisi)


@pytest.mark.parametrize(
    ("testo", "atteso"),
    [
        ("REPARTO FEMMINILE", (TipoUnita.REPARTO, Composizione.FEMMINILE)),
        ("REPARTO MISTO", (TipoUnita.REPARTO, Composizione.MISTA)),
        ("BRANCO/CERCHIO MISTO", (TipoUnita.BRANCO_CERCHIO, Composizione.MISTA)),
        ("CLAN/FUOCO", (TipoUnita.CLAN_FUOCO, Composizione.MISTA)),
        ("COMUNITA` CAPI", (TipoUnita.COMUNITA_CAPI, Composizione.MISTA)),
        ("FUOCO", (TipoUnita.CLAN_FUOCO, Composizione.FEMMINILE)),
        ("SCONOSCIUTO", None),
    ],
)
def test_tipo_unita(testo, atteso):
    assert interpreta_tipo_unita(testo) == atteso


def test_codici_del_codice_fiscale():
    assert codice_cognome("Rossi") == "RSS"
    assert codice_cognome("De Luca") == "DLC"
    assert codice_nome("Mario") == "MRA"
    assert codice_nome("Anna Maria") == "NMR"  # 4+ consonants: 1st, 3rd, 4th
    assert codice_cognome("Fò") == "FOX"


def test_separa_nome_composto_grazie_al_codice_fiscale():
    assert separa_nome_completo("De Luca Anna Maria", "DLCNMR82C41A509Z") == (
        "De Luca",
        "Anna Maria",
        True,
    )


def test_separa_nome_senza_conferma_segnala():
    cognome, nome, verificato = separa_nome_completo("Rossi Mario", "TEST000000000001")
    assert (cognome, nome, verificato) == ("Rossi", "Mario", False)


def test_genitori_letti_dalla_stringa_buonastrada():
    genitori, illeggibili = leggi_genitori(GENITORI_ROSSI)
    assert illeggibili == []
    assert [(g.cognome, g.nome) for g in genitori] == [
        ("Rossi", "Mario"),
        ("De Luca", "Anna Maria"),
    ]
    assert genitori[1].codice_fiscale == "DLCNMR82C41A509Z"
    assert genitori[1].data_nascita == date(1982, 3, 1)
    assert genitori[0].cellulare == "3330000001"


def test_genitore_illeggibile_segnalato():
    _, illeggibili = leggi_genitori("testo libero senza formato")
    assert illeggibili == ["testo libero senza formato"]
