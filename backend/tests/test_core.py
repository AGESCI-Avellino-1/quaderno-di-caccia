from datetime import date

import pytest

from apps.core.anno import AnnoAssociativo, eta_al_riferimento
from apps.core.date_parziali import DataParziale, PrecisioneData


@pytest.mark.parametrize(
    ("giorno", "atteso"),
    [
        (date(2025, 9, 30), 2025),
        (date(2025, 10, 1), 2026),
        (date(2026, 1, 15), 2026),
        (date(2026, 9, 30), 2026),
    ],
)
def test_anno_associativo_cambia_il_primo_ottobre(giorno, atteso):
    assert AnnoAssociativo.da_data(giorno).anno_fine == atteso


def test_anno_associativo_estremi_ed_etichetta():
    anno = AnnoAssociativo(2026)
    assert anno.inizio == date(2025, 10, 1)
    assert anno.fine == date(2026, 9, 30)
    assert anno.etichetta == "2025/26"
    assert anno.contiene(date(2026, 4, 30))
    assert not anno.contiene(date(2026, 10, 1))


@pytest.mark.parametrize(
    ("nascita", "atteso"),
    [
        (date(2014, 4, 30), 12),  # birthday on the reference day counts
        (date(2014, 5, 1), 11),  # one day later does not
        (date(2013, 12, 31), 12),
    ],
)
def test_eta_al_30_aprile(nascita, atteso):
    assert eta_al_riferimento(nascita, AnnoAssociativo(2026)) == atteso


def test_eta_con_data_di_riferimento_personalizzata():
    assert eta_al_riferimento(date(2014, 5, 1), AnnoAssociativo(2026), mese=6, giorno=1) == 12


def test_data_parziale_non_inventa_il_primo_gennaio():
    solo_anno = DataParziale.solo_anno(2019)
    assert solo_anno.precisione == PrecisioneData.ANNO
    assert str(solo_anno) == "2019"
    with pytest.raises(ValueError):
        DataParziale(date(2019, 6, 12), PrecisioneData.ANNO)


def test_data_ignota_senza_valore():
    assert str(DataParziale.ignota()) == "data non documentata"
    with pytest.raises(ValueError):
        DataParziale(date(2020, 1, 1), PrecisioneData.IGNOTA)
