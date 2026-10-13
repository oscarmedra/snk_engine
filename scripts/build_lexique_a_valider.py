"""Rassemble les mots prêts à entrer dans le moteur, pour une relecture d'un seul tenant.

Deux gisements :
  - data/references/mots.yaml : les mots donnés au fil des textes, glosés mais jamais
    promus. Ils servent à `comprendre`, pas à générer.
  - l'alignement bilingue (scripts/aligner_lexique.py) : les mots du corpus que
    personne n'a encore glosés, avec une traduction devinée.

La colonne « catégorie » est une *proposition* déduite de la glose française, jamais
une décision : le moteur range un objet et un complément à des endroits différents,
et se tromper de case produirait des phrases fausses.

    uv run python scripts/build_lexique_a_valider.py --excel data/sources/lexique_a_valider.xlsx
"""

import argparse
import json
import re
from collections import Counter
from pathlib import Path

import yaml

from aligner_lexique import MOT, aligner, charger_paires
from snk_engine.understand import _key, _simple_meaning, load_lexicon

ROOT = Path(__file__).resolve().parents[1]

MOMENTS = ("hier", "demain", "aujourd", "matin", "soir", "nuit", "jour", "semaine",
           "année", "mois", "tôt", "tard", "moment", "heure", "midi", "minuit")
GRAMMAIRE = ("introduit", "marque", "forme ", "insiste", "pluriel", "suffixe", "particule",
             "parce que", "ensuite", "jusqu", "encore", "quand", "où", "après", "devant",
             "dans", "avec", "sans", "pour", "mais", "ensemble", "aussi")


ADJECTIFS = ("difficile", "facile", "chaud", "froid", "bon", "mauvais", "grand", "petit",
             "beau", "fatigué", "propre", "sale", "cher", "long", "court", "lourd", "léger")


def categorie_proposee(fr: str) -> str:
    """Déduite du sens français ; une proposition, à confirmer par le locuteur.

    Vos gloses sont des noms nus (« riz », « marché ») plutôt que des groupes avec
    article, d'où l'ordre : on écarte d'abord la grammaire et les moments, et ce qui
    reste de court est tenu pour un nom — le cas de loin le plus fréquent.
    """
    bas = fr.lower().strip()
    # une note de grammaire plutôt qu'un mot : « n, an, a, o, xa, i + nom »
    if "+" in bas or bas.count(",") >= 2:
        return "?"
    if bas.startswith(("au ", "à la ", "aux ", "chez ", "dans ")):
        return "lieu"
    if any(m in bas for m in MOMENTS):
        return "moment"
    if any(g in bas for g in GRAMMAIRE):
        return "grammaire"
    if bas in ADJECTIFS:
        return "adjectif"
    if bas.startswith(("le ", "la ", "les ", "l'", "un ", "une ", "du ", "de la ", "des ")):
        return "nom"
    return "nom" if len(bas.split()) <= 2 else "?"


def plat(noeud):
    if isinstance(noeud, dict):
        return [noeud] if "snk" in noeud else [x for v in noeud.values() for x in plat(v)]
    return [x for i in noeud for x in plat(i)] if isinstance(noeud, list) else []


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--excel", type=Path, required=True)
    args = parser.parse_args()

    data = ROOT / "data"
    objets = yaml.safe_load((data / "grammaire" / "objets.yaml").read_text(encoding="utf-8")) or {}
    deja = {_key(i["snk"]) for s in ("objets", "complements") for i in (objets.get(s) or []) if i.get("snk")}

    paires = charger_paires()
    occurrences = Counter(_key(m) for snk, _ in paires for m in MOT.findall(snk))
    exemples: dict[str, tuple[str, str]] = {}
    for snk, fr in paires:
        for m in MOT.findall(snk):
            exemples.setdefault(_key(m), (snk, fr))

    # ce que l'alignement bilingue dit du même mot : un contrôle croisé de la glose
    aligne = {p["snk"]: (p["propose"], p["score"]) for p in aligner(paires, load_lexicon())}

    lignes = []
    mots = yaml.safe_load((data / "references" / "mots.yaml").read_text(encoding="utf-8")) or {}
    for section, contenu in mots.items():
        for item in plat(contenu):
            if not _simple_meaning(item.get("snk"), item.get("fr")):
                continue
            cle = _key(item["snk"])
            if cle in deja:
                continue
            deja.add(cle)
            vu = occurrences.get(cle, 0)
            devine, score = aligne.get(cle, ("", ""))
            lignes.append([item["snk"], item["fr"], categorie_proposee(item["fr"]), section,
                           vu, devine, score, "", "",
                           *exemples.get(cle, ("", ""))])

    # puis les mots que seul l'alignement connaît : aucune glose enregistrée
    for p in aligner(paires, load_lexicon()):
        if p["snk"] in deja:
            continue
        deja.add(p["snk"])
        lignes.append([p["snk"], "", "?", "alignement seul", p["occurrences"],
                       p["propose"], p["score"], "", "", p["exemple_snk"], p["exemple_fr"]])

    # les noms d'abord : ils se valident d'un coup d'œil. La grammaire et les cas
    # douteux ferment la marche, pour ne pas épuiser le relecteur dès la première page.
    ordre = {"nom": 0, "moment": 1, "lieu": 2, "adjectif": 3, "grammaire": 4, "?": 5}
    lignes.sort(key=lambda l: (ordre.get(l[2], 9), -l[4], l[0]))

    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    wb = Workbook()
    ws = wb.active
    ws.title = "lexique à valider"
    ws.append(["mot soninké", "sens enregistré", "catégorie proposée", "venu de", "vu",
               "deviné par alignement", "score", "CORRIGER LE SENS", "CORRIGER LA CATÉGORIE",
               "exemple (soninké)", "exemple (français)"])
    for c in ws[1]:
        c.font = Font(bold=True)
        c.alignment = Alignment(wrap_text=True, vertical="center")
    jaune = PatternFill("solid", fgColor="FFF3CD")
    for ligne in lignes:
        ws.append(ligne)
        for col in ("H", "I"):                      # les deux colonnes à remplir
            ws[f"{col}{ws.max_row}"].fill = jaune
    for col, large in zip("ABCDEFGHIJK", (16, 26, 14, 16, 6, 18, 7, 22, 20, 44, 44)):
        ws.column_dimensions[col].width = large
    for ligne in ws.iter_rows(min_row=2):
        for c in ligne:
            c.alignment = Alignment(vertical="top", wrap_text=True)
    ws.freeze_panes = "A2"
    args.excel.parent.mkdir(parents=True, exist_ok=True)
    wb.save(args.excel)

    cats = Counter(l[2] for l in lignes)
    print(f"{len(lignes)} mots à valider → {args.excel}")
    print("   catégories proposées : " + ", ".join(f"{k} {v}" for k, v in cats.most_common()))
    print(f"   dont {sum(1 for l in lignes if l[5])} recoupés par l'alignement bilingue")


if __name__ == "__main__":
    main()
