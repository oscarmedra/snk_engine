"""Génère docs/langue/prononciation.md à partir du guide d'écriture.

Rien n'est inventé ici : tout vient de `data/references/guide_ecriture_2020.yaml`,
transcrit du Guide d'écriture de la langue soninké (Dramé & Hagg, SIL Mali 2020),
validé par la Direction Nationale de l'Éducation Non-Formelle du Mali.

Le guide le dit lui-même : « Standardiser ne veut pas dire changer sa manière de
parler mais plutôt avoir une seule façon d'écrire les mots. » La page décrit donc
des sons, pas une façon correcte de parler.

    uv run python scripts/build_prononciation.py
"""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "data" / "references" / "guide_ecriture_2020.yaml"
SORTIE = ROOT / "docs" / "langue" / "prononciation.md"

# ce que la nasale fait au son suivant, en français lisible
NASALES = {
    "m_b_p": "devant **m**, **b**, **p**", "ŋ": "devant **ŋ**", "a": "devant **a**",
    "w": "devant **w**", "y": "devant **y**", "f_h": "devant **f** ou **h**",
    "s": "devant **s**", "x": "devant **x**", "r_l": "devant **r** ou **l**",
}


def main() -> None:
    guide = yaml.safe_load(GUIDE.read_text(encoding="utf-8"))
    alphabet = guide["alphabet"]
    out = [
        "---",
        'description: "Prononciation du soninké : l\'alphabet lettre par lettre, les '
        'voyelles longues et nasales, et ce que la nasale fait au son suivant."',
        "---",
        "",
        "# La prononciation",
        "",
        "Cette page est **générée** à partir des données (`scripts/build_prononciation.py`).",
        "",
        "Elle suit le *Guide d'écriture de la langue soninké* (Bandiougou S. Dramé et",
        "Marianne Hagg, SIL Mali, 2020), validé par la Direction Nationale de l'Éducation",
        "Non-Formelle du Mali et fondé sur le décret de 1982 et les rencontres",
        "d'harmonisation de Bakel (1995) à Serekunda (2018).",
        "",
        "!!! note \"Une norme d'écriture, pas de parole\"",
        "    Le guide le précise lui-même : « Standardiser ne veut pas dire changer sa",
        "    manière de parler mais plutôt avoir une seule façon d'écrire les mots. »",
        "    Les parlers diffèrent d'un pays à l'autre, et aucun n'est fautif.",
        "",
        f"## L'alphabet — {alphabet['lettres']} lettres",
        "",
        f"**Voyelles** : {', '.join(f'`{v}`' for v in alphabet['voyelles'])}  ",
        f"**Consonnes** : {', '.join(f'`{c}`' for c in alphabet['consonnes'])}",
        "",
        "| lettre | se prononce | exemple | sens |",
        "|---|---|---|---|",
    ]
    for lettre, d in alphabet["prononciation"].items():
        note = f" *{d['note']}*" if d.get("note") else ""
        out.append(f"| **{lettre}** | {d['son']}{note} | `{d['exemple']}` | {d['fr']} |")

    voyelles = guide["voyelles"]
    out += ["", "## Les voyelles", "",
            f"**Longues** — {voyelles['longues']}.", "",
            f"**Nasales** — {voyelles['nasales']}.", "",
            f"{voyelles['note'].capitalize()}.", ""]

    out += [
        "## Ce que la nasale fait au son suivant",
        "",
        "C'est la clé de la **particule** du projet. Les formes `n'`, `m'`, `l'`, `ŋ'`,",
        "`q'` ne sont pas une règle d'écriture : elles notent ce que la nasale devient",
        "selon la lettre qu'elle précède. La norme malienne écrit toujours `n` et laisse",
        "la prononciation faire son œuvre ; le projet, lui, écrit le son entendu.",
        "",
        "Les deux notent la même parole.",
        "",
        "| position | se prononce | la norme écrit | exemple |",
        "|---|---|---|---|",
    ]
    for cle, d in guide["nasale_devant"].items():
        exemple = (d.get("exemples") or [""])[0]
        out.append(f"| {NASALES.get(cle, cle)} | {d.get('prononce', '—')} | "
                   f"`{d['ecrit']}` | {exemple} |")

    out += ["", "## Ce qui change d'un parler à l'autre", ""]
    for cle, texte in guide["variation_documentee"].items():
        titre = {"f_h": "**f** et **h**", "r_l": "**r** et **l**", "x_q": "**x** et **q**",
                 "variantes_dialectales": "Les variantes", "pluriel": "Le pluriel"}.get(cle, cle)
        out.append(f"- {titre} — {texte}")
    out += ["", "Voir aussi [L'orthographe](orthographe.md) et [La particule](particule.md).", ""]

    SORTIE.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"{len(alphabet['prononciation'])} lettres → {SORTIE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
