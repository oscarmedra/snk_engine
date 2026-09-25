"""Rassemble les formes que les règles proposent mais que personne n'a validées.

Chaque ligne est un couple temps × pronom manquant. Une fois relue, la forme est
ajoutée aux personnes du temps dans data/grammaire/soninke.yaml, ce qui débloque
ce temps pour les 182 verbes d'un coup.

    uv run python scripts/build_propositions.py
"""

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

from snk_engine.conjugation import ConjugationError, default_engine
from snk_engine.french import conjugate_fr
from snk_engine.sentences import french_verbs

ROOT = Path(__file__).resolve().parents[1]
# l'impératif n'a pas de sujet : ses « manques » n'ont pas de sens
SANS_SUJET = {"imperatif", "imperatif_objet", "imperatif_negatif", "imperatif_pluriel"}
TEMOINS = ["dagaer", "yigeyer"]        # deux verbes, pour voir la forme sous deux angles
HEADERS = ["ID", "Temps", "Pronom", "Phrase proposée", "Français", "Correct ?", "Correction", "Remarque"]
HELP = [
    "Ces phrases ne viennent pas de toi : ce sont les formes que les règles prévoient",
    "pour des personnes que tu n'as jamais données à ce temps.",
    "",
    "« oui » si la phrase se dit, « non » sinon — et dans ce cas la bonne forme",
    "dans « Correction ».",
    "",
    "Chaque ligne validée débloque ce temps pour les 182 verbes du moteur.",
]


def main() -> None:
    engine = default_engine()
    fr_verbs = french_verbs(engine)
    rows = []
    for tense, definition in engine.tenses.items():
        if tense in SANS_SUJET:
            continue
        obj = "maro" if definition.object else None
        for pronoun in engine.pronouns:
            try:
                engine.conjugate("dagaer", pronoun, tense, obj)
                continue                      # déjà confirmé
            except ConjugationError:
                pass
            for verb in TEMOINS:
                try:
                    snk = engine.conjugate(verb, pronoun, tense, obj, strict=False)
                except ConjugationError:
                    continue
                person = engine.pronouns[pronoun][0].person
                try:
                    fr = conjugate_fr(fr_verbs[verb], person, tense, "du riz" if obj else None)
                except Exception:
                    fr = ""
                rows.append((definition.label, pronoun, snk, fr))
                break

    wb = Workbook()
    ws = wb.active
    ws.title = "Propositions"
    ws.append(HEADERS)
    fill = PatternFill("solid", fgColor="FFF2CC")
    for i, (tense, pronoun, snk, fr) in enumerate(rows, start=1):
        ws.append([f"p-{i:03d}", tense, pronoun, snk, fr, None, None, None])
        for col in (6, 7, 8):
            ws.cell(ws.max_row, col).fill = fill
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F4E78")
        cell.alignment = Alignment(horizontal="center", wrap_text=True)
    for letter, width in zip("ABCDEFGH", (8, 26, 10, 34, 30, 10, 26, 26)):
        ws.column_dimensions[letter].width = width
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "B2"

    dv = DataValidation(type="list", formula1='"oui,non"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f"F2:F{len(rows) + 1}")

    help_ws = wb.create_sheet("Mode d'emploi")
    help_ws.column_dimensions["A"].width = 95
    for line in HELP:
        help_ws.append([line])

    out = ROOT / "data" / "questionnaires" / "propositions_01.xlsx"
    wb.save(out)
    print(f"{out} : {len(rows)} propositions sur {len({r[0] for r in rows})} temps")


if __name__ == "__main__":
    main()
