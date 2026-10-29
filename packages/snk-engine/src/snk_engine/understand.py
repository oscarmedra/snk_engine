"""Comprendre une phrase soninké et la traduire en français.

C'est le sens inverse du reste du moteur : au lieu de produire une phrase à partir
de règles, on part du texte et on cherche ce qu'il contient. L'analyse se fait en
trois étapes, comme un compilateur :

  1. **segmentation** — phrases, puis mots ; la particule collée (n', m', l', ŋ', q')
     est détachée du mot qu'elle accentue ;
  2. **tagage** — chaque mot reçoit toutes les catégories possibles (pronom,
     déterminant, marqueur de temps, verbe, mot interrogatif, mot du lexique) ;
  3. **assemblage** — les catégories sont replacées dans l'ordre confirmé par la
     grammaire : sujet – marqueur – objet – verbe – compléments.

Rien n'est deviné. Un mot qu'aucune donnée ne couvre reste tel quel côté soninké et
devient le mot littéral « unknown » côté français, avec une note qui dit lequel.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .conjugation import DATA_DIR, ConjugationEngine, ConjugationError, default_engine
from .french import PERSONS, SUBJECTS, FrenchError, FrenchVerb, conjugate_fr
from .orthography import modernize

UNKNOWN = "[unknown]"
PARTICLES = ("n'", "m'", "l'", "ŋ'", "q'")
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
CLAUSE_SPLIT = re.compile(r"\s*([,;:])\s*")
PUNCTUATION = "…,;:.!?«»\"()"

# Mots interrogatifs confirmés (docs/langue/questions.md)
QUESTION_WORDS = {
    "minna": "où", "xa": "où", "mane-ni": "pourquoi", "mane": "quoi", "ko": "qui",
    "kan dimma": "quand", "mani-me": "combien", "moxo": "comment", "ba": "(question)",
}


class AnalysisError(ValueError):
    """Rien n'a pu être identifié dans la phrase."""


@dataclass(frozen=True)
class Token:
    index: int
    raw: str          # tel qu'écrit, ponctuation retirée
    word: str         # sans la particule, en orthographe du projet
    particle: str | None = None
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class Analysis:
    snk: str
    fr: str
    confirme: bool
    frame: dict
    notes: tuple[str, ...] = ()
    tokens: tuple[Token, ...] = ()
    ponctuation: str = ""   # ce qui suivait la proposition dans le texte (, ; : . ? !)


# --- Les données, lues une fois -------------------------------------------------

@dataclass(frozen=True)
class Lexicon:
    engine: ConjugationEngine
    verbs: dict[str, tuple[str, str]]        # forme → (clé du verbe, quel champ)
    reference_verbs: dict[str, str]          # radical → sens, non confirmés
    markers: dict[str, tuple[str, ...]]      # marqueur → temps possibles
    glossary: dict[str, str]                 # mot soninké → français
    french: dict[str, FrenchVerb] = field(default_factory=dict)


def _clean(word: str) -> str:
    return unicodedata.normalize("NFC", word).strip(PUNCTUATION).strip()


def _key(word: str) -> str:
    """Forme de comparaison : orthographe du projet, sans majuscule."""
    return modernize(_clean(word)).lower()


def _simple_meaning(snk, fr) -> bool:
    """Écarte les entrées ambiguës : « ? », parenthèses, plusieurs sens séparés par /."""
    if not isinstance(snk, str) or not isinstance(fr, str) or not snk or not fr:
        return False
    return not any(c in fr for c in "?(/") and "…" not in snk and "?" not in snk


def _walk_words(node) -> list[dict]:
    """Aplati data/references/mots.yaml, dont la structure varie selon les thèmes."""
    found: list[dict] = []
    if isinstance(node, dict):
        if "snk" in node:
            found.append(node)
        else:
            for value in node.values():
                found += _walk_words(value)
    elif isinstance(node, list):
        for item in node:
            found += _walk_words(item)
    return found


def load_lexicon(engine: ConjugationEngine | None = None, data_dir: Path | None = None) -> Lexicon:
    engine = engine or default_engine()
    data_dir = data_dir or DATA_DIR

    verbs: dict[str, tuple[str, str]] = {}
    for name, verb in engine.verbs.items():
        for field_name, form in (("forme", verb.form), ("gerondif", verb.gerund),
                                 ("forme_objet", verb.object_form),
                                 ("gerondif_objet", verb.object_gerund),
                                 ("nom_action", verb.action_noun)):
            if form:
                verbs.setdefault(_key(form), (name, field_name))
        # formes particulières déclarées dans les règles du verbe (riya, data…)
        for tense, rule in verb.rules.items():
            for form in [rule.form, *rule.exceptions.values()]:
                if form and "{" not in form:
                    verbs.setdefault(_key(form), (name, f"conjugaison.{tense}"))

    # verbes du locuteur, pas encore confirmés ; la section `sources` est écartée
    reference: dict[str, str] = {}
    ref_path = data_dir / "references" / "verbes.yaml"
    if ref_path.exists():
        data = yaml.safe_load(ref_path.read_text(encoding="utf-8")) or {}
        for item in (data.get("locuteur") or []) + (data.get("liste") or []):
            radical, sens = item.get("radical"), item.get("fr")
            if radical and sens and radical != "?" and "?" not in sens:
                reference.setdefault(_key(radical), sens)

    markers: dict[str, list[str]] = {}
    for name, tense in engine.tenses.items():
        if tense.marker:
            markers.setdefault(_key(tense.marker), []).append(name)

    glossary: dict[str, str] = {}
    objects_path = data_dir / "grammaire" / "objets.yaml"
    if objects_path.exists():
        data = yaml.safe_load(objects_path.read_text(encoding="utf-8")) or {}
        for item in (data.get("objets") or []) + (data.get("complements") or []):
            if _simple_meaning(item.get("snk"), item.get("fr")):
                glossary.setdefault(_key(item["snk"]), item["fr"])
    words_path = data_dir / "references" / "mots.yaml"
    if words_path.exists():
        data = yaml.safe_load(words_path.read_text(encoding="utf-8")) or {}
        for item in _walk_words(data):
            if _simple_meaning(item.get("snk"), item.get("fr")):
                glossary.setdefault(_key(item["snk"]), item["fr"])

    french: dict[str, FrenchVerb] = {}
    raw = yaml.safe_load((data_dir / "grammaire" / "soninke.yaml").read_text(encoding="utf-8")) or {}
    for name, verb in (raw.get("verbes") or {}).items():
        if verb.get("francais"):
            french[name] = FrenchVerb.from_data(name, verb["francais"])

    return Lexicon(engine, verbs, reference, {k: tuple(v) for k, v in markers.items()}, glossary, french)


# --- Étape 1 : segmentation -----------------------------------------------------

def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in SENTENCE_SPLIT.split(text.strip()) if s.strip()]


def tokenize(sentence: str) -> list[Token]:
    tokens = []
    for i, raw in enumerate(w for w in sentence.split() if _clean(w)):
        word = _clean(raw)
        particle = next((p for p in PARTICLES if word.lower().startswith(p) and len(word) > len(p)), None)
        tokens.append(Token(i, word, word[len(particle):] if particle else word, particle))
    return tokens


# --- Étape 2 : tagage -----------------------------------------------------------

def tag(tokens: list[Token], lex: Lexicon) -> list[Token]:
    """Donne à chaque mot toutes ses catégories possibles ; l'assemblage tranchera."""
    tagged = []
    for token in tokens:
        key = _key(token.word)
        tags = []
        if key in lex.engine.pronouns:
            tags.append("pronom")
        if key in ("ke", "ku"):
            tags.append("determinant")
        if key in lex.markers:
            tags.append("marqueur")
        if key in lex.verbs:
            tags.append("verbe")
        elif key in lex.reference_verbs:
            tags.append("verbe_reference")
        if key in QUESTION_WORDS:
            tags.append("interrogatif")
        if key in lex.glossary:
            tags.append("lexique")
        tagged.append(Token(token.index, token.raw, token.word, token.particle, tuple(tags)))
    return tagged


def _marker_at(tokens: list[Token], i: int, lex: Lexicon) -> tuple[str, tuple[str, ...], int] | None:
    """Marqueur d'un ou deux mots à partir de la position i (« yi rini », « n'ti rini »)."""
    for length in (2, 1):
        if i + length > len(tokens):
            continue
        for use_raw in (True, False):
            text = " ".join((t.raw if use_raw else t.word) for t in tokens[i:i + length])
            tenses = lex.markers.get(_key(text))
            if tenses:
                return _key(text), tenses, length
    return None


# --- Étape 3 : assemblage -------------------------------------------------------

def assemble(tokens: list[Token], lex: Lexicon) -> tuple[dict, list[str]]:
    notes: list[str] = []
    frame: dict = {"sujet": None, "personne": None, "temps": None, "objet": None,
                   "verbe": None, "verbe_confirme": False, "forme_verbe": None,
                   "complements": [], "question": None, "sujet_nominal": False}
    i = 0

    # 1. sujet : un pronom en tête de phrase
    if tokens and "pronom" in tokens[0].tags:
        pronoun = _key(tokens[0].word)
        if pronoun == "xa" and len(tokens) > 1:
            notes.append("« xa » en tête : lu comme le pronom « vous » (il peut aussi vouloir dire « où »)")
        frame["sujet"] = pronoun
        frame["personne"] = lex.engine.pronouns[pronoun][0].person
        i = 1
        # « a renme di maro n'yiga » : le marqueur ne suit pas le pronom mais le nom,
        # donc le pronom est ici un possessif et le groupe entier est le sujet
        if not _marker_at(tokens, 1, lex):
            for j in range(2, min(len(tokens), 6)):
                if "verbe" in tokens[j - 1].tags:
                    break
                if _marker_at(tokens, j, lex):
                    frame["sujet"] = " ".join(x.raw for x in tokens[:j])
                    frame["sujet_nominal"] = True
                    frame["personne"] = "3pl" if _key(tokens[j - 1].word) == "ku" else "3sg"
                    i = j
                    break
    elif tokens and "verbe" not in tokens[0].tags:
        # Sujet nominal : « n'ma di o su xiri » (ma mère appelle tout le monde).
        # Un texte suivi parle de gens et de choses, pas de « il » et « nous ».
        #
        # On ne le retient que si un marqueur de temps suit, sans quoi la phrase est
        # un impératif, qui commence lui aussi sans pronom : « kudu xa kini ŋa »
        # (donne-moi une cuillère) n'a pas de sujet, et n'en veut pas.
        for j in range(1, min(len(tokens), 6)):
            if _marker_at(tokens, j, lex):
                # on prend le mot entier : dans « n'ma » (ma mère) le n' est le
                # possessif, pas la particule verbale que le tokeniseur a détachée
                mots = [t.raw for t in tokens[:j]]
                frame["sujet"] = " ".join(mots)
                frame["sujet_nominal"] = True
                # `ku` est le déterminant du pluriel ; sinon le nom vaut un « il »
                frame["personne"] = "3pl" if _key(mots[-1]) == "ku" else "3sg"
                i = j
                break

    # 2. marqueur de temps
    candidates: tuple[str, ...] = ()
    marker_at = None
    found = _marker_at(tokens, i, lex)
    if found:
        _, candidates, length = found
        marker_at, i = i, i + length

    # 3. verbe, et ce qui le précède (l'objet)
    verb_at = next((j for j in range(i, len(tokens))
                    if {"verbe", "verbe_reference"} & set(tokens[j].tags)), None)
    if verb_at is None and marker_at is not None:
        # certains mots sont à la fois marqueur et verbe (« rini » : futur lointain,
        # mais aussi forme en -ni de « venir ») : sans autre verbe, c'est le verbe
        for j in range(marker_at, i):
            if "verbe" in tokens[j].tags:
                verb_at, i, candidates = j, marker_at, ()
                notes.append(f"« {tokens[j].word} » lu comme verbe, faute d'un autre verbe dans la phrase")
                break
    if verb_at is not None:
        object_tokens = [t for t in tokens[i:verb_at] if "interrogatif" not in t.tags]
        if object_tokens:
            frame["objet"] = " ".join(t.word for t in object_tokens)
        verb_token = tokens[verb_at]
        key = _key(verb_token.word)
        if "verbe" in verb_token.tags:
            frame["verbe"], frame["forme_verbe"] = lex.verbs[key]
            frame["verbe_confirme"] = True
        else:
            frame["verbe"] = lex.reference_verbs[key]
            notes.append(f"« {verb_token.word} » : verbe connu mais non confirmé ({frame['verbe']})")
        rest = tokens[verb_at + 1:]
    else:
        rest = tokens[i:]
        notes.append("aucun verbe reconnu")

    # 4. choisir le temps parmi les candidats : d'abord l'objet, puis vérification
    #    croisée en reconjuguant avec le moteur (le bon temps redonne la phrase)
    if candidates:
        wants_object = frame["objet"] is not None
        matching = [t for t in candidates if lex.engine.tenses[t].object == wants_object] or list(candidates)
        if (len(matching) > 1 and frame["sujet"] and frame["verbe_confirme"]
                and not frame["sujet_nominal"]):
            observed = _key(" ".join(t.raw for t in tokens))
            regenerated = []
            for tense in matching:
                try:
                    produced = lex.engine.conjugate(frame["verbe"], frame["sujet"], tense, frame["objet"])
                except ConjugationError:
                    continue
                if observed.startswith(_key(produced)):
                    regenerated.append(tense)
            matching = regenerated or matching
        frame["temps"] = matching[0]
        if len(matching) > 1:
            notes.append(f"plusieurs temps possibles : {', '.join(matching)}")
    elif frame["verbe"] and frame["sujet"]:
        if frame.get("forme_verbe") in ("gerondif", "gerondif_objet", "nom_action"):
            # une forme en -ni sans marqueur : le temps ne se déduit pas
            notes.append(f"« {frame['verbe']} » est à la forme en -ni sans marqueur : temps non identifié")
        else:
            frame["temps"] = "past_object" if frame["objet"] else "past"
    elif frame["verbe"] and not frame["sujet"]:
        frame["temps"] = "imperatif_objet" if frame["objet"] else "imperatif"

    # 5. compléments et mot interrogatif
    for token in rest:
        if "interrogatif" in token.tags and (token.index == len(tokens) - 1 or _key(token.word) != "xa"):
            frame["question"] = QUESTION_WORDS[_key(token.word)]
        elif "determinant" in token.tags and frame["complements"]:
            frame["complements"][-1] += f" {token.word}"
        else:
            frame["complements"].append(token.word)

    # 5a. le suffixe du temps (watia, ni ya me) appartient au verbe, pas aux compléments
    suffix = lex.engine.tenses[frame["temps"]].suffix if frame["temps"] else None
    if suffix:
        parts = [_key(w) for w in suffix.split()]
        tail = [_key(w) for w in frame["complements"][-len(parts):]]
        if tail == parts:
            frame["complements"] = frame["complements"][:-len(parts)]

    # 5b. les expressions du lexique en plusieurs mots (koota su, kan dimma)
    merged: list[str] = []
    for word in frame["complements"]:
        if merged and _key(f"{merged[-1]} {word}") in lex.glossary:
            merged[-1] = f"{merged[-1]} {word}"
        else:
            merged.append(word)
    # un mot interrogatif en deux mots (« kan dimma ») n'apparaît qu'une fois regroupé
    kept = []
    for word in merged:
        if _key(word) in QUESTION_WORDS and frame["question"] is None:
            frame["question"] = QUESTION_WORDS[_key(word)]
        else:
            kept.append(word)
    frame["complements"] = kept

    # 6. vérification croisée de la particule
    for token in tokens:
        if token.particle:
            try:
                expected = lex.engine.particle(token.word)
            except ConjugationError:
                continue
            if expected != token.particle:
                notes.append(f"particule inattendue : « {token.raw} » (attendu {expected}{token.word})")

    if frame["sujet"] is None and frame["verbe"] is None:
        raise AnalysisError("aucun sujet ni verbe reconnu dans la phrase")
    return frame, notes


# --- Génération du français -----------------------------------------------------

def _translate(word: str, lex: Lexicon, notes: list[str]) -> str:
    fr = lex.glossary.get(_key(word))
    if fr:
        return fr
    notes.append(f"« {word} » : mot absent du lexique → {UNKNOWN}")
    return UNKNOWN


# Un pronom posé devant un nom en est le possessif. Le guide d'écriture le donne :
# « n ma » (ma mère), « an yaqe » (ta femme), « a renme » (son enfant),
# « o faaba » (notre père), « axa ma » (votre mère), « i renme » (leur enfant).
POSSESSIFS = {
    "n": ("mon", "ma"), "in": ("mon", "ma"), "nke": ("mon", "ma"),
    "an": ("ton", "ta"), "anke": ("ton", "ta"),
    "a": ("son", "sa"), "ake": ("son", "sa"),
    "o": ("notre", "notre"), "oku": ("notre", "notre"),
    "xa": ("votre", "votre"), "axa": ("votre", "votre"), "xaku": ("votre", "votre"),
    "i": ("leur", "leur"), "iku": ("leur", "leur"),
}


# Plusieurs sens coexistent pour un même mot : « ma » vaut « jusqu'à » autant que
# « mère ». Dans un possessif seul un nom a un sens, et « mon jusqu'à » n'en a aucun.
GRAMMATICAL = ("prédicatif", "jusqu", "introduit", "marque", "particule", "postposition",
               "conjonction", "pronom", "adverbe", "suffixe", "pluriel")


def _mot_grammatical(sens: str) -> bool:
    bas = sens.lower()
    return any(g in bas for g in GRAMMATICAL) or bas in ("ou", "et", "mais", "dans", "avec")


def _traduire_sujet(sujet: str, lex: Lexicon, notes: list[str]) -> str | None:
    """Traduit un groupe sujet : un nom, ou un pronom possessif suivi d'un nom."""
    direct = _translate(sujet, lex, notes)
    if direct and UNKNOWN not in direct:
        return direct

    mots = sujet.split()
    tete = _key(mots[0]).rstrip("'")
    # « n'ma » s'écrit collé : le possessif est la particule que le tokeniseur a ôtée
    if len(mots) == 1:
        for prefixe in ("n'", "ŋ'", "m'", "l'"):
            if sujet.lower().startswith(prefixe):
                tete, mots = "n", [prefixe, sujet[len(prefixe):]]
                break
    if tete not in POSSESSIFS or len(mots) < 2:
        return None

    nom_fr = _translate(" ".join(mots[1:]), lex, notes)
    if not nom_fr or UNKNOWN in nom_fr or _mot_grammatical(nom_fr):
        return None
    masculin, feminin = POSSESSIFS[tete]
    # le genre se lit dans l'article de la glose, qu'on remplace par le possessif
    sans_article = re.sub(r"^(le |la |les |l'|un |une |du |de la |des )", "", nom_fr, flags=re.I)
    feminin_ici = re.match(r"^(la |une |de la )", nom_fr, flags=re.I) is not None
    return f"{feminin if feminin_ici else masculin} {sans_article}"


def to_french(frame: dict, lex: Lexicon, notes: list[str]) -> str:
    complements = [_translate(w, lex, notes) for w in frame["complements"]]
    obj_fr = _translate(frame["objet"], lex, notes) if frame["objet"] else None
    person = frame["personne"] or "2sg"
    subject = SUBJECTS.get(person, UNKNOWN)
    # un sujet nominal se traduit et prend la place du pronom : « le père a mangé »
    # plutôt que « il a mangé »
    sujet_fr = _traduire_sujet(frame["sujet"], lex, notes) if frame["sujet_nominal"] else None
    if sujet_fr:
        subject = sujet_fr

    if frame["verbe_confirme"] and frame["temps"] and frame["verbe"] in lex.french:
        try:
            core = conjugate_fr(lex.french[frame["verbe"]], person, frame["temps"], obj_fr)
            if sujet_fr:
                pronom = SUBJECTS.get(person, "")
                if core.startswith(f"{pronom} "):
                    core = f"{sujet_fr} {core[len(pronom) + 1:]}"
        except FrenchError as exc:
            notes.append(f"pas de traduction française pour ce temps ({exc}) → {UNKNOWN}")
            core = f"{subject} {UNKNOWN}" + (f" {obj_fr}" if obj_fr else "")
    else:
        if frame["verbe"] and not frame["verbe_confirme"]:
            verb_fr = f"{frame['verbe']} [non confirmé]"
        else:
            if frame["verbe"] and not frame["temps"]:
                notes.append(f"temps non identifié → {UNKNOWN}")
            elif not frame["verbe"]:
                notes.append(f"verbe non reconnu → {UNKNOWN}")
            verb_fr = UNKNOWN
        parts = [subject] if frame["sujet"] else []
        parts.append(verb_fr)
        if obj_fr:
            parts.append(obj_fr)
        core = " ".join(parts)

    phrase = " ".join([core, *complements]).strip()
    if frame["question"]:
        phrase = f"{phrase} {frame['question']}".strip() if frame["question"] != "(question)" else phrase
        return phrase.rstrip(" ?") + " ?"
    return phrase


def collapse_unknowns(text: str) -> str:
    """« [unknown] [unknown] [unknown] » → « [unknown] » : une seule marque par passage."""
    return re.sub(rf"(?:{re.escape(UNKNOWN)}\s*)+", UNKNOWN + " ", text).strip()


# --- Entrée publique ------------------------------------------------------------

def analyze(sentence: str, lex: Lexicon | None = None) -> Analysis:
    """Analyse une proposition. Lève AnalysisError si rien n'y est reconnu."""
    lex = lex or load_lexicon()
    tokens = tag(tokenize(sentence), lex)
    frame, notes = assemble(tokens, lex)
    french = collapse_unknowns(to_french(frame, lex, notes))
    confirmed = bool(frame["verbe_confirme"] and frame["temps"]) and UNKNOWN not in french
    return Analysis(sentence.strip(), french, confirmed, frame, tuple(notes), tuple(tokens))


def _word_by_word(clause: str, lex: Lexicon) -> Analysis:
    """Dernier recours : aucune structure reconnue, on traduit mot à mot ce qui peut l'être."""
    tokens = tag(tokenize(clause), lex)
    notes: list[str] = ["aucune structure de phrase reconnue : traduction mot à mot"]
    words = []
    for t in tokens:
        key = _key(t.word)
        if key in lex.glossary:
            words.append(lex.glossary[key])
        else:
            words.append(UNKNOWN)
            notes.append(f"« {t.raw} » : non reconnu → {UNKNOWN}")
    return Analysis(clause.strip(), collapse_unknowns(" ".join(words)), False, {}, tuple(notes), tuple(tokens))


def analyze_text(text: str, lex: Lexicon | None = None) -> list[Analysis]:
    """Traduit n'importe quel texte, sans jamais échouer.

    Le texte est découpé en phrases, puis en propositions (sur , ; :). Chaque
    proposition est analysée ; si rien n'y est reconnu, elle est traduite mot à mot,
    et tout ce qui n'est pas compris devient [unknown].
    """
    lex = lex or load_lexicon()
    results: list[Analysis] = []
    for sentence in split_sentences(text):
        end = sentence[-1] if sentence[-1] in ".!?" else ""
        parts = CLAUSE_SPLIT.split(sentence.rstrip(".!?").strip())
        clauses = [(parts[i], parts[i + 1] if i + 1 < len(parts) else end) for i in range(0, len(parts), 2)]
        for clause, punct in clauses:
            if not _clean(clause):
                continue
            try:
                a = analyze(clause, lex)
            except AnalysisError:
                a = _word_by_word(clause, lex)
            results.append(Analysis(a.snk, a.fr, a.confirme, a.frame, a.notes, a.tokens, punct))
    return results


def render(analyses: list[Analysis]) -> str:
    """Recompose la traduction d'un texte, avec sa ponctuation."""
    out = ""
    for a in analyses:
        out += a.fr + (a.ponctuation if a.ponctuation in ".!?" else a.ponctuation) + " "
    return re.sub(r"\s+([,;:.!?])", r"\1", out).strip()
