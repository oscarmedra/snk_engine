"""Fait entrer dans le moteur les noms du glossaire, avec leurs trois déterminations.

Le locuteur l'a dit : l'article français n'a pas à être deviné, puisque c'est `ke`
qui porte la détermination en soninké, et sa place qui en décide le sens.

    alikaati          un policier
    alikaati ke       le policier
    ke alikaati       ce policier

Il ne manquait donc que le GENRE français — affaire de français, pas de soninké :
scripts/genre_francais.py le donne, par terminaison puis par liste écrite à la main.

N'entrent que les entrées dont le glossaire marque le nombre, « (i, nu) » : c'est
ainsi qu'il signale un nom. Les adjectifs et les gloses trop longues restent dehors.
Les verbes compatibles se limitent à `wori` (voir), la revendication la plus faible :
aucune source ne dit ce qui se mange, s'achète ou se porte.

    uv run python scripts/promouvoir_noms_glossaire.py            # essai à blanc
    uv run python scripts/promouvoir_noms_glossaire.py --ecrire
"""

import re
import sys
from pathlib import Path

import yaml

from comparer_hagg import pivot
from genre_francais import corriger, est_adjectif, genre

ROOT = Path(__file__).resolve().parents[1]
OBJETS = ROOT / "data" / "grammaire" / "objets.yaml"
GLOSSAIRE = ROOT / "data" / "references" / "glossaire.yaml"
GLOSE_NETTE = re.compile(r"^[A-Za-zÀ-ÿ'’\- ]{2,24}$")
VOYELLE = re.compile(r"^[aeiouéèêâîôûh]", re.I)
SOURCE = "glossaire, validé par le locuteur 2026-10-29"


def trois_formes(snk: str, nom: str, g: str) -> list[tuple[str, str]]:
    indefini = "un" if g == "m" else "une"
    defini = f"l'{nom}" if VOYELLE.match(nom) else f"{'le' if g == 'm' else 'la'} {nom}"
    if g == "f":
        demonstratif = f"cette {nom}"
    else:
        demonstratif = f"cet {nom}" if VOYELLE.match(nom) else f"ce {nom}"
    return [(snk, f"{indefini} {nom}"), (f"{snk} ke", defini), (f"ke {snk}", demonstratif)]


def main(ecrire: bool = False) -> None:
    objets = yaml.safe_load(OBJETS.read_text(encoding="utf-8")) or {}
    presents = {pivot(i["snk"]) for s in ("objets", "complements")
                for i in (objets.get(s) or []) if i.get("snk")}
    # un jour ou un mois est déjà complément : « je vois un vendredi » n'a pas de sens
    sens_pris = {str(i.get("fr", "")).lower().removeprefix("en ")
                 for i in (objets.get("complements") or [])}

    ajouts, ecartes = [], {"pas un nom": 0, "glose peu nette": 0, "genre inconnu": 0,
                           "déjà connu": 0}
    for e in yaml.safe_load(GLOSSAIRE.read_text(encoding="utf-8"))["entrees"]:
        snk, fr = e["snk"].strip().lower(), e["fr"].strip()
        if not e.get("nombre"):
            ecartes["pas un nom"] += 1
            continue
        if not GLOSE_NETTE.match(fr) or len(fr.split()) > 2:
            ecartes["glose peu nette"] += 1
            continue
        if est_adjectif(fr):
            ecartes["pas un nom"] += 1
            continue
        if pivot(snk) in presents or fr.lower() in sens_pris:
            ecartes["déjà connu"] += 1
            continue
        g = genre(fr)
        if not g:
            ecartes["genre inconnu"] += 1
            continue
        presents.add(pivot(snk))
        for forme, sens in trois_formes(snk, corriger(fr), g):
            ajouts.append({"snk": forme, "fr": sens})

    print(f"{len(ajouts)} formes à ajouter ({len(ajouts) // 3} noms × 3 déterminations)")
    print("   écartés : " + ", ".join(f"{k} ({v})" for k, v in ecartes.items()) + "\n")
    for a in ajouts[:9]:
        print(f"   {a['snk']:20} {a['fr']}")

    if not ecrire:
        print("\n(essai à blanc — relancer avec --ecrire)")
        return

    lignes = ["  - {" + f'snk: "{a["snk"]}", fr: {a["fr"]}, verbes: [wori], source: "{SOURCE}"' + "}"
              for a in ajouts]
    texte = OBJETS.read_text(encoding="utf-8").rstrip()
    bloc = "\n\n  # --- noms du glossaire, avec leurs trois déterminations ---\n" + "\n".join(lignes)
    OBJETS.write_text(texte.replace("\ncomplements:", bloc + "\n\ncomplements:") + "\n",
                      encoding="utf-8")
    print(f"\nécrit : {len(ajouts)} formes")


if __name__ == "__main__":
    main("--ecrire" in sys.argv)
