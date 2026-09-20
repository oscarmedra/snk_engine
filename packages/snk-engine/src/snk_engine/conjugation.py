"""Moteur de conjugaison soninké, piloté par les données de data/grammaire/.

Résolution d'une forme : sujet + marqueur du temps (s'il existe) + forme verbale.
La forme verbale est cherchée dans cet ordre, au niveau du verbe puis de sa classe :

  1. forme propre au sujet     (conjugaison.<temps>.formes.<sujet>
                                ou conjugaison.<temps>.exceptions.<sujet>)
  2. forme propre au temps     (conjugaison.<temps>.forme)
  3. forme du verbe            (forme)

Dans une forme, « {forme} » est remplacé par la forme du verbe et « {gerondif} »
par son gérondif (forme en -nV : dagana, rini).

Objet : un temps marqué `objet: true` place l'objet entre le marqueur et le verbe
(ake n'di maro n'yiga) ; le verbe prend alors sa `forme_objet` si elle est connue.

Particule (section `particules`) : pour un temps marqué `particule: true` et un sujet
listé dans `particules.personnes`, elle se colle au premier mot qui suit le sujet
(marqueur ou verbe) et dépend de l'initiale de ce mot : aké n'daga, aké n'yi rini daga.

Le moteur n'applique aucune règle implicite : un verbe sans conjugaison, un temps
non renseigné ou une personne absente de `personnes` lèvent une erreur.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

def _find_grammar() -> Path:
    """Remonte jusqu'au dossier data/grammaire du dépôt (le code peut être déplacé)."""
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "data" / "grammaire"
        if candidate.is_dir():
            return candidate
    return Path("data/grammaire")


DEFAULT_GRAMMAR = _find_grammar()
DATA_DIR = DEFAULT_GRAMMAR.parent


class ConjugationError(Exception):
    pass


class UnknownVerbError(ConjugationError):
    pass


class UnknownSubjectError(ConjugationError):
    pass


class UnknownTenseError(ConjugationError):
    pass


class ConjugationNotDefinedError(ConjugationError):
    pass


def _nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


@dataclass(frozen=True)
class Pronoun:
    form: str
    person: str
    french: str
    series: str | None = None


@dataclass(frozen=True)
class Tense:
    name: str
    label: str
    marker: str | None = None
    particle: bool = False
    suffix: str | None = None   # placé après le verbe
    object: bool = False        # un objet se place entre le marqueur et le verbe
    verb_particle: bool = False # le verbe qui suit l'objet prend aussi la particule
    no_subject: bool = False    # l'impératif ne montre pas son sujet


@dataclass(frozen=True)
class ParticleRule:
    """Particule placée devant le mot qui suit le sujet, choisie d'après son initiale."""

    persons: frozenset[str] = frozenset()
    by_initial: dict[str, str] = field(default_factory=dict)
    default: str | None = None
    unconfirmed: frozenset[str] = frozenset()


@dataclass(frozen=True)
class TenseRule:
    """Formes confirmées d'un verbe (ou d'une classe) pour un temps."""

    persons: frozenset[str] = frozenset()
    form: str | None = None
    exceptions: dict[str, str] = field(default_factory=dict)
    notes: str | None = None


@dataclass(frozen=True)
class ConjugationClass:
    name: str
    rules: dict[str, TenseRule] = field(default_factory=dict)


@dataclass(frozen=True)
class Verb:
    infinitive: str
    french: str
    form: str | None = None
    conjugation_class: str | None = None
    rules: dict[str, TenseRule] = field(default_factory=dict)
    gerund: str | None = None      # forme en -nV (dagana, rini)
    object_form: str | None = None # forme du verbe quand il a un objet (yiga)
    object_gerund: str | None = None # forme en -ni de la forme à objet (yigane)
    transitive: bool = False       # le verbe accepte un objet (confirmé)


class ConjugationEngine:
    def __init__(
        self,
        pronouns: list[Pronoun],
        tenses: dict[str, Tense],
        verbs: dict[str, Verb],
        classes: dict[str, ConjugationClass] | None = None,
        particles: ParticleRule | None = None,
    ) -> None:
        self.pronouns: dict[str, list[Pronoun]] = {}
        for p in pronouns:
            self.pronouns.setdefault(p.form, []).append(p)
        self.tenses = tenses
        self.verbs = verbs
        self.classes = classes or {}
        self.particles = particles or ParticleRule()
        self._check()

    def _check(self) -> None:
        for v in self.verbs.values():
            if v.conjugation_class and v.conjugation_class not in self.classes:
                raise ConjugationError(f"Classe inconnue '{v.conjugation_class}' pour le verbe '{v.infinitive}'")
        owners = [(v.infinitive, v.rules) for v in self.verbs.values()]
        owners += [(f"classe {c.name}", c.rules) for c in self.classes.values()]
        for owner, rules in owners:
            for tense, rule in rules.items():
                if tense not in self.tenses:
                    raise ConjugationError(f"Temps inconnu '{tense}' dans {owner}")
                for subject in rule.persons | rule.exceptions.keys():
                    if subject not in self.pronouns:
                        raise ConjugationError(f"Sujet inconnu '{subject}' dans {owner} ({tense})")
        for subject in self.particles.persons - self.pronouns.keys():
            raise ConjugationError(f"Sujet inconnu '{subject}' dans particules")

    def _rules(self, verb: Verb, tense: str) -> list[TenseRule]:
        rules = [verb.rules[tense]] if tense in verb.rules else []
        cls = self.classes.get(verb.conjugation_class or "")
        if cls and tense in cls.rules:
            rules.append(cls.rules[tense])
        return rules

    def particle(self, form: str) -> str:
        """Particule à placer devant le mot `form` (ex. daga → n')."""
        initial = _nfc(form)[:1].lower()
        if not initial:
            raise ConjugationNotDefinedError("Forme vide : particule indéterminable")
        if initial in self.particles.by_initial:
            return self.particles.by_initial[initial]
        if initial in self.particles.unconfirmed or self.particles.default is None:
            raise ConjugationNotDefinedError(f"Particle not confirmed for initial '{initial}' ('{form}')")
        return self.particles.default

    def is_conjugable(self, verb: str) -> bool:
        v = self.verbs.get(_nfc(verb))
        return bool(v and (v.rules or v.conjugation_class))

    def conjugate(self, verb: str, subject: str, tense: str, obj: str | None = None) -> str:
        predicate = self.predicate(verb, subject, tense, obj)
        if tense in self.tenses and self.tenses[tense].no_subject:
            return predicate
        return f"{_nfc(subject)} {predicate}"

    def predicate(self, verb: str, subject: str, tense: str, obj: str | None = None) -> str:
        """Tout ce qui suit le sujet : particule + marqueur (+ objet) + forme verbale."""
        subject = _nfc(subject)
        t = self.tenses[tense] if tense in self.tenses else None
        if t is not None:
            if t.object and obj is None:
                raise ConjugationNotDefinedError(f"Le temps '{tense}' demande un objet")
            if obj is not None and not t.object:
                raise ConjugationNotDefinedError(f"Le temps '{tense}' ne prend pas d'objet")
        form = self.verb_form(verb, subject, tense, obj is not None)
        t = self.tenses[tense]
        if t.verb_particle:
            form = self.particle(form) + form
        words = " ".join(p for p in (t.marker, _nfc(obj) if obj else None, form, t.suffix) if p)
        if t.particle and subject in self.particles.persons:
            words = self.particle(words) + words
        return words

    def verb_form(self, verb: str, subject: str, tense: str, with_object: bool = False) -> str:
        """Forme verbale seule, sans sujet ni marqueur de temps."""
        verb, subject = _nfc(verb), _nfc(subject)
        v = self.verbs.get(verb)
        if v is None:
            raise UnknownVerbError(f"Verbe inconnu : '{verb}'")
        if subject not in self.pronouns:
            raise UnknownSubjectError(f"Sujet inconnu : '{subject}'")
        if tense not in self.tenses:
            raise UnknownTenseError(f"Temps inconnu : '{tense}'")
        if not self.is_conjugable(verb):
            raise ConjugationNotDefinedError(f"Conjugation rule not defined for verb '{verb}'")

        rules = self._rules(v, tense)
        if not rules:
            raise ConjugationNotDefinedError(f"Conjugation rule not defined for verb '{verb}' in tense '{tense}'")
        if not any(subject in r.persons for r in rules):
            raise ConjugationNotDefinedError(
                f"Form not confirmed for verb '{verb}', subject '{subject}', tense '{tense}'"
            )

        if with_object and v.object_form and not any("{gerondif" in (r.form or "") for r in rules):
            return v.object_form
        form = next((r.exceptions[subject] for r in rules if subject in r.exceptions), None)
        if form is None:  # forme vide "" permise : le marqueur suffit (ex. okou yi rini)
            form = next((r.form for r in rules if r.form is not None), v.form)
        if form is None:
            raise ConjugationNotDefinedError(f"No verb form defined for '{verb}' in tense '{tense}'")
        for placeholder, value in (("{forme}", v.form), ("{gerondif_objet}", v.object_gerund),
                                   ("{gerondif}", v.gerund)):
            if placeholder in form:
                if value is None:
                    raise ConjugationNotDefinedError(f"Verb '{verb}' has no value for '{placeholder}'")
                form = form.replace(placeholder, value)
        return form

    @classmethod
    def from_paths(cls, paths: list[Path]) -> "ConjugationEngine":
        data: dict = {"pronoms": [], "temps": {}, "classes": {}, "verbes": {}, "particules": {}}
        for path in _yaml_files(paths):
            content = yaml.safe_load(_nfc(path.read_text(encoding="utf-8"))) or {}
            data["pronoms"] += content.get("pronoms") or []
            for key in ("temps", "classes", "verbes", "particules"):
                section = content.get(key) or {}
                if dup := data[key].keys() & section.keys():
                    raise ConjugationError(f"{key} définis plusieurs fois ({path.name}) : {sorted(dup)}")
                data[key].update(section)

        pronouns = [Pronoun(p["forme"], p["personne"], p["fr"], p.get("serie")) for p in data["pronoms"]]
        tenses = {
            name: Tense(name, t.get("nom", name), t.get("marqueur"), bool(t.get("particule")),
                        t.get("suffixe"), bool(t.get("objet")), bool(t.get("particule_verbe")),
                        bool(t.get("sans_sujet")))
            for name, t in data["temps"].items()
        }
        classes = {
            name: ConjugationClass(name, _parse_rules((c or {}).get("conjugaison")))
            for name, c in data["classes"].items()
        }
        verbs = {
            inf: Verb(
                infinitive=inf,
                french=v["fr"],
                form=v.get("forme"),
                conjugation_class=v.get("classe"),
                rules=_parse_rules(v.get("conjugaison")),
                gerund=v.get("gerondif"),
                object_form=v.get("forme_objet"),
                object_gerund=v.get("gerondif_objet"),
                transitive=bool(v.get("transitif")),
            )
            for inf, v in data["verbes"].items()
        }
        part = data["particules"]
        particles = ParticleRule(
            persons=frozenset(_nfc(x) for x in part.get("personnes") or []),
            by_initial={_nfc(k).lower(): v for k, v in (part.get("par_initiale") or {}).items()},
            default=part.get("defaut"),
            unconfirmed=frozenset(_nfc(k).lower() for k in part.get("a_confirmer") or []),
        )
        return cls(pronouns, tenses, verbs, classes, particles)


def _parse_rules(raw: dict | None) -> dict[str, TenseRule]:
    rules: dict[str, TenseRule] = {}
    for tense, r in (raw or {}).items():
        r = r or {}
        by_subject = {**(r.get("exceptions") or {}), **(r.get("formes") or {})}
        rules[tense] = TenseRule(
            persons=frozenset(r.get("personnes") or []) | frozenset(r.get("formes") or {}),
            form=r.get("forme"),
            exceptions=by_subject,
            notes=r.get("remarques"),
        )
    return rules


def _yaml_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for p in paths:
        files.extend(sorted(p.rglob("*.y*ml")) if p.is_dir() else [p])
    return files


@lru_cache(maxsize=1)
def default_engine() -> ConjugationEngine:
    return ConjugationEngine.from_paths([DEFAULT_GRAMMAR])


def conjugate(verb: str, subject: str, tense: str) -> str:
    return default_engine().conjugate(verb, subject, tense)
