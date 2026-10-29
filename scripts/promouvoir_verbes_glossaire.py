"""Fait entrer dans le moteur les verbes du glossaire dont tout est connu.

Trois pièces sont nécessaires, et le glossaire n'en donne que deux :

  le radical          il le donne (« Betu »)
  l'infinitif français il le donne (« Serrer »)
  la forme en -ni     il donne une seconde forme, mais pas toujours celle-là :
                      « bono / bonno » est une géminée, pas un -ni.

D'où le choix : le gérondif vient de LA RÈGLE DU LOCUTEUR — le suffixe reprend la
dernière voyelle — que le glossaire a par ailleurs confirmée sur 201 verbes. Quand
sa seconde forme diffère, elle est notée à part comme variante à trancher, et non
substituée à la règle.

Côté français, seuls les deux groupes réguliers sont dérivables : un verbe
irrégulier resterait faux à conjuguer, donc il attend.

    uv run python scripts/promouvoir_verbes_glossaire.py            # essai à blanc
    uv run python scripts/promouvoir_verbes_glossaire.py --ecrire
"""

import re
import sys
from pathlib import Path

import yaml

from promote_verbes import french_forms, propose_gerund

ROOT = Path(__file__).resolve().parents[1]
GRAMMAIRE = ROOT / "data" / "grammaire" / "soninke.yaml"
GLOSSAIRE = ROOT / "data" / "references" / "glossaire.yaml"
INFINITIF = re.compile(r"^(se |s')?[a-zà-ÿ]+(er|ir)$", re.I)


def main(ecrire: bool = False) -> None:
    texte = GRAMMAIRE.read_text(encoding="utf-8")
    grammaire = yaml.safe_load(texte)
    entrees = yaml.safe_load(GLOSSAIRE.read_text(encoding="utf-8"))["entrees"]

    connus = {str(v.get("forme", "")).lower() for v in grammaire["verbes"].values()}
    cles = set(grammaire["verbes"])

    neufs, variantes, ecartes = {}, [], 0
    for e in entrees:
        forme2, radical = e.get("forme2"), e["snk"].lower()
        sens = e["fr"].split(",")[0].strip().lower()
        if not forme2 or not INFINITIF.match(sens) or radical in connus:
            continue
        groupe = "1er" if sens.endswith("er") else "2e"
        francais = french_forms(sens, groupe)
        if not francais:
            ecartes += 1
            continue
        gerondif = propose_gerund(radical)
        if forme2.lower() != gerondif:
            variantes.append((radical, gerondif, forme2.lower()))
        cle = radical if radical not in cles else f"{radical}2"
        cles.add(cle)
        connus.add(radical)
        neufs[cle] = {"fr": sens, "forme": radical, "gerondif": gerondif,
                      "classe": "regulier", "francais": francais,
                      "source": "glossaire, validé par le locuteur 2026-10-29"}

    print(f"{len(neufs)} verbes prêts à entrer ({ecartes} écartés : français irrégulier)")
    print(f"{len(variantes)} ont dans le glossaire une seconde forme qui n'est pas le -ni\n")
    for cle, v in list(neufs.items())[:6]:
        print(f"   {cle:14} {v['fr']:16} {v['forme']} / {v['gerondif']}")
    print("\n   secondes formes à trancher (règle du locuteur / glossaire) :")
    for r, g, f2 in variantes[:8]:
        print(f"      {r:14} {g:16} ≠ {f2}")

    if not ecrire:
        print("\n(essai à blanc — relancer avec --ecrire)")
        return

    bloc = yaml.safe_dump({"verbes": neufs}, allow_unicode=True, sort_keys=False, width=200)
    bloc = "\n".join(l[2:] if l.startswith("  ") else l for l in bloc.splitlines()[1:])
    GRAMMAIRE.write_text(
        texte.rstrip() + "\n\n  # --- verbes du glossaire (gérondif par la règle du locuteur) ---\n"
        + "\n".join("  " + l for l in bloc.splitlines()) + "\n", encoding="utf-8")
    (ROOT / "data" / "references" / "secondes_formes.yaml").write_text(
        "# Secondes formes du glossaire qui ne sont pas des formes en -ni : des géminées,\n"
        "# probablement un autre temps. Le moteur garde la règle du locuteur ; celles-ci\n"
        "# attendent son avis.\n\n"
        + yaml.safe_dump({"a_trancher": [{"radical": r, "regle": g, "glossaire": f}
                                         for r, g, f in variantes]},
                         allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"\nécrit : {len(neufs)} verbes, et {len(variantes)} secondes formes mises de côté")


if __name__ == "__main__":
    main("--ecrire" in sys.argv)
