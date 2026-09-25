from pathlib import Path

import pytest
from openpyxl import load_workbook

from snk_engine.conjugation import default_engine
from snk_engine.verbs_excel import ExcelImportError, export_verbs, read_verbs


def _workbook(tmp_path: Path, extra_rows: list[list] = ()) -> Path:
    xlsx = export_verbs(default_engine(), tmp_path / "v.xlsx")
    wb = load_workbook(xlsx)
    for r in extra_rows:
        wb["Verbes"].append(r)
    wb.save(xlsx)
    return xlsx


def test_export_contains_full_predicates(tmp_path):
    verbs = read_verbs(_workbook(tmp_path), default_engine())
    assert verbs["dagaer"]["forme"] == "daga"
    assert verbs["dagaer"]["conjugaison"]["past"]["formes"] == {
        "nke": "daga", "anke": "n'daga", "ake": "n'daga", "oku": "daga", "xaku": "n'daga", "iku": "n'daga",
        "n": "daga", "an": "daga", "a": "daga", "o": "daga", "xa": "daga", "i": "daga",
    }
    assert verbs["dagaer"]["conjugaison"]["future"]["formes"]["anke"] == "n'yi rini daga"
    imminent = verbs["dagaer"]["conjugaison"]["imminent"]["formes"]
    assert imminent["nke"] == "fayi rini daga" and imminent["ake"] == "m'fayi rini daga"
    assert verbs["rier"]["conjugaison"]["past"]["formes"]["xaku"] == "l'ri"


def test_submitted_row_is_read_with_notes(tmp_path):
    blanks = [None] * (len(default_engine().pronouns) - 1)
    row = ["testverbe", "tester", "tst", "passé / accompli", "f1", *blanks, "note"]
    verbs = read_verbs(_workbook(tmp_path, [row]), default_engine())
    assert verbs["testverbe"]["conjugaison"]["past"] == {"formes": {"nke": "f1"}, "remarques": "note"}


@pytest.mark.parametrize(
    "row, message",
    [
        (["dagaer", "partir", "daga", "passé / accompli", "x", None, None, None, None, None], "deux fois"),
        (["dagaer", "aller", None, None, None, None, None, None, None, None], "incohérent"),
        (["xverbe", "x", None, "imparfait", "x", None, None, None, None, None], "temps inconnu"),
        (["xverbe", "x", None, None, "x", None, None, None, None, None], "sans temps"),
        (["xverbe", None, None, None, None, None, None, None, None, None], "Sens"),
    ],
)
def test_invalid_rows_are_reported(tmp_path, row, message):
    with pytest.raises(ExcelImportError, match=message):
        read_verbs(_workbook(tmp_path, [row]), default_engine())
