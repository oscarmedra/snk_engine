"""Rend aux verbes venus du glossaire la forme que l'on emploie réellement.

Le locuteur tranche : « ma règle n'est pas fausse mais ce que le glossaire a montré
est celui utilisé. En parlant on saute beaucoup de choses et au final ça devient la
norme. » Autrement dit la règle donne la forme sous-jacente — bono + no = bonono —
et l'usage la contracte en bonno, qui est la forme vivante.

Le moteur doit produire ce qui se dit. On remplace donc le gérondif dérivé par celui
du glossaire, mais seulement :

  - pour les verbes QUE LE GLOSSAIRE A APPORTÉS. Les formes que le locuteur a
    lui-même confirmées ne bougent pas : son `rini` (venir), qui sert aussi de
    marqueur de temps, ne devient pas le `riini` du glossaire.
  - quand la forme est saine. L'extraction du PDF a laissé des débris (« kappa) r »),
    et une forme bien plus courte que son radical trahit une entrée mal découpée
    (jigijappe / jinmi).

    uv run python scripts/corriger_gerondifs_glossaire.py            # essai à blanc
    uv run python scripts/corriger_gerondifs_glossaire.py --ecrire
"""

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
GRAMMAIRE = ROOT / "data" / "grammaire" / "soninke.yaml"
GLOSSAIRE = ROOT / "data" / "references" / "glossaire.yaml"
MARQUE = "glossaire, validé par le locuteur"
PROPRE = re.compile(r"^[a-zà-ÿŋɲñ]+$")


def utilisable(radical: str, forme: str) -> bool:
    return bool(PROPRE.match(forme)) and len(forme) >= len(radical) - 1 and forme[:2] == radical[:2]


def main(ecrire: bool = False) -> None:
    texte = GRAMMAIRE.read_text(encoding="utf-8")
    verbes = yaml.safe_load(texte)["verbes"]
    glossaire = {e["snk"].lower(): e["forme2"].lower()
                 for e in yaml.safe_load(GLOSSAIRE.read_text(encoding="utf-8"))["entrees"]
                 if e.get("forme2")}

    corriges, refuses = [], []
    for cle, v in verbes.items():
        if MARQUE not in str(v.get("source", "")):
            continue
        radical, gerondif = str(v.get("forme", "")).lower(), str(v.get("gerondif", "")).lower()
        employe = glossaire.get(radical)
        if not employe or employe == gerondif:
            continue
        (corriges if utilisable(radical, employe) else refuses).append((cle, gerondif, employe))

    print(f"{len(corriges)} gérondifs à remplacer par la forme employée")
    print(f"{len(refuses)} formes refusées (abîmées à l'extraction)\n")
    for cle, avant, apres in corriges[:10]:
        print(f"   {cle:14} {avant:16} → {apres}")
    if refuses:
        print("\n   refusées : " + ", ".join(f"{c} ({a}→{b})" for c, a, b in refuses[:6]))

    if not ecrire:
        print("\n(essai à blanc — relancer avec --ecrire)")
        return

    for cle, avant, apres in corriges:
        # chaque verbe tient sur sa ligne `gerondif: ...` dans son propre bloc
        texte = texte.replace(f"gerondif: {avant}\n", f"gerondif: {apres}\n", 1)
    GRAMMAIRE.write_text(texte, encoding="utf-8")
    print(f"\nécrit : {len(corriges)} gérondifs ramenés à l'usage")


if __name__ == "__main__":
    main("--ecrire" in sys.argv)
