"""Énumère toutes les phrases que le moteur sait produire, avec leur traduction.

Pour chaque verbe, chaque pronom et chaque temps confirmé, on obtient une paire
soninké / français. Les temps qui demandent un objet parcourent en plus la liste
d'objets (data/grammaire/objets.yaml) ; un complément de lieu ou de temps peut
être ajouté aux temps qui l'acceptent.

Rien n'est inventé : si le moteur refuse une combinaison, elle est simplement absente.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import yaml

from .conjugation import DEFAULT_GRAMMAR, ConjugationEngine, ConjugationError, Verb
from .french import FrenchError, FrenchVerb, conjugate_fr

# Temps auxquels on peut ajouter un complément de lieu ou de temps (confirmé par corp1/serie_02)
COMPLEMENT_TENSES = {"past", "past_object", "future", "future_lointain", "demande", "demande_objet",
                     "en_cours", "en_cours_objet", "en_cours_fayi", "en_cours_objet_fayi",
                     "en_cours_do", "en_cours_objet_do", "en_cours_wa", "en_cours_objet_wa",
                     "past_object_da"}


@dataclass(frozen=True)
class Sentence:
    snk: str
    fr: str
    verb: str
    tense: str
    person: str
    pronoun: str
    obj: str | None = None
    complement: str | None = None


def load_objects(path: Path | None = None) -> tuple[list[dict], list[dict]]:
    """Objets et compléments (lieux, moments) avec leur traduction."""
    path = path or DEFAULT_GRAMMAR / "objets.yaml"
    if not path.exists():
        return [], []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return list(data.get("objets") or []), list(data.get("complements") or [])


def french_verbs(engine: ConjugationEngine, raw_path: Path | None = None) -> dict[str, FrenchVerb]:
    """Lit la section `francais` de chaque verbe dans les données de grammaire."""
    raw_path = raw_path or DEFAULT_GRAMMAR / "soninke.yaml"
    data = yaml.safe_load(raw_path.read_text(encoding="utf-8")) or {}
    out = {}
    for name, v in (data.get("verbes") or {}).items():
        if v.get("francais"):
            out[name] = FrenchVerb.from_data(name, v["francais"])
    return out


def _person_of(engine: ConjugationEngine, pronoun: str) -> str:
    return engine.pronouns[pronoun][0].person


def generate(
    engine: ConjugationEngine,
    fr_verbs: dict[str, FrenchVerb] | None = None,
    objects: list[dict] | None = None,
    complements: list[dict] | None = None,
) -> Iterator[Sentence]:
    fr_verbs = fr_verbs if fr_verbs is not None else french_verbs(engine)
    if objects is None or complements is None:
        loaded_objects, loaded_complements = load_objects()
        objects = loaded_objects if objects is None else objects
        complements = loaded_complements if complements is None else complements

    for name, verb in engine.verbs.items():
        fr_verb = fr_verbs.get(name)
        if fr_verb is None:
            continue
        for tense, tense_def in engine.tenses.items():
            if tense_def.object and not verb.transitive:
                continue          # verbe intransitif : pas de phrase avec objet
            fillers = [o for o in objects if name in (o.get("verbes") or [name])] \
                if tense_def.object else [None]
            for pronoun in engine.pronouns:
                person = _person_of(engine, pronoun)
                for filler in fillers:
                    allowed = [c for c in complements
                               if tense in COMPLEMENT_TENSES and tense in (c.get("temps") or [tense])]
                    yield from _build(engine, verb, fr_verb, tense, pronoun, person, filler, allowed)


def _build(engine, verb: Verb, fr_verb: FrenchVerb, tense: str, pronoun: str, person: str,
           filler: dict | None, complements: list[dict]) -> Iterator[Sentence]:
    obj_snk = filler["snk"] if filler else None
    obj_fr = filler["fr"] if filler else None
    try:
        snk = engine.conjugate(verb.infinitive, pronoun, tense, obj_snk)
        fr = conjugate_fr(fr_verb, person, tense, obj_fr)
    except (ConjugationError, FrenchError):
        return
    yield Sentence(snk, fr, verb.infinitive, tense, person, pronoun, obj_snk)
    for comp in complements:
        yield Sentence(f"{snk} {comp['snk']}", f"{fr} {comp['fr']}", verb.infinitive, tense,
                       person, pronoun, obj_snk, comp["snk"])


def count(engine: ConjugationEngine, **kwargs) -> int:
    return sum(1 for _ in generate(engine, **kwargs))
