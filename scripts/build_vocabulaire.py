"""Génère docs/langue/vocabulaire.md en fusionnant toutes les sources de mots.

Quatre provenances, qui n'ont pas le même statut :

  locuteur   data/grammaire/objets.yaml et data/references/mots.yaml — donné et
             confirmé par le locuteur du projet au fil des textes.
  SIL 2016   « Parlons le soninké et le français » (Hagg) — soninké du Mali.
  glossaire  le glossaire fourni par le locuteur — graphie du Sénégal/Mauritanie.
  guide 2020 le guide d'écriture (Dramé & Hagg) — norme d'écriture du Mali.

La provenance est affichée pour chaque mot : les trois dernières notent des
variétés qui ne sont pas forcément celle du locuteur, et le lecteur doit pouvoir
le voir. Un mot attesté par plusieurs sources est signalé comme tel — c'est la
meilleure garantie qu'on ait.

    uv run python scripts/build_vocabulaire.py
"""

import re
from collections import defaultdict
from pathlib import Path

import yaml

from snk_engine.understand import _simple_meaning, _walk_words

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SORTIE = ROOT / "docs" / "langue" / "vocabulaire.md"

# Les thèmes de l'ouvrage SIL, dans un ordre qui va du proche au lointain.
THEMES = [
    ("famille", "La famille"), ("corps", "Le corps"), ("animaux", "Les animaux"),
    ("vivres", "Les vivres"), ("choses", "Les choses"), ("jours", "Les jours"),
    ("mois", "Les mois"), ("nombres", "Les nombres"), ("questions", "Les questions"),
    ("salutations", "Les salutations"),
]


def pivot(mot: str) -> str:
    """Squelette commun aux graphies : voyelles longues, dj/j, ɲ/ñ, nn/nŋ."""
    import unicodedata
    m = unicodedata.normalize("NFD", mot.lower())
    m = "".join(c for c in m if not unicodedata.combining(c))
    m = m.replace("dj", "j").replace("ɲ", "ny").replace("ñ", "ny").replace("ŋ", "ng")
    m = m.replace("kh", "x").replace("ou", "u")
    return re.sub(r"(.)\1+", r"\1", m).strip("' ")


def nettoie(fr: str) -> str:
    return re.sub(r"\s+", " ", str(fr)).strip(" .,;")


def rassemble() -> dict[str, dict]:
    """pivot → {formes, sens, sources, theme}."""
    mots: dict[str, dict] = defaultdict(lambda: {"formes": [], "sens": [], "sources": [], "theme": ""})

    def ajoute(snk, fr, source, theme=""):
        if not snk or not fr:
            return
        snk, fr = str(snk).strip(), nettoie(fr)
        if not snk or not fr or len(snk) > 40:
            return
        e = mots[pivot(snk)]
        # le glossaire capitalise ses entrées : « Faabe » et « faabe » sont le même mot,
        # et les afficher côte à côte ne dirait rien au lecteur
        if snk.lower() not in [f.lower() for f in e["formes"]]:
            e["formes"].append(snk)
        if fr.lower() not in [s.lower() for s in e["sens"]]:
            e["sens"].append(fr)
        if source not in e["sources"]:
            e["sources"].append(source)
        if theme and not e["theme"]:
            e["theme"] = theme

    objets = yaml.safe_load((DATA / "grammaire" / "objets.yaml").read_text(encoding="utf-8")) or {}
    for section in ("objets", "complements"):
        for item in objets.get(section) or []:
            ajoute(item.get("snk"), item.get("fr"), "locuteur")
    reference = yaml.safe_load((DATA / "references" / "mots.yaml").read_text(encoding="utf-8")) or {}
    for item in _walk_words(reference):
        if _simple_meaning(item.get("snk"), item.get("fr")):
            ajoute(item["snk"], item["fr"], "locuteur")

    hagg = yaml.safe_load((DATA / "references" / "hagg_2016.yaml").read_text(encoding="utf-8")) or {}
    for theme, entrees in hagg.items():
        if isinstance(entrees, list):
            for item in entrees:
                ajoute(item.get("snk"), item.get("fr"), "SIL 2016", theme)
                if item.get("variante"):
                    ajoute(item["variante"].split("(")[0].strip(), item["fr"], "SIL 2016", theme)

    glossaire = yaml.safe_load((DATA / "references" / "glossaire.yaml").read_text(encoding="utf-8")) or {}
    for item in glossaire.get("entrees") or []:
        ajoute(item.get("snk"), item.get("fr"), "glossaire")

    guide = yaml.safe_load((DATA / "references" / "guide_ecriture_2020.yaml").read_text(encoding="utf-8")) or {}
    for lettre in (guide.get("alphabet", {}).get("prononciation") or {}).values():
        ajoute(lettre.get("exemple"), lettre.get("fr"), "guide 2020")
    return mots


def tableau(entrees: list[tuple[str, dict]]) -> list[str]:
    lignes = ["| soninké | français | source |", "|---|---|---|"]
    for _, e in entrees:
        formes = " · ".join(e["formes"][:3])
        sens = " ; ".join(e["sens"][:2])
        sources = ", ".join(e["sources"])
        marque = " ✓" if len(e["sources"]) > 1 else ""
        lignes.append(f"| **{formes}** | {sens} | {sources}{marque} |")
    return lignes + [""]


def main() -> None:
    mots = rassemble()
    par_theme: dict[str, list] = defaultdict(list)
    for cle, e in mots.items():
        par_theme[e["theme"] or "_reste"].append((cle, e))
    for liste in par_theme.values():
        liste.sort(key=lambda x: x[0])

    confirmes = sum(1 for e in mots.values() if len(e["sources"]) > 1)
    out = [
        "---",
        'description: "Vocabulaire soninké-français : plus de mille mots réunis des données '
        'du locuteur, du manuel SIL, du guide d\'écriture et du glossaire."',
        "---",
        "",
        "# Le vocabulaire",
        "",
        "Cette page est **générée** à partir des données (`scripts/build_vocabulaire.py`).",
        "Elle réunit tout ce que le projet sait d'un mot, quelle qu'en soit la provenance.",
        "",
        f"**{len(mots)} mots**, dont **{confirmes}** attestés par au moins deux sources "
        "indépendantes — ceux-là portent un ✓.",
        "",
        "## D'où viennent ces mots",
        "",
        "| source | ce que c'est | réserve |",
        "|---|---|---|",
        "| `locuteur` | donné et confirmé par le locuteur du projet | aucune : c'est la variété de référence |",
        "| `SIL 2016` | *Parlons le soninké et le français*, Marianne Hagg | soninké du Mali |",
        "| `guide 2020` | *Guide d'écriture*, Dramé & Hagg, norme malienne | norme d'écriture, pas de parole |",
        "| `glossaire` | le glossaire soninké-français | graphie du Sénégal, Gambie ou Mauritanie |",
        "",
        "Le soninké se parle au Mali, au Sénégal, en Gambie, en Mauritanie et en Guinée-Bissau,",
        "et les parlers diffèrent. Un mot marqué `glossaire` ou `SIL 2016` n'est donc pas",
        "forcément celui qu'emploie le locuteur du projet — d'où la colonne « source ».",
        "Seules les formes `locuteur` entrent dans le moteur de conjugaison.",
        "",
        "Voir aussi [Le lexique](lexique.md), qui ne donne que les mots du moteur.",
        "",
    ]
    for cle, titre in THEMES:
        if par_theme.get(cle):
            out += [f"## {titre}", ""] + tableau(par_theme[cle])
    reste = par_theme.get("_reste", [])
    if reste:
        out += ["## Le reste, par ordre alphabétique", ""] + tableau(reste)

    SORTIE.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"{len(mots)} mots ({confirmes} multi-sources) → {SORTIE.relative_to(ROOT)}")
    for cle, titre in THEMES:
        if par_theme.get(cle):
            print(f"   {titre:18} {len(par_theme[cle]):5}")
    print(f"   {'reste':18} {len(reste):5}")


if __name__ == "__main__":
    main()
