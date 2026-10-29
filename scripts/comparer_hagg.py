"""Confronte le lexique SIL (Hagg 2016) aux données du projet, mot à mot.

L'ouvrage annonce « orthographe : soninké du Mali » ; le projet note la variété de
son locuteur. Les deux peuvent diverger — en orthographe (maaro / maro) comme en
vocabulaire (renme / lemine). Ce script ne décide rien : il trie en trois tas.

  accord      le mot et le sens concordent        → confirmation gratuite
  divergence  le sens concorde, la forme non      → à trancher par le locuteur
  nouveau     absent des données du projet        → candidat à l'import

    uv run python scripts/comparer_hagg.py
"""

import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

import yaml

from snk_engine.understand import _simple_meaning, _walk_words

ROOT = Path(__file__).resolve().parents[1]
MOT = re.compile(r"[a-zà-ÿŋñɲ']+")


def pivot(mot: str) -> str:
    """Forme de comparaison, indifférente aux écarts d'orthographe connus.

    Les deux sources ne notent pas pareil : voyelles longues (maaro / maro),
    « dj » contre « j » (dji / ji), accents de l'ancienne notation (yimbé / yinbe),
    consonnes doublées (sappe / sape). On ramène tout à un squelette commun.
    """
    m = unicodedata.normalize("NFD", mot.lower())
    m = "".join(c for c in m if not unicodedata.combining(c))
    m = m.replace("dj", "j").replace("ɲ", "ny").replace("ñ", "ny").replace("ŋ", "ng")
    m = m.replace("kh", "x").replace("ou", "u")
    m = re.sub(r"(.)\1+", r"\1", m)            # voyelles et consonnes doublées
    return m.strip("' ")


def sens_pivot(fr: str) -> str:
    """Sens français sans article ni précision entre parenthèses."""
    f = re.sub(r"\(.*?\)", "", fr.lower()).strip()
    f = re.sub(r"^(le |la |les |l'|un |une |du |de la |des |au |à la )", "", f)
    return f.strip(" .")


def donnees_projet() -> dict[str, list[str]]:
    """Tout ce que le projet connaît : pivot → sens enregistrés."""
    connu: dict[str, list[str]] = {}
    data = ROOT / "data"

    def ajoute(snk, fr):
        if snk and fr:
            connu.setdefault(pivot(str(snk)), []).append(str(fr))

    objets = yaml.safe_load((data / "grammaire" / "objets.yaml").read_text(encoding="utf-8")) or {}
    for section in ("objets", "complements"):
        for item in objets.get(section) or []:
            ajoute(item.get("snk"), item.get("fr"))
    mots = yaml.safe_load((data / "references" / "mots.yaml").read_text(encoding="utf-8")) or {}
    for item in _walk_words(mots):
        if _simple_meaning(item.get("snk"), item.get("fr")):
            ajoute(item["snk"], item["fr"])
    grammaire = yaml.safe_load((data / "grammaire" / "soninke.yaml").read_text(encoding="utf-8")) or {}
    for nom, verbe in (grammaire.get("verbes") or {}).items():
        ajoute(verbe.get("forme"), verbe.get("fr"))
        ajoute(verbe.get("nom_action"), verbe.get("fr"))
    verbes = yaml.safe_load((data / "references" / "verbes.yaml").read_text(encoding="utf-8")) or {}
    for item in (verbes.get("locuteur") or []) + (verbes.get("liste") or []):
        ajoute(item.get("radical"), item.get("fr"))
    return connu


def main() -> None:
    connu = donnees_projet()
    corpus = Counter()
    for fichier in sorted((ROOT / "corpus" / "valide").glob("*.jsonl")):
        for ligne in fichier.read_text(encoding="utf-8").splitlines():
            if ligne.strip():
                for mot in MOT.findall(json.loads(ligne)["snk"]):
                    corpus[pivot(mot)] += 1

    livre = yaml.safe_load((ROOT / "data" / "references" / "hagg_2016.yaml").read_text(encoding="utf-8"))
    accord, divergence, nouveau = [], [], []
    for section, entrees in livre.items():
        if not isinstance(entrees, list):
            continue
        for item in entrees:
            snk, fr = item["snk"], item["fr"]
            p = pivot(snk)
            if p in connu:
                sens = connu[p]
                if any(sens_pivot(fr) == sens_pivot(s) or sens_pivot(fr) in sens_pivot(s)
                       or sens_pivot(s) in sens_pivot(fr) for s in sens):
                    accord.append((section, snk, fr, sens[0]))
                else:
                    divergence.append((section, snk, fr, " / ".join(dict.fromkeys(sens))))
            else:
                nouveau.append((section, snk, fr, corpus.get(p, 0)))

    total = len(accord) + len(divergence) + len(nouveau)
    print(f"{total} entrées du livre confrontées aux données du projet\n")
    print(f"  accord      {len(accord):4}   le livre confirme ce que vous aviez dit")
    print(f"  divergence  {len(divergence):4}   même forme, sens différent — à trancher")
    print(f"  nouveau     {len(nouveau):4}   absent du projet — candidat à l'import\n")

    print("— ACCORDS (le livre vous confirme) —")
    for s, snk, fr, chez in accord:
        print(f"   {snk:16} {fr:28} (projet : {chez})")
    print("\n— DIVERGENCES (à trancher) —")
    for s, snk, fr, chez in divergence:
        print(f"   {snk:16} livre : {fr:24} projet : {chez}")
    print(f"\n— NOUVEAUX vus dans votre corpus (donc sûrement de votre variété) —")
    for s, snk, fr, vu in sorted((n for n in nouveau if n[3]), key=lambda x: -x[3]):
        print(f"   {snk:16} {fr:28} vu {vu}× dans le corpus")


if __name__ == "__main__":
    main()
