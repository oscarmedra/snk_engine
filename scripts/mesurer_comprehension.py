"""Mesure ce que le moteur comprend du corpus validé, par type de phrase.

Une phrase compte pour comprise si le moteur en retrouve le verbe, le temps, et le
sujet QUAND IL Y EN A UN : un impératif n'en a pas — « maxa daga » (ne pars pas) est
parfaitement analysé sans sujet, et l'exiger fausserait la mesure.

    uv run python scripts/mesurer_comprehension.py
"""

import json
from collections import defaultdict
from pathlib import Path

from snk_engine.understand import (AnalysisError, analyze, load_lexicon,
                                   split_sentences, tag, tokenize)

ROOT = Path(__file__).resolve().parents[1]
SANS_SUJET = ("imperatif", "imperatif_objet", "imperatif_pluriel", "imperatif_negatif")


def comprise(phrase: str, lex) -> bool:
    for part in split_sentences(phrase) or [phrase]:
        try:
            frame = analyze(part, lex).frame
        except AnalysisError:
            return False
        if not frame.get("verbe") or not frame.get("temps"):
            return False
        if frame["temps"] not in SANS_SUJET and not frame.get("sujet"):
            return False
    return True


def categorie(phrase: str, lex) -> str:
    if len(split_sentences(phrase)) > 1:
        return "plusieurs phrases"
    tokens = tag(tokenize(phrase), lex)
    if not tokens:
        return "vide"
    tete = tokens[0]
    if "pronom" in tete.tags:
        return "sujet pronom"
    if "interrogatif" in tete.tags:
        return "question en tête"
    if "marqueur" in tete.tags:
        return "marqueur ou impératif"
    if tete.particle:
        return "particule en tête"
    return "sujet nominal"


def main() -> None:
    lex = load_lexicon()
    phrases = [json.loads(l)["snk"]
               for f in sorted((ROOT / "corpus" / "valide").glob("*.jsonl"))
               for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]

    groupes = defaultdict(list)
    for p in phrases:
        groupes[categorie(p, lex)].append(p)
    total = sum(1 for p in phrases if comprise(p, lex))

    print(f"COMPRÉHENSION DU CORPUS : {total}/{len(phrases)}  ({100 * total // len(phrases)} %)\n")
    for nom, groupe in sorted(groupes.items(), key=lambda x: -len(x[1])):
        ok = sum(1 for p in groupe if comprise(p, lex))
        print(f"   {nom:26} {len(groupe):4} → {ok:4}  ({100 * ok // len(groupe):3} %)")


if __name__ == "__main__":
    main()
