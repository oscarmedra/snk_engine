"""Prépare l'Excel qui complète les verbes de l'inventaire.

Pour chaque verbe, la forme en -ni est PROPOSÉE par la règle (le suffixe reprend
la dernière voyelle : daga → dagana, xiri → xirini). Le locuteur n'a qu'à valider
ou corriger, et à dire si le verbe prend un objet.

    uv run python scripts/build_verbes_a_completer.py [nombre]
"""

import sys
from pathlib import Path

import yaml
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parents[1]
HEADERS = ["Radical", "Sens", "Nom d'action", "Forme en -ni (proposée)",
           "Correct ?", "Correction", "Prend un objet ?", "Remarque"]
HELP = [
    "La colonne « Forme en -ni (proposée) » est calculée par la règle :",
    "le suffixe -n reprend la dernière voyelle du radical (daga → dagana, xiri → xirini).",
    "",
    "Écris « oui » si la forme proposée est juste, « non » sinon — et dans ce cas,",
    "écris la bonne forme dans « Correction ».",
    "",
    "« Prend un objet ? » : oui si l'on peut dire « il X quelque chose »",
    "(manger le riz, écrire une lettre) ; non pour partir, dormir, courir…",
    "",
    "Un verbe validé entre dans le moteur et devient conjugable aux 24 temps.",
]

VOWELS = "aeiou"


def propose_gerund(radical: str) -> str:
    """Règle confirmée : radical + n + dernière voyelle du radical."""
    last = next((c for c in reversed(radical) if c in VOWELS), "i")
    return f"{radical}n{last}" if radical[-1] in VOWELS else f"{radical}ni"


def main(count: int | None = None) -> None:
    data = yaml.safe_load((ROOT / "data" / "references" / "verbes.yaml").read_text(encoding="utf-8"))
    verbs = [v for v in (data.get("liste") or []) if v.get("radical") and v.get("fr")]
    if count:
        verbs = verbs[:count]

    wb = Workbook()
    ws = wb.active
    ws.title = "Verbes"
    ws.append(HEADERS)
    fill = PatternFill("solid", fgColor="FFF2CC")
    for v in verbs:
        ws.append([v["radical"], v["fr"], v.get("nom_action"), propose_gerund(v["radical"]),
                   None, None, None, None])
        for col in (5, 6, 7, 8):
            ws.cell(ws.max_row, col).fill = fill
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F4E78")
        cell.alignment = Alignment(horizontal="center", wrap_text=True)
    for letter, width in zip("ABCDEFGH", (16, 22, 18, 22, 10, 20, 14, 28)):
        ws.column_dimensions[letter].width = width
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "A2"

    for column in ("E", "G"):
        dv = DataValidation(type="list", formula1='"oui,non"', allow_blank=True)
        ws.add_data_validation(dv)
        dv.add(f"{column}2:{column}{len(verbs) + 1}")

    help_ws = wb.create_sheet("Mode d'emploi")
    help_ws.column_dimensions["A"].width = 95
    for line in HELP:
        help_ws.append([line])

    out = ROOT / "data" / "questionnaires" / "verbes_a_completer.xlsx"
    wb.save(out)
    print(f"{out} : {len(verbs)} verbes")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else None)
