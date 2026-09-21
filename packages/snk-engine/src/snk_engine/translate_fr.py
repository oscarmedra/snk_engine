"""Traduire du français vers le soninké.

Le principe est symétrique de understand.py, et tout aussi prudent :

  1. **reconnaître le verbe** : le moteur sait produire le français de chaque verbe
     confirmé, à chaque personne et à chaque temps (conjugate_fr). On en construit
     l'index inverse — « il a mangé » → (yigeyer, 3sg, past) ;
  2. **reconnaître le reste** : ce qui suit le verbe est cherché dans le glossaire
     inversé (objets et compléments confirmés d'abord, lexique ensuite) ;
  3. **produire le soninké** avec le moteur de conjugaison lui-même.

Rien n'est deviné : un passage français qu'aucune donnée ne couvre devient [unknown].
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from .conjugation import ConjugationError
from .french import PERSONS, FrenchError, conjugate_fr
from .understand import UNKNOWN, Lexicon, collapse_unknowns, load_lexicon

SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
CLAUSE_SPLIT = re.compile(r"\s*([,;:])\s*")

# Quand plusieurs temps donnent le même français, on préfère le plus courant.
TENSE_PREFERENCE = [
    "past", "past_object", "en_cours", "en_cours_objet", "future", "past_negative",
    "future_negative", "imperatif", "imperatif_objet", "imperatif_negatif",
    "imperatif_pluriel", "demande", "demande_objet", "imminent", "en_cours_do",
    "en_cours_objet_do", "progressive_watia", "en_cours_fayi", "en_cours_objet_fayi",
    "future_negative_ntaxa",
]
WITH_OBJECT = {"past": "past_object", "en_cours": "en_cours_objet", "demande": "demande_objet",
               "imperatif": "imperatif_objet", "en_cours_fayi": "en_cours_objet_fayi",
               "en_cours_do": "en_cours_objet_do"}
SUBJECT_ALIASES = {"elle": "il", "elles": "ils", "on": "nous"}


@dataclass(frozen=True)
class Translation:
    fr: str
    snk: str
    confirme: bool
    frame: dict
    notes: tuple[str, ...] = ()
    ponctuation: str = ""


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFC", text).lower().replace("’", "'")
    text = re.sub(r"\b(elles?|on)\b", lambda m: SUBJECT_ALIASES[m.group(1)], text)
    return re.sub(r"\s+", " ", text.strip(" .!?")).strip()


def build_index(lex: Lexicon) -> dict[str, list[tuple[str, str, str]]]:
    """Français produit par le moteur → [(verbe, personne, temps)]."""
    index: dict[str, list[tuple[str, str, str]]] = {}
    for verb, fr_verb in lex.french.items():
        for tense in lex.engine.tenses:
            if lex.engine.tenses[tense].object:
                continue            # les variantes à objet se retrouvent via WITH_OBJECT
            for person in PERSONS:
                try:
                    phrase = conjugate_fr(fr_verb, person, tense)
                except FrenchError:
                    continue
                index.setdefault(_norm(phrase), []).append((verb, person, tense))
    for entries in index.values():
        entries.sort(key=lambda e: TENSE_PREFERENCE.index(e[2]) if e[2] in TENSE_PREFERENCE else 99)
    return index


def reverse_glossary(lex: Lexicon) -> dict[str, str]:
    """Français → soninké ; le glossaire est déjà ordonné : confirmé d'abord."""
    out: dict[str, str] = {}
    for snk, fr in lex.glossary.items():
        out.setdefault(_norm(fr), snk)
    return out


def _match_phrases(words: list[str], glossary: dict[str, str], notes: list[str]) -> list[str]:
    """Découpe le reste de la phrase en expressions connues, la plus longue d'abord."""
    out, i = [], 0
    while i < len(words):
        for j in range(len(words), i, -1):
            chunk = " ".join(words[i:j])
            if chunk in glossary:
                out.append(glossary[chunk])
                i = j
                break
        else:
            notes.append(f"« {words[i]} » : non reconnu → {UNKNOWN}")
            out.append(UNKNOWN)
            i += 1
    return out


def _pronoun_for(lex: Lexicon, verb: str, person: str, tense: str, obj: str | None) -> str | None:
    """Premier pronom de cette personne pour lequel le moteur confirme la forme."""
    for form, pronouns in lex.engine.pronouns.items():
        if pronouns[0].person != person:
            continue
        try:
            lex.engine.conjugate(verb, form, tense, obj)
            return form
        except ConjugationError:
            continue
    return None


def translate_clause(clause: str, lex: Lexicon, index=None, glossary=None) -> Translation:
    index = index if index is not None else build_index(lex)
    glossary = glossary if glossary is not None else reverse_glossary(lex)
    notes: list[str] = []
    text = _norm(clause)
    words = text.split()

    # 1. le verbe conjugué : la plus longue expression connue en tête de phrase
    for cut in range(len(words), 0, -1):
        head = " ".join(words[:cut])
        if head not in index:
            continue
        for verb, person, tense in index[head]:
            rest = words[cut:]
            parts = _match_phrases(rest, glossary, notes)
            obj, complements = None, parts
            # un objet juste après le verbe → variante « avec objet » du temps
            if parts and parts[0] != UNKNOWN and lex.engine.verbs[verb].transitive and tense in WITH_OBJECT:
                obj_tense = WITH_OBJECT[tense]
                pronoun = _pronoun_for(lex, verb, person, obj_tense, parts[0])
                if pronoun:
                    obj, tense, complements = parts[0], obj_tense, parts[1:]
            pronoun = _pronoun_for(lex, verb, person, tense, obj)
            if pronoun is None:
                continue
            snk = " ".join([lex.engine.conjugate(verb, pronoun, tense, obj), *complements])
            snk = collapse_unknowns(snk)
            frame = {"verbe": verb, "personne": person, "temps": tense, "objet": obj,
                     "complements": complements, "pronom": pronoun}
            return Translation(clause.strip(), snk, UNKNOWN not in snk, frame, tuple(notes))

    # 2. aucun verbe reconnu : mot à mot, avec [unknown] pour le reste
    notes.append("aucun verbe reconnu : traduction mot à mot")
    snk = collapse_unknowns(" ".join(_match_phrases(words, glossary, notes)))
    return Translation(clause.strip(), snk, False, {}, tuple(notes))


def translate_text(text: str, lex: Lexicon | None = None) -> list[Translation]:
    """Traduit n'importe quel texte français, sans jamais échouer."""
    lex = lex or load_lexicon()
    index, glossary = build_index(lex), reverse_glossary(lex)
    results = []
    for sentence in (s.strip() for s in SENTENCE_SPLIT.split(text.strip()) if s.strip()):
        end = sentence[-1] if sentence[-1] in ".!?" else ""
        parts = CLAUSE_SPLIT.split(sentence.rstrip(".!?").strip())
        for i in range(0, len(parts), 2):
            if not parts[i].strip():
                continue
            punct = parts[i + 1] if i + 1 < len(parts) else end
            t = translate_clause(parts[i], lex, index, glossary)
            results.append(Translation(t.fr, t.snk, t.confirme, t.frame, t.notes, punct))
    return results


def render(translations: list[Translation]) -> str:
    out = " ".join(t.snk + t.ponctuation for t in translations)
    return re.sub(r"\s+([,;:.!?])", r"\1", out).strip()
