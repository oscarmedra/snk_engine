import unicodedata
from pathlib import Path

import pytest

from snk_engine.conjugation import (
    ConjugationEngine,
    ConjugationError,
    ConjugationNotDefinedError,
    UnknownSubjectError,
    UnknownTenseError,
    UnknownVerbError,
    conjugate,
    default_engine,
)


# --- Formes confirmées (corp1.xlsx + corrections) ---------------------------

@pytest.mark.parametrize(
    "subject, tense, expected",
    [
        ("nke", "past", "nke daga"),
        ("anke", "past", "anke n'daga"),
        ("ake", "past", "ake n'daga"),
        ("oku", "past", "oku daga"),
        ("xaku", "past", "xaku n'daga"),
        ("iku", "past", "iku n'daga"),
        ("nke", "imminent", "nke fayi rini daga"),
        ("anke", "imminent", "anke m'fayi rini daga"),
        ("nke", "progressive_watia", "nke fayi dagana watia"),
        ("anke", "progressive_watia", "anke m'fayi dagana watia"),
        ("nke", "future", "nke yi rini daga"),
        ("anke", "future", "anke n'yi rini daga"),
        ("ake", "future", "ake n'yi rini daga"),
        ("oku", "future", "oku yi rini daga"),
        ("xaku", "future", "xaku n'yi rini daga"),
        ("nke", "past_negative", "nke maxa daga"),
        ("anke", "past_negative", "anke maxa daga"),
        ("nke", "future_negative", "nke n'ti rini daga"),
        ("anke", "future_negative", "anke n'ti rini daga"),
        ("anke", "future_negative_ntaxa", "anke n'taxa rini daga"),
    ],
)
def test_dagaer_confirmed_forms(subject, tense, expected):
    assert conjugate("dagaer", subject, tense) == expected


@pytest.mark.parametrize(
    "verb, subject, tense, expected",
    [
        ("rier", "nke", "past", "nke ri"),
        ("rier", "anke", "past", "anke l'ri"),
        ("rier", "ake", "past", "ake l'ri"),
        ("rier", "oku", "past", "oku ri"),
        ("rier", "xaku", "past", "xaku l'ri"),
        ("rier", "oku", "future", "oku yi rini"),
        ("rier", "ake", "future", "ake n'yi rini"),
        ("fayinder", "ake", "past", "ake m'faye"),
        ("mini", "ake", "past", "ake m'mini"),
        ("wori", "ake", "past", "ake ŋ'wori"),
        ("fayinder", "n", "en_cours", "n yi fayeni"),
        ("mini", "n", "en_cours", "n yi minini"),
        ("wori", "anke", "en_cours", "anke n'yi worini"),
        ("dagaer", "nke", "demande", "nke na daga"),
        ("yigeyer", "a", "demande", "a na yige"),
        ("wurier", "o", "demande", "o na wuru"),
        ("wurier", "n", "en_cours", "n yi wurunu"),
        ("wurier", "an", "en_cours", "an yi wurunu"),
        ("wurier", "i", "en_cours", "i yi wurunu"),
        ("dagaer", "a", "en_cours", "a yi dagana"),
        ("dagaer", "xa", "en_cours", "xa yi dagana"),
        ("wurier", "nke", "en_cours", "nke yi wurunu"),
        ("wurier", "anke", "en_cours", "anke n'yi wurunu"),
        ("wurier", "iku", "en_cours", "iku n'yi wurunu"),
        ("dagaer", "oku", "en_cours", "oku yi dagana"),
        ("rier", "iku", "future_negative", "iku n'ti rini"),
        ("yigeyer", "ake", "progressive_watia", "ake m'fayi yigene watia"),
        ("wurier", "ake", "progressive_watia", "ake m'fayi wurunu watia"),
        ("sefeer", "anke", "future_negative", "anke n'ti rini sefe"),
        ("wurier", "anke", "future_negative", "anke n'ti rini wuru"),
        ("sefeer", "ake", "progressive_watia", "ake m'fayi sefene watia"),
        ("yigeyer", "ake", "past", "ake n'yige"),
        ("sefeer", "ake", "past", "ake n'sefe"),
        ("wurier", "ake", "past", "ake ŋ'wuru"),
    ],
)
def test_other_verbs_confirmed_forms(verb, subject, tense, expected):
    assert conjugate(verb, subject, tense) == expected


@pytest.mark.parametrize(
    "verb, subject, obj, expected",
    [
        ("yigeyer", "ake", "maro", "ake n'di maro n'yiga"),
        ("yigeyer", "anke", "maro", "anke n'di maro n'yiga"),
        ("yigeyer", "oku", "maro", "oku di maro n'yiga"),
        ("yigeyer", "n", "maro", "n di maro n'yiga"),
        ("yigeyer", "ake", "maro ke", "ake n'di maro ke n'yiga"),
        ("mini", "ake", "xati", "ake n'di xati m'mini"),
        ("mini", "oku", "xati", "oku di xati m'mini"),
    ],
)
def test_object_clause(verb, subject, obj, expected):
    assert default_engine().conjugate(verb, subject, "past_object", obj) == expected


@pytest.mark.parametrize(
    "subject, expected",
    [
        ("nke", "nke yi maro yigane"),
        ("anke", "anke n'yi maro yigane"),
        ("ake", "ake n'yi maro yigane"),
        ("oku", "oku yi maro yigane"),
        ("xaku", "xaku n'yi maro yigane"),
        ("iku", "iku n'yi maro yigane"),
        ("n", "n yi maro yigane"),
        ("a", "a yi maro yigane"),
        ("i", "i yi maro yigane"),
    ],
)
def test_en_cours_with_object(subject, expected):
    # la particule se colle à yi ; le verbe après l'objet reste nu (≠ passé avec objet)
    assert default_engine().conjugate("yigeyer", subject, "en_cours_objet", "maro") == expected


def test_demande_with_object():
    e = default_engine()
    assert e.conjugate("yigeyer", "a", "demande_objet", "maro") == "a na maro n'yiga"
    assert e.conjugate("mini", "n", "demande_objet", "xati") == "n na xati m'mini"
    with pytest.raises(ConjugationNotDefinedError):   # particule avec ake : à confirmer
        e.conjugate("yigeyer", "ake", "demande")


def test_object_is_required_and_refused():
    e = default_engine()
    with pytest.raises(ConjugationNotDefinedError, match="demande un objet"):
        e.conjugate("yigeyer", "ake", "past_object")
    with pytest.raises(ConjugationNotDefinedError, match="ne prend pas d'objet"):
        e.conjugate("yigeyer", "ake", "past", "maro")


def test_object_form_differs_from_bare_form():
    e = default_engine()
    assert e.conjugate("yigeyer", "ake", "past") == "ake n'yige"          # sans objet
    assert e.conjugate("yigeyer", "ake", "past_object", "maro").endswith("n'yiga")


def test_keyword_api():
    assert conjugate(verb="dagaer", subject="nke", tense="past") == "nke daga"


# --- Règles A-C généralisées (confirmées pour tous les verbes) ---------------

@pytest.mark.parametrize(
    "verb, subject, tense, expected",
    [
        ("sefeer", "oku", "past", "oku sefe"),
        ("sefeer", "iku", "future", "iku n'yi rini sefe"),
        ("rier", "iku", "future", "iku n'yi rini"),
        ("wurier", "nke", "future", "nke yi rini wuru"),
    ],
)
def test_regular_class_derives_past_and_future(verb, subject, tense, expected):
    assert conjugate(verb, subject, tense) == expected


@pytest.mark.parametrize(
    "verb, subject, tense, expected",
    [
        ("dagaer", "an", "past", "an daga"),
        ("dagaer", "a", "past", "a daga"),
        ("dagaer", "o", "past", "o daga"),
        ("dagaer", "xa", "past", "xa daga"),
        ("dagaer", "i", "past", "i daga"),
        ("dagaer", "a", "future", "a yi rini daga"),
        ("rier", "an", "past", "an ri"),
        ("sefeer", "i", "future", "i yi rini sefe"),
        ("dagaer", "a", "past_negative", "a maxa daga"),
        ("sefeer", "i", "past_negative", "i maxa sefe"),
        ("rier", "anke", "past_negative", "anke maxa ri"),
    ],
)
def test_short_pronouns_never_take_particle(verb, subject, tense, expected):
    assert conjugate(verb, subject, tense) == expected


def test_particle_never_for_nke_oku():
    engine = default_engine()
    for verb in engine.verbs:
        for tense in ("past", "future"):
            for subject in ("nke", "oku", "an", "a", "o", "xa", "i"):
                assert "'" not in engine.predicate(verb, subject, tense)


# --- Rien n'est inventé ------------------------------------------------------

@pytest.mark.parametrize(
    "verb, subject, tense",
    [
        ("dagaer", "xaku", "imminent"),  # particule avec xaku/iku au progressif : à confirmer
        ("dagaer", "ake", "future_negative"),  # seulement nke et anke confirmés
        ("sefeer", "nke", "imminent"),
        ("dagaer", "iku", "progressive_watia"),  # particule avec iku au progressif : à confirmer
        ("dagaer", "a", "imminent"),
    ],
)
def test_unconfirmed_forms_are_refused(verb, subject, tense):
    with pytest.raises(ConjugationNotDefinedError):
        conjugate(verb, subject, tense)


def test_verbs_are_registered():
    engine = default_engine()
    expected = {"dagaer": "partir", "rier": "venir", "fayinder": "regarder", "sefeer": "parler",
                "yigeyer": "manger", "mini": "boire", "wori": "voir", "wurier": "courir"}
    assert {k: v.french for k, v in engine.verbs.items()} == expected


def test_unknown_inputs():
    with pytest.raises(UnknownVerbError):
        conjugate("aller", "nke", "past")
    with pytest.raises(UnknownSubjectError):
        conjugate("dagaer", "moi", "past")
    with pytest.raises(UnknownTenseError):
        conjugate("dagaer", "nke", "imparfait")


# --- Données et Unicode ------------------------------------------------------

def test_pronouns_in_confirmed_orthography():
    engine = default_engine()
    assert list(engine.pronouns) == ["nke", "anke", "ake", "oku", "xaku", "iku", "n", "an", "a", "o", "xa", "i"]
    assert [p.french for p in engine.pronouns["xaku"]] == ["vous"]
    assert [p.series for p in engine.pronouns["xa"]] == ["diminutif"]
    assert [p.french for p in engine.pronouns["iku"]] == ["ils / elles"]


def test_orthography_x_u_e():
    engine = default_engine()
    texts = list(engine.pronouns) + [t.marker or "" for t in engine.tenses.values()]
    texts += [x for v in engine.verbs.values() for x in (v.infinitive, v.form or "", v.gerund or "")]
    assert not any(bad in t for t in texts for bad in ("kh", "ou", "é", "gue", "gui"))


def test_old_spelling_is_refused():
    with pytest.raises(UnknownSubjectError):
        conjugate("dagaer", "nké", "past")


def test_decomposed_unicode_input_is_normalized(tmp_path):
    text = GRAMMAR.replace("p1", "pé")
    e = _engine(tmp_path, text)
    assert e.conjugate("v1", unicodedata.normalize("NFD", "pé"), "t") == "pé m pre-base"


# --- Mécanique du moteur (données fictives, pas du soninke) -----------------

GRAMMAR = """
pronoms:
  - {forme: p1, personne: 1sg, fr: x}
  - {forme: p2, personne: 2sg, fr: y}
temps:
  t: {nom: t, marqueur: m}
classes:
  c:
    conjugaison:
      t: {forme: "pre-{forme}", personnes: [p1, p2], exceptions: {p2: exc}}
verbes:
  v1: {fr: a, forme: base, classe: c}
  v2: {fr: b, forme: base, classe: c, conjugaison: {t: {personnes: [p1], exceptions: {p1: propre}}}}
"""

PARTICLE_GRAMMAR = """
pronoms:
  - {forme: p1, personne: 1sg, fr: x}
  - {forme: p2, personne: 2sg, fr: y}
temps:
  sans: {nom: sans, marqueur: null, particule: true}
  avec: {nom: avec, marqueur: bo, particule: true}
  neutre: {nom: neutre, marqueur: null}
particules:
  personnes: [p2]
  par_initiale: {b: "m'"}
  defaut: "n'"
  a_confirmer: [p]
classes:
  r:
    conjugaison:
      sans: {personnes: [p1, p2]}
      avec: {personnes: [p1, p2]}
      neutre: {personnes: [p1, p2]}
verbes:
  v: {fr: a, forme: daa, classe: r}
  w: {fr: b, forme: poo, classe: r}
"""


def _engine(tmp_path: Path, text: str = GRAMMAR) -> ConjugationEngine:
    f = tmp_path / "g.yaml"
    f.write_text(text, encoding="utf-8")
    return ConjugationEngine.from_paths([tmp_path])


def test_class_rules_and_exceptions(tmp_path):
    e = _engine(tmp_path)
    assert e.conjugate("v1", "p1", "t") == "p1 m pre-base"
    assert e.conjugate("v1", "p2", "t") == "p2 m exc"
    assert e.conjugate("v2", "p1", "t") == "p1 m propre"  # le verbe prime sur sa classe


def test_invalid_data_is_rejected(tmp_path):
    with pytest.raises(ConjugationError, match="Classe inconnue"):
        _engine(tmp_path, GRAMMAR.replace("classe: c}", "classe: zz}", 1))
    with pytest.raises(ConjugationError, match="Sujet inconnu"):
        _engine(tmp_path, GRAMMAR.replace("exceptions: {p2: exc}", "exceptions: {p9: exc}"))
    with pytest.raises(ConjugationError, match="Sujet inconnu"):
        _engine(tmp_path, PARTICLE_GRAMMAR.replace("personnes: [p2]", "personnes: [p9]"))


def test_particle_attaches_to_first_word_after_subject(tmp_path):
    e = _engine(tmp_path, PARTICLE_GRAMMAR)
    assert e.conjugate("v", "p1", "sans") == "p1 daa"       # sujet sans particule
    assert e.conjugate("v", "p2", "sans") == "p2 n'daa"     # devant le verbe
    assert e.conjugate("v", "p2", "avec") == "p2 m'bo daa"  # devant le marqueur, selon son initiale
    assert e.conjugate("v", "p2", "neutre") == "p2 daa"        # temps sans particule
    assert e.conjugate("w", "p2", "avec") == "p2 m'bo poo"
    with pytest.raises(ConjugationNotDefinedError, match="Particle not confirmed"):
        e.conjugate("w", "p2", "sans")


# --- Particules --------------------------------------------------------------

@pytest.mark.parametrize(
    "form, expected",
    [
        ("mara", "m'"),   # exemple confirmé : maréer → m'mara
        ("daga", "n'"),
        ("yi rini", "n'"),
        ("bxx", "m'"),
        ("fxx", "m'"),
        ("rxx", "l'"),
        ("Rxx", "l'"),
    ],
)
def test_particle_by_initial(form, expected):
    assert default_engine().particle(form) == expected


@pytest.mark.parametrize("form", ["nxx", "pxx", "lxx"])
def test_particle_unconfirmed_initials(form):
    with pytest.raises(ConjugationNotDefinedError, match="Particle not confirmed"):
        default_engine().particle(form)
