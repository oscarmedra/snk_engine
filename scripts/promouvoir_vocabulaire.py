"""Fait entrer dans le moteur les noms des sources validées par le locuteur.

Le moteur ne pouvait fabriquer des phrases qu'avec huit objets. Les sources en
apportent des centaines — mais un mot n'y suffit pas : pour produire une phrase il
faut aussi sa CATÉGORIE (objet ? complément ?), son ARTICLE français, et les verbes
qui l'acceptent.

Ce que les sources donnent vraiment :
  - la catégorie se lit dans leur structure même. Le glossaire marque ses noms d'un
    couple singulier/pluriel « (i, nu) » ; SIL 2016 range les siens par thème.
  - l'article français, SIL 2016 le donne (« le père ») ; le glossaire presque
    jamais (« Policier »). Sans lui le moteur écrirait « je vois policier », donc
    seules les entrées déjà pourvues entrent ici.
  - les verbes compatibles, aucune source ne les donne. On retient donc la
    revendication la plus faible possible : `wori` (voir) accepte tout ce qui est
    concret, et c'est le seul verbe porté par les huit objets déjà confirmés. Les
    vivres reçoivent en plus `yigeyer` (manger), ce que leur thème suffit à établir.

    uv run python scripts/promouvoir_vocabulaire.py            # essai à blanc
    uv run python scripts/promouvoir_vocabulaire.py --ecrire
"""

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
OBJETS = ROOT / "data" / "grammaire" / "objets.yaml"
HAGG = ROOT / "data" / "references" / "hagg_2016.yaml"

ARTICLE = re.compile(r"^(le |la |les |l'|un |une |du |de la |des )", re.I)
THEMES_OBJET = ("famille", "corps", "animaux", "vivres", "choses")
SOURCE = "SIL 2016 (Hagg), validé par le locuteur 2026-10-29"


def pivot(mot: str) -> str:
    import unicodedata
    m = unicodedata.normalize("NFD", mot.lower())
    m = "".join(c for c in m if not unicodedata.combining(c))
    m = m.replace("dj", "j").replace("ɲ", "ny").replace("ñ", "ny").replace("ŋ", "ng")
    return re.sub(r"(.)\1+", r"\1", m).strip("' ")


def main(ecrire: bool = False) -> None:
    objets = yaml.safe_load(OBJETS.read_text(encoding="utf-8")) or {}
    hagg = yaml.safe_load(HAGG.read_text(encoding="utf-8")) or {}
    connus = {pivot(i["snk"]) for s in ("objets", "complements")
              for i in (objets.get(s) or []) if i.get("snk")}

    neufs_objets, neufs_complements, ecartes = [], [], []
    for theme in THEMES_OBJET:
        for item in hagg.get(theme) or []:
            snk, fr = item.get("snk", ""), item.get("fr", "")
            if not ARTICLE.match(fr):
                ecartes.append((snk, fr, "pas d'article français"))
                continue
            if pivot(snk) in connus:
                ecartes.append((snk, fr, "déjà dans le moteur"))
                continue
            connus.add(pivot(snk))
            verbes = ["yigeyer", "wori"] if theme == "vivres" else ["wori"]
            neufs_objets.append({"snk": snk, "fr": fr, "verbes": verbes,
                                 "theme": theme, "source": SOURCE})

    # un jour de la semaine se met tel quel (« je mange dimanche »), un mois prend « en »
    for theme, gabarit in (("jours", "{}"), ("mois", "en {}")):
        for item in hagg.get(theme) or []:
            snk, fr = item.get("snk", ""), item.get("fr", "")
            if pivot(snk) in connus or ARTICLE.match(fr):
                ecartes.append((snk, fr, "déjà connu ou porte un article"))
                continue
            connus.add(pivot(snk))
            neufs_complements.append({"snk": snk, "fr": gabarit.format(fr),
                                      "theme": theme, "source": SOURCE})

    print(f"{len(neufs_objets)} objets et {len(neufs_complements)} compléments à ajouter")
    print(f"{len(ecartes)} entrées écartées\n")
    for o in neufs_objets[:6]:
        print(f"   objet      {o['snk']:14} {o['fr']:22} {o['verbes']}")
    for c in neufs_complements[:3]:
        print(f"   complément {c['snk']:14} {c['fr']}")
    raisons: dict[str, int] = {}
    for _, _, r in ecartes:
        raisons[r] = raisons.get(r, 0) + 1
    print("\n   écartés : " + ", ".join(f"{r} ({n})" for r, n in raisons.items()))

    if not ecrire:
        print("\n(essai à blanc — relancer avec --ecrire)")
        return

    def bloc(entrees: list[dict]) -> str:
        lignes = []
        for e in entrees:
            champs = [f"snk: {e['snk']}", f"fr: {e['fr']}"]
            if e.get("verbes"):
                champs.append(f"verbes: [{', '.join(e['verbes'])}]")
            champs.append(f'source: "{e["source"]}"')
            lignes.append("  - {" + ", ".join(champs) + "}")
        return "\n".join(lignes)

    texte = OBJETS.read_text(encoding="utf-8").rstrip()
    entete = f"\n\n  # --- noms des sources validées le 2026-10-29 ---\n"
    if neufs_objets:
        texte = texte.replace("\ncomplements:", entete + bloc(neufs_objets) + "\n\ncomplements:")
    if neufs_complements:
        texte += entete + bloc(neufs_complements)
    OBJETS.write_text(texte + "\n", encoding="utf-8")
    print(f"\nécrit dans {OBJETS.relative_to(ROOT)}")


if __name__ == "__main__":
    main("--ecrire" in sys.argv)
